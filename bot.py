import socket
import ssl
import time
import random
import os

TOKEN = os.environ.get('TWITCH_TOKEN', 'oauth:2e4x9y0ojlktr5pi60zm8rt803k0i8')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')
BOT = os.environ.get('TWITCH_BOT', 'sesionesoldschool')

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

num_activo = False
num_secreto = 0

vf_activo = False
vf_pregunta = ""
vf_respuesta = ""

frases_animar = [
    "¿Qué género os gusta más, techno o house?",
    "¿Alguien tiene algún set de Remember recomendado?",
    "¿De dónde sois todos? ¡Saludad en el chat!",
    "¿Cuál es vuestro BPM favorito para bailar?",
    "¿Techno duro o melódico? ¡Os leo!",
    "¿Quién más está disfrutando de la sesión?",
    "¡Escribe !comandos para ver todo lo que puedo hacer!"
]

palabras_ahorcado = [
    "techno", "house", "trance", "vinilo", "mezcla", "bpm",
    "rave", "fiesta", "bass", "drop", "set", "dj", "platina",
    "sintetizador", "acido", "detroit", "ibiza", "berlin",
    "minimal", "progressive", "hardcore", "remember", "makina"
]

preguntas_vf = [
    ("Los Beatles se originaron en Liverpool.", "verdadero"),
    ("El piano estándar tiene 88 teclas.", "verdadero"),
    ("Michael Jackson es el Rey del Rock.", "falso"),
    ("El reguetón se originó en Puerto Rico.", "verdadero"),
    ("Beethoven quedó sordo al final de su vida.", "verdadero"),
    ("La guitarra eléctrica se inventó antes que la acústica.", "falso"),
    ("Woodstock fue en 1969.", "verdadero"),
    ("Shakira es de México.", "falso"),
    ("El saxofón es un instrumento de viento madera.", "verdadero"),
    ("El flamenco es originario de Andalucía.", "verdadero"),
    ("El violín tiene 6 cuerdas.", "falso"),
    ("El rap y el hip-hop son lo mismo.", "falso"),
    ("David Bowie creó Ziggy Stardust.", "verdadero"),
    ("La ópera se originó en Italia.", "verdadero"),
    ("El sintetizador Moog fue clave en la música electrónica.", "verdadero"),
    ("Queen fue fundado por Freddie Mercury y Paul McCartney.", "falso"),
    ("El Techno nació en Detroit.", "verdadero"),
    ("El mariachi es de Argentina.", "falso"),
    ("Nirvana es el máximo exponente del Grunge.", "verdadero"),
    ("Mozart compuso su primera sinfonía a los 8 años.", "verdadero"),
    ("El bajo eléctrico tiene 4 cuerdas normalmente.", "verdadero"),
    ("El Dubstep tiene bajos pesados y ritmos a medio tiempo.", "verdadero"),
    ("Elvis Presley es el Rey del Pop.", "falso"),
    ("The Rolling Stones se formó en los 80.", "falso"),
    ("El Hardstyle tiene un BPM típico de 150.", "verdadero"),
    ("Bach era alemán.", "verdadero"),
    ("El Trap se originó en el sur de Estados Unidos.", "verdadero"),
    ("La flauta travesera es de viento metal.", "falso"),
    ("Thriller es el álbum más vendido de la historia.", "verdadero"),
    ("La Salsa tiene raíces en el Caribe y Nueva York.", "verdadero"),
    ("Tiesto es de Alemania.", "falso"),
    ("Drum and Bass tiene ritmos rápidos de breakbeat.", "verdadero"),
    ("Beethoven escribió 9 sinfonías.", "verdadero"),
    ("El Punk tiene canciones largas y solos complejos.", "falso"),
    ("Daft Punk es de Francia.", "verdadero")
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


def conectar():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = context.wrap_socket(s)
    s.connect(("irc.chat.twitch.tv", 6697))
    s.send(("PASS " + TOKEN + "\r\n").encode())
    s.send(("NICK " + BOT + "\r\n").encode())
    s.send(b"CAP REQ :twitch.tv/commands\r\n")
    s.send(("JOIN #" + CANAL + "\r\n").encode())
    return s


def enviar(s, msg):
    print("[ENVIANDO] " + msg)
    s.send(("PRIVMSG #" + CANAL + " :" + msg + "\r\n").encode())
    time.sleep(1.5)


def ttt_imprimir():
    return ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + "\n-----\n" + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + "\n-----\n" + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]


