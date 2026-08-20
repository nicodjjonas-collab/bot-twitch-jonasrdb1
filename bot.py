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
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET, 
            prefix='!',
            initial_channels=[CANAL]
        )
        # Variables de tiempo y estado
        self.ultimo_mensaje = time.time()
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm", "ResidentSleeper", "FireChest"]
        self.ultimos_mensajes_chat = []  # Memoria temporal de los últimos mensajes del chat para contexto
        
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
        print(f'¡Conectado a Twitch exitosamente!')
        print(f'Escuchando el canal: {CANAL}')
        self.loop.create_task(self.animar_chat_autonomo())

    # Función para comprobar si el canal está en directo
    async def esta_en_directo(self) -> bool:
        try:
            streams = await self.fetch_streams(user_logins=[CANAL])
            return len(streams) > 0
        except Exception as e:
            print(f"Error comprobando el estado del directo: {e}")
            return False

    async def event_message(self, message):
        if message.echo:
            return
        
        # Si el canal está offline, ignorar por completo
        if not await self.esta_en_directo():
            return

        self.ultimo_mensaje = time.time()
        
        # Guardar en memoria los últimos mensajes del chat para dar contexto a la IA
        self.ultimos_mensajes_chat.append(f"{message.author.name}: {message.content}")
        if len(self.ultimos_mensajes_chat) > 10:
            self.ultimos_mensajes_chat.pop(0)

        # Si alguien le habla directamente al bot o usa comandos, procesarlo
        await self.handle_commands(message)

        # Ocasionalmente (probabilidad del 25%), si el mensaje no es un comando, la IA decide intervenir de forma natural como uno más
        if not message.content.startswith('!') and random.random() < 0.25 and ai_client:
            try:
                canal_obj = self.get_channel(CANAL)
                if canal_obj:
                    contexto_chat = " | ".join(self.ultimos_mensajes_chat[-5:])
                    prompt = (
                        f"Eres un espectador más y un colega fiestero en el chat del canal de Twitch de un DJ de música Remember, Trance, Eurodance y Hard Dance. "
                        f"Estás viendo el directo. Contexto reciente del chat: [{contexto_chat}]. "
                        f"El último mensaje fue de {message.author.name}: '{message.content}'. "
                        f"Responde de forma natural, corta (máximo 120 caracteres), informal, como un usuario real más, opinando o tirando buen rollo. "
                        f"Usa obligatoriamente al menos uno de estos emotes de Twitch: {random.choice(self.emotes_twitch)}"
                    )
                    response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    respuesta = response.text.strip().replace('\n', ' ')
                    await canal_obj.send(respuesta[:150])
            except Exception as e:
                print(f"Error en intervención espontánea: {e}")

    # ----------------------------------------
    # COMANDOS DE AYUDA Y LISTADO
    # ----------------------------------------
    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        msg = ("🤖 IA: !ia <pregunta> | "
               "🎮 Juegos: !ahorcado, !3enraya, !adivinar, !vf, !trivia | "
               "📌 Info: !normas, !redes, !prime | "
               "🎲 Diversión: !festero, !amor @usuario, !ruleta, !ppt, !moneda, !bola8")
        await ctx.send(msg)

    # ----------------------------------------
    # COMANDOS DE INFORMACIÓN
    # ----------------------------------------
    @commands.command(name='normas')
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("⚠️ NORMAS DEL CHAT ⚠️ Respeta un lenguaje educado, cero ataques personales y tolerancia cero con el odio o acoso. Incumplirlas = BAN PERMANENTE. 🎧 ¡Disfruta del Hard Dance!")

    @commands.command(name='redes')
    async def cmd_redes(self, ctx: commands.Context):
        await ctx.send("🌐 Sígueme en mis redes y canales oficiales para estar al día de todas las sesiones Remember, Hard Dance y Trance de JONAS RDB.")

    @commands.command(name='prime')
    async def cmd_prime(self, ctx: commands.Context):
        await ctx.send("🔔 ¡SUSCRÍBETE GRATIS CON AMAZON PRIME! Consigue insignias, emotes exclusivos, directos sin anuncios y participa en sorteos exclusivos. ¡Únete a la rave! JONAS RDB // HARD DANCE 🖤")

    # ----------------------------------------
    # INTELIGENCIA ARTIFICIAL AUTÓNOMA Y ANIMADOR
    # ----------------------------------------
    async def animar_chat_autonomo(self):
        while True:
            await asyncio.sleep(75) # Comprueba cada poco tiempo
            if not await self.esta_en_directo():
                continue

            # Si el chat lleva más de 2 minutos inactivo, la IA toma la iniciativa por completo para romper el hielo
            if time.time() - self.ultimo_mensaje > 120:
                canal_obj = self.get_channel(CANAL)
                if not canal_obj:
                    continue
                try:
                    if ai_client:
                        prompt_autonomo = (
                            f"Eres un espectador veterano y súper activo en el canal de Twitch del DJ Jonas RDB, centrado en música Remember, Trance, Eurodance y Hard Dance. "
                            f"El chat lleva un par de minutos tranquilo. Escribe un mensaje corto y espontáneo (máximo 130 caracteres) como si estuvieras allí bailando, preguntando qué temazo está sonando o animando a la gente. "
                            f"Usa obligatoriamente este emote: {random.choice(self.emotes_twitch)}"
                        )
                        response = ai_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_autonomo,
                        )
                        mensaje_animacion = response.text.strip().replace('\n', ' ')
                    else:
                        mensaje_animacion = f"¡Vaya pepinazo de sesión! ¿De qué año es este tema familia? {random.choice(self.emotes_twitch)}"
                    
                    await canal_obj.send(mensaje_animacion)
                    self.ultimo_mensaje = time.time()
                except Exception as e:
                    print(f"Error en bucle autónomo: {e}")

    # ----------------------------------------
    # IA MANUAL (!ia)
    # ----------------------------------------
    @commands.command(name='ia')
    async def ia_command(self, ctx: commands.Context):
        if not ai_client: return await ctx.send("La IA no está configurada.")
        prompt = ctx.message.content.replace('!ia', '').strip()
        if not prompt: return await ctx.send("Dime algo para hablar: !ia ¿Qué te parece este tema?")
        try:
            prompt_sistema = (
                f"Eres un usuario más del chat en el canal de Twitch de Jonas RDB (DJ de música Remember y Hard Dance). "
                f"Responde a {ctx.author.name} de forma cercana, amigable, como un colega fiestero, opinando sobre música electrónica y cultura de club. "
                f"Añade al menos un emote como {random.choice(self.emotes_twitch)}. Pregunta: {prompt}"
            )
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_sistema)
            respuesta = response.text.strip().replace('\n', ' ')
            await ctx.send(f"@{ctx.author.name} {respuesta[:430]}")
        except:
            await ctx.send(f"@{ctx.author.name} ¡Uy, me he quedado rayado con el beat! Prueba otra vez. 😅")

    # ----------------------------------------
    # MEDIDOR DE FIESTA
    # ----------------------------------------
    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        porcentaje = random.randint(0, 100)
        if porcentaje < 20: reaccion = "Necesitas un buen temazo hard dance para despertar. 😴"
        elif porcentaje < 50: reaccion = "Estás calentando motores poco a poco. 🎵"
        elif porcentaje < 80: reaccion = "¡Ya estás a tope para darlo todo en la pista! 🕺💃"
        else: reaccion = "¡DIOS MÍO! ¡Eres el alma de la fiesta! 🔥🎶"
        await ctx.send(f"🎉 @{ctx.author.name} tiene un {porcentaje}% de ganas de fiesta hoy. {reaccion}")

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
        if self.vf_respuesta == "V": await ctx.send(f"✅ ¡CORRECTO @{ctx.author.name}! Era VERDADERO. 🔥")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era FALSO. 😜")

    @commands.command(name='f')
    async def vf_f(self, ctx: commands.Context):
        if not self.vf_activo: return
        self.vf_activo = False
        if self.vf_respuesta == "F": await ctx.send(f"✅ ¡CORRECTO @{ctx.author.name}! Era FALSO. 🔥")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era VERDADERO. 😜")

    # ----------------------------------------
    # JUEGO: AHORCADO
    # ----------------------------------------
    @commands.command(name='ahorcado')
    async def ahorcado_start(self, ctx: commands.Context):
        if self.ahorcado_activo: return await ctx.send("¡Ya hay un juego activo! Usa !letra <letra>")
        palabras = ["TEMAZO", "TRAKTOR", "TRANCE", "REMIX", "STREAM", "EURODANCE", "HARDDANCE", "PIONEER", "VINILO", "FESTIVAL"]
        self.ahorcado_palabra = random.choice(palabras)
        self.ahorcado_adivinadas = set()
        self.ahorcado_intentos = 6
        self.ahorcado_activo = True
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
        oculto = " ".join([l if l in self.ahorcado_adivinadas else "_" for l in self.ahorcado_palabra])
        if "_" not in oculto:
            self.ahorcado_activo = False
            await ctx.send(f"🏆 ¡Qué máquina @{ctx.author.name}! Has ganado el ahorcado. La palabra era: {self.ahorcado_palabra}.")
        elif self.ahorcado_intentos <= 0:
            self.ahorcado_activo = False
            await ctx.send(f"💀 ¡Game Over! Os habéis quedado sin intentos. Era: {self.ahorcado_palabra}.")
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
            await ctx.send(f"🎉 ¡T Toma ya, @{ctx.author.name} ha acertado ({self.trivia_respuesta})!")
        else:
            await ctx.send(f"❌ Casi, @{ctx.author.name}. La correcta era la {self.trivia_respuesta}.")

    # ----------------------------------------
    # JUEGOS RÁPIDOS Y SOCIALES
    # ----------------------------------------
    @commands.command(name='amor')
    async def amor(self, ctx: commands.Context):
        msg = ctx.message.content.split()
        if len(msg) < 2: return await ctx.send("Menciona a alguien: !amor @usuario")
        porcentaje = random.randint(0, 100)
        await ctx.send(f"💘 El nivel de amor musical entre @{ctx.author.name} y {msg[1]} es del {porcentaje}%!")

    @commands.command(name='ruleta')
    async def ruleta(self, ctx: commands.Context):
        if random.randint(1, 6) == 1: await ctx.send(f"💥 ¡PUM! @{ctx.author.name} se ha eliminado de la sesión. F 💀")
        else: await ctx.send(f"💨 *Click*... Te has salvado de milagro, @{ctx.author.name}. 😅")

    @commands.command(name='moneda')
    async def moneda(self, ctx: commands.Context):
        await ctx.send(f"🪙 @{ctx.author.name} tira la moneda... ¡Sale {random.choice(['Cara 🪙', 'Cruz ❌'])}!")

    @commands.command(name='bola8')
    async def bola8(self, ctx: commands.Context):
        if len(ctx.message.content.split()) < 2: return await ctx.send("Pregúntale algo a la bola: !bola8 <pregunta>")
        respuestas = ["Sí, totalmente.", "Es más que seguro.", "Sin ninguna duda.", "Ni de broma.", "No cuentes con ello.", "Mis fuentes dicen que no."]
        await ctx.send(f"🎱 @{ctx.author.name}: {random.choice(respuestas)}")

    @commands.command(name='ppt')
    async def ppt(self, ctx: commands.Context):
        opciones = ["piedra", "papel", "tijera"]
        msg = ctx.message.content.lower().split()
        if len(msg) < 2 or msg[1] not in opciones: return await ctx.send("Usa: !ppt <piedra|papel|tijera>")
        bot_elige = random.choice(opciones)
        j = msg[1]
        res = "¡Empate! 🤝" if j == bot_elige else "¡Me ganaste! 🎉" if (j=="piedra" and bot_elige=="tijera") or (j=="papel" and bot_elige=="piedra") or (j=="tijera" and bot_elige=="papel") else "¡Gano yo, máquina! 🤖"
        await ctx.send(f"Elegiste {j}, yo saqué {bot_elige}. {res}")

    # ----------------------------------------
    # JUEGO: ADIVINAR EL NÚMERO
    # ----------------------------------------
    @commands.command(name='adivinar')
    async def start_adivinar(self, ctx: commands.Context):
        if self.num_activo: return await ctx.send("¡Ya hay un número activo! Adivina con !n <numero>")
        self.num_secreto = random.randint(1, 100)
        self.num_activo = True
        await ctx.send("🔢 He pensado un número del 1 al 100. ¡Adivina con !n <numero>")

    @commands.command(name='n')
    async def play_adivinar(self, ctx: commands.Context):
        if not self.num_activo: return
        try: intento = int(ctx.message.content.split()[1])
        except: return
        if intento == self.num_secreto:
            self.num_activo = False
            await ctx.send(f"🎉 ¡BRUTAL @{ctx.author.name}! Has acertado el número secreto ({self.num_secreto}).")
        elif intento < self.num_secreto: await ctx.send(f"🔼 ¡Sube más, @{ctx.author.name}!")
        else: await ctx.send(f"🔽 ¡Baja, @{ctx.author.name}!")

    # ----------------------------------------
    # JUEGO: 3 EN RAYA
    # ----------------------------------------
    @commands.command(name='3enraya')
    async def ttt_start(self, ctx: commands.Context):
        self.ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.ttt_activo = True
        t = self.ttt_tablero
        await ctx.send(f"🎮 3 en raya contra el bot. Eres las X. Usa !casilla <1-9>. Tablero: [{t[0]}][{t[1]}][{t[2]}] - [{t[3]}][{t[4]}][{t[5]}] - [{t[6]}][{t[7]}][{t[8]}]")

    @commands.command(name='casilla')
    async def ttt_play(self, ctx: commands.Context):
        if not self.ttt_activo: return
        try:
            c = int(ctx.message.content.split()[1]) - 1
            if c < 0 or c > 8 or self.ttt_tablero[c] in ['X', 'O']: return await ctx.send("Casilla inválida o ya ocupada.")
        except: return

        self.ttt_tablero[c] = 'X'
        if self.check_ganador('X'):
            self.ttt_activo = False
            return await ctx.send(f"🎉 ¡Impresionante @{ctx.author.name}, me has ganado al 3 en raya!")

        libres = [i for i, x in enumerate(self.ttt_tablero) if x not in ['X', 'O']]
        if not libres:
            self.ttt_activo = False
            return await ctx.send("🤝 ¡Empate técnico en el tablero!")
            
        self.ttt_tablero[random.choice(libres)] = 'O'
        if self.check_ganador('O'):
            self.ttt_activo = False
            t = self.ttt_tablero
            return await ctx.send(f"🤖 ¡Te gané! Tablero final: [{t[0]}][{t[1]}][{t[2]}] - [{t[3]}][{t[4]}][{t[5]}] - [{t[6]}][{t[7]}][{t[8]}]")

        t = self.ttt_tablero
        await ctx.send(f"🤖 Mi turno... Tablero: [{t[0]}][{t[1]}][{t[2]}] - [{t[3]}][{t[4]}][{t[5]}] - [{t[6]}][{t[7]}][{t[8]}]")

    def check_ganador(self, f):
        t = self.ttt_tablero
        for a, b, c in [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]:
            if t[a] == t[b] == t[c] == f: return True
        return False

if __name__ == '__main__':
    if not TOKEN or not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR CRÍTICO: Faltan variables de entorno esenciales en Railway.")
    else:
        bot = Bot()
        bot.run()
