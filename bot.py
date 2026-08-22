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
CANAL = os.environ.get('TWITCH_CANAL', 'sesionesoldschool').lower()

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

        # Minijuegos clásicos
        self.ahorcado_activo = False
        self.ahorcado_palabra = ""
        self.ahorcado_adivinadas = set()
        self.ahorcado_intentos = 6
        self.ttt_activo = False
        self.ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        
        # Minijuegos Arcade
        self.pelea_activa = False
        self.peleador_1 = None
        self.peleador_2 = None
        self.vida_p1 = 100
        self.vida_p2 = 100
        self.turno_pelea = None

        self.invasion_activa = False
        self.alien_vida = 100
        
        # Inicializar el texto de OBS vacío
        self.actualizar_txt_obs("🎮 Arcade Inactivo - ¡Escribe !invasion o !pelea!")

    def actualizar_txt_obs(self, texto):
        try:
            with open("estado_juego.txt", "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            print(f"Error al escribir estado_juego.txt: {e}")

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
        
        # Comprobar si mencionan al canal (@sesionesoldschool) para activar la IA
        mencion_canal = f"@{CANAL}".lower()
        if mencion_canal in content.lower():
            if ai_client:
                try:
                    prompt_usuario = content.lower().replace(mencion_canal, "").strip()
                    if not prompt_usuario:
                        prompt_usuario = "¡Hola tío!"
                        
                    contexto_actual = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt_final = f"Historial del chat: [{contexto_actual}]\n\n{message.author.name} te menciona diciendo: '{prompt_usuario}'. Resóndele de forma natural."
                    
                    response = ai_client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt_final,
                        config={
                            'system_instruction': (
                                f"Eres una persona real, un colega más y viewer habitual en el canal de Twitch de {CANAL}. "
                                "Hablas de tú, con total naturalidad, jerga coloquial de España (tío, mola, brutal, crack, etc.). "
                                "PROHIBIDO sonar como asistente o bot. Breve y directo (máx 250 caracteres)."
                            ),
                        }
                    )
                    texto_respuesta = response.text if response and response.text else "¡Qué pasa tío! Totalmente de acuerdo. 🔥"
                    await message.channel.send(f"@{message.author.name} {texto_respuesta.strip()[:350]}")
                except Exception as e:
                    print(f"[ERROR GEMINI MENCION] {e}")
                    await message.channel.send(f"@{message.author.name} ¡Vaya temazo está sonando! 🎧🔥")

        # Comprobar comandos personalizados
        if content.startswith('!'):
            partes = content[1:].split(' ', 1)
            nombre_cmd = partes[0].lower()
            
            if nombre_cmd in self.comandos_custom:
                await message.channel.send(self.comandos_custom[nombre_cmd])
                return

        await self.handle_commands(message)

        # Intervención espontánea ocasional en el chat
        if not message.content.startswith('!') and random.random() < 0.25 and ai_client and mencion_canal not in content.lower():
            try:
                canal_obj = self.get_channel(CANAL)
                if canal_obj:
                    contexto_completo = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt = f"Conversación actual en el chat:\n[{contexto_completo}]\n\nOpina, ríete o suelta un comentario corto a lo que se está hablando, como un usuario más del chat."
                    
                    response = ai_client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt,
                        config={
                            'system_instruction': (
                                f"Eres un colega más en el chat de Twitch de {CANAL}. Eres un espectador humano, "
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
                                model='gemini-3.5-flash',
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

    # ==================== COMANDOS ARCADE (CON REFLEJO EN OBS) ====================

    @commands.command(name='pelea')
    async def cmd_pelea(self, ctx: commands.Context):
        msg = ctx.message.content.split()
        if len(msg) < 2:
            return await ctx.send(f"@{ctx.author.name} ¡Debes retar a alguien! Usa: !pelea @usuario")
        
        rival = msg[1].replace('@', '')
        if rival.lower() == ctx.author.name.lower():
            return await ctx.send(f"@{ctx.author.name} No puedes pegarte a ti mismo, máquina. 🥊")

        self.pelea_activa = True
        self.invasion_activa = False
        self.peleador_1 = ctx.author.name
        self.peleador_2 = rival
        self.vida_p1 = 100
        self.vida_p2 = 100
        self.turno_pelea = self.peleador_1

        info_obs = f"🥊 DUELO: @{self.peleador_1} (❤️{self.vida_p1}) VS @{self.peleador_2} (❤️{self.vida_p2}) | Turno: @{self.turno_pelea}"
        self.actualizar_txt_obs(info_obs)

        await ctx.send(f"🕹️ ¡DUELO ARCADE! 🥊 @{self.peleador_1} VS @{self.peleador_2}! Turno de @{self.turno_pelea}. Usa `!atacar` o `!defender`")

    @commands.command(name='atacar')
    async def cmd_atacar(self, ctx: commands.Context):
        if not self.pelea_activa: return
        autor = ctx.author.name.lower()

        if autor != self.peleador_1.lower() and autor != self.peleador_2.lower():
            return
        if autor != self.turno_pelea.lower():
            return await ctx.send(f"⏳ @{ctx.author.name}, ¡espera tu turno!")

        danio = random.randint(15, 30)
        if autor == self.peleador_1.lower():
            self.vida_p2 -= danio
            if self.vida_p2 < 0: self.vida_p2 = 0
            self.turno_pelea = self.peleador_2
            
            info_obs = f"🥊 DUELO: @{self.peleador_1} (❤️{self.vida_p1}) VS @{self.peleador_2} (❤️{self.vida_p2}) | Turno: @{self.turno_pelea}"
            self.actualizar_txt_obs(info_obs)

            await ctx.send(f"💥 ¡@{self.peleador_1} atesta un golpe de {danio} de daño! ➔ Vida de @{self.peleador_2}: ❤️ {self.vida_p2}/100. Turno de @{self.peleador_2}")
            if self.vida_p2 == 0:
                self.pelea_activa = False
                self.actualizar_txt_obs(f"🏆 ¡Ganador de la pelea: @{self.peleador_1}! 🎉")
                await ctx.send(f"🏆 ¡VICTORIA! @{self.peleador_1} ha destrozado a @{self.peleador_2} en la recreativa. 🎉")
        else:
            self.vida_p1 -= danio
            if self.vida_p1 < 0: self.vida_p1 = 0
            self.turno_pelea = self.peleador_1
            
            info_obs = f"🥊 DUELO: @{self.peleador_1} (❤️{self.vida_p1}) VS @{self.peleador_2} (❤️{self.vida_p2}) | Turno: @{self.turno_pelea}"
            self.actualizar_txt_obs(info_obs)

            await ctx.send(f"💥 ¡@{self.peleador_2} ataca causando {danio} de daño! ➔ Vida de @{self.peleador_1}: ❤️ {self.vida_p1}/100. Turno de @{self.peleador_1}")
            if self.vida_p1 == 0:
                self.pelea_activa = False
                self.actualizar_txt_obs(f"🏆 ¡Ganador de la pelea: @{self.peleador_2}! 🎉")
                await ctx.send(f"🏆 ¡VICTORIA! @{self.peleador_2} se alza con el cinturón frente a @{self.peleador_1}. 🎉")

    @commands.command(name='defender')
    async def cmd_defender(self, ctx: commands.Context):
        if not self.pelea_activa: return
        autor = ctx.author.name.lower()
        if autor != self.turno_pelea.lower(): return

        cura = random.randint(10, 20)
        if autor == self.peleador_1.lower():
            self.vida_p1 += cura
            if self.vida_p1 > 100: self.vida_p1 = 100
            self.turno_pelea = self.peleador_2
            
            info_obs = f"🥊 DUELO: @{self.peleador_1} (❤️{self.vida_p1}) VS @{self.peleador_2} (❤️{self.vida_p2}) | Turno: @{self.turno_pelea}"
            self.actualizar_txt_obs(info_obs)
            await ctx.send(f"🛡️ @{self.peleador_1} se defiende y recupera vida (❤️ {self.vida_p1}/100). Turno de @{self.peleador_2}")
        else:
            self.vida_p2 += cura
            if self.vida_p2 > 100: self.vida_p2 = 100
            self.turno_pelea = self.peleador_1
            
            info_obs = f"🥊 DUELO: @{self.peleador_1} (❤️{self.vida_p1}) VS @{self.peleador_2} (❤️{self.vida_p2}) | Turno: @{self.turno_pelea}"
            self.actualizar_txt_obs(info_obs)
            await ctx.send(f"🛡️ @{self.peleador_2} se defiende y recupera vida (❤️ {self.vida_p2}/100). Turno de @{self.peleador_1}")

    @commands.command(name='invasion')
    async def cmd_invasion(self, ctx: commands.Context):
        if self.invasion_activa:
            return await ctx.send(f"👾 ¡Ya hay una invasión activa! Dispara con `!disparar`")
        
        self.invasion_activa = True
        self.pelea_activa = False
        self.alien_vida = 100
        
        self.actualizar_txt_obs(f"👾 JEFE ALIEN: 💚 {self.alien_vida}/100 HP | Usa !disparar")
        await ctx.send(f"🛸 ¡ALERTA DE INVASIÓN ARCADE! 👾 Un jefe espacial se acerca a la nave Remember (Vida: 💚 100/100). ¡A disparar con `!disparar`!")

    @commands.command(name='disparar')
    async def cmd_disparar(self, ctx: commands.Context):
        if not self.invasion_activa:
            return await ctx.send(f"@{ctx.author.name} No hay ninguna invasión activa. Lanza una con `!invasion`")
        
        impacto = random.randint(8, 18)
        self.alien_vida -= impacto
        if self.alien_vida < 0: self.alien_vida = 0

        self.actualizar_txt_obs(f"👾 JEFE ALIEN: 💚 {self.alien_vida}/100 HP | Último tiro: @{ctx.author.name}")

        if self.alien_vida == 0:
            self.invasion_activa = False
            self.actualizar_txt_obs("🚀 ¡Invasión repelida con éxito por el chat! 🎉")
            await ctx.send(f"🚀 ¡BLAM! @{ctx.author.name} metió el disparo definitivo. ¡Invasión repelida con éxito, equipo! 🎉🔥")
        else:
            await ctx.send(f"🎯 ¡Disparo de @{ctx.author.name}! (-{impacto} DMG). Vida del alien: 💚 {self.alien_vida}/100")

    # ==================== COMANDOS GENERALES Y CLÁSICOS ====================

    @commands.command(name='addcmd')
    async def cmd_add(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} No tienes permisos.")
        partes = ctx.message.content.split(' ', 2)
        if len(partes) < 3: return await ctx.send("Uso: !addcmd <nombre> <respuesta>")
        nombre = partes[1].lower().replace('!', '')
        self.comandos_custom[nombre] = partes[2]
        self.guardar_comandos_custom()
        await ctx.send(f"✅ ¡Comando '!{nombre}' creado!")

    @commands.command(name='delcmd')
    async def cmd_del(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} No tienes permisos.")
        partes = ctx.message.content.split(' ', 1)
        if len(partes) < 2: return await ctx.send("Uso: !delcmd <nombre>")
        nombre = partes[1].lower().replace('!', '')
        if nombre in self.comandos_custom:
            del self.comandos_custom[nombre]
            self.guardar_comandos_custom()
            await ctx.send(f"🗑️ ¡Comando '!{nombre}' borrado!")
        else:
            await ctx.send(f"❌ El comando '!{nombre}' no existe.")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        es_admin_o_mod = ctx.author.is_mod or ctx.author.name.lower() == CANAL.lower()
        customs = ", ".join([f"!{c}" for c in self.comandos_custom.keys()])
        custom_txt = f" | 📌 Custom: {customs}" if (es_admin_o_mod and customs) else ""
        await ctx.send(f"🤖 Habla conmigo usando @{CANAL} | 🕹️ Arcade: !pelea @user, !invasion, !3enraya, !ahorcado | 🎲 Extras: !festero, !amor, !ruleta{custom_txt}")

    @commands.command(name='normas')
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("⚠️ NORMAS: Respeto absoluto. ¡A disfrutar del Remember y el Hard Dance! 🎧")

    @commands.command(name='redes')
    async def cmd_redes(self, ctx: commands.Context):
        await ctx.send("🌐 Sígueme en los directos y redes para no perderte nada de Sesiones Old School.")

    @commands.command(name='prime')
    async def cmd_prime(self, ctx: commands.Context):
        await ctx.send("🔔 ¡Apoya con Amazon Prime! Consigue insignias y emotes exclusivos.")

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
