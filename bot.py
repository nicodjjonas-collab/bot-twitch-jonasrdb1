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
            print(f"[WEB] Servidor HTTP activo en el puerto {PORT}")
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


# ==========================================
# 3. CLASE BOT
# ==========================================
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=CANALES
        )

        # --- IA conversacional (PRIMERO — necesario para _init_canal_estado) ---
        self.historial_chat = {}          # {canal: [(autor, texto), ...]}
        self.MAX_HISTORIAL = 15
        self.cooldown_ia = {}             # {canal: timestamp último mensaje IA}
        self.COOLDOWN_SEGUNDOS = 10       # mínimo entre respuestas de la IA
        self.PROB_INTERVENCION = 0.30     # 30% de entrar en conversación genérica

        # --- Emotes y listas temáticas ---
        self.emotes_twitch = ["Kappa", "PogChamp", "NotLikeThis", "BibleThump", "LUL", "pepeJAM", "CatJAM", "Kreygasm"]

        self.palabras_ahorcado = [
            "makina", "hardance", "trance", "eurodance", "valencia",
            "puzle", "spook", "chasis", "pontateri", "bakalao",
            "cabina", "vinilo", "discoteca", "remember", "clubber"
        ]

        self.salas_historias = [
            "¿Sabías que la mítica ruta del bakalao en Valencia cambió la historia de la música electrónica en España?",
            "Recordando los cierres épicos en Puzzle, Spook Factory y Central Rock. ¡Menudos templos del sonido!",
            "El sonido Makina, el Hard Dance a 150 BPM, el Uplifting Trance y el Eurodance marcaron a toda una generación.",
            "¿Quién vivió las sesiones legendarias de Chasis, Pont Aeri, Central o Masía? ¡Que levante el dedo el chat!",
            "Aquellas noches de sábado que empezaban el viernes y acababan el domingo... ¡irrepetibles!",
            "Los viniles de Bonzai Records, Music Man, Dancing Mood... eso era cultura, no solo música.",
        ]

        self.preguntas_trivia = [
            {"pregunta": "¿En qué año se lanzó 'Fly on the Wings of Love' de XTM & DJ Chus?", "respuesta": "2003"},
            {"pregunta": "¿De qué estilo hablamos si mencionamos bombos pesados a 150 BPM típicos de la zona de levante?", "respuesta": "makina"},
            {"pregunta": "¿Qué famoso DJ firmó el temazo trance 'Silence' con Sarah McLachlan?", "respuesta": "tiesto"},
            {"pregunta": "¿Qué estilo melódico y bailable arrasaba en las discotecas a finales de los 90 y principios de los 2000?", "respuesta": "eurodance"},
            {"pregunta": "¿Cómo se llamaba la discoteca valenciana conocida como templo del Hard Dance y la Makina?", "respuesta": "spook"},
            {"pregunta": "¿Qué grupo publicó el himno eurodance 'Blue (Da Ba Dee)'?", "respuesta": "eiffel 65"},
            {"pregunta": "¿En qué ciudad española tuvo su epicentro la ruta del bakalao?", "respuesta": "valencia"},
        ]

        self.preguntas_vf = [
            {"pregunta": "La Ruta del Bakalao se desarrolló principalmente en la Comunidad Valenciana.", "respuesta": "verdadero"},
            {"pregunta": "El estilo Makina suele rondar habitualmente entre los 90 y 100 BPM.", "respuesta": "falso"},
            {"pregunta": "Discotecas como Puzzle y Spook Factory fueron auténticos templos de la música electrónica en los 90.", "respuesta": "verdadero"},
            {"pregunta": "El Trance es un género musical que se originó en los años 50.", "respuesta": "falso"},
            {"pregunta": "El vinilo sigue siendo un formato legendario muy valorado en las sesiones de música remember.", "respuesta": "verdadero"},
            {"pregunta": "Pont Aeri era una discoteca situada en Tarragona.", "respuesta": "verdadero"},
            {"pregunta": "El Eurodance es exactamente lo mismo que el Hard Trance.", "respuesta": "falso"},
        ]

        # --- Estado de juegos por canal ---
        self.juegos_estado = {}
        self.usuarios_saludados = {}

        for chan in CANALES:
            self._init_canal_estado(chan)

    # ─── Inicialización de estado por canal ───────────────────────────────────
    def _init_canal_estado(self, canal):
        self.juegos_estado[canal] = {
            "trivia_activa": False,
            "trivia_respuesta_correcta": "",
            "ahorcado_activo": False,
            "palabra_secreta": "",
            "letras_adivinadas": set(),
            "intentos_ahorcado": 6,
            "vf_activo": False,
            "vf_respuesta_correcta": "",
        }
        self.usuarios_saludados[canal] = set()
        self.historial_chat[canal] = []

    # ─── Gestión de puntos ────────────────────────────────────────────────────
    def _archivo_puntos(self, canal):
        return f"puntos_liga_{canal.lower()}.json"

    def cargar_puntos(self, canal):
        archivo = self._archivo_puntos(canal)
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def guardar_puntos(self, canal, datos):
        try:
            with open(self._archivo_puntos(canal), 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def sumar_puntos(self, canal, usuario, cantidad):
        datos = self.cargar_puntos(canal)
        datos[usuario] = datos.get(usuario, 10) + cantidad
        if datos[usuario] < 0:
            datos[usuario] = 0
        self.guardar_puntos(canal, datos)
        return datos[usuario]

    # ─── Peticiones OBS ───────────────────────────────────────────────────────
    def guardar_peticion_obs(self, canal, usuario, cancion):
        try:
            with open(f"peticiones_{canal}.txt", "a", encoding="utf-8") as f:
                f.write(f"@{usuario} pidió: {cancion}\n")
        except Exception:
            pass

    # ─── Historial conversacional para la IA ──────────────────────────────────
    def registrar_en_historial(self, canal, autor, texto):
        if canal not in self.historial_chat:
            self.historial_chat[canal] = []
        self.historial_chat[canal].append((autor, texto))
        if len(self.historial_chat[canal]) > self.MAX_HISTORIAL:
            self.historial_chat[canal].pop(0)

    def construir_contexto(self, canal):
        historial = self.historial_chat.get(canal, [])
        if not historial:
            return "(Sin mensajes previos en el chat)"
        return "\n".join(f"{a}: {t}" for a, t in historial)

    # ─── Lógica de cuándo interviene la IA ───────────────────────────────────
    def debe_intervenir(self, canal, autor_lower, texto):
        ahora = time.time()
        if ahora - self.cooldown_ia.get(canal, 0) < self.COOLDOWN_SEGUNDOS:
            return False

        texto_lower = texto.lower()
        bot_mencionado = BOT_NICK in texto_lower

        # Siempre responde si le mencionan directamente
        if bot_mencionado:
            return True

        # Preguntas abiertas al chat
        es_pregunta = (
            "?" in texto or
            any(texto_lower.startswith(p) for p in [
                "alguien", "qué", "que ", "cuál", "cual", "quién", "quien",
                "os gusta", "os acordáis", "recordáis", "sabéis", "sabe alguien"
            ])
        )
        if es_pregunta and random.random() < 0.65:
            return True

        # Temas que le apasionan — entra con ganas
        temas_calientes = [
            "makina", "bakalao", "trance", "hardance", "hard dance",
            "eurodance", "spook", "puzzle", "pont aeri", "chasis",
            "ruta", "remember", "vinilo", "dj", "sesión", "session",
            "tema", "temazos", "clubber", "discoteca", "valencia"
        ]
        if any(t in texto_lower for t in temas_calientes) and random.random() < 0.55:
            return True

        # Intervención aleatoria natural
        if random.random() < self.PROB_INTERVENCION:
            return True

        return False

    # ─── Llamada a Gemini con contexto ────────────────────────────────────────
    async def responder_con_ia(self, canal, autor_actual, texto_actual):
        contexto = self.construir_contexto(canal)

        prompt = (
            f"Eres 'sesionesoldschool', un tío del chat de Twitch. Eres de Valencia, llevas toda la vida con el "
            f"remember, la makina, el trance y el eurodance de los 90 y 2000. Conoces la ruta del bakalao de "
            f"memoria: Spook Factory, Puzzle, Pont Aeri, Chasis, Central Rock, Barraca, Espiral... "
            f"Hablas de forma natural y coloquial, como alguien del chat, no como un bot. Puedes opinar, "
            f"contradecir, hacer bromas, recordar artistas, preguntar de vuelta. "
            f"NO digas que eres una IA. NO uses frases de bot ni presentaciones. "
            f"Escribe como se escribe en Twitch: corto, directo, sin rollos. Máximo 180 caracteres. "
            f"Sin saltos de línea. Sin emojis exagerados. "
            f"Si el mensaje no te incumbe o no tienes nada que aportar, responde SOLO con la palabra: SILENCIO\n\n"
            f"Chat reciente:\n{contexto}\n\n"
            f"Último mensaje ({autor_actual}): \"{texto_actual}\"\n"
            f"¿Qué dices?"
        )

        try:
            respuesta = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            if respuesta and hasattr(respuesta, 'text') and respuesta.text:
                texto = respuesta.text.strip().replace('\n', ' ')
                if texto.upper().startswith("SILENCIO"):
                    return None
                return texto
        except Exception as e:
            print(f"❌ [IA ERROR]: {e}")
            traceback.print_exc()
        return None

    # ==========================================
    # EVENTOS PRINCIPALES
    # ==========================================
    async def event_ready(self):
        print(f'=== BOT CONECTADO EN: {CANALES} ===')
        asyncio.create_task(self.bucle_autonomo_chat())
        asyncio.create_task(self.bucle_puntos_actividad())

    async def event_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"[ERROR COMANDO] {error}")

    async def event_message(self, message):
        if message.echo:
            return

        autor = message.author.name
        autor_lower = autor.lower()
        canal = message.channel.name.lower()

        if autor_lower == BOT_NICK:
            return

        # Inicializar canal si no existe
        if canal not in self.juegos_estado:
            self._init_canal_estado(canal)

        content = message.content.strip()
        content_lower = content.lower()
        estado = self.juegos_estado[canal]

        # --- Puntos por participar ---
        self.sumar_puntos(canal, autor_lower, 3)

        # --- Saludo de bienvenida (una vez por sesión) ---
        if autor_lower not in self.usuarios_saludados[canal] and autor_lower != canal:
            self.usuarios_saludados[canal].add(autor_lower)
            await message.channel.send(
                f"¡Qué pasa @{autor}! Pilla sitio. Cuanto más chatees, más subes en la Liga Mensual. 🎧🔥"
            )

        # ─── JUEGOS: comprobación de respuestas activas ───────────────────────

        # Trivia
        if estado["trivia_activa"] and not content.startswith('!'):
            if content_lower == estado["trivia_respuesta_correcta"].lower():
                estado["trivia_activa"] = False
                total = self.sumar_puntos(canal, autor_lower, 50)
                await message.channel.send(
                    f"¡Buena, @{autor}! Has clavado la trivia (+50 pts → {total} pts). 🎯"
                )
                return

        # Verdadero/Falso
        if estado["vf_activo"] and content_lower in ["verdadero", "v", "falso", "f"]:
            val_usuario = "verdadero" if content_lower in ["verdadero", "v"] else "falso"
            if val_usuario == estado["vf_respuesta_correcta"]:
                estado["vf_activo"] = False
                total = self.sumar_puntos(canal, autor_lower, 30)
                await message.channel.send(
                    f"✅ ¡Correcto @{autor}! Era **{estado['vf_respuesta_correcta'].upper()}** (+30 pts → {total} pts). 🎉"
                )
                return

        # Ahorcado — letra suelta
        if estado["ahorcado_activo"] and not content.startswith('!'):
            if len(content_lower) == 1 and content_lower.isalpha():
                letra = content_lower
                if letra in estado["letras_adivinadas"]:
                    return  # letra ya usada, ignorar
                estado["letras_adivinadas"].add(letra)
                if letra in estado["palabra_secreta"]:
                    progreso = " ".join(
                        l.upper() if l in estado["letras_adivinadas"] else "_"
                        for l in estado["palabra_secreta"]
                    )
                    if all(l in estado["letras_adivinadas"] for l in estado["palabra_secreta"]):
                        estado["ahorcado_activo"] = False
                        total = self.sumar_puntos(canal, autor_lower, 40)
                        await message.channel.send(
                            f"🎉 ¡@{autor} completó la palabra: **{estado['palabra_secreta'].upper()}** (+40 pts → {total} pts)!"
                        )
                    else:
                        await message.channel.send(f"✅ ¡Está! → {progreso} (Intentos: {estado['intentos_ahorcado']})")
                else:
                    estado["intentos_ahorcado"] -= 1
                    progreso = " ".join(
                        l.upper() if l in estado["letras_adivinadas"] else "_"
                        for l in estado["palabra_secreta"]
                    )
                    if estado["intentos_ahorcado"] <= 0:
                        estado["ahorcado_activo"] = False
                        await message.channel.send(
                            f"💀 ¡Sin intentos! La palabra era: **{estado['palabra_secreta'].upper()}**"
                        )
                    else:
                        await message.channel.send(
                            f"❌ '{letra.upper()}' no está → {progreso} (Intentos: {estado['intentos_ahorcado']})"
                        )
                return

            # Ahorcado — palabra completa
            elif content_lower == estado["palabra_secreta"] and len(content_lower) > 1:
                estado["ahorcado_activo"] = False
                total = self.sumar_puntos(canal, autor_lower, 50)
                await message.channel.send(
                    f"🏆 ¡BOOM! @{autor} adivinó: **{estado['palabra_secreta'].upper()}** (+50 pts → {total} pts)."
                )
                return

        # ─── COMANDOS ────────────────────────────────────────────────────────
        if content.startswith('!'):
            await self.handle_commands(message)
            return

        # ─── IA CONVERSACIONAL ────────────────────────────────────────────────
        self.registrar_en_historial(canal, autor, content)

        if gemini_client and self.debe_intervenir(canal, autor_lower, content):
            respuesta = await self.responder_con_ia(canal, autor, content)
            if respuesta:
                self.cooldown_ia[canal] = time.time()
                await message.channel.send(respuesta)

    # ==========================================
    # BUCLES AUTÓNOMOS
    # ==========================================
    async def bucle_puntos_actividad(self):
        """Reparte puntos pasivos a todos los usuarios cada 5 minutos."""
        while True:
            await asyncio.sleep(300)
            for canal in CANALES:
                datos = self.cargar_puntos(canal)
                if datos:
                    for usr in datos:
                        datos[usr] = datos.get(usr, 0) + 15
                    self.guardar_puntos(canal, datos)

    async def bucle_autonomo_chat(self):
        """Mensaje periódico al chat cada ~3 minutos usando la IA."""
        await asyncio.sleep(30)
        while True:
            try:
                await asyncio.sleep(180)
                for canal_nombre in CANALES:
                    canal_obj = self.get_channel(canal_nombre)
                    if not canal_obj:
                        continue

                    if gemini_client:
                        contexto = self.construir_contexto(canal_nombre)
                        prompt = (
                            f"Eres 'sesionesoldschool', un tío del chat de Twitch que sabe todo sobre el remember, "
                            f"la makina, el trance y el eurodance de los 90/2000. "
                            f"Suelta un comentario corto, natural y espontáneo sobre la música, una sala mítica, "
                            f"un recuerdo clubber o pregunta algo al chat. Sin presentarte, como si llevaras rato aquí. "
                            f"Máximo 180 caracteres. Sin saltos de línea.\n\n"
                            f"Contexto reciente del chat:\n{contexto}"
                        )
                        try:
                            r = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                            if r and hasattr(r, 'text') and r.text:
                                await canal_obj.send(r.text.strip().replace('\n', ' '))
                                continue
                        except Exception as e:
                            print(f"[BUCLE IA ERROR]: {e}")

                    # Fallback si falla la IA
                    await canal_obj.send(
                        f"{random.choice(self.salas_historias)} {random.choice(self.emotes_twitch)}"
                    )

            except Exception as e:
                print(f"[ERROR BUCLE AUTÓNOMO]: {e}")

    # ==========================================
    # COMANDOS
    # ==========================================

    # --- Liga y puntos ---
    @commands.command(name='puntos', aliases=['vatios', 'fiesta'])
    async def cmd_puntos(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        datos = self.cargar_puntos(canal)
        cant = datos.get(usr, 10)
        await ctx.send(f"@{ctx.author.name}, llevas **{cant} puntos** en la Liga Mensual. ⚡")

    @commands.command(name='liga', aliases=['top', 'ranking'])
    async def cmd_liga(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        datos = self.cargar_puntos(canal)
        if not datos:
            return await ctx.send("La liga mensual acaba de arrancar. ¡Escribe en el chat para puntuar!")
        top3 = sorted(datos.items(), key=lambda x: x[1], reverse=True)[:3]
        medallas = ["🥇", "🥈", "🥉"]
        texto = "🏆 TOP 3 LIGA MENSUAL: " + "  ".join(
            f"{medallas[i]} @{usr} ({pts} pts)" for i, (usr, pts) in enumerate(top3)
        )
        await ctx.send(texto)

    @commands.command(name='premio', aliases=['sesionmes'])
    async def cmd_premio(self, ctx: commands.Context):
        await ctx.send(
            "🎁 **PREMIO MENSUAL:** ¡El seguidor que más participe ganará una **sesión exclusiva** personalizada! 🎧🔥"
        )

    # --- Ruleta ---
    @commands.command(name='ruleta', aliases=['suerte', 'apostar'])
    async def cmd_ruleta(self, ctx: commands.Context):
        usr = ctx.author.name.lower()
        canal = ctx.channel.name.lower()
        resultado = random.choice([-20, -10, 15, 30, 60, 120, 250])
        total = self.sumar_puntos(canal, usr, resultado)
        if resultado > 0:
            await ctx.send(f"🎡 @{ctx.author.name} gana **+{resultado} pts** en la ruleta! (Total: {total} pts) 🚀")
        else:
            await ctx.send(f"🎡 Ay @{ctx.author.name}, la ruleta pinchó: **{resultado} pts** (Total: {total} pts) 💥")

    # --- Ahorcado ---
    @commands.command(name='ahorcado')
    async def cmd_ahorcado(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]

        if estado["ahorcado_activo"]:
            progreso = " ".join(
                l.upper() if l in estado["letras_adivinadas"] else "_"
                for l in estado["palabra_secreta"]
            )
            return await ctx.send(
                f"🎮 Ahorcado activo: {progreso} (Intentos restantes: {estado['intentos_ahorcado']})"
            )

        palabra = random.choice(self.palabras_ahorcado)
        estado["palabra_secreta"] = palabra
        estado["letras_adivinadas"] = set()
        estado["intentos_ahorcado"] = 6
        estado["ahorcado_activo"] = True
        guiones = " ".join("_" for _ in palabra)
        await ctx.send(
            f"🕹️ **¡Ahorcado Clubber!** [{len(palabra)} letras] → {guiones} "
            f"| Escribe una letra o la palabra entera. Pista: música remember."
        )

    # --- Trivia ---
    @commands.command(name='trivia', aliases=['adivina'])
    async def cmd_trivia(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["trivia_activa"]:
            return await ctx.send("⚠️ ¡Ya hay una trivia en marcha! Responde en el chat.")
        p = random.choice(self.preguntas_trivia)
        estado["trivia_activa"] = True
        estado["trivia_respuesta_correcta"] = p["respuesta"]
        await ctx.send(f"🧠 **TRIVIA (+50 pts):** {p['pregunta']}")

    # --- Verdadero/Falso ---
    @commands.command(name='verdaderofalso', aliases=['vf'])
    async def cmd_vf(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        estado = self.juegos_estado[canal]
        if estado["vf_activo"]:
            return await ctx.send("⚠️ ¡Ya hay una pregunta activa! Escribe `verdadero` o `falso`.")
        p = random.choice(self.preguntas_vf)
        estado["vf_activo"] = True
        estado["vf_respuesta_correcta"] = p["respuesta"]
        await ctx.send(f"❓ **V/F (+30 pts):** {p['pregunta']} | Responde: `verdadero` o `falso`")

    # --- Sala / nostalgia ---
    @commands.command(name='sala', aliases=['nostalgia', 'ruta'])
    async def cmd_sala(self, ctx: commands.Context):
        await ctx.send(f"🏛️ **MEMORIA CLUBBER:** {random.choice(self.salas_historias)}")

    # --- Petición de temas ---
    @commands.command(name='pedir')
    async def cmd_pedir(self, ctx: commands.Context):
        canal = ctx.channel.name.lower()
        partes = ctx.message.content.split(' ', 1)
        if len(partes) < 2:
            return await ctx.send(f"@{ctx.author.name} Usa así: `!pedir Artista - Canción`")
        cancion = partes[1].strip()
        self.guardar_peticion_obs(canal, ctx.author.name, cancion)
        await ctx.send(f"🎵 ¡Apuntado! '{cancion}' pedido por @{ctx.author.name}.")

    # --- Medidor festero ---
    @commands.command(name='festero')
    async def cmd_festero(self, ctx: commands.Context):
        nivel = random.randint(0, 100)
        if nivel >= 80:
            msg = "¡Hoy sales hasta el amanecer! 🌅🔥"
        elif nivel >= 50:
            msg = "Con ganas pero sin pasarse... por ahora. 😏"
        else:
            msg = "Parece que hoy toca sofá y recuerdos. 😴"
        await ctx.send(f"🎉 @{ctx.author.name} tiene un **{nivel}% de energía festera** hoy. {msg}")

    # --- Normas ---
    @commands.command(name='normas', aliases=['reglas'])
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send(
            "📜 **Normas:** 1. Respeto ante todo. 2. Cero toxicidad. "
            "3. Disfruta del buen Remember, Makina y Trance. ¡Somos familia clubber! 🎧"
        )

    # --- Lista de comandos ---
    @commands.command(name='comandos', aliases=['help', 'ayuda'])
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(
            "🤖 Comandos disponibles: !liga · !puntos · !ruleta · "
            "!ahorcado · !trivia · !vf · !pedir · !sala · !festero · !premio · !normas"
        )


# ==========================================
# 4. ARRANQUE
# ==========================================
if __name__ == '__main__':
    if not TOKEN:
        print("[ERROR CRÍTICO] Falta la variable TWITCH_TOKEN en el entorno.")
    else:
        try:
            bot = Bot()
            bot.run()
        except Exception as e:
            print(f"[CRITICAL ERROR]: {e}")
            traceback.print_exc()
