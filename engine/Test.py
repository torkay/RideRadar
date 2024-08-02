import asyncio
from src_scraper import mass

async def test():
    # Create an instance of the mass.scrape class
    worker = mass.scrape()

    # Create an instance of the pickles class, passing the worker instance
    pickles_worker = mass.scrape.pickles(worker)
    
    # Run the async method
    await pickles_worker.assign()
    print("done")
    
if __name__ == "__main__":
    asyncio.run(test())

'''
https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=1&RecordsPerPage=120&searchType=P&page=1
https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=2&RecordsPerPage=120&searchType=P&page=2

https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=5&RecordsPerPage=120&searchType=P&

Next page button
//*[@id="result-Container"]/nav[2]/div/div[2]/div[2]/ul/li[8]/a
//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[9]/a
//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[9]/a
//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[10]/a
//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[11]/a
href="/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=6&RecordsPerPage=120&searchType=P&page=1"
//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[11]/a
href="/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=7&RecordsPerPage=120&searchType=P&page=1"
'''