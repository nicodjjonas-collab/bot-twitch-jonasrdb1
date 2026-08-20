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
GEMINI_KEY = os.environ.get('GEMINI_KEY', '')

# Variables de juegos
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

# Control de actividad del chat
ultimo_mensaje_chat = time.time()
mensajes_automaticos_enviados = 0
MAX_MENSAJES_SILENCIO = 5

# EMOTES DEL CANAL - Añade aquí los emotes de tu canal
# Puedes usar emotes por nombre (si son globales) o por ID numérica (emotes del canal)
emotes_canal = [
    "Kappa", "PogChamp", "LUL", "OMEGALUL", "KEKW", "monkaS", "Sadge", 
    "PepeHands", "FeelsGoodMan", "FeelsBadMan", "TriHard", "ResidentSleeper",
    "BibleThump", "Kreygasm", "NotLikeThis", "DansGame", "WutFace", "PJSalt",
    "FailFish", "SwiftRage", "ArsonNoSexy", "CoolStoryBob", "ImGlitch",
    "RitzMitz", "TheRinger", "VoHiYo", "WholeWheat", "BabyRage"
]

# Si tienes emotes personalizados del canal, añade sus IDs aquí (ejemplo: "emote12345")
# emotes_personalizados = ["emote12345", "emote67890"]
emotes_personalizados = []

# Temas para que la IA inicie conversaciones
temas_ia = [
    "¿Qué os parece la sesión de hoy? ¿Está buena la música?",
    "¿De dónde sois todos? ¡Quiero saber de qué parte del mundo me escucháis!",
    "¿Cuál es vuestro género favorito? ¿Techno, house, makina?",
    "¿Alguien ha ido a algún rave últimamente? ¡Contadme vuestra experiencia!",
    "¿Vinilo o digital? ¿Qué preferís los DJs de hoy en día?",
    "¿Cuál fue el mejor DJ que habéis visto en vivo?",
    "¿Qué os parece el estado de la música electrónica actual?",
    "¿Recordáis la época dorada del Remember? ¡Qué tiempos aquellos!",
    "¿Cuál es vuestro BPM favorito para bailar sin parar?",
    "¿Alguien colecciona vinilos? ¿Cuántos tenéis?",
    "¿Qué os parece si hacemos una trivia musical? ¡Escribid !trivia!",
    "¿Quién se anima a un juego de !3enraya? ¡Necesito rival!",
    "¿Alguien sabe qué es el BPM? ¡Preguntadme lo que queráis sobre música!",
    "¿Qué DJ os gustaría que pinchase en la próxima sesión?",
    "¿Cuál es vuestra canción favorita de los 90s?",
    "¿Techno duro o melódico? ¡Quiero saber vuestra opinión!",
    "¿Alguien tiene algún set recomendado para esta noche?",
    "¿Qué os parece la energía del chat? ¡Vamos a animar esto!",
    "¿Cuál fue el último track que os hizo bailar sin parar?",
    "¿Qué género musical no soportáis? ¡Sed sinceros!"
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
    ("La guitarra eléctrica se inventó antes que la guitarra acústica.", "falso"),
    ("El festival de Woodstock tuvo lugar en el año 1969.", "verdadero"),
    ("Shakira es originaria de México.", "falso"),
    ("El saxofón está clasificado como un instrumento de viento madera.", "verdadero"),
    ("El flamenco es un género musical originario de Andalucía, España.", "verdadero"),
    ("El violín tiene 6 cuerdas.", "falso"),
    ("El rap y el hip-hop son exactamente el mismo género musical.", "falso"),
    ("David Bowie es el creador del personaje 'Ziggy Stardust'.", "verdadero"),
    ("La ópera se originó históricamente en Italia.", "verdadero"),
    ("El sintetizador Moog fue fundamental en el desarrollo de la música electrónica.", "verdadero"),
    ("El grupo 'Queen' fue fundado por Freddie Mercury y Paul McCartney.", "falso"),
    ("El género Techno nació en la ciudad de Detroit, Estados Unidos.", "verdadero"),
    ("El mariachi es un género musical tradicional de Argentina.", "falso"),
    ("El grupo 'Nirvana' es el máximo exponente del Grunge.", "verdadero"),
    ("Mozart compuso su primera sinfonía a los 8 años.", "verdadero"),
    ("El bajo eléctrico tiene normalmente 4 cuerdas.", "verdadero"),
    ("El género 'Dubstep' se caracteriza por sus bajos pesados y ritmos a medio tiempo.", "verdadero"),
    ("Elvis Presley es conocido como 'El Rey del Pop'.", "falso"),
    ("La banda 'The Rolling Stones' se formó en los años 80.", "falso"),
    ("El 'Hardstyle' es un subgénero del EDM con un BPM típico de 150.", "verdadero"),
    ("El compositor Johann Sebastian Bach era alemán.", "verdadero"),
    ("El 'Trap' musical se originó en el sur de Estados Unidos.", "verdadero"),
    ("La flauta travesera es un instrumento de viento metal.", "falso"),
    ("El álbum 'Thriller' de Michael Jackson es el más vendido de la historia.", "verdadero"),
    ("El género 'Salsa' tiene sus raíces principales en el Caribe y Nueva York.", "verdadero"),
    ("El DJ Tiesto es originario de Alemania.", "falso"),
    ("El 'Drum and Bass' se caracteriza por ritmos rápidos de breakbeat.", "verdadero"),
    ("Beethoven escribió 9 sinfonías.", "verdadero"),
    ("El 'Punk' rock se caracteriza por canciones largas y solos de guitarra complejos.", "falso"),
    ("El grupo 'Daft Punk' es originario de Francia.", "verdadero")
]

