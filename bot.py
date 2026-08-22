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

print(f"[INIT] Arrancando bot asíncrono para el canal: {CANAL}")

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
        
        self.archivo_comandos = "comandos_custom.json"
        self.comandos_custom = self.cargar_comandos_custom()

        # Minijuegos clásicos y arcade
        self.ahorcado_activo = False
        self.ahorcado_palabra = ""
        self.ahorcado_adivinadas = set()
        self.ahorcado_intentos = 6
        self.ttt_activo = False
        self.ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        
        self.pelea_activa = False
        self.peleador_1 = None
        self.peleador_2 = None
        self.vida_p1 = 100
        self.vida_p2 = 100
        self.turno_pelea = None

        self.invasion_activa = False
        self.alien_vida = 100
        
        self.actualizar_txt_obs("🎮 Arcade Inactivo - ¡Escribe !invasion o !pelea!")

    def actualizar_txt_obs(self, texto):
        try:
            with open("estado_juego.txt", "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            print(f"Error al escribir estado_juego.txt: {e}")

    def cargar_comandos_custom(self):
        if os.path.exists(self.archivo_comandos):
            try:
                with open(self.archivo_comandos, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar comandos custom: {e}")
        return {}

    def guardar_comandos_custom(self):
        try:
            with open(self.archivo_comandos, 'w', encoding='utf-8') as f:
                json.dump(self.comandos_custom, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar comandos custom: {e}")

    async def event_ready(self):
        print(f'=== ¡BOT CONECTADO Y ESCUCHANDO EN EL CANAL: {CANAL} ===')
        asyncio.create_task(self.bucle_autonomo_chat())

    async def event_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return  
        print(f"[ERROR COMANDO] {error}")

    async def event_message(self, message):
        print(f"[CHAT] {message.author.name if message.author else 'Sistema'}: {message.content}")
        if message.echo:
            return

        self.ultimo_mensaje = time.time()
        
        self.ultimos_mensajes_chat.append(f"{message.author.name}: {message.content}")
        if len(self.ultimos_mensajes_chat) > 15:
            self.ultimos_mensajes_chat.pop(0)

        content = message.content.strip()
        
        # Comprobar mención al bot (@sesionesoldschool)
        mencion_canal = f"@{BOT_NICK}".lower()
        if mencion_canal in content.lower():
            if ai_client:
                try:
                    prompt_usuario = content.lower().replace(mencion_canal, "").strip()
                    if not prompt_usuario:
                        prompt_usuario = "¡Hola tío!"
                        
                    contexto_actual = " | ".join(self.ultimos_mensajes_chat[-8:])
                    prompt_final = f"Historial del chat: [{contexto_actual}]\n\n{message.author.name} te menciona diciendo: '{prompt_usuario}'. Resóndele de forma natural."
                    
                    print(f"[DEBUG GEMINI] Enviando chat a Gemini: {prompt_usuario}")
                    
                    # Corrección: Uso de chat sessions recomendado por la SDK oficial
                    chat_session = ai_client.chats.create(
                        model='gemini-2.5-flash',
                        config={
                            'system_instruction': (
                                f"Eres una persona real, un colega más y viewer habitual en el canal de Twitch de {CANAL}. "
                                "Hablas de tú, con total naturalidad, jerga coloquial de España (tío, mola, brutal, crack, etc.). "
                                "PROHIBIDO sonar como asistente o bot. Breve y directo (máx 250 caracteres)."
                            ),
                        }
                    )
                    response = chat_session.send_message(prompt_final)
                    
                    texto_respuesta = response.text if response and response.text else "¡Qué pasa tío! Totalmente de acuerdo. 🔥"
                    print(f"[DEBUG GEMINI] Respuesta recibida: {texto_respuesta}")
                    await message.channel.send(f"@{message.author.name} {texto_respuesta.strip()[:350]}")
                    
                except Exception as e:
                    print(f"[ERROR CRÍTICO GEMINI MENCION]: {e}")
                    await message.channel.send(f"@{message.author.name} ¡Vaya temazo está sonando! 🎧🔥")
            else:
                print("[AVISO] Alguien mencionó al bot pero ai_client es None (falta clave de Gemini).")
                await message.channel.send(f"@{message.author.name} ¡Ey! (La IA está desconectada ahora mismo)")

        # Comprobar comandos custom
        if content.startswith('!'):
            partes = content[1:].split(' ', 1)
            nombre_cmd = partes[0].lower()
            if nombre_cmd in self.comandos_custom:
                await message.channel.send(self.comandos_custom[nombre_cmd])
                return

        await self.handle_commands(message)

    async def bucle_autonomo_chat(self):
        asyncio.create_task(self._bucle_real())

    async def _bucle_real(self):
        await asyncio.sleep(20)
        while True:
            try:
                await asyncio.sleep(120)
                if time.time() - self.ultimo_mensaje > 180:
                    canal_obj = self.get_channel(CANAL)
                    if canal_obj:
                        if ai_client:
                            chat_session = ai_client.chats.create(
                                model='gemini-2.5-flash',
                                config={
                                    'system_instruction': "Eres un colega más en el chat de Twitch. Escribe corto, súper natural, como si estuvieras viendo el directo desde el sofá.",
                                }
                            )
                            response = chat_session.send_message("El chat lleva un rato tranquilo. Suelta un comentario guapo sobre la música Remember o la sesión para romper el hielo.")
                            msg = (response.text if response and response.text else "¡Menuda sesión nos estamos pegando!").replace('\n', ' ')
                        else:
                            msg = f"¡Vaya temazos de sesión familia! {random.choice(self.emotes_twitch)}"
                        await canal_obj.send(f"{msg} {random.choice(self.emotes_twitch)}")
                        self.ultimo_mensaje = time.time()
            except Exception as e:
                print(f"Error bucle autónomo: {e}")

    # ==================== COMANDOS GENERALES ====================

    @commands.command(name='comandos')
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(f"🤖 Habla conmigo usando @{BOT_NICK} | 🕹️ Arcade: !pelea @user, !invasion, !3enraya, !ahorcado | 🎲 Extras: !festero, !amor, !ruleta")

    @commands.command(name='festero')
    async def festero(self, ctx: commands.Context):
        await ctx.send(f"🎉 @{ctx.author.name} tiene un {random.randint(0,100)}% de ganas de fiesta hoy. 🔥")

    @commands.command(name='normas')
    async def cmd_normas(self, ctx: commands.Context):
        await ctx.send("⚠️ NORMAS: Respeto absoluto. ¡A disfrutar del Remember y el Hard Dance! 🎧")

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
