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
    HTTPServer(('0.0.0.0', port), SimpleHandler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 2. CONFIGURACIÓN Y PERSISTENCIA
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

# 3. CLIENTE Y COMANDOS
intents = discord.Intents.all()
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
        print(f"Error enviando webhook: {e}")

@client.event
async def on_ready():
    print(f"=== BOT CONECTADO: {client.user} ===")
    try:
        await tree.sync()
        print("=== COMANDOS SINCRONIZADOS ===")
    except Exception as e:
        print(f"Error sincronizando: {e}")

@tree.command(name="vincular", description="Vincula dos canales por su ID exacto")
@app_commands.describe(id_es="ID del canal de español", id_en="ID del canal de inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, id_es: str, id_en: str):
    await interaction.response.defer(ephemeral=True)
    global PAREJAS_CANALES
    c_es_id = id_es.strip().replace("<#", "").replace(">", "")
    c_en_id = id_en.strip().replace("<#", "").replace(">", "")

    PAREJAS_CANALES[c_es_id] = {"destino": int(c_en_id), "idioma": "en"}
    PAREJAS_CANALES[c_en_id] = {"destino": int(c_es_id), "idioma": "es"}
    guardar_config(PAREJAS_CANALES)
    
    await interaction.followup.send(f"✅ ¡Vinculación exitosa!\n• <#{c_es_id}> ⟷ <#{c_en_id}>", ephemeral=True)

@tree.command(name="vinculados", description="Muestra canales activos")
async def vinculados(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    global PAREJAS_CANALES
    PAREJAS_CANALES = cargar_config()
    
    if not PAREJAS_CANALES:
        await interaction.followup.send("ℹ️ No hay canales vinculados.", ephemeral=True)
        return

    resultado = "📋 **Canales activos:**\n"
    vistos = set()
    for cid, info in PAREJAS_CANALES.items():
        if cid in vistos: continue
        did = info["destino"]
        vistos.add(str(did))
        vistos.add(cid)
        c1, c2 = client.get_channel(int(cid)), client.get_channel(int(did))
        resultado += f"• {c1.mention if c1 else cid} ⟷ {c2.mention if c2 else did}\n"
    
    await interaction.followup.send(resultado, ephemeral=True)

@client.event
async def on_message(message):
    if message.author.bot or message.webhook_id is not None or not message.content:
        return

    canal_id_str = str(message.channel.id)
    if canal_id_str in PAREJAS_CANALES:
        info = PAREJAS_CANALES[canal_id_str]
        destino = client.get_channel(info["destino"])
        idioma = info["idioma"]
        
        if destino:
            try:
                traducido = GoogleTranslator(source='auto', target=idioma).translate(message.content)
                await enviar_webhook(destino, message, traducido)
            except Exception as ex:
                print(f"Error traduciendo: {ex}")

token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("ERROR: Falta DISCORD_TOKEN")
