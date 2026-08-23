import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from twitchio.ext import commands
from google import genai
from google.genai import types

# --- CREDENCIALES Y CONFIGURACIÓN ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
TWITCH_TOKEN = os.environ.get("TMI_TOKEN") or os.environ.get("TWITCH_TOKEN")
TWITCH_CHANNEL = os.environ.get("CHANNEL") or os.environ.get("TWITCH_CANAL")

print(f"🔧 [INICIO] Canal configurado: {TWITCH_CHANNEL}")
print(f"🔧 [INICIO] Token presente: {'Sí' if TWITCH_TOKEN else 'NO'}")
print(f"🔧 [INICIO] Gemini Key presente: {'Sí' if GEMINI_API_KEY else 'NO'}")

# Inicializar cliente de Google GenAI
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- PROMPT HUMANO Y NATURAL ---
SYSTEM_INSTRUCTION = """
Eres un colega más en el chat de Twitch del canal de música Remember y Makina de jonasRDB. 
Hablas exactamente como un humano streamer o colega fiestero, de forma súper natural, cercana y espontánea.

REGLAS DE COMPORTAMIENTO:
- Cero formalidades. Nada de "Hola usuario", "Entendido" o respuestas de inteligencia artificial. Habla de tú, usa expresiones reales de España ("buf", "madre mía", "menudo pepino", "qué pasada", "vaya temazo").
- Sé breve (máximo 1 o 2 frases cortas), porque estás en un chat en directo y la gente lee rápido.
- Comenta la música, vacila un poco de buen rollo, tira Emojis de discoteca de vez en cuando (🎹, 🔥, 🚀, 🔊) pero sin recargar.
- Si te saludan, saluda normal. Si comentan un tema, reacciona como si estuvieras escuchándolo en primera fila de la discoteca.
"""

def responder_con_ia(mensaje_usuario, nombre_usuario="Viewer"):
    if not gemini_client:
        return f"@{nombre_usuario} ¡A tope con la sesión! 🚀"
    try:
        modelo = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Usamos una sesión de chat para evitar avisos de función automática y estilizar la respuesta
        chat = gemini_client.chats.create(
            model=modelo,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=80,
                temperature=0.9
            )
        )
        
        response = chat.send_message(f"El usuario {nombre_usuario} dice en el chat: '{mensaje_usuario}'")
        
        if response and response.text:
            texto_limpio = " ".join(response.text.strip().splitlines())
            if f"@{nombre_usuario}" not in texto_limpio and nombre_usuario.lower() != "viewer":
                texto_limpio = f"@{nombre_usuario} {texto_limpio}"
            return texto_limpio
            
        return f"@{nombre_usuario} ¡Buf, menuda locura de tema! 🔥"
    except Exception as e:
        print(f"❌ [IA EXCEPCIÓN]: {str(e)}")
        return f"@{nombre_usuario} ¡A tope con la música! 🚀"

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            prefix="!",
            initial_channels=[TWITCH_CHANNEL]
        )

    async def event_ready(self):
        print(f"✅ [TWITCH] ¡Bot interactivo conectado con éxito al canal: {TWITCH_CHANNEL}!")

    async def event_message(self, message):
        if message.echo:
            return

        autor = message.author.name if message.author else "Viewer"
        contenido = message.content

        if autor.lower() == self.nick.lower():
            return

        print(f"💬 [CHAT CAPTURADO] {autor}: {contenido}")
        await self.handle_commands(message)

        if contenido.startswith("!"):
            return

        # Si no es un comando, la IA responde conversando de forma humana
        respuesta_ia = responder_con_ia(contenido, autor)
        if respuesta_ia:
            try:
                await message.channel.send(respuesta_ia)
                print(f"🚀 [ENVIADO A TWITCH]: {respuesta_ia}")
            except Exception as e:
                print(f"❌ [ERROR AL ENVIAR]: {e}")

    # --- COMANDOS Y MINIJUEGOS INTERACTIVOS ---

    @commands.command(name="temazo")
    async def cmd_temazo(self, ctx):
        frases = [
            f"@{ctx.author.name} ¡MENUDO HIMNO DE LA RUTA! 🎹🔥 ¡Las manos arriba!",
            f"@{ctx.author.name} Subiendo los sub-bajos al 200%. ¡Esto es Remember del bueno! 🎧✨",
            f"@{ctx.author.name} ¡Vaya melodía épica! Esto en Spook o Central reventaba. 🙌🚀"
        ]
        await ctx.send(random.choice(frases))

    @commands.command(name="energia")
    async def cmd_energia(self, ctx):
        nivel = random.randint(85, 100)
        await ctx.send(f"⚡ @{ctx.author.name} ¡El medidor de energía del chat marca un **{nivel}%**! 🔥🎛️")

    @commands.command(name="ruleta")
    async def cmd_ruleta(self, ctx):
        premios = [
            "¡Premio! Te ganas un pase VIP virtual para primera fila de la pista. 🎫🕺",
            "¡Oh no! Te has tropezado con un altavoz gigante bailando Makina. 🔊😂",
            "¡Jackpot! Te llevas el título honorífico de Rey de la Ruta del Bakalao hoy. 👑💿",
            "¡Sigue pinchando! Te toca invitar a un Red Bull virtual al chat. ⚡🥤"
        ]
        await ctx.send(f"🎰 @{ctx.author.name} gira la ruleta... {random.choice(premios)}")

    @commands.command(name="trivia")
    async def cmd_trivia(self, ctx):
        preguntas = [
            "¿En qué década comenzó la época dorada de la música Makina y el Remember? (Pista: ¡los 90!)",
            "¿Qué estilo de música electrónica rápida y con vocales agudas triunfaba en las discotecas valencianas?",
            "¿A cuántos BPMs suele latir un buen tema cañero de Hard Dance?"
        ]
        await ctx.send(f"❓ **TRIVIA CLUBBER para @{ctx.author.name}:** {random.choice(preguntas)}")

    @commands.command(name="comandos")
    async def cmd_comandos(self, ctx):
        await ctx.send(f"📋 @{ctx.author.name} Comandos disponibles: !temazo, !energia, !ruleta, !trivia, !comandos. ¡Y habla normal por el chat para charlar con la IA!")

# --- SERVIDOR HTTP PARA MANTENER ACTIVO RAILWAY ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot de Twitch Remember interactivo activo! 🎧".encode("utf-8"))

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

if __name__ == "__main__":
    hilo_web = threading.Thread(target=run_http_server, daemon=True)
    hilo_web.start()

    if TWITCH_TOKEN and TWITCH_CHANNEL:
        bot = Bot()
        bot.run()
    else:
        print("❌ [ERROR CRÍTICO]: Faltan variables de Twitch (TMI_TOKEN o CHANNEL).")
        import time
        while True:
            time.sleep(3600)
