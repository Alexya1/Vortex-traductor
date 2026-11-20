import os
import json
import asyncio
import urllib.parse
import urllib.request
import discord
from discord import app_commands

CONFIG_FILE = "canales_config.json"


def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def guardar_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


PAREJAS_CANALES = cargar_config()


def traducir_google_gtx(texto, source_lang, target_lang):
    q = urllib.parse.quote(texto)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data and data[0]:
            return "".join(part[0] for part in data[0] if part and part[0])
    return None


def traducir_mymemory(texto, source_lang, target_lang):
    q = urllib.parse.quote(texto)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair={source_lang}|{target_lang}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        trad = data.get("responseData", {}).get("translatedText", "")
        if trad and "MYMEMORY WARNING" not in trad.upper():
            return trad
    return None


def traducir_texto(texto, target_lang):
    target = "en" if target_lang.lower() == "en" else "es"
    source = "es" if target == "en" else "en"

    for motor, fn in (("Google GTX", traducir_google_gtx), ("MyMemory", traducir_mymemory)):
        try:
            resultado = fn(texto, source, target)
            if resultado and resultado.strip():
                return resultado.strip()
        except Exception as e:
            print(f"Fallo en {motor}: {e}")
    return None


async def enviar_webhook(canal_destino, mensaje, texto_traducido):
    try:
        webhooks = await canal_destino.webhooks()
        webhook = discord.utils.get(webhooks, name="TraductorEspejo")
        if webhook is None:
            webhook = await canal_destino.create_webhook(name="TraductorEspejo")

        await webhook.send(
            content=texto_traducido,
            username=mensaje.author.display_name,
            avatar_url=mensaje.author.display_avatar.url
        )
        print(f"WEBHOOK ENVIADO A #{canal_destino.name}")
    except Exception as e:
        print(f"ERROR EN WEBHOOK: {e}")


def registrar_vinculaciones(client: discord.Client, tree: app_commands.CommandTree):
    @tree.command(name="vincular", description="Vincula dos canales (español e inglés) de forma bidireccional")
    @app_commands.describe(canal_es="Canal en español", canal_en="Canal en inglés")
    @app_commands.checks.has_permissions(administrator=True)
    async def vincular(
        interaction: discord.Interaction,
        canal_es: discord.TextChannel,
        canal_en: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)
        if canal_es.id == canal_en.id:
            await interaction.followup.send("⚠️ Debes elegir dos canales distintos.", ephemeral=True)
            return

        PAREJAS_CANALES[str(canal_es.id)] = {"destino": canal_en.id, "idioma": "en"}
        PAREJAS_CANALES[str(canal_en.id)] = {"destino": canal_es.id, "idioma": "es"}
        guardar_config(PAREJAS_CANALES)

        await interaction.followup.send(
            f"✅ Vinculados {canal_es.mention} ⟷ {canal_en.mention} bidireccionalmente.",
            ephemeral=True
        )

    @tree.command(name="desvincular", description="Elimina la vinculación de traducción de un canal")
    @app_commands.describe(canal="Cualquiera de los dos canales vinculados")
    @app_commands.checks.has_permissions(administrator=True)
    async def desvincular(interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        cid = str(canal.id)
        if cid not in PAREJAS_CANALES:
            await interaction.followup.send(f"ℹ️ {canal.mention} no está vinculado.", ephemeral=True)
            return

        destino_id = str(PAREJAS_CANALES[cid].get("destino", ""))
        del PAREJAS_CANALES[cid]
        if destino_id in PAREJAS_CANALES:
            del PAREJAS_CANALES[destino_id]

        guardar_config(PAREJAS_CANALES)
        destino_mention = f"<#{destino_id}>" if destino_id else "su pareja"
        await interaction.followup.send(
            f"🗑️ Desvinculados {canal.mention} y {destino_mention}.",
            ephemeral=True
        )

    @tree.command(name="vinculados", description="Muestra las parejas de canales vinculadas")
    @app_commands.checks.has_permissions(administrator=True)
    async def vinculados(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not PAREJAS_CANALES:
            await interaction.followup.send("📭 No hay canales vinculados actualmente.", ephemeral=True)
            return

        vistos = set()
        lineas = []
        for origen_str, data in PAREJAS_CANALES.items():
            destino_str = str(data.get("destino", ""))
            par = tuple(sorted([origen_str, destino_str]))
            if par in vistos:
                continue
            vistos.add(par)
            if data.get("idioma") == "en":
                lineas.append(f"• <#{origen_str}> (ES) ⟷ <#{destino_str}> (EN)")
            else:
                lineas.append(f"• <#{destino_str}> (ES) ⟷ <#{origen_str}> (EN)")

        await interaction.followup.send("**Canales vinculados:**\n" + "\n".join(lineas), ephemeral=True)

    async def on_message_vinculaciones(message: discord.Message):
        if message.author.bot or message.webhook_id is not None or not message.content:
            return

        canal_id = str(message.channel.id)
        if canal_id in PAREJAS_CANALES:
            info = PAREJAS_CANALES[canal_id]
            destino = client.get_channel(info["destino"])
            idioma = info["idioma"]

            if destino:
                try:
                    loop = asyncio.get_running_loop()
                    traducido = await loop.run_in_executor(None, traducir_texto, message.content, idioma)
                    if traducido:
                        await enviar_webhook(destino, message, traducido)
                    else:
                        print("Traducción omitida: los motores gratuitos no respondieron.")
                except Exception as e:
                    print(f"Error procesando mensaje: {e}")

    client.add_listener(on_message_vinculaciones, "on_message")
