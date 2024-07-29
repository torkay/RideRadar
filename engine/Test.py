from vendor_storage import manheim, pickles
import webhook_handler
from utils import *
import src_scraper as src
import asyncio

async def test():
    search = src.search_by.specific("BMW M3")
    request = await search.search_pickles()
    for vehicle in request:
        await webhook_handler.run(vehicle)

if __name__ == "__main__":
    asyncio.run(test())
