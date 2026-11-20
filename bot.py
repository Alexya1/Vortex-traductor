import os
import json
import asyncio
import sys
import urllib.parse
import urllib.request
import discord
from discord import app_commands

sys.stdout.reconfigure(line_buffering=True)

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

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

@client.event
async def on_ready():
    print(f"BOT LOGUEADO CORRECTAMENTE COMO: {client.user}")
    try:
        await tree.sync()
        print("Comandos barra sincronizados.")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")

@tree.command(name="vincular", description="Vincula dos canales por su ID")
@app_commands.describe(id_es="ID canal español", id_en="ID canal inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, id_es: str, id_en: str):
    await interaction.response.defer(ephemeral=True)
    global PAREJAS_CANALES
    c_es = id_es.strip().replace("<#", "").replace(">", "")
    c_en = id_en.strip().replace("<#", "").replace(">", "")

    PAREJAS_CANALES[c_es] = {"destino": int(c_en), "idioma": "en"}
    PAREJAS_CANALES[c_en] = {"destino": int(c_es), "idioma": "es"}
    guardar_config(PAREJAS_CANALES)

    await interaction.followup.send(f"✅ ¡Vinculados <#{c_es}> ⟷ <#{c_en}> bidireccionalmente!", ephemeral=True)

@client.event
async def on_message(message):
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

token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("ERROR CRÍTICO: Falta DISCORD_TOKEN en las variables de entorno.")