retos = [
    "Pon la canción que más te haga bailar ahora mismo",
    "Di tu género favorito y por qué",
    "Cuéntanos tu mejor experiencia en un rave",
    "Nombra 3 DJs que te encanten",
    "¿Vinilo o digital? Defiende tu postura",
    "Describe tu sesión perfecta en 3 palabras",
    "¿Cuál fue el último track que te voló la cabeza?",
    "Recomienda un set para esta noche"
]

verdades = [
    "¿Cuál es tu guilty pleasure musical?",
    "¿Alguna vez has llorado con una canción?",
    "¿Qué género no soportas?",
    "¿Cuál es el track más raro que tienes?",
    "¿Techno a las 8am o house a las 4am?",
    "¿Tu momento más épico en una pista?",
    "¿Qué DJ te hubiera gustado ver en vivo?",
    "¿Vinilo más caro que has comprado?"
]

respuestas_bola = [
    "Definitivamente sí", "Sin duda", "Sí, totalmente",
    "Las señales apuntan a que sí", "Pregunta de nuevo más tarde",
    "Mejor no te digo ahora", "Mis fuentes dicen que no",
    "Muy dudoso...", "No cuentes con ello", "El universo dice que sí"
]


def obtener_emote_aleatorio():
    """Obtiene un emote aleatorio (global o personalizado)"""
    todos_emotes = emotes_canal + emotes_personalizados
    if todos_emotes:
        return random.choice(todos_emotes)
    return ""


