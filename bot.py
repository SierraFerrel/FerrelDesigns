
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

PURPLE = 0x7B3FF2
BLUE = 0x3B82F6
SILVER = 0xC0C4CC

WELCOME_CHANNEL_ID = 1558404692466335807

print("FERREL DESIGNS UPDATED CODE IS LOADING")


class FerrelDesignsBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(QuotePanelView())

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
intents.members = True

bot = FerrelDesignsBot(
    command_prefix="!",
    intents=intents
)


class QuotePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Request a Quote",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="ferrel_quote_request"
    )
   
    async def request_quote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild
        member = interaction.user

        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "Please use this button inside the Ferrel Designs server.",
                ephemeral=True
            )
            return

        # Check whether this member already has an open inquiry.
        existing = discord.utils.get(
            guild.text_channels,
            topic=f"ferrel_quote_user:{member.id}"
        )

        if existing:
            await interaction.response.send_message(
                f"You already have an open inquiry: {existing.mention}",
                ephemeral=True
            )
            return

        # Set up private channel permissions.
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        bot_member = guild.me
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

        # Let server administrators access the inquiry.
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:
            channel = await guild.create_text_channel(
                name=f"quote-{member.name}".lower()[:90],
                topic=f"ferrel_quote_user:{member.id}",
                overwrites=overwrites,
                reason=f"Quote inquiry opened by {member}"
            )

            embed = make_embed(
                "Your Project Inquiry 💜💙",
                (
                    f"Welcome, {member.mention}! Thanks for reaching out.\n\n"
                    "**1. Community:** What is your server for?\n"
                    "**2. Current setup:** Is this a new or existing server?\n"
                    "**3. Features:** What roles, channels, bots, applications, "
                    "tickets, or workflows do you need?\n"
                    "**4. Style:** What branding, colors, or examples do you like?\n"
                    "**5. Budget:** Which package or budget range are you considering?\n"
                    "**6. Timeline:** When would you like the project completed?\n\n"
                    "You can answer in one message or respond to each question "
                    "at your own pace. I'll review your needs and discuss the "
                    "price and timeline before any work begins.\n\n"
                    "🔒 **Never share passwords, bot tokens, or login credentials.**"
                ),
                PURPLE
            )

            await channel.send(embed=embed)

            await interaction.followup.send(
                f"Your private inquiry is ready: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't create your inquiry channel. Please check "
                "the bot's channel permissions and try again.",
                ephemeral=True
            )

        except Exception as error:
            print(
                f"Quote channel creation failed: "
                f"{type(error).__name__}: {error}"
            )
            await interaction.followup.send(
                "Something went wrong while creating your inquiry. "
                "Please try again later.",
                ephemeral=True
            )


@bot.event
async def on_ready():
    print(f"Ferrel Designs bot is online as {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        print(
            f"Welcome channel {WELCOME_CHANNEL_ID} "
            f"was not found in {member.guild.name}."
        )
        return

    embed = make_embed(
        "Welcome to Ferrel Designs 💜💙",
        (
            f"Welcome to Ferrel Designs, {member.mention}!\n\n"
            "Your community deserves a Discord server "
            "that looks great and works well.\n\n"
            "I'm here to help you build an organized, ready-to-use "
            "Discord server tailored to your community's needs. "
            "From roles and permissions to bots, automation, and branding, "
            "I want to make managing your community easier.\n\n"
            "**Explore my services:**\n"
            "🛠️ See what I offer\n"
            "💰 Review my pricing\n"
            "📝 Request a project quote\n\n"
            "I'm excited to hear about your project and help bring "
            "your vision to life!"
        ),
        PURPLE
    )

    await channel.send(
        content=f"Welcome, {member.mention}! 💜",
        embed=embed
    )

    print(
        f"Sent welcome message for {member} "
        f"in #{channel.name}."
    )


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
    name="post-quote-panel",
    description="Post the Ferrel Designs quote request panel."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_quote_panel(interaction: discord.Interaction):
    embed = make_embed(
        "Let's Build Your Community 💜💙",
        (
            "Ready to give your Discord community a better setup?\n\n"
            "Click the button below to open a private inquiry with me. "
            "I'll learn about your project, discuss the features you need, "
            "and provide a quote before any work begins.\n\n"
            "**What to have ready:**\n"
            "• Your community's purpose and vision\n"
            "• Features and workflows you want\n"
            "• Your preferred budget and timeline\n\n"
            "Submitting an inquiry does not commit you to a purchase."
        ),
        PURPLE
    )

    await interaction.response.send_message(
        embed=embed,
        view=QuotePanelView()
    )


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
            "that looks great and works well.\n\n"
            "I'm here to help you build an organized, ready-to-use "
            "Discord server tailored to your community's needs. "
            "From roles and permissions to bots, automation, and branding, "
            "I want to make managing your community easier.\n\n"
            "**Explore my services:**\n"
            "🛠️ See what I offer\n"
            "💰 Review my pricing\n"
            "📝 Request a project quote\n\n"
            "I'm excited to hear about your project and help bring "
            "your vision to life!"
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
