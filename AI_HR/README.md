# AI HR System

Система для HR-интервью с распознаванием речи и анализом резюме.

## Возможности

-  **Распознавание речи** - real-time обработка аудио с помощью Vosk
-  **Анализ резюме** - сравнение кандидатов с требованиями вакансии
-  **AI обработка** - улучшение текста и анализ с помощью Claude 3.5 Sonnet

## Быстрый старт

1. **Установка зависимостей:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Настройка API ключа:**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

3. **Запуск backend:**
```bash
python main.py
```

4. **Запуск frontend:**
```bash
cd ../frontend-react
npm install
npm start
```

5. **Открыть приложение:**
```
http://localhost:3000
```

## Технологии

- **Backend:** FastAPI, Vosk, OpenRouter API
- **Frontend:** React, TypeScript
- **AI:** Claude 3.5 Sonnet для анализа резюме