def consultar_gemini(pregunta):
    """Consulta a la API de Gemini"""
    if not GEMINI_KEY:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_KEY
        prompt = "Eres " + BOT_NAME + ", DJ y animador del chat de JonasRDB. Eres autónomo y hablas solo para animar el chat. Responde en español, máximo 2 frases cortas, con energía rave y buen rollo. Pregunta o tema: " + pregunta
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 150, "temperature": 0.8}
        }
        data = json.dumps(payload).encode('utf-8')
        req = Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print("[ERROR IA] " + str(e))
        return None


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CANAL])
    
    async def event_ready(self):
        print('Bot conectado a #' + CANAL)
        print('Bot autónomo con IA activado')
        print('Emotes disponibles: ' + str(len(emotes_canal) + len(emotes_personalizados)))
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
        
        # Actualizar timestamp de actividad
        ultimo_mensaje_chat = time.time()
        mensajes_automaticos_enviados = 0
        
        # Detectar si mencionan al bot para responder con IA
        mencion = "@" + BOT_NAME.lower()
        if mencion in content.lower():
            pregunta = content.lower().replace(mencion, "").strip()
            if len(pregunta) > 2:
                print("[IA] Procesando pregunta de " + user + ": " + pregunta)
                respuesta = consultar_gemini(pregunta)
                if respuesta:
                    emote = obtener_emote_aleatorio()
                    if emote:
                        await message.channel.send("@" + user + " " + respuesta[:350] + " " + emote)
                    else:
                        await message.channel.send("@" + user + " " + respuesta[:400])
                else:
                    await message.channel.send("@" + user + " La IA no está disponible ahora.")
        
        # Procesar comandos
        if content.startswith("!"):
            await self.procesar_comando(message, user, content)
    
    async def monitorear_silencio(self):
        """Monitorea el chat y envía mensajes cuando hay silencio"""
        global ultimo_mensaje_chat, mensajes_automaticos_enviados
        TIEMPO_SILENCIO = 120  # 2 minutos de silencio
        
        while True:
            await asyncio.sleep(30)
            
            tiempo_sin_actividad = time.time() - ultimo_mensaje_chat
            
            if tiempo_sin_actividad > TIEMPO_SILENCIO and mensajes_automaticos_enviados < MAX_MENSAJES_SILENCIO:
                channel = self.get_channel(CANAL)
                if channel:
                    emote = obtener_emote_aleatorio()
                    
                    # 50% probabilidad de usar IA, 50% frases predefinidas
                    if random.random() > 0.5 and GEMINI_KEY:
                        tema = random.choice(temas_ia)
                        print("[IA AUTÓNOMA] Generando respuesta sobre: " + tema)
                        respuesta = consultar_gemini(tema)
                        if respuesta:
                            if emote:
                                await channel.send(respuesta[:350] + " " + emote)
                            else:
                                await channel.send(respuesta[:400])
                            mensajes_automaticos_enviados += 1
                            print("[IA AUTÓNOMA] Mensaje enviado (" + str(mensajes_automaticos_enviados) + "/" + str(MAX_MENSAJES_SILENCIO) + ")")
                    else:
                        frase = random.choice(temas_ia)
                        if emote:
                            await channel.send(frase + " " + emote)
                        else:
                            await channel.send(frase)
                        mensajes_automaticos_enviados += 1
                        print("[SILENCIO] Frase enviada (" + str(mensajes_automaticos_enviados) + "/" + str(MAX_MENSAJES_SILENCIO) + ")")
    
    async def ia_autonoma(self):
        """La IA habla sola cada cierto tiempo para mantener el chat activo"""
        TIEMPO_ENTRE_MENSAJES = 300  # 5 minutos entre mensajes automáticos de la IA
        
        while True:
            await asyncio.sleep(TIEMPO_ENTRE_MENSAJES)
            
            channel = self.get_channel(CANAL)
            if channel and GEMINI_KEY:
                emote = obtener_emote_aleatorio()
                tema = random.choice(temas_ia)
                print("[IA AUTÓNOMA] Iniciando conversación sobre: " + tema)
                respuesta = consultar_gemini(tema + " (Habla de forma natural, haz una pregunta al chat para que participen)")
                if respuesta:
                    if emote:
                        await channel.send(respuesta[:350] + " " + emote)
                    else:
                        await channel.send(respuesta[:400])
                    print("[IA AUTÓNOMA] Conversación iniciada")
    
    async def procesar_comando(self, message, user, content):
        global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
        global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
        global num_activo, num_secreto
        global vf_activo, vf_pregunta, vf_respuesta

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ["!comandos", "!ayuda", "!help"]:
            await message.channel.send('INFO: !redes, !sobre, !normas, !prime. DIVERSION: !festero, !vf, !reto, !bola [pregunta], !dado, !moneda, !ppt [piedra/papel/tijera].')
            await message.channel.send('JUEGOS: !3enraya (!unirse, !mover), !ahorcado (!letra), !numero (!adivinanum), !trivia (!respuesta), !ruleta, !bpm (!adivinarbpm).')
        elif cmd == "!redes":
            await message.channel.send('Sigueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB | FB: https://www.facebook.com/profile.php?id=61582389543371')
        elif cmd == "!sobre":
            await message.channel.send('JONAS RDB // HARD DANCE. DJ alicantino criado entre vinilos desde 1994. +30 años haciendo vibrar pistas con Hard Dance, Remember y pura energía rave.')
        elif cmd == "!normas":
            await message.channel.send('NORMAS: 1) Lenguaje respetuoso. 2) Emotes sin ofender. 3) Criticas constructivas SI, ataques NO. TOLERANCIA CERO: amenazas, acoso, doxxing, odio o spam. Incumplir = BAN PERMANENTE. ¡Disfruta!')
        elif cmd in ["!prime", "!suscri"]:
            await message.channel.send('Suscribete GRATIS con Twitch Prime! Apoya el canal sin coste extra, desbloquea emotes y ayuda a que la fiesta no pare. ¡Gracias!')
        elif cmd in ["!festero", "!fiesta", "!animado"]:
            p = random.randint(0, 100)
            emote = obtener_emote_aleatorio()
            if p >= 85:
                frase = "¡@" + user + " esta al " + str(p) + "% de festero! ¡A ROMPERLA!"
            elif p >= 65:
                frase = "@" + user + " esta al " + str(p) + "% de festero. ¡Sube el volumen!"
            elif p >= 45:
                frase = "@" + user + " esta al " + str(p) + "% de festero. Vas bien, ¡sigue bailando!"
            elif p >= 25:
                frase = "@" + user + " esta al " + str(p) + "% de festero. ¡Despierta que empieza la sesion!"
            else:
                frase = "@" + user + " esta al " + str(p) + "% sin ganas... ¿Necesitas un Red Bull?"
            if emote:
                await message.channel.send(frase + " " + emote)
            else:
                await message.channel.send(frase)
        elif cmd in ["!vf", "!verdaderofalso"]:
            if vf_activo:
                await message.channel.send("Ya hay pregunta activa: " + vf_pregunta + " (Responde !v o !f)")
            else:
                vf_activo = True
                q, a = random.choice(preguntas_vf)
                vf_pregunta = q
                vf_respuesta = a
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !verdadero / !f o !falso) " + emote)
                else:
                    await message.channel.send("¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !verdadero / !f o !falso)")
        elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
            if not vf_activo:
                await message.channel.send("No hay pregunta activa. Inicia con !vf")
            else:
                resp = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
                emote = obtener_emote_aleatorio()
                if resp == vf_respuesta:
                    if emote:
                        await message.channel.send("¡CORRECTO @" + user + "! Era " + vf_respuesta + ". ¡Escribe !vf para otra! " + emote)
                    else:
                        await message.channel.send("¡CORRECTO @" + user + "! Era " + vf_respuesta + ". ¡Escribe !vf para otra!")
                else:
                    if emote:
                        await message.channel.send("Incorrecto @" + user + ". La respuesta era " + vf_respuesta + ". ¡Escribe !vf para otra! " + emote)
                    else:
                        await message.channel.send("Incorrecto @" + user + ". La respuesta era " + vf_respuesta + ". ¡Escribe !vf para otra!")
                vf_activo = False
        elif cmd in ["!3enraya", "!tictactoe"]:
            if ttt_activo:
                tab = ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + " - " + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + " - " + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]
                await message.channel.send("Ya hay partida en curso. Tablero: " + tab)
            else:
                ttt_activo = True
                ttt_x = user
                ttt_o = ""
                ttt_turno = "X"
                ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("@" + user + " inicio 3 en Raya! Otro viewer debe escribir !unirse para jugar como O. " + emote)
                else:
                    await message.channel.send("@" + user + " inicio 3 en Raya! Otro viewer debe escribir !unirse para jugar como O.")
        elif cmd == "!unirse":
            if not ttt_activo:
                await message.channel.send("No hay partida activa. Inicia con !3enraya")
            elif ttt_o != "":
                await message.channel.send("La partida ya tiene 2 jugadores.")
            elif user == ttt_x:
                await message.channel.send("No puedes jugar contra ti mismo.")
            else:
                ttt_o = user
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("@" + ttt_o + " se unio como O. ¡@" + ttt_x + " (X), es tu turno! Escribe: !mover [1-9] " + emote)
                else:
                    await message.channel.send("@" + ttt_o + " se unio como O. ¡@" + ttt_x + " (X), es tu turno! Escribe: !mover [1-9]")
        elif cmd == "!mover":
            if not ttt_activo:
                await message.channel.send("No hay partida activa. Inicia con !3enraya")
                return
            if user not in [ttt_x, ttt_o]:
                await message.channel.send("No eres parte de esta partida.")
                return
            if (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o):
                await message.channel.send("No es tu turno. Le toca a " + ("X" if ttt_turno == "X" else "O"))
                return
            if not arg:
                await message.channel.send("Usa un numero del 1 al 9. Ejemplo: !mover 5")
                return
            pos_str = arg.strip()
            if not pos_str.isdigit() or not (1 <= int(pos_str) <= 9):
                await message.channel.send("Usa un numero del 1 al 9.")
                return
            pos = int(pos_str) - 1
            if ttt_tablero[pos] in ["X", "O"]:
                await message.channel.send("Casilla ocupada.")
                return
            ttt_tablero[pos] = ttt_turno
            ganar = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
            ganador = None
            for a, b, c in ganar:
                if ttt_tablero[a] == ttt_tablero[b] == ttt_tablero[c]:
                    ganador = ttt_tablero[a]
                    break
            tab = ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + " - " + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + " - " + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]
            emote = obtener_emote_aleatorio()
            if not ganador and all(c in ["X", "O"] for c in ttt_tablero):
                ganador = "Empate"
            if ganador == "Empate":
                if emote:
                    await message.channel.send("¡Empate! Tablero: " + tab + " " + emote)
                else:
                    await message.channel.send("¡Empate! Tablero: " + tab)
                ttt_activo = False
            elif ganador:
                ganador_user = ttt_x if ganador == "X" else ttt_o
                if emote:
                    await message.channel.send("¡GANADOR! @" + ganador_user + "! Tablero: " + tab + " " + emote)
                else:
                    await message.channel.send("¡GANADOR! @" + ganador_user + "! Tablero: " + tab)
                ttt_activo = False
            else:
                ttt_turno = "O" if ttt_turno == "X" else "X"
                siguiente = ttt_x if ttt_turno == "X" else ttt_o
                if emote:
                    await message.channel.send("Turno de " + ttt_turno + " (@" + siguiente + "). Escribe: !mover [1-9]. Tablero: " + tab + " " + emote)
                else:
                    await message.channel.send("Turno de " + ttt_turno + " (@" + siguiente + "). Escribe: !mover [1-9]. Tablero: " + tab)
        elif cmd == "!cancelar3":
            if ttt_activo and (user == ttt_x or user == CANAL):
                ttt_activo = False
                await message.channel.send("Partida cancelada.")
            else:
                await message.channel.send("No hay partida activa.")
        elif cmd == "!tablero":
            if ttt_activo:
                tab = ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + " - " + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + " - " + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]
                await message.channel.send("Tablero: " + tab + " - Turno: " + ttt_turno)
            else:
                await message.channel.send("No hay partida activa.")
        elif cmd == "!ahorcado":
            if ahorcado_activo:
                estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                await message.channel.send("Ya hay ahorcado activo. Estado: " + estado + " | Intentos: " + str(ahorcado_intentos))
            else:
                ahorcado_activo = True
                ahorcado_palabra = random.choice(palabras_ahorcado)
                ahorcado_adivinadas = set()
                ahorcado_intentos = 6
                estado = " ".join(["_" for _ in ahorcado_palabra])
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("@" + user + " inicio el AHORCADO! Palabra secreta: " + estado + " | Escribe !letra [a-z] " + emote)
                else:
                    await message.channel.send("@" + user + " inicio el AHORCADO! Palabra secreta: " + estado + " | Escribe !letra [a-z]")
        elif cmd == "!letra":
            if not ahorcado_activo:
                await message.channel.send("No hay ahorcado activo. Inicia con !ahorcado")
                return
            if not arg:
                await message.channel.send("Escribe UNA letra. Ejemplo: !letra a")
                return
            letra = arg.strip().lower()
            if len(letra) != 1 or not letra.isalpha():
                await message.channel.send("Escribe UNA sola letra. Ejemplo: !letra a")
                return
            if letra in ahorcado_adivinadas:
                await message.channel.send("Ya probaste '" + letra + "'. Elige otra.")
                return
            ahorcado_adivinadas.add(letra)
            emote = obtener_emote_aleatorio()
            if letra in ahorcado_palabra:
                if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                    if emote:
                        await message.channel.send("¡GANO @" + user + "! La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra! " + emote)
                    else:
                        await message.channel.send("¡GANO @" + user + "! La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra!")
                    ahorcado_activo = False
                else:
                    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                    if emote:
                        await message.channel.send("¡Bien! '" + letra + "' esta. Estado: " + estado + " " + emote)
                    else:
                        await message.channel.send("¡Bien! '" + letra + "' esta. Estado: " + estado)
            else:
                ahorcado_intentos -= 1
                if ahorcado_intentos <= 0:
                    if emote:
                        await message.channel.send("¡PERDISTE @" + user + "! La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra! " + emote)
                    else:
                        await message.channel.send("¡PERDISTE @" + user + "! La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra!")
                    ahorcado_activo = False
                else:
                    if emote:
                        await message.channel.send("'" + letra + "' NO esta. Intentos restantes: " + str(ahorcado_intentos) + " " + emote)
                    else:
                        await message.channel.send("'" + letra + "' NO esta. Intentos restantes: " + str(ahorcado_intentos))
        elif cmd == "!numero":
            if not num_activo:
                num_activo = True
                num_secreto = random.randint(1, 100)
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("@" + user + " inicio 'Adivina el Numero' (1-100). Escribe: !adivinanum [numero] " + emote)
                else:
                    await message.channel.send("@" + user + " inicio 'Adivina el Numero' (1-100). Escribe: !adivinanum [numero]")
            else:
                await message.channel.send("Ya hay juego activo. Escribe !adivinanum [1-100]")
        elif cmd == "!adivinanum":
            if not num_activo:
                await message.channel.send("No hay juego activo. Inicia con !numero")
                return
            if not arg:
                await message.channel.send("Escribe un numero. Ejemplo: !adivinanum 50")
                return
            try:
                n = int(arg.strip())
                if n < 1 or n > 100:
                    await message.channel.send("El numero debe ser entre 1 y 100.")
                    return
                emote = obtener_emote_aleatorio()
                if n == num_secreto:
                    if emote:
                        await message.channel.send("¡@" + user + " ACERTO! Era " + str(num_secreto) + ". ¡Escribe !numero para otra! " + emote)
                    else:
                        await message.channel.send("¡@" + user + " ACERTO! Era " + str(num_secreto) + ". ¡Escribe !numero para otra!")
                    num_activo = False
                elif n < num_secreto:
                    if emote:
                        await message.channel.send("@" + user + ": el numero es MAS ALTO que " + str(n) + " " + emote)
                    else:
                        await message.channel.send("@" + user + ": el numero es MAS ALTO que " + str(n))
                else:
                    if emote:
                        await message.channel.send("@" + user + ": el numero es MAS BAJO que " + str(n) + " " + emote)
                    else:
                        await message.channel.send("@" + user + ": el numero es MAS BAJO que " + str(n))
            except:
                await message.channel.send("Escribe un numero valido.")
        elif cmd in ["!ppt", "!piedra"]:
            opciones = ["piedra", "papel", "tijera"]
            if not arg:
                await message.channel.send("Elige: piedra, papel o tijera. Ejemplo: !ppt piedra")
                return
            eleccion_bot = random.choice(opciones)
            eleccion_user = arg.strip().lower()
            if eleccion_user not in opciones:
                await message.channel.send("Elige: piedra, papel o tijera. Ejemplo: !ppt piedra")
                return
            emote = obtener_emote_aleatorio()
            if eleccion_user == eleccion_bot:
                resultado = "Empate. Ambos " + eleccion_user + "."
            elif (eleccion_user == "piedra" and eleccion_bot == "tijera") or (eleccion_user == "papel" and eleccion_bot == "piedra") or (eleccion_user == "tijera" and eleccion_bot == "papel"):
                resultado = "¡@" + user + " GANA! " + eleccion_user + " vence a " + eleccion_bot + "."
            else:
                resultado = "¡Gana el bot! " + eleccion_bot + " vence a " + eleccion_user + "."
            if emote:
                await message.channel.send("@" + user + ": " + eleccion_user + " vs Bot: " + eleccion_bot + ". " + resultado + " " + emote)
            else:
                await message.channel.send("@" + user + ": " + eleccion_user + " vs Bot: " + eleccion_bot + ". " + resultado)
        elif cmd == "!dado":
            n = random.randint(1, 6)
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("@" + user + " tiro el dado: " + str(n) + " " + emote)
            else:
                await message.channel.send("@" + user + " tiro el dado: " + str(n))
        elif cmd == "!moneda":
            r = random.choice(["CARA", "CRUZ"])
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("@" + user + " lanzo la moneda: " + r + " " + emote)
            else:
                await message.channel.send("@" + user + " lanzo la moneda: " + r)
        elif cmd in ["!bola", "!bola8"]:
            if not arg:
                await message.channel.send("Haz una pregunta. Ejemplo: !bola ire a un rave?")
                return
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("@" + user + ": " + random.choice(respuestas_bola) + " " + emote)
            else:
                await message.channel.send("@" + user + ": " + random.choice(respuestas_bola))
        elif cmd in ["!reto", "!verdad"]:
            tipo = random.choice(["RETO", "VERDAD"])
            cont = random.choice(retos) if tipo == "RETO" else random.choice(verdades)
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("@" + user + " te toca un " + tipo + ": " + cont + " " + emote)
            else:
                await message.channel.send("@" + user + " te toca un " + tipo + ": " + cont)
        elif cmd == "!trivia":
            if not trivia_on:
                qs = [{"p":"BPM tipico del techno?","r":"130"},{"p":"Ciudad natal del techno?","r":"detroit"},{"p":"House + techno?","r":"tech house"},{"p":"Cuna del drum&bass?","r":"londres"},{"p":"Que es BPM?","r":"beats por minuto"}]
                q = random.choice(qs)
                trivia_on = True
                trivia_r = q["r"]
                emote = obtener_emote_aleatorio()
                if emote:
                    await message.channel.send("TRIVIA! " + q["p"] + " (Responde: !respuesta [tu respuesta]) " + emote)
                else:
                    await message.channel.send("TRIVIA! " + q["p"] + " (Responde: !respuesta [tu respuesta])")
            else:
                await message.channel.send("Ya hay trivia activa. Responde con !respuesta")
        elif cmd == "!respuesta":
            if not trivia_on:
                await message.channel.send("No hay trivia activa. Inicia con !trivia")
                return
            if not arg:
                await message.channel.send("Escribe tu respuesta. Ejemplo: !respuesta 130")
                return
            emote = obtener_emote_aleatorio()
            if arg.lower().strip() == trivia_r:
                if emote:
                    await message.channel.send("¡CORRECTO @" + user + "! " + emote)
                else:
                    await message.channel.send("¡CORRECTO @" + user + "!")
                trivia_on = False
            else:
                if emote:
                    await message.channel.send("Incorrecto @" + user + ". " + emote)
                else:
                    await message.channel.send("Incorrecto @" + user + ".")
        elif cmd == "!ruleta":
            g = random.choice(["Techno","House","Trance","Drum&Bass","Dubstep","Hardstyle","Remember"])
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("¡Ruleta! Genero: " + g + ". ¡Pon una cancion! " + emote)
            else:
                await message.channel.send("¡Ruleta! Genero: " + g + ". ¡Pon una cancion!")
        elif cmd == "!bpm":
            bpm_n = random.randint(120, 174)
            emote = obtener_emote_aleatorio()
            if emote:
                await message.channel.send("Adivina el BPM (120-174): !adivinarbpm [numero] " + emote)
            else:
                await message.channel.send("Adivina el BPM (120-174): !adivinarbpm [numero]")
        elif cmd == "!adivinarbpm":
            if bpm_n is None:
                await message.channel.send("Inicia con !bpm primero")
                return
            if not arg:
                await message.channel.send("Escribe un numero. Ejemplo: !adivinarbpm 130")
                return
            try:
                n = int(arg)
                emote = obtener_emote_aleatorio()
                if n == bpm_n:
                    if emote:
                        await message.channel.send("¡EXACTO @" + user + "! Era " + str(bpm_n) + " BPM. " + emote)
                    else:
                        await message.channel.send("¡EXACTO @" + user + "! Era " + str(bpm_n) + " BPM.")
                    bpm_n = None
                elif abs(n - bpm_n) <= 5:
                    if emote:
                        await message.channel.send("¡Muy cerca @" + user + "! A " + str(abs(n-bpm_n)) + " BPM. " + emote)
                    else:
                        await message.channel.send("¡Muy cerca @" + user + "! A " + str(abs(n-bpm_n)) + " BPM.")
                else:
                    if emote:
                        await message.channel.send("Frio @" + user + ". " + emote)
                    else:
                        await message.channel.send("Frio @" + user + ".")
            except:
                await message.channel.send("Escribe un numero valido.")


bot = Bot()

if __name__ == '__main__':
    bot.run()
