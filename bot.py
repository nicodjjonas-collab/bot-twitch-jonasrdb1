import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from twitchio import Client
from google import genai
from google.genai import types

# --- CREDENCIALES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
TWITCH_TOKEN = os.environ.get("TMI_TOKEN")
TWITCH_CHANNEL = os.environ.get("CHANNEL")

print(f"🔧 [CONFIG] Canal: {TWITCH_CHANNEL} | Token: {'OK' if TWITCH_TOKEN else 'FALTA'} | Gemini: {'OK' if GEMINI_API_KEY else 'FALTA'}")

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
        
        # Llamada estructurada correcta para google-genai
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


class BotTwitch(Client):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            nick=TWITCH_CHANNEL,
            prefix="!",
            initial_channels=[TWITCH_CHANNEL]
        )

    async def event_ready(self):
        print(f"✅ ¡BOT CONECTADO CORRECTAMENTE A TWITCH COMO: {self.nick}!")

    async def event_message(self, message):
        if message.echo:
            return

        autor = message.author.name if message.author else "Viewer"
        contenido = message.content

        # Evitar bucles si el bot habla
        if autor.lower() == self.nick.lower():
            return

        print(f"💬 [CHAT RECIBIDO] {autor}: {contenido}")

        # Comandos rápidos
        if contenido.lower() == "!temazo":
            await message.channel.send(f"@{autor} ¡MENUDO HIMNO DE LA RUTA! 🎹🔥 ¡A bailar!")
            return
        elif contenido.lower() == "!energia":
            nivel = random.randint(85, 100)
            await message.channel.send(f"⚡ @{autor} ¡El nivel de energía está al **{nivel}%**! 🔥🎛️")
            return

        # Si no es comando, procesa la IA
        respuesta_ia = responder_con_ia(contenido, autor)
        if respuesta_ia:
            try:
                await message.channel.send(respuesta_ia)
                print(f"🤖 [ENVIADO A TWITCH]: {respuesta_ia}")
            except Exception as e:
                print(f"❌ [ERROR AL ENVIAR A TWITCH]: {e}")


# Servidor web obligatorio para Railway
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot de Twitch Remember con IA activo! 🎧".encode("utf-8"))

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
        print("❌ Faltan credenciales de Twitch en las variables de entorno.")
        import time
        while True:
            time.sleep(3600)
