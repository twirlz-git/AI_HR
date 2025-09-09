import subprocess
import re
import logging
from collections import deque
from fastapi import WebSocket
import numpy as np
from . import settings

logger = logging.getLogger(__name__)

class BaseSTT:
    def __init__(self, chunk_duration=settings.CHUNK_DURATION):
        self.ffmpeg_process = None
        self.pcm_buffer = deque(maxlen=settings.SAMPLE_RATE * settings.BUFFER_DURATION)
        self.session_active = False
        self.sample_rate = settings.SAMPLE_RATE
        self.chunk_duration = chunk_duration
        self.segments = []
        self.accumulated = ""
        self.improved_text = ""  # Улучшенный текст от Gemini
        
    def start_ffmpeg_stream(self):
        try:
            self.ffmpeg_process = subprocess.Popen(
                settings.FFMPEG_ARGS,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            return True
        except:
            return False
    
    def stop_ffmpeg_stream(self):
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except:
                self.ffmpeg_process.kill()
    
    def read_pcm_stream(self):
        try:
            while self.session_active and self.ffmpeg_process:
                pcm_chunk = self.ffmpeg_process.stdout.read(settings.PCM_CHUNK_SIZE)
                if not pcm_chunk:
                    break
                self.pcm_buffer.extend(np.frombuffer(pcm_chunk, dtype=np.int16))
        except:
            pass
    
    def clean_russian_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'[^а-яёА-ЯЁ\d\s\.,!?\-]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def deduplicate_text(self, new_text: str, segments: list) -> str:
        if not segments or not new_text:
            return new_text
        
        last_text = segments[-1].get("text", "")
        new_words = new_text.split()
        last_words = last_text.split()
        max_overlap = min(len(new_words), len(last_words), settings.MAX_OVERLAP_WORDS)
        
        for i in range(max_overlap, 0, -1):
            if last_words[-i:] == new_words[:i]:
                return " ".join(new_words[i:])
        return new_text
    
    def reset_session(self):
        self.session_active = False
        self.segments = []
        self.accumulated = ""
        self.improved_text = ""
        self.pcm_buffer.clear()
        self.stop_ffmpeg_stream()
        
    async def send_result(self, websocket: WebSocket, segment: dict, engine: str):
        try:
            await websocket.send_json({
                "type": "result",
                "segment_text": segment["text"],
                "accumulated": self.accumulated.strip(),
                "timestamp": segment["timestamp"],
                "segment_id": len(self.segments),
                "confidence": segment.get("confidence", 0.9),
                "engine": engine
            })
        except:
            pass
