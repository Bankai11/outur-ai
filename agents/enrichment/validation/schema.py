from typing import Any

# Standardized Industry Names
STANDARD_INDUSTRIES = [
    "Software Development",
    "Information Technology",
    "Financial Services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Education",
    "Real Estate",
    "Consulting",
    "Marketing",
    "Unknown"
]

# Standardized Funding Stages
STANDARD_FUNDING_STAGES = [
    "Pre-Seed",
    "Seed",
    "Series A",
    "Series B",
    "Series C",
    "Series D+",
    "Public",
    "Bootstrapped",
    "Acquired",
    "Unknown"
]

def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    if not url:
        return False
    return url.startswith("http://") or url.startswith("https://")

def is_valid_linkedin(url: str) -> bool:
    """Basic LinkedIn URL validation."""
    if not url:
        return False
    return "linkedin.com/in/" in url or "linkedin.com/company/" in url
