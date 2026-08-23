import os
import random
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from twitchio import Client
from google import genai

# --- CONFIGURACIÓN DE CREDENCIALES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
TWITCH_TOKEN = os.environ.get("TMI_TOKEN")
TWITCH_CHANNEL = os.environ.get("CHANNEL")

print(f"🔧 [CONFIG] Canal configurado: {TWITCH_CHANNEL}")
print(f"🔧 [CONFIG] Token presente: {'Sí' if TWITCH_TOKEN else 'NO'}")
print(f"🔧 [CONFIG] Gemini API Key presente: {'Sí' if GEMINI_API_KEY else 'NO'}")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_PROMPT = """
Eres el Copiloto IA y DJ virtual oficial del canal de Twitch de música Remember, Makina, Hard Dance, Eurodance y Tech House. 
Tu objetivo es animar el chat, comentar los temazos que suenan, interactuar con los viewers y dar ambiente de discoteca de los 90 y 2000.
Sé cercano, divertido, usa jerga electrónica y expresión fiestera (¡A tope!, ¡Vivan los 90!, ¡Temazo!).
Responde siempre de forma natural, amigable y participativa a lo que digan en el chat.
"""

def responder_con_ia(mensaje_usuario, nombre_usuario="Viewer"):
    if not gemini_client:
        return "¡A tope con la sesión! 🚀"
    try:
        modelo_actual = "gemini-2.5-flash"
        prompt_completo = f"{SYSTEM_PROMPT}\n\n{nombre_usuario} dice: {mensaje_usuario}"
        
        respuesta = gemini_client.models.generate_content(
            model=modelo_actual,
            contents=prompt_completo
        )
        
        if respuesta and respuesta.text:
            return " ".join(respuesta.text.strip().splitlines())
        
        return "¡Qué pasa! ¡Menudo ambientazo tenemos por el chat! 🎧🔥"
    except Exception as e:
        print(f"❌ [IA ERROR]: {e}")
        return "¡A tope con la sesión! 🚀"


# --- CLIENTE NATIVO DE TWITCHIO (MÁS ESTABLE) ---
class BotTwitch(Client):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            nick=TWITCH_CHANNEL,
            prefix="!",
            initial_channels=[TWITCH_CHANNEL]
        )

    async def event_ready(self):
        print(f"✅ ¡BOT CONECTADO EXITOSAMENTE COMO: {self.nick}! Canales: {self.initial_channels}")

    async def event_message(self, message):
        if message.echo:
            return

        autor = message.author.name if message.author else "Viewer"
        contenido = message.content
        
        # Evitar responderse a sí mismo
        if autor.lower() == self.nick.lower():
            return

        print(f"💬 [CHAT] {autor}: {contenido}")

        # Comandos básicos manuales
        if contenido.lower() == "!temazo":
            await message.channel.send(f"@{autor} ¡MENUDO HIMNO DE LA RUTA! 🎹🔥 ¡A bailar se ha dicho!")
            return
        elif contenido.lower() == "!energia":
            nivel = random.randint(85, 100)
            await message.channel.send(f"⚡ @{autor} ¡El nivel de energía del chat está al **{nivel}%**! 🔥🎛️")
            return

        # Si no es comando, responde la IA
        respuesta_ia = responder_con_ia(contenido, autor)
        if respuesta_ia:
            try:
                await message.channel.send(respuesta_ia)
                print(f"🤖 [IA ENVIADA]: {respuesta_ia}")
            except Exception as e:
                print(f"❌ [ERROR AL ENVIAR A TWITCH]: {e}")


# --- SERVIDOR HTTP PARA RAILWAY ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot de Twitch Remember activo! 🎧".encode("utf-8"))

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()


if __name__ == "__main__":
    hilo_web = threading.Thread(target=run_http_server, daemon=True)
    hilo_web.start()

    if TWITCH_TOKEN and TWITCH_CHANNEL:
        bot = BotTwitch()
        bot.run()
    else:
        print("❌ [ERROR CRÍTICO]: Faltan TMI_TOKEN o CHANNEL en las variables de entorno.")
        import time
        while True:
            time.sleep(3600)
