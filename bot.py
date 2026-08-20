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

trivia_on, trivia_r, bpm_n = False, "", None
ttt_activo, ttt_x, ttt_o, ttt_turno = False, "", "", "X"
ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
ahorcado_activo, ahorcado_palabra, ahorcado_intentos = False, "", 6
ahorcado_adivinadas = set()
num_activo, num_secreto = False, 0
vf_activo, vf_pregunta, vf_respuesta = False, "", ""
ultimo_mensaje_chat = time.time()
mensajes_automaticos = 0

EMOTES = ["Kappa", "PogChamp", "LUL", "OMEGALUL", "KEKW", "monkaS", "Sadge"]
TEMAS = ["¿Qué os parece la sesión?", "¿De dónde sois?", "¿Techno o house?", "¿Alguien ha ido a un rave?", "¿Vinilo o digital?", "¿Mejor DJ en vivo?", "¿Recordáis el Remember?", "¿BPM favorito?", "¿Hacemos trivia? !trivia", "¿Jugamos !3enraya?", "¿Techno duro o melódico?", "¿Set recomendado?"]
AHORCADO = ["techno", "house", "trance", "vinilo", "mezcla", "bpm", "rave", "fiesta", "bass", "drop", "set", "dj", "platina", "sintetizador", "acido", "detroit", "ibiza", "berlin", "minimal", "progressive", "hardcore", "remember", "makina", "eurodance", "disco"]
VF = [("Los Beatles son de Liverpool.", "verdadero"), ("El piano tiene 88 teclas.", "verdadero"), ("Michael Jackson es el Rey del Rock.", "falso"), ("El reguetón es de Puerto Rico.", "verdadero"), ("Beethoven quedó sordo.", "verdadero"), ("Woodstock fue en 1969.", "verdadero"), ("Shakira es de México.", "falso"), ("El Techno nació en Detroit.", "verdadero"), ("Daft Punk es de Francia.", "verdadero")]
RETOS = ["Pon tu canción favorita", "Di tu género favorito", "Cuéntanos tu mejor rave", "Nombra 3 DJs"]
VERDADES = ["¿Guilty pleasure?", "¿Lloraste con una canción?", "¿Qué género no soportas?", "¿Techno 8am o house 4am?"]
BOLA = ["Definitivamente sí", "Sin duda", "Sí, totalmente", "Las señales apuntan a que sí", "Pregunta más tarde", "Mejor no te digo", "Mis fuentes dicen que no", "Muy dudoso", "No cuentes con ello", "El universo dice que sí"]

def emote():
    return random.choice(EMOTES) if EMOTES else ""

