from vendor_storage import manheim, pickles
from utils import *
import src_scraper as src
import asyncio

async def test():
    search = src.search_by.specific("Mercedes C63")
    request = await search.search_pickles()
    print(request)

if __name__ == "__main__":
    asyncio.run(test())
