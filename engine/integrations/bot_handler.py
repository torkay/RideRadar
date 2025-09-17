import os
import discord
from discord import app_commands
import RideRadar.engine.storage.vendor_storage as vendor_storage
import RideRadar.engine.integrations.webhook_handler as webhook_handler
import asyncio
from RideRadar.engine.integrations.bid_watcher import watch

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Optional: limit commands to a single guild if provided
_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
GUILD_OBJ = discord.Object(id=int(_GUILD_ID)) if _GUILD_ID and _GUILD_ID.isdigit() else None

# Define your slash command
@tree.command(
    name="search",
    description="Search for a vehicles on various salvage vendors",
    guild=GUILD_OBJ,
)
async def search_command(interaction: discord.Interaction, vehicle: str):
    # Send a message to acknowledge the user's command
    await interaction.response.send_message("I'm searching for the requested vehicle. Please wait...")

    try:
        # Start the scraping process asynchronously with a timeout of 60 seconds
        search_task = asyncio.wait_for(webhook_handler.run(vehicle), timeout=480)

        # Wait for the scraping process to complete
        result = await search_task

        # Process the result and send the search results
        if result:
            embed = discord.Embed(title="Success! 🥳", description=f"I searched for {vehicle} and yielded the results above", color=discord.Color.blue())
            embed.set_footer(text="Save time, scrape the web")
        else:
            embed = discord.Embed(title="You're all up to date! 🥳", description=f"I searched for {vehicle} and yielded no new results", color=discord.Color.blue())
            embed.set_footer(text="Save time, scrape the web")

        # Send the search results
        await interaction.followup.send(embed=embed)

    except asyncio.TimeoutError:
        # Handle timeout error
        await interaction.followup.send("Sorry, the search took too long. Please try again later.")

    except Exception as e:
        # Handle other exceptions
        print(f"An error occurred during search: {e}")
        await interaction.followup.send("An error occurred during the search. Please try again later.")

@tree.command(
    name="calculate",
    description="Add all fixed and variable fees onto an amount of money",
    guild=GUILD_OBJ,
)
async def calculate_command(interaction: discord.Interaction, amount: float):
    # Process the user's response
    total1 = calculate_manheim(amount)
    total2 = calculate_pickles(amount)
    response = f"""Total amount sum is:
`Manheim` ${total1}
`Pickles` ${total2}"""

    # Send the response to the original interaction
    await interaction.response.send_message(response)

@tree.command(
    name="watchlist",
    description="Add a listing to the watchlist",
    guild=GUILD_OBJ,
)
async def watchlist_command(interaction: discord.Interaction, listing_url: str):
    # Add the listing URL to the watchlist
    await watch.bid(listing_url)
    await interaction.response.send_message("Listing added to watchlist.")

# Function to calculate the total amount for Manheim
def calculate_manheim(amount):
    if amount < 201:
        total = amount + 33
    elif amount < 1001:
        total = amount + 60.01
    else:
        total = amount + 13.45
    total += 77  # Administration fee
    return total

# Function to calculate the total amount for Pickles
def calculate_pickles(amount):
    total = amount + 150  # Fixed fee for Pickles
    return total

# Sync commands to Discord when the client is ready
@client.event
async def on_ready():
    if GUILD_OBJ is not None:
        await tree.sync(guild=GUILD_OBJ)
    else:
        await tree.sync()
    print("Ready!")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("DISCORD_BOT_TOKEN not set; bot will not start.")
    else:
        client.run(token)
