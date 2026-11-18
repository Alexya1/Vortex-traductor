@tree.command(name="vincular", description="Vincula dos canales por su ID exacto")
@app_commands.describe(id_es="ID del canal de español", id_en="ID del canal de inglés")
@app_commands.checks.has_permissions(administrator=True)
async def vincular(interaction: discord.Interaction, id_es: str, id_en: str):
    await interaction.response.defer(ephemeral=True)
    
    global PAREJAS_CANALES
    # Limpiamos los IDs por si copian menciones con <#!>
    c_es_id = id_es.strip().replace("<#", "").replace(">", "")
    c_en_id = id_en.strip().replace("<#", "").replace(">", "")

    PAREJAS_CANALES[c_es_id] = {"destino": int(c_en_id), "idioma": "en"}
    PAREJAS_CANALES[c_en_id] = {"destino": int(c_es_id), "idioma": "es"}
    guardar_config(PAREJAS_CANALES)
    
    await interaction.followup.send(f"✅ ¡Vinculación exitosa por ID!\n• <#{c_es_id}> ⟷ <#{c_en_id}>", ephemeral=True)
