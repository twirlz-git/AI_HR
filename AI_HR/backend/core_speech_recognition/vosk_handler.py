import asyncio
import time
import json
import logging
import vosk
import numpy as np
from fastapi import WebSocket
from .base_stt import BaseSTT
from .openrouter_processor import OpenRouterProcessor
from .hr_interviewer import HRInterviewer
from . import settings

logger = logging.getLogger(__name__)

class VoskHandler(BaseSTT):
    def __init__(self, model_path=settings.MODEL_PATH, chunk_duration=settings.CHUNK_DURATION):
        super().__init__(chunk_duration)
        self.model_path = model_path
        self.vosk_model = None
        self.openrouter = OpenRouterProcessor()
        self.hr_interviewer = HRInterviewer()
        self.last_speech_time = time.time()  # Инициализируем время последней речи
        # Gate that enables silence-based auto finalize. True for Q1, disabled after finalize
        self.silence_gate_enabled = True
        
    async def initialize(self):
        import os
        if not os.path.exists(self.model_path):
            logger.error(f"Model not found: {self.model_path}")
            return False
        
        self.vosk_model = vosk.Model(self.model_path)
        logger.info("Vosk model loaded")
        return True
    
    async def process_stream(self, websocket: WebSocket):
        logger.info(f"Starting process_stream, session_active={self.session_active}")
        last_processed_time = time.time()
        self.last_speech_time = time.time()  # Используем атрибут класса 
        
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
                                
                                # Накапливаем для OpenRouter
                                if self.accumulated:
                                    self.accumulated += settings.TEXT_SEPARATOR + new_text
                                else:
                                    self.accumulated = new_text
                                
                                # Обновляем время последней речи
                                self.last_speech_time = current_time
                        
                        last_processed_time = current_time
                
                # Проверяем тишину для автоматической обработки
                silence_duration = current_time - self.last_speech_time
                # logger.debug(f"Checking silence: accumulated='{self.accumulated}', silence={silence_duration:.1f}s, interview_active={self.hr_interviewer.interview_active}")
                
                # Обработка молчания в интервью: 5 сек молчания → спиннер + обработка
                # Выполняется только если включен gate (активируется нажатием кнопки на 2+ вопросах)
                if (silence_duration >= settings.SILENCE_THRESHOLD and
                    self.hr_interviewer.interview_active and
                    self.silence_gate_enabled):
                    
                    logger.info(f"Silence detected ({settings.SILENCE_THRESHOLD}s), processing answer...")
                    logger.info(f"Sending processing_started message")

                    # Показываем спиннер
                    try:
                        await websocket.send_json({
                            "type": "processing_started",
                            "message": "Начинаем обработку ответа..."
                        })
                        logger.info(f"processing_started message sent")
                    except Exception as e:
                        logger.error(f"Error sending processing_started: {e}")
                        return
                    
                    # СРАЗУ обрабатываем ответ
                    interview_continues = await self.finalize_session(websocket)
                    
                    # Проверяем, завершилось ли интервью
                    if not interview_continues:
                        logger.info("Interview finished, exiting process_stream loop")
                        break
                    
                    # Сбрасываем состояние
                    self.accumulated = ""
                    self.segments = []
                    self.last_speech_time = time.time()
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await asyncio.sleep(1)
        
        logger.warning(f"process_stream loop exited! session_active={self.session_active}")
    
    
    async def finalize_session(self, websocket: WebSocket):
        """Финализация сессии - обработка ответа в HR интервью"""
        if self.accumulated and self.accumulated.strip():
            if self.hr_interviewer.interview_active:
                # Обрабатываем ответ в рамках интервью
                logger.info(f"Processing answer for question {self.hr_interviewer.current_question + 1}")
                result = await self.hr_interviewer.process_answer(self.accumulated)
                
                # Отправляем результат на фронтенд
                try:
                    await websocket.send_json(result)
                    logger.info("Answer processed, result sent")
                except Exception as e:
                    logger.error(f"Error sending result: {e}")
                    return
                
                # ВАЖНО: Сбрасываем состояние после обработки
                self.accumulated = ""
                self.last_speech_time = time.time()
                # Отключаем gate до явной активации с фронта для следующего вопроса
                self.silence_gate_enabled = False
                
                # НЕ ОСТАНАВЛИВАЕМ ОБРАБОТКУ - продолжаем слушать следующий ответ
                # self.stop_processing()
                
                # Возвращаем статус интервью
                return self.hr_interviewer.interview_active
        else:
            logger.info("No text to process")
            if self.hr_interviewer.interview_active:
                # Пользователь молчал - обрабатываем как пустой ответ
                logger.info("Processing silence as empty answer in interview")
                result = await self.hr_interviewer.process_answer("Кандидат промолчал")
                try:
                    await websocket.send_json(result)
                    logger.info("Silence processed, result sent")
                except Exception as e:
                    logger.error(f"Error sending silence result: {e}")
                    return
                
                # ВАЖНО: Сбрасываем состояние после обработки
                self.accumulated = ""
                self.last_speech_time = time.time()
                # Отключаем gate до явной активации с фронта для следующего вопроса
                self.silence_gate_enabled = False
                
                # НЕ ОСТАНАВЛИВАЕМ ОБРАБОТКУ - продолжаем слушать следующий ответ
                # self.stop_processing()
                
                # Возвращаем статус интервью
                return self.hr_interviewer.interview_active
        
        # Если не было обработки, интервью продолжается
        return True
    
    def reset_speech_timer(self):
        """Reset speech timer to current time"""
        self.last_speech_time = time.time()
    
    def stop_processing(self):
        """Stop current processing session"""
        self.session_active = False
        logger.info("Запись остановлена")
    
    def is_model_loaded(self):
        """Проверка загружена ли модель"""
        return self.vosk_model is not None