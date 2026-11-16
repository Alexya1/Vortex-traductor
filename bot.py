import os
import discord
from deep_translator import GoogleTranslator

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Tus 5 parejas de canales configuradas (Español <-> Inglés)
PAREJAS_CANALES = {
    1514521167694659687: 1571787294799691907,  # General
    1557565723943895040: 1571786940293058670,  # Informacion
    1557573531909361714: 1571787068508737676,  # Reglas
    1556507804167045150: 1571787236079570957,  # Crear Ticket
    1557576022289944657: 1571787322016530502   # Referencias
}

ES_A_EN = PAREJAS_CANALES
EN_A_ES = {v: k for k, v in PAREJAS_CANALES.items()}

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
    print(f'Bot conectado exitosamente como {client.user}')

@client.event
async def on_message(message):
    if message.author.bot or message.webhook_id is not None or not message.content:
        return

    canal_id = message.channel.id

    if canal_id in ES_A_EN:
        destino = client.get_channel(ES_A_EN[canal_id])
        if destino:
            traduccion = GoogleTranslator(source='es', target='en').translate(message.content)
            await enviar_webhook(destino, message, traduccion)

    elif canal_id in EN_A_ES:
        destino = client.get_channel(EN_A_ES[canal_id])
        if destino:
            traduccion = GoogleTranslator(source='en', target='es').translate(message.content)
            await enviar_webhook(destino, message, traduccion)

client.run(os.environ.get("DISCORD_TOKEN"))
