
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load local environment variables when running on your computer.
# Render will provide its own environment variables later.
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Ferrel Designs bot is online as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Could not sync slash commands: {error}")


@bot.tree.command(
    name="ping",
    description="Check whether the Ferrel Designs bot is online."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Ferrel Designs is online and ready! 💜💙",
        ephemeral=True
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Set it in your environment."
        )

    bot.run(TOKEN)