def ttt_verificar():
    ganar = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in ganar:
        if ttt_tablero[a] == ttt_tablero[b] == ttt_tablero[c]:
            return ttt_tablero[a]
    if all(c in ["X", "O"] for c in ttt_tablero):
        return "Empate"
    return None


def dibujar_ahorcado(intentos):
    fallos = 6 - intentos
    dibujo = ""
    if fallos >= 1:
        dibujo += "🟡"
    if fallos >= 2:
        dibujo += "🟩"
    if fallos >= 3:
        dibujo += "🟦"
    if fallos >= 4:
        dibujo += "🟦"
    if fallos >= 5:
        dibujo += "🟪"
    if fallos >= 6:
        dibujo += "💀"
    return dibujo


def ahorcado_estado():
    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
    letras = ", ".join(sorted(ahorcado_adivinadas)) if ahorcado_adivinadas else "ninguna"
    return dibujo_ahorcado_texto(ahorcado_intentos) + " | " + estado + " | Intentos: " + str(ahorcado_intentos) + " | Letras: " + letras


def dibujo_ahorcado_texto(intentos):
    return dibujar_ahorcado(intentos)


def comando(s, user, cmd, arg):
    global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
    global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
    global num_activo, num_secreto
    global vf_activo, vf_pregunta, vf_respuesta

    if cmd in ["!comandos", "!ayuda", "!help"]:
        enviar(s, "INFO: !redes, !sobre, !normas, !prime. DIVERSIÓN: !festero, !vf, !reto, !bola [pregunta], !dado, !moneda, !ppt [piedra/papel/tijera].")
        enviar(s, "JUEGOS: !3enraya (!unirse, !mover), !ahorcado (!letra), !numero (!adivinanum), !trivia (!respuesta), !ruleta, !bpm (!adivinarbpm).")
    elif cmd == "!redes":
        enviar(s, "Sígueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB | FB: https://www.facebook.com/profile.php?id=61582389543371")
    elif cmd == "!sobre":
        enviar(s, "JONAS RDB // HARD DANCE. DJ alicantino criado entre vinilos desde 1994. +30 años haciendo vibrar pistas con Hard Dance, Remember y pura energía rave.")
    elif cmd == "!normas":
        enviar(s, "NORMAS: 1) Lenguaje respetuoso. 2) Emotes sin ofender. 3) Críticas constructivas SÍ, ataques NO. TOLERANCIA CERO: amenazas, acoso, doxxing, odio o spam. Incumplir = BAN PERMANENTE. ¡Disfruta!")
    elif cmd in ["!prime", "!suscri"]:
        enviar(s, "¡Suscríbete GRATIS con Twitch Prime! Apoya el canal sin coste extra, desbloquea emotes y ayuda a que la fiesta no pare. ¡Gracias!")
    elif cmd in ["!festero", "!fiesta", "!animado"]:
        p = random.randint(0, 100)
        if p >= 85:
            frase = "¡@" + user + " está al " + str(p) + "% de festero! ¡A ROMPERLA!"
        elif p >= 65:
            frase = "@" + user + " está al " + str(p) + "% de festero. ¡Sube el volumen!"
        elif p >= 45:
            frase = "@" + user + " está al " + str(p) + "% de festero. Vas bien, ¡sigue bailando!"
        elif p >= 25:
            frase = "@" + user + " está al " + str(p) + "% de festero. ¡Despierta que empieza la sesión!"
        else:
            frase = "@" + user + " está al " + str(p) + "% sin ganas... ¿Necesitas un Red Bull?"
        enviar(s, frase)
    elif cmd in ["!vf", "!verdaderofalso"]:
        if vf_activo:
            enviar(s, "Ya hay pregunta activa: " + vf_pregunta + " (Responde !v o !f)")
        else:
            vf_activo = True
            q, a = random.choice(preguntas_vf)
            vf_pregunta = q
            vf_respuesta = a
            enviar(s, "¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !verdadero / !f o !falso)")
    elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
        if not vf_activo:
            enviar(s, "No hay pregunta activa. Inicia con !vf")
        else:
            resp_user = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
            if resp_user == vf_respuesta:
                enviar(s, "¡CORRECTO @" + user + "! Era " + vf_respuesta + ". ¡Escribe !vf para otra!")
            else:
                enviar(s, "Incorrecto @" + user + ". La respuesta era " + vf_respuesta + ". ¡Escribe !vf para otra!")
            vf_activo = False
    elif cmd in ["!3enraya", "!tictactoe"]:
        if ttt_activo:
            enviar(s, "Ya hay partida en curso. Tablero:\n" + ttt_imprimir())
        else:
            ttt_activo = True
            ttt_x = user
            ttt_o = ""
            ttt_turno = "X"
            ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
            enviar(s, "@" + user + " inició 3 en Raya! Otro viewer debe escribir !unirse para jugar como O.")
    elif cmd == "!unirse":
        if not ttt_activo:
            enviar(s, "No hay partida activa. Inicia con !3enraya")
        elif ttt_o != "":
            enviar(s, "La partida ya tiene 2 jugadores.")
        elif user == ttt_x:
            enviar(s, "No puedes jugar contra ti mismo.")
        else:
            ttt_o = user
            enviar(s, "@" + ttt_o + " se unió como O. ¡@" + ttt_x + " (X), es tu turno! Escribe: !mover [1-9]")
    elif cmd == "!mover":
        if not ttt_activo:
            enviar(s, "No hay partida activa. Inicia con !3enraya")
            return
        if user not in [ttt_x, ttt_o]:
            enviar(s, "No eres parte de esta partida.")
            return
        if (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o):
            enviar(s, "No es tu turno. Le toca a " + ("X" if ttt_turno == "X" else "O") + ".")
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
            enviar(s, "¡Empate! Tablero:\n" + ttt_imprimir())
            ttt_activo = False
        elif ganador:
            ganador_user = ttt_x if ganador == "X" else ttt_o
            enviar(s, "¡GANADOR! @" + ganador_user + "!\n" + ttt_imprimir())
            ttt_activo = False
        else:
            ttt_turno = "O" if ttt_turno == "X" else "X"
            siguiente = ttt_x if ttt_turno == "X" else ttt_o
            enviar(s, "Turno de " + ttt_turno + " (@" + siguiente + "). Escribe: !mover [1-9]\n" + ttt_imprimir())
    elif cmd == "!cancelar3":
        if ttt_activo and (user == ttt_x or user == CANAL):
            ttt_activo = False
            enviar(s, "Partida cancelada.")
        else:
            enviar(s, "No hay partida activa.")
    elif cmd == "!ahorcado":
        if ahorcado_activo:
            enviar(s, "Ya hay ahorcado activo. Estado: " + ahorcado_estado())
        else:
            ahorcado_activo = True
            ahorcado_palabra = random.choice(palabras_ahorcado)
            ahorcado_adivinadas = set()
            ahorcado_intentos = 6
            estado = " ".join(["_" for l in ahorcado_palabra])
            enviar(s, "@" + user + " inició el AHORCADO! Palabra secreta: " + estado + " | Escribe !letra [a-z]")
    elif cmd == "!letra":
        if not ahorcado_activo:
            enviar(s, "No hay ahorcado activo. Inicia con !ahorcado")
            return
        letra = arg.strip().lower()
        if len(letra) != 1 or not letra.isalpha():
            enviar(s, "Escribe UNA sola letra. Ejemplo: !letra a")
            return
        if letra in ahorcado_adivinadas:
            enviar(s, "Ya probaste '" + letra + "'. Elige otra.")
            return
        ahorcado_adivinadas.add(letra)
        if letra in ahorcado_palabra:
            if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                enviar(s, "¡@" + user + " GANÓ! La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra!")
                ahorcado_activo = False
            else:
                enviar(s, "¡Bien! '" + letra + "' está. Estado: " + ahorcado_estado())
        else:
            ahorcado_intentos -= 1
            if ahorcado_intentos <= 0:
                enviar(s, "¡PERDISTE @" + user + "! " + dibujar_ahorcado(0) + " La palabra era '" + ahorcado_palabra + "'. ¡Escribe !ahorcado para otra!")
                ahorcado_activo = False
            else:
                enviar(s, "'" + letra + "' NO está. Estado: " + ahorcado_estado())
    elif cmd == "!numero":
        if num_activo:
            enviar(s, "Ya hay juego activo. Escribe !adivinanum [1-100]")
        else:
            num_activo = True
            num_secreto = random.randint(1, 100)
            enviar(s, "@" + user + " inició 'Adivina el Número' (1-100). Escribe: !adivinanum [número]")
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
                enviar(s, "¡@" + user + " ACERTÓ! Era " + str(num_secreto) + ". ¡Escribe !numero para otra!")
                num_activo = False
            elif n < num_secreto:
                enviar(s, "@" + user + ": el número es MÁS ALTO que " + str(n) + ".")
            else:
                enviar(s, "@" + user + ": el número es MÁS BAJO que " + str(n) + ".")
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
            resultado = "Empate. Ambos " + eleccion_user + "."
        elif (eleccion_user == "piedra" and eleccion_bot == "tijera") or (eleccion_user == "papel" and eleccion_bot == "piedra") or (eleccion_user == "tijera" and eleccion_bot == "papel"):
            resultado = "¡@" + user + " GANA! " + eleccion_user + " vence a " + eleccion_bot + "."
        else:
            resultado = "¡Gana el bot! " + eleccion_bot + " vence a " + eleccion_user + "."
        enviar(s, "@" + user + ": " + eleccion_user + " vs Bot: " + eleccion_bot + ". " + resultado)
    elif cmd == "!dado":
        resultado = random.randint(1, 6)
        enviar(s, "@" + user + " tiró el dado: " + str(resultado))
    elif cmd == "!moneda":
        resultado = random.choice(["CARA", "CRUZ"])
        enviar(s, "@" + user + " lanzó la moneda: ¡" + resultado + "!")
    elif cmd in ["!bola", "!bola8"]:
        if not arg.strip():
            enviar(s, "Haz una pregunta. Ejemplo: !bola ¿Iré a un rave?")
            return
        enviar(s, "@" + user + ": " + random.choice(respuestas_bola))
    elif cmd in ["!reto", "!verdad"]:
        tipo = random.choice(["RETO", "VERDAD"])
        contenido = random.choice(retos) if tipo == "RETO" else random.choice(verdades)
        enviar(s, "@" + user + " te toca un " + tipo + ": " + contenido)
    elif cmd == "!trivia" and not trivia_on:
        qs = [{"p": "BPM típico del techno?", "r": "130"}, {"p": "Ciudad natal del techno?", "r": "detroit"}, {"p": "House + techno?", "r": "tech house"}, {"p": "Cuna del drum&bass?", "r": "londres"}, {"p": "¿Qué es BPM?", "r": "beats por minuto"}]
        q = random.choice(qs)
        trivia_on = True
        trivia_r = q["r"]
        enviar(s, "TRIVIA! " + q["p"] + " (Responde: !respuesta [tu respuesta])")
    elif cmd == "!respuesta" and trivia_on:
        if arg.lower().strip() == trivia_r:
            enviar(s, "¡CORRECTO @" + user + "!")
            trivia_on = False
        else:
            enviar(s, "Incorrecto @" + user + ".")
    elif cmd == "!ruleta":
        g = random.choice(["Techno", "House", "Trance", "Drum&Bass", "Dubstep", "Hardstyle", "Remember"])
        enviar(s, "¡Ruleta! Género: " + g + ". ¡Pon una canción!")
    elif cmd == "!bpm":
        bpm_n = random.randint(120, 174)
        enviar(s, "Adivina el BPM (120-174): !adivinarbpm [numero]")
    elif cmd == "!adivinarbpm" and bpm_n is not None:
        try:
            n = int(arg)
            if n == bpm_n:
                enviar(s, "¡EXACTO @" + user + "! Era " + str(bpm_n) + " BPM.")
                bpm_n = None
            elif abs(n - bpm_n) <= 5:
                enviar(s, "¡Muy cerca @" + user + "! A " + str(abs(n - bpm_n)) + " BPM.")
            else:
                enviar(s, "Frío @" + user + ".")
        except:
            enviar(s, "Escribe un número válido.")


