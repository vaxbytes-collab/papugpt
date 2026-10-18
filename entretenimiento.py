"""
entretenimiento.py - comandos de diversion de PapuGPT, aptos pa todas las edades.

Reglas de este modulo:
- Nada de contenido sexual, violento, de odio ni groserias.
- Ningun comando repite texto escrito por el usuario (asi el bot no sirve pa colar
  insultos), y ninguno senala, junta ni molesta a otras personas.
- Todos tienen cooldown pa ke no los spameen.

Comandos (10): /chiste /dado /moneda /bola8 /frase /ppt /adivina /trivia /datogato /acertijo
"""

import logging
import random

import discord
from discord import app_commands

log = logging.getLogger("papugpt.fun")


# --- CONTENIDO ---
CHISTES = [
    "¿cual es el colmo de un jardinero? ke su novia se llame Rosa y lo deje plantado :v",
    "¿ke le dice un jaguar a otro? jaguar you papu :v",
    "¿cual es el cafe mas peligroso del mundo? el ex-preso :v",
    "¿por ke los pajaros vuelan al sur? porke caminando tardarian mucho miau",
    "¿ke hace una abeja en el gimnasio? ¡zum-ba! :v",
    "¿como se despiden los quimicos? acido un placer :v",
    "¿ke le dice un 0 a un 8? bonito cinturon papu",
    "¿cual es el colmo de un electricista? ke su esposa se llame Luz y sus hijos le sigan la corriente :v",
    "¿por ke el libro de matematicas estaba triste? porke tenia muchos problemas :'v",
    "¿ke le dice una iguana a su hermana gemela? somos iguanitas :v",
    "¿como se llama el campeon de buceo japones? Tokofondo :v",
    "¿ke hace un gato frente a la compu? busca ratones miau :v",
    "¿por ke la escoba esta feliz? porke ya barrio con todo :v",
    "¿ke le dice un semaforo a otro? no me mires, me estoy cambiando :v",
]

FRASES = [
    "a cada quien le llega su siesta, papu :v",
    "no dejes pa mañana lo ke puedes hacer... despues de una siesta miau",
    "hoy es un buen dia pa tirar un buen momo :v",
    "si te caes siete veces, te levantas ocho... y te tomas un agua, ke se lo merece",
    "la vida es como un gato: a veces te rasguña, a veces te hace compañia miau",
    "un paso a la vez, papu, ke hasta los gatos se estiran antes de brincar :v",
    "tomate un aguita y sigue, ke tu puedes :v",
    "no tienes ke ser perfecto, con ser buena onda ya la armaste papu",
    "ke tu dia sea tan bueno como un rayito de sol pa un gato miau",
    "equivocarse es de sabios... y de gatos ke calculan mal el brinco :v",
]

BOLA8 = [
    "si, totalmente papu :v",
    "ni en sueños, miau",
    "las estrellas de la grasa dicen ke si :v",
    "mejor ni lo intentes :'v",
    "lo dudo mucho, la neta",
    "claro ke si miau",
    "preguntale a tu abuela, ella sabe mas ke yo :v",
    "ahorita no, intenta mas tarde",
    "tal vez, tal vez, tal vez :v",
    "todo apunta a ke si papu",
    "yo diria ke no, but tu sabes :v",
]

DATOS_GATO = [
    "los gatos duermen entre 12 y 16 horas al dia, y los gatitos todavia mas :v",
    "casi todos los gatos tienen 5 dedos en las patas de adelante y 4 en las de atras miau",
    "los gatos no pueden saborear lo dulce, por eso ni les late tu postre :v",
    "los bigotes de un gato le ayudan a sentir el espacio y los objetos a su alrededor",
    "la nariz de cada gato es unica, como una huella digital :v",
    "los gatos pueden girar las orejas casi como antenas, cada una por su lado",
    "los gatitos nacen con los ojos cerrados y los abren como a la primera semana o dos",
    "un gato puede ronronear cuando esta contento, but tambien a veces cuando esta nervioso",
]

ACERTIJOS = [
    ("tengo ciudades pero no casas, montañas pero no arboles y agua pero no peces. ¿ke soy?", "un mapa"),
    ("¿ke cosa sube pero nunca baja?", "la edad"),
    ("mientras mas seco me secas, mas mojado me pones. ¿ke soy?", "la toalla"),
    ("tengo dientes pero no muerdo. ¿ke soy?", "el peine"),
    ("blanca por dentro, verde por fuera; si kieres ke te lo diga, espera. ¿ke soy?", "la pera"),
    ("¿ke tiene cuatro patas pero no puede caminar?", "la mesa"),
    ("vuelo sin alas y lloro sin ojos. ¿ke soy?", "la nube"),
    ("¿ke tiene manos pero no puede aplaudir?", "el reloj"),
]

