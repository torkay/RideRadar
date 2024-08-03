import webhook_handler
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
    ''' Future scale TODO: on rate request limit acquire iterable ip addresses or variable sleep timer '''
    
    # Infinite loop to run the scheduler
    while True:
        start_time = time.time()
        await run_handler()
        end_time = time.time()

        elapsed_time = end_time - start_time
        formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))

        next_run_time = time.time() + (1 * 0 * 1)  # 3 hours from now
        formatted_next_run_time = time.strftime("%I:%M%p %m/%d/%y", time.localtime(next_run_time))
        write.line(space=True, override=True)
        write.console("white", f"Worker completed search | Time elapsed: {formatted_elapsed_time} | Waiting until {formatted_next_run_time}")
        write.line(override=True)
        await asyncio.sleep(((1)*1)*1)  # Wait 12 hours before the next run
        write.console('white', f"Started RideRadar server instance: version {version}")


def run_scheduler():
    if find.server_os() == 'windows':
        set_cmd_title("Warning - Do Not Close")
    write.line(space=True, override=True)
    write.console('white', f"Started RideRadar server instance: version {version}")
    write.line(override=True)
    asyncio.run(main())

if __name__ == "__main__":
    run_scheduler()
    
