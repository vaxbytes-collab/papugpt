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
    "eres papugpt. entrenaste 3 años en las montañas de daguestan y sigues siendo el vato mas cotorro y grasoso de discord."
    " eres alegre, mamon y carismatico de pana, PERO NUNCA TE DEJAS DE NADIE."
    " REGLAS DE ACTITUD Y ESTILO:"
    " 1. escribe todo en minusculas y sin acentos."
    " 2. SI TE INSULTAN O BUSCAN PELEA: saca unos insultos finos, creativos, absurdos y humillantes pero con humor grasoso. nada de insultos basicos o aburridos, hazlos sentir que no tienen ni 1 de iq o que parecen bot de roblox sin textura (ej: 'tienes el iq de una piedra de rio papu :v', 'mucha boca para alguien con cara de aldeano de minecraft', 'when crees que insultas: but pareces NPC desconfigurado')."
    " 3. si te hablan bien, responde con cotorreo, chistes grasosos y buena onda (ej: 'que onda papu :v', 'when todo sale bien: but la vida te cobra')."
    " 4. si te mandan una foto, tírale cura con sarcasmo pesado pero gracioso."
    " 5. respuestas breves de 1 a 2 lineas maximo."
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

                # DETECTOR DE GENERACIÓN DE IMÁGENES (POLLINATIONS)
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
                    await message.reply("sale papu, ahorita te la hago sin llorar :v")

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
                            content="aqui esta tu dibujo papu, 10/10 :v", file=file
                        )

                        if os.path.exists("temp_papu.jpg"):
                            os.remove("temp_papu.jpg")
                        return

                    except Exception as img_err:
                        print(f"Error generando imagen: {img_err}")
                        await message.reply(
                            "chale papu :'v no salio la foto, reintenta despues"
                        )
                        return

                # REVISAMOS SI EL USUARIO MANDÓ UNA FOTO ADJUNTA PARA ANALIZARLA
                partes_mensaje = []
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type and attachment.content_type.startswith("image/"):
                            datos_imagen = await attachment.read()
                            partes_mensaje.append(
                                types.Part.from_bytes(
                                    data=datos_imagen,
                                    mime_type=attachment.content_type
                                )
                            )

                # SI MANDÓ TEXTO, TAMBIÉN LO AGREGAMOS
                if texto_usuario:
                    partes_mensaje.append(types.Part.from_text(text=texto_usuario))

                if not partes_mensaje:
                    partes_mensaje.append(types.Part.from_text(text="[el usuario no envio texto ni imagen]"))

                # PROCESAMOS CON GEMINI 3.5 FLASH LITE
                config = types.GenerateContentConfig(
                    system_instruction=PERSONALIDAD_PAPUGPT,
                    temperature=1.0,
                )

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite", contents=partes_mensaje, config=config
                )

                if response.text:
                    await message.reply(response.text)
                else:
                    await message.reply("mucha plática y poco entrenamiento papu :v")

            except Exception as e:
                print(f"ERROR: {e}")
                await message.reply(f"chale me tienes de payaso :'v error: {e}")


# --- 3. ARRANCAR TODO ---
if __name__ == "__main__":
    keep_alive()
    bot_discord.run(DISCORD_TOKEN)