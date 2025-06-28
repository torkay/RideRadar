import RideRadar.engine.integrations.webhook_handler as webhook_handler
import configparser
import asyncio
import time
import os
from utils import find, write, version

def set_cmd_title(title):
    os.system(f"title {title}")

async def process_vehicles(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            vehicle_make = line.strip()  # Remove leading/trailing whitespaces and newlines
            await webhook_handler.run(vehicle_make)

async def run_handler():
    file_path = find.vehicle_text()
    if find.server_os() == 'windows':
        os.system(f"title RideRadar: Scheduler (DO NOT CLOSE)")
    await process_vehicles(file_path)

async def main():
    ''' Run the handler once without looping '''
    
    start_time = time.time()
    await run_handler()
    end_time = time.time()

    elapsed_time = end_time - start_time
    formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    
    write.line(space=True, override=True)
    write.console("white", f"Worker completed search | Time elapsed: {formatted_elapsed_time}")
    write.line(override=True)

def run_scheduler():
    if find.server_os() == 'windows':
        set_cmd_title("Warning - Do Not Close")
    write.line(space=True, override=True)
    write.console('white', f"Started RideRadar server instance: version {version}")
    write.line(override=True)
    asyncio.run(main())

if __name__ == "__main__":
    run_scheduler()
