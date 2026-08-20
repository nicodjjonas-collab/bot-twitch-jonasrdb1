import os
import random
import time
import asyncio
import twitchio
from twitchio.ext import commands
from google import genai

# ----------------------------------------
# 1. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ----------------------------------------
TOKEN = os.environ.get('TWITCH_TOKEN')
CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            client_id=CLIENT_ID,
            prefix='!',
            initial_channels=[CANAL]
        )
        # Variables de tiempo y estado
        self.ultimo_mensaje = time.time()
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM"]
        
        # Estados de los minijuegos
        self.ahorcado_activo = False
        self.ahorcado_palabra = ""
        self.ahorcado_adivinadas = set()
        self.ahorcado_intentos = 6
        
        self.ttt_activo = False
        self.ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

        self.num_activo = False
        self.num_secreto = 0
        
        self.vf_activo = False
        self.vf_respuesta = ""

        self.trivia_activo = False
        self.trivia_respuesta = ""

    async def event_ready(self):
        print(f'¡Conectado a Twitch como {self.nick}!')
        print(f'Escuchando el canal: {CANAL}')
        self.loop.create_task(self.animar_chat_automatico())

    async def event_message(self, message):
        if message.echo:
            return
        self.ultimo_mensaje = time.time()
        await self.handle_commands(message)

    # ----------------------------------------
    # COMANDOS DE AYUDA Y LISTADO
    # ----------------------------------------
    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        msg = ("🤖 Comandos: !ia (Habla con la IA) | "
               "🎮 Juegos Largos: !ahorcado, !3enraya, !adivinar, !vf (Verdadero/Falso), !trivia | "
               "🎲 Juegos Rápidos: !ruleta, !ppt, !moneda, !bola8, !amor @usuario")
        await ctx.send(msg)

    # ----------------------------------------
    # ANIMADOR AUTOMÁTICO (IA)
    # ----------------------------------------
    async def animar_chat_automatico(self):
        while True:
            await asyncio.sleep(60)
            if time.time() - self.ultimo_mensaje > 180:
                canal_obj = self.get_channel(CANAL)
                if not canal_obj:
                    continue
                try:
                    if ai_client:
                        prompt_autonomo = f"Eres el bot moderador en el canal de Twitch de un DJ que pincha música Remember, Trance y Eurodance. El chat lleva inactivo 3 minutos. Escribe un mensaje CORTO (máximo 120 caracteres) para animar, hacer una pregunta musical, o incitar a bailar. Usa este emote: {random.choice(self.emotes_twitch)}"
                        response = ai_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_autonomo,
                        )
                        mensaje_animacion = response.text.strip().replace('\n', ' ')
                    else:
                        frases = [
                            f"¡Que no decaiga la fiesta familia! {random.choice(self.emotes_twitch)}",
                            f"¿Alguna petición remember para la sesión de hoy? Os leo 👀"
                        ]
                        mensaje_animacion = random.choice(frases)
                    
                    await canal_obj.send(mensaje_animacion)
                except Exception as e:
                    print(f"Error IA automática: {e}")
                self.ultimo_mensaje = time.time()

    # ----------------------------------------
    # IA MANUAL
    # ----------------------------------------
    @commands.command(name='ia')
    async def ia_command(self, ctx: commands.Context):
        if not ai_client: return await ctx.send("La IA no está configurada.")
        prompt = ctx.message.content.replace('!ia', '').strip()
        if not prompt: return await ctx.send("Pregunta algo: !ia ¿Qué es el Eurodance?")
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            respuesta = response.text.strip().replace('\n', ' ')
            await ctx.send(f"@{ctx.author.name} {respuesta[:447] + '...' if len(respuesta)>450 else respuesta}")
        except:
            await ctx.send(f"@{ctx.author.name} Error con la IA.")

    # ----------------------------------------
    # JUEGO: VERDADERO O FALSO
    # ----------------------------------------
    @commands.command(name='vf')
    async def vf_start(self, ctx: commands.Context):
        if self.vf_activo: return await ctx.send("¡Ya hay un Verdadero/Falso activo! Responde con !v o !f")
        
        preguntas = [
            ("El estilo Trance se originó en Alemania en los 90s.", "V"),
            ("El vinilo fue inventado en el año 2005.", "F"),
            ("El Pioneer CDJ-1000 revolucionó el mundo DJ en 2001.", "V"),
            ("El Eurodance mezcla House, Synthpop y Rap.", "V"),
            ("Techno y House son exactamente el mismo género.", "F")
        ]
        pregunta, self.vf_respuesta = random.choice(preguntas)
        self.vf_activo = True
        await ctx.send(f"🧠 VERDADERO O FALSO: {pregunta} (Responde con !v o !f)")

    @commands.command(name='v')
    async def vf_v(self, ctx: commands.Context):
        if not self.vf_activo: return
        self.vf_activo = False
        if self.vf_respuesta == "V": await ctx.send(f"✅ ¡CORRECTO @{ctx.author.name}! Era VERDADERO.")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era FALSO.")

    @commands.command(name='f')
    async def vf_f(self, ctx: commands.Context):
        if not self.vf_activo: return
        self.vf_activo = False
        if self.vf_respuesta == "F": await ctx.send(f"✅ ¡CORRECTO @{ctx.author.name}! Era FALSO.")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era VERDADERO.")

    # ----------------------------------------
    # JUEGO: AHORCADO (Visualización mejorada)
    # ----------------------------------------
    @commands.command(name='ahorcado')
    async def ahorcado_start(self, ctx: commands.Context):
        if self.ahorcado_activo: return await ctx.send("¡Ya hay un juego activo! Usa !letra <letra>")
            
        palabras = ["TEMAZO", "TRAKTOR", "TRANCE", "REMIX", "STREAM", "EURODANCE", "HARDDANCE", "PIONEER", "VINILO", "FESTIVAL"]
        self.ahorcado_palabra = random.choice(palabras)
        self.ahorcado_adivinadas = set()
        self.ahorcado_intentos = 6
        self.ahorcado_activo = True
        
        # Muestra formato: _ _ _ _ _
        oculto = " ".join(["_" for _ in self.ahorcado_palabra])
        await ctx.send(f"🎮 ¡Ahorcado! Palabra: {oculto} | Intentos: {self.ahorcado_intentos}. Usa !letra A")

    @commands.command(name='letra')
    async def ahorcado_play(self, ctx: commands.Context):
        if not self.ahorcado_activo: return
        msg = ctx.message.content.split()
        if len(msg) < 2: return
            
        letra = msg[1].upper()
        if len(letra) != 1: return await ctx.send("Dime solo UNA letra.")
        if letra in self.ahorcado_adivinadas: return await ctx.send("Ya dijiste esa letra.")
            
        self.ahorcado_adivinadas.add(letra)
        if letra not in self.ahorcado_palabra: self.ahorcado_intentos -= 1
            
        # Reconstruye la palabra mostrando las acertadas y ocultando con "_" las restantes
        oculto = " ".join([l if l in self.ahorcado_adivinadas else "_" for l in self.ahorcado_palabra])
        
        if "_" not in oculto:
            self.ahorcado_activo = False
            await ctx.send(f"🏆 ¡GANASTE @{ctx.author.name}! La palabra era: {self.ahorcado_palabra}.")
        elif self.ahorcado_intentos <= 0:
            self.ahorcado_activo = False
            await ctx.send(f"💀 ¡AHORCADO! Perdisteis. La palabra era: {self.ahorcado_palabra}.")
        else:
            await ctx.send(f"Palabra: {oculto} | Intentos restantes: {self.ahorcado_intentos}")

    # ----------------------------------------
    # JUEGO: TRIVIA RÁPIDO
    # ----------------------------------------
    @commands.command(name='trivia')
    async def trivia_start(self, ctx: commands.Context):
        if self.trivia_activo: return await ctx.send("¡Ya hay un trivia activo! Responde con !r <respuesta>")
        preguntas = [
            ("¿Cuántos BPM suele tener el Hardstyle? (A) 120 (B) 150 (C) 90", "B"),
            ("¿Qué significa DJ? (A) Disc Jockey (B) Dance Jam (C) Digital Juke", "A"),
            ("¿En qué década nació el Eurodance? (A) 70s (B) 80s (C) 90s", "C")
        ]
        pregunta, self.trivia_respuesta = random.choice(preguntas)
        self.trivia_activo = True
        await ctx.send(f"💡 TRIVIA: {pregunta} (Responde con !r A, !r B o !r C)")

    @commands.command(name='r')
    async def trivia_play(self, ctx: commands.Context):
        if not self.trivia_activo: return
        msg = ctx.message.content.split()
        if len(msg) < 2: return
        intento = msg[1].upper()
        
        self.trivia_activo = False
        if intento == self.trivia_respuesta:
            await ctx.send(f"🎉 ¡@{ctx.author.name} ACERTÓ la respuesta ({self.trivia_respuesta})!")
        else:
            await ctx.send(f"❌ Fallaste @{ctx.author.name}. La correcta era la {self.trivia_respuesta}.")

    # ----------------------------------------
    # JUEGOS RÁPIDOS Y SOCIALES
    # ----------------------------------------
    @commands.command(
