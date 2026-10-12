
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
NEW_INQUIRIES_CHANNEL_ID = 1558704116581273722
COMPLETED_WORK_CHANNEL_ID = 1558704266363932682

print("FERREL DESIGNS UPDATED CODE IS LOADING")



async def close_inquiry_channel(
    channel: discord.TextChannel,
    actor: discord.Member
) -> bool:
    guild = channel.guild
    prefix = "ferrel_quote_user:"

    if not channel.topic or not channel.topic.startswith(prefix):
        await actor.send(
            "This isn't an active Ferrel Designs inquiry."
        )
        return False

    try:
        client_id = int(channel.topic[len(prefix):])
    except ValueError:
        await actor.send("I couldn't identify the inquiry owner.")
        return False

    if (
        actor.id != client_id
        and not actor.guild_permissions.administrator
    ):
        await actor.send(
            "Only the client who opened this inquiry or a server "
            "administrator can close it."
        )
        return False

    client = guild.get_member(client_id)

    if client is None:
        try:
            client = await guild.fetch_member(client_id)
        except discord.NotFound:
            client = None

    try:
        # Collect the full conversation before changing the channel.
        transcript_lines = [
            f"Ferrel Designs Inquiry Transcript",
            f"Channel: #{channel.name}",
            f"Client ID: {client_id}",
            f"Closed by: {actor} ({actor.id})",
            f"Transcript generated: {discord.utils.utcnow().isoformat()}",
            "=" * 70,
            ""
        ]

        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            transcript_lines.append(
                f"[{timestamp}] {message.author} ({message.author.id})"
            )

            if message.content:
                transcript_lines.append(message.content)

            for embed in message.embeds:
                if embed.title:
                    transcript_lines.append(f"Embed title: {embed.title}")
                if embed.description:
                    transcript_lines.append(
                        f"Embed description: {embed.description}"
                    )

            for attachment in message.attachments:
                transcript_lines.append(
                    f"Attachment: {attachment.filename} — {attachment.url}"
                )

            transcript_lines.append("")

        transcript_text = "\n".join(transcript_lines)
        transcript_bytes = transcript_text.encode("utf-8")

        # Build the completed-work record.
        completed_channel = guild.get_channel(
            COMPLETED_WORK_CHANNEL_ID
        )

        if completed_channel is None:
            completed_channel = await bot.fetch_channel(
                COMPLETED_WORK_CHANNEL_ID
            )

        client_mention = client.mention if client else f"User ID: {client_id}"

        summary = make_embed(
            "Completed Inquiry 📁",
            (
                f"**Client:** {client_mention}\n"
                f"**Inquiry:** `#{channel.name}`\n"
                f"**Closed by:** {actor.mention}\n\n"
                "The full conversation transcript is attached."
            ),
            PURPLE
        )
        summary.set_footer(
            text="Ferrel Designs | Designed for your community. Built to work."
        )

        # Store the full transcript in the completed-work channel.
        await completed_channel.send(
            embed=summary,
            file=discord.File(
                io.BytesIO(transcript_bytes),
                filename=f"{channel.name}-transcript.txt"
            )
        )

        # Send a separate copy to the client, if possible.
        dm_sent = False
        if client:
            try:
                await client.send(
                    embed=make_embed(
                        "Your Inquiry Transcript 💜💙",
                        (
                            "Your Ferrel Designs inquiry has been closed. "
                            "I've attached a copy of the conversation "
                            "for your records. Thank you for reaching out!"
                        ),
                        BLUE
                    ),
                    file=discord.File(
                        io.BytesIO(transcript_bytes),
                        filename=f"{channel.name}-transcript.txt"
                    )
                )
                dm_sent = True
            except discord.Forbidden:
                print(
                    f"Could not DM transcript to client {client_id}; "
                    "their DMs may be closed."
                )

        # Lock the channel after the transcript has been saved.
        if client:
            await channel.set_permissions(
                client,
                overwrite=discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=False
                ),
                reason="Ferrel Designs inquiry closed"
            )

        await channel.edit(
            name=f"closed-{channel.name}"[:100],
            topic=f"closed_ferrel_quote_user:{client_id}",
            reason=f"Inquiry closed by {actor}"
        )

        await channel.send(
            embed=make_embed(
                "Inquiry Closed 🔒",
                (
                    f"This inquiry was closed by {actor.mention}.\n\n"
                    "The conversation history has been preserved and "
                    "the transcript has been saved to the completed-work "
                    "channel."
                    + (
                        "\nThe client was also sent a DM copy."
                        if dm_sent
                        else "\nThe client could not be sent a DM copy; "
                             "the transcript is saved in completed work."
                    )
                ),
                SILVER
            )
        )

        return True

    except discord.Forbidden as error:
        print(f"CLOSE PERMISSION ERROR: {error!r}")
        await actor.send(
            "I couldn't finish closing this inquiry. Check the bot's "
            "permissions for the inquiry channel and #completed-work."
        )
        return False

    except Exception as error:
        print(
            f"Close inquiry failed: {type(error).__name__}: {error}"
        )
        await actor.send(
            "Something went wrong while closing this inquiry. "
            "Please check the bot logs."
        )
        return False


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
intents.message_content = True


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

        channel = None

        try:
            channel = await guild.create_text_channel(
                name=f"quote-{member.name}".lower()[:90],
                topic=f"ferrel_quote_user:{member.id}",
                overwrites=overwrites,
                reason=f"Quote inquiry opened by {member}"
            )

            await interaction.followup.send(
                f"Your private inquiry is ready: {channel.mention}",
                ephemeral=True
            )

            
        await channel.send(
            f"Welcome, {member.mention}! 💜💙\n\n"
            "I'll guide you through a few questions, one at a time, "
            "so I can understand your project and prepare a quote.\n"
            "Please answer each question in this channel. "
            "You have 10 minutes to answer each one.\n\n"
            "If you decide not to continue, you can close this inquiry "
            "using the button below or by typing `$close`.",
            view=CloseInquiryView()
        )


            questions = [
                (
                    "1 of 6 — Your Community",
                    "What is your community or Discord server about? "
                    "For example, a FiveM roleplay server, gaming community, "
                    "business, or creator community."
                ),
                (
                    "2 of 6 — Current Setup",
                    "Do you need a brand-new Discord server, or do you "
                    "already have a server you want me to improve? "
                    "If it already exists, what would you like changed?"
                ),
                (
                    "3 of 6 — Features",
                    "What would you like included? For example, categories, "
                    "channels, roles, permissions, applications, tickets, "
                    "bots, automation, staff departments, or documentation."
                ),
                (
                    "4 of 6 — Branding and Style",
                    "Do you have existing logos, colors, or branding? "
                    "Describe the look you want, or share any visual "
                    "references in this channel."
                ),
                (
                    "5 of 6 — Budget",
                    "Which budget range are you considering? My packages "
                    "start at $40 for Foundation, $75 for Professional, "
                    "and $100+ for Custom. You can also tell me if "
                    "you're unsure and would like a recommendation."
                ),
                (
                    "6 of 6 — Timeline",
                    "When would you ideally like the project completed? "
                    "Please include a target date or approximate timeframe."
                )
            ]

            answers = []

            for title, question in questions:
                await channel.send(
                    embed=make_embed(title, question, PURPLE)
                )

                def check(message):
                    return (
                        message.author.id == member.id
                        and message.channel.id == channel.id
                        and not message.author.bot
                    )

                try:
                    answer = await bot.wait_for(
                        "message",
                        check=check,
                        timeout=600
                    )
                except asyncio.TimeoutError:
                    await channel.send(
                        f"{member.mention}, I haven't received an answer "
                        "within 10 minutes, so I'll pause the intake here. "
                        "Please contact me in this channel when you're "
                        "ready to continue."
                    )
                    return

                answers.append(answer.content.strip() or "[No text provided]")

            summary = make_embed(
                "New Project Inquiry 📋",
                (
                    f"**Client:** {member.mention}\n"
                    f"**Discord:** {member}\n"
                    f"**Private inquiry:** {channel.mention}\n\n"
                    "The client has completed all six intake questions. "
                    "Review their answers below and follow up before "
                    "confirming a package or price."
                ),
                PURPLE
            )

            field_names = [
                "Community",
                "Current Setup",
                "Requested Features",
                "Branding & Style",
                "Budget",
                "Timeline"
            ]

            for name, answer in zip(field_names, answers):
                # Discord embed fields have a 1024-character limit.
                summary.add_field(
                    name=name,
                    value=answer[:1024],
                    inline=False
                )

            summary.set_footer(
                text="Ferrel Designs | Designed for your community. Built to work."
            )

            inquiries_channel = guild.get_channel(
                NEW_INQUIRIES_CHANNEL_ID
            )

            if inquiries_channel is None:
                inquiries_channel = await bot.fetch_channel(
                    NEW_INQUIRIES_CHANNEL_ID
                )

            await inquiries_channel.send(embed=summary)

            await channel.send(
                f"Thank you, {member.mention}! 🎉 You've completed "
                "the initial project questions. I've sent your inquiry "
                "to the Ferrel Designs project review channel. "
                "I'll review your details and follow up here about "
                "scope, pricing, and next steps."
            )

        except discord.Forbidden as error:
            print(f"QUOTE PERMISSION ERROR: {error!r}")
            message = (
                "I couldn't complete the intake because I lack a required "
                "Discord permission. Please check my channel permissions."
            )
            if channel is not None:
                await channel.send(message)
            else:
                await interaction.followup.send(message, ephemeral=True)

        except Exception as error:
            print(
                f"Quote intake failed: {type(error).__name__}: {error}"
            )
            if channel is not None:
                await channel.send(
                    "Something went wrong while processing this inquiry. "
                    "I've logged the error so the issue can be investigated."
                )


class CloseInquiryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(
        label="Confirm Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ferrel_confirm_close"
    )
    async def confirm_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This action is only available inside the server.",
                ephemeral=True
            )
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "This isn't a valid inquiry channel.",
                ephemeral=True
            )
            return

        if not channel.topic or not channel.topic.startswith(
            "ferrel_quote_user:"
        ):
            await interaction.response.send_message(
                "This inquiry is already closed or isn't valid.",
                ephemeral=True
            )
            return

        client_id = int(
            channel.topic[len("ferrel_quote_user:"):]
        )

        actor = interaction.user

        if (
            actor.id != client_id
            and not actor.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Only the client who opened this inquiry or a server "
                "administrator can close it.",
                ephemeral=True
            )
            return

        
        await interaction.response.defer(ephemeral=True)

        success = await close_inquiry_channel(channel, actor)

        if success:
            await interaction.followup.send(
                "The inquiry has been closed. The transcript has been archived.",
                ephemeral=True
           )
        else:
            await interaction.followup.send(
                "The inquiry could not be fully closed. Please check the bot logs.",
                ephemeral=True
            )
        return

        for child in self.children:
            child.disabled = True

        try:
            await interaction.message.edit(view=self)
        except (discord.HTTPException, AttributeError):
            pass

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="↩️",
        custom_id="ferrel_cancel_close"
    )
    async def cancel_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="Inquiry closure cancelled.",
            embed=None,
            view=None
        )


@bot.command(name="close")
async def close_command(ctx: commands.Context):
    if not isinstance(ctx.author, discord.Member):
        return

    channel = ctx.channel

    if not isinstance(channel, discord.TextChannel):
        await ctx.reply("This command only works in a text channel.")
        return

    if not channel.topic or not channel.topic.startswith(
        "ferrel_quote_user:"
    ):
        await ctx.reply(
            "This isn't an active Ferrel Designs inquiry channel."
        )
        return

    client_id = int(
        channel.topic[len("ferrel_quote_user:"):]
    )

    if (
        ctx.author.id != client_id
        and not ctx.author.guild_permissions.administrator
    ):
        await ctx.reply(
            "Only the client who opened this inquiry or a server "
            "administrator can close it."
        )
        return

    view = CloseInquiryView()

    await ctx.send(
        embed=make_embed(
            "Close This Inquiry?",
            (
                "Are you sure you want to close this inquiry?\n\n"
                "Closing will lock the conversation and preserve "
                "the existing history."
            ),
            PURPLE
        ),
        view=view
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
