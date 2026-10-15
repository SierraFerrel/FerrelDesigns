import os
import io
import asyncio
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

PURPLE = 0x7B3FF2
BLUE = 0x3B82F6
SILVER = 0xC0C4CC

RULES_MESSAGE_ID = 1559107562115170355
WELCOME_CHANNEL_ID = 1558404692466335807
NEW_INQUIRIES_CHANNEL_ID = 1558704116581273722
COMPLETED_WORK_CHANNEL_ID = 1558704266363932682
COMMUNITY_ROLE_ID = 1558706183508987966
CLIENT_ROLE_ID = 1558706829461291038
RULES_CHANNEL_ID = 1559102565013004398
ACTIVE_TICKETS_CATEGORY_ID = 1559100928018350103
RULES_REACTION = "💜"


def make_embed(title, description, color=PURPLE):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(
        text="Ferrel Designs | Designed for your community. Built to work."
    )
    return embed


intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class FerrelDesignsBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(QuotePanelView())
        self.add_view(GeneralInquiryPanelView())
        self.add_view(CloseInquiryView())

        print(
            "LOCAL SLASH COMMANDS:",
            [command.name for command in self.tree.get_commands()]
        )
        print("Starting Ferrel Designs command synchronization...")

        try:
            synced = await self.tree.sync()
            print(f"SUCCESS: Synced {len(synced)} global slash commands.")

            for command in synced:
                print(f"Registered command: /{command.name}")

        except Exception as error:
            print(
                f"COMMAND SYNC FAILED: {type(error).__name__}: {error}"
            )
            raise


bot = FerrelDesignsBot(
    command_prefix=["!", "$"],
    intents=intents
)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id is None:
        return

    if payload.channel_id != RULES_CHANNEL_ID:
        return

    if payload.message_id != RULES_MESSAGE_ID:
        return

    if str(payload.emoji) != RULES_REACTION:
        return

    if bot.user and payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = payload.member
    if member is None:
        try:
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return
        except discord.HTTPException as error:
            print(f"Could not fetch reacting member: {error}")
            return

    community_role = guild.get_role(COMMUNITY_ROLE_ID)
    if community_role is None:
        print("ERROR: Ferrel Community role was not found.")
        return

    if community_role in member.roles:
        return

    try:
        await member.add_roles(
            community_role,
            reason="Accepted Ferrel Designs community rules"
        )
        print(f"Assigned Ferrel Community to {member}.")

    except discord.Forbidden:
        print(
            "ERROR: Cannot assign Ferrel Community. "
            "Check the bot's Manage Roles permission and role hierarchy."
        )
    except discord.HTTPException as error:
        print(f"Could not assign Ferrel Community: {error}")


async def close_inquiry_channel(
    channel: discord.TextChannel,
    actor: discord.Member
) -> bool:
    guild = channel.guild

    prefixes = (
        "ferrel_quote_user:",
        "ferrel_general_user:"
    )

    if not channel.topic:
        return False

    prefix = next(
        (p for p in prefixes if channel.topic.startswith(p)),
        None
    )

    if prefix is None:
        return False

    try:
        client_id = int(channel.topic[len(prefix):])
    except ValueError:
        return False

    if (
        actor.id != client_id
        and not actor.guild_permissions.administrator
    ):
        return False

    client = guild.get_member(client_id)

    if client is None:
        try:
            client = await guild.fetch_member(client_id)
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            client = None

    try:
        transcript_lines = [
            "Ferrel Designs Inquiry Transcript",
            f"Channel: #{channel.name}",
            f"Client ID: {client_id}",
            f"Closed by: {actor} ({actor.id})",
            f"Transcript generated: {discord.utils.utcnow().isoformat()}",
            "=" * 70,
            ""
        ]

        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):
            timestamp = message.created_at.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

            transcript_lines.append(
                f"[{timestamp}] {message.author} ({message.author.id})"
            )

            if message.content:
                transcript_lines.append(message.content)

            for embed in message.embeds:
                if embed.title:
                    transcript_lines.append(
                        f"Embed title: {embed.title}"
                    )

                if embed.description:
                    transcript_lines.append(
                        f"Embed description: {embed.description}"
                    )

            for attachment in message.attachments:
                transcript_lines.append(
                    f"Attachment: {attachment.filename} — {attachment.url}"
                )

            transcript_lines.append("")

        transcript_bytes = "\n".join(
            transcript_lines
        ).encode("utf-8")

        filename = f"{channel.name}-transcript.txt"

        completed_channel = guild.get_channel(
            COMPLETED_WORK_CHANNEL_ID
        )

        if completed_channel is None:
            completed_channel = await bot.fetch_channel(
                COMPLETED_WORK_CHANNEL_ID
            )

        if not isinstance(completed_channel, discord.TextChannel):
            raise RuntimeError(
                "The completed-work ID is not a text channel."
            )

        client_mention = (
            client.mention if client else f"User ID: {client_id}"
        )

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

        await completed_channel.send(
            embed=summary,
            file=discord.File(
                io.BytesIO(transcript_bytes),
                filename=filename
            )
        )

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
                        filename=filename
                    )
                )
            except discord.Forbidden:
                print(
                    f"Could not DM transcript to client {client_id}."
                )

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

        await channel.send(
            embed=make_embed(
                "Inquiry Closed 🔒",
                f"This inquiry was closed by {actor.mention}.\n\n"
                "The conversation transcript has been preserved. "
                "This channel will be deleted in 5 seconds. 💜"
            )
        )

        await asyncio.sleep(5)

        await channel.delete(
            reason=f"Ferrel Designs inquiry closed by {actor}"
        )

        return True

    except Exception as error:
        print(
            f"CLOSE INQUIRY ERROR: {type(error).__name__}: {error}"
        )
        traceback.print_exc()
        return False


class CloseInquiryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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

        prefixes = (
            "ferrel_quote_user:",
            "ferrel_general_user:"
        )

        if (
            not channel.topic
            or not channel.topic.startswith(prefixes)
        ):
            await interaction.response.send_message(
                "This inquiry is already closed or isn't valid.",
                ephemeral=True
            )
            return

        prefix = next(
            p for p in prefixes if channel.topic.startswith(p)
        )

        try:
            client_id = int(channel.topic[len(prefix):])
        except ValueError:
            await interaction.response.send_message(
                "I couldn't identify the inquiry owner.",
                ephemeral=True
            )
            return

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
            for child in self.children:
                child.disabled = True

            try:
                await interaction.message.edit(view=self)
            except (discord.HTTPException, AttributeError):
                pass

            await interaction.followup.send(
                "The inquiry has been closed and the transcript archived.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "The inquiry could not be fully closed. "
                "Check the Render logs for details.",
                ephemeral=True
            )

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


class GeneralInquiryModal(discord.ui.Modal, title="General Inquiry"):
    inquiry = discord.ui.TextInput(
        label="What can I help you with today?",
        placeholder=(
            "Tell me about your question, partnership, "
            "promotion, report, or other inquiry..."
        ),
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        await create_general_inquiry_ticket(
            interaction,
            str(self.inquiry.value).strip()
        )


class GeneralInquiryPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open General Inquiry",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="ferrel_general_inquiry"
    )
    async def open_general_inquiry(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(GeneralInquiryModal())


async def create_general_inquiry_ticket(
    interaction: discord.Interaction,
    inquiry_text: str
):
    guild = interaction.guild
    member = interaction.user

    if guild is None or not isinstance(member, discord.Member):
        await interaction.followup.send(
            "Please use this application inside the Ferrel Designs server.",
            ephemeral=True
        )
        return

    topic = f"ferrel_general_user:{member.id}"

    existing = discord.utils.get(
        guild.text_channels,
        topic=topic
    )

    if existing:
        await interaction.followup.send(
            f"You already have an open general inquiry: {existing.mention}",
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

    try:
        category = guild.get_channel(ACTIVE_TICKETS_CATEGORY_ID)

        if not isinstance(category, discord.CategoryChannel):
            raise RuntimeError(
                "The Active Tickets category was not found."
            )

        channel = await guild.create_text_channel(
            name=f"general-{member.name}".lower()[:90],
            topic=topic,
            category=category,
            overwrites=overwrites,
            reason=f"General inquiry opened by {member}"
        )

        await channel.send(
            embed=make_embed(
                "New General Inquiry 💬",
                (
                    f"Welcome, {member.mention}! 💜💙\n\n"
                    "Thank you for reaching out to Ferrel Designs. "
                    "I've received your inquiry and will review it "
                    "as soon as I can.\n\n"
                    f"**Your inquiry:**\n{inquiry_text}\n\n"
                    "Please use this private channel for any additional "
                    "details or follow-up messages."
                ),
                PURPLE
            ),
            view=CloseInquiryView()
        )

        await interaction.followup.send(
            f"Your private general inquiry is ready: {channel.mention}",
            ephemeral=True
        )

    except Exception as error:
        print(
            "GENERAL INQUIRY CREATION ERROR: "
            f"{type(error).__name__}: {error}"
        )
        traceback.print_exc()

        try:
            await interaction.followup.send(
                "I couldn't create your general inquiry. "
                "Please contact me directly.",
                ephemeral=True
            )
        except discord.HTTPException as followup_error:
            print(
                "GENERAL INQUIRY ERROR MESSAGE FAILED: "
                f"{type(followup_error).__name__}: {followup_error}"
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

        if (
            guild is None
            or not isinstance(member, discord.Member)
        ):
            await interaction.response.send_message(
                "Please use this button inside the Ferrel Designs server.",
                ephemeral=True
            )
            return

        community_role = guild.get_role(COMMUNITY_ROLE_ID)

        if community_role is None:
            await interaction.response.send_message(
                "The community role is not configured correctly. "
                "Please contact the server administrator.",
                ephemeral=True
            )
            return

        if community_role not in member.roles:
            await interaction.response.send_message(
                "💜 Before requesting a quote, please visit "
                "#rules-and-vibes and react with 💜 to receive "
                "the Ferrel Community role!",
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

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

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

        channel = None

        try:
            category = guild.get_channel(ACTIVE_TICKETS_CATEGORY_ID)

            if not isinstance(category, discord.CategoryChannel):
                raise RuntimeError(
                    "The Active Tickets category was not found."
                )

            channel = await guild.create_text_channel(
                name=f"quote-{member.name}".lower()[:90],
                topic=f"ferrel_quote_user:{member.id}",
                category=category,
                overwrites=overwrites,
                reason=f"Quote inquiry opened by {member}"
            )

            await interaction.followup.send(
                f"Your private inquiry is ready: {channel.mention}",
                ephemeral=True
            )

            await channel.send(
                f"Welcome, {member.mention}! 💜💙\n\n"
                "I'll guide you through six questions, one at a time, "
                "so I can understand your project and prepare a quote.\n"
                "Please answer each question in this channel. "
                "You have 10 minutes to answer each question.\n\n"
                "If you decide not to continue, use the close buttons "
                "below or type `$close`.",
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
                    "Describe the look you want, or share visual references."
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
                        "within 10 minutes, so I've paused the intake. "
                        "Please contact me when you're ready to continue."
                    )
                    return

                answers.append(
                    answer.content.strip() or "[No text provided]"
                )

            summary = make_embed(
                "New Project Inquiry 📋",
                (
                    f"**Client:** {member.mention}\n"
                    f"**Discord:** {member}\n"
                    f"**Private inquiry:** {channel.mention}\n\n"
                    "The client has completed all six intake questions. "
                    "Review their answers before confirming a package or price."
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
                summary.add_field(
                    name=name,
                    value=answer[:1024],
                    inline=False
                )

            inquiries_channel = guild.get_channel(
                NEW_INQUIRIES_CHANNEL_ID
            )

            if inquiries_channel is None:
                inquiries_channel = await bot.fetch_channel(
                    NEW_INQUIRIES_CHANNEL_ID
                )

            if not isinstance(
                inquiries_channel,
                discord.TextChannel
            ):
                raise RuntimeError(
                    "The new-inquiries ID is not a text channel."
                )

            await inquiries_channel.send(embed=summary)

            # Assign Ferrel Client without removing existing roles.
            client_role = guild.get_role(CLIENT_ROLE_ID)

            if client_role is None:
                print("ERROR: Ferrel Client role was not found.")
                await channel.send(
                    "Your inquiry was submitted successfully, but I "
                    "couldn't automatically assign your client role. "
                    "Please contact me so I can fix that. 💜"
                )
            elif client_role not in member.roles:
                try:
                    await member.add_roles(
                        client_role,
                        reason="Completed Ferrel Designs quote application"
                    )
                    print(f"Assigned Ferrel Client to {member}.")

                except discord.Forbidden:
                    print(
                        "ERROR: Cannot assign Ferrel Client. "
                        "Check Manage Roles permission and role hierarchy."
                    )
                    await channel.send(
                        "Your inquiry was submitted successfully, but I "
                        "couldn't automatically assign your client role. "
                        "Please contact me so I can fix that. 💜"
                    )

            await channel.send(
                f"Thank you, {member.mention}! 🎉 You've completed "
                "the initial project questions. I've sent your inquiry "
                "to my project review channel. I'll follow up here about "
                "scope, pricing, and next steps."
            )

        except discord.Forbidden:
            print("QUOTE PERMISSION ERROR:")
            traceback.print_exc()

            try:
                if channel is not None:
                    await channel.send(
                        "I couldn't complete the intake because I lack a "
                        "required Discord permission. Please contact me."
                    )
                else:
                    await interaction.followup.send(
                        "I couldn't create your inquiry. Please contact me.",
                        ephemeral=True
                    )
            except discord.HTTPException:
                pass

        except Exception as error:
            print(
                f"QUOTE INTAKE ERROR: {type(error).__name__}: {error}"
            )
            traceback.print_exc()

            try:
                if channel is not None:
                    await channel.send(
                        "Something went wrong while processing this inquiry. "
                        "I've logged the error for investigation."
                    )
                else:
                    await interaction.followup.send(
                        "Something went wrong creating your inquiry. "
                        "Please try again later.",
                        ephemeral=True
                    )
            except discord.HTTPException:
                pass


@bot.command(name="close")
async def close_command(ctx: commands.Context):
    if not isinstance(ctx.author, discord.Member):
        return

    channel = ctx.channel

    if not isinstance(channel, discord.TextChannel):
        await ctx.reply("This command only works in a text channel.")
        return

    prefixes = (
        "ferrel_quote_user:",
        "ferrel_general_user:",
    )

    if not channel.topic or not channel.topic.startswith(prefixes):
        await ctx.reply(
            "This isn't an active Ferrel Designs inquiry channel."
        )
        return

    prefix = next(
        p for p in prefixes if channel.topic.startswith(p)
    )

    try:
        client_id = int(channel.topic[len(prefix):])
    except ValueError:
        await ctx.reply("I couldn't identify the inquiry owner.")
        return

    if (
        ctx.author.id != client_id
        and not ctx.author.guild_permissions.administrator
    ):
        await ctx.reply(
            "Only the client who opened this inquiry or a server "
            "administrator can close it."
        )
        return

    await ctx.send(
        embed=make_embed(
            "Close This Inquiry?",
            (
                "Are you sure you want to close this inquiry?\n\n"
                "Closing will archive the conversation transcript "
                "and delete this channel."
            ),
            PURPLE
        ),
        view=CloseInquiryView()
    )
@bot.event
async def on_member_join(member: discord.Member):
    channel = member.guild.get_channel(
        WELCOME_CHANNEL_ID
    )

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
            "**✨ Get Started:**\n"
            "💜 Head over to <#1559102565013004398> and react with 💜 "
            "to the rules message to unlock the Ferrel Community role.\n\n"
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
    name="post-quote-panel",
    description="Post the Ferrel Designs quote request panel."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_quote_panel(
    interaction: discord.Interaction
):
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
    name="post-general-inquiry-panel",
    description="Post the General Inquiry application panel."
)
@app_commands.checks.has_permissions(administrator=True)
async def post_general_inquiry_panel(
    interaction: discord.Interaction
):
    embed = make_embed(
        "General Inquiries 💬",
        (
            "Have a question, partnership idea, promotion opportunity, "
            "or something else you'd like to discuss?\n\n"
            "You can also use this application to report misuse of "
            "Ferrel Designs work or raise any other concerns.\n\n"
            "**How it works:**\n"
            "• Click the button below.\n"
            "• Describe your inquiry in the form.\n"
            "• A private ticket will be created for you.\n\n"
            "I'm happy to hear from you! 💜💙"
        ),
        PURPLE
    )

    await interaction.response.send_message(
        embed=embed,
        view=GeneralInquiryPanelView()
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Set it in your environment."
        )

    bot.run(TOKEN)
