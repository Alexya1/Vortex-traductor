import io
from datetime import datetime, timezone
import discord
from discord import app_commands

TRANSCRIPT_CHANNEL_ID = 1518545714500735107

ROLES_BONDS_GP = [
    1416424801744195646,
    1556538124056657980,
    1571735505341648927,
]

ROLES_STAFF_DOS = [
    1416424801744195646,
    1556538124056657980,
]


def _construir_overwrites(guild: discord.Guild, member: discord.Member, role_ids: list[int]) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
        )
    for rid in role_ids:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )
    return overwrites


def _menciones_roles(guild: discord.Guild, role_ids: list[int]) -> str:
    menciones = []
    for rid in role_ids:
        role = guild.get_role(rid)
        menciones.append(role.mention if role else f"<@&{rid}>")
    return " ".join(menciones)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="vortex_en_close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ This can only be used inside a ticket channel.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Saving transcript and closing ticket...", ephemeral=False)

        guild = interaction.guild
        transcript_channel = guild.get_channel(TRANSCRIPT_CHANNEL_ID) if guild else None
        if not isinstance(transcript_channel, discord.TextChannel) and guild:
            try:
                transcript_channel = await guild.fetch_channel(TRANSCRIPT_CHANNEL_ID)
            except Exception:
                transcript_channel = None

        lineas = [
            f"Ticket Transcript: #{channel.name} (ID: {channel.id})",
            f"Closed by: {interaction.user} (ID: {interaction.user.id})",
            f"Closed at (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 60,
        ]

        try:
            mensajes = [m async for m in channel.history(limit=None, oldest_first=True)]
            for m in mensajes:
                ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
                contenido = m.content or ""
                adjuntos = ", ".join(a.url for a in m.attachments)
                linea = f"[{ts}] {m.author} ({m.author.id}): {contenido}"
                if adjuntos:
                    linea += f" [Attachments: {adjuntos}]"
                lineas.append(linea)
        except Exception as e:
            lineas.append(f"[Error reading history: {e}]")

        contenido_txt = "\n".join(lineas)
        archivo = discord.File(
            fp=io.BytesIO(contenido_txt.encode("utf-8")),
            filename=f"transcript-{channel.name}.txt",
        )

        if isinstance(transcript_channel, discord.TextChannel):
            try:
                embed = discord.Embed(
                    title="📄 Ticket Transcript",
                    description=(
                        f"**Channel:** `#{channel.name}`\n"
                        f"**Closed by:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**Total messages:** {max(len(lineas) - 4, 0)}"
                    ),
                    color=discord.Color.blurple(),
                    timestamp=datetime.now(timezone.utc),
                )
                await transcript_channel.send(embed=embed, file=archivo)
            except Exception as e:
                print(f"Error sending transcript to #historial-no-tocar: {e}")
        else:
            print(f"Transcript channel {TRANSCRIPT_CHANNEL_ID} not found.")

        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")


async def _crear_canal_ticket(
    interaction: discord.Interaction,
    prefijo: str,
    role_ids: list[int],
    mensaje_bienvenida: str,
):
    guild = interaction.guild
    member = interaction.user if isinstance(interaction.user, discord.Member) else None

    if not guild or not member:
        await interaction.response.send_message("❌ This command/button only works inside a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    nombre_limpio = "".join(c for c in member.name.lower() if c.isalnum() or c in ("-", "_"))[:15] or "user"
    channel_name = f"{prefijo}-{nombre_limpio}"[:95]

    try:
        overwrites = _construir_overwrites(guild, member, role_ids)
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=None,  # Arriba sin categoría
            overwrites=overwrites,
            reason=f"English ticket opened by {member}",
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission (`Manage Channels`) to create ticket channels.",
            ephemeral=True,
        )
        return
    except Exception as e:
        await interaction.followup.send(f"❌ Error creating ticket: `{e}`", ephemeral=True)
        return

    menciones = _menciones_roles(guild, role_ids)
    embed = discord.Embed(
        description=mensaje_bienvenida.format(user=member.mention),
        color=discord.Color.gold(),
    )

    await ticket_channel.send(
        content=f"{member.mention} {menciones}",
        embed=embed,
        view=CloseTicketView(),
    )

    await interaction.followup.send(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)


