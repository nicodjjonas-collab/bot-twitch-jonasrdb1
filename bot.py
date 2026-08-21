import os
import random
import time
import json
import asyncio
import traceback
import twitchio
from twitchio.ext import commands
from google import genai

TOKEN = os.environ.get('TWITCH_TOKEN', '').strip()
BOT_NICK = os.environ.get('TWITCH_BOT', 'jonasrdb').lower() 
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb').lower()

GEMINI_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

print(f"[INIT] Arrancando bot asíncrono para el canal: {CANAL}")

ai_client = None
if GEMINI_KEY:
    try:
        os.environ['GEMINI_API_KEY'] = GEMINI_KEY
        ai_client = genai.Client()
        print("[INIT] Gemini conectado correctamente.")
    except Exception as e:
        print(f"[INIT] Error crítico al iniciar Gemini: {e}")
else:
    print("[INIT] AVISO: No se encontró la clave de Gemini.")

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=[CANAL]
        )
        self.ultimo_mensaje = time.time()
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm"]
        self.ultimos_mensajes_chat = []  
        
        self.archivo_comandos = "comandos_custom.json"
        self.comandos_custom = self.cargar_comandos_custom()

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

    def cargar_comandos_custom(self):
        if os.path.exists(self.archivo_comandos):
            try:
                with open(self.archivo_comandos, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar comandos custom: {e}")
        return {}

    def guardar_comandos_custom(self):
        try:
            with open(self.archivo_comandos, 'w', encoding='utf-8') as f:
                json.dump(self.comandos_custom, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar comandos custom: {e}")

    async def event_ready(self):
        print(f'=== ¡BOT CONECTADO Y ESCUCHANDO EN EL CANAL: {CANAL} ===')
        asyncio.create_task(self.bucle_autonomo_chat())

    async def event_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return  
        print(f"[ERROR COMANDO] {error}")

    async def event_message(self, message):
        print(f"[CHAT] {message.author.name if message.author else 'Sistema'}: {message.content}")
        if message.echo:
            return

        self.ultimo_mensaje = time.time()
        
        self.ultimos_mensajes_chat.append(f"{message.author.name}: {message.content}")
        if len(self.ultimos_mensajes_chat) > 15:
            self.ultimos_mensajes_chat.pop(0)

        content = message.content.strip()
        if content.startswith('!'):
            partes = content[1:].split(' ', 1)
            nombre_cmd = partes[0].lower()
            
            if nombre_cmd in self.comandos_custom:
                await message.channel.send(self.comandos_custom[nombre_cmd])
                return

        await self.handle_commands(message)

        if not message.content.startswith('!') and random.random() < 0.25 and ai_client:
            try:
                canal_obj = self.get_channel(CANAL)
                if canal_obj:
                    contexto_completo = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt = f"Conversación actual en el chat:\n[{contexto_completo}]\n\nOpina, ríete o suelta un comentario corto a lo que se está hablando, como un usuario más del chat."
                    
                    response = ai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config={
                            'system_instruction': (
                                "Eres un colega más en el chat de Twitch de Jonas RDB. Eres un espectador humano, "
                                "hablas en español de España con total naturalidad (tío, mola, brutal, qué pasada, etc.). "
                                "NUNCA digas que eres una IA o un asistente. No saludes formalmente. Sé súper breve y directo."
                            ),
                        }
                    )
                    texto_ia = response.text if response and response.text else "¡Totalmente de acuerdo tío! 🔥"
                    await canal_obj.send(f"{texto_ia.strip().replace(chr(10), ' ')} {random.choice(self.emotes_twitch)}")
            except Exception as e:
                print(f"Error IA espontánea: {e}")

    async def bucle_autonomo_chat(self):
        asyncio.create_task(self._bucle_real())

    async def _bucle_real(self):
        await asyncio.sleep(20)
        while True:
            try:
                await asyncio.sleep(120)
                if time.time() - self.ultimo_mensaje > 180:
                    canal_obj = self.get_channel(CANAL)
                    if canal_obj:
                        if ai_client:
                            contexto_previo = " | ".join(self.ultimos_mensajes_chat[-5:]) if self.ultimos_mensajes_chat else "Silencio en el chat."
                            prompt = f"El chat lleva un rato tranquilo. Últimas cosas dichas: [{contexto_previo}]. Suelta un comentario guapo sobre la música Remember, la sesión o para romper el hielo como un colega."
                            response = ai_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt,
                                config={
                                    'system_instruction': "Eres un colega más en el chat de Twitch. Escribe corto, súper natural, como si estuvieras viendo el directo desde el sofá.",
                                }
                            )
                            msg = (response.text if response and response.text else "¡Menuda sesión nos estamos pegando!").replace('\n', ' ')
                        else:
                            msg = f"¡Vaya temazos de sesión familia! {random.choice(self.emotes_twitch)}"
                        await canal_obj.send(f"{msg} {random.choice(self.emotes_twitch)}")
                        self.ultimo_mensaje = time.time()
            except Exception as e:
                print(f"Error bucle autónomo: {e}")

    @commands.command(name='addcmd')
    async def cmd_add(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} No tienes permisos para crear comandos.")
        
        partes = ctx.message.content.split(' ', 2)
        if len(partes) < 3:
            return await ctx.send(f"@{ctx.author.name} Uso correcto: !addcmd <nombre> <respuesta>")
        
        nombre = partes[1].lower().replace('!', '')
        respuesta = partes[2]
        
        self.comandos_custom[nombre] = respuesta
        self.guardar_comandos_custom()
        await ctx.send(f"✅ ¡Comando '!{nombre}' creado correctamente, máquina!")

    @commands.command(name='delcmd')
    async def cmd_del(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} No tienes permisos para borrar comandos.")
        
        partes = ctx.message.content.split(' ', 1)
        if len(partes) < 2:
            return await ctx.send(f"@{ctx.author.name} Uso correcto: !delcmd <nombre>")
        
        nombre = partes[1].lower().replace('!', '')
        
        if nombre in self.comandos_custom:
            del self.comandos_custom[nombre]
            self.guardar_comandos_custom()
            await ctx.send(f"🗑️ ¡Comando '!{nombre}' borrado con éxito!")
        else:
            await ctx.send(f"❌ El comando '!{nombre}' no existe en los personalizados.")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        es_admin_o_mod = ctx.author.is_mod or ctx.author.name.lower() == CANAL.lower()
        customs = ", ".join([f"!{c}" for c in self.comandos_custom.keys()])
        custom_txt = f" | 📌 Custom (Mod): {customs}" if (es_admin_o_mod and customs) else ""
        await ctx.send(f"🤖 IA: !ia o !hola | 🎮 Juegos: !ahorcado, !3enraya, !adivinar, !vf, !trivia | 🎲 Extras: !festero, !amor, !ruleta{custom_txt}")

    @commands.command(name='normas')
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("⚠️ NORMAS: Respeto absoluto. ¡A disfrutar del Remember y el Hard Dance! 🎧")

    @commands.command(name='redes')
    async def cmd_redes(self, ctx: commands.Context):
        await ctx.send("🌐 Sígueme en los directos y redes para no perderte nada de JONAS RDB.")

    @commands.command(name='prime')
    async def cmd_prime(self, ctx: commands.Context):
        await ctx.send("🔔 ¡Apoya con Amazon Prime! Consigue insignias, emotes exclusivos y apoya las sesiones de JONAS RDB.")

    @commands.command(name='ia', aliases=['hola', 'chat'])
    async def ia_command(self, ctx: commands.Context):
        print(f"[DEBUG] Comando !ia ejecutado por: {ctx.author.name}")
        
        if not ai_client: 
            print("[DEBUG ERROR] ai_client es None. La API key de Gemini no está cargada.")
            return await ctx.send(f"@{ctx.author.name} Configura la clave de la API en el entorno.")
        
        content_parts = ctx.message.content.split(' ', 1)
        prompt_usuario = content_parts[1] if len(content_parts) > 1 else "¡Hola tío!"
        
        try:
            contexto_actual = " | ".join(self.ultimos_mensajes_chat[-8:])
            prompt_final = f"Historial del chat: [{contexto_actual}]\n\n{ctx.author.name} te dice directamente: '{prompt_usuario}'. Resóndele metiéndote en la conversación de forma natural."

            print(f"[DEBUG] Enviando prompt a Gemini...")
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_final,
                config={
                    'system_instruction': (
                        "Eres una persona real, un colega más y viewer habitual en el canal de Twitch de Jonas RDB. "
                        "Hablas de tú, con total naturalidad, jerga coloquial de España (tío, mola, brutal, ostras, crack, etc.), "
                        "opinando de lo que te digan y de lo que se hable en el chat. "
                        "PROHIBIDO absoluto sonar como un asistente, NUNCA digas cosas como '¿En qué puedo ayudarte?', 'Soy un bot', "
                        "ni actúes con formalidad. Eres un amigo más tomando algo mientras escucha la sesión de música Remember. "
                        "Responde de forma directa, corta y natural (máximo 250 caracteres)."
                    ),
                }
            )
            
            texto_respuesta = response.text if response and response.text else "¡Qué pasa tío! Totalmente de acuerdo. 🔥"
            print(f"[DEBUG] Respuesta recibida de Gemini: {texto_respuesta}")
            await ctx.send(f"@{ctx.author.name} {texto_respuesta.strip()[:350]}")
            
        except Exception as e:
            print(f"[ERROR GEMINI DETALLADO] Tipo: {type(e).__name__} | Mensaje: {e}")
            traceback.print_exc()
            # Mostramos el error exacto en el chat para diagnosticar qué pasa en la API
            await ctx.send(f"@{ctx.author.name} ERROR GEMINI: {type(e).__name__} - {str(e)[:150]}")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene un {random.randint(0,100)}% de ganas de fiesta hoy. 🔥")

    @commands.command(name='amor')
    async def amor(self, ctx: commands.Context):
        msg = ctx.message.content.split()
        if len(msg) < 2: return await ctx.send("Usa: !amor @usuario")
        await ctx.send(f"💘 Sintonía musical entre @{ctx.author.name} y {msg[1]}: {random.randint(0,100)}%!")

    @commands.command(name='ruleta')
    async def ruleta(self, ctx: commands.Context):
        if random.randint(1, 6) == 1: await ctx.send(f"💥 ¡PUM! @{ctx.author.name} eliminado de la sesión. F 💀")
        else: await ctx.send(f"💨 *Click*... Te salvaste por los pelos, @{ctx.author.name}. 😅")

    @commands.command(name='moneda')
    async def moneda(self, ctx: commands.Context):
        await ctx.send(f"🪙 @{ctx.author.name} tira la moneda... ¡Sale {random.choice(['Cara 🪙', 'Cruz ❌'])}!")

    @commands.command(name='bola8')
    async def bola8(self, ctx: commands.Context):
        if len(ctx.message.content.split()) < 2: return await ctx.send("Pregúntale algo: !bola8 <pregunta>")
        respuestas = ["Sí, totalmente.", "Es más que seguro.", "Sin ninguna duda.", "Ni de broma.", "No cuentes con ello."]
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

    @commands.command(name='ahorcado')
    async def ahorcado_start(self, ctx: commands.Context):
        if self.ahorcado_activo: return await ctx.send("¡Ya hay un ahorcado activo! Usa !letra <letra>")
        self.ahorcado_palabra = random.choice(["TEMAZO", "TRAKTOR", "TRANCE", "REMIX", "STREAM", "EURODANCE", "HARDDANCE", "PIONEER"])
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
        if len(letra) != 1 or letra in self.ahorcado_adivinadas: return
        self.ahorcado_adivinadas.add(letra)
        if letra not in self.ahorcado_palabra: self.ahorcado_intentos -= 1
        oculto = " ".join([l if l in self.ahorcado_adivinadas else "_" for l in self.ahorcado_palabra])
        if "_" not in oculto:
            self.ahorcado_activo = False
            await ctx.send(f"🏆 ¡Ganaste el ahorcado, @{ctx.author.name}! ({self.ahorcado_palabra})")
        elif self.ahorcado_intentos <= 0:
            self.ahorcado_activo = False
            await ctx.send(f"💀 ¡Game Over! Era: {self.ahorcado_palabra}.")
        else:
            await ctx.send(f"Palabra: {oculto} | Intentos: {self.ahorcado_intentos}")

    @commands.command(name='adivinar')
    async def start_adivinar(self, ctx: commands.Context):
        if self.num_activo: return await ctx.send("¡Número activo! Adivina con !n <numero>")
        self.num_secreto = random.randint(1, 50)
        self.num_activo = True
        await ctx.send("🔢 He pensado un número del 1 al 50. ¡Adivina con !n <numero>")

    @commands.command(name='n')
    async def play_adivinar(self, ctx: commands.Context):
        if not self.num_activo: return
        try: intento = int(ctx.message.content.split()[1])
        except: return
        if intento == self.num_secreto:
            self.num_activo = False
            await ctx.send(f"🎉 ¡Acertaste el número secreto ({self.num_secreto}), @{ctx.author.name}!")
        elif intento < self.num_secreto: await ctx.send(f"🔼 ¡Sube, @{ctx.author.name}!")
        else: await ctx.send(f"🔽 ¡Baja, @{ctx.author.name}!")

    @commands.command(name='vf')
    async def vf_start(self, ctx: commands.Context):
        if self.vf_activo: return await ctx.send("¡Ya hay un V/F activo! Responde con !v o !f")
        preguntas = [
            ("El estilo Trance se originó en los años 90.", "V"),
            ("El vinilo fue inventado en el año 2005.", "F"),
            ("El Eurodance mezcla House, Synthpop y Rap.", "V")
        ]
        pregunta, self.vf_respuesta = random.choice(preguntas)
        self.vf_activo = True
        await ctx.send(f"🧠 VERDADERO O FALSO: {pregunta} (Responde con !v o !f)")

    @commands.command(name='v')
    async def vf_v(self, ctx: commands.Context):
        if not self.vf_activo: return
        self.vf_activo = False
        if self.vf_respuesta == "V": await ctx.send(f"✅ ¡Correcto @{ctx.author.name}! Era VERDADERO. 🔥")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era FALSO. 😜")

    @commands.command(name='f')
    async def vf_f(self, ctx: commands.Context):
        if not self.vf_activo: return
        self.vf_activo = False
        if self.vf_respuesta == "F": await ctx.send(f"✅ ¡Correcto @{ctx.author.name}! Era FALSO. 🔥")
        else: await ctx.send(f"❌ ¡Fallaste @{ctx.author.name}! Era VERDADERO. 😜")

    @commands.command(name='trivia')
    async def trivia_start(self, ctx: commands.Context):
        if self.trivia_activo: return await ctx.send("¡Ya hay una trivia activa! Responde con !r <A/B/C>")
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
            await ctx.send(f"🎉 ¡Toma ya, @{ctx.author.name} ha acertado ({self.trivia_respuesta})!")
        else:
            await ctx.send(f"❌ Casi, @{ctx.author.name}. La correcta era la {self.trivia_respuesta}.")

    @commands.command(name='3enraya')
    async def ttt_start(self, ctx: commands.Context):
        self.ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.ttt_activo = True
        t = self.ttt_tablero
        await ctx.send(f"🎮 3 en raya. Eres las X. Usa !casilla <1-9>. Tablero: [{t[0]}][{t[1]}][{t[2]}] - [{t[3]}][{t[4]}][{t[5]}] - [{t[6]}][{t[7]}][{t[8]}]")

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

async def main():
    if not TOKEN:
        print("ERROR: Falta TWITCH_TOKEN.")
        return
    bot = Bot()
    await bot.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[RECONEXIÓN] Error: {e}")
        traceback.print_exc()
