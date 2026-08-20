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
    "¿De dónde sois todos? ¡Saludad!",
    "¡Escribe !comandos para ver lo que puedo hacer!"
]

palabras_ahorcado = ["techno", "house", "trance", "vinilo", "mezcla", "bpm", "rave", "fiesta"]

preguntas_vf = [
    ("Los Beatles son de Liverpool.", "verdadero"),
    ("El piano tiene 88 teclas.", "verdadero"),
    ("Michael Jackson es el Rey del Rock.", "falso"),
    ("El reguetón es de Puerto Rico.", "verdadero")
]

retos = ["Pon tu canción favorita", "Di tu género favorito", "¿Vinilo o digital?"]
verdades = ["¿Tu guilty pleasure?", "¿Qué género no soportas?"]
respuestas_bola = ["Sí", "No", "Quizás", "Pregunta de nuevo"]


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


def comando(s, user, cmd, arg):
    global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
    global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
    global num_activo, num_secreto
    global vf_activo, vf_pregunta, vf_respuesta

    if cmd in ["!comandos", "!ayuda", "!help"]:
        enviar(s, "INFO: !redes, !sobre, !festero, !vf, !dado, !moneda, !bola, !trivia, !ahorcado, !numero")
    elif cmd == "!redes":
        enviar(s, "Sígueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB")
    elif cmd == "!sobre":
        enviar(s, "JONAS RDB // HARD DANCE. DJ alicantino desde 1994. +30 años de Hard Dance y Remember.")
    elif cmd in ["!festero", "!fiesta"]:
        p = random.randint(0, 100)
        if p >= 85:
            frase = "¡@" + user + " está al " + str(p) + "% de festero! ¡A ROMPERLA!"
        elif p >= 65:
            frase = "@" + user + " está al " + str(p) + "% de festero. ¡Sube el volumen!"
        elif p >= 45:
            frase = "@" + user + " está al " + str(p) + "% de festero. ¡Sigue bailando!"
        else:
            frase = "@" + user + " está al " + str(p) + "%... ¿Necesitas un Red Bull?"
        enviar(s, frase)
    elif cmd in ["!vf", "!verdaderofalso"]:
        if vf_activo:
            enviar(s, "Ya hay pregunta: " + vf_pregunta + " (Responde !v o !f)")
        else:
            vf_activo = True
            q, a = random.choice(preguntas_vf)
            vf_pregunta = q
            vf_respuesta = a
            enviar(s, "¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !f)")
    elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
        if not vf_activo:
            enviar(s, "No hay pregunta. Inicia con !vf")
        else:
            resp = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
            if resp == vf_respuesta:
                enviar(s, "¡CORRECTO @" + user + "! Era " + vf_respuesta)
            else:
                enviar(s, "Incorrecto @" + user + ". Era " + vf_respuesta)
            vf_activo = False
    elif cmd == "!dado":
        n = random.randint(1, 6)
        enviar(s, "@" + user + " tiró el dado: " + str(n))
    elif cmd == "!moneda":
        r = random.choice(["CARA", "CRUZ"])
        enviar(s, "@" + user + " lanzó la moneda: " + r)
    elif cmd in ["!bola", "!bola8"]:
        if not arg.strip():
            enviar(s, "Haz una pregunta. Ej: !bola ¿Iré a un rave?")
            return
        enviar(s, "@" + user + ": " + random.choice(respuestas_bola))
    elif cmd == "!trivia" and not trivia_on:
        qs = [{"p": "BPM del techno?", "r": "130"}, {"p": "Ciudad del techno?", "r": "detroit"}]
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
    elif cmd == "!ahorcado":
        if not ahorcado_activo:
            ahorcado_activo = True
            ahorcado_palabra = random.choice(palabras_ahorcado)
            ahorcado_adivinadas = set()
            ahorcado_intentos = 6
            estado = " ".join(["_" for _ in ahorcado_palabra])
            enviar(s, "@" + user + " inició AHORCADO! Palabra: " + estado)
    elif cmd == "!letra":
        if not ahorcado_activo:
            enviar(s, "Inicia con !ahorcado")
            return
        letra = arg.strip().lower()
        if len(letra) != 1:
            enviar(s, "Escribe UNA letra. Ej: !letra a")
            return
        if letra in ahorcado_adivinadas:
            enviar(s, "Ya probaste '" + letra + "'")
            return
        ahorcado_adivinadas.add(letra)
        if letra in ahorcado_palabra:
            if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                enviar(s, "¡GANÓ @" + user + "! Era '" + ahorcado_palabra + "'")
                ahorcado_activo = False
            else:
                estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                enviar(s, "¡Bien! '" + letra + "' está. " + estado)
        else:
            ahorcado_intentos -= 1
            if ahorcado_intentos <= 0:
                enviar(s, "PERDISTE @" + user + ". Era '" + ahorcado_palabra + "'")
                ahorcado_activo = False
            else:
                enviar(s, "'" + letra + "' NO está. Intentos: " + str(ahorcado_intentos))
    elif cmd == "!numero":
        if not num_activo:
            num_activo = True
            num_secreto = random.randint(1, 100)
            enviar(s, "@" + user + " inició 'Adivina el Número' (1-100). !adivinanum [número]")
    elif cmd == "!adivinanum":
        if not num_activo:
            enviar(s, "Inicia con !numero")
            return
        try:
            n = int(arg.strip())
            if n == num_secreto:
                enviar(s, "¡ACERTÓ @" + user + "! Era " + str(num_secreto))
                num_activo = False
            elif n < num_secreto:
                enviar(s, "@" + user + ": es MÁS ALTO que " + str(n))
            else:
                enviar(s, "@" + user + ": es MÁS BAJO que " + str(n))
        except:
            enviar(s, "Escribe un número válido")


def main():
    global ultimo_mensaje
    print("Bot de Twitch para Railway")
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
            print("Reconectando...")
            time.sleep(5)
            try:
                s = conectar()
            except:
                pass


if __name__ == "__main__":
    main()
