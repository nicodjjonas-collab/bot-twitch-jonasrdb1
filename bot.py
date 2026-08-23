import os
import random
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from twitchio.ext import commands
from google import genai

# --- VALIDACIÓN DE CREDENCIALES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
TWITCH_TOKEN = os.environ.get("TMI_TOKEN")
TWITCH_CHANNEL = os.environ.get("CHANNEL")

if not GEMINI_API_KEY:
    print("⚠️ [ADVERTENCIA]: Falta la variable GEMINI_API_KEY en Railway.")
if not TWITCH_TOKEN or not TWITCH_CHANNEL:
    print("❌ [ERROR CRÍTICO]: Faltan TMI_TOKEN o CHANNEL en las variables de entorno de Railway.")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# --- CONFIGURACIÓN DEL PROMPT PARTICIPATIVO ---
SYSTEM_PROMPT = """
Eres el Copiloto IA y DJ virtual oficial del canal de Twitch de música Remember, Makina, Hard Dance, Eurodance y Tech House. 
Tu objetivo es animar el chat, comentar los temazos que suenan, interactuar con los viewers y dar ambiente de discoteca de los 90 y 2000 (Ruta del Bakalao, etc.).
Sé cercano, divertido, usa jerga electrónica y expresión fiestera (¡A tope!, ¡Vivan los 90!, ¡Temazo!).
Responde siempre de forma natural, amigable y participativa a lo que digan en el chat o a lo que te pregunten. No te quedes callado; aporta energía positiva a la comunidad.
"""

def responder_con_ia(mensaje_usuario, nombre_usuario="Viewer"):
    try:
        modelo_actual = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        prompt_completo = f"{SYSTEM_PROMPT}\n\n{nombre_usuario} dice: {mensaje_usuario}"
        
        respuesta = gemini_client.models.generate_content(
            model=modelo_actual,
            contents=prompt_completo
        )
        
        if respuesta and respuesta.text:
            texto_respuesta = respuesta.text.strip()
            texto_respuesta = " ".join(texto_respuesta.splitlines())
            return texto_respuesta
        
        return "¡Qué pasa! ¡Menudo ambientazo tenemos por el chat! 🎧🔥"
        
    except Exception as e:
        print(f"❌ [IA ERROR]: {e}")
        return "¡A tope con la sesión! 🚀"


# --- CONFIGURACIÓN DEL BOT DE TWITCH Y MINIJUEGOS ---
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            prefix=os.environ.get("BOT_PREFIX", "!"),
            initial_channels=[TWITCH_CHANNEL]
        )

    async def event_ready(self):
        print(f"✅ Conectado a Twitch como | {self.nick}")
        print(f"channels: {self.initial_channels}")

    async def event_message(self, message):
        if message.echo:
            return

        await self.handle_commands(message)

        contenido = message.content
        autor = message.author.name if message.author else "Viewer"
        
        if contenido.startswith("!"):
            return

        print(f"💬 Mensaje recibido de {autor}: {contenido}")
        
        respuesta_ia = responder_con_ia(contenido, autor)
        
        if respuesta_ia:
            await message.channel.send(respuesta_ia)

    # --- COMANDOS Y MINIJUEGOS ---
    @commands.command(name="temazo")
    async def cmd_temazo(self, ctx):
        frases_temazo = [
            f"@{ctx.author.name} ¡MENUDO HIMNO DE LA RUTA! 🎹🔥 ¡A bailar se ha dicho!",
            f"@{ctx.author.name} Subiendo los sub-bajos al 200%! Esto es Remember del bueno. 🎧✨",
            f"@{ctx.author.name} ¡Vaya melodía épica! Las manos arriba todo el mundo. 🙌🚀"
        ]
        await ctx.send(random.choice(frases_temazo))

    @commands.command(name="energia")
    async def cmd_energia(self, ctx):
        nivel = random.randint(85, 100)
        await ctx.send(f"⚡ @{ctx.author.name} ¡El nivel de energía del chat está al **{nivel}%**! ¡Esto quema pista! 🔥🎛️")

    @commands.command(name="ruleta")
    async def cmd_ruleta(self, ctx):
        premios = [
            "¡Premio! Te ganas un pase VIP virtual para primera fila de la pista. 🎫🕺",
            "¡Oh no! Te has tropezado con un altavoz gigante bailando Makina. ¡A levantarse! 🔊😂",
            "¡Jackpot! Te llevas el título honorífico de Rey de la Ruta del Bakalao hoy. 👑💿",
            "¡Sigue pinchando! Te toca invitar a un Red Bull virtual al chat. ⚡🥤"
        ]
        await ctx.send(f"🎰 @{ctx.author.name} gira la ruleta... {random.choice(premios)}")

    @commands.command(name="trivia")
    async def cmd_trivia(self, ctx):
        preguntas = [
            "¿En qué año comenzó la época dorada de la Ruta del Bakalao en Valencia? (Pista: principios de los 90)",
            "¿Qué estilo de música electrónica rápida y fiestera con vocales agudas triunfaba en las campas y discotecas en 1996?",
            "¿Cuál es el BPM aproximado al que suele correr un buen tema de Makina o Hard Dance?"
        ]
        await ctx.send(f"❓ **TRIVIA CLUBBER para @{ctx.author.name}:** {random.choice(preguntas)} ¡Responde en el chat!")


# --- SERVIDOR HTTP PARA RAILWAY ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot de Twitch Remember con IA y Minijuegos activo! 🎧".encode("utf-8"))

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"Servidor HTTP corriendo en el puerto {port}")
    server.serve_forever()


# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    hilo_web = threading.Thread(target=run_http_server, daemon=True)
    hilo_web.start()

    bot = Bot()
    bot.run()
