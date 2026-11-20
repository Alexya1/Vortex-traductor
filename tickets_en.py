import io
import html
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

# 1) Bonds & GP (Ms)
MENSAJE_BIENVENIDA_BONDS_GP = (
    "👋 **Welcome to your Economy Ticket, {user}!**\n\n"
    "A member of the **Vórtex OSRS** team will assist you shortly.\n"
    ".\n"
    "📌 **Please let us know:**\n"
    "- Are you going to buy or sell **Bonds** or **GP (Ms)**?\n"
    "- The **amount** of Ms or Bonds you need.\n"
    "- Your **payment method** (whether Pago Móvil, Binance, or others).\n"
    ".\n"
    "⚠️ *A moderator will review your request shortly.*"
)

# 2) Skills, Quests & Services
MENSAJE_BIENVENIDA_SERVICIOS = (
    "👋 **Welcome to your Account Services Ticket, {user}!**\n"
    ".\n"
    "The **Vórtex OSRS** boosters and moderators team will pick up your request right away.\n"
    ".\n"
    "📌 **Please let us know:**\n"
    "- **Skills:** Skill you want to train and from what level to what level (e.g., Mining 60 to 70).\n"
    "- **Quests / Diaries:** Specific quests or diaries you need completed.\n"
    "- **Services / KC:** If you require Bosses, Raids, Kits, or Diaries service.\n"
    ".\n"
    "⚠️ *Leave the details below and we will give you a quick quote.*"
)

# 3) Middleman
MENSAJE_BIENVENIDA_MIDDLEMAN = (
    "👋 **Welcome to the Middleman Service, {user}!**\n"
    ".\n"
    "An administrator or official from **Vortex OSRS** will take care of the safety of your trade.\n"
    ".\n"
    "📌 **Please let us know:**\n"
    "- Who are the two parties in the deal? (Mention the user you are trading with, who is the buyer and who is the seller).\n"
    "- The total value or amount of the account/trade.\n"
    ".\n"
    "⚠️ *For your safety, DO NOT hand over details, gold, or accounts until the Official Middleman is present in this chat.*"
)


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


