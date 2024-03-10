import discord
from discord import app_commands
import vendor_storage
import webhook_handler
import asyncio

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Define your slash command
@tree.command(
    name="search",
    description="Search for a vehicles on various salvage vendors",
    guild=discord.Object(id="1013725487476002897")
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
    guild=discord.Object(id="1013725487476002897")
)
async def calculate_command(interaction: discord.Interaction, amount: float):
    try:
        # Send a message asking for the auction house choice
        message = await interaction.response.send_message(content="Please select an auction house for the calculation: Manheim or Pickles")

        # Define the check function for wait_for
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        # Wait for the user's response
        response_msg = await client.wait_for('message', timeout=60.0, check=check)

        # Process the user's response
        if response_msg.content.lower() == 'manheim':
            total = calculate_manheim(amount)
            response = f"Total amount for Manheim: ${total}"
        elif response_msg.content.lower() == 'pickles':
            total = calculate_pickles(amount)
            response = f"Total amount for Pickles: ${total}"
        else:
            response = "Invalid choice."

        # Send the response to the original interaction
        await interaction.followup.send(response)

    except asyncio.TimeoutError:
        await interaction.followup.send("You took too long to respond.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")



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
    await tree.sync(guild=discord.Object(id="1013725487476002897"))
    print("Ready!")

# Run the bot
client.run('MTIxNTk4MjM2MDk5OTM2Mjc0Mg.GUoHa9.s3y5gx8OJ-vfApUe2S5FmIVvO0q06o9ymCdFOc')
