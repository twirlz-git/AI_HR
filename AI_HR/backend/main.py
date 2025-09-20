import asyncio
import json
import logging
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from core_speech_recognition.vosk_handler import VoskHandler
import core_speech_recognition.settings as settings
from pydantic import BaseModel
from typing import List, Dict, Optional
from resume_analysis import (
    init_llm_client,
    analyze_candidate as _analyze_candidate,
    analyze_job as _analyze_job,
    analyze_matching as _analyze_matching,
    parse_upload_to_text as _parse_upload_to_text,
)

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Создаем приложение
app = FastAPI(title="Speech Recognition API", description="Real-time speech-to-text with Vosk")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"], 
    allow_methods=["*"], 
    allow_headers=["*"],
    allow_credentials=True
)

# Инициализируем Vosk обработчик
vosk_handler = VoskHandler()

init_llm_client(settings.OPENROUTER_API_KEY)



class AnalysisRequest(BaseModel):
    job_description: str
    resumes: List[str]

@app.on_event("startup")
async def startup():
    """Инициализация при запуске приложения"""
    if not await vosk_handler.initialize():
        logger.error("Failed to initialize Vosk STT")
        exit(1)

@app.get("/health")
async def health():
    """Проверка состояния сервера"""
    return {
        "status": "ok", 
        "message": "Server is running",
        "vosk_enabled": vosk_handler.is_model_loaded()
    }

@app.get("/")
async def root():
    """API status"""
    return {"status": "AI HR Backend is running", "version": "1.0"}


@app.post("/analyze_resumes")
async def analyze_resumes(req: AnalysisRequest):
    """Analyze job description against multiple resumes and return name+score list."""
    try:
        logger.info(f"Analyzing {len(req.resumes)} resumes against job description")
        
        if not req.job_description or not req.resumes:
            logger.warning("Empty job description or resumes list")
            return {"results": [], "error": "Job description and resumes are required"}
        
        if not settings.OPENROUTER_API_KEY:
            logger.error("OpenRouter API key not configured")
            return {"results": [], "error": "API key not configured"}
        
        job = _analyze_job(req.job_description)
        results: List[Dict] = []
        
        for i, cv_text in enumerate(req.resumes):
            if not cv_text:
                continue
            try:
                logger.info(f"Processing resume {i+1}/{len(req.resumes)}")
                cand = _analyze_candidate(cv_text)
                match = _analyze_matching(job, cand)
                name = cand.get("candidate_name") or f"Резюме {i+1}"
                score = match.get("score", 0.0)
                results.append({"name": name, "score": score})
                logger.info(f"Resume {i+1} processed: {name} - score: {score}")
            except Exception as e:
                logger.error(f"Error processing resume {i+1}: {e}")
                results.append({"name": f"Резюме {i+1} (Ошибка)", "score": 0.0})
        
        # sort by score desc
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        logger.info(f"Analysis completed. {len(results)} results returned")
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Error in analyze_resumes: {e}")
        return {"results": [], "error": str(e)}


