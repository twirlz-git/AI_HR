import asyncio
import time
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import vosk
import numpy as np
from base_stt import BaseSTT
from openrouter_processor import OpenRouterProcessor
from hr_interviewer import HRInterviewer
import settings

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

class CleanVoskSTT(BaseSTT):
    def __init__(self, model_path=settings.MODEL_PATH, chunk_duration=settings.CHUNK_DURATION):
        super().__init__(chunk_duration)
        self.model_path = model_path
        self.vosk_model = None
        self.openrouter = OpenRouterProcessor()
        self.hr_interviewer = HRInterviewer()
        # Убираем автоматическую обработку по таймеру
        
    async def initialize(self):
        import os
        if not os.path.exists(self.model_path):
            logger.error(f"Model not found: {self.model_path}")
            return False
        
        self.vosk_model = vosk.Model(self.model_path)
        logger.info("Vosk model loaded")
        return True
    
    async def process_stream(self, websocket: WebSocket):
        last_processed_time = time.time()
        last_speech_time = time.time()
        
        while self.session_active:
            try:
                current_time = time.time()
                
                if (current_time - last_processed_time) >= self.chunk_duration:
                    chunk_samples = int(self.sample_rate * self.chunk_duration)
                    
                    if len(self.pcm_buffer) >= chunk_samples:
                        audio_data = list(self.pcm_buffer)[-chunk_samples:]
                        
                        recognizer = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
                        
                        audio_array = np.array(audio_data)
                        max_val = np.max(np.abs(audio_array))
                        
                        if max_val > 0:
                            if max_val < settings.AUDIO_AMPLIFICATION_THRESHOLD:
                                amplification = settings.AUDIO_AMPLIFICATION_THRESHOLD / max_val
                                audio_array = audio_array * amplification
                        
                        audio_bytes = (audio_array).astype(np.int16).tobytes()
                        
                        recognizer.AcceptWaveform(audio_bytes)
                        final_result = json.loads(recognizer.FinalResult())
                        
                        text = final_result.get("text", "").strip()
                        
                        if text:
                            new_text = self.deduplicate_text(text, self.segments)
                            
                            if new_text:
                                segment = {
                                    "text": new_text,
                                    "timestamp": current_time,
                                    "duration": self.chunk_duration,
                                    "confidence": final_result.get("confidence", 0.8)
                                }
                                
                                self.segments.append(segment)
                                
                                # Отправляем только новый сегмент
                                await self.send_result(websocket, segment, "vosk")
                                print(f"✅ {new_text}")
                                
                                # Накапливаем для OpenRouter
                                if self.accumulated:
                                    self.accumulated += settings.TEXT_SEPARATOR + new_text
                                else:
                                    self.accumulated = new_text
                                
                                # Обновляем время последней речи
                                last_speech_time = current_time
                        
                        last_processed_time = current_time
                
                # Проверяем тишину для автоматической обработки
                if (self.accumulated and 
                    (current_time - last_speech_time) >= settings.SILENCE_THRESHOLD and
                    self.hr_interviewer.interview_active):
                    
                    print(f"🔇 Обнаружена тишина {settings.SILENCE_THRESHOLD} сек, обрабатываем ответ...")
                    
                    # Отправляем сообщение о начале обработки
                    await websocket.send_json({
                        "type": "processing_started",
                        "message": "Начинаем обработку ответа..."
                    })
                    
                    await self.finalize_session(websocket)
                    
                    # Сбрасываем только накопленный текст в режиме интервью
                    self.accumulated = ""
                    self.segments = []
                    last_speech_time = current_time  # Сбрасываем таймер тишины
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await asyncio.sleep(1)
    
    async def process_with_openrouter(self, websocket: WebSocket):
        """Обработка накопленного текста через OpenRouter"""
        try:
            if self.accumulated:
                print("🤖 Обрабатываем текст через OpenRouter...")
                improved = await self.openrouter.process_text(self.accumulated)
                if improved != self.accumulated:
                    self.improved_text = improved
                    # Отправляем улучшенный текст
                    await websocket.send_json({
                        "type": "improved",
                        "original_text": self.accumulated,
                        "improved_text": improved,
                        "segments_count": len(self.segments)
                    })
                    print(f"✨ OpenRouter результат: {improved}")
                else:
                    print("📝 OpenRouter: текст не требует улучшения")
        except Exception as e:
            logger.error(f"OpenRouter processing error: {e}")
    
    async def finalize_session(self, websocket: WebSocket):
        """Финализация сессии - обработка ответа в HR интервью"""
        if self.accumulated and self.accumulated.strip():
            if self.hr_interviewer.interview_active:
                # Обрабатываем ответ в рамках интервью
                print(f"💬 Обрабатываем ответ на вопрос {self.hr_interviewer.current_question + 1}")
                result = await self.hr_interviewer.process_answer(self.accumulated)
                
                # Отправляем результат на фронтенд
                await websocket.send_json(result)
                print(f"✅ Ответ обработан, результат отправлен")
            else:
                # Обычная обработка через OpenRouter
                await self.process_with_openrouter(websocket)
        else:
            print("📝 Нет текста для обработки")

# Создаем приложение
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

vosk_stt = CleanVoskSTT()

@app.on_event("startup")
async def startup():
    if not await vosk_stt.initialize():
        exit(1)

@app.get("/")
async def root():
    import os
    return FileResponse(os.path.join(os.path.dirname(__file__), settings.FRONTEND_PATH))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vosk_stt.session_active = True
    
    if not vosk_stt.start_ffmpeg_stream():
        await websocket.close()
        return
    
    import threading
    threading.Thread(target=vosk_stt.read_pcm_stream, daemon=True).start()
    processing_task = asyncio.create_task(vosk_stt.process_stream(websocket))
    
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    if vosk_stt.ffmpeg_process and vosk_stt.ffmpeg_process.stdin:
                        vosk_stt.ffmpeg_process.stdin.write(message["bytes"])
                        vosk_stt.ffmpeg_process.stdin.flush()
                elif "text" in message:
                    # Обрабатываем текстовые сообщения
                    text_data = json.loads(message["text"])
                    
                    if text_data.get("action") == "start_interview":
                        print("🎤 Начинаем HR интервью")
                        question_data = vosk_stt.hr_interviewer.start_interview()
                        await websocket.send_json(question_data)
                        
            elif message["type"] == "websocket.disconnect":
                break
    except:
        pass
    finally:
        # Обрабатываем финальный текст через OpenRouter перед закрытием
        await vosk_stt.finalize_session(websocket)
        
        # В режиме интервью не сбрасываем сессию полностью
        if not vosk_stt.hr_interviewer.interview_active:
            vosk_stt.reset_session()
        
        processing_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
