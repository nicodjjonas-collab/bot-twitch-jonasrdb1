import socket
import ssl
import time
import random
import os
import requests

# CONFIGURACIÓN
TOKEN = os.environ.get('TWITCH_TOKEN', 'oauth:2e4x9y0ojlktr5pi60zm8rt803k0i8')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
BOT = os.environ.get('TWITCH_BOT', 'sesionesoldschool')
GEMINI_KEY = os.environ.get('GEMINI_KEY', '')

# Variables de juegos
trivia_on = False
trivia_r = ""
bpm_n = None
ultimo_mensaje = time.time()

ttt_activo = False
ttt_x = ""
ttt_o = ""
ttt_turno = "X"
ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

ahorcado_activo = False
ahorcado_palabra = ""
ahorcado_adivinadas = set()
ahorcado_intentos = 6
ahorcado_jugador = ""

num_activo = False
num_secreto = 0
num_jugador = ""

vf_activo = False
vf_pregunta = ""
vf_respuesta = ""

frases_animar = [
    "¿Qué género os gusta más, techno o house? 🎧",
    "¿Alguien tiene algún set de Remember recomendado? 🔥",
    "¿De dónde sois todos? ¡Saludad en el chat! 🌍",
    "¿Cuál es vuestro BPM favorito para bailar? 💃",
    "¿Techno duro o melódico? ¡Os leo! 👀",
    "¿Quién más está disfrutando de la sesión? 🏠",
    "¿Qué os parece la energía de hoy? ¡Subid el volumen! 🔊",
    "¡Escribe !comandos para ver todo lo que puedo hacer!"
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
    "Pon la canción que más te haga bailar ahora mismo 🎵",
    "Di tu género favorito y por qué 🎧",
    "Cuéntanos tu mejor experiencia en un rave 🎪",
    "Nombra 3 DJs que te encanten ",
    "¿Vinilo o digital? Defiende tu postura 💿",
    "Describe tu sesión perfecta en 3 palabras ✨",
    "¿Cuál fue el último track que te voló la cabeza? 🤯",
    "Recomienda un set para esta noche 🔥"
]

verdades = [
    "¿Cuál es tu guilty pleasure musical? 🎶",
    "¿Alguna vez has llorado con una canción? 😢",
    "¿Qué género no soportas? 🤔",
    "¿Cuál es el track más raro que tienes? 🦄",
    "¿Techno a las 8am o house a las 4am? ⏰",
    "¿Tu momento más épico en una pista? ",
    "¿Qué DJ te hubiera gustado ver en vivo? 🎟️",
    "¿Vinilo más caro que has comprado? 💸"
]

respuestas_bola = [
    "Definitivamente sí 🔮", "Sin duda ✅", "Sí, totalmente ✅",
    "Las señales apuntan a que sí ✨", "Pregunta de nuevo más tarde 🔄",
    "Mejor no te digo ahora 🤫", "Mis fuentes dicen que no ❌",
    "Muy dudoso... ", "No cuentes con ello 🚫", "El universo dice que sí 🌟"
]

def conectar():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = context.wrap_socket(s)
    s.connect(("irc.chat.twitch.tv", 6697))
    s.send(f"PASS {TOKEN}\r\n".encode())
    s.send(f"NICK {BOT}\r\n".encode())
    s.send("CAP REQ :twitch.tv/commands\r\n".encode())
    s.send(f"JOIN #{CANAL}\r\n".encode())
    return s

def enviar(s, msg):
    print(f"[ENVIANDO] {msg}")
    s.send(f"PRIVMSG #{CANAL} :{msg}\r\n".encode())
    time.sleep(1.5)

def ia_gemini(preg):
    if not GEMINI_KEY:
        return "La IA no está configurada."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        prompt = f"Eres {BOT}, DJ y animador del chat de JonasRDB. Responde en español, máximo 2 frases cortas, con energía rave. Pregunta del usuario: {preg}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 100, "temperature": 0.7}
        }
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[ERROR IA] {e}")
    return None

