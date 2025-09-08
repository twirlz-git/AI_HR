# 🎤 Speech Combined - HR Interview System

1. **Установка зависимостей:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

2. **Скачивание модели Vosk:**
```bash
cd backend
wget https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip
unzip vosk-model-ru-0.10.zip -d models/
```

3. **Настройка API ключа:**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

4. **Запуск сервера:**
```bash
python main.py
```

5. **Открыть в браузере:**
```
http://localhost:8007
```

## ⚙️ Настройки

Основные настройки в `backend/settings.py`:
- `SILENCE_THRESHOLD = 5.0` - время тишины для обработки (сек)
- `OPENROUTER_MODEL` - модель AI для обработки
- `HOST` и `PORT` - настройки сервера
