from vendor_storage import manheim, pickles
import webhook_handler
from utils import *
import src_scraper as src
import asyncio

async def test():
    search = src.search_by.vehicle_brand("BMW")
    result = await search.search_gumtree()
    print(result)
    

if __name__ == "__main__":
    asyncio.run(test())
