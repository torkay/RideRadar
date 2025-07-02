from .vendors.pickles_scraper import scrape_pickles
from .vendors.manheim_scraper import scrape_manheim
from .vendors.gumtree_scraper import scrape_gumtree
import json
from pathlib import Path

def run_all_scrapers(make):
    all_listings = []

    print(f"\nScraping for {make} across all vendors...\n")
    all_listings.extend(scrape_pickles(make))
    all_listings.extend(scrape_manheim(make))
    all_listings.extend(scrape_gumtree(make))

    print(f"\nScraped total {len(all_listings)} listings.\n")

    filtered = process_listings(all_listings)
    existing = load_existing_listings()
    sold = detect_sold_listings(existing, filtered)

    save_to_datastore(filtered)

    if sold:
        print(f"Detected {len(sold)} sold/removed listings:")
        for item in sold:
            print(f"- {item.get('title')} ({item.get('link')})")

    return filtered

def run_full_scrape():
    all_listings = []

    print("\nPerforming FULL vendor scrapes...\n")
    all_listings.extend(scrape_gumtree())
    #all_listings.extend(scrape_pickles(make=None))
    #all_listings.extend(scrape_manheim(make=None))

    print(f"\nScraped total {len(all_listings)} listings.\n")

    filtered = process_listings(all_listings)
    existing = load_existing_listings()
    sold = detect_sold_listings(existing, filtered)

    save_to_datastore(filtered)

    if sold:
        print(f"Detected {len(sold)} sold/removed listings:")
        for item in sold:
            print(f"- {item.get('title')} ({item.get('link')})")

    return filtered

def process_listings(listings):
    seen = set()
    unique = []

    for listing in listings:
        key = listing.get("link")
        if key and key not in seen:
            seen.add(key)
            unique.append(listing)

    print(f"Filtered down to {len(unique)} unique listings.")
    return unique

def load_existing_listings():
    DATA_PATH = Path(__file__).resolve().parent.parent / "storage" / "vehicles_data.json"
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def detect_sold_listings(existing, current):
    current_links = {item.get("link") for item in current}
    sold = [item for item in existing if item.get("link") not in current_links]
    return sold

def save_to_datastore(listings):
    DATA_PATH = Path(__file__).resolve().parent.parent / "storage" / "vehicles_data.json"
    with open(DATA_PATH, "w") as f:
        json.dump(listings, f, indent=4)
    print(f"Saved {len(listings)} listings to datastore.")

def manual_scraper_runner():
    print("\nRideRadar Manual Scraper Runner")
    print("-----------------------------")
    print("1. Targeted search (single make)")
    print("2. Full vendor scrape")
    choice = input("Select option [1/2]: ").strip()

    if choice == "1":
        make = input("Enter vehicle make to scrape: ").strip()
        if not make:
            print("No make entered. Exiting.")
            return
        results = run_all_scrapers(make)
    elif choice == "2":
        results = run_full_scrape()
    else:
        print("Invalid choice. Exiting.")
        return

    print(f"\n{len(results)} listings collected and stored.\n")

if __name__ == "__main__":
    manual_scraper_runner()
