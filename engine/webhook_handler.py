import discord
from discord import Webhook
import aiohttp
import json
from src_scraper import search_by, request
import asyncio
from colorama import init, Fore, Style
import time
from vendor_storage import manheim, pickles
from utils import *

init()

# Define the file to save the data
DATA_FILE = 'vehicles_data.json'

async def retrieve_and_send(url, previous_data, vehicle_make):
    # Retrieve data for vehicles
    if ' ' in vehicle_make:
        # Assume it's a specific search query
        search = search_by.specific(vehicle_make)
        current_data = await search.search_by_specific()  # Call the correct method here
    else:
        # Assume it's a search by brand
        search = search_by.vehicle_brand(vehicle_make)
        current_data = await search.search_by_brand()  # Call the correct method here

    # Save the current data to the file with indentation and separators
    with open(DATA_FILE, 'a') as file:
        json.dump(current_data, file, indent=4, separators=(',', ': '))



    # Compare current data with previous data
    new_data = [vehicle for vehicle in current_data if vehicle not in previous_data]

    if new_data:
        write.console("green", "\nWebhooking new embeds...")
        for vehicle in new_data:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(url, session=session)
                # Try new embed else run old embed
                try:
                    embed = discord.Embed(
                        title=vehicle["title"],
                        url=vehicle["link"],
                        description=f"{vehicle['subtitle']}",
                        color=0x00ff00
                    )
                    if vehicle["vendor"] == "Manheim":
                        embed.set_author(name=manheim["Name"], url=manheim["Url"], icon_url=manheim["Logo"])
                    elif vehicle["vendor"] == "Pickles":
                        embed.set_author(name=pickles["Name"], url=pickles["Url"], icon_url=pickles["Logo"])
                    embed.set_image(url=vehicle["img"])
                    embed.set_footer(text="If there's no image, I'm bandwidth restricted!")
                    embed.add_field(name="📍 Location", value=f"{vehicle['location']}")
                    embed.add_field(name="💼 Vendor", value=f"{vehicle['vendor']}")
                    embed.add_field(name="📋 WOVR", value=f"{vehicle['wovr']}")
                    embed.add_field(name="🔢 Cylinder", value=f"{vehicle['cylinder']}")
                    embed.add_field(name="⚙️ Gearbox", value=f"{vehicle['gearbox']}  ")
                    embed.add_field(name="⏱️ Odometer", value=f"{vehicle['odometer']}")
                    embed.add_field(name="🕒 Time of Auction", value=f"{vehicle['date']}")
                
                except:
                    embed = discord.Embed(
                        title=vehicle["title"],
                        url=vehicle["link"],
                        description=f"Newly added vehicle to **{vehicle['vendor']}!**",
                        color=0x00ff00
                    )
                    if vehicle["vendor"] == "Manheim":
                        embed.set_author(name=manheim["Name"], url=manheim["Url"], icon_url=manheim["Logo"])
                    elif vehicle["vendor"] == "Pickles":
                        embed.set_author(name=pickles["Name"], url=pickles["Url"], icon_url=pickles["Logo"])
                    embed.set_image(url=vehicle["img"])
                    embed.set_footer(text="If there's no image, I'm bandwidth restricted!")


                await webhook.send(embed=embed, username="Captain Hook")
        write.console("green", "New embeds sent.")
        return True
    else:
        print(f"{Fore.GREEN}")
        write.console("yellow", "No new data found.")
        write.console("yellow", "No embeds sent.")
        return False
    

async def run(vehicle_make):
    url = "https://discord.com/api/webhooks/1215992538704379995/FDhwehNxKhlMgmXJDWNCc-w7N8ObauV2ei2fOLUdQlP7IucvIBwMyrW6wUREPIwXaJT4"

    # Load previous data from the file if available
    try:
        with open(DATA_FILE, 'r') as file:
            try:
                previous_data = json.load(file)
            except json.JSONDecodeError:
                # Handle invalid JSON data or empty file
                previous_data = []
    except FileNotFoundError:
        # If the file doesn't exist, initialize previous data as an empty list
        previous_data = []

    result = await retrieve_and_send(url, previous_data, vehicle_make)
    return result


if __name__ == "__main__":
    asyncio.run(run("Porsche"))