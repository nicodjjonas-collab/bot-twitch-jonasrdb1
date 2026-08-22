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

print(f"[INIT] Arrancando bot con TODOS los juegos y modo humano para: {CANAL}")

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

        # Estado del Ahorcado
        self.ahorcado_activo = False
        self.palabra_secreta = ""
        self.letras_adivinadas = set()
        self.intentos_ahorcado = 6

        # Palabras para el Ahorcado (temática remember / clubber)
        self.palabras_ahorcado = ["makina", "hardance", "trance", "eurodance", "valencia", "puzle", "spook", "chasis", "pontateri", "bakalao", "cabina", "vinilo"]

        # Salas Míticas
        self.salas_historias = [
            "¿Sabías que la mítica ruta del bakalao en Valencia cambió la historia de la música electrónica en España?",
            "Recordando los cierres épicos en Puzzle, Spook Factory y Central Rock. ¡Menudos templos del sonido!",
            "El sonido Makina, el Hard Dance a 150 BPM, el Uplifting Trance y el Eurodance marcaron a toda una generación.",
            "¿Quién vivió las sesiones legendarias de Chasis, Pont Aeri, Central o Masía? ¡Que levante el dedo el chat!"
        ]

        self.preguntas_trivia = [
            {"pregunta": "¿En qué año se lanzó el icónico anthem 'Fly on the Wings of Love' de XTM & DJ Chus?", "respuesta": "2003"},
            {"pregunta": "¿De qué estilo principal hablamos si mencionamos bombos pesados a 150 BPM típicos de la zona norte y levante?", "respuesta": "makina"},
            {"pregunta": "¿Qué famoso grupo firmó el temazo trance 'Silence' con Sarah McLachlan?", "respuesta": "tiesto"},
            {"pregunta": "¿Qué estilo melódico y bailable arrasaba en las discotecas a finales de los 90 y principios de los 2000?", "respuesta": "eurodance"}
        ]

        self.actualizar_txt_obs("🏆 Liga de Fieles Activa - ¡Participa en los minijuegos y gana una sesión!")

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
        print(f'=== ¡BOT MÁXIMO PODER CONECTADO EN EL CANAL: {CANAL} ===')
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

        # Puntos de la Liga de Fieles
        if autor_lower not in self.puntos:
            self.puntos[autor_lower] = 50
        else:
            self.puntos[autor_lower] += 2
        self.guardar_json(self.archivo_puntos, self.puntos)

        # Saludo automático a nuevos espectadores
        if autor_lower not in self.usuarios_saludados and autor_lower != CANAL.lower():
            self.usuarios_saludados.add(autor_lower)
            await message.channel.send(f"¡Qué pasa @{autor}! Pilla sitio, disfruta del buen Remember (Makina, Hard Dance, Trance...) y prueba comandos como `!ruleta`, `!ahorcado` o `!liga`. 🎧🔥")

        self.ultimos_mensajes_chat.append(f"{autor}: {message.content}")
        if len(self.ultimos_mensajes_chat) > 15:
            self.ultimos_mensajes_chat.pop(0)

        content = message.content.strip()

        # Comprobar respuestas de Trivia
        if self.trivia_activa:
            if content.lower() == self.trivia_respuesta_correcta.lower():
                self.trivia_activa = False
                self.puntos[autor_lower] += 50 
                self.guardar_json(self.archivo_puntos, self.puntos)
                await message.channel.send(f"¡Buena, @{autor}! Has clavado la trivia y te llevas 50 puntos extra para la liga. 🎯")

        # Comprobar votos de Duelo
        if self.duelo_activo:
            if content == "1":
                self.votos_duelo["opcion1"] += 1
            elif content == "2":
                self.votos_duelo["opcion2"] += 1

        # Comprobar juego del Ahorcado (si escriben una letra o la palabra completa)
        if self.ahorcado_activo:
            c_low = content.lower()
            if len(c_low) == 1 and c_low.isalpha():
                if c_low in self.palabra_secreta:
                    self.letras_adivinadas.add(c_low)
                    # Comprobar si ganó
                    if all(l in self.letras_adivinadas for l in self.palabra_secreta):
                        self.ahorcado_activo = False
                        self.puntos[autor_lower] += 40
                        self.guardar_json(self.archivo_puntos, self.puntos)
                        await message.channel.send(f"¡Impresionante @{autor}! Has completado la palabra **{self.palabra_secreta.upper()}** y te llevas 40 puntos. 🎉")
                    else:
                        progreso = "".join([l if l in self.letras_adivinadas else "_" for l in self.palabra_secreta])
                        await message.channel.send(f"¡Bien @{autor}! Letra acertada: `{progreso}`")
                else:
                    self.intentos_ahorcado -= 1
                    if self.intentos_ahorcado <= 0:
                        self.ahorcado_activo = False
                        await message.channel.send(f"💀 ¡Se acabaron los intentos! El ahorcado se quedó sin vida. La palabra era: **{self.palabra_secreta.upper()}**")
                    else:
                        await message.channel.send(f"❌ Fallaste @{autor}. Quedan {self.intentos_ahorcado} intentos.")
            elif c_low == self.palabra_secreta:
                self.ahorcado_activo = False
                self.puntos[autor_lower] += 50
                self.guardar_json(self.archivo_puntos, self.puntos)
                await message.channel.send(f"🏆 ¡BOOM! @{autor} adivinó la palabra secreta de golpe: **{self.palabra_secreta.upper()}** (+50 pts).")

        # Mención a la IA (@sesionesoldschool) de forma humana y natural
        mencion_canal = f"@{BOT_NICK}".lower()
        if mencion_canal in content.lower():
            if ai_client:
                try:
                    prompt_usuario = content.lower().replace(mencion_canal, "").strip()
                    if not prompt_usuario:
                        prompt_usuario = "¡Hola máquina!"
                        
                    contexto_actual = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt_final = f"Historial reciente del chat: [{contexto_actual}]\n\n{autor} te dice: '{prompt_usuario}'. Respóndele como un colega más que está viendo el directo de música remember."
                    
                    chat_session = ai_client.chats.create(
                        model='gemini-3.6-flash',
                        config={
                            'system_instruction': (
                                f"Eres un colega y espectador más en el canal de Twitch de {CANAL}, especializado en música remember, hard dance, uplifting trance, eurodance y tech house. "
                                "Hablas exclusivamente en español, de forma muy natural, coloquial y cercana (como un colega en un bar o en el chat). "
                                "REGLAS ESTRICTAS: "
                                "1. Nunca digas que eres una inteligencia artificial, un bot o un asistente. "
                                "2. No uses frases formales ni de atención al cliente. "
                                "3. Responde directo, sin rodeos y al grano (máximo 150 caracteres). "
                                "4. Comenta sobre la música, los minijuegos o lo que te estén diciendo de forma fluida."
                            ),
                        }
                    )
                    response = chat_session.send_message(prompt_final)
                    texto_respuesta = response.text if response and response.text else "¡Totalmente de acuerdo tío! Menudo temarral."
                    await message.channel.send(f"@{autor} {texto_respuesta.strip()[:200]}")
                except Exception as e:
                    print(f"[ERROR GEMINI]: {e}")
                    await message.channel.send(f"@{autor} ¡Totalmente, vaya temazo llevamos en cabina! 🔥")

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
            await asyncio.sleep(300) 
            if self.puntos:
                for usr in self.puntos:
                    self.puntos[usr] += 10
                self.guardar_json(self.archivo_puntos, self.puntos)

    async def bucle_autonomo_chat(self):
        await asyncio.sleep(30)
        while True:
            try:
                await asyncio.sleep(180) 
                if time.time() - self.ultimo_mensaje > 200:
                    canal_obj = self.get_channel(CANAL)
                    if canal_obj:
                        if ai_client:
                            chat_session = ai_client.chats.create(
                                model='gemini-3.6-flash',
                                config={
                                    'system_instruction': (
                                        "Eres un colega más viendo el directo de música remember en Twitch. "
                                        "El chat lleva un rato callado. Suelta un comentario corto, súper natural y callejero sobre la sesión, "
                                        "el buen rollo o animando a usar !ruleta o !ahorcado. "
                                        "Cero formalidades, máximo 120 caracteres."
                                    ),
                                }
                            )
                            response = chat_session.send_message("Suelta una frase corta para romper el hielo en el chat.")
                            msg = (response.text if response and response.text else "¡Menuda sesión guapa nos estamos marcando hoy familia!").replace('\n', ' ')
                        else:
                            msg = f"¡Vaya temazos de sesión familia! {random.choice(self.emotes_twitch)}"
                        await canal_obj.send(f"{msg}")
                        self.ultimo_mensaje = time.time()
            except Exception as e:
                print(f"Error bucle autónomo: {e}")

    # ==================== COMANDOS Y JUEGOS AL MÁXIMO ====================

    @commands.command(name='puntos', aliases=['vatios', 'fiesta'])
    async def cmd_puntos(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        cant = self.puntos.get(usr, 50)
        await ctx.send(f"@{ctx.author.name}, vas con **{cant} puntos** acumulados en la liga de este mes. ¡A tope! ⚡")

    @commands.command(name='liga', aliases=['top', 'ranking'])
    async def cmd_liga(self, ctx: commands.Context):
        if not self.puntos:
            return await ctx.send("La liga acaba de empezar. ¡Escribe en el chat para pillar plaza!")
        ranking_ordenado = sorted(self.puntos.items(), key=lambda x: x[1], reverse=True)[:3]
        texto_ranking = "🏆 Top 3 de la liga (¡el primero se lleva la sesión exclusiva a fin de mes!): "
        for i, (usr, pts) in enumerate(ranking_ordenado, 1):
            medalla = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
            texto_ranking += f"{medalla} @{usr} ({pts} pts)  "
        await ctx.send(texto_ranking)

    @commands.command(name='resetliga')
    async def cmd_resetliga(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} Comando exclusivo para moderadores.")
        self.puntos = {}
        self.guardar_json(self.archivo_puntos, self.puntos)
        await ctx.send("¡Liga reseteada! Arranca el contador del nuevo mes para llevarse la sesión de regalo. 🎁🔥")

    @commands.command(name='ruleta', aliases=['suerte', 'apostar'])
    async def cmd_ruleta(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        if usr not in self.puntos:
            self.puntos[usr] = 50
        
        resultado = random.choice([-30, -15, 10, 25, 50, 100, 200])
        self.puntos[usr] += resultado
        if self.puntos[usr] < 0:
            self.puntos[usr] = 0
        self.guardar_json(self.archivo_puntos, self.puntos)

        if resultado > 0:
            await ctx.send(f"🎡 ¡La ruleta gira para @{ctx.author.name} y gana **+{resultado} puntos**! (Total: {self.puntos[usr]} pts) 🚀")
        else:
            await ctx.send(f"🎡 ¡Ay @{ctx.author.name}, la ruleta pinchó y pierdes **{resultado} puntos**! (Total: {self.puntos[usr]} pts) 💥")

    @commands.command(name='ahorcado')
    async def cmd_ahorcado(self, ctx: commands.Context):
        if self.ahorcado_activo:
            progreso = "".join([l if l in self.letras_adivinadas else "_" for l in self.palabra_secreta])
            return await ctx.send(f"🎮 Ya hay un ahorcado activo: `{progreso}` (Intentos: {self.intentos_ahorcado}). Escribe una letra.")
        
        self.palabra_secreta = random.choice(self.palabras_ahorcado)
        self.letras_adivinadas = set()
        self.intentos_ahorcado = 6
        self.ahorcado_activo = True
        
        oculto = "_" * len(self.palabra_secreta)
        await ctx.send(f"🕹️ **¡Arranca el Ahorcado Clubber!** Pista: Palabra de música remember. `{oculto}` (Escribe letras en el chat o arriésgate con la palabra)")

    @commands.command(name='pedir')
    async def cmd_pedir(self, ctx: commands.Context):
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send(f"@{ctx.author.name} Pon el tema así: `!pedir [Artista - Canción]`")
        peticion = msg[1]
        self.guardar_peticion_obs(ctx.author.name, peticion)
        await ctx.send(f"¡Apuntado '{peticion}', @{ctx.author.name}! Guardado para la sesión. 🎵")

    @commands.command(name='ultimostemas', aliases=['historial'])
    async def cmd_ultimostemas(self, ctx: commands.Context):
        if not self.ultimos_temas:
            await ctx.send("Aún no hay temas registrados en el historial.")
        else:
            lista = " | ".join(self.ultimos_temas[-3:])
            await ctx.send(f"🎶 Últimos temazos sonando: {lista}")

    @commands.command(name='añadirtema')
    async def cmd_añadirtema(self, ctx: commands.Context):
        if not ctx.author.is_mod and ctx.author.name.lower() != CANAL.lower():
            return await ctx.send(f"@{ctx.author.name} Solo mods.")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send("Uso: `!añadirtema [Artista - Título]`")
        tema = msg[1]
        self.ultimos_temas.append(tema)
        if len(self.ultimos_temas) > 10:
            self.ultimos_temas.pop(0)
        await ctx.send(f"✅ Apuntado al historial: **{tema}** 🎛️")

    @commands.command(name='trivia', aliases=['adivina'])
    async def cmd_trivia(self, ctx: commands.Context):
        if self.trivia_activa:
            return await ctx.send("⚠️ ¡Ya hay una trivia en marcha!")
        pregunta_obj = random.choice(self.preguntas_trivia)
        self.trivia_activa = True
        self.trivia_respuesta_correcta = pregunta_obj["respuesta"]
        await ctx.send(f"🧠 **TRIVIA REMEMBER:** {pregunta_obj['pregunta']} (¡Responde en el chat y gana puntos!)")

    @commands.command(name='duelo')
    async def cmd_duelo(self, ctx: commands.Context):
        if self.duelo_activo:
            return await ctx.send("⚠️ ¡Ya hay un duelo activo!")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2 or "|" not in msg[1]:
            return await ctx.send("Uso correcto: `!duelo [Estilo 1] | [Estilo 2]`")
        partes = msg[1].split("|")
        opt1, opt2 = partes[0].strip(), partes[1].strip()
        self.votos_duelo = {"opcion1": 0, "opcion2": 0}
        self.duelo_activo = True
        await ctx.send(f"⚔️ **DUELO:** Escribe **1** para [{opt1}] o **2** para [{opt2}]. ¡30 segundos!")
        await asyncio.sleep(30)
        self.duelo_activo = False
        v1, v2 = self.vnos_duelo["opcion1"] if hasattr(self, 'vnos_duelo') else self.votos_duelo["opcion1"], self.votos_duelo["opcion2"]
        ganador = opt1 if v1 > v2 else (opt2 if v2 > v1 else "¡Empate técnico!")
        await ctx.send(f"🏁 **RESULTADO:** [{opt1}: {v1}] vs [{opt2}: {v2}] ➔ Gana: **{ganador}**! 🔥")

    @commands.command(name='sala', aliases=['nostalgia', 'ruta'])
    async def cmd_sala(self, ctx: commands.Context):
        await ctx.send(f"🏛️ **MEMORIA CLUBBER:** {random.choice(self.salas_historias)}")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(f"🤖 IA: @{BOT_NICK} | 🏆 Liga: !liga, !puntos, !ruleta | 🕹️ Juegos: !ahorcado, !trivia, !duelo | 🎵 Música: !pedir, !ultimostemas, !sala")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene hoy un {random.randint(0,100)}% de energía festera. ¡A darlo todo! 🔥")

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
