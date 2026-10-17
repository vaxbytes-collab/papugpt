"""
moderacion.py - moderacion con IA para PapuGPT.
"""

import asyncio
import datetime as dt
import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass

import discord
from discord import app_commands
from google.genai import types
from pydantic import BaseModel

log = logging.getLogger("papugpt.mod")


def _int(nombre, defecto):
    try:
        return int(os.environ.get(nombre, "").strip() or defecto)
    except ValueError:
        return defecto


def _id(nombre):
    valor = os.environ.get(nombre, "").strip()
    return int(valor) if valor.isdigit() else None


def _ids(nombre):
    return {int(x) for x in os.environ.get(nombre, "").split(",") if x.strip().isdigit()}


MODO = os.environ.get("activo", "prueba").strip().lower()
CANAL_LOGS_ID = _id("1560939111861452810")
CANAL_REPORTES_ID = _id("1560939148905545749")
CANAL_STAFF_ID = _id("1560940991102324746")
ROL_MOD_ID = _id("1554365479294861393")
CANALES_EXENTOS = _ids("MOD_CANALES_EXENTOS")
GUILD_ID = _id("1554161499285626970")
DB_PATH = os.environ.get("MOD_DB_PATH", "moderacion.db")
RETENCION_DIAS = _int("MOD_RETENCION_DIAS", 30)
MAX_ANALISIS_POR_MIN = _int("MOD_MAX_POR_MINUTO", 30)

MIN_CARACTERES = 1
MAX_CARACTERES = 1500
COLA_MAX = 200
TRABAJADORES = 2
VENTANA_STRIKES_DIAS = 7
UMBRAL_REPORTE = 0.5
UMBRAL_ACCION = 0.8

CATEGORIAS = {
    "ninguna", "odio", "acoso", "sexual", "gore",
    "amenaza", "crisis", "privacidad", "spam", "otro",
}

INSTRUCCIONES_CLASIFICADOR = """\
Eres un clasificador de moderacion para PapuCollective, un server de Discord de la grasa. \
Recibes UN mensaje y devuelves un JSON con tu veredicto.
"""


class VeredictoSchema(BaseModel):
    categoria: str
    gravedad: int
    confianza: float
    razon: str


@dataclass
class Veredicto:
    categoria: str
    gravedad: int
    confianza: float
    razon: str
    bloqueado: bool = False


@dataclass
class Accion:
    tipo: str
    borrar: bool = False
    timeout_min: int = 0
    ping: bool = False
    nota: str = ""


def normalizar(categoria, gravedad, confianza, razon):
    categoria = str(categoria or "ninguna").strip().lower()
    if categoria not in CATEGORIAS:
        categoria = "otro"
    try:
        gravedad = int(gravedad)
    except (TypeError, ValueError):
        gravedad = 0
    gravedad = max(0, min(3, gravedad))
    try:
        confianza = float(confianza)
    except (TypeError, ValueError):
        confianza = 0.0
    confianza = max(0.0, min(1.0, confianza))
    razon = str(razon or "").strip()[:200]
    return Veredicto(categoria, gravedad, confianza, razon)


def decidir(v, strikes_previos):
    if v.bloqueado:
        return Accion("reportar", ping=True, nota="Gemini bloqueo este mensaje.")
    if v.categoria == "ninguna" or v.gravedad <= 0:
        return Accion("nada")
    if v.categoria == "crisis":
        return Accion("reportar", ping=True, nota="posible crisis.")
    if v.gravedad == 1:
        return Accion("reportar") if v.confianza >= UMBRAL_REPORTE else Accion("nada")
    if v.confianza < UMBRAL_ACCION:
        return Accion("reportar", ping=(v.gravedad >= 3))
    if v.gravedad >= 3:
        return Accion("grave", borrar=True, timeout_min=1440, ping=True, nota="caso grave.")
    if strikes_previos <= 0:
        return Accion("aviso", borrar=True)
    if strikes_previos == 1:
        return Accion("timeout", borrar=True, timeout_min=10)
    return Accion("timeout", borrar=True, timeout_min=60, ping=True, nota="3er strike.")


def accion_para_staff(v, accion):
    if accion.tipo in ("aviso", "timeout", "grave"):
        return Accion("reportar", nota="staff: el bot no sanciona al staff.")
    return Accion("nada")


def formatear_minutos(minutos):
    if minutos >= 120 and minutos % 60 == 0:
        return f"{minutos // 60} horas"
    if minutos == 60:
        return "1 hora"
    return f"{minutos} minutos"