def _generar_html_transcript(channel: discord.TextChannel, closed_by: discord.abc.User, mensajes: list[discord.Message]) -> bytes:
    closed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    bloques_html = []

    for m in mensajes:
        autor = html.escape(m.author.display_name)
        tag_autor = html.escape(str(m.author))
        avatar_url = html.escape(m.author.display_avatar.url)
        hora = html.escape(m.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        cuerpo = html.escape(m.content or "").replace("\n", "<br>")
        badge_bot = '<span class="badge">APP</span>' if m.author.bot else ""

        adjuntos_html = ""
        if m.attachments:
            items = []
            for att in m.attachments:
                url_esc = html.escape(att.url)
                nombre_esc = html.escape(att.filename)
                if att.content_type and att.content_type.startswith("image/"):
                    items.append(
                        f'<div class="attachment"><a href="{url_esc}" target="_blank">'
                        f'<img src="{url_esc}" alt="{nombre_esc}" /></a></div>'
                    )
                else:
                    items.append(
                        f'<div class="attachment"><a href="{url_esc}" target="_blank">📎 {nombre_esc}</a></div>'
                    )
            adjuntos_html = "".join(items)

        bloques_html.append(
            f"""
            <div class="msg">
                <img class="avatar" src="{avatar_url}" alt="{autor}" />
                <div class="msg-body">
                    <div class="msg-header">
                        <span class="author" title="{tag_autor}">{autor}</span>
                        {badge_bot}
                        <span class="time">{hora}</span>
                    </div>
                    <div class="content">{cuerpo}</div>
                    {adjuntos_html}
                </div>
            </div>
            """
        )

    cuerpo_mensajes = "\n".join(bloques_html) if bloques_html else '<div class="empty">No messages in this ticket.</div>'
    canal_esc = html.escape(channel.name)
    cerrado_por_esc = html.escape(str(closed_by))

    documento = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Transcript - #{canal_esc}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0;
    background-color: #313338;
    color: #dbdee1;
    font-family: "gg sans", "Noto Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
  }}
  .header {{
    background-color: #2b2d31;
    border-bottom: 1px solid #1e1f22;
    padding: 18px 24px;
    position: sticky;
    top: 0;
    z-index: 10;
  }}
  .header h1 {{
    margin: 0 0 6px 0;
    font-size: 20px;
    color: #f2f3f5;
  }}
  .meta {{
    font-size: 13px;
    color: #949ba4;
  }}
  .chat {{
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px 16px 40px 16px;
  }}
  .msg {{
    display: flex;
    gap: 14px;
    padding: 8px 10px;
    border-radius: 6px;
  }}
  .msg:hover {{
    background-color: #2e3035;
  }}
  .avatar {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .msg-body {{
    min-width: 0;
    flex: 1;
  }}
  .msg-header {{
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 3px;
  }}
  .author {{
    font-weight: 600;
    color: #f2f3f5;
    font-size: 15px;
  }}
  .badge {{
    background-color: #5865f2;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    text-transform: uppercase;
  }}
  .time {{
    font-size: 12px;
    color: #949ba4;
  }}
  .content {{
    font-size: 15px;
    line-height: 1.4;
    word-wrap: break-word;
  }}
  .attachment {{
    margin-top: 8px;
  }}
  .attachment img {{
    max-width: 380px;
    max-height: 300px;
    border-radius: 6px;
    display: block;
  }}
  .attachment a {{
    color: #00a8fc;
    text-decoration: none;
  }}
  .attachment a:hover {{
    text-decoration: underline;
  }}
  .empty {{
    text-align: center;
    color: #949ba4;
    padding: 40px;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>Vórtex OSRS — Ticket Transcript (#{canal_esc})</h1>
    <div class="meta">Channel ID: {channel.id} • Closed by: {cerrado_por_esc} • Closed at: {html.escape(closed_at)} • Messages: {len(mensajes)}</div>
  </div>
  <div class="chat">
    {cuerpo_mensajes}
  </div>
</body>
</html>"""
    return documento.encode("utf-8")


class TicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="vortex_en_claim_ticket",
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ This button only works inside a ticket.", ephemeral=True)
            return

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name[:18]}"
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        await interaction.response.send_message(
            f"🙋 **Ticket claimed!** {interaction.user.mention} will attend to this ticket.",
            ephemeral=False,
        )

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

        await interaction.response.send_message("🔒 Generating chat transcript and closing ticket...", ephemeral=False)

        guild = interaction.guild
        transcript_channel = guild.get_channel(TRANSCRIPT_CHANNEL_ID) if guild else None
        if not isinstance(transcript_channel, discord.TextChannel) and guild:
            try:
                transcript_channel = await guild.fetch_channel(TRANSCRIPT_CHANNEL_ID)
            except Exception:
                transcript_channel = None

        try:
            mensajes = [m async for m in channel.history(limit=None, oldest_first=True)]
        except Exception as e:
            print(f"Error reading channel history: {e}")
            mensajes = []

        html_bytes = _generar_html_transcript(channel, interaction.user, mensajes)
        archivo = discord.File(
            fp=io.BytesIO(html_bytes),
            filename=f"transcript-{channel.name}.html",
        )

        if isinstance(transcript_channel, discord.TextChannel):
            try:
                embed = discord.Embed(
                    title="📄 Ticket Chat Transcript",
                    description=(
                        f"**Channel:** `#{channel.name}`\n"
                        f"**Closed by:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**Total messages:** {len(mensajes)}\n"
                        f"*Download the HTML file to view the full chat with names, timestamps, and attachments.*"
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
            category=None,
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
        view=TicketActionsView(),
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
        await _crear_canal_ticket(interaction, "bonds-gp", ROLES_BONDS_GP, MENSAJE_BIENVENIDA_BONDS_GP)

    @discord.ui.button(
        label="Skills, Quests & Services",
        style=discord.ButtonStyle.primary,
        emoji="⚔️",
        custom_id="vortex_en_open_services",
    )
    async def open_services(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _crear_canal_ticket(interaction, "services", ROLES_STAFF_DOS, MENSAJE_BIENVENIDA_SERVICIOS)

    @discord.ui.button(
        label="Middleman",
        style=discord.ButtonStyle.primary,
        emoji="🛡️",
        custom_id="vortex_en_open_middleman",
    )
    async def open_middleman(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _crear_canal_ticket(interaction, "middleman", ROLES_STAFF_DOS, MENSAJE_BIENVENIDA_MIDDLEMAN)


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
        client.add_view(TicketActionsView())

    on_ready_callbacks.append(_registrar_vistas_persistentes)
