import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from deep_translator import GoogleTranslator

# Servidor web falso para que Render detecte un puerto abierto y no cierre el bot
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Iniciar el servidor web en un hilo secundario
threading.Thread(target=run_server, daemon=True).start()

# --- CONFIGURACIÓN DE TU BOT DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

PAREJAS_CANALES = {
    # Pon tus IDs aquí si usas fijos, o déjalo vacío
}

@client.event
async def on_ready():
    print(f'Bot conectado exitosamente como {client.user}')

client.run(os.environ.get("DISCORD_TOKEN"))
