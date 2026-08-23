import os
import random
import time
import asyncio
import traceback
import json
import http.server
import socketserver
import threading
from twitchio.ext import commands
from openai import OpenAI

# ==========================================
# SERVIDOR HTTP SIMPLE PARA RAILWAY
# ==========================================
PORT = int(os.environ.get("PORT", 8080))

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        return  # Desactiva los logs HTTP repetitivos en la consola

def run_server():
    try:
        with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
            print(f"[WEB] Servidor HTTP activo en el puerto {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[WEB] Error en servidor HTTP: {e}")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