@app.post("/upload_analyze")
async def upload_analyze(job: UploadFile = File(...), resumes: List[UploadFile] = File(...)):
    """Upload job description file and multiple resume files. Returns name+score list."""
    try:
        logger.info(f"Analyzing uploaded files: job={job.filename}, resumes={len(resumes)} files")
        
        if not settings.OPENROUTER_API_KEY:
            logger.error("OpenRouter API key not configured")
            return {"results": [], "error": "API key not configured"}
        
        job_text = _parse_upload_to_text(job)
        if not job_text:
            logger.warning(f"Could not extract text from job file: {job.filename}")
            return {"results": [], "error": f"Could not extract text from job file: {job.filename}"}
        
        job_info = _analyze_job(job_text)
        out: List[Dict] = []
        
        for i, f in enumerate(resumes or []):
            try:
                logger.info(f"Processing resume file {i+1}/{len(resumes)}: {f.filename}")
                cv_text = _parse_upload_to_text(f)
                if not cv_text:
                    logger.warning(f"Could not extract text from resume file: {f.filename}")
                    out.append({"name": f"{f.filename} (Error)", "score": 0.0})
                    continue
                
                cand = _analyze_candidate(cv_text)
                match = _analyze_matching(job_info, cand)
                name = f.filename
                score = match.get("score", 0.0)
                out.append({"name": name, "score": score})
                logger.info(f"Resume file {i+1} processed: {name} - score: {score}")
                
            except Exception as e:
                logger.error(f"Error processing resume file {i+1} ({f.filename}): {e}")
                out.append({"name": f"{f.filename} (Error)", "score": 0.0})
        
        out.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        logger.info(f"File analysis completed. {len(out)} results returned")
        return {"results": out}
        
    except Exception as e:
        logger.error(f"Error in upload_analyze: {e}")
        return {"results": [], "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для real-time обработки аудио"""
    await websocket.accept()
    vosk_handler.session_active = True
    
    if not vosk_handler.start_ffmpeg_stream():
        await websocket.close(code=1000, reason="Failed to start FFmpeg")
        return
    
    # НЕ запускаем process_stream сразу - только при команде start_recording
    processing_task = None
    
    try:
        while True:
            # Получаем данные от клиента
            data = await websocket.receive()
            logger.debug(f"Raw WebSocket data: type={data.get('type')}, has_bytes={'bytes' in data}, has_text={'text' in data}")
            
            # Проверяем тип сообщения
            if data["type"] == "websocket.disconnect":
                logger.info("Client disconnected")
                break
            elif data["type"] == "websocket.receive":
                if "bytes" in data:
                    # Отправляем аудио данные в FFmpeg
                    if vosk_handler.ffmpeg_process and vosk_handler.ffmpeg_process.stdin:
                        try:
                            vosk_handler.ffmpeg_process.stdin.write(data["bytes"])
                            vosk_handler.ffmpeg_process.stdin.flush()
                        except Exception as e:
                            logger.error(f"Error writing to FFmpeg: {e}")
                elif "text" in data:
                    # Обрабатываем текстовые команды
                    try:
                        message = json.loads(data["text"])
                        logger.info(f"Received message: {message}")
                        if message.get("action") == "start_interview":
                            logger.info("Starting HR interview")
                            result = vosk_handler.hr_interviewer.start_interview()
                            await websocket.send_json(result)
                        elif message.get("action") == "start_recording":
                            logger.info("Запись включена")
                            logger.info(f"Interview active: {vosk_handler.hr_interviewer.interview_active}, Question {vosk_handler.hr_interviewer.current_question}/{vosk_handler.hr_interviewer.total_questions}")
                            
                            # Только для первого запуска
                            if not processing_task or processing_task.done():
                                # Активируем сессию
                                vosk_handler.session_active = True
                                
                                # Очищаем буферы для нового сеанса записи
                                vosk_handler.pcm_buffer.clear()
                                vosk_handler.accumulated = ""
                                vosk_handler.segments = []
                                
                                # Запускаем чтение PCM потока
                                threading.Thread(target=vosk_handler.read_pcm_stream, daemon=True).start()
                                # Запускаем обработку потока
                                processing_task = asyncio.create_task(vosk_handler.process_stream(websocket))
                            
                            if not vosk_handler.hr_interviewer.interview_active:
                                logger.warning("Интервью завершено! Кнопка записи больше не работает.")
                        elif message.get("action") == "reset_timer":
                            vosk_handler.reset_speech_timer()
                        elif message.get("action") == "activate_listening":
                            logger.info("🎤 Активируем прослушивание для следующего вопроса")
                            vosk_handler.reset_speech_timer()  # Сбрасываем таймер при активации
                            # Включаем gate: теперь 5 сек молчания снова активируют обработку
                            vosk_handler.silence_gate_enabled = True
                    except Exception as e:
                        logger.error(f"Error processing text message: {e}")
                        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Обрабатываем финальный текст перед закрытием
        await vosk_handler.finalize_session(websocket)
        
        # Очистка ресурсов
        try:
            if processing_task and not processing_task.done():
                processing_task.cancel()
        except Exception as e:
            logger.warning(f"Failed to cancel processing task: {e}")
        vosk_handler.session_active = False
        
        # В режиме интервью не сбрасываем сессию полностью
        if not vosk_handler.hr_interviewer.interview_active:
            vosk_handler.reset_session()
        else:
            # Только очищаем текущие сегменты, но сохраняем состояние интервью
            vosk_handler.segments.clear()
            vosk_handler.accumulated = ""
        
        vosk_handler.stop_ffmpeg_stream()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)