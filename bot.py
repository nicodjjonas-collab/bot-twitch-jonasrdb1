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
BOT_NICK = os.environ.get('TWITCH_BOT', 'sesionesoldschool').lower() 
CANAL = os.environ.get('TWITCH_CANAL', 'jonasRdb').lower()

GEMINI_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

print(f"[INIT] Arrancando bot pro con Liga de Fieles para: {CANAL}")

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
        self.usuarios_saludados = set()
        
        # Archivos de persistencia
        self.archivo_comandos = "comandos_custom.json"
        self.comandos_custom = self.cargar_json(self.archivo_comandos, {})
        
        self.archivo_puntos = "puntos_usuarios.json"
        self.puntos = self.cargar_json(self.archivo_puntos, {})

        # Historial de música
        self.ultimos_temas = []

        # Estado de Trivia y Duelos
        self.trivia_activa = False
        self.trivia_respuesta_correcta = ""
        self.duelo_activo = False
        self.votos_duelo = {"opcion1": 0, "opcion2": 0}

        # Salas Míticas
        self.salas_historias = [
            "¿Sabías que la mítica ruta del bakalao en Valencia cambió la historia de la música electrónica en España?",
            "Recordando los cierres épicos en Puzzle, Spook Factory y Central Rock. ¡Menudos templos del sonido!",
            "El sonido Makina y el Hard Dance de los 90 y 2000 marcaron a toda una generación en las pistas de baile.",
            "¿Quién vivió las sesiones legendarias de Chasis o Pont Aeri? ¡Que levante el dedo el chat!"
        ]

        self.preguntas_trivia = [
            {"pregunta": "¿En qué año se lanzó el icónico anthem 'Fly on the Wings of Love' de XTM & DJ Chus?", "respuesta": "2003"},
            {"pregunta": "¿De qué estilo principal hablamos si mencionamos bombos pesados a 150 BPM típicos de la zona norte y levante?", "respuesta": "makina"},
            {"pregunta": "¿Qué famoso grupo firmó el temazo trance 'Silence' con Sarah McLachlan?", "respuesta": "tiesto"}
        ]

        self.actualizar_txt_obs("🏆 Liga de Fieles Activa - ¡Participa y gana una sesión!")

    def actualizar_txt_obs(self, texto):
        try:
            with open("estado_juego.txt", "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            print(f"Error al escribir estado_juego.txt: {e}")

    def guardar_peticion_obs(self, usuario, cancion):
        try:
            with open("peticiones.txt", "a", encoding="utf-8") as f:
                f.write(f"@{usuario} pidió: {cancion}\n")
        except Exception as e:
            print(f"Error al guardar peticiones.txt: {e}")

    def cargar_json(self, archivo, valor_por_defecto):
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar {archivo}: {e}")
        return valor_por_defecto

    def guardar_json(self, archivo, datos):
        try:
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar {archivo}: {e}")

    async def event_ready(self):
        print(f'=== ¡BOT PRO CON LIGA DE FIELES CONECTADO: {CANAL} ===')
        asyncio.create_task(self.bucle_autonomo_chat())
        asyncio.create_task(self.bucle_repartir_puntos())

    async def event_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return  
        print(f"[ERROR COMANDO] {error}")

    async def event_message(self, message):
        if message.echo:
            return

        self.ultimo_mensaje = time.time()
        autor = message.author.name
        autor_lower = autor.lower()

        # Inicializar puntos y sumar por actividad en el chat (cada mensaje suma 2 puntos para la Liga)
        if autor_lower not in self.puntos:
            self.puntos[autor_lower] = 50
        else:
            self.puntos[autor_lower] += 2
        self.guardar_json(self.archivo_puntos, self.puntos)

        # Saludo automático a nuevos espectadores
        if autor_lower not in self.usuarios_saludados and autor_lower != CANAL.lower():
            self.usuarios_saludados.add(autor_lower)
            await message.channel.send(f"¡Bienvenido al chat, @{autor}! Estás participando en la Liga de Fieles mensual. ¡Comenta y gana una sesión exclusiva! 🎧🔥")

        self.ultimos_mensajes_chat.append(f"{autor}: {message.content}")
        if len(self.ultimos_mensajes_chat) > 15:
            self.ultimos_mensajes_chat.pop(0)

        content = message.content.strip()

        # Comprobar respuestas de Trivia
        if self.trivia_activa:
            if content.lower() == self.trivia_respuesta_correcta.lower():
                self.trivia_activa = False
                self.puntos[autor_lower] += 50 # Bonus extra para la liga
                self.guardar_json(self.archivo_puntos, self.puntos)
                await message.channel.send(f"🏆 ¡Correcto, @{autor}! Acertaste la trivia y sumas +50 puntos extra para la Liga de Fieles. 🎉")

        # Comprobar votos de Duelo
        if self.duelo_activo:
            if content == "1":
                self.votos_duelo["opcion1"] += 1
            elif content == "2":
                self.votos_duelo["opcion2"] += 1

        # Mención a la IA (@sesionesoldschool)
        mencion_canal = f"@{BOT_NICK}".lower()
        if mencion_canal in content.lower():
            if ai_client:
                try:
                    prompt_usuario = content.lower().replace(mencion_canal, "").strip()
                    if not prompt_usuario:
                        prompt_usuario = "¡Hola máquina!"
                        
                    contexto_actual = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt_final = f"Historial del chat: [{contexto_actual}]\n\n{autor} te menciona: '{prompt_usuario}'. Resóndele como colega del canal."
                    
                    chat_session = ai_client.chats.create(
                        model='gemini-3.6-flash',
                        config={
                            'system_instruction': (
                                f"Eres un colega y viewer habitual en el canal de Twitch de {CANAL} centrado en música Remember y Hard Dance. "
                                "Hablas con jerga coloquial española, natural, cercano. Breve (máx 250 caracteres)."
                            ),
                        }
                    )
                    response = chat_session.send_message(prompt_final)
                    texto_respuesta = response.text if response and response.text else "¡Totalmente de acuerdo tío! 🔥"
                    await message.channel.send(f"@{autor} {texto_respuesta.strip()[:350]}")
                except Exception as e:
                    print(f"[ERROR GEMINI]: {e}")
                    await message.channel.send(f"@{autor} ¡Menudo temarral tenemos en cabina! 🎧")

        # Comandos Custom
        if content.startswith('!'):
            partes = content[1:].split(' ', 1)
            nombre_cmd = partes[0].lower()
            if nombre_cmd in self.comandos_custom:
                await message.channel.send(self.comandos_custom[nombre_cmd])
                return

        await self.handle_commands(message)

    async def bucle_repartir_puntos(self):
        while True:
            await asyncio.sleep(300) # Cada 5 minutos de visualización suma puntos pasivos
            if self.puntos:
                for usr in self.puntos:
                    self.puntos[usr] += 10
                self.guardar_json(self.archivo_puntos, self.puntos)

    async def bucle_autonomo_chat(self):
        await asyncio.sleep(25)
        while True:
            try:
                await asyncio.sleep(150)
                if time.time() - self.ultimo_mensaje > 200:
                    canal_obj = self.get_channel(CANAL)
                    if canal_obj:
                        if ai_client:
                            chat_session = ai_client.chats.create(
                                model='gemini-3.6-flash',
                                config={
                                    'system_instruction': "Eres un colega más en el chat de Twitch de música remember. Escribe corto, natural, comentando la sesión y recordando la liga de fieles.",
                                }
                            )
                            response = chat_session.send_message("Suelta un comentario recordando al chat que participen en la liga de fieles para ganar la sesión de regalo.")
                            msg = (response.text if response and response.text else "¡Recordad que el que más participe se lleva la sesión de regalo a fin de mes!").replace('\n', ' ')
                        else:
                            msg = f"¡Recordad usar !liga para ver cómo va vuestra posición en la Liga de Fieles! {random.choice(self.emotes_twitch)}"
                        await canal_obj.send(f"{msg} {random.choice(self.emotes_twitch)}")
                        self.ultimo_mensaje = time.time()
            except Exception as e:
                print(f"Error bucle autónomo: {e}")

    # ==================== COMANDOS DE LIGA Y GAMIFICATION ====================

    @commands.command(name='puntos', aliases=['vatios', 'fiesta'])
    async def cmd_puntos(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        cant = self.puntos.get(usr, 50)
        await ctx.send(f"⚡ @{ctx.author.name}, tienes **{cant} puntos** acumulados para la Liga de Fieles de este mes.")

    @commands.command(name='liga', aliases=['top', 'ranking'])
    async def cmd_liga(self, ctx: commands.Context):
        if not self.puntos:
            return await ctx.send("🏆 La Liga de Fieles acaba de empezar. ¡Sé el primero en escribir en el chat!")
        
        # Ordenar usuarios por puntos de mayor a menor
        ranking_ordenado = sorted(self.puntos.items(), key=lambda x: x[1], reverse=True)[:3]
        
        texto_ranking = "🏆 **TOP 3 LIGA DE FIELES (¡Premio: Sesión exclusiva a fin de mes!):** "
        for i, (usr, pts) in enumerate(ranking_ordenado, 1):
            medalla = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
            texto_ranking += f"{medalla} @{usr} ({pts} pts)  "
            
        await ctx.send(texto_ranking)

    @commands.command(name='resetliga')
    async def cmd_resetliga(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} Este comando es exclusivo para moderadores.")
        
        self.puntos = {}
        self.guardar_json(self.archivo_puntos, self.puntos)
        await ctx.send("🔄 ¡Se ha reseteado la Liga de Fieles! Comienza un nuevo mes de acumulación de puntos. ¡A por la sesión de regalo! 🎁🔥")

    @commands.command(name='pedir')
    async def cmd_pedir(self, ctx: commands.Context):
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send(f"@{ctx.author.name} Indica el tema. Uso: `!pedir [Artista - Canción]`")
        peticion = msg[1]
        self.guardar_peticion_obs(ctx.author.name, peticion)
        await ctx.send(f"🎵 ¡Apuntada tu petición, @{ctx.author.name}! '{peticion}' guardada para la sesión. 🔥")

    @commands.command(name='ultimostemas', aliases=['historial'])
    async def cmd_ultimostemas(self, ctx: commands.Context):
        if not self.ultimos_temas:
            await ctx.send("🎧 Todavía no hay historial de temas. ¡Usa `!añadirtema` si eres mod!")
        else:
            lista = " | ".join(self.ultimos_temas[-3:])
            await ctx.send(f"🎶 Últimos temazos sonando: {lista}")

    @commands.command(name='añadirtema')
    async def cmd_añadirtema(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} Comando exclusivo para moderadores.")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send("Uso: `!añadirtema [Artista - Título]`")
        tema = msg[1]
        self.ultimos_temas.append(tema)
        if len(self.ultimos_temas) > 10:
            self.ultimos_temas.pop(0)
        await ctx.send(f"✅ Tema añadido al historial: **{tema}** 🎛️")

    @commands.command(name='trivia', aliases=['adivina'])
    async def cmd_trivia(self, ctx: commands.Context):
        if self.trivia_activa:
            return await ctx.send("⚠️ ¡Ya hay una trivia activa!")
        pregunta_obj = random.choice(self.preguntas_trivia)
        self.trivia_activa = True
        self.trivia_respuesta_correcta = pregunta_obj["respuesta"]
        await ctx.send(f"🧠 **TRIVIA REMEMBER:** {pregunta_obj['pregunta']} (¡Responde en el chat y gana puntos para la liga!)")

    @commands.command(name='duelo')
    async def cmd_duelo(self, ctx: commands.Context):
        if self.duelo_activo:
            return await ctx.send("⚠️ ¡Ya hay un duelo activo!")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2 or "|" not in msg[1]:
            return await ctx.send("Uso: `!duelo [Estilo 1] | [Estilo 2]`")
        partes = msg[1].split("|")
        opt1, opt2 = partes[0].strip(), partes[1].strip()
        self.votos_duelo = {"opcion1": 0, "opcion2": 0}
        self.duelo_activo = True
        await ctx.send(f"⚔️ **DUELO DE ESTILOS:** Escribe **1** para [{opt1}] o **2** para [{opt2}]. ¡30 segundos!")
        await asyncio.sleep(30)
        self.duelo_activo = False
        v1, v2 = self.votos_duelo["opcion1"], self.votos_duelo["opcion2"]
        ganador = opt1 if v1 > v2 else (opt2 if v2 > v1 else "¡Empate!")
        await ctx.send(f"🏁 **RESULTADO:** [{opt1}: {v1}] vs [{opt2}: {v2}] ➔ Gana: **{ganador}**! 🔥")

    @commands.command(name='sala', aliases=['nostalgia', 'ruta'])
    async def cmd_sala(self, ctx: commands.Context):
        await ctx.send(f"🏛️ **MEMORIA CLUBBER:** {random.choice(self.salas_historias)}")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(f"🤖 IA: @{BOT_NICK} | 🏆 Liga: !liga, !puntos | 🎵 Música: !pedir | 🕹️ Juegos: !trivia, !duelo, !sala")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene un {random.randint(0,100)}% de energía festera hoy. 🔥")

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