class TicketPanelENView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bonds & GP (Ms)",
        style=discord.ButtonStyle.primary,
        emoji="💰",
        custom_id="vortex_en_open_bonds_gp",
    )
    async def open_bonds_gp(self, interaction: discord.Interaction, button: discord.ui.Button):
        bienvenida = (
            "👋 **Welcome to your Economy Ticket, {user}!**\n\n"
            "A member of the **Vórtex OSRS** team will be with you shortly.\n"
            ".\n"
            "📌 **Please let us know:**\n"
            "- Are you buying or selling **Bonds** or **GP (Ms)**?\n"
            "- The **amount** of Ms or Bonds you need.\n"
            "- Your **payment method** (Pago Móvil, Binance, or others).\n"
            ".\n"
            "⚠️ *A moderator will review your request shortly.*"
        )
        await _crear_canal_ticket(interaction, "bonds-gp", ROLES_BONDS_GP, bienvenida)

    @discord.ui.button(
        label="Skills, Quests & Services",
        style=discord.ButtonStyle.primary,
        emoji="⚔️",
        custom_id="vortex_en_open_services",
    )
    async def open_services(self, interaction: discord.Interaction, button: discord.ui.Button):
        bienvenida = (
            "👋 **Welcome to your Services Ticket, {user}!**\n\n"
            "A member of the **Vórtex OSRS** team will be with you shortly.\n"
            ".\n"
            "📌 **Please let us know:**\n"
            "- Which **Skills**, **Quests**, or **Services** do you need?\n"
            "- Any extra details or requirements for your order.\n"
            "- Your **preferred payment method**.\n"
            ".\n"
            "⚠️ *Our staff team will review your request shortly.*"
        )
        await _crear_canal_ticket(interaction, "services", ROLES_STAFF_DOS, bienvenida)

    @discord.ui.button(
        label="Middleman",
        style=discord.ButtonStyle.primary,
        emoji="🛡️",
        custom_id="vortex_en_open_middleman",
    )
    async def open_middleman(self, interaction: discord.Interaction, button: discord.ui.Button):
        bienvenida = (
            "👋 **Welcome to your Middleman Ticket, {user}!**\n\n"
            "A **Vórtex OSRS** Middleman will assist you shortly.\n"
            ".\n"
            "📌 **Please let us know:**\n"
            "- Who is the other party involved in the trade?\n"
            "- What **items, GP, or services** are being traded and their value?\n"
            "- Your **payment methods** and deal details.\n"
            ".\n"
            "⚠️ *All deals must stay inside this ticket — zero DM trades.*"
        )
        await _crear_canal_ticket(interaction, "middleman", ROLES_STAFF_DOS, bienvenida)


def construir_panel_en_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ ATTENTION — Vortex OSRS",
        description=(
            "We offer Bonds/GP sales, Skills/Quests/Services, and Middleman.\n\n"
            "🚨 **ANTI-SCAM WARNING:**\n"
            "• **ZERO DM DEALS:** No Admin or Booster will message you in DMs to offer services or ask for details.\n"
            "• **EVERYTHING IS BY TICKET:** All payments and processes happen **ONLY** inside a ticket opened here.\n"
            "• **If someone DMs you pretending to be Staff, they are a scammer.**\n\n"
            "👇 **Open your ticket safely using the buttons below:**\n\n"
            "**Choose your service**\n"
            "💰 **Bonds & GP (Ms)** — Buy or sell Bonds & GP (Ms)\n"
            "⚔️ **Skills, Quests & Services** — Skills, Quests & Services\n"
            "🛡️ **Middleman** — Middleman service"
        ),
        color=discord.Color.blue(),
    )
    return embed


def registrar_tickets_en(client: discord.Client, tree: app_commands.CommandTree, on_ready_callbacks: list):
    @tree.command(name="panel_en", description="Publishes the English ticket panel in a channel")
    @app_commands.describe(channel="Channel where the English ticket panel will be posted (defaults to current)")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_en(interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("❌ Invalid text channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await target.send(embed=construir_panel_en_embed(), view=TicketPanelENView())
            await interaction.followup.send(f"✅ English ticket panel posted in {target.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Missing permission to send messages in {target.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error posting panel: `{e}`", ephemeral=True)

    async def _registrar_vistas_persistentes():
        client.add_view(TicketPanelENView())
        client.add_view(CloseTicketView())

    on_ready_callbacks.append(_registrar_vistas_persistentes)
