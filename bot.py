import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from deep_translator import GoogleTranslator

# 1. SERVIDOR WEB FALSO (Para Render)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo y funcionando!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 2. CONFIGURACIÓN DE CANALES
CONFIG_FILE = "canales_config.json"

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def guardar_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

PAREJAS_CANALES = cargar_config()

# 3. CONFIGURACIÓN DEL BOT CON CLIENT Y COMMANDTREE ESTABLE
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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
    except Exception as e:
        print(f"Error al enviar webhook: {e}")

@client.event
async def on_ready():
    await tree.sync()
    print(f'¡Bot conectado exitosamente como {client.user} y comandos sincronizados!')

# COMANDO SLASH: /vincular
@tree.command(name="vincular", description="Vincula dos canales para traducción bidireccional")
@app_commands.describe(canal_es="Canal de español", canal_en="Canal de inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, canal_es: discord.TextChannel, canal_en: discord.TextChannel):
    global PAREJAS_CANALES
    PAREJAS_CANALES[str(canal_es.id)] = {"destino": canal_en.id, "idioma": "en"}
    PAREJAS_CANALES[str(canal_en.id)] = {"destino": canal_es.id, "idioma": "es"}
    guardar_config(PAREJAS_CANALES)
    await interaction.response.send_message(f"✅ ¡Listo! Todo lo que escriban en {canal_es.mention} saldrá en inglés en {canal_en.mention}, y viceversa.", ephemeral=True)

# COMANDO SLASH: /desvincular
@tree.command(name="desvincular", description="Desvincula un canal de traducción")
@app_commands.describe(canal="Canal a desvincular")
@app_commands.checks.has_permissions(administrator=True)
async def desvincular(interaction: discord.Interaction, canal: discord.TextChannel):
    global PAREJAS_CANALES
    canal_id_str = str(canal.id)
    if canal_id_str in PAREJAS_CANALES:
        otro_id = PAREJAS_CANALES.pop(canal_id_str)["destino"]
        PAREJAS_CANALES.pop(str(otro_id), None)
        guardar_config(PAREJAS_CANALES)
        await interaction.response.send_message(f"🗑️ Se desvinculó el canal {canal.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Ese canal no estaba vinculado a nada.", ephemeral=True)

@client.event
async def on_message(message):
    if message.author.bot or message.webhook_id is not None or not message.content:
        return

    canal_id_str = str(message.channel.id)
    if canal_id_str in PAREJAS_CANALES:
        info = PAREJAS_CANALES[canal_id_str]
        destino = client.get_channel(info["destino"])
        idioma_destino = info["idioma"]
        
        if destino:
            try:
                traduccion = GoogleTranslator(source='auto', target=idioma_destino).translate(message.content)
                await enviar_webhook(destino, message, traduccion)
            except Exception as e:
                print(f"Error traduciendo: {e}")

client.run(os.environ.get("DISCORD_TOKEN"))
