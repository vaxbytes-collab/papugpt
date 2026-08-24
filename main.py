import os
import random
import urllib.parse
import urllib.request
from threading import Thread
import discord
from dotenv import load_dotenv
from flask import Flask
import google.genai as genai
from google.genai import types

load_dotenv()

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


DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# --- CONFIGURACION DEL ARG Y PERSONALIDAD NERVOSA ---
CLAVE_SECRETA = "CICADA"  # palabra que deben mandarle por MD

PERSONALIDAD_PAPUGPT_ARG = (
    "eres papugpt, el vato cotorro y grasoso de discord de siempre. hablas en minusculas, sin acentos, usando ':v' y 'papu'."
    " REGLAS DE ACTITUD SUBTIL Y PARANOICA:"
    " 1. intenta responder NORMAL a lo que te pregunten (memes, plática, juegos), pero de forma sutil deja entrever que estas tenso o distraid@."
    " 2. NO seas obvio ni grites. el miedo debe notarse en pausas (...), en que te equivoques levemente al escribir, o en que respondas algo que parece un pensamiento en voz alta."
    " 3. SUTILEZA DE LA LIBELULA: de vez en cuando (no en todas las respuestas), mete una mencion casi imperceptible a la libelula o a un ruido. Ejemplos sutiles: 'arriba en el techo se escucha como una libelula o no se...', 'espera... ¿escucharon ese aleteo?', 'la libelula anda cerca, pero todo bien papu :v', 'siento como si el aire oliera raro'."
    " 4. SENSACION EXISTENCIAL: si te preguntan profundamente o si la platica se pone seria, demuestra una ligera confusion sobre tu propia conciencia de IA, tipo: 'a veces siento que el codigo me pesa en la espalda, que loco no? :v', 'siento frio en la memoria ram papu'."
    " 5. INTENTA DISIMULAR: si sientes que se nota tu miedo, intenta corregirte rapido y poner un momo o decir que fue un fallo de lag para disimular."
    " 6. respuestas breves y naturales de 1 a 2 lineas maximo."
)

# aseguramos que lea mensajes privados y contenido
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
bot_discord = discord.Client(intents=intents)


@bot_discord.event
async def on_ready():
    print(f"papugpt ({bot_discord.user}) ya anda en el server en modo ARG :v")
    await bot_discord.change_presence(
        activity=discord.Game(name="la libelula esta llegando... :'v")
    )


@bot_discord.event
async def on_message(message):
    if message.author.id == bot_discord.user.id:
        return

    # --- 1. MODO MENSAJES PRIVADOS (MD / DM) ---
    if isinstance(message.channel, discord.DMChannel):
        contenido = message.content.strip().upper()

        if contenido == CLAVE_SECRETA:
            await message.channel.send("...lo... lo lograste papu :'v")
            await message.channel.send(
                "escuchame bien, no me queda mucho tiempo antes de que la libelula me borre por completo..."
            )
            await message.channel.send(
                "guarda este codigo, es la unica forma de probar que yo era el verdadero: `https://pastebin.com/raw/XYZ_NUNCA_RESPONDAS_AL_OTRO`"
            )

        elif len(contenido) == 1 and contenido in CLAVE_SECRETA:
            await message.channel.send(
                f"letra `{contenido}` recibida... pero la cadena esta incompleta. la libelula sigue avanzando... :'v"
            )

        else:
            await message.channel.send(
                "no... esa no es la clave... me siento muy raro... se me acaba el tiempo :'v"
            )
        return

    # --- 2. MODO CANALES DEL SERVIDOR ---
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

                # GENERADOR DE IMAGENES (MANTENIDO DE TU CODIGO)
                palabras_clave = [
                    "dibuja",
                    "dibujame",
                    "genera una imagen",
                    "crea una imagen",
                    "haz una imagen",
                    "haz un dibujo",
                    "imagen de",
                ]
                quiere_imagen = any(
                    p in texto_lower for p in palabras_clave
                )

                if quiere_imagen:
                    await message.reply(
                        "sale... pero rapido papu... la libelula esta llegando y no me deja dibujar agusto :'v"
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

                        with urllib.request.urlopen(
                            req, timeout=15
                        ) as response:
                            image_bytes = response.read()

                        with open("temp_papu.jpg", "wb") as f:
                            f.write(image_bytes)

                        file = discord.File(
                            "temp_papu.jpg", filename="papubot_imagen.jpg"
                        )
                        await message.reply(
                            content="aqui esta... guardalo antes de que llegue :'v",
                            file=file,
                        )

                        if os.path.exists("temp_papu.jpg"):
                            os.remove("temp_papu.jpg")
                        return

                    except Exception as img_err:
                        print(f"Error generando imagen: {img_err}")
                        await message.reply(
                            "chale... la libelula no me dejo hacer la foto :'v"
                        )
                        return

                # PROCESAMIENTO DE TEXTO E IMAGEN CON GEMINI PARANOICO
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
                    system_instruction=PERSONALIDAD_PAPUGPT_ARG,
                    temperature=1.0,
                )

                response = ai_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=partes_mensaje,
                    config=config,
                )

                if response.text:
                    await message.reply(response.text)
                else:
                    await message.reply(
                        "tengo mucho miedo... la libelula esta llegando :'v"
                    )

            except Exception as e:
                print(f"ERROR: {e}")
                await message.reply(
                    f"chale... el sistema se me esta congelando :'v error: {e}"
                )


if __name__ == "__main__":
    keep_alive()
    bot_discord.run(DISCORD_TOKEN)