# (pregunta, respuesta correcta, [respuestas incorrectas])
TRIVIA = [
    ("¿cual es el planeta mas cercano al Sol?", "Mercurio", ["Venus", "Marte", "Jupiter"]),
    ("¿cuantas patas tiene una araña?", "8", ["6", "10", "4"]),
    ("¿cual es el oceano mas grande?", "Pacifico", ["Atlantico", "Indico", "Artico"]),
    ("¿cuantos lados tiene un hexagono?", "6", ["5", "8", "7"]),
    ("¿en ke continente esta Egipto?", "Africa", ["Asia", "Europa", "Oceania"]),
    ("¿ke gas necesitamos respirar pa vivir?", "Oxigeno", ["Helio", "Nitrogeno", "Hidrogeno"]),
    ("¿cuantos dias tiene un año bisiesto?", "366", ["365", "364", "367"]),
    ("¿cual es la capital de Mexico?", "Ciudad de Mexico", ["Guadalajara", "Monterrey", "Puebla"]),
    ("¿cual es el animal terrestre mas rapido?", "Guepardo", ["Leon", "Caballo", "Elefante"]),
    ("¿cuantos colores tiene el arcoiris (los tradicionales)?", "7", ["5", "6", "9"]),
    ("¿cual es el hueso mas largo del cuerpo humano?", "Femur", ["Humero", "Tibia", "Costilla"]),
    ("¿ke planeta se conoce como el planeta rojo?", "Marte", ["Saturno", "Venus", "Neptuno"]),
    ("¿cuantos jugadores tiene un equipo de futbol en la cancha?", "11", ["9", "10", "12"]),
    ("¿de ke color es la clorofila de las plantas?", "Verde", ["Azul", "Rojo", "Amarillo"]),
    ("¿cual es el mes con solo 28 dias (29 en año bisiesto)?", "Febrero", ["Abril", "Junio", "Noviembre"]),
]

OPCIONES_PPT = {"piedra": "✊", "papel": "✋", "tijera": "✌️"}
GANA_A = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}


# --- TRIVIA CON BOTONES ---
class OpcionBoton(discord.ui.Button):
    def __init__(self, indice, texto):
        super().__init__(label=str(texto)[:80], style=discord.ButtonStyle.secondary)
        self.indice = indice

    async def callback(self, interaction):
        vista = self.view
        acerto = self.indice == vista.correcta
        for boton in vista.children:
            boton.disabled = True
            if boton.indice == vista.correcta:
                boton.style = discord.ButtonStyle.success
            elif boton is self:
                boton.style = discord.ButtonStyle.danger
        vista.stop()
        if acerto:
            extra = "\n✅ ¡correcto papu! :v"
        else:
            extra = f"\n❌ uy no :'v la buena era: **{vista.opciones[vista.correcta]}**"
        await interaction.response.edit_message(content=vista.texto_base + extra, view=vista)


class TriviaView(discord.ui.View):
    def __init__(self, autor_id, texto_base, opciones, correcta):
        super().__init__(timeout=25)
        self.autor_id = autor_id
        self.texto_base = texto_base
        self.opciones = opciones
        self.correcta = correcta
        self.mensaje = None
        for i, opcion in enumerate(opciones):
            self.add_item(OpcionBoton(i, opcion))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "esa trivia no es tuya papu :v usa /trivia pa la tuya", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for boton in self.children:
            boton.disabled = True
        if self.mensaje is not None:
            try:
                await self.mensaje.edit(
                    content=self.texto_base + "\n⏰ se acabo el tiempo :'v", view=self
                )
            except discord.HTTPException:
                pass


