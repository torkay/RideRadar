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
    ''' Future scale TODO: on rate request limit acquire iteratable ip addresses or variable sleep timer '''
    
    # Infinite loop to run the scheduler
    while True:
        await run_handler()
        print("Awaiting schedule...")
        await asyncio.sleep(((60)*60)*3)  # Check three hour
        current_time = time.localtime()
        formatted_time = time.strftime("%I:%M%p %m/%d/%y", current_time)
        print(f"Initiating search on {formatted_time}")

if __name__ == "__main__":
    if find.server_os() == 'windows':
        set_cmd_title("Warning - Do Not Close")
    write.line(space=True, override=True)
    write.console('white', f"Started RideRadar server instance: version {version}")
    write.line(override=True)
    asyncio.run(main())