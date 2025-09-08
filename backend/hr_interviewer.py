import asyncio
import logging
import settings
from openrouter_processor import OpenRouterProcessor

logger = logging.getLogger(__name__)

class HRInterviewer:
    def __init__(self):
        self.openrouter = OpenRouterProcessor()
        self.current_question = 0
        self.initial_questions = [
            "Расскажите о себе и почему вы заинтересованы в этой позиции?",
            "Какой у вас опыт работы и какие ключевые навыки вы можете предложить?", 
            "Как вы видите свое развитие в нашей компании и какие у вас карьерные цели?"
        ]
        self.conversation_history = []
        self.interview_active = False
        self.total_questions = 3
    
    def start_interview(self):
        """Начинает интервью"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = True
        return self.get_current_question()
    
    def get_current_question(self):
        """Возвращает текущий вопрос"""
        if self.current_question >= self.total_questions:
            return self.finish_interview()
            
        # Используем заготовленные вопросы если они есть
        if self.current_question < len(self.initial_questions):
            question = self.initial_questions[self.current_question]
        else:
            # Для дополнительных вопросов (если total_questions > len(initial_questions))
            question = "Дополнительный вопрос будет сгенерирован"
            
        return {
            "type": "question",
            "question_number": self.current_question + 1,
            "total_questions": self.total_questions,
            "question": question
        }
    
    async def process_answer(self, answer_text: str):
        """Обрабатывает ответ кандидата"""
        if not self.interview_active or self.current_question >= self.total_questions:
            return {"type": "error", "message": "Интервью не активно"}
        
        # 1. Улучшаем ответ через OpenRouter
        improved_answer = await self.openrouter.process_text(answer_text)
        
        # 2. Добавляем в историю диалога
        # Берем текущий вопрос из заготовленных
        current_q = self.initial_questions[self.current_question] if self.current_question < len(self.initial_questions) else "Сгенерированный вопрос"
        
        self.conversation_history.append({
            "question": current_q,
            "raw_answer": answer_text,
            "improved_answer": improved_answer
        })
        
        # 3. Переходим к следующему вопросу
        self.current_question += 1
        
        if self.current_question < self.total_questions:
            # 4. Генерируем следующий вопрос на основе истории
            next_question_text = await self.generate_next_question()
            
            next_question = {
                "type": "question",
                "question_number": self.current_question + 1,
                "total_questions": self.total_questions,
                "question": next_question_text
            }
            
            return {
                "type": "answer_processed",
                "improved_answer": improved_answer,
                "next_question": next_question
            }
        else:
            # Интервью завершено
            return await self.finish_interview()
    
    async def generate_next_question(self):
        """Генерирует следующий вопрос на основе истории диалога"""
        # Создаем контекст из истории
        history_context = "История беседы:\n"
        for i, entry in enumerate(self.conversation_history, 1):
            history_context += f"Вопрос {i}: {entry['question']}\n"
            history_context += f"Ответ: {entry['improved_answer']}\n\n"
        
        # Промпт для генерации следующего вопроса
        question_prompt = f"""Ты HR-интервьюер. На основе истории беседы задай следующий логичный вопрос для собеседования.

{history_context}

Требования:
- Вопрос должен быть связан с предыдущими ответами
- Углубляй тему или переходи к новым аспектам
- Это вопрос {self.current_question + 1} из {self.total_questions}
- Вопрос должен быть профессиональным и релевантным для HR-интервью
- Отвечай только текстом вопроса, без комментариев

Следующий вопрос:"""

        next_question = await self.openrouter.generate_interview_question(
            self.current_question + 1, 
            [entry['improved_answer'] for entry in self.conversation_history]
        )
        return next_question.strip()
    
    async def finish_interview(self):
        """Завершает интервью и генерирует итоговый отчет"""
        self.interview_active = False
        
        if not self.conversation_history:
            return {
                "type": "interview_finished",
                "message": "Интервью завершено без ответов"
            }
        
        # Создаем итоговый отчет
        interview_summary = self.create_interview_summary()
        
        # Генерируем оценку через OpenRouter
        evaluation_prompt = f"""Проанализируй это HR-интервью и дай краткую оценку кандидата:

{interview_summary}

Оцени:
- Коммуникативные навыки
- Профессиональный опыт  
- Мотивацию
- Общее впечатление

Дай краткую рекомендацию (2-3 предложения)."""

        evaluation = await self.openrouter.process_text(evaluation_prompt)
        
        return {
            "type": "interview_finished",
            "summary": interview_summary,
            "evaluation": evaluation,
            "total_answers": len(self.conversation_history)
        }
    
    def create_interview_summary(self):
        """Создает краткое резюме интервью"""
        summary = "=== ИТОГИ HR-ИНТЕРВЬЮ ===\n\n"
        
        for i, entry in enumerate(self.conversation_history, 1):
            summary += f"Вопрос {i}: {entry['question']}\n"
            summary += f"Ответ: {entry['improved_answer']}\n\n"
        
        return summary
    
    def reset_interview(self):
        """Сбрасывает состояние интервью"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = False
