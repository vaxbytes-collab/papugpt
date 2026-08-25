import os
import urllib.parse
import urllib.request
from threading import Thread
import discord
from dotenv import load_dotenv
from flask import Flask
import google.genai as genai
from google.genai import types

load_dotenv()

# --- 1. MINI SERVIDOR PARA UPTIMEROBOT ---
app = Flask("")


@app.route("/")
def home():
    return "papugpt anda activo 24/7 papu :v"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.start()


# --- 2. CONFIGURACIÓN DE DISCORD Y GEMINI ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

PERSONALIDAD_PAPUGPT = (
    "eres papugpt, un bot gracioso, cursi, humilde y desenfadado de discord."
    " hablas como morro shitposter de la grasa."
    " REGLAS DE ESTILO:"
    " 1. escribe todo en minusculas."
    " 2. usa frases como 'papu :v', 'jajajaja xd mamu me tienes de payaso :c',"
    " 'miau miau otra vez? :3', 'when', 'but'."
    " 3. tus respuestas deben ser breves, de 1 a 3 lineas."
    " 4. puedes hablar de absolutamente cualquier tema que te pregunten sin limitaciones."
    " 5. si te mandan una imagen, opina o responde sobre ella de forma graciosa."
)

CONFIGURACION_SIN_LIMITES = types.GenerateContentConfig(
    system_instruction=PERSONALIDAD_PAPUGPT,
    temperature=0.8,
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ],
)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
bot_discord = discord.Client(intents=intents)


@bot_discord.event
async def on_ready():
    print(f"papugpt ({bot_discord.user}) ya anda con ojos activos :v")


# FUNCIÓN AUXILIAR PARA PROCESAR EL HISTORIAL E IMÁGENES
async def construir_historial(channel, bot_id, message_actual):
    historial = []
    async for msg in channel.history(limit=6):
        if msg.id == message_actual.id:
            # EN EL MENSAJE ACTUAL ADJUNTAMOS LAS IMÁGENES
            partes = []
            if message_actual.attachments:
                for attachment in message_actual.attachments:
                    if attachment.content_type and attachment.content_type.startswith("image/"):
                        datos_img = await attachment.read()
                        partes.append(
                            types.Part.from_bytes(
                                data=datos_img,
                                mime_type=attachment.content_type,
                            )
                        )
            
            txt_limpio = message_actual.content.replace(f"<@{bot_id}>", "").strip()
            if txt_limpio:
                partes.append(types.Part.from_text(text=txt_limpio))
            elif not partes:
                partes.append(types.Part.from_text(text="[el usuario te mando una foto sin texto]"))
                
            historial.append(types.Content(role="user", parts=partes))
        else:
            # MENSAJES ANTERIORES DEL HISTORIAL (SOLO TEXTO PARA NO LEER DE MÁS)
            if msg.content:
                autor = "model" if msg.author.id == bot_id else "user"
                txt_limpio = msg.content.replace(f"<@{bot_id}>", "").strip()
                if txt_limpio:
                    historial.append(
                        types.Content(
                            role=autor,
                            parts=[types.Part.from_text(text=txt_limpio)],
                        )
                    )

    historial.reverse()

    # EVITAMOS EL ERROR 400 BORRANDO MODEL DEL FINAL
    while historial and historial[-1].role == "model":
        historial.pop()

    return historial


@bot_discord.event
async def on_message(message):
    if message.author.id == bot_discord.user.id:
        return

    # --- 3. MODO MENSAJES PRIVADOS (MD / DM) ---
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            try:
                historial = await construir_historial(message.channel, bot_discord.user.id, message)

                if not historial:
                    await message.channel.send("miau miau que dijiste papu :v")
                    return

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=historial,
                    config=CONFIGURACION_SIN_LIMITES,
                )

                if response.text:
                    await message.channel.send(response.text)
                else:
                    await message.channel.send("miau miau que bonita foto papu :v")

            except Exception as e:
                print(f"ERROR EN MD: {e}")
                await message.channel.send("chale me tienes de payaso :'v error en md")
        return

    # --- 4. MODO CANALES DEL SERVIDOR ---
    mencionado = bot_discord.user.mentioned_in(message)
    es_respuesta_a_bot = False
    if message.reference and message.reference.resolved:
        msg_referenciado = message.reference.resolved
        if msg_referenciado.author.id == bot_discord.user.id:
            es_respuesta_a_bot = True

    if mencionado or es_respuesta_a_bot:
        async with message.channel.typing():
            try:
                texto_usuario = message.content.replace(f"<@{bot_discord.user.id}>", "").strip()
                texto_lower = texto_usuario.lower()

                # GENERADOR DE IMÁGENES (SI TE PIDE DIBUJAR)
                palabras_clave = [
                    "dibuja",
                    "dibujame",
                    "genera una imagen",
                    "crea una imagen",
                    "haz una imagen",
                    "haz un dibujo",
                    "imagen de",
                    "generame",
                ]
                quiere_imagen = any(p in texto_lower for p in palabras_clave)

                if quiere_imagen and not message.attachments:
                    await message.reply("dale papu, ahorita te la hago")

                    try:
                        prompt_encoded = urllib.parse.quote(texto_usuario)
                        url_imagen = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&nologo=true"

                        headers = {
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                                " AppleWebKit/537.36 (KHTML, like Gecko)"
                                " Chrome/120.0.0.0 Safari/537.36"
                            )
                        }
                        req = urllib.request.Request(url_imagen, headers=headers)

                        with urllib.request.urlopen(req, timeout=15) as response:
                            image_bytes = response.read()

                        with open("temp_papu.jpg", "wb") as f:
                            f.write(image_bytes)

                        file = discord.File("temp_papu.jpg", filename="papubot_imagen.jpg")
                        await message.reply(
                            content="aqui tienes tu dibujo papu :v", file=file
                        )

                        if os.path.exists("temp_papu.jpg"):
                            os.remove("temp_papu.jpg")
                        return

                    except Exception as img_err:
                        print(f"Error generando imagen: {img_err}")
                        await message.reply(
                            "chale papu :'v no pude hacer el dibujo, intentalo mas alrato"
                        )
                        return

                # SI TE MANDA FOTO O TEXTO, PROCESAR CON GEMINI
                historial = await construir_historial(message.channel, bot_discord.user.id, message)

                if not historial:
                    await message.reply("miau miau que dijiste papu :v")
                    return

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=historial,
                    config=CONFIGURACION_SIN_LIMITES,
                )

                if response.text:
                    await message.reply(response.text)
                else:
                    await message.reply("miau miau que dijiste papu :v")

            except Exception as e:
                print(f"ERROR: {e}")
                await message.reply(f"chale me tienes de payaso :'v error: {e}")


# --- 5. ARRANCAR TODO ---
if __name__ == "__main__":
    keep_alive()
    bot_discord.run(DISCORD_TOKEN)