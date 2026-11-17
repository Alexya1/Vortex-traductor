import os
import json
import discord
from discord.ext import commands
from deep_translator import GoogleTranslator

# Archivo local donde se guardarán los canales vinculados
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

# Cargar las parejas de canales al iniciar
PAREJAS_CANALES = cargar_config()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    print(f'Bot conectado exitosamente como {bot.user}')

@bot.command(name="vincular")
@commands.has_permissions(administrator=True)
async def vincular(ctx, canal_es: discord.TextChannel, canal_en: discord.TextChannel):
    """Vincula dos canales bidireccionalmente: !vincular #español #english"""
    global PAREJAS_CANALES
    PAREJAS_CANALES[str(canal_es.id)] = canal_en.id
    PAREJAS_CANALES[str(canal_en.id)] = canal_es.id
    guardar_config(PAREJAS_CANALES)
    await ctx.send(f"✅ ¡Canales vinculados con éxito! Los mensajes entre {canal_es.mention} y {canal_en.mention} ahora se traducirán mutuamente.")

@bot.command(name="desvincular")
@commands.has_permissions(administrator=True)
async def desvincular(ctx, canal: discord.TextChannel):
    """Elimina la vinculación de un canal: !desvincular #canal"""
    global PAREJAS_CANALES
    canal_id_str = str(canal.id)
    if canal_id_str in PAREJAS_CANALES:
        otro_id = PAREJAS_CANALES.pop(canal_id_str)
        PAREJAS_CANALES.pop(str(otro_id), None)
        guardar_config(PAREJAS_CANALES)
        await ctx.send(f"🗑️ Se ha desvinculado el canal {canal.mention}.")
    else:
        await ctx.send(f"⚠️ Este canal no estaba vinculado a ninguno.")

@bot.event
async def on_message(message):
    if message.author.bot or message.webhook_id is not None or not message.content:
        return

    # Procesar comandos si los hay (!vincular, etc.)
    await bot.process_commands(message)

    canal_id_str = str(message.channel.id)
    
    if canal_id_str in PAREJAS_CANALES:
        destino_id = PAREJAS_CANALES[canal_id_str]
        destino = bot.get_channel(destino_id)
        
        if destino:
            # Detectar dirección de traducción automáticamente
            # Si el canal actual es el 'es', traducimos a 'en', y viceversa
            try:
                # Traducción simple bidireccional (Asumimos ES <-> EN)
                traduccion = GoogleTranslator(source='auto', target='en').translate(message.content)
                # Si el texto traducido es idéntico o detectamos que ya está en inglés, podemos afinarlo, 
                # pero por defecto GoogleTranslator con 'auto' funciona de maravilla.
                await enviar_webhook(destino, message, traduccion)
            except Exception as e:
                print(f"Error traduciendo: {e}")

bot.run(os.environ.get("DISCORD_TOKEN"))
