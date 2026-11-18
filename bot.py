# COMANDO SLASH: /vincular
@tree.command(name="vincular", description="Vincula dos canales para traducción bidireccional")
@app_commands.describe(canal_es="Canal de español", canal_en="Canal de inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, canal_es: discord.TextChannel, canal_en: discord.TextChannel):
    # Primero le decimos a Discord que estamos procesando para evitar el error de tiempo de espera
    await interaction.response.defer(ephemeral=True)
    
    global PAREJAS_CANALES
    PAREJAS_CANALES[str(canal_es.id)] = {"destino": canal_en.id, "idioma": "en"}
    PAREJAS_CANALES[str(canal_en.id)] = {"destino": canal_es.id, "idioma": "es"}
    guardar_config(PAREJAS_CANALES)
    
    # Enviamos el mensaje final ya procesado
    await interaction.followup.send(f"✅ ¡Listo! Todo lo que escriban en {canal_es.mention} saldrá en inglés en {canal_en.mention}, y viceversa.", ephemeral=True)

# COMANDO SLASH: /desvincular
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
