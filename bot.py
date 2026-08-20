import os
import random
import time
import twitchio
from twitchio.ext import commands

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
    "Que genero os gusta mas, techno o house?",
    "Alguien tiene algun set de Remember recomendado?",
    "De donde sois todos? Saludad en el chat!",
    "Escribe !comandos para ver lo que puedo hacer!"
]

palabras_ahorcado = ["techno", "house", "trance", "vinilo", "mezcla", "bpm", "rave", "fiesta"]

preguntas_vf = [
    ("Los Beatles son de Liverpool.", "verdadero"),
    ("El piano tiene 88 teclas.", "verdadero"),
    ("Michael Jackson es el Rey del Rock.", "falso"),
    ("El regueton es de Puerto Rico.", "verdadero"),
    ("Beethoven quedo sordo al final.", "verdadero"),
    ("La guitarra electrica se invento antes que la acustica.", "falso"),
    ("Woodstock fue en 1969.", "verdadero"),
    ("Shakira es de Mexico.", "falso"),
    ("El saxofon es de viento madera.", "verdadero"),
    ("El flamenco es de Andalucia.", "verdadero"),
    ("El violin tiene 6 cuerdas.", "falso"),
    ("El rap y el hip-hop son lo mismo.", "falso"),
    ("David Bowie creo Ziggy Stardust.", "verdadero"),
    ("La opera se origino en Italia.", "verdadero"),
    ("El Techno nacio en Detroit.", "verdadero"),
    ("El mariachi es de Argentina.", "falso"),
    ("Nirvana es el maximo exponente del Grunge.", "verdadero"),
    ("Mozart compuso su primera sinfonia a los 8 anos.", "verdadero"),
    ("El bajo electrico tiene 4 cuerdas.", "verdadero"),
    ("El Hardstyle tiene 150 BPM.", "verdadero"),
    ("Bach era aleman.", "verdadero"),
    ("El Trap se origino en el sur de EEUU.", "verdadero"),
    ("La flauta travesera es de viento metal.", "falso"),
    ("Thriller es el album mas vendido.", "verdadero"),
    ("Tiesto es de Alemania.", "falso"),
    ("Drum and Bass tiene ritmos rapidos.", "verdadero"),
    ("Beethoven escribio 9 sinfonias.", "verdadero"),
    ("El Punk tiene canciones largas.", "falso"),
    ("Daft Punk es de Francia.", "verdadero")
]

retos = [
    "Pon la cancion que mas te haga bailar",
    "Di tu genero favorito y por que",
    "Cuentanos tu mejor experiencia en un rave",
    "Nombra 3 DJs que te encanten",
    "Vinilo o digital? Defiende tu postura",
    "Describe tu sesion perfecta en 3 palabras"
]

verdades = [
    "Cual es tu guilty pleasure musical?",
    "Alguna vez has llorado con una cancion?",
    "Que genero no soportas?",
    "Cual es el track mas raro que tienes?",
    "Techno a las 8am o house a las 4am?",
    "Tu momento mas epico en una pista?"
]

