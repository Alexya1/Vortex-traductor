import io
import os
import re
import json
import asyncio
import urllib.parse
import urllib.request
import discord
from discord import app_commands

CONFIG_FILE = "canales_config.json"
BACKUP_CHANNEL_ID = 1518545714500735107
BACKUP_PREFIX = "VORTEX_VINCULOS_STATE:"

FULL_CUSTOM_EMOJI_RE = re.compile(r"<a?:([A-Za-z0-9_~]+):(\d+)>")
SHORT_EMOJI_RE = re.compile(r":([A-Za-z0-9_~]{2,32}):")


def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def guardar_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


PAREJAS_CANALES = cargar_config()
_MENSAJE_RESPALDO_ID: int | None = None

# Mapa: id_mensaje_original -> {"canal_id": int, "mensaje_id": int}
MENSAJES_ESPEJO: dict[int, dict[str, int]] = {}


def _registrar_espejo(origen_msg_id: int, destino_canal_id: int, destino_msg_id: int):
    MENSAJES_ESPEJO[origen_msg_id] = {
        "canal_id": destino_canal_id,
        "mensaje_id": destino_msg_id,
    }
    # Limitar el tamaño en memoria para no crecer indefinidamente
    if len(MENSAJES_ESPEJO) > 2000:
        clave_mas_vieja = next(iter(MENSAJES_ESPEJO))
        MENSAJES_ESPEJO.pop(clave_mas_vieja, None)


async def _obtener_canal_respaldo(client: discord.Client) -> discord.TextChannel | None:
    canal = client.get_channel(BACKUP_CHANNEL_ID)
    if not isinstance(canal, discord.TextChannel):
        try:
            canal = await client.fetch_channel(BACKUP_CHANNEL_ID)
        except Exception:
            canal = None
    return canal if isinstance(canal, discord.TextChannel) else None


async def _sincronizar_respaldo_canal(client: discord.Client):
    global PAREJAS_CANALES, _MENSAJE_RESPALDO_ID
    canal = await _obtener_canal_respaldo(client)
    if not canal:
        return

    try:
        async for msg in canal.history(limit=50):
            if msg.author == client.user and msg.content.startswith(BACKUP_PREFIX):
                _MENSAJE_RESPALDO_ID = msg.id
                raw = msg.content[len(BACKUP_PREFIX):].strip()
                datos = json.loads(raw)
                if isinstance(datos, dict) and datos and not PAREJAS_CANALES:
                    PAREJAS_CANALES = datos
                    guardar_config(PAREJAS_CANALES)
                    print(f"Vinculaciones restauradas automáticamente ({len(PAREJAS_CANALES)} canales).")
                break
    except Exception as e:
        print(f"Error leyendo respaldo de vinculaciones: {e}")


async def _guardar_respaldo_canal(client: discord.Client):
    global _MENSAJE_RESPALDO_ID
    canal = await _obtener_canal_respaldo(client)
    if not canal:
        return

    payload = BACKUP_PREFIX + json.dumps(PAREJAS_CANALES, separators=(",", ":"))
    if len(payload) > 1950:
        print("Advertencia: demasiadas vinculaciones para respaldo en un solo mensaje.")
        return

    try:
        if _MENSAJE_RESPALDO_ID is not None:
            try:
                msg = await canal.fetch_message(_MENSAJE_RESPALDO_ID)
                await msg.edit(content=payload)
                return
            except Exception:
                _MENSAJE_RESPALDO_ID = None

        nuevo_msg = await canal.send(payload)
        _MENSAJE_RESPALDO_ID = nuevo_msg.id
    except Exception as e:
        print(f"Error guardando respaldo de vinculaciones: {e}")


def traducir_google_gtx(texto, source_lang, target_lang):
    q = urllib.parse.quote(texto)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data and data[0]:
            return "".join(part[0] for part in data[0] if part and part[0])
    return None


def traducir_mymemory(texto, source_lang, target_lang):
    q = urllib.parse.quote(texto)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair={source_lang}|{target_lang}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        trad = data.get("responseData", {}).get("translatedText", "")
        if trad and "MYMEMORY WARNING" not in trad.upper():
            return trad
    return None


def _resolver_emoji_en_cliente(client: discord.Client | None, raw_token: str) -> str:
    if FULL_CUSTOM_EMOJI_RE.fullmatch(raw_token):
        return raw_token

    m_short = SHORT_EMOJI_RE.fullmatch(raw_token)
    if m_short and client is not None:
        nombre = m_short.group(1)
        emoji_obj = discord.utils.get(client.emojis, name=nombre)
        if emoji_obj is not None:
            return str(emoji_obj)

    return raw_token


def _proteger_emojis(texto: str) -> tuple[str, dict[str, str]]:
    mapa: dict[str, str] = {}
    texto_protegido = texto
    contador = 0

    for match in FULL_CUSTOM_EMOJI_RE.finditer(texto):
        original = match.group(0)
        token = f"EMJTOKEN{contador}END"
        contador += 1
        mapa[token] = original
        texto_protegido = texto_protegido.replace(original, token, 1)

    for match in SHORT_EMOJI_RE.finditer(texto_protegido):
        original = match.group(0)
        token = f"EMJTOKEN{contador}END"
        contador += 1
        mapa[token] = original
        texto_protegido = texto_protegido.replace(original, token, 1)

    return texto_protegido, mapa


