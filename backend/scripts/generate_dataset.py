"""Generate a deterministic 100,000-row search-query dataset.

The vocabulary contains generic commerce, learning, travel, media, and technology
terms. Counts follow a Zipf-like popularity curve, which resembles real search logs.
"""

from __future__ import annotations

import csv
import random
from itertools import product
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "queries.csv"
TARGET_SIZE = 100_000

FEATURED = [
    ("iphone", 1_000_000),
    ("iphone 15", 850_000),
    ("iphone charger", 600_000),
    ("iphone 15 pro max", 550_000),
    ("iphone case", 510_000),
    ("iphone 16", 500_000),
    ("iphone 16 pro", 485_000),
    ("iphone price", 470_000),
    ("iphone cover", 455_000),
    ("iphone screen protector", 440_000),
    ("iphone wireless charger", 425_000),
    ("java tutorial", 400_000),
    ("java interview questions", 395_000),
    ("java course", 390_000),
    ("java programming", 385_000),
    ("java download", 380_000),
    ("java compiler", 375_000),
    ("java projects", 370_000),
    ("java roadmap", 365_000),
    ("java spring boot", 360_000),
    ("java documentation", 355_000),
    ("python tutorial", 390_000),
    ("python course", 385_000),
    ("python download", 380_000),
    ("python interview questions", 375_000),
    ("python projects", 370_000),
    ("python programming", 365_000),
    ("python compiler", 360_000),
    ("python for beginners", 355_000),
    ("python data science", 350_000),
    ("python documentation", 345_000),
    ("running shoes", 380_000),
    ("machine learning course", 370_000),
    ("wireless headphones", 360_000),
]

QUALIFIERS = [
    "best",
    "affordable",
    "premium",
    "latest",
    "popular",
    "top rated",
    "lightweight",
    "professional",
    "beginner",
    "advanced",
    "compact",
    "wireless",
    "smart",
    "durable",
    "eco friendly",
    "fast",
    "portable",
    "modern",
    "classic",
    "minimal",
    "complete",
    "practical",
    "essential",
    "recommended",
    "new",
    "refurbished",
    "budget",
    "luxury",
    "high performance",
    "open source",
    "cloud",
    "secure",
    "automatic",
    "custom",
    "everyday",
    "waterproof",
    "ergonomic",
    "energy efficient",
    "limited edition",
    "pro",
]

SUBJECTS = [
    "phone",
    "laptop",
    "tablet",
    "monitor",
    "keyboard",
    "mouse",
    "headphones",
    "speaker",
    "camera",
    "smartwatch",
    "charger",
    "backpack",
    "running shoes",
    "office chair",
    "desk",
    "coffee maker",
    "air purifier",
    "vacuum cleaner",
    "refrigerator",
    "washing machine",
    "python course",
    "java course",
    "system design",
    "data science",
    "machine learning",
    "web development",
    "mobile development",
    "cyber security",
    "cloud computing",
    "devops",
    "database tutorial",
    "interview questions",
    "resume template",
    "project ideas",
    "books",
    "movies",
    "music",
    "podcasts",
    "news",
    "weather",
    "flights",
    "hotels",
    "restaurants",
    "fitness plan",
    "healthy recipes",
    "meditation app",
    "language lessons",
    "online degree",
    "stock market",
    "personal finance",
    "home decor",
    "gaming console",
    "graphics card",
]

CONTEXTS = [
    "for students",
    "for developers",
    "for designers",
    "for remote work",
    "for travel",
    "for home",
    "for office",
    "for gaming",
    "for beginners",
    "for professionals",
    "under 100",
    "under 500",
    "under 1000",
    "near me",
    "online",
    "with certification",
    "2026",
    "comparison",
    "reviews",
    "price",
    "deals",
    "guide",
    "tutorial",
    "examples",
    "download",
    "setup",
    "tips",
    "ideas",
    "alternatives",
    "features",
    "performance test",
    "india",
    "delhi",
    "mumbai",
    "bangalore",
    "weekend",
    "today",
    "this month",
    "free",
    "subscription",
    "for small business",
    "for teams",
    "for creators",
    "for kids",
    "for adults",
    "with warranty",
    "same day delivery",
    "open now",
    "step by step",
]


def generate() -> list[tuple[str, int]]:
    random.seed(2028)
    rows = list(FEATURED)
    seen = {query for query, _count in rows}
    rank = len(rows) + 1
    for qualifier, subject, context in product(QUALIFIERS, SUBJECTS, CONTEXTS):
        query = f"{qualifier} {subject} {context}"
        if query in seen:
            continue
        count = max(5, int(900_000 / (rank**0.63)) + random.randint(0, 80))
        rows.append((query, count))
        seen.add(query)
        rank += 1
        if len(rows) == TARGET_SIZE:
            break
    if len(rows) != TARGET_SIZE:
        raise RuntimeError(f"Expected {TARGET_SIZE} rows, generated {len(rows)}")
    return rows


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = generate()
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["query", "count"])
        writer.writerows(rows)
    print(f"Generated {len(rows):,} unique queries at {OUTPUT}")


if __name__ == "__main__":
    main()