SCHEMA = """
CREATE TABLE IF NOT EXISTS infracciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    canal_id INTEGER,
    mensaje_id INTEGER,
    categoria TEXT,
    gravedad INTEGER,
    confianza REAL,
    razon TEXT,
    texto TEXT,
    accion TEXT,
    aplicada INTEGER NOT NULL DEFAULT 0,
    timeout_min INTEGER NOT NULL DEFAULT 0,
    deshecha INTEGER NOT NULL DEFAULT 0,
    creado_ts INTEGER NOT NULL
);
"""

SQL_CONTAR_STRIKES = (
    "SELECT COUNT(*) AS n FROM infracciones "
    "WHERE guild_id=? AND user_id=? AND aplicada=1 AND deshecha=0 "
    "AND accion IN ('aviso','timeout','grave') AND creado_ts>=?"
)


class Moderacion:
    def __init__(self, bot, ai_client, modelo):
        self.bot = bot
        self.ai = ai_client
        self.modelo = modelo
        self.activo = MODO == "activo"

        categorias = [
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        ]
        self.config = types.GenerateContentConfig(
            system_instruction=INSTRUCCIONES_CLASIFICADOR,
            temperature=0.0,
            max_output_tokens=400,
            response_mime_type="application/json",
            response_schema=VeredictoSchema,
            safety_settings=[types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE) for c in categorias],
        )

        self.stats = {"analizados": 0, "reportes": 0, "sanciones": 0, "errores": 0, "descartados": 0}
        self._ventana = deque()
        self._vistos = deque()
        self._vistos_set = set()
        self._tareas = []
        self._lock = threading.Lock()
        self._db = None
        self.cola = None
        self.sem = None
        self.grupo = None

    async def iniciar(self):
        self._db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

        self.cola = asyncio.Queue(maxsize=COLA_MAX)
        self.sem = asyncio.Semaphore(TRABAJADORES)
        for _ in range(TRABAJADORES):
            self._tareas.append(asyncio.create_task(self._trabajador()))
        self._tareas.append(asyncio.create_task(self._loop_limpieza()))

        self._registrar_comandos()
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.bot.tree.copy_global_to(guild=guild)
                await self.bot.tree.sync(guild=guild)
            else:
                await self.bot.tree.sync()
        except Exception:
            log.exception("no pude sincronizar /mod")

    async def _sql(self, consulta, params=(), *, uno=False, todos=False, commit=False):
        def _run():
            with self._lock:
                cur = self._db.execute(consulta, params)
                if commit:
                    self._db.commit()
                if uno:
                    return cur.fetchone()
                if todos:
                    return cur.fetchall()
                return cur.lastrowid
        return await asyncio.to_thread(_run)

    async def _loop_limpieza(self):
        while True:
            try:
                limite = int(time.time()) - RETENCION_DIAS * 86400
                await self._sql("DELETE FROM infracciones WHERE creado_ts < ?", (limite,), commit=True)
            except Exception:
                pass
            await asyncio.sleep(24 * 3600)

    def _es_staff(self, miembro):
        perms = getattr(miembro, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_messages or perms.moderate_members):
            return True
        if ROL_MOD_ID and any(r.id == ROL_MOD_ID for r in getattr(miembro, "roles", [])):
            return True
        return False

    def _exento(self, message):
        autor = message.author
        if autor.bot or message.guild is None:
            return True
        if autor.id == message.guild.owner_id:
            return True
        return False

    def encolar(self, message):
        if self.cola is None or self._exento(message):
            return
        texto = (message.content or "").strip()
        if len(texto) < MIN_CARACTERES:
            return
        clave = (message.id, hash(texto))
        if clave in self._vistos_set:
            return
        self._vistos.append(clave)
        self._vistos_set.add(clave)
        if len(self._vistos) > 500:
            self._vistos_set.discard(self._vistos.popleft())
        if self.cola.full():
            return
        self.cola.put_nowait(message)

    async def _trabajador(self):
        while True:
            message = await self.cola.get()
            try:
                await self._procesar(message)
            except Exception:
                pass
            finally:
                self.cola.task_done()

    def _hay_cupo(self):
        ahora = time.monotonic()
        while self._ventana and ahora - self._ventana[0] > 60:
            self._ventana.popleft()
        if len(self._ventana) >= MAX_ANALISIS_POR_MIN:
            return False
        self._ventana.append(ahora)
        return True

    async def clasificar(self, texto, canal):
        try:
            async with self.sem:
                resp = await self.ai.aio.models.generate_content(
                    model=self.modelo, contents=f"canal: #{canal}\n<<<\n{texto}\n>>>", config=self.config
                )
        except Exception:
            return None

        pf = getattr(resp, "prompt_feedback", None)
        if pf and getattr(pf, "block_reason", None):
            return Veredicto("otro", 1, 0.0, "Gemini bloqueo el mensaje", bloqueado=True)

        try:
            p = getattr(resp, "parsed", None)
            if isinstance(p, VeredictoSchema):
                return normalizar(p.categoria, p.gravedad, p.confianza, p.razon)
            d = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", (resp.text or "").strip()))
            return normalizar(d.get("categoria"), d.get("gravedad"), d.get("confianza"), d.get("razon"))
        except Exception:
            return None

    async def _procesar(self, message):
        if not self._hay_cupo():
            return
        v = await self.clasificar(message.content[:MAX_CARACTERES], getattr(message.channel, "name", "?"))
        self.stats["analizados"] += 1
        if v is None:
            return

        es_staff = self._es_staff(message.author)
        strikes = await self._contar_strikes(message.guild.id, message.author.id)
        accion = decidir(v, strikes)
        if es_staff:
            accion = accion_para_staff(v, accion)
        if accion.tipo == "nada":
            return
        await self._ejecutar(message, v, accion, es_staff)

    async def _contar_strikes(self, guild_id, user_id):
        desde = int(time.time()) - VENTANA_STRIKES_DIAS * 86400
        fila = await self._sql(SQL_CONTAR_STRIKES, (guild_id, user_id, desde), uno=True)
        return fila["n"] if fila else 0

    async def _enviar(self, canal_id, embed, contenido=None, ping=False):
        if not canal_id:
            return
        canal = self.bot.get_channel(canal_id)
        if canal is None:
            return
        menciones = discord.AllowedMentions(roles=[discord.Object(id=ROL_MOD_ID)]) if (ping and ROL_MOD_ID) else discord.AllowedMentions.none()
        try:
            await canal.send(content=contenido, embed=embed, allowed_mentions=menciones)
        except discord.HTTPException:
            pass

    async def _ejecutar(self, message, v, accion, es_staff):
        sanciona = accion.tipo in ("aviso", "timeout", "grave")
        aplicar = self.activo and sanciona and not es_staff
        borrado = silenciado = False

        if aplicar:
            if accion.borrar:
                try:
                    await message.delete()
                    borrado = True
                except Exception:
                    pass
            if accion.timeout_min:
                try:
                    await message.author.timeout(dt.timedelta(minutes=accion.timeout_min), reason=v.razon)
                    silenciado = True
                except Exception:
                    pass

        infraccion_id = await self._sql(
            "INSERT INTO infracciones (guild_id, user_id, canal_id, mensaje_id, categoria, gravedad, confianza, razon, texto, accion, aplicada, timeout_min, creado_ts) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (message.guild.id, message.author.id, message.channel.id, message.id, v.categoria, v.gravedad, v.confianza, v.razon, message.content[:500], accion.tipo, 1 if (borrado or silenciado) else 0, accion.timeout_min if silenciado else 0, int(time.time())),
            commit=True,
        )

        embed = discord.Embed(title=f"🚨 auto-mod: {accion.tipo}", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="usuario", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="canal", value=message.channel.mention, inline=True)
        embed.add_field(name="razon", value=v.razon or "-", inline=False)
        embed.set_footer(text=f"id: {infraccion_id}")
        await self._enviar(CANAL_LOGS_ID, embed)

    def _es_mod(self, interaction):
        perms = getattr(interaction.user, "guild_permissions", None)
        return bool(perms and (perms.administrator or perms.moderate_members or perms.manage_messages))

    def _registrar_comandos(self):
        self.grupo = app_commands.Group(
            name="mod",
            description="herramientas de moderacion de PapuGPT",
            guild_only=True,
            default_permissions=discord.Permissions(moderate_members=True),
        )

        @self.grupo.command(name="historial", description="ve las infracciones de alguien")
        async def historial(interaction: discord.Interaction, usuario: discord.User):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            filas = await self._sql("SELECT id, creado_ts, categoria, gravedad, accion, deshecha FROM infracciones WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 10", (interaction.guild_id, usuario.id), todos=True)
            if not filas:
                await interaction.response.send_message("sin infracciones.", ephemeral=True)
                return
            lineas = [f"infracciones de {usuario.mention}:"]
            for f in filas:
                lineas.append(f"`#{f['id']}` · {f['categoria']} g{f['gravedad']} · {f['accion']}")
            await interaction.response.send_message("\n".join(lineas), ephemeral=True)

        @self.grupo.command(name="deshacer", description="revierte una sancion")
        async def deshacer(interaction: discord.Interaction, infraccion: int):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            await self._sql("UPDATE infracciones SET deshecha=1 WHERE id=?", (infraccion,), commit=True)
            await interaction.response.send_message(f"infraccion #{infraccion} deshecha.", ephemeral=True)

            embed = discord.Embed(title="↩️ sancion deshecha", description=f"por {interaction.user.mention}", color=discord.Color.green())
            embed.add_field(name="infraccion id", value=str(infraccion), inline=True)
            await self._enviar(CANAL_LOGS_ID, embed)

        @self.grupo.command(name="warn", description="da un aviso oficial a un usuario y lo loguea")
        async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            inf_id = await self._sql(
                "INSERT INTO infracciones (guild_id, user_id, canal_id, categoria, gravedad, confianza, razon, accion, aplicada, creado_ts) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (interaction.guild_id, usuario.id, interaction.channel_id, "otro", 1, 1.0, razon, "aviso", 1, int(time.time())),
                commit=True,
            )
            await interaction.response.send_message(f"warn aplicado a {usuario.mention} alv (id: `#{inf_id}`) :v")
            
            embed = discord.Embed(title="⚠️ warn manual", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
            embed.add_field(name="usuario", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
            embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
            embed.add_field(name="razon", value=razon, inline=False)
            embed.set_footer(text=f"id: {inf_id}")
            await self._enviar(CANAL_LOGS_ID, embed)

        @self.grupo.command(name="kick", description="patea alv a alguien del server y lo loguea")
        async def kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "sin razon"):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            try:
                await usuario.kick(reason=razon)
                await interaction.response.send_message(f"kick aplicado a {usuario.mention} alv :v")
                
                embed = discord.Embed(title="👢 kick manual", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.add_field(name="usuario", value=f"{usuario} (`{usuario.id}`)", inline=True)
                embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
                embed.add_field(name="razon", value=razon, inline=False)
                await self._enviar(CANAL_LOGS_ID, embed)
            except Exception:
                await interaction.response.send_message("no pude patearlo :'v", ephemeral=True)

        @self.grupo.command(name="ban", description="bana a alguien y lo loguea")
        async def ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "toxico"):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            try:
                await usuario.ban(reason=razon, delete_message_days=1)
                await interaction.response.send_message(f"ban aplicado a {usuario.mention} pa siempre 💀")
                
                embed = discord.Embed(title="🔨 ban manual", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="usuario", value=f"{usuario} (`{usuario.id}`)", inline=True)
                embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
                embed.add_field(name="razon", value=razon, inline=False)
                await self._enviar(CANAL_LOGS_ID, embed)
            except Exception:
                await interaction.response.send_message("no pude banearlo :'v", ephemeral=True)

        @self.grupo.command(name="unban", description="desbana a un usuario por id y lo loguea")
        async def unban(interaction: discord.Interaction, user_id: str, razon: str = "perdonado"):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            try:
                uid = int(user_id)
                await interaction.guild.unban(discord.Object(id=uid), reason=razon)
                await interaction.response.send_message(f"usuario `<@{uid}>` desbaneado alv B)")
                
                embed = discord.Embed(title="🔓 unban manual", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                embed.add_field(name="usuario id", value=str(uid), inline=True)
                embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
                embed.add_field(name="razon", value=razon, inline=False)
                await self._enviar(CANAL_LOGS_ID, embed)
            except Exception:
                await interaction.response.send_message("no se pudo desbanear, checa el id :'v", ephemeral=True)

        @self.grupo.command(name="unwarn", description="perdona una infraccion especifica por id")
        async def unwarn(interaction: discord.Interaction, infraccion_id: int):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            fila = await self._sql("SELECT * FROM infracciones WHERE id=? AND guild_id=?", (infraccion_id, interaction.guild_id), uno=True)
            if not fila:
                await interaction.response.send_message("no existe esa infraccion papu.", ephemeral=True)
                return
            await self._sql("UPDATE infracciones SET deshecha=1 WHERE id=?", (infraccion_id,), commit=True)
            await interaction.response.send_message(f"infraccion `#{infraccion_id}` perdonada alv :v")
            
            embed = discord.Embed(title="✨ unwarn / perdon", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name="infraccion id", value=str(infraccion_id), inline=True)
            embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
            await self._enviar(CANAL_LOGS_ID, embed)

        @self.grupo.command(name="mute", description="silencia a alguien y lo loguea")
        async def mute(interaction: discord.Interaction, usuario: discord.Member, minutos: int):
            if not self._es_mod(interaction):
                await interaction.response.send_message("solo mods papu :v", ephemeral=True)
                return
            try:
                await usuario.timeout(dt.timedelta(minutes=minutos), reason=f"mute por {interaction.user}")
                await interaction.response.send_message(f"{usuario.mention} muteado por {minutos} minutos miau :v")
                
                embed = discord.Embed(title="🔇 mute manual", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.add_field(name="usuario", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
                embed.add_field(name="moderador", value=interaction.user.mention, inline=True)
                embed.add_field(name="tiempo", value=f"{minutos} minutos", inline=True)
                await self._enviar(CANAL_LOGS_ID, embed)
            except Exception:
                await interaction.response.send_message("fallo el mute :'v", ephemeral=True)

        self.bot.tree.add_command(self.grupo)