def main():
    global ultimo_mensaje
    print("Bot de Twitch para la nube (Railway)")
    print("Canal: #" + CANAL)
    print("Bot: " + BOT)

    s = conectar()
    print("Bot listo en #" + CANAL + "!")
    print("Escribe en Twitch: !comandos")
    ultimo_mensaje = time.time()

    while True:
        try:
            if time.time() - ultimo_mensaje > 180:
                enviar(s, random.choice(frases_animar))
                ultimo_mensaje = time.time()

            data = s.recv(4096).decode('utf-8', errors='ignore')
            if data.startswith("PING"):
                s.send(b"PONG\r\n")
            elif "PRIVMSG" in data:
                ultimo_mensaje = time.time()
                parts = data.split(" ", 3)
                if len(parts) >= 4:
                    user = parts[0].split("!")[0][1:]
                    msg = parts[3][1:].strip()
                    print("[" + user + "]: " + msg)

                    if msg.startswith("!"):
                        pc = msg.split(" ", 1)
                        cmd = pc[0].lower()
                        arg = pc[1] if len(pc) > 1 else ""
                        comando(s, user, cmd, arg)
        except Exception as e:
            print("Error: " + str(e))
            print("Reconectando en 5 segundos...")
            time.sleep(5)
            try:
                s = conectar()
            except:
                pass


if __name__ == "__main__":
    main()