def _restaurar_emojis(client: discord.Client | None, texto_traducido: str, mapa: dict[str, str]) -> str:
    if not mapa:
        return texto_traducido

    resultado = texto_traducido
    for token, raw_emoji in mapa.items():
        emoji_final = _resolver_emoji_en_cliente(client, raw_emoji)
        patron = re.compile(re.escape(token), re.IGNORECASE)
        resultado = patron.sub(emoji_final, resultado)
    return resultado


def traducir_texto(texto, target_lang, client: discord.Client | None = None):
    target = "en" if target_lang.lower() == "en" else "es"
    source = "es" if target == "en" else "en"

    texto_limpio, mapa_emojis = _proteger_emojis(texto)
    if not texto_limpio.strip():
        if not mapa_emojis:
            return None
        resueltos = [_resolver_emoji_en_cliente(client, val) for val in mapa_emojis.values()]
        return " ".join(resueltos)

    for motor, fn in (("Google GTX", traducir_google_gtx), ("MyMemory", traducir_mymemory)):
        try:
            resultado = fn(texto_limpio, source, target)
            if resultado and resultado.strip():
                return _restaurar_emojis(client, resultado.strip(), mapa_emojis).strip()
        except Exception as e:
            print(f"Fallo en {motor}: {e}")
    return None