def consultar_ia(pregunta):
    if not GROQ_KEY:
        print("[ERROR] GROQ_KEY no configurada")
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "qwen-2.5-32b",
            "messages": [
                {"role": "system", "content": f"Eres {BOT_NAME}, DJ y animador del chat de JonasRDB. Responde en español, máximo 2 frases cortas, con energía rave."},
                {"role": "user", "content": pregunta}
            ],
            "max_tokens": 150,
            "temperature": 0.8
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {GROQ_KEY.strip()}'}
        req = Request(url, data=data, headers=headers, method='POST')
        with urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR IA] {e}")
    return None

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CANAL])

    async def event_ready(self):
        print(f'✅ Bot conectado a #{CANAL}')
        print('🤖 Bot autónomo con Qwen IA (Groq)')
        print(f'💬 Menciona @{BOT_NAME} para hablar con la IA')
        self.loop.create_task(self.silencio())
        self.loop.create_task(self.autonomo())

    async def event_message(self, message):
        global ultimo_mensaje_chat, mensajes_automaticos
        if message.echo: return
        user = message.author.name
        content = message.content.strip()
        print(f"[{user}]: {content}")
        ultimo_mensaje_chat = time.time()
        mensajes_automaticos = 0

        mencion = f"@{BOT_NAME.lower()}"
        if mencion in content.lower():
            pregunta = content.lower().replace(mencion, "").strip()
            if len(pregunta) > 2:
                print(f"[IA] Procesando: {pregunta}")
                resp = consultar_ia(pregunta)
                e = emote()
                if resp:
                    await message.channel.send(f"@{user} {resp[:350]}{' ' + e if e else ''}")
                else:
                    await message.channel.send(f"@{user} Error con la IA. Intenta de nuevo.")

        if content.startswith("!"):
            await self.comandos(message, user, content)

    async def silencio(self):
        global ultimo_mensaje_chat, mensajes_automaticos
        while True:
            await asyncio.sleep(30)
            if time.time() - ultimo_mensaje_chat > 120 and mensajes_automaticos < 5:
                channel = self.get_channel(CANAL)
                if channel:
                    e = emote()
                    if random.random() > 0.5 and GROQ_KEY:
                        tema = random.choice(TEMAS)
                        resp = consultar_ia(tema)
                        if resp:
                            await channel.send(f"{resp[:350]}{' ' + e if e else ''}")
                            mensajes_automaticos += 1
                    else:
                        await channel.send(f"{random.choice(TEMAS)}{' ' + e if e else ''}")
                        mensajes_automaticos += 1

    async def autonomo(self):
        while True:
            await asyncio.sleep(300)
            channel = self.get_channel(CANAL)
            if channel and GROQ_KEY:
                e = emote()
                tema = random.choice(TEMAS)
                resp = consultar_ia(f"{tema} (Habla natural, haz pregunta al chat)")
                if resp:
                    await channel.send(f"{resp[:350]}{' ' + e if e else ''}")

    async def comandos(self, message, user, content):
        global trivia_on, trivia_r, bpm_n, ttt_activo, ttt_x, ttt_o, ttt_turno, ttt_tablero
        global ahorcado_activo, ahorcado_palabra, ahorcado_adivinadas, ahorcado_intentos
        global num_activo, num_secreto, vf_activo, vf_pregunta, vf_respuesta

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        e = emote()
        suf = f" {e}" if e else ""

        if cmd in ["!comandos", "!ayuda", "!help"]:
            await message.channel.send('INFO: !redes, !sobre, !normas, !prime. DIVERSION: !festero, !vf, !reto, !bola, !dado, !moneda, !ppt.')
            await message.channel.send('JUEGOS: !3enraya, !ahorcado, !numero, !trivia, !ruleta, !bpm.')
        elif cmd == "!redes":
            await message.channel.send('Sigueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB')
        elif cmd == "!sobre":
            await message.channel.send('JONAS RDB // HARD DANCE. DJ alicantino desde 1994. +30 años de Hard Dance y Remember.')
        elif cmd == "!normas":
            await message.channel.send('NORMAS: Respeto, sin spam, sin odio. BAN PERMANENTE si incumples. ¡Disfruta!')
        elif cmd in ["!prime", "!suscri"]:
            await message.channel.send('Suscribete GRATIS con Twitch Prime!')
        elif cmd in ["!festero", "!fiesta", "!animado"]:
            p = random.randint(0, 100)
            if p >= 85: frase = f"¡@{user} al {p}% de festero! ¡A ROMPERLA!"
            elif p >= 65: frase = f"@{user} al {p}%. ¡Sube volumen!"
            elif p >= 45: frase = f"@{user} al {p}%. ¡Sigue bailando!"
            else: frase = f"@{user} al {p}%... ¿Red Bull?"
            await message.channel.send(frase + suf)
        elif cmd in ["!vf", "!verdaderofalso"]:
            if vf_activo: await message.channel.send(f"Ya hay pregunta: {vf_pregunta}")
            else:
                vf_activo = True
                q, a = random.choice(VF)
                vf_pregunta, vf_respuesta = q, a
                await message.channel.send(f"¡VF! {vf_pregunta} (!v o !f){suf}")
        elif cmd in ["!v", "!verdadero", "!f", "!falso"]:
            if not vf_activo: await message.channel.send("No hay pregunta. Inicia con !vf")
            else:
                resp = "verdadero" if cmd in ["!v", "!verdadero"] else "falso"
                if resp == vf_respuesta: await message.channel.send(f"¡CORRECTO @{user}! Era {vf_respuesta}{suf}")
                else: await message.channel.send(f"Incorrecto @{user}. Era {vf_respuesta}{suf}")
                vf_activo = False
        elif cmd in ["!3enraya", "!tictactoe"]:
            if ttt_activo: await message.channel.send("Ya hay partida.")
            else:
                ttt_activo, ttt_x, ttt_o, ttt_turno = True, user, "", "X"
                ttt_tablero = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                await message.channel.send(f"@{user} inició 3enRaya! Otro escribe !unirse{suf}")
        elif cmd == "!unirse":
            if not ttt_activo or ttt_o or user == ttt_x: await message.channel.send("No puedes unirte.")
            else:
                ttt_o = user
                await message.channel.send(f"@{ttt_o} se unió como O. @{ttt_x} (X) tu turno: !mover [1-9]{suf}")
        elif cmd == "!mover":
            if not ttt_activo or user not in [ttt_x, ttt_o]: await message.channel.send("No es tu turno."); return
            if (ttt_turno == "X" and user != ttt_x) or (ttt_turno == "O" and user != ttt_o): await message.channel.send(f"No es tu turno. Le toca {'X' if ttt_turno == 'X' else 'O'}."); return
            if not arg or not arg.isdigit() or not (1 <= int(arg) <= 9): await message.channel.send("Usa número 1-9. Ej: !mover 5"); return
            pos = int(arg) - 1
            if ttt_tablero[pos] in ["X", "O"]: await message.channel.send("Casilla ocupada."); return
            ttt_tablero[pos] = ttt_turno
            ganar = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
            ganador = next((ttt_tablero[a] for a, b, c in ganar if ttt_tablero[a] == ttt_tablero[b] == ttt_tablero[c]), None)
            if not ganador and all(c in ["X", "O"] for c in ttt_tablero): ganador = "Empate"
            tab = f"{ttt_tablero[0]}|{ttt_tablero[1]}|{ttt_tablero[2]} - {ttt_tablero[3]}|{ttt_tablero[4]}|{ttt_tablero[5]} - {ttt_tablero[6]}|{ttt_tablero[7]}|{ttt_tablero[8]}"
            if ganador == "Empate": await message.channel.send(f"¡Empate! {tab}{suf}"); ttt_activo = False
            elif ganador: await message.channel.send(f"¡GANADOR @{ttt_x if ganador == 'X' else ttt_o}! {tab}{suf}"); ttt_activo = False
            else:
                ttt_turno = "O" if ttt_turno == "X" else "X"
                await message.channel.send(f"Turno {ttt_turno} (@{ttt_x if ttt_turno == 'X' else ttt_o}). !mover [1-9]. {tab}{suf}")
        elif cmd == "!ahorcado":
            if not ahorcado_activo:
                ahorcado_activo = True
                ahorcado_palabra = random.choice(AHORCADO)
                ahorcado_adivinadas, ahorcado_intentos = set(), 6
                await message.channel.send(f"@{user} inició AHORCADO! Palabra: {' '.join(['_' for _ in ahorcado_palabra])} | !letra [a-z]{suf}")
        elif cmd == "!letra":
            if not ahorcado_activo or not arg or len(arg) != 1 or not arg.isalpha(): await message.channel.send("Escribe UNA letra. Ej: !letra a"); return
            letra = arg.lower()
            if letra in ahorcado_adivinadas: await message.channel.send(f"Ya probaste '{letra}'"); return
            ahorcado_adivinadas.add(letra)
            if letra in ahorcado_palabra:
                if all(l in ahorcado_adivinadas for l in ahorcado_palabra):
                    await message.channel.send(f"¡GANÓ @{user}! Era '{ahorcado_palabra}'{suf}"); ahorcado_activo = False
                else:
                    estado = " ".join([l if l in ahorcado_adivinadas else "_" for l in ahorcado_palabra])
                    await message.channel.send(f"¡Bien! '{letra}' está. {estado}{suf}")
            else:
                ahorcado_intentos -= 1
                if ahorcado_intentos <= 0: await message.channel.send(f"¡PERDISTE @{user}! Era '{ahorcado_palabra}'{suf}"); ahorcado_activo = False
                else: await message.channel.send(f"'{letra}' NO está. Intentos: {ahorcado_intentos}{suf}")
        elif cmd == "!numero":
            if not num_activo:
                num_activo, num_secreto = True, random.randint(1, 100)
                await message.channel.send(f"@{user} inició 'Adivina el Número' (1-100). !adivinanum [n]{suf}")
        elif cmd == "!adivinanum":
            if not num_activo or not arg: await message.channel.send("Inicia con !numero o escribe número."); return
            try:
                n = int(arg)
                if n == num_secreto: await message.channel.send(f"¡@{user} ACERTÓ! Era {num_secreto}{suf}"); num_activo = False
                elif n < num_secreto: await message.channel.send(f"@{user}: MÁS ALTO que {n}{suf}")
                else: await message.channel.send(f"@{user}: MÁS BAJO que {n}{suf}")
            except: await message.channel.send("Número válido.")
        elif cmd in ["!ppt", "!piedra"]:
            opciones = ["piedra", "papel", "tijera"]
            if not arg or arg.lower() not in opciones: await message.channel.send("Elige: piedra, papel o tijera. Ej: !ppt piedra"); return
            eu, eb = arg.lower(), random.choice(opciones)
            if eu == eb: res = f"Empate. Ambos {eu}."
            elif (eu == "piedra" and eb == "tijera") or (eu == "papel" and eb == "piedra") or (eu == "tijera" and eb == "papel"): res = f"¡@{user} GANA! {eu} vence a {eb}."
            else: res = f"¡Gana el bot! {eb} vence a {eu}."
            await message.channel.send(f"@{user}: {eu} vs Bot: {eb}. {res}{suf}")
        elif cmd == "!dado": await message.channel.send(f"@{user} tiró: {random.randint(1, 6)}{suf}")
        elif cmd == "!moneda": await message.channel.send(f"@{user}: {random.choice(['CARA', 'CRUZ'])}{suf}")
        elif cmd in ["!bola", "!bola8"]:
            if not arg: await message.channel.send("Haz pregunta. Ej: !bola iré a rave?"); return
            await message.channel.send(f"@{user}: {random.choice(BOLA)}{suf}")
        elif cmd in ["!reto", "!verdad"]:
            tipo = random.choice(["RETO", "VERDAD"])
            cont = random.choice(RETOS) if tipo == "RETO" else random.choice(VERDADES)
            await message.channel.send(f"@{user} te toca {tipo}: {cont}{suf}")
        elif cmd == "!trivia":
            if not trivia_on:
                qs = [{"p":"BPM techno?","r":"130"},{"p":"Ciudad techno?","r":"detroit"},{"p":"House+techno?","r":"tech house"}]
                q = random.choice(qs)
                trivia_on, trivia_r = True, q["r"]
                await message.channel.send(f"TRIVIA! {q['p']} (!respuesta){suf}")
        elif cmd == "!respuesta":
            if not trivia_on or not arg: await message.channel.send("Inicia con !trivia o escribe respuesta."); return
            if arg.lower().strip() == trivia_r: await message.channel.send(f"¡CORRECTO @{user}!{suf}"); trivia_on = False
            else: await message.channel.send(f"Incorrecto @{user}.{suf}")
        elif cmd == "!ruleta": await message.channel.send(f"¡Ruleta! Género: {random.choice(['Techno','House','Trance','Drum&Bass','Dubstep','Hardstyle','Remember'])}. ¡Pon canción!{suf}")
        elif cmd == "!bpm":
            bpm_n = random.randint(120, 174)
            await message.channel.send(f"Adivina BPM (120-174): !adivinarbpm [n]{suf}")
        elif cmd == "!adivinarbpm":
            if bpm_n is None or not arg: await message.channel.send("Inicia con !bpm o escribe número."); return
            try:
                n = int(arg)
                if n == bpm_n: await message.channel.send(f"¡EXACTO @{user}! Era {bpm_n} BPM.{suf}"); bpm_n = None
                elif abs(n - bpm_n) <= 5: await message.channel.send(f"¡Muy cerca @{user}! A {abs(n-bpm_n)} BPM.{suf}")
                else: await message.channel.send(f"Frío @{user}.{suf}")
            except: await message.channel.send("Número válido.")

if __name__ == '__main__':
    Bot().run()
