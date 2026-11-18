@client.event
async def on_ready():
    await tree.sync()
    print(f'🚨 ID DEL BOT CONECTADO EN RENDER: {client.user.id}')
    print(f'🚨 NOMBRE DEL BOT: {client.user.name}')
