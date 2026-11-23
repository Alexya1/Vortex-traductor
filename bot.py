import os
import sys
import discord
from discord import app_commands
from vinculaciones import registrar_vinculaciones
from tickets_en import registrar_tickets_en

sys.stdout.reconfigure(line_buffering=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
handlers_on_message = []
handlers_on_message_delete = []
on_ready_callbacks = []

registrar_vinculaciones(
    client,
    tree,
    handlers_on_message,
    on_ready_callbacks,
    handlers_on_message_delete,
)
registrar_tickets_en(client, tree, on_ready_callbacks)


@client.event
async def on_message(message: discord.Message):
    for handler in handlers_on_message:
        await handler(message)


@client.event
async def on_message_delete(message: discord.Message):
    for handler in handlers_on_message_delete:
        await handler(message)


@client.event
async def on_ready():
    print(f"BOT LOGUEADO CORRECTAMENTE COMO: {client.user}")
    for cb in on_ready_callbacks:
        await cb()
    try:
        await tree.sync()
        print("Comandos barra sincronizados.")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")


token = os.environ.get("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("ERROR CRÍTICO: Falta DISCORD_TOKEN en las variables de entorno.")
