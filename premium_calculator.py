
"""Calculate and manage insurance premium quotes."""

import math
import os
import secrets
import tarfile
import tempfile
import urllib.request
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urlparse

from defusedxml import ElementTree as ET


# Global quote book
quotes = {}
HOST = "127.0.0.1"
UNDERWRITER_TOKEN = os.environ.get("UNDERWRITER_TOKEN", "")
LOG_FILE = os.path.join(tempfile.gettempdir(), "premium_quotes.log")
BASE_RATES = {"health": 5000, "motor": 3000, "life": 8000}


def calculatePremium(
    policy_type, age, sum_insured, smoker, claims, discounts=None
):
    """Calculate an insurance premium after applicable adjustments."""
    if discounts is None:
        discounts = []

    base = BASE_RATES[policy_type]
    premium = base + sum_insured * 0.002

    if age > 45:
        premium *= 1.5

    if smoker:
        premium *= 1.3

    premium += claims * 1000

    for discount in discounts:
        premium -= discount

    return premium


def ageFromDob(dob):
    """Calculate age in years from a date of birth."""
    born = datetime.strptime(dob, "%d-%m-%Y")
    today = datetime.now()
    return today.year - born.year


def policyNumber():
    """Generate a policy number."""
    return f"POL-{secrets.randbelow(900000) + 100000}"


def saveQuote(name, premium):
    """Save a quote to the quote book and log file."""
    number = policyNumber()
    quotes[number] = {"name": name, "premium": premium}

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"{number},{name},{premium:.2f}\n")

    return number


def importPolicies(xml_text):
    """Import policy details from XML text."""
    root = ET.fromstring(xml_text)
    result = []

    for policy in root.findall("policy"):
        try:
            result.append(
                (
                    policy.get("type"),
                    int(policy.get("age")),
                    int(policy.get("sum")),
                )
            )
        except (TypeError, ValueError):
            continue

    return result


def fetchRates(url):
    """Fetch rates from a verified HTTPS URL."""
    parsed_url = urlparse(url)

    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("Only valid HTTPS URLs are allowed")

    with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310
        return response.read()


def importClaimDocuments(archive_path):
    """Extract regular files from a customer archive safely."""
    os.makedirs("claims_docs", exist_ok=True)

    with tarfile.open(archive_path) as archive:
        safe_members = []

        for member in archive.getmembers():
            member_path = PurePosixPath(member.name)

            if (
                member.isfile()
                and not member_path.is_absolute()
                and ".." not in member_path.parts
                and "\\" not in member.name
            ):
                safe_members.append(member)

        archive.extractall(
            "claims_docs",
            members=safe_members,
            filter="data",
        )


def monthlyInstalment(premium, months=12):
    """Calculate the monthly instalment."""
    if months == 0:
        return premium

    return math.floor(premium / months)


def isAuthorised(token):
    """Check whether a token matches the configured token."""
    return bool(UNDERWRITER_TOKEN) and token == UNDERWRITER_TOKEN


def renewalDue(start, years=1):
    """Calculate the renewal date."""
    date = datetime.strptime(start, "%Y-%m-%d")
    return date.replace(year=date.year + years).strftime("%Y-%m-%d")


def printQuotes():
    """Print all saved quotes."""
    print("===== Quote Book =====")

    for index, (number, quote) in enumerate(quotes.items(), start=1):
        print(
            index,
            number,
            quote["name"],
            "Rs.",
            quote["premium"],
        )


def main():
    """Run example calculations and print the results."""
    p1 = calculatePremium("health", 30, 500000, False, 0)
    p2 = calculatePremium("health", 30, 500000, False, 0)
    p3 = calculatePremium("motor", 50, 800000, False, 0)
    p4 = calculatePremium(
        "life", 25, 100000, False, 0, [3000, 3000, 3000]
    )

    print("Quote 1:", p1)
    print("Quote 2 (same customer details):", p2)
    print("Non-smoker aged 50:", p3)
    print("Life with stacked discounts:", p4)
    print("Age from DOB 31-12-1990:", ageFromDob("31-12-1990"))
    print("Monthly instalment:", monthlyInstalment(p3))
    print("Renewal due:", renewalDue("2025-03-15"))

    sample_xml = (
        "<policies>"
        "<policy type='health' age='40' sum='300000'/>"
        "<policy type='motor' age='abc' sum='1'/>"
        "</policies>"
    )
    print("Imported:", importPolicies(sample_xml))
    print("Saved as:", saveQuote("Kiran", p1))
    print("Authorised:", isAuthorised(UNDERWRITER_TOKEN))
    print("Server would listen on", HOST)
    printQuotes()


if __name__ == "__main__":
    main()
