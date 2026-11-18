import os
import discord
from discord import app_commands
from deep_translator import GoogleTranslator
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Servidor web obligatorio para Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), SimpleHandler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f"=== EL BOT HA INICIADO: {client.user} ===")
    try:
        await tree.sync()
        print("=== COMANDOS SINCRONIZADOS ===")
    except Exception as e:
        print(f"Error sincronizando: {e}")

@tree.command(name="prueba", description="Comando de prueba rápido")
async def prueba(interaction: discord.Interaction):
    await interaction.response.send_message("¡El bot responde!", ephemeral=True)

@client.event
async def on_message(message):
    print(f">> MENSAJE DETECTADO EN CANAL {message.channel.id}: {message.content}")
    if message.author.bot:
        return

token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("ERROR CRÍTICO: No hay DISCORD_TOKEN configurado.")
