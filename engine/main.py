from scraper import MongoDBHandler, mass

def main():
    # Initialize MongoDB handler
    db_handler = MongoDBHandler(
        db_name='vehicle_database', 
        collection_name='vehicles'
    )

    # Initialize web scraper
    web_scraper = mass(specific_search=None)  # Replace None with specific search term if needed

    # Define functions for each vendor
    async def scrape_manheim():
        manheim_scraper = web_scraper.manheim(web_scraper)
        await manheim_scraper.assign()
        # Assuming you have a method to get data from manheim_scraper
        data = manheim_scraper.get_data()
        db_handler.insert_data(data)

    async def scrape_pickles():
        pickles_scraper = web_scraper.pickles(web_scraper)
        await pickles_scraper.assign()
        # Assuming you have a method to get data from pickles_scraper
        data = pickles_scraper.get_data()
        db_handler.insert_data(data)

    # Run the scraping tasks
    async def run_scrapers():
        await scrape_manheim()
        await scrape_pickles()

    # Run the async function
    import asyncio
    asyncio.run(run_scrapers())

if __name__ == "__main__":
    main()
