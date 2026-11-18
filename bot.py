import os
import json
import threading
import asyncio
import sys
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands

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

def traducir_texto(texto, target_lang):
    langpair = f"autofrom|{target_lang}"
    encoded_text = urllib.parse.quote(texto)
    url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={langpair}"
    
    # Sistema de reintentos automáticos ante errores 429 o de red
    for intento in range(3):
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                translated = res_data.get("responseData", {}).get("translatedText", "")
                if translated:
                    return translated
        except Exception as e:
            print(f"Intento {intento + 1} fallido (Error: {e}). Reintentando...")
            import time
            time.sleep(1.5 * (intento + 1)) # Espera progresiva
            
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
                await asyncio.sleep(0.4)
                loop = asyncio.get_running_loop()
                traducido = await loop.run_in_executor(None, traducir_texto, message.content, idioma)
                if traducido:
                    await enviar_webhook(destino, message, traducido)
                else:
                    print("No se pudo traducir el mensaje tras los reintentos.")
            except Exception as e:
                print(f"Error procesando mensaje: {e}")

token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("ERROR CRÍTICO: Falta DISCORD_TOKEN en las variables de entorno.")