def ttt_imprimir():
    return f"{ttt_tablero[0]}|{ttt_tablero[1]}|{ttt_tablero[2]}\n-----\n{ttt_tablero[3]}|{ttt_tablero[4]}|{ttt_tablero[5]}\n-----\n{ttt_tablero[6]}|{ttt_tablero[7]}|{ttt_tablero[8]}"

def ttt_verificar():
    ganar = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a,b,c in ganar:
        if ttt_tablero[a] == ttt_tablero[b] == ttt_tablero[c]:
            return ttt_tablero[a]
    if all(c in ["X", "O"] for c in ttt_tablero):
        return "Empate"
    return None

def dibujar_ahorcado(intentos):
    fallos = 6 - intentos
    dibujo = ""
    if fallos >= 1: dibujo += "🟡"
    if fallos >= 2: dibujo += "🟩"
    if fallos >= 3: dibujo += ""
    if fallos >= 4: dibujo += "🟦"
    if fallos >= 5: dibujo += "🟪"
    if fallos >= 6: dibujo += "💀"
    return dibujo

def ahorcado_estado():
    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
    letras = ", ".join(sorted(ahorcado_adivinadas)) if ahorcado_adivinadas else "ninguna"
    return f"{dibujar_ahorcado(ahorcado_intentos)} | {estado} | Intentos: {ahorcado_intentos} | Letras: {letras}"

