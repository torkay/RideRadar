from .vendors.pickles_scraper import scrape_pickles
from .vendors.manheim_scraper import scrape_manheim
from .vendors.gumtree_scraper import scrape_gumtree

def run_all_scrapers(make):
    all_listings = []

    print(f"\nScraping for {make} across all vendors...\n")
    all_listings.extend(scrape_pickles(make))
    all_listings.extend(scrape_manheim(make))
    all_listings.extend(scrape_gumtree(make))

    print(f"\nScraped total {len(all_listings)} listings.\n")
    return all_listings