def _descargar_url_sync(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


async def _preparar_archivos_y_stickers(mensaje: discord.Message) -> tuple[list[discord.File], list[str]]:
    archivos: list[discord.File] = []
    notas_extra: list[str] = []

    for att in mensaje.attachments:
        try:
            data = await asyncio.wait_for(att.read(), timeout=15)
            archivos.append(
                discord.File(
                    fp=io.BytesIO(data),
                    filename=att.filename,
                    spoiler=att.is_spoiler(),
                )
            )
        except Exception as e:
            print(f"Error descargando adjunto {att.filename}: {e}")

    loop = asyncio.get_running_loop()
    for sticker in mensaje.stickers:
        try:
            url = getattr(sticker, "url", None)
            if url and not url.endswith(".json"):
                data = await loop.run_in_executor(None, _descargar_url_sync, url)
                if data:
                    ext = ".png"
                    if ".apng" in url:
                        ext = ".apng"
                    elif ".webp" in url:
                        ext = ".webp"
                    elif ".gif" in url:
                        ext = ".gif"
                    nombre = f"sticker-{sticker.name or sticker.id}{ext}".replace(" ", "_")
                    archivos.append(discord.File(fp=io.BytesIO(data), filename=nombre))
                    continue
            notas_extra.append(f"[Sticker: {sticker.name}]")
        except Exception as e:
            print(f"Error descargando sticker {sticker.name}: {e}")
            notas_extra.append(f"[Sticker: {sticker.name}]")

    return archivos, notas_extra


async def enviar_webhook(canal_destino, mensaje, texto_traducido: str):
    try:
        webhooks = await canal_destino.webhooks()
        webhook = discord.utils.get(webhooks, name="TraductorEspejo")
        if webhook is None:
            webhook = await canal_destino.create_webhook(name="TraductorEspejo")

        archivos, notas_extra = await _preparar_archivos_y_stickers(mensaje)
        partes_texto = []
        if texto_traducido and texto_traducido.strip():
            partes_texto.append(texto_traducido.strip())
        if notas_extra:
            partes_texto.append(" ".join(notas_extra))

        contenido = "\n".join(partes_texto) if partes_texto else None

        if not contenido and not archivos:
            print("Mensaje sin contenido traducible, adjuntos ni stickers para reenviar.")
            return

        kwargs = {
            "username": mensaje.author.display_name,
            "avatar_url": mensaje.author.display_avatar.url,
            "wait": True,
        }
        if contenido:
            kwargs["content"] = contenido
        if archivos:
            kwargs["files"] = archivos

        msg_enviado = await webhook.send(**kwargs)
        if msg_enviado is not None:
            _registrar_espejo(mensaje.id, canal_destino.id, msg_enviado.id)
        print(f"WEBHOOK ENVIADO A #{canal_destino.name} (archivos: {len(archivos)})")
    except discord.Forbidden:
        print(f"ERROR EN WEBHOOK: Sin permisos para gestionar/enviar webhooks en #{canal_destino.name}.")
    except Exception as e:
        print(f"ERROR EN WEBHOOK: {e}")


def registrar_vinculaciones(
    client: discord.Client,
    tree: app_commands.CommandTree,
    handlers_on_message: list,
    on_ready_callbacks: list | None = None,
    handlers_on_message_delete: list | None = None,
):
    @tree.command(name="vincular", description="Vincula dos canales (español e inglés) de forma bidireccional")
    @app_commands.describe(canal_es="Canal en español", canal_en="Canal en inglés")
    @app_commands.checks.has_permissions(administrator=True)
    async def vincular(
        interaction: discord.Interaction,
        canal_es: discord.TextChannel,
        canal_en: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)
        if canal_es.id == canal_en.id:
            await interaction.followup.send("⚠️ Debes elegir dos canales distintos.", ephemeral=True)
            return

        PAREJAS_CANALES[str(canal_es.id)] = {"destino": canal_en.id, "idioma": "en"}
        PAREJAS_CANALES[str(canal_en.id)] = {"destino": canal_es.id, "idioma": "es"}
        guardar_config(PAREJAS_CANALES)
        await _guardar_respaldo_canal(client)

        await interaction.followup.send(
            f"✅ Vinculados {canal_es.mention} ⟷ {canal_en.mention} bidireccionalmente.",
            ephemeral=True
        )

    @tree.command(name="desvincular", description="Elimina la vinculación de traducción de un canal")
    @app_commands.describe(canal="Cualquiera de los dos canales vinculados")
    @app_commands.checks.has_permissions(administrator=True)
    async def desvincular(interaction: discord.Interaction, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        cid = str(canal.id)
        if cid not in PAREJAS_CANALES:
            await interaction.followup.send(f"ℹ️ {canal.mention} no está vinculado.", ephemeral=True)
            return

        destino_id = str(PAREJAS_CANALES[cid].get("destino", ""))
        del PAREJAS_CANALES[cid]
        if destino_id in PAREJAS_CANALES:
            del PAREJAS_CANALES[destino_id]

        guardar_config(PAREJAS_CANALES)
        await _guardar_respaldo_canal(client)
        destino_mention = f"<#{destino_id}>" if destino_id else "su pareja"
        await interaction.followup.send(
            f"🗑️ Desvinculados {canal.mention} y {destino_mention}.",
            ephemeral=True
        )

    @tree.command(name="vinculados", description="Muestra las parejas de canales vinculadas")
    @app_commands.checks.has_permissions(administrator=True)
    async def vinculados(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not PAREJAS_CANALES:
            await interaction.followup.send("📭 No hay canales vinculados actualmente.", ephemeral=True)
            return

        vistos = set()
        lineas = []
        for origen_str, data in PAREJAS_CANALES.items():
            destino_str = str(data.get("destino", ""))
            par = tuple(sorted([origen_str, destino_str]))
            if par in vistos:
                continue
            vistos.add(par)
            if data.get("idioma") == "en":
                lineas.append(f"• <#{origen_str}> (ES) ⟷ <#{destino_str}> (EN)")
            else:
                lineas.append(f"• <#{destino_str}> (ES) ⟷ <#{origen_str}> (EN)")

        await interaction.followup.send("**Canales vinculados:**\n" + "\n".join(lineas), ephemeral=True)

    async def on_message_vinculaciones(message: discord.Message):
        if message.author.bot or message.webhook_id is not None:
            return
        if not message.content and not message.attachments and not message.stickers:
            return

        canal_id = str(message.channel.id)
        if canal_id in PAREJAS_CANALES:
            info = PAREJAS_CANALES[canal_id]
            destino = client.get_channel(info["destino"])
            idioma = info["idioma"]

            if destino:
                try:
                    traducido = ""
                    if message.content and message.content.strip():
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(None, traducir_texto, message.content, idioma, client)
                        if res:
                            traducido = res
                        else:
                            print("Traducción omitida: los motores gratuitos no respondieron.")

                    if traducido or message.attachments or message.stickers:
                        await enviar_webhook(destino, message, traducido)
                except Exception as e:
                    print(f"Error procesando mensaje: {e}")

    async def on_message_delete_vinculaciones(message: discord.Message):
        ref = MENSAJES_ESPEJO.pop(message.id, None)
        if not ref:
            return

        destino_canal = client.get_channel(ref["canal_id"])
        if not isinstance(destino_canal, discord.TextChannel):
            try:
                fetched = await client.fetch_channel(ref["canal_id"])
                destino_canal = fetched if isinstance(fetched, discord.TextChannel) else None
            except Exception:
                destino_canal = None

        if not isinstance(destino_canal, discord.TextChannel):
            return

        try:
            msg_espejo = await destino_canal.fetch_message(ref["mensaje_id"])
            await msg_espejo.delete()
            print(f"Mensaje espejo eliminado en #{destino_canal.name}.")
        except discord.NotFound:
            pass
        except discord.Forbidden:
            print(f"Sin permisos para borrar mensaje espejo en #{destino_canal.name}.")
        except Exception as e:
            print(f"Error borrando mensaje espejo: {e}")

    handlers_on_message.append(on_message_vinculaciones)

    if handlers_on_message_delete is not None:
        handlers_on_message_delete.append(on_message_delete_vinculaciones)

    if on_ready_callbacks is not None:
        async def _cargar_respaldo():
            await _sincronizar_respaldo_canal(client)
        on_ready_callbacks.append(_cargar_respaldo)