def comando(s, user, cmd, arg):
    global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
    global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos, ahorcado_jugador
    global num_activo, num_secreto, num_jugador
    global vf_activo, vf_pregunta, vf_respuesta
    
    if cmd in ["!comandos", "!ayuda", "!help"]:
        enviar(s, "📜 INFO: !redes, !sobre, !normas, !prime. 🎉 DIVERSIÓN: !festero, !vf, !reto, !bola [pregunta], !dado, !moneda, !ppt [piedra/papel/tijera].")
        enviar(s, "🎮 JUEGOS: !3enraya (!unirse, !mover), !ahorcado (!letra), !numero (!adivinanum), !trivia (!respuesta), !ruleta, !bpm (!adivinarbpm).")
    elif cmd == "!redes":
        enviar(s, "🔗 Sígueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB | FB: https://www.facebook.com/profile.php?id=61582389543371")
    elif cmd == "!sobre":
        enviar(s, "🎧 JONAS RDB // HARD DANCE. DJ alicantino criado entre vinilos desde 1994. +30 años haciendo vibrar pistas con Hard Dance, Remember y pura energía rave. 🚀")
    elif cmd == "!normas":
        enviar(s, "⚠️ NORMAS: 1️⃣ Lenguaje respetuoso. 2️⃣ Emotes sin ofender. 3️⃣ Críticas constructivas SÍ, ataques NO. 🚫 TOLERANCIA CERO: amenazas, acoso, doxxing, odio o spam. ⛔ Incumplir = BAN PERMANENTE. ¡Disfruta! 🎧")
    elif cmd in ["!prime", "!suscri"]:
        enviar(s, "👑 ¡Suscríbete GRATIS con Twitch Prime! Apoya el canal sin coste extra, desbloquea emotes y ayuda a que la fiesta no pare. ¡Gracias! ❤️")
    elif cmd in ["!festero", "!fiesta", "!animado"]:
        p = random.randint(0, 100)
        if p >= 85: frase = f"🔥 ¡@{user} está al {p}% de festero! ¡A ROMPERLA! 🎉"
        elif p >= 65: frase = f" @{user} está al {p}% de festero. ¡Sube el volumen! 🎧"
        elif p >= 45: frase = f"🎶 @{user} está al {p}% de festero. Vas bien, ¡sigue bailando! 💃"
        elif p >= 25: frase = f"😐 @{user} está al {p}% de festero. ¡Despierta que empieza la sesión! ⚡"
        else: frase = f"😴 @{user} está al {p}% sin ganas... ¿Necesitas un Red Bull? 🥱"
        enviar(s, frase)
    elif cmd in ["!vf", "!verdaderofalso"]:
        if vf_activo:
            enviar(s, f"Ya hay pregunta activa: {vf_pregunta} (Responde !v o !f)")
        else:
            vf_activo = True
            q, a = random.choice(preguntas_vf)
            vf_pregunta, vf_respuesta = q, a
            enviar(s, f"🧠 ¡VERDADERO O FALSO! {vf_pregunta} (Responde !v o !verdadero / !f o !falso)")
    elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
        if not vf_activo:
            enviar(s, "No hay pregunta activa. Inicia con !vf")
        else:
            resp_user = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
            if resp_user == vf_respuesta:
                enviar(s, f"🎉 ¡CORRECTO @{user}! Era {vf_respuesta.capitalize()}. ¡Escribe !vf para otra!")
            else:
                enviar(s, f"❌ Incorrecto @{user}. La respuesta era {vf_respuesta.capitalize()}. ¡Escribe !vf para otra!")
            vf_activo = False
    elif cmd in ["!3enraya", "!tictactoe"]:
        if ttt_activo:
            enviar(s, f"Ya hay partida en curso. Tablero:\n{ttt_imprimir()}")
        else:
            ttt_activo, ttt_x, ttt_o, ttt_turno = True, user, "", "X"
            ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
            enviar(s, f"🎮 @{user} inició 3 en Raya! Otro viewer debe escribir !unirse para jugar como 'O'.")
    elif cmd == "!unirse":
        if not ttt_activo:
            enviar(s, "No hay partida activa. Inicia con !3enraya")
        elif ttt_o != "":
            enviar(s, "La partida ya tiene 2 jugadores.")
        elif user == ttt_x:
            enviar(s, "No puedes jugar contra ti mismo.")
        else:
            ttt_o = user
            enviar(s, f" @{ttt_o} se unió como 'O'. ¡@{ttt_x} (X), es tu turno! Escribe: !mover [1-9]")
    elif cmd == "!mover":
        if not ttt_activo:
            enviar(s, "No hay partida activa. Inicia con !3enraya")
            return
        if user not in [ttt_x, ttt_o]:
            enviar(s, "No eres parte de esta partida.")
            return
        if (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o):
            enviar(s, f"No es tu turno. Le toca a {'X' if ttt_turno == 'X' else 'O'}.")
            return
        pos_str = arg.strip()
        if not pos_str.isdigit() or not (1 <= int(pos_str) <= 9):
            enviar(s, "Usa un número del 1 al 9.")
            return
        pos = int(pos_str) - 1
        if ttt_tablero[pos] in ["X", "O"]:
            enviar(s, "Casilla ocupada.")
            return
        ttt_tablero[pos] = ttt_turno
        ganador = ttt_verificar()
        if ganador == "Empate":
            enviar(s, f" ¡Empate! Tablero:\n{ttt_imprimir()}")
            ttt_activo = False
        elif ganador:
            enviar(s, f"🎉 ¡GANADOR! @{ttt_x if ganador == 'X' else ttt_o}!\n{ttt_imprimir()}")
            ttt_activo = False
        else:
            ttt_turno = "O" if ttt_turno == "X" else "X"
            enviar(s, f"Turno de {ttt_turno} (@{ttt_x if ttt_turno == 'X' else ttt_o}). Escribe: !mover [1-9]\n{ttt_imprimir()}")
    elif cmd == "!cancelar3":
        if ttt_activo and (user == ttt_x or user == CANAL):
            ttt_activo = False
            enviar(s, "🚫 Partida cancelada.")
        else:
            enviar(s, "No hay partida activa.")
    elif cmd == "!tablero":
        if ttt_activo:
            enviar(s, f"Tablero:\n{ttt_imprimir()}\nTurno: {ttt_turno}")
        else:
            enviar(s, "No hay partida activa.")
    elif cmd == "!ahorcado":
        if ahorcado_activo:
            enviar(s, f"Ya hay ahorcado activo. Estado: {ahorcado_estado()}")
        else:
            ahorcado_activo = True
            ahorcado_palabra = random.choice(palabras_ahorcado)
            ahorcado_adivinadas = set()
            ahorcado_intentos = 6
            ahorcado_jugador = user
            enviar(s, f"🎮 @{user} inició el AHORCADO! Palabra secreta: {ahorcado_estado()} | Escribe !letra [a-z]")
    elif cmd == "!letra":
        if not ahorcado_activo:
            enviar(s, "No hay ahorcado activo. Inicia con !ahorcado")
            return
        letra = arg.strip().lower()
        if len(letra) != 1 or not letra.isalpha():
            enviar(s, "Escribe UNA sola letra. Ejemplo: !letra a")
            return
        if letra in ahorcado_adivinadas:
            enviar(s, f"Ya probaste '{letra}'. Elige otra.")
            return
        ahorcado_adivinadas.add(letra)
        if letra in ahorcado_palabra:
            if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                enviar(s, f"🎉 ¡@{user} GANÓ! La palabra era '{ahorcado_palabra}'. ¡Escribe !ahorcado para otra!")
                ahorcado_activo = False
            else:
                enviar(s, f"✅ ¡Bien! '{letra}' está. Estado: {ahorcado_estado()}")
        else:
            ahorcado_intentos -= 1
            if ahorcado_intentos <= 0:
                enviar(s, f"💀 ¡PERDISTE @{user}! {dibujar_ahorcado(0)} La palabra era '{ahorcado_palabra}'. ¡Escribe !ahorcado para otra!")
                ahorcado_activo = False
            else:
                enviar(s, f"❌ '{letra}' NO está. Estado: {ahorcado_estado()}")
    elif cmd == "!rendirse":
        if ahorcado_activo and user == ahorcado_jugador:
            enviar(s, f"🏳️ @{user} se rindió. La palabra era '{ahorcado_palabra}'.")
            ahorcado_activo = False
        else:
            enviar(s, "No hay ahorcado activo o no eres el jugador.")
    elif cmd == "!numero":
        if num_activo:
            enviar(s, "Ya hay juego activo. Escribe !adivinanum [1-100]")
        else:
            num_activo = True
            num_secreto = random.randint(1, 100)
            num_jugador = user
            enviar(s, f" @{user} inició 'Adivina el Número' (1-100). Escribe: !adivinanum [número]")
    elif cmd == "!adivinanum":
        if not num_activo:
            enviar(s, "No hay juego activo. Inicia con !numero")
            return
        try:
            n = int(arg.strip())
            if n < 1 or n > 100:
                enviar(s, "El número debe ser entre 1 y 100.")
                return
            if n == num_secreto:
                enviar(s, f"🎉 ¡@{user} ACERTÓ! Era {num_secreto}. ¡Escribe !numero para otra!")
                num_activo = False
            elif n < num_secreto:
                enviar(s, f"️ @{user}: el número es MÁS ALTO que {n}.")
            else:
                enviar(s, f"⬇️ @{user}: el número es MÁS BAJO que {n}.")
        except:
            enviar(s, "Escribe un número válido.")
    elif cmd in ["!ppt", "!piedra"]:
        opciones = ["piedra", "papel", "tijera"]
        eleccion_bot = random.choice(opciones)
        eleccion_user = arg.strip().lower()
        if eleccion_user not in opciones:
            enviar(s, "Elige: piedra, papel o tijera. Ejemplo: !ppt piedra")
            return
        if eleccion_user == eleccion_bot:
            resultado = f"🤝 Empate. Ambos {eleccion_user}."
        elif (eleccion_user == "piedra" and eleccion_bot == "tijera") or (eleccion_user == "papel" and eleccion_bot == "piedra") or (eleccion_user == "tijera" and eleccion_bot == "papel"):
            resultado = f"🎉 ¡@{user} GANA! {eleccion_user} vence a {eleccion_bot}."
        else:
            resultado = f"😈 ¡Gana el bot! {eleccion_bot} vence a {eleccion_user}."
        enviar(s, f"📄✂️ @{user}: {eleccion_user} vs Bot: {eleccion_bot}. {resultado}")
    elif cmd == "!dado":
        resultado = random.randint(1, 6)
        emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        enviar(s, f" @{user} tiró el dado: {emojis[resultado]} {resultado}")
    elif cmd == "!moneda":
        resultado = random.choice(["CARA 👑", "CRUZ ✝️"])
        enviar(s, f"🪙 @{user} lanzó la moneda: ¡{resultado}!")
    elif cmd in ["!bola", "!bola8"]:
        if not arg.strip():
            enviar(s, "Haz una pregunta. Ejemplo: !bola ¿Iré a un rave?")
            return
        enviar(s, f"🔮 @{user}: {random.choice(respuestas_bola)}")
    elif cmd in ["!reto", "!verdad"]:
        tipo = random.choice(["RETO 🎯", "VERDAD 💬"])
        contenido = random.choice(retos) if tipo.startswith("RETO") else random.choice(verdades)
        enviar(s, f" @{user} te toca un {tipo}: {contenido}")
    elif cmd == "!trivia" and not trivia_on:
        qs = [{"p":"BPM del techno?","r":"130"},{"p":"Rey techno Detroit?","r":"juan atkins"},{"p":"House + techno?","r":"tech house"},{"p":"Cuna drum&bass?","r":"londres"},{"p":"Que es BPM?","r":"beats por minuto"}]
        q = random.choice(qs)
        trivia_on, trivia_r = True, q["r"]
        enviar(s, f"🎵 TRIVIA! {q['p']} (Responde: !respuesta [tu respuesta])")
    elif cmd == "!respuesta" and trivia_on:
        if arg.lower().strip() == trivia_r:
            enviar(s, f"🎉 ¡CORRECTO @{user}!")
            trivia_on = False
        else:
            enviar(s, f"❌ Incorrecto @{user}.")
    elif cmd == "!ruleta":
        g = random.choice(["Techno","House","Trance","Drum&Bass","Dubstep","Hardstyle","Remember"])
        enviar(s, f"🎲 ¡Ruleta! Género: {g}. ¡Pon una canción!")
    elif cmd == "!bpm":
        bpm_n = random.randint(120, 174)
        enviar(s, f"🎧 Adivina el BPM (120-174): !adivinarbpm [numero]")
    elif cmd == "!adivinarbpm" and bpm_n is not None:
        try:
            n = int(arg)
            if n == bpm_n:
                enviar(s, f"🎉 ¡EXACTO @{user}! Era {bpm_n} BPM.")
                bpm_n = None
            elif abs(n - bpm_n) <= 5:
                enviar(s, f"🔥 ¡Muy cerca @{user}! A {abs(n-bpm_n)} BPM.")
            else:
                enviar(s, f"❌ Frío @{user}.")
        except:
            enviar(s, "Escribe un número válido.")

