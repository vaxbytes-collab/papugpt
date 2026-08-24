import os
from threading import Thread
import urllib.parse
import urllib.request
import discord
from dotenv import load_dotenv
from flask import Flask
import google.genai as genai
from google.genai import types

# CARGAMOS EL ARCHIVO .ENV (LOCAL EN TU COMPA)
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
    "eres papugpt, un bot gracioso, humilde y desenfadado de discord y un poco serio."
    " hablas como morro shitposter de la grasa."
    " REGLAS DE ESTILO:"
    " 1. escribe todo en minusculas."
    " 2. usa frases como 'papu :v', 'pinche meco',"
    " 'miau miau', 'when', 'but'."
    " 3. tus respuestas deben ser breves, de 1 a 3 lineas."
)

intents = discord.Intents.default()
intents.message_content = True
bot_discord = discord.Client(intents=intents)


@bot_discord.event
async def on_ready():
    print(f"papugpt ({bot_discord.user}) ya anda en el server :v")


@bot_discord.event
async def on_message(message):
    # RESPONDE A OTROS BOTS BUT NO A SÍ MISMO :v
    if message.author.id == bot_discord.user.id:
        return

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
                    message.content.replace(f"<@{bot_discord.user.id}>", "").strip()
                )
                texto_lower = texto_usuario.lower()

                # DETECTOR DE IMÁGENES PAPU :v
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

                if quiere_imagen:
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

                # SI NO PIDIÓ IMAGEN, RESPONDE TEXTO NORMAL CON GEMINI
                historial = []
                async for msg in message.channel.history(limit=6):
                    if msg.content:
                        autor = "model" if msg.author == bot_discord.user else "user"
                        txt_limpio = msg.content.replace(
                            f"<@{bot_discord.user.id}>", ""
                        ).strip()
                        if txt_limpio:
                            contenido = types.Content(
                                role=autor, parts=[types.Part.from_text(text=txt_limpio)]
                            )
                            historial.append(contenido)

                historial.reverse()

                config = types.GenerateContentConfig(
                    system_instruction=PERSONALIDAD_PAPUGPT,
                    temperature=1.0,
                )

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite", contents=historial, config=config
                )

                if response.text:
                    await message.reply(response.text)
                else:
                    await message.reply("miau miau que dijiste papu :v")

            except Exception as e:
                print(f"ERROR: {e}")
                await message.reply(f"chale me tienes de payaso :'v error: {e}")


# --- 3. ARRANCAR TODO ---
if __name__ == "__main__":
    keep_alive()
    bot_discord.run(DISCORD_TOKEN)