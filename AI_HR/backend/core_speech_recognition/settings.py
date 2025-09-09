import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Audio Settings
SAMPLE_RATE = 16000  # Hz - частота дискретизации
CHUNK_DURATION = 3.0  # секунд - интервал обработки
BUFFER_DURATION = 30  # секунд - размер буфера
PCM_CHUNK_SIZE = 1024  # байт - размер чанка PCM

# Audio Processing
AUDIO_AMPLIFICATION_THRESHOLD = 16000  # усиление слабого сигнала до этого уровня
MAX_OVERLAP_WORDS = 5  # максимум слов для дедупликации
SILENCE_THRESHOLD = 6.0  # секунд тишины для автоматической обработки ответа
PROCESSING_INTERVAL = 1.0  # секунд - интервал отправки результатов
SILENCE_TIMEOUT = 3.0  # секунд - таймаут молчания для финализации

# Model Settings
MODEL_PATH = os.getenv("MODEL_PATH", "./models/vosk-model-ru-0.10")  # путь к модели Vosk

# Server Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8007"))

# Frontend Settings
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "../frontend/vosk_test.html")

# FFmpeg Settings
FFMPEG_ARGS = [
    'ffmpeg',
    '-f', 'webm',
    '-i', 'pipe:0',
    '-ar', str(SAMPLE_RATE),
    '-ac', '1',
    '-f', 's16le',
    'pipe:1'
]

# Text Processing
TEXT_SEPARATOR = " | "  # разделитель между сегментами текста

# Logging
LOG_LEVEL = "INFO"

# OpenRouter Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"
OPENROUTER_ENABLED = True
OPENROUTER_PROMPT = """Исправь этот текст из распознавания речи для HR-интервью:
- Убери повторы, паузы и ошибки распознавания
- Сделай текст профессиональным и структурированным
- Отвечай только исправленным текстом без комментариев

Текст: {text}"""
