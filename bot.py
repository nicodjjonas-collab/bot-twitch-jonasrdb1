import os
import random
import time
import asyncio
import json
from urllib.request import Request, urlopen
import twitchio
from twitchio.ext import commands

TOKEN = os.environ.get('TWITCH_TOKEN')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
BOT_NAME = os.environ.get('TWITCH_BOT', 'sesionesoldschool')
GROQ_KEY = os.environ.get('GROQ_KEY', '')

trivia_on = False
trivia_r = ""
bpm_n = None

ttt_activo = False
ttt_x = ""
ttt_o = ""
ttt_turno = "X"
ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

ahorcado_activo = False
ahorcado_palabra = ""
ahorcado_adivinadas = set()
ahorcado_intentos = 6

num_activo = False
num_secreto = 0

vf_activo = False
vf_pregunta = ""
vf_respuesta = ""

ultimo_mensaje_chat = time.time()
mensajes_automaticos_enviados = 0
MAX_MENSAJES_SILENCIO = 5

emotes_canal = [
    "Kappa", "PogChamp", "LUL", "OMEGALUL", "KEKW", "monkaS", "Sadge",
    "PepeHands", "FeelsGoodMan", "FeelsBadMan", "TriHard", "ResidentSleeper",
    "BibleThump", "Kreygasm", "NotLikeThis", "DansGame", "WutFace", "PJSalt",
    "FailFish", "SwiftRage", "CoolStoryBob", "VoHiYo", "WholeWheat", "BabyRage"
]
emotes_personalizados = []

temas_ia = [
    "¿Qué os parece la sesión de hoy? ¿Está buena la música?",
    "¿De dónde sois todos? ¡Quiero saber de qué parte del mundo me escucháis!",
    "¿Cuál es vuestro género favorito? ¿Techno, house, makina?",
    "¿Alguien ha ido a algún rave últimamente? ¡Contadme vuestra experiencia!",
    "¿Vinilo o digital? ¿Qué preferís los DJs de hoy en día?",
    "¿Cuál fue el mejor DJ que habéis visto en vivo?",
    "¿Recordáis la época dorada del Remember? ¡Qué tiempos aquellos!",
    "¿Cuál es vuestro BPM favorito para bailar sin parar?",
    "¿Qué os parece si hacemos una trivia musical? ¡Escribid !trivia!",
    "¿Quién se anima a un juego de !3enraya? ¡Necesito rival!",
    "¿Techno duro o melódico? ¡Quiero saber vuestra opinión!",
    "¿Alguien tiene algún set recomendado para esta noche?"
]

palabras_ahorcado = [
    "techno", "house", "trance", "vinilo", "mezcla", "bpm", "rave",
    "fiesta", "bass", "drop", "set", "dj", "platina", "sintetizador",
    "acido", "detroit", "ibiza", "berlin", "minimal", "progressive",
    "hardcore", "remember", "makina", "eurodance", "disco"
]

preguntas_vf = [
    ("Los Beatles se originaron en la ciudad de Liverpool.", "verdadero"),
    ("El piano estándar tiene 88 teclas.", "verdadero"),
    ("Michael Jackson es conocido mundialmente como el 'Rey del Rock'.", "falso"),
    ("El reguetón se originó principalmente en Puerto Rico.", "verdadero"),
    ("Beethoven quedó completamente sordo al final de su vida.", "verdadero"),
    ("El festival de Woodstock tuvo lugar en el año 1969.", "verdadero"),
    ("Shakira es originaria de México.", "falso"),
    ("El género Techno nació en la ciudad de Detroit, Estados Unidos.", "verdadero"),
    ("El grupo 'Daft Punk' es originario de Francia.", "verdadero")
]

retos = [
    "Pon la canción que más te haga bailar ahora mismo",
    "Di tu género favorito y por qué",
    "Cuéntanos tu mejor experiencia en un rave",
    "Nombra 3 DJs que te encanten"
]

