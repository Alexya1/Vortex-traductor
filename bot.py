import os
import sys
import discord
from discord import app_commands
from vinculaciones import registrar_vinculaciones

sys.stdout.reconfigure(line_buffering=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

registrar_vinculaciones(client, tree)


@client.event
async def on_ready():
    print(f"BOT LOGUEADO CORRECTAMENTE COMO: {client.user}")
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
