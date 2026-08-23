import os
import random
import time
import asyncio
import traceback
import json
import http.server
import socketserver
import threading
from twitchio.ext import commands
from google import genai

# ==========================================
# 1. SERVIDOR HTTP OBLIGATORIO PARA RAILWAY
# ==========================================
PORT = int(os.environ.get("PORT", 8080))

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def iniciar_web():
    try:
        with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
            print(f"[WEB] Servidor HTTP activo y escuchando en el puerto {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[WEB] Error crítico en servidor HTTP: {e}")

hilo_web = threading.Thread(target=iniciar_web, daemon=True)
hilo_web.start()

# ==========================================
# 2. CONFIGURACIÓN DEL BOT Y GEMINI
# ==========================================
TOKEN = os.environ.get('TWITCH_TOKEN', '').strip()
BOT_NICK = os.environ.get('TWITCH_BOT', 'sesionesoldschool').lower() 

canal_env = os.environ.get('TWITCH_CANAL', 'jonasRDB').strip().lower()
CANALES = [canal_env, 'koko_deejay'] if canal_env != 'koko_deejay' else [canal_env]

GEMINI_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

print(f"[INIT] Arrancando bot para canales: {CANALES} | Modelo: {GEMINI_MODEL}")
print(f"[INIT] ¿Existe GEMINI_API_KEY?: {bool(GEMINI_KEY)}")

gemini_client = None
if GEMINI_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_KEY)
        print("[INIT] ¡Cliente de Google Gemini conectado con éxito!")
    except Exception as e:
        print(f"[INIT ERROR] Falló al crear genai.Client: {e}")
        traceback.print_exc()
