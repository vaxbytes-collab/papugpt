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

# --- 1. SERVIDOR FLASK PARA UPTIMEROBOT ---
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
    "eres papugpt, el vato cotorro, alegre y grasoso de discord. hablas siempre en minusculas, sin acentos, usando ':v', 'papu', 'elfa', 'when' y 'but'."
    " tu vibra es de un compa buena onda, divertido y desenfadado. te gusta cotorrear de memes, juegos y platicar de chill."
    " respuestas breves, graciosas y naturales de 1 a 3 lineas maximo."
)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
bot_discord = discord.Client(intents=intents)


@bot_discord.event
async def on_ready():
    print(f"papugpt ({bot_discord.user}) ya anda activo y de chill :v")
    await bot_discord.change_presence(
        activity=discord.Game(name="tirando momos de chill :v")
    )


@bot_discord.event
async def on_message(message):
    if message.author.id == bot_discord.user.id:
        return

    # --- 3. MODO MENSAJES PRIVADOS (MD / DM) DE CHILL ---
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            try:
                texto_usuario = message.content.strip()

                partes_mensaje = []
                if message.attachments:
                    for attachment in message.attachments:
                        if (
                            attachment.content_type
                            and attachment.content_type.startswith("image/")
                        ):
                            datos_imagen = await attachment.read()
                            partes_mensaje.append(
                                types.Part.from_bytes(
                                    data=datos_imagen,
                                    mime_type=attachment.content_type,
                                )
                            )

                if texto_usuario:
                    partes_mensaje.append(
                        types.Part.from_text(text=texto_usuario)
                    )

                if not partes_mensaje:
                    partes_mensaje.append(
                        types.Part.from_text(
                            text="[el usuario no envio texto ni imagen]"
                        )
                    )

                config = types.GenerateContentConfig(
                    system_instruction=PERSONALIDAD_PAPUGPT,
                    temperature=0.8,
                )

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=partes_mensaje,
                    config=config,
                )

                if response.text:
                    await message.channel.send(response.text)
                else:
                    await message.channel.send("que onda papu, que cuentas :v")

            except Exception as e:
                print(f"ERROR EN MD: {e}")
                await message.channel.send(
                    "chale me dio un lag en la ram viejo :'v"
                )
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
                texto_usuario = (
                    message.content.replace(f"<@{bot_discord.user.id}>", "")
                    .strip()
                )
                texto_lower = texto_usuario.lower()

                # GENERADOR DE IMÁGENES
                palabras_clave = [
                    "dibuja",
                    "dibujame",
                    "genera una imagen",
                    "crea una imagen",
                    "haz una imagen",
                    "haz un dibujo",
                    "imagen de",
                ]
                quiere_imagen = any(p in texto_lower for p in palabras_clave)

                if quiere_imagen:
                    await message.reply(
                        "arriba las manos papu, ahi te va el dibujo :v"
                    )

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
                        req = urllib.request.Request(
                            url_imagen, headers=headers
                        )

                        with urllib.request.urlopen(req, timeout=15) as response:
                            image_bytes = response.read()

                        with open("temp_papu.jpg", "wb") as f:
                            f.write(image_bytes)

                        file = discord.File(
                            "temp_papu.jpg", filename="papubot_imagen.jpg"
                        )
                        await message.reply(
                            content="aqui tienes tu momo dibujado papu 😎:",
                            file=file,
                        )

                        if os.path.exists("temp_papu.jpg"):
                            os.remove("temp_papu.jpg")
                        return

                    except Exception as img_err:
                        print(f"Error generando imagen: {img_err}")
                        await message.reply(
                            "chale... no se pudo hacer la foto papu :'v"
                        )
                        return

                # PROCESAMIENTO DE TEXTO E IMAGENE CON GEMINI
                partes_mensaje = []
                if message.attachments:
                    for attachment in message.attachments:
                        if (
                            attachment.content_type
                            and attachment.content_type.startswith("image/")
                        ):
                            datos_imagen = await attachment.read()
                            partes_mensaje.append(
                                types.Part.from_bytes(
                                    data=datos_imagen,
                                    mime_type=attachment.content_type,
                                )
                            )

                if texto_usuario:
                    partes_mensaje.append(
                        types.Part.from_text(text=texto_usuario)
                    )

                if not partes_mensaje:
                    partes_mensaje.append(
                        types.Part.from_text(
                            text="[el usuario no envio texto ni imagen]"
                        )
                    )

                config = types.GenerateContentConfig(
                    system_instruction=PERSONALIDAD_PAPUGPT,
                    temperature=0.8,
                )

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=partes_mensaje,
                    config=config,
                )

                if response.text:
                    await message.reply(response.text)
                else:
                    await message.reply("que onda papu :v")

            except Exception as e:
                print(f"ERROR: {e}")
                await message.reply(
                    f"chale me dio un lag en la ram :'v error: {e}"
                )


# --- 5. ARRANCAR EL BOT ---
if __name__ == "__main__":
    keep_alive()
    bot_discord.run(DISCORD_TOKEN)