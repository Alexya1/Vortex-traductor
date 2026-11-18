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

# 2. CONFIGURACIÓN DE CANALES Y PERSISTENCIA
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

# 3. INICIALIZACIÓN
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
        print(f"✅ Traducción enviada con éxito a {canal_destino.name}")
    except Exception as e:
        print(f"❌ Error al enviar webhook en {canal_destino.name}: {e}")

@client.event
async def on_ready():
    await tree.sync()
    print(f'¡Bot conectado exitosamente como {client.user} y comandos sincronizados!')

# COMANDOS SLASH
@tree.command(name="vincular", description="Vincula dos canales para traducción bidireccional")
@app_commands.describe(canal_es="Canal de español", canal_en="Canal de inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, canal_es: discord.TextChannel, canal_en: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    
    global PAREJAS_CANALES
    PAREJAS_CANALES[str(canal_es.id)] = {"destino": canal_en.id, "idioma": "en"}
    PAREJAS_CANALES[str(canal_en.id)] = {"destino": canal_es.id, "idioma": "es"}
    guardar_config(PAREJAS_CANALES)
    
    await interaction.followup.send(f"✅ ¡Listo! Todo lo que escriban en {canal_es.mention} saldrá en inglés en {canal_en.mention}, y viceversa.", ephemeral=True)

@tree.command(name="desvincular", description="Desvincula un canal de traducción")
@app_commands.describe(canal="Canal a desvincular")
@app_commands.checks.has_permissions(administrator=True)
async def desvincular(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    
    global PAREJAS_CANALES
    canal_id_str = str(canal.id)
    if canal_id_str in PAREJAS_CANALES:
        otro_id = PAREJAS_CANALES.pop(canal_id_str)["destino"]
        PAREJAS_CANALES.pop(str(otro_id), None)
        guardar_config(PAREJAS_CANALES)
        await interaction.followup.send(f"🗑️ Se desvinculó el canal {canal.mention}.", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ Ese canal no estaba vinculado a nada.", ephemeral=True)

@tree.command(name="vinculados", description="Muestra la lista de canales actualmente vinculados")
async def vinculados(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    if not PAREJAS_CANALES:
        await interaction.followup.send("ℹ️ No hay canales vinculados en este momento.", ephemeral=True)
        return

    # Para evitar repetir parejas (ya que guardamos ida y vuelta), filtramos
    vistos = set()
    texto_lista = "📋 **Canales de traducción activos:**\n"
    
    for canal_id_str, info in PAREJAS_CANALES.items():
        if canal_id_str in vistos:
            continue
        
        destino_id = info["destino"]
        vistos.add(str(destino_id))
        vistos.add(canal_id_str)
        
        canal_1 = client.get_channel(int(canal_id_str))
        canal_2 = client.get_channel(int(destino_id))
        
        c1_m = canal_1.mention if canal_1 else f"<#{canal_id_str}>"
        c2_m = canal_2.mention if canal_2 else f"<#{destino_id}>"
        
        texto_lista.append(f"• {c1_m} ⟷ {c2_m}\n" if hasattr(texto_lista, 'append') else f"• {c1_m} ⟷ {c2_m}\n")
        # Si prefieres formato plano acumulativo:
        # texto_lista += f"• {c1_m} ⟷ {c2_m}\n"

    # Corrección limpia para concatenar strings
    resultado = "📋 **Canales de traducción activos:**\n"
    vistos_limpios = set()
    for canal_id_str, info in PAREJAS_CANALES.items():
        if canal_id_str in vistos_limpios:
            continue
        destino_id = info["destino"]
        vistos_limpios.add(str(destino_id))
        vistos_limpios.add(canal_id_str)
        
        c1 = client.get_channel(int(canal_id_str))
        c2 = client.get_channel(int(destino_id))
        m1 = c1.mention if c1 else f"<#{canal_id_str}>"
        m2 = c2.mention if c2 else f"<#{destino_id}>"
        resultado += f"• {m1} ⟷ {m2}\n"

    await interaction.followup.send(resultado, ephemeral=True)

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