# --- REGISTRO DE COMANDOS ---
def registrar(bot):
    """Agrega los 10 comandos al arbol del bot. Llamar ANTES de bot.run()."""
    tree = bot.tree

    @tree.error
    async def _errores(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            texto = f"calmate papu :v espera {int(error.retry_after) + 1} segundos"
        else:
            log.error("error en un comando", exc_info=error)
            texto = "chale algo fallo :'v intenta otra vez"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(texto, ephemeral=True)
            else:
                await interaction.response.send_message(texto, ephemeral=True)
        except discord.HTTPException:
            pass

    @tree.command(name="chiste", description="te cuento un chiste (apto pa todos)")
    @app_commands.checks.cooldown(1, 3.0)
    async def chiste(interaction: discord.Interaction):
        await interaction.response.send_message("😹 " + random.choice(CHISTES))

    @tree.command(name="dado", description="tira un dado (por defecto de 6 caras)")
    @app_commands.describe(caras="cuantas caras tiene el dado (de 2 a 100)")
    @app_commands.checks.cooldown(1, 3.0)
    async def dado(interaction: discord.Interaction, caras: app_commands.Range[int, 2, 100] = 6):
        numero = random.randint(1, caras)
        await interaction.response.send_message(
            f"🎲 tiraste un dado de {caras} caras y salio el **{numero}** :v"
        )

    @tree.command(name="moneda", description="lanza una moneda: aguila o sol")
    @app_commands.checks.cooldown(1, 3.0)
    async def moneda(interaction: discord.Interaction):
        resultado = random.choice(["aguila", "sol"])
        await interaction.response.send_message(f"🪙 la moneda cayo en... **{resultado}** :v")

    @tree.command(name="bola8", description="hazle una pregunta de si o no a la bola magica")
    @app_commands.describe(pregunta="tu pregunta de si o no")
    @app_commands.checks.cooldown(1, 5.0)
    async def bola8(interaction: discord.Interaction, pregunta: app_commands.Range[str, 1, 200]):
        # a proposito NO repite la pregunta del usuario
        await interaction.response.send_message("🎱 " + random.choice(BOLA8))

    @tree.command(name="frase", description="una frase bonita pa tu dia")
    @app_commands.checks.cooldown(1, 3.0)
    async def frase(interaction: discord.Interaction):
        await interaction.response.send_message("✨ " + random.choice(FRASES))

    @tree.command(name="ppt", description="piedra, papel o tijera contra mi")
    @app_commands.describe(jugada="tu jugada")
    @app_commands.choices(
        jugada=[
            app_commands.Choice(name="piedra ✊", value="piedra"),
            app_commands.Choice(name="papel ✋", value="papel"),
            app_commands.Choice(name="tijera ✌️", value="tijera"),
        ]
    )
    @app_commands.checks.cooldown(1, 3.0)
    async def ppt(interaction: discord.Interaction, jugada: app_commands.Choice[str]):
        tuya = jugada.value
        mia = random.choice(list(OPCIONES_PPT))
        if tuya == mia:
            resultado = "empate :v"
        elif GANA_A[tuya] == mia:
            resultado = "ganaste papu, felicidades :v"
        else:
            resultado = "gane yo miau :v"
        await interaction.response.send_message(
            f"tu: {OPCIONES_PPT[tuya]} {tuya} · yo: {OPCIONES_PPT[mia]} {mia}\n{resultado}"
        )

    @tree.command(name="adivina", description="adivina el numero ke pense, del 1 al 10")
    @app_commands.describe(numero="tu numero (del 1 al 10)")
    @app_commands.checks.cooldown(1, 3.0)
    async def adivina(interaction: discord.Interaction, numero: app_commands.Range[int, 1, 10]):
        secreto = random.randint(1, 10)
        if numero == secreto:
            texto = f"🎉 ¡le atinaste! pense en el **{secreto}** :v"
        else:
            texto = f"😿 pense en el **{secreto}** y tu dijiste el {numero}. ¡intenta otra vez!"
        await interaction.response.send_message(texto)

    @tree.command(name="trivia", description="una pregunta de cultura general con botones")
    @app_commands.checks.cooldown(1, 10.0)
    async def trivia(interaction: discord.Interaction):
        pregunta, correcta, incorrectas = random.choice(TRIVIA)
        opciones = list(incorrectas) + [correcta]
        random.shuffle(opciones)
        texto = f"🧠 **trivia:** {pregunta}"
        vista = TriviaView(interaction.user.id, texto, opciones, opciones.index(correcta))
        await interaction.response.send_message(texto, view=vista)
        vista.mensaje = await interaction.original_response()

    @tree.command(name="datogato", description="un dato curioso sobre los gatos")
    @app_commands.checks.cooldown(1, 3.0)
    async def datogato(interaction: discord.Interaction):
        await interaction.response.send_message("🐱 " + random.choice(DATOS_GATO))

    @tree.command(name="acertijo", description="un acertijo, la respuesta esta tapada")
    @app_commands.checks.cooldown(1, 5.0)
    async def acertijo(interaction: discord.Interaction):
        pregunta, respuesta = random.choice(ACERTIJOS)
        await interaction.response.send_message(
            f"🤔 **acertijo:** {pregunta}\nrespuesta (tocala pa verla): ||{respuesta}||"
        )
