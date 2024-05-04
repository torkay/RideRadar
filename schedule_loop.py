import webhook_handler
import configparser
import asyncio
import time
import os

def set_cmd_title(title):
    os.system(f"title {title}")

async def process_vehicles(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            vehicle_make = line.strip()  # Remove leading/trailing whitespaces and newlines
            await webhook_handler.run(vehicle_make)

async def run_handler():
    file_path = 'vehicles.txt'
    os.system(f"title RideRadar: Scheduler (DO NOT CLOSE)")
    await process_vehicles(file_path)
    
async def main():
    
    # Infinite loop to run the scheduler
    while True:
        await run_handler()
        print("Awaiting schedule...")
        await asyncio.sleep(((60)*60)*3)  # Check three hour
        current_time = time.localtime()
        formatted_time = time.strftime("%I:%M%p %m/%d/%y", current_time)
        print(f"Initiating search on {formatted_time}")

if __name__ == "__main__":
    set_cmd_title("Warning - Do Not Close")
    asyncio.run(main())