else:
    print("[INIT AVISO] No se encontró GEMINI_API_KEY en el entorno.")

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=CANALES
        )
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm"]
        self.juegos_estado = {}
        self.usuarios_saludados = {}

        for chan in CANALES:
            self.juegos_estado[chan] = {
                "trivia_activa": False, "trivia_respuesta_correcta": "",
                "ahorcado_activo": False, "palabra_secreta": "", "letras_adivinadas": set(), "intentos_ahorcado": 6,
                "vf_activo": False, "vf_respuesta_correcta": ""
            }
            self.usuarios_saludados[chan] = set()

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
            except:
                pass
        return {}

    def guardar_puntos_canal(self, canal, datos):
        archivo = self.obtener_archivo_puntos(canal)
        try:
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except:
            pass

    def guardar_peticion_obs(self, canal, usuario, cancion):
        try:
            with open(f"peticiones_{canal}.txt", "a", encoding="utf-8") as f:
                f.write(f"@{usuario} pidió: {cancion}\n")
        except:
            pass

    async def event_ready(self):
        print(f'=== ¡BOT CONECTADO CORRECTAMENTE EN: {CANALES} ===')
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

        if autor_lower == BOT_NICK:
            return

        if canal_nombre not in self.juegos_estado:
            self.juegos_estado[canal_nombre] = {
                "trivia_activa": False, "trivia_respuesta_correcta": "",
                "ahorcado_activo": False, "palabra_secreta": "", "letras_adivinadas": set(), "intentos_ahorcado": 6,
                "vf_activo": False, "vf_respuesta_correcta": ""
            }
        if canal_nombre not in self.usuarios_saludados:
            self.usuarios_saludados[canal_nombre] = set()

        puntos_canal = self.cargar_puntos_canal(canal_nombre)
        puntos_canal[autor_lower] = puntos_canal.get(autor_lower, 10) + 3
        self.guardar_puntos_canal(canal_nombre, puntos_canal)

        if autor_lower not in self.usuarios_saludados[canal_nombre] and autor_lower != canal_nombre:
            self.usuarios_saludados[canal_nombre].add(autor_lower)
            await message.channel.send(f"¡Qué pasa @{autor}! Pilla sitio. Cuanto más chatees, más subes en la Liga Mensual para ganar **una sesión exclusiva**. 🎧🔥")

        content = message.content.strip()
        content_lower = content.lower()
        estado = self.juegos_estado[canal_nombre]

        if estado["trivia_activa"] and content_lower == estado["trivia_respuesta_correcta"].lower():
            estado["trivia_activa"] = False
            puntos_canal[autor_lower] += 50 
            self.guardar_puntos_canal(canal_nombre, puntos_canal)
            await message.channel.send(f"¡Buena, @{autor}! Has clavado la trivia (+50 pts). 🎯")
            return

        if estado["vf_activo"] and content_lower in ["verdadero", "v", "falso", "f"]:
            val_usuario = "verdadero" if content_lower in ["verdadero", "v"] else "falso"
            if val_usuario == estado["vf_respuesta_correcta"]:
                estado["vf_activo"] = False
                puntos_canal[autor_lower] += 30
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"✅ ¡Correcto @{autor}! Era **{estado['vf_respuesta_correcta'].upper()}** (+30 pts). 🎉")
                return

        if estado["ahorcado_activo"]:
            if len(content_lower) == 1 and content_lower.isalpha():
                if content_lower in estado["palabra_secreta"]:
                    estado["letras_adivinadas"].add(content_lower)
                    if all(l in estado["letras_adivinadas"] for l in estado["palabra_secreta"]):
                        estado["ahorcado_activo"] = False
                        puntos_canal[autor_lower] += 40
                        self.guardar_puntos_canal(canal_nombre, puntos_canal)
                        await message.channel.send(f"¡Impresionante @{autor}! Palabra completada: **{estado['palabra_secreta'].upper()}** (+40 pts). 🎉")
                else:
                    estado["intentos_ahorcado"] -= 1
                    if estado["intentos_ahorcado"] <= 0:
                        estado["ahorcado_activo"] = False
                        await message.channel.send(f"💀 ¡Sin intentos! La palabra era: **{estado['palabra_secreta'].upper()}**")
                return
            elif content_lower == estado["palabra_secreta"]:
                estado["ahorcado_activo"] = False
                puntos_canal[autor_lower] += 50
                self.guardar_puntos_canal(canal_nombre, puntos_canal)
                await message.channel.send(f"🏆 ¡BOOM! @{autor} adivinó la palabra secreta: **{estado['palabra_secreta'].upper()}** (+50 pts).")
                return

        if content.startswith('!'):
            await self.handle_commands(message)
            return

        # ==========================================
        # CONVERSACIÓN LIBRE DIRECTA CON LA IA
        # ==========================================
        texto_limpio = content.replace(f"@{BOT_NICK}", "").strip()
        if not texto_limpio:
            return

        print(f"🔥 [CHAT IA] Mensaje de @{autor}: '{texto_limpio}'")
        
        if not gemini_client:
            print("❌ [ERROR] gemini_client es None. Revisa tu variable GEMINI_API_KEY en Railway.")
            await message.channel.send(f"@{autor} ¡Ey! Falta configurar la API Key de Gemini en el servidor.")
            return

        try:
            prompt = (
                f"Eres un bot de Twitch llamado 'sesionesoldschool' experto en música Remember, Hard Dance y Trance. "
                f"El usuario {autor} te ha dicho: '{texto_limpio}'. "
                f"Responde de forma natural, cercana y como un colega festero. "
                f"Máximo 100 caracteres, sin saltos de línea."
            )

            print(f"🤖 [GEMINI REQUEST] Enviando a modelo '{GEMINI_MODEL}'...")
            respuesta_ia = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            if respuesta_ia and hasattr(respuesta_ia, 'text') and respuesta_ia.text:
                texto_final = respuesta_ia.text.strip().replace('\n', ' ')
                print(f"✅ [IA RESPONDE]: {texto_final}")
                await message.channel.send(f"@{autor} {texto_final}")
                return
            else:
                print("⚠️ [AVISO] La API respondió pero el texto vino vacío o sin la propiedad .text")
                print(f"Objeto respuesta recibido: {respuesta_ia}")
        except Exception as e:
            print(f"❌ [EXCEPCIÓN CRÍTICA EN GEMINI]: {e}")
            traceback.print_exc()

        # Respuesta de emergencia si falla la IA
        await message.channel.send(f"@{autor} ¡A tope con la sesión de remember!")

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
                        msg = f"¡Vaya temazos de sesión familia! Recordad usar !liga para ganar la sesión. {random.choice(self.emotes_twitch)}"
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

if __name__ == '__main__':
    if not TOKEN:
        print("[ERROR CRÍTICO] Falta la variable TWITCH_TOKEN.")
    else:
        try:
            bot = Bot()
            bot.run()
        except Exception as e:
            print(f"[CRITICAL ERROR]: {e}")
            traceback.print_exc()
