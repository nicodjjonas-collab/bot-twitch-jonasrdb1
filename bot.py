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

# Canales simultáneos donde entrará el bot
CANALES = ['jonasrdb', 'koko_deejay']

GEMINI_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

print(f"[INIT] Arrancando bot ULTRATOP DEFINITIVO para canales: {CANALES}")

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
            initial_channels=CANALES
        )
        self.ultimo_mensaje = time.time()
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm"]
        self.ultimos_mensajes_chat = {} 
        self.usuarios_saludados = {}    
        
        # Historial de música global
        self.ultimos_temas = []

        # Estado de juegos y variables por canal
        self.juegos_estado = {}
        for chan in CANALES:
            self.juegos_estado[chan] = {
                "trivia_activa": False,
                "trivia_respuesta_correcta": "",
                "duelo_activo": False,
                "votos_duelo": {"opcion1": 0, "opcion2": 0},
                "ahorcado_activo": False,
                "palabra_secreta": "",
                "letras_adivinadas": set(),
                "intentos_ahorcado": 6
            }
            self.ultimos_mensajes_chat[chan] = []
            self.usuarios_saludados[chan] = set()

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

    def obtener_archivo_puntos(self, canal):
        return f"puntos_{canal.lower()}.json"

    def cargar_puntos_canal(self, canal):
        archivo = self.obtener_archivo_puntos(canal)
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar {archivo}: {e}")
        return {}

    def guardar_puntos_canal(self, canal, datos):
        archivo = self.obtener_archivo_puntos(canal)
        try:
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar {archivo}: {e}")

    def guardar_peticion_obs(self, canal, usuario, cancion):
        try:
            with open(f"peticiones_{canal}.txt", "a", encoding="utf-8") as f:
                f.write(f"@{usuario} pidió: {cancion}\n")
        except Exception as e:
            print(f"Error al guardar peticiones_{canal}.txt: {e}")

    async def event_ready(self):
        print(f'=== ¡BOT MÁXIMO PODER MULTICANAL CONECTADO EN: {CANALES} ===')
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
        canal_nombre = message.channel.name.lower()

        if canal_nombre not in self.juegos_estado:
            self.juegos_estado[canal_nombre] = {
                "trivia_activa": False, "trivia_respuesta_correcta": "",
                "duelo_activo": False, "votos_duelo": {"opcion1": 0, "opcion2": 0},
                "ahorcado_activo": False, "palabra_secreta": "", "letras_adivinadas": set(), "intentos_ahorcado": 6
            }
        if canal_nombre not in self.ultimos_mensajes_chat:
            self.ultimos_mensajes_chat[canal_nombre] = []
        if canal_nombre not in self.usuarios_saludados:
            self.usuarios_saludados[canal_nombre] = set()

        # Sumar puntos independientes de la Liga de Fieles
        puntos_canal = self.cargar_puntos_canal(canal_nombre)
        if autor_lower not in puntos_canal:
            puntos_canal[autor_lower] = 50
        else:
            puntos_canal[autor_lower] += 2
        self.guardar_puntos_canal(canal_nombre, puntos_canal)

        # Saludo automático a nuevos espectadores en este canal
        if autor_lower not in self.usuarios_saludados[canal_nombre] and autor_lower != canal_nombre:
            self.usuarios_saludados[canal_nombre].add(autor_lower)
            await message.channel.send(f"¡Qué pasa @{autor}! Pilla sitio, disfruta del buen Remember (Makina, Trance, Eurodance...) y prueba comandos como `!ruleta`, `!ahorcado` o `!liga`. 🎧🔥")

        self.ultimos_mensajes_chat[canal_nombre].append(f"{autor}: {message.content}")
        if len(self.ultimos_mensajes_chat[canal_nombre]) > 15:
            self.ultimos_mensajes_chat[canal_nombre].pop(0)

        content = message.content.strip()
        estado = self.juegos_estado[canal_nombre]

        # Comprobar respuestas de Trivia
        if estado["trivia_activa"]:
            if content.lower() == estado["trivia_respuesta_correcta"].lower():
                estado["trivia_activa"] = False
                puntos_canal[autor_lower] += 50 
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"¡Buena, @{autor}! Has clavado la trivia y te llevas 50 puntos extra para la liga. 🎯")

        # Comprobar votos de Duelo
        if estado["duelo_activo"]:
            if content == "1":
                estado["votos_duelo"]["opcion1"] += 1
            elif content == "2":
                estado["votos_duelo"]["opcion2"] += 1

        # Comprobar juego del Ahorcado
        if estado["ahorcado_activo"]:
            c_low = content.lower()
            if len(c_low) == 1 and c_low.isalpha():
                if c_low in estado["palabra_secreta"]:
                    estado["letras_adivinadas"].add(c_low)
                    if all(l in estado["letras_adivinadas"] for l in estado["palabra_secreta"]):
                        estado["ahorcado_activo"] = False
                        puntos_canal[autor_lower] += 40
                        self.guardar_puntos_canal(canal_nombre, puntos_canal)
                        await message.channel.send(f"¡Impresionante @{autor}! Has completado la palabra **{estado['palabra_secreta'].upper()}** y te llevas 40 puntos. 🎉")
                    else:
                        progreso = "".join([l if l in estado["letras_adivinadas"] else "_" for l in estado["palabra_secreta"]])
                        await message.channel.send(f"¡Bien @{autor}! Letra acertada: `{progreso}`")
                else:
                    estado["intentos_ahorcado"] -= 1
                    if estado["intentos_ahorcado"] <= 0:
                        estado["ahorcado_activo"] = False
                        await message.channel.send(f"💀 ¡Se acabaron los intentos! El ahorcado se quedó sin vida. La palabra era: **{estado['palabra_secreta'].upper()}**")
                    else:
                        await message.channel.send(f"❌ Fallaste @{autor}. Quedan {estado['intentos_ahorcado']} intentos.")
            elif c_low == estado["palabra_secreta"]:
                estado["ahorcado_activo"] = False
                puntos_canal[autor_lower] += 50
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"🏆 ¡BOOM! @{autor} adivinó la palabra secreta de golpe: **{estado['palabra_secreta'].upper()}** (+50 pts).")

        # Mención a la IA (@sesionesoldschool) 100% blindada y humana
        content_lower = content.lower()
        if BOT_NICK in content_lower or "sesiones" in content_lower:
            if ai_client:
                try:
                    prompt_usuario = content_lower.replace(f"@{BOT_NICK}", "").replace(BOT_NICK, "").strip()
                    if not prompt_usuario:
                        prompt_usuario = "¡Hola máquina!"
                        
                    contexto_actual = " | ".join(self.ultimos_mensajes_chat[canal_nombre][-8:])
                    prompt_final = f"Historial reciente del chat en {canal_nombre}: [{contexto_actual}]\n\n{autor} te dice: '{prompt_usuario}'. Respóndele como un colega más que está viendo el directo de música remember."
                    
                    chat_session = ai_client.chats.create(
                        model='gemini-3.6-flash',
                        config={
                            'system_instruction': (
                                f"Eres un colega más que está viendo el directo de música remember en el canal de Twitch de {canal_nombre}. "
                                "Hablas exclusivamente en español, de forma muy natural, coloquial y callejera (como un amigo en el chat o en un bar). "
                                "REGLAS DE ORO: "
                                "1. Jamás digas que eres una inteligencia artificial, un bot, un modelo o un asistente. "
                                "2. No uses fórmulas de atención al cliente ni discursos formales. "
                                "3. Sé directo, breve y ve al grano (máximo 120 caracteres, como un mensaje rápido de Twitch). "
                                "4. Opina sobre la música, el ambiente, el chat o vacila con buen rollo si te preguntan."
                            ),
                        }
                    )
                    response = chat_session.send_message(prompt_final)
                    texto_respuesta = response.text if response and response.text else "¡Totalmente de acuerdo tío! Menudo temarral."
                    await message.channel.send(f"@{autor} {texto_respuesta.strip()[:150]}".replace('@@', '@'))
                    return
                except Exception as e:
                    print(f"[ERROR GEMINI]: {e}")
                    await message.channel.send(f"@{autor} ¡Totalmente, vaya temazo llevamos en cabina! 🔥")
                    return

        await self.handle_commands(message)

    async def bucle_repartir_puntos(self):
        while True:
            await asyncio.sleep(300) 
            for canal in CANALES:
                puntos_canal = self.cargar_puntos_canal(canal)
                if puntos_canal:
                    for usr in puntos_canal:
                        puntos_canal[usr] += 10
                    self.guardar_puntos_canal(canal, puntos_canal)

    async def bucle_autonomo_chat(self):
        await asyncio.sleep(30)
        while True:
            try:
                await asyncio.sleep(180) 
                if time.time() - self.ultimo_mensaje > 200:
                    for canal_nombre in CANALES:
                        canal_obj = self.get_channel(canal_nombre)
                        if canal_obj:
                            if ai_client:
                                chat_session = ai_client.chats.create(
                                    model='gemini-3.6-flash',
                                    config={
                                        'system_instruction': (
                                            f"Eres un colega más viendo el directo de música remember en el canal {canal_nombre} de Twitch. "
                                            "El chat lleva un rato callado. Suelta un comentario corto, súper natural y callejero sobre la sesión, "
                                            "el buen rollo o animando a usar !ruleta o !ahorcado. "
                                            "Cero formalidades, máximo 100 caracteres."
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

    # ==================== COMANDOS COMPLETOS AL MÁXIMO ====================

    @commands.command(name='puntos', aliases=['vatios', 'fiesta'])
    async def cmd_puntos(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        cant = puntos_canal.get(usr, 50)
        await ctx.send(f"@{ctx.author.name}, vas con **{cant} puntos** acumulados en la liga de este mes. ¡A tope! ⚡")

    @commands.command(name='liga', aliases=['top', 'ranking'])
    async def cmd_liga(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        if not puntos_canal:
            return await ctx.send("La liga acaba de empezar. ¡Escribe en el chat para pillar plaza!")
        ranking_ordenado = sorted(puntos_canal.items(), key=lambda x: x[1], reverse=True)[:3]
        texto_ranking = "🏆 Top 3 de la liga (¡el primero se lleva la sesión exclusiva a fin de mes!): "
        for i, (usr, pts) in enumerate(ranking_ordenado, 1):
            medalla = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
            texto_ranking += f"{medalla} @{usr} ({pts} pts)  "
        await ctx.send(texto_ranking)

    @commands.command(name='resetliga')
    async def cmd_resetliga(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        if not ctx.author.is_mod and ctx.author.name.lower() != canal:
            return await ctx.send(f"@{ctx.author.name} Comando exclusivo para moderadores.")
        self.guardar_puntos_canal(canal, {})
        await ctx.send("¡Liga reseteada! Arranca el contador del nuevo mes para llevarse la sesión de regalo. 🎁🔥")

    @commands.command(name='ruleta', aliases=['suerte', 'apostar'])
    async def cmd_ruleta(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        if usr not in puntos_canal:
            puntos_canal[usr] = 50
        
        resultado = random.choice([-30, -15, 10, 25, 50, 100, 200])
        puntos_canal[usr] += resultado
        if puntos_canal[usr] < 0:
            puntos_canal[usr] = 0
        self.guardar_puntos_canal(canal, puntos_canal)

        if resultado > 0:
            await ctx.send(f"🎡 ¡La ruleta gira para @{ctx.author.name} y gana **+{resultado} puntos**! (Total: {puntos_canal[usr]} pts) 🚀")
        else:
            await ctx.send(f"🎡 ¡Ay @{ctx.author.name}, la ruleta pinchó y pierdes **{resultado} puntos**! (Total: {puntos_canal[usr]} pts) 💥")

    @commands.command(name='ahorcado')
    async def cmd_ahorcado(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["ahorcado_activo"]:
            progreso = "".join([l if l in estado["letras_adivinadas"] else "_" for l in estado["palabra_secreta"]])
            return await ctx.send(f"🎮 Ya hay un ahorcado activo: `{progreso}` (Intentos: {estado['intentos_ahorcado']}). Escribe una letra.")
        
        estado["palabra_secreta"] = random.choice(self.palabras_ahorcado)
        estado["letras_adivinadas"] = set()
        estado["intentos_ahorcado"] = 6
        estado["ahorcado_activo"] = True
        
        oculto = "_" * len(estado["palabra_secreta"])
        await ctx.send(f"🕹️ **¡Arranca el Ahorcado Clubber!** Pista: Música remember. `{oculto}` (Escribe letras o arriésgate con la palabra)")

    @commands.command(name='trivia', aliases=['adivina'])
    async def cmd_trivia(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["trivia_activa"]:
            return await ctx.send("⚠️ ¡Ya hay una trivia en marcha!")
        pregunta_obj = random.choice(self.preguntas_trivia)
        estado["trivia_activa"] = True
        estado["trivia_respuesta_correcta"] = pregunta_obj["respuesta"]
        await ctx.send(f"🧠 **TRIVIA REMEMBER:** {pregunta_obj['pregunta']} (¡Responde en el chat y gana puntos!)")

    @commands.command(name='duelo')
    async def cmd_duelo(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["duelo_activo"]:
            return await ctx.send("⚠️ ¡Ya hay un duelo activo!")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2 or "|" not in msg[1]:
            return await ctx.send("Uso correcto: `!duelo [Estilo 1] | [Estilo 2]`")
        partes = msg[1].split("|")
        opt1, opt2 = partes[0].strip(), partes[1].strip()
        estado["votos_duelo"] = {"opcion1": 0, "opcion2": 0}
        estado["duelo_activo"] = True
        await ctx.send(f"⚔️ **DUELO:** Escribe **1** para [{opt1}] o **2** para [{opt2}]. ¡30 segundos!")
        await asyncio.sleep(30)
        estado["duelo_activo"] = False
        v1, v2 = estado["votos_duelo"]["opcion1"], estado["votos_duelo"]["opcion2"]
        ganador = opt1 if v1 > v2 else (opt2 if v2 > v1 else "¡Empate técnico!")
        await ctx.send(f"🏁 **RESULTADO:** [{opt1}: {v1}] vs [{opt2}: {v2}] ➔ Gana: **{ganador}**! 🔥")

    @commands.command(name='sala', aliases=['nostalgia', 'ruta'])
    async def cmd_sala(self, ctx: commands.Context):
        await ctx.send(f"🏛️ **MEMORIA CLUBBER:** {random.choice(self.salas_historias)}")

    @commands.command(name='pedir')
    async def cmd_pedir(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send(f"@{ctx.author.name} Pon el tema así: `!pedir [Artista - Canción]`")
        peticion = msg[1]
        self.guardar_peticion_obs(canal, ctx.author.name, peticion)
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
        canal = ctx.channel.name.lower()
        if not ctx.author.is_mod and ctx.author.name.lower() != canal:
            return await ctx.send(f"@{ctx.author.name} Solo mods.")
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2:
            return await ctx.send("Uso: `!añadirtema [Artista - Título]`")
        tema = msg[1]
        self.ultimos_temas.append(tema)
        if len(self.ultimos_temas) > 10:
            self.ultimos_temas.pop(0)
        await ctx.send(f"✅ Apuntado al historial: **{tema}** 🎛️")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene hoy un {random.randint(0,100)}% de energía festera. ¡A darlo todo! 🔥")

    @commands.command(name='normas', aliases=['reglas'])
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("📜 **Normas del canal:** 1. Respeto ante todo. 2. Cero toxicidad. 3. ¡Disfruta del buen Remember, el Hard Dance y el Trance al máximo! 🎧")

    @commands.command(name='suscribete', aliases=['sub'])
    async def cmd_suscribete(self, ctx: commands.Context):
        await ctx.send("⭐ ¡Apoya el canal suscribiéndote con Prime o de pago! Llévate los emblemas exclusivos y participa en los sorteos VIP de sesiones a fin de mes. 🚀")

    @commands.command(name='redes', aliases=['social'])
    async def cmd_redes(self, ctx: commands.Context):
        await ctx.send("🌐 ¡Sígueme en redes y no te pierdas ningún directo ni sesión exclusiva de Remember!")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(f"🤖 IA: @{BOT_NICK} | 🏆 Liga/Juegos: !liga, !puntos, !ruleta, !ahorcado, !trivia, !duelo | 🎵 Música: !pedir, !ultimostemas, !sala | ⭐ Info: !normas, !suscribete")

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
