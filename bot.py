import os
import json
import threading
import asyncio
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from googletrans import Translator

sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), SimpleHandler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

CONFIG_FILE = "canales_config.json"

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def guardar_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

PAREJAS_CANALES = cargar_config()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
translator = Translator()

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
    await tree.sync()

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
    
    await interaction.followup.send(f"✅ ¡Vinculados <#{c_es}> ⟷ <#{c_en}>!", ephemeral=True)

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
                # Traducción segura con reintento interno
                loop = asyncio.get_running_loop()
                resultado = await loop.run_in_executor(
                    None, 
                    lambda: translator.translate(message.content, dest=idioma)
                )
                if resultado and resultado.text:
                    await enviar_webhook(destino, message, resultado.text)
            except Exception as e:
                print(f"Error crítico en traducción: {e}")

token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
