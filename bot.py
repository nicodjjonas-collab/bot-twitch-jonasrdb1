import os
import random
import time
import json
import asyncio
import traceback
import twitchio
from twitchio.ext import commands
from openai import OpenAI

TOKEN = os.environ.get('TWITCH_TOKEN', '').strip()
BOT_NICK = os.environ.get('TWITCH_BOT', 'sesionesoldschool').lower() 

canal_env = os.environ.get('TWITCH_CANAL', 'jonasrdb').strip().lower()
CANALES = [canal_env, 'koko_deejay'] if canal_env != 'koko_deejay' else [canal_env]

# Configuración de DeepSeek API
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat') # O deepseek-reasoner si prefieres

print(f"[INIT] Arrancando bot con DeepSeek para los canales: {CANALES} (Bot nick: {BOT_NICK})")

deepseek_client = None
if DEEPSEEK_KEY:
    try:
        deepseek_client = OpenAI(
            api_key=DEEPSEEK_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        print("[INIT] ¡Cliente de DeepSeek conectado correctamente!")
    except Exception as e:
        print(f"[INIT] Error al iniciar cliente DeepSeek: {e}")
else:
    print("[INIT] AVISO: No se encontró DEEPSEEK_API_KEY en las variables de entorno.")

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=CANALES
        )
        self.ultimos_mensajes_canal = {} 
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm"]
        self.ultimos_mensajes_chat = {} 
        self.usuarios_saludados = {}    
        self.ultimos_temas = []

        self.juegos_estado = {}
        for chan in CANALES:
            self.juegos_estado[chan] = {
                "trivia_activa": False, "trivia_respuesta_correcta": "",
                "duelo_activo": False, "votos_duelo": {"opcion1": 0, "opcion2": 0},
                "ahorcado_activo": False, "palabra_secreta": "", "letras_adivinadas": set(), "intentos_ahorcado": 6,
                "vf_activo": False, "vf_respuesta_correcta": ""
            }
            self.ultimos_mensajes_chat[chan] = []
            self.usuarios_saludados[chan] = set()
            self.ultimos_mensajes_canal[chan] = time.time()

        self.palabras_ahorcado = ["makina", "hardance", "trance", "eurodance", "valencia", "puzle", "spook", "chasis", "pontateri", "bakalao", "cabina", "vinilo"]
        
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

        self.preguntas_vf = [
            {"pregunta": "La Ruta del Bakalao se desarrolló principalmente en la comunidad Valenciana.", "respuesta": "verdadero"},
            {"pregunta": "El estilo Makina suele rondar habitualmente entre los 90 y 100 BPM.", "respuesta": "falso"},
            {"pregunta": "Discotecas como Puzzle y Spook Factory fueron auténticos templos de la música electrónica en los 90.", "respuesta": "verdadero"},
            {"pregunta": "El Trance es un género musical que se originó en los años 50.", "respuesta": "falso"},
            {"pregunta": "El vinilo sigue siendo un formato legendario muy valorado en las sesiones de música remember.", "respuesta": "verdadero"}
        ]

    def obtener_archivo_puntos(self, canal):
        return f"puntos_liga_{canal.lower()}.json"

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
        print(f'=== ¡BOT CONECTADO EN: {CANALES} ===')
        asyncio.create_task(self.bucle_autonomo_chat())
        asyncio.create_task(self.bucle_repartir_puntos_actividad())

    async def event_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return  
        print(f"[ERROR COMANDO] {error}")

    async def event_message(self, message):
        if message.echo:
            return

        autor = message.author.name
        autor_lower = autor.lower()
        canal_nombre = message.channel.name.lower()

        self.ultimos_mensajes_canal[canal_nombre] = time.time()

        if canal_nombre not in self.juegos_estado:
            self.juegos_estado[canal_nombre] = {
                "trivia_activa": False, "trivia_respuesta_correcta": "",
                "duelo_activo": False, "votos_duelo": {"opcion1": 0, "opcion2": 0},
                "ahorcado_activo": False, "palabra_secreta": "", "letras_adivinadas": set(), "intentos_ahorcado": 6,
                "vf_activo": False, "vf_respuesta_correcta": ""
            }
        if canal_nombre not in self.ultimos_mensajes_chat:
            self.ultimos_mensajes_chat[canal_nombre] = []
        if canal_nombre not in self.usuarios_saludados:
            self.usuarios_saludados[canal_nombre] = set()

        # Puntos por chatear
        puntos_canal = self.cargar_puntos_canal(canal_nombre)
        if autor_lower not in puntos_canal:
            puntos_canal[autor_lower] = 10
        else:
            puntos_canal[autor_lower] += 3
        self.guardar_puntos_canal(canal_nombre, puntos_canal)

        if autor_lower not in self.usuarios_saludados[canal_nombre] and autor_lower != canal_nombre:
            self.usuarios_saludados[canal_nombre].add(autor_lower)
            await message.channel.send(f"¡Qué pasa @{autor}! Pilla sitio. Cuanto más chatees y participes, más subes en la Liga Mensual para ganar **una sesión exclusiva**. 🎧🔥")

        self.ultimos_mensajes_chat[canal_nombre].append(f"{autor}: {message.content}")
        if len(self.ultimos_mensajes_chat[canal_nombre]) > 15:
            self.ultimos_mensajes_chat[canal_nombre].pop(0)

        content = message.content.strip()
        content_lower = content.lower()
        estado = self.juegos_estado[canal_nombre]

        # Comprobar Juegos
        if estado["trivia_activa"] and content_lower == estado["trivia_respuesta_correcta"].lower():
            estado["trivia_activa"] = False
            puntos_canal[autor_lower] += 50 
            self.guardar_puntos_canal(canal_nombre, puntos_canal)
            await message.channel.send(f"¡Buena, @{autor}! Has clavado la trivia y sumas 50 puntos para la liga mensual. 🎯")

        if estado["vf_activo"] and content_lower in ["verdadero", "v", "falso", "f"]:
            val_usuario = "verdadero" if content_lower in ["verdadero", "v"] else "falso"
            if val_usuario == estado["vf_respuesta_correcta"]:
                estado["vf_activo"] = False
                puntos_canal[autor_lower] += 30
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"✅ ¡Correcto @{autor}! Era **{estado['vf_respuesta_correcta'].upper()}** (+30 pts). 🎉")

        if estado["ahorcado_activo"]:
            if len(content_lower) == 1 and content_lower.isalpha():
                if content_lower in estado["palabra_secreta"]:
                    estado["letras_adivinadas"].add(content_lower)
                    if all(l in estado["letras_adivinadas"] for l in estado["palabra_secreta"]):
                        estado["ahorcado_activo"] = False
                        puntos_canal[autor_lower] += 40
                        self.guardar_puntos_canal(canal_nombre, puntos_canal)
                        await message.channel.send(f"¡Impresionante @{autor}! Has completado la palabra **{estado['palabra_secreta'].upper()}** (+40 pts). 🎉")
                    else:
                        progreso = "".join([l if l in estado["letras_adivinadas"] else "_" for l in estado["palabra_secreta"]])
                        await message.channel.send(f"Letra acertada: `{progreso}`")
                else:
                    estado["intentos_ahorcado"] -= 1
                    if estado["intentos_ahorcado"] <= 0:
                        estado["ahorcado_activo"] = False
                        await message.channel.send(f"💀 ¡Se acabaron los intentos! La palabra era: **{estado['palabra_secreta'].upper()}**")
            elif content_lower == estado["palabra_secreta"]:
                estado["ahorcado_activo"] = False
                puntos_canal[autor_lower] += 50
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"🏆 ¡BOOM! @{autor} adivinó la palabra secreta: **{estado['palabra_secreta'].upper()}** (+50 pts).")

        # ==========================================
        # INTELIGENCIA ARTIFICIAL (DEEPSEEK)
        # ==========================================
        es_mencion_bot = BOT_NICK in content_lower or f"@{BOT_NICK}" in content_lower or "hola" in content_lower
        
        if deepseek_client and es_mencion_bot and not content.startswith('!'):
            print(f"🔥 [EVENTO DEEPSEEK] Mensaje detectado de {autor}: '{content}'")
            try:
                prompt_usuario = content_lower.replace(f"@{BOT_NICK}", "").replace(BOT_NICK, "").strip()
                if not prompt_usuario:
                    prompt_usuario = "¡Hola máquina!"
                
                response = deepseek_client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": "Eres un colega más viendo el directo de música remember en Twitch. Habla en español, de forma cercana, natural y callejera. Máximo 140 caracteres."},
                        {"role": "user", "content": f"El usuario {autor} dice: '{prompt_usuario}'"}
                    ],
                    temperature=0.9,
                    max_tokens=80
                )
                
                if response and response.choices:
                    texto_respuesta = response.choices[0].message.content.strip().replace('\n', ' ')
                    print(f"✅ [ÉXITO DEEPSEEK] Respuesta: {texto_respuesta}")
                    await message.channel.send(f"@{autor} {texto_respuesta}")
                    return
            except Exception as e:
                print(f"❌ [ERROR CRÍTICO DEEPSEEK]: {type(e).__name__} - {e}")

        await self.handle_commands(message)

    async def bucle_repartir_puntos_actividad(self):
        while True:
            await asyncio.sleep(300) 
            for canal in CANALES:
                puntos_canal = self.cargar_puntos_canal(canal)
                if puntos_canal:
                    for usr in puntos_canal:
                        puntos_canal[usr] += 15
                    self.guardar_puntos_canal(canal, puntos_canal)

    async def bucle_autonomo_chat(self):
        await asyncio.sleep(30)
        while True:
            try:
                await asyncio.sleep(180) 
                for canal_nombre in CANALES:
                    canal_obj = self.get_channel(canal_nombre)
                    if canal_obj:
                        if deepseek_client:
                            try:
                                response = deepseek_client.chat.completions.create(
                                    model=DEEPSEEK_MODEL,
                                    messages=[
                                        {"role": "system", "content": "Eres un espectador en un directo de música remember. Suelta una frase corta de colega animando el chat y haz una pregunta rápida. Máximo 100 caracteres."}
                                    ],
                                    temperature=0.9,
                                    max_tokens=80
                                )
                                msg = (response.choices[0].message.content if response and response.choices else "¿Qué pasa chat? ¿Estáis dormidos o qué track os pongo?").replace('\n', ' ')
                            except Exception as e:
                                print(f"[ERROR BUCLE AUTONOMO DEEPSEEK]: {e}")
                                msg = f"¡Vaya temazos de sesión familia! Recordad usar !liga para ganar la sesión. {random.choice(self.emotes_twitch)}"
                        else:
                            msg = f"¡Vaya temazos de sesión familia! {random.choice(self.emotes_twitch)}"
                        await canal_obj.send(f"{msg}")
            except Exception as e:
                print(f"Error bucle autónomo: {e}")

    # ==================== COMANDOS ====================
    @commands.command(name='puntos', aliases=['vatios', 'fiesta'])
    async def cmd_puntos(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        cant = puntos_canal.get(usr, 10)
        await ctx.send(f"@{ctx.author.name}, llevas acumulados **{cant} puntos** en la Liga Mensual. ⚡")

    @commands.command(name='liga', aliases=['top', 'ranking'])
    async def cmd_liga(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        if not puntos_canal:
            return await ctx.send("La liga mensual acaba de arrancar. ¡Escribe en el chat para puntuar!")
        ranking_ordenado = sorted(puntos_canal.items(), key=lambda x: x[1], reverse=True)[:3]
        texto_ranking = "🏆 TOP 3 LIGA MENSUAL: "
        for i, (usr, pts) in enumerate(ranking_ordenado, 1):
            medalla = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
            texto_ranking += f"{medalla} @{usr} ({pts} pts)  "
        await ctx.send(texto_ranking)

    @commands.command(name='premio', aliases=['sesionmes'])
    async def cmd_premio(self, ctx: commands.Context):
        await ctx.send("🎁 **PREMIO MENSUAL:** ¡El seguidor que más participe ganará una **sesión exclusiva** personalizada! 🎧🔥")

    @commands.command(name='ruleta', aliases=['suerte', 'apostar'])
    async def cmd_ruleta(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        puntos_canal = self.cargar_puntos_canal(canal)
        if usr not in puntos_canal: puntos_canal[usr] = 10
        resultado = random.choice([-20, -10, 15, 30, 60, 120, 250])
        puntos_canal[usr] += resultado
        if puntos_canal[usr] < 0: puntos_canal[usr] = 0
        self.guardar_puntos_canal(canal, puntos_canal)
        if resultado > 0:
            await ctx.send(f"🎡 @{ctx.author.name} gana **+{resultado} puntos** en la ruleta! (Total: {puntos_canal[usr]} pts) 🚀")
        else:
            await ctx.send(f"🎡 ¡Ay @{ctx.author.name}, la ruleta pinchó y pierdes **{resultado} puntos**! 💥")

    @commands.command(name='ahorcado')
    async def cmd_ahorcado(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["ahorcado_activo"]:
            progreso = "".join([l if l in estado["letras_adivinadas"] else "_" for l in estado["palabra_secreta"]])
            return await ctx.send(f"🎮 Ahorcado activo: `{progreso}` (Intentos: {estado['intentos_ahorcado']})")
        estado["palabra_secreta"] = random.choice(self.palabras_ahorcado)
        estado["letras_adivinadas"] = set()
        estado["intentos_ahorcado"] = 6
        estado["ahorcado_activo"] = True
        await ctx.send(f"🕹️ **¡Ahorcado Clubber!** Pista: Remember. `{'_' * len(estado['palabra_secreta'])}`")

    @commands.command(name='trivia', aliases=['adivina'])
    async def cmd_trivia(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["trivia_activa"]: return await ctx.send("⚠️ ¡Ya hay trivia en marcha!")
        p_obj = random.choice(self.preguntas_trivia)
        estado["trivia_activa"] = True
        estado["trivia_respuesta_correcta"] = p_obj["respuesta"]
        await ctx.send(f"🧠 **TRIVIA:** {p_obj['pregunta']}")

    @commands.command(name='verdaderofalso', aliases=['vf'])
    async def cmd_verdaderofalso(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["vf_activo"]: return await ctx.send("⚠️ ¡Ya hay una pregunta activa!")
        p_obj = random.choice(self.preguntas_vf)
        estado["vf_activo"] = True
        estado["vf_respuesta_correcta"] = p_obj["respuesta"]
        await ctx.send(f"❓ **V/F:** {p_obj['pregunta']} (Escribe `verdadero` o `falso`)")

    @commands.command(name='sala', aliases=['nostalgia', 'ruta'])
    async def cmd_sala(self, ctx: commands.Context):
        await ctx.send(f"🏛️ **MEMORIA CLUBBER:** {random.choice(self.salas_historias)}")

    @commands.command(name='pedir')
    async def cmd_pedir(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        msg = ctx.message.content.split(' ', 1)
        if len(msg) < 2: return await ctx.send(f"@{ctx.author.name} Pon el tema así: `!pedir [Artista - Canción]`")
        self.guardar_peticion_obs(canal, ctx.author.name, msg[1])
        await ctx.send(f"¡Apuntado '{msg[1]}', @{ctx.author.name}! 🎵")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene un {random.randint(0,100)}% de energía festera hoy. 🔥")

    @commands.command(name='normas', aliases=['reglas'])
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("📜 **Normas:** 1. Respeto. 2. Cero toxicidad. 3. ¡Disfruta del buen Remember y Trance! 🎧")

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send("🤖 Comandos: !liga, !puntos, !ruleta, !ahorcado, !trivia, !vf, !pedir, !sala, !festero")

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
