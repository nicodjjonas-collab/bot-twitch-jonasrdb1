import os
import random
import time
import asyncio
import json
import twitchio
from twitchio.ext import commands
import google.generativeai as genai

# 1. Carga de Variables de Entorno (Configúralas en Railway)
TOKEN = os.environ.get('TWITCH_TOKEN')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
BOT_NAME = os.environ.get('TWITCH_BOT', 'sesionesoldschool')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Configuración de la IA de Google Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

# Variables de estado del bot
trivia_on, trivia_r, bpm_n = False, "", None
ttt_activo, ttt_x, ttt_o, ttt_turno = False, "", "", "X"
ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
ahorcado_activo, ahorcado_palabra, ahorcado_intentos = False, "", 6
ahorcado_adivinadas = set()
num_activo, num_secreto = False, 0
vf_activo, vf_pregunta, vf_respuesta = False, "", ""
ultimo_mensaje_chat = time.time()
mensajes_automaticos = 0

EMOTES = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL"]

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=[CANAL]
        )

    async def event_ready(self):
        print(f'¡Conectado a Twitch como {self.nick}!')
        print(f'Escuchando el canal: {CANAL}')

    async def event_message(self, message):
        if message.echo:
            return
        
        print(f'[{message.channel.name}] {message.author.name}: {message.content}')
        await self.handle_commands(message)

    # Comando básico de prueba
    @commands.command(name='hola')
    async def hola_command(self, ctx: commands.Context):
        await ctx.send(f'¡Hola @{ctx.author.name}! Qué bueno verte por aquí.')

    # Comando integrado con Google Gemini
    @commands.command(name='ia')
    async def ia_command(self, ctx: commands.Context):
        if not gemini_model:
            await ctx.send(f"@{ctx.author.name} La IA no está configurada (falta la GEMINI_API_KEY en Railway).")
            return

        # Extraer el texto que mandó el usuario después de !ia
        prompt = ctx.message.content.replace('!ia', '').strip()
        if not prompt:
            await ctx.send(f"@{ctx.author.name} Por favor, escribe algo para preguntarle a la IA. Ejemplo: !ia ¿Qué es Python?")
            return

        try:
            # Consulta a Gemini de forma síncrona/asíncrona segura
            response = gemini_model.generate_content(prompt)
            respuesta_texto = response.text.strip().replace('\n', ' ')
            
            # Twitch tiene un límite de caracteres, cortamos si es muy largo (ej. 450 chars)
            if len(respuesta_texto) > 450:
                respuesta_texto = respuesta_texto[:447] + "..."
                
            await ctx.send(f"@{ctx.author.name} {respuesta_texto}")
            
        except Exception as e:
            print(f"Error detallado con Gemini: {str(e)}")
            await ctx.send(f"@{ctx.author.name} Error con la IA. Intenta de nuevo.")

if __name__ == '__main__':
    bot = Bot()
    bot.run()
