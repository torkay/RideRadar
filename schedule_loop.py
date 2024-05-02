import webhook_handler
import asyncio
import time
import os

def set_cmd_title(title):
    os.system(f"title {title}")

async def run_handler():
    # Main
    await webhook_handler.run("Porsche")

    # Edge case
    await webhook_handler.run("Ferrari")
    await webhook_handler.run("Aston Martin")
    await webhook_handler.run("Maserati")
    await webhook_handler.run("Lamborghini")
    await webhook_handler.run("Lotus")
    await webhook_handler.run("Mclaren")
    
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