#!/usr/bin/env python3
"""
Простой HTTP-сервер для тестирования приложения.
Запустите этот скрипт и откройте http://localhost:8080 в браузере.
"""
import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).parent

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        # Добавляем CORS заголовки для локальной разработки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def run_server():
    print(f" Запуск сервера на http://localhost:{PORT}")
    print(f"📁 Директория: {DIRECTORY}")
    print(f"\n📄 Доступные файлы:")
    print(f"   - http://localhost:{PORT}/test-page.html (главное приложение)")
    print(f"   - http://localhost:{PORT}/knowledge-base-direct.html (база знаний)")
    print(f"   - http://localhost:{PORT}/lmstudio-diagnostic.html (диагностика)")
    print(f"\n⏹️  Для остановки нажмите Ctrl+C")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        # Автоматически открыть браузер
        webbrowser.open(f"http://localhost:{PORT}/test-page.html")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✅ Сервер остановлен")

if __name__ == "__main__":
    run_server()