respuestas_bola = [
    "Definitivamente si", "Sin duda", "Si, totalmente",
    "Las senales apuntan a que si", "Pregunta de nuevo mas tarde",
    "Mejor no te digo ahora", "Mis fuentes dicen que no",
    "Muy dudoso...", "No cuentes con ello", "El universo dice que si"
]


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=TOKEN, prefix="!", initial_channels=[CANAL])

    async def event_ready(self):
        print("Bot listo en #" + CANAL)
        print("Escribe en Twitch: !comandos")

    async def event_message(self, message):
        global ultimo_mensaje
        if message.echo:
            return
        user = message.author.name
        content = message.content.strip()
        ultimo_mensaje = time.time()
        print("[" + user + "]: " + content)
        if content.startswith("!"):
            await self.procesar_comando(message, user, content)
        if time.time() - ultimo_mensaje > 180:
            await message.channel.send(random.choice(frases_animar))
            ultimo_mensaje = time.time()

    async def procesar_comando(self, message, user, content):
        global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
        global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
        global num_activo, num_secreto
        global vf_activo, vf_pregunta, vf_respuesta

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ["!comandos", "!ayuda", "!help"]:
            await message.channel.send("INFO: !redes, !sobre, !normas, !prime. DIVERSION: !festero, !vf, !reto, !bola, !dado, !moneda, !ppt.")
            await message.channel.send("JUEGOS: !3enraya, !ahorcado, !numero, !trivia, !ruleta, !bpm.")
        elif cmd == "!redes":
            await message.channel.send("Sigueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB")
        elif cmd == "!sobre":
            await message.channel.send("JONAS RDB // HARD DANCE. DJ alicantino desde 1994. +30 anos de Hard Dance y Remember.")
        elif cmd == "!normas":
            await message.channel.send("NORMAS: 1) Lenguaje respetuoso. 2) Emotes sin ofender. 3) Criticas constructivas SI, ataques NO. TOLERANCIA CERO: amenazas, acoso, doxxing, odio o spam. Incumplir = BAN PERMANENTE.")
        elif cmd in ["!prime", "!suscri"]:
            await message.channel.send("Suscribete GRATIS con Twitch Prime! Apoya el canal sin coste extra.")
        elif cmd in ["!festero", "!fiesta", "!animado"]:
            p = random.randint(0, 100)
            if p >= 85:
                frase = "¡@" + user + " esta al " + str(p) + "% de festero! ¡A ROMPERLA!"
            elif p >= 65:
                frase = "@" + user + " esta al " + str(p) + "% de festero. ¡Sube el volumen!"
            elif p >= 45:
                frase = "@" + user + " esta al " + str(p) + "% de festero. Sigue bailando!"
            elif p >= 25:
                frase = "@" + user + " esta al " + str(p) + "% de festero. ¡Despierta!"
            else:
                frase = "@" + user + " esta al " + str(p) + "% sin ganas... ¿Necesitas un Red Bull?"
            await message.channel.send(frase)
        elif cmd in ["!vf", "!verdaderofalso"]:
            if vf_activo:
                await message.channel.send("Ya hay pregunta: " + vf_pregunta + " (Responde !v o !f)")
            else:
                vf_activo = True
                q, a = random.choice(preguntas_vf)
                vf_pregunta = q
                vf_respuesta = a
                await message.channel.send("¡VERDADERO O FALSO! " + vf_pregunta + " (Responde !v o !f)")
        elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
            if not vf_activo:
                await message.channel.send("No hay pregunta. Inicia con !vf")
            else:
                resp = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
                if resp == vf_respuesta:
                    await message.channel.send("¡CORRECTO @" + user + "! Era " + vf_respuesta)
                else:
                    await message.channel.send("Incorrecto @" + user + ". Era " + vf_respuesta)
                vf_activo = False
        elif cmd in ["!3enraya", "!tictactoe"]:
            if ttt_activo:
                tab = ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + " - " + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + " - " + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]
                await message.channel.send("Ya hay partida. Tablero: " + tab)
            else:
                ttt_activo = True
                ttt_x = user
                ttt_o = ""
                ttt_turno = "X"
                ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                await message.channel.send("@" + user + " inicio 3 en Raya! Otro viewer escribe !unirse para jugar como O.")
        elif cmd == "!unirse":
            if not ttt_activo:
                await message.channel.send("No hay partida. Inicia con !3enraya")
            elif ttt_o != "":
                await message.channel.send("La partida ya tiene 2 jugadores.")
            elif user == ttt_x:
                await message.channel.send("No puedes jugar contra ti mismo.")
            else:
                ttt_o = user
                await message.channel.send("@" + ttt_o + " se unio como O. @" + ttt_x + " (X) es tu turno. Escribe: !mover [1-9]")
        elif cmd == "!mover":
            if not ttt_activo:
                await message.channel.send("No hay partida. Inicia con !3enraya")
                return
            if user not in [ttt_x, ttt_o]:
                await message.channel.send("No eres parte de esta partida.")
                return
            if (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o):
                await message.channel.send("No es tu turno. Le toca " + ("X" if ttt_turno == "X" else "O"))
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
            if not ganador and all(c in ["X", "O"] for c in ttt_tablero):
                ganador = "Empate"
            tab = ttt_tablero[0] + "|" + ttt_tablero[1] + "|" + ttt_tablero[2] + " - " + ttt_tablero[3] + "|" + ttt_tablero[4] + "|" + ttt_tablero[5] + " - " + ttt_tablero[6] + "|" + ttt_tablero[7] + "|" + ttt_tablero[8]
            if ganador == "Empate":
                await message.channel.send("¡Empate! Tablero: " + tab)
                ttt_activo = False
            elif ganador:
                gan_user = ttt_x if ganador == "X" else ttt_o
                await message.channel.send("¡GANADOR! @" + gan_user + "! Tablero: " + tab)
                ttt_activo = False
            else:
                ttt_turno = "O" if ttt_turno == "X" else "X"
                sig = ttt_x if ttt_turno == "X" else ttt_o
                await message.channel.send("Turno de " + ttt_turno + " (@" + sig + "). Escribe: !mover [1-9]. Tablero: " + tab)
        elif cmd == "!ahorcado":
            if not ahorcado_activo:
                ahorcado_activo = True
                ahorcado_palabra = random.choice(palabras_ahorcado)
                ahorcado_adivinadas = set()
                ahorcado_intentos = 6
                estado = " ".join(["_" for _ in ahorcado_palabra])
                await message.channel.send("@" + user + " inicio AHORCADO! Palabra: " + estado + " | Escribe !letra [a-z]")
        elif cmd == "!letra":
            if not ahorcado_activo:
                await message.channel.send("Inicia con !ahorcado")
                return
            letra = arg.strip().lower()
            if len(letra) != 1 or not letra.isalpha():
                await message.channel.send("Escribe UNA letra. Ej: !letra a")
                return
            if letra in ahorcado_adivinadas:
                await message.channel.send("Ya probaste '" + letra + "'")
                return
            ahorcado_adivinadas.add(letra)
            if letra in ahorcado_palabra:
                if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                    await message.channel.send("¡GANO @" + user + "! Era '" + ahorcado_palabra + "'")
                    ahorcado_activo = False
                else:
                    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                    await message.channel.send("¡Bien! '" + letra + "' esta. " + estado)
            else:
                ahorcado_intentos -= 1
                if ahorcado_intentos <= 0:
                    await message.channel.send("PERDISTE @" + user + ". Era '" + ahorcado_palabra + "'")
                    ahorcado_activo = False
                else:
                    await message.channel.send("'" + letra + "' NO esta. Intentos: " + str(ahorcado_intentos))
        elif cmd == "!numero":
            if not num_activo:
                num_activo = True
                num_secreto = random.randint(1, 100)
                await message.channel.send("@" + user + " inicio 'Adivina el Numero' (1-100). !adivinanum [numero]")
        elif cmd == "!adivinanum":
            if not num_activo:
                await message.channel.send("Inicia con !numero")
                return
            try:
                n = int(arg.strip())
                if n == num_secreto:
                    await message.channel.send("¡ACERTO @" + user + "! Era " + str(num_secreto))
                    num_activo = False
                elif n < num_secreto:
                    await message.channel.send("@" + user + ": es MAS ALTO que " + str(n))
                else:
                    await message.channel.send("@" + user + ": es MAS BAJO que " + str(n))
            except:
                await message.channel.send("Escribe un numero valido")
        elif cmd in ["!ppt", "!piedra"]:
            opciones = ["piedra", "papel", "tijera"]
            bot_e = random.choice(opciones)
            user_e = arg.strip().lower()
            if user_e not in opciones:
                await message.channel.send("Elige: piedra, papel o tijera. Ej: !ppt piedra")
                return
            if user_e == bot_e:
                res = "Empate. Ambos " + user_e + "."
            elif (user_e == "piedra" and bot_e == "tijera") or (user_e == "papel" and bot_e == "piedra") or (user_e == "tijera" and bot_e == "papel"):
                res = "¡GANA @" + user + "! " + user_e + " vence a " + bot_e + "."
            else:
                res = "Gana el bot! " + bot_e + " vence a " + user_e + "."
            await message.channel.send("@" + user + ": " + user_e + " vs Bot: " + bot_e + ". " + res)
        elif cmd == "!dado":
            n = random.randint(1, 6)
            await message.channel.send("@" + user + " tiro el dado: " + str(n))
        elif cmd == "!moneda":
            r = random.choice(["CARA", "CRUZ"])
            await message.channel.send("@" + user + " lanzo la moneda: " + r)
        elif cmd in ["!bola", "!bola8"]:
            if not arg.strip():
                await message.channel.send("Haz una pregunta. Ej: !bola ire a un rave?")
                return
            await message.channel.send("@" + user + ": " + random.choice(respuestas_bola))
        elif cmd in ["!reto", "!verdad"]:
            tipo = random.choice(["RETO", "VERDAD"])
            cont = random.choice(retos) if tipo == "RETO" else random.choice(verdades)
            await message.channel.send("@" + user + " te toca un " + tipo + ": " + cont)
        elif cmd == "!trivia" and not trivia_on:
            qs = [{"p": "BPM tipico del techno?", "r": "130"}, {"p": "Ciudad natal del techno?", "r": "detroit"}, {"p": "House + techno?", "r": "tech house"}, {"p": "Cuna del drum&bass?", "r": "londres"}]
            q = random.choice(qs)
            trivia_on = True
            trivia_r = q["r"]
            await message.channel.send("TRIVIA! " + q["p"] + " (Responde: !respuesta [tu respuesta])")
        elif cmd == "!respuesta" and trivia_on:
            if arg.lower().strip() == trivia_r:
                await message.channel.send("¡CORRECTO @" + user + "!")
                trivia_on = False
            else:
                await message.channel.send("Incorrecto @" + user + ".")
        elif cmd == "!ruleta":
            g = random.choice(["Techno", "House", "Trance", "Drum&Bass", "Dubstep", "Hardstyle", "Remember"])
            await message.channel.send("¡Ruleta! Genero: " + g + ". ¡Pon una cancion!")
        elif cmd == "!bpm":
            bpm_n = random.randint(120, 174)
            await message.channel.send("Adivina el BPM (120-174): !adivinarbpm [numero]")
        elif cmd == "!adivinarbpm" and bpm_n is not None:
            try:
                n = int(arg)
                if n == bpm_n:
                    await message.channel.send("¡EXACTO @" + user + "! Era " + str(bpm_n) + " BPM.")
                    bpm_n = None
                elif abs(n - bpm_n) <= 5:
                    await message.channel.send("¡Muy cerca @" + user + "! A " + str(abs(n - bpm_n)) + " BPM.")
                else:
                    await message.channel.send("Frio @" + user + ".")
            except:
                await message.channel.send("Escribe un numero valido.")


bot = Bot()

if __name__ == "__main__":
    bot.run()
