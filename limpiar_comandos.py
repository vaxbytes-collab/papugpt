"""
limpiar_comandos.py - borra TODOS los comandos slash de PapuGPT (globales y del server).

Usalo UNA vez cuando salgan comandos repetidos o viejos (ej. /8ball junto a /bola8).
Despues arranca main.py normal y registra solo los nuevos.

ANTES de correrlo:
  1) apaga todos los PapuGPT ke esten corriendo (tu compu, hosting, otra terminal).
     si queda uno viejo prendido, vuelve a registrar los comandos viejos al reiniciarse.
  2) ten el .env con DISCORD_TOKEN (y MOD_GUILD_ID si tu server cambio).

Uso:  python limpiar_comandos.py
"""

import os

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("MOD_GUILD_ID", "1554161499285626970"))

if not TOKEN:
    raise SystemExit("falta DISCORD_TOKEN en el .env")


class Limpiador(discord.Client):
    async def setup_hook(self):
        try:
            tree = discord.app_commands.CommandTree(self)
            guild = discord.Object(id=GUILD_ID)

            # un arbol vacio sincronizado = Discord borra todo lo ke habia
            tree.clear_commands(guild=None)
            await tree.sync()
            tree.clear_commands(guild=guild)
            await tree.sync(guild=guild)

            globales = await tree.fetch_commands()
            en_server = await tree.fetch_commands(guild=guild)
            print(f"comandos globales ke quedan: {len(globales)}")
            print(f"comandos del server ke quedan: {len(en_server)}")
            if globales or en_server:
                print("OJO: todavia quedan comandos. Revisa MOD_GUILD_ID y ke el bot tenga 'applications.commands'.")
            else:
                print("listo: todo borrado. Ahora arranca main.py (un solo PapuGPT) y refresca Discord con Ctrl+R.")
        except Exception as e:
            print("fallo la limpieza:", repr(e))
        finally:
            await self.close()


if __name__ == "__main__":
    Limpiador(intents=discord.Intents.none()).run(TOKEN)
