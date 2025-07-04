import asyncio
import time
from engine.scraper.vendors.pickles_scraper import scrape_pickles
from engine.scraper.vendors.manheim_scraper import scrape_manheim
from engine.scraper.vendors.ebay_scraper import scrape_ebay
from engine.scraper.common_utils import write

# Toggle scrapers on/off here
ENABLED_VENDORS = {
    "pickles": True,
    "manheim": True,
    "ebay": True,
    "gumtree": False,
    "bikesales": False
}

async def run_scraper(name, scrape_func):
    write(f"[ {name.upper()} ] Starting scraper", style="info")
    start_time = time.time()
    try:
        listings = await asyncio.to_thread(scrape_func)
        duration = time.time() - start_time
        write(f"[ {name.upper()} ] Collected {len(listings)} listings in {duration:.2f}s", style="success")
    except Exception as e:
        write(f"[ {name.upper()} ] ERROR: {e}", style="error")

def get_enabled_scrapers():
    scrapers = []
    if ENABLED_VENDORS["pickles"]:
        scrapers.append(("pickles", scrape_pickles))
    if ENABLED_VENDORS["manheim"]:
        scrapers.append(("manheim", scrape_manheim))
    if ENABLED_VENDORS["ebay"]:
        scrapers.append(("ebay", scrape_ebay))
    # Gumtree and Bikesales can be added when stable
    return scrapers

async def main():
    write("RideRadar Parallel Scraper Runner", style="header")
    write("---------------------------------", style="header")

    scrapers = get_enabled_scrapers()
    write(f"Preparing to run {len(scrapers)} vendor scrapers concurrently\n", style="info")

    tasks = [run_scraper(name, func) for name, func in scrapers]

    await asyncio.gather(*tasks)

    write("\nAll enabled vendor scrapes completed.", style="success")

if __name__ == "__main__":
    asyncio.run(main())