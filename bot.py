
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

PURPLE = 0x7B3FF2
BLUE = 0x3B82F6
SILVER = 0xC0C4CC

print("FERREL DESIGNS UPDATED CODE IS LOADING")

class FerrelDesignsBot(commands.Bot):
    async def setup_hook(self):
        print("Starting Ferrel Designs command synchronization...")

        try:
            synced = await self.tree.sync()
            print(f"SUCCESS: Synced {len(synced)} global slash commands.")

            for command in synced:
                print(f"Registered command: /{command.name}")

        except Exception as error:
            print(
                f"COMMAND SYNC FAILED: "
                f"{type(error).__name__}: {error}"
            )
            raise


intents = discord.Intents.default()

bot = FerrelDesignsBot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Ferrel Designs bot is online as {bot.user}")


def make_embed(title, description, color):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(
        text="Ferrel Designs | Designed for your community. Built to work."
    )
    return embed


@bot.tree.command(
    name="ping",
    description="Check whether the Ferrel Designs bot is online."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Ferrel Designs is online and ready! 💜💙",
        ephemeral=True
    )


@bot.tree.command(
    name="post-welcome",
    description="Post the Ferrel Designs welcome embed."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_welcome(interaction: discord.Interaction):
    embed = make_embed(
        "Welcome to Ferrel Designs 💜💙",
        (
            "Your community deserves a Discord server "
            "that looks good and works well.\n\n"
            "We design organized, ready-to-use Discord communities "
            "with thoughtful roles, permissions, workflows, and branding.\n\n"
            "**Explore the server:**\n"
            "🛠️ Check out our services\n"
            "💰 Review our pricing\n"
            "📝 Request a project quote\n\n"
            "Designed for your community. Built to work."
        ),
        PURPLE
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="post-services",
    description="Post the Ferrel Designs services embed."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_services(interaction: discord.Interaction):
    embed = make_embed(
        "Our Services 🛠️",
        (
            "**Discord Server Builds**\n"
            "Categories, channels, roles, permissions, and organization.\n\n"
            "**Bots & Automation**\n"
            "Bot configuration, onboarding, applications, tickets, and workflows.\n\n"
            "**Visual Organization**\n"
            "Coordinated embeds, channel layouts, and a consistent community identity.\n\n"
            "**Community Workflows**\n"
            "Staff structures, departments, rules, and practical documentation.\n\n"
            "Every project is scoped to your needs. Ongoing server management "
            "is not included in standard builds."
        ),
        BLUE
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="post-pricing",
    description="Post the Ferrel Designs pricing embed."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_pricing(interaction: discord.Interaction):
    embed = make_embed(
        "Packages & Pricing 💰",
        (
            "**Foundation — $40**\n"
            "A clean server structure, basic roles and permissions, "
            "and one revision round.\n\n"
            "**Professional — $75**\n"
            "Advanced role structures, up to three bot configurations, "
            "one application workflow, one ticket workflow, and two revision rounds.\n\n"
            "**Custom — Starting at $100**\n"
            "For more complex servers, additional workflows, automation, "
            "and documentation. Final pricing depends on project scope.\n\n"
            "**Before we begin**\n"
            "Every project starts with an inquiry so we can confirm "
            "your requirements, price, and timeline.\n\n"
            "Ongoing management and new features after handoff "
            "are quoted separately."
        ),
        PURPLE
    )
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Set it in your environment."
        )

    bot.run(TOKEN)