def main():
    global ultimo_mensaje
    print("🚀 Bot de Twitch para la nube (Railway)")
    print(f"📺 Canal: #{CANAL}")
    print(f" Bot: {BOT}")
    print(f"🧠 Gemini: {'✅ Configurado' if GEMINI_KEY else '❌ No configurado (IA desactivada)'}")
    
    s = conectar()
    print(f"✅ Bot listo en #{CANAL}!")
    print("🎮 Escribe en Twitch: !comandos")
    ultimo_mensaje = time.time()
    
    while True:
        try:
            if time.time() - ultimo_mensaje > 180:
                enviar(s, random.choice(frases_animar))
                ultimo_mensaje = time.time()
            
            data = s.recv(4096).decode('utf-8', errors='ignore')
            if data.startswith("PING"):
                s.send("PONG\r\n".encode())
            elif "PRIVMSG" in data:
                ultimo_mensaje = time.time()
                parts = data.split(" ", 3)
                if len(parts) >= 4:
                    user = parts[0].split("!")[0][1:]
                    msg = parts[3][1:].strip()
                    print(f"[{user}]: {msg}")
                    
                    if f"@{BOT.lower()}" in msg.lower():
                        preg = msg.lower().replace(f"@{BOT.lower()}", "").strip()
                        if len(preg) > 2:
                            print(f"[IA Gemini] Procesando: {preg}")
                            resp = ia_gemini(preg)
                            if resp:
                                enviar(s, resp[:400])
                    
                    if msg.startswith("!"):
                        pc = msg.split(" ", 1)
                        comando(s, user, pc[0].lower(), pc[1] if len(pc) > 1 else "")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Reconectando en 5 segundos...")
            time.sleep(5)
            try:
                s = conectar()
            except:
                pass

if __name__ == "__main__":
    main()