verdades = [
    "¿Cuál es tu guilty pleasure musical?",
    "¿Alguna vez has llorado con una canción?",
    "¿Qué género no soportas?",
    "¿Techno a las 8am o house a las 4am?"
]

respuestas_bola = [
    "Definitivamente sí", "Sin duda", "Sí, totalmente",
    "Las señales apuntan a que sí", "Pregunta de nuevo más tarde",
    "Mejor no te digo ahora", "Mis fuentes dicen que no",
    "Muy dudoso...", "No cuentes con ello", "El universo dice que sí"
]


def obtener_emote_aleatorio():
    todos_emotes = emotes_canal + emotes_personalizados
    return random.choice(todos_emotes) if todos_emotes else ""


def consultar_qwen(pregunta):
    if not GROQ_KEY:
        print("[ERROR IA] GROQ_KEY no está configurada")
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        system_prompt = f"Eres {BOT_NAME}, DJ y animador del chat de JonasRDB. Eres autónomo y hablas solo para animar el chat. Responde en español, máximo 2 frases cortas, con energía rave y buen rollo. Usa emojis de música."
        
        payload = {
            "model": "qwen-2.5-32b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pregunta}
            ],
            "max_tokens": 150,
            "temperature": 0.8
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GROQ_KEY}'
        }
        req = Request(url, data=data, headers=headers, method='POST')
        
        with urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            print("[ERROR IA] Respuesta inesperada: " + str(result))
            return None
    except Exception as e:
        print("[ERROR IA] " + str(e))
        return None


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CANAL])

    async def event_ready(self):
        print('Bot conectado a #' + CANAL)
        print('Bot autónomo con Qwen IA activado (Groq)')
        print('Menciona @' + BOT_NAME + ' para hablar con la IA')
        self.loop.create_task(self.monitorear_silencio())
        self.loop.create_task(self.ia_autonoma())

    async def event_message(self, message):
        global ultimo_mensaje_chat, mensajes_automaticos_enviados
        if message.echo:
            return
        user = message.author.name
        content = message.content.strip()
        print("[" + user + "]: " + content)

        ultimo_mensaje_chat = time.time()
        mensajes_automaticos_enviados = 0

        mencion = "@" + BOT_NAME.lower()
        if mencion in content.lower():
            pregunta = content.lower().replace(mencion, "").strip()
            if len(pregunta) > 2:
                print("[IA] Procesando pregunta de " + user + ": " + pregunta)
                respuesta = consultar_qwen(pregunta)
                if respuesta:
                    emote = obtener_emote_aleatorio()
                    await message.channel.send("@" + user + " " + respuesta[:350] + (" " + emote if emote else ""))
                else:
                    if not GROQ_KEY:
                        await message.channel.send("@" + user + " La IA no está configurada. Contacta al admin.")
                    else:
                        await message.channel.send("@" + user + " Hubo un error con la IA. Intenta de nuevo.")

        if content.startswith("!"):
            await self.procesar_comando(message, user, content)

    async def monitorear_silencio(self):
        global ultimo_mensaje_chat, mensajes_automaticos_enviados
        TIEMPO_SILENCIO = 120
        while True:
            await asyncio.sleep(30)
            tiempo_sin_actividad = time.time() - ultimo_mensaje_chat
            if tiempo_sin_actividad > TIEMPO_SILENCIO and mensajes_automaticos_enviados < MAX_MENSAJES_SILENCIO:
                channel = self.get_channel(CANAL)
                if channel:
                    emote = obtener_emote_aleatorio()
                    if random.random() > 0.5 and GROQ_KEY:
                        tema = random.choice(temas_ia)
                        respuesta = consultar_qwen(tema)
                        if respuesta:
                            await channel.send(respuesta[:350] + (" " + emote if emote else ""))
                            mensajes_automaticos_enviados += 1
                    else:
                        await channel.send(random.choice(temas_ia) + (" " + emote if emote else ""))
                        mensajes_automaticos_enviados += 1

    async def ia_autonoma(self):
        TIEMPO_ENTRE_MENSAJES = 300
        while True:
            await asyncio.sleep(TIEMPO_ENTRE_MENSAJES)
            channel = self.get_channel(CANAL)
            if channel and GROQ_KEY:
                emote = obtener_emote_aleatorio()
                tema = random.choice(temas_ia)
                respuesta = consultar_qwen(tema + " (Habla de forma natural, haz una pregunta al chat para que participen)")
                if respuesta:
                    await channel.send(respuesta[:350] + (" " + emote if emote else ""))

    async def procesar_comando(self, message, user, content):
        global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
        global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
        global num_activo, num_secreto, vf_activo, vf_pregunta, vf_respuesta

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        emote = obtener_emote_aleatorio()
        sufijo = " " + emote if emote else ""

        if cmd in ["!comandos", "!ayuda", "!help"]:
            await message.channel.send('INFO: !redes, !sobre, !normas, !prime. DIVERSION: !festero, !vf, !reto, !bola, !dado, !moneda, !ppt.')
            await message.channel.send('JUEGOS: !3enraya, !ahorcado, !numero, !trivia, !ruleta, !bpm.')
        elif cmd == "!redes":
            await message.channel.send('Sigueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB')
        elif cmd == "!sobre":
            await message.channel.send('JONAS RDB // HARD DANCE. DJ alicantino desde 1994. +30 años de Hard Dance y Remember.')
        elif cmd == "!normas":
            await message.channel.send('NORMAS: 1) Lenguaje respetuoso. 2) Emotes sin ofender. 3) Criticas constructivas SI, ataques NO. TOLERANCIA CERO. ¡Disfruta!')
        elif cmd in ["!prime", "!suscri"]:
            await message.channel.send('Suscribete GRATIS con Twitch Prime! Apoya el canal sin coste extra.')
        elif cmd in ["!festero", "!fiesta", "!animado"]:
            p = random.randint(0, 100)
            if p >= 85: frase = f"¡@{user} esta al {p}% de festero! ¡A ROMPERLA!"
            elif p >= 65: frase = f"@{user} esta al {p}% de festero. ¡Sube el volumen!"
            elif p >= 45: frase = f"@{user} esta al {p}% de festero. Vas bien, ¡sigue bailando!"
            else: frase = f"@{user} esta al {p}% sin ganas... ¿Necesitas un Red Bull?"
            await message.channel.send(frase + sufijo)
        elif cmd in ["!vf", "!verdaderofalso"]:
            if vf_activo:
                await message.channel.send("Ya hay pregunta activa: " + vf_pregunta + " (Responde !v o !f)")
            else:
                vf_activo = True
                q, a = random.choice(preguntas_vf)
                vf_pregunta, vf_respuesta = q, a
                await message.channel.send("¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !f)" + sufijo)
        elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
            if not vf_activo:
                await message.channel.send("No hay pregunta activa. Inicia con !vf")
            else:
                resp = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
                if resp == vf_respuesta:
                    await message.channel.send("¡CORRECTO @" + user + "! Era " + vf_respuesta + sufijo)
                else:
                    await message.channel.send("Incorrecto @" + user + ". Era " + vf_respuesta + sufijo)
                vf_activo = False
        elif cmd in ["!3enraya", "!tictactoe"]:
            if ttt_activo:
                await message.channel.send("Ya hay partida en curso.")
            else:
                ttt_activo, ttt_x, ttt_o, ttt_turno = True, user, "", "X"
                ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                await message.channel.send("@" + user + " inicio 3 en Raya! Otro viewer escribe !unirse para jugar como O." + sufijo)
        elif cmd == "!unirse":
            if not ttt_activo or ttt_o != "" or user == ttt_x:
                await message.channel.send("No puedes unirte a esta partida.")
            else:
                ttt_o = user
                await message.channel.send("@" + ttt_o + " se unio como O. ¡@" + ttt_x + " (X), es tu turno! Escribe: !mover [1-9]" + sufijo)
        elif cmd == "!mover":
            if not ttt_activo or user not in [ttt_x, ttt_o] or (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o):
                await message.channel.send("No es tu turno o no eres parte de la partida.")
                return
            if not arg or not arg.isdigit() or not (1 <= int(arg) <= 9):
                await message.channel.send("Usa un numero del 1 al 9. Ej: !mover 5")
                return
            pos = int(arg) - 1
            if ttt_tablero[pos] in ["X", "O"]:
                await message.channel.send("Casilla ocupada.")
                return
            ttt_tablero[pos] = ttt_turno
            ganar = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
            ganador = next((ttt_tablero[a] for a, b, c in ganar if ttt_tablero[a] == ttt_tablero[b] == ttt_tablero[c]), None)
            if not ganador and all(c in ["X", "O"] for c in ttt_tablero):
                ganador = "Empate"
            
            tab = f"{ttt_tablero[0]}|{ttt_tablero[1]}|{ttt_tablero[2]} - {ttt_tablero[3]}|{ttt_tablero[4]}|{ttt_tablero[5]} - {ttt_tablero[6]}|{ttt_tablero[7]}|{ttt_tablero[8]}"
            if ganador == "Empate":
                await message.channel.send("¡Empate! Tablero: " + tab + sufijo)
                ttt_activo = False
            elif ganador:
                await message.channel.send("¡GANADOR! @" + (ttt_x if ganador == "X" else ttt_o) + "! Tablero: " + tab + sufijo)
                ttt_activo = False
            else:
                ttt_turno = "O" if ttt_turno == "X" else "X"
                await message.channel.send("Turno de " + ttt_turno + " (@" + (ttt_x if ttt_turno == "X" else ttt_o) + "). Escribe: !mover [1-9]. Tablero: " + tab + sufijo)
        elif cmd == "!ahorcado":
            if not ahorcado_activo:
                ahorcado_activo = True
                ahorcado_palabra = random.choice(palabras_ahorcado)
                ahorcado_adivinadas, ahorcado_intentos = set(), 6
                await message.channel.send("@" + user + " inicio el AHORCADO! Palabra: " + " ".join(["_" for _ in ahorcado_palabra]) + " | Escribe !letra [a-z]" + sufijo)
        elif cmd == "!letra":
            if not ahorcado_activo or not arg or len(arg) != 1 or not arg.isalpha():
                await message.channel.send("Escribe UNA letra. Ej: !letra a")
                return
            letra = arg.lower()
            if letra in ahorcado_adivinadas:
                await message.channel.send("Ya probaste '" + letra + "'")
                return
            ahorcado_adivinadas.add(letra)
            if letra in ahorcado_palabra:
                if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                    await message.channel.send("¡GANO @" + user + "! La palabra era '" + ahorcado_palabra + "'" + sufijo)
                    ahorcado_activo = False
                else:
                    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                    await message.channel.send("¡Bien! '" + letra + "' esta. Estado: " + estado + sufijo)
            else:
                ahorcado_intentos -= 1
                if ahorcado_intentos <= 0:
                    await message.channel.send("¡PERDISTE @" + user + "! Era '" + ahorcado_palabra + "'" + sufijo)
                    ahorcado_activo = False
                else:
                    await message.channel.send("'" + letra + "' NO esta. Intentos: " + str(ahorcado_intentos) + sufijo)
        elif cmd == "!numero":
            if not num_activo:
                num_activo, num_secreto = True, random.randint(1, 100)
                await message.channel.send("@" + user + " inicio 'Adivina el Numero' (1-100). Escribe: !adivinanum [numero]" + sufijo)
        elif cmd == "!adivinanum":
            if not num_activo or not arg:
                await message.channel.send("Inicia con !numero o escribe un numero.")
                return
            try:
                n = int(arg)
                if n == num_secreto:
                    await message.channel.send("¡@" + user + " ACERTO! Era " + str(num_secreto) + sufijo)
                    num_activo = False
                elif n < num_secreto:
                    await message.channel.send("@" + user + ": es MAS ALTO que " + str(n) + sufijo)
                else:
                    await message.channel.send("@" + user + ": es MAS BAJO que " + str(n) + sufijo)
            except:
                await message.channel.send("Escribe un numero valido.")
        elif cmd in ["!ppt", "!piedra"]:
            opciones = ["piedra", "papel", "tijera"]
            if not arg or arg.lower() not in opciones:
                await message.channel.send("Elige: piedra, papel o tijera. Ej: !ppt piedra")
                return
            eleccion_user, eleccion_bot = arg.lower(), random.choice(opciones)
            if eleccion_user == eleccion_bot:
                res = "Empate. Ambos " + eleccion_user + "."
            elif (eleccion_user == "piedra" and eleccion_bot == "tijera") or (eleccion_user == "papel" and eleccion_bot == "piedra") or (eleccion_user == "tijera" and eleccion_bot == "papel"):
                res = "¡@" + user + " GANA! " + eleccion_user + " vence a " + eleccion_bot + "."
            else:
                res = "¡Gana el bot! " + eleccion_bot + " vence a " + eleccion_user + "."
            await message.channel.send("@" + user + ": " + eleccion_user + " vs Bot: " + eleccion_bot + ". " + res + sufijo)
        elif cmd == "!dado":
            await message.channel.send("@" + user + " tiro el dado: " + str(random.randint(1, 6)) + sufijo)
        elif cmd == "!moneda":
            await message.channel.send("@" + user + " lanzo la moneda: " + random.choice(["CARA", "CRUZ"]) + sufijo)
        elif cmd in ["!bola", "!bola8"]:
            if not arg:
                await message.channel.send("Haz una pregunta. Ej: !bola ire a un rave?")
                return
            await message.channel.send("@" + user + ": " + random.choice(respuestas_bola) + sufijo)
        elif cmd in ["!reto", "!verdad"]:
            tipo = random.choice(["RETO", "VERDAD"])
            cont = random.choice(retos) if tipo == "RETO" else random.choice(verdades)
            await message.channel.send("@" + user + " te toca un " + tipo + ": " + cont + sufijo)
        elif cmd == "!trivia":
            if not trivia_on:
                qs = [{"p":"BPM tipico del techno?","r":"130"},{"p":"Ciudad natal del techno?","r":"detroit"},{"p":"House + techno?","r":"tech house"}]
                q = random.choice(qs)
                trivia_on, trivia_r = True, q["r"]
                await message.channel.send("TRIVIA! " + q["p"] + " (Responde: !respuesta [tu respuesta])" + sufijo)
        elif cmd == "!respuesta":
            if not trivia_on or not arg:
                await message.channel.send("Inicia con !trivia o escribe tu respuesta.")
                return
            if arg.lower().strip() == trivia_r:
                await message.channel.send("¡CORRECTO @" + user + "!" + sufijo)
                trivia_on = False
            else:
                await message.channel.send("Incorrecto @" + user + "." + sufijo)
        elif cmd == "!ruleta":
            await message.channel.send("¡Ruleta! Genero: " + random.choice(["Techno","House","Trance","Drum&Bass","Dubstep","Hardstyle","Remember"]) + ". ¡Pon una cancion!" + sufijo)
        elif cmd == "!bpm":
            bpm_n = random.randint(120, 174)
            await message.channel.send("Adivina el BPM (120-174): !adivinarbpm [numero]" + sufijo)
        elif cmd == "!adivinarbpm":
            if bpm_n is None or not arg:
                await message.channel.send("Inicia con !bpm o escribe un numero.")
                return
            try:
                n = int(arg)
                if n == bpm_n:
                    await message.channel.send("¡EXACTO @" + user + "! Era " + str(bpm_n) + " BPM." + sufijo)
                    bpm_n = None
                elif abs(n - bpm_n) <= 5:
                    await message.channel.send("¡Muy cerca @" + user + "! A " + str(abs(n-bpm_n)) + " BPM." + sufijo)
                else:
                    await message.channel.send("Frio @" + user + "." + sufijo)
            except:
                await message.channel.send("Escribe un numero valido.")

bot = Bot()

if __name__ == '__main__':
    bot.run()
