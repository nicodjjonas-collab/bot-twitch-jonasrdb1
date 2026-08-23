import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from twitchio.ext import commands
from google import genai
from google.genai import types

# --- CREDENCIALES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
TWITCH_TOKEN = os.environ.get("TMI_TOKEN")
TWITCH_CHANNEL = os.environ.get("CHANNEL")

print(f"🔧 [INICIO] Canal configurado: {TWITCH_CHANNEL}")
print(f"🔧 [INICIO] Token presente: {'Sí' if TWITCH_TOKEN else 'NO'}")
print(f"🔧 [INICIO] Gemini Key presente: {'Sí' if GEMINI_API_KEY else 'NO'}")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_INSTRUCTION = """
Eres el DJ virtual y copiloto IA oficial del canal de Twitch de música Remember, Makina, Hard Dance y Eurodance. 
Anima el chat, comenta los temazos y habla con jerga fiestera de los 90 y 2000 (¡A tope!, ¡Temazo!, ¡Vivan los 90!). 
Sé breve, divertido y natural en tus respuestas.
"""

def responder_con_ia(mensaje_usuario, nombre_usuario="Viewer"):
    if not gemini_client:
        print("❌ [IA] Cliente de Gemini no inicializado.")
        return "¡A tope con la sesión! 🚀"
    try:
        print(f"🤖 [IA] Consultando para {nombre_usuario}: {mensaje_usuario}")
        
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"{nombre_usuario} dice en el chat: {mensaje_usuario}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=150,
                temperature=0.7
            )
        )
        
        if response and response.text:
            texto = " ".join(response.text.strip().splitlines())
            print(f"✅ [IA RESPUESTA]: {texto}")
            return texto
            
        print("⚠️ [IA] Respuesta vacía de la API.")
        return "¡Menudo ambientazo tenemos por el chat! 🎧🔥"
        
    except Exception as e:
        print(f"❌ [IA ERROR CRÍTICO]: {e}")
        return "¡A tope con la música! 🚀"


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            prefix=os.environ.get("BOT_PREFIX", "!"),
            initial_channels=[TWITCH_CHANNEL]
        )

    async def event_ready(self):
        print(f"✅ [TWITCH] ¡Bot conectado con éxito como {self.nick}! Canal: {self.initial_channels}")

    async def event_message(self, message):
        # Ignorar mensajes del propio bot
        if message.echo:
            return

        autor = message.author.name if message.author else "Viewer"
        contenido = message.content

        if autor.lower() == self.nick.lower():
            return

        print(f"💬 [CHAT CAPTURADO] {autor}: {contenido}")

        # Procesar comandos si los hay
        await self.handle_commands(message)

        if contenido.startswith("!"):
            return

        # Llamar a la IA si es un mensaje normal de chat
        respuesta_ia = responder_con_ia(contenido, autor)
        if respuesta_ia:
            try:
                await message.channel.send(respuesta_ia)
                print(f"🚀 [ENVIADO A TWITCH]: {respuesta_ia}")
            except Exception as e:
                print(f"❌ [ERROR AL ENVIAR A TWITCH]: {e}")

    @commands.command(name="temazo")
    async def cmd_temazo(self, ctx):
        await ctx.send(f"@{ctx.author.name} ¡MENUDO HIMNO DE LA RUTA! 🎹🔥 ¡A bailar!")

    @commands.command(name="energia")
    async def cmd_energia(self, ctx):
        nivel = random.randint(85, 100)
        await ctx.send(f"⚡ @{ctx.author.name} ¡El nivel de energía está al **{nivel}%**! 🔥🎛️")


# --- SERVIDOR HTTP PARA RAILWAY ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot de Twitch Remember con IA activo! 🎧".encode("utf-8"))

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"🌐 [WEB] Servidor HTTP corriendo en el puerto {port}")
    server.serve_forever()


if __name__ == "__main__":
    # Iniciar servidor HTTP en segundo plano para Railway
    hilo_web = threading.Thread(target=run_http_server, daemon=True)
    hilo_web.start()

    if TWITCH_TOKEN and TWITCH_CHANNEL:
        print("🚀 [INICIO] Arrancando el bot de Twitch...")
        bot = Bot()
        bot.run()
    else:
        print("❌ [ERROR CRÍTICO]: Faltan variables de entorno de Twitch (TMI_TOKEN o CHANNEL).")
        import time
        while True:
            time.sleep(3600)
