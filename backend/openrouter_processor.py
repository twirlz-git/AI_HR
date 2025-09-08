import asyncio
import logging
from openai import AsyncOpenAI
import settings

logger = logging.getLogger(__name__)

class OpenRouterProcessor:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.model = settings.OPENROUTER_MODEL
        logger.info("OpenRouter initialized")
    
    async def process_text(self, text: str) -> str:
        """Process text through OpenRouter API"""
        if not text or not text.strip():
            return text
        
        if not settings.OPENROUTER_ENABLED:
            logger.info("OpenRouter disabled, returning original text")
            return text
        
        try:
            prompt = settings.OPENROUTER_PROMPT.format(text=text)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            improved_text = response.choices[0].message.content.strip()
            logger.info(f"OpenRouter processed text: {len(text)} -> {len(improved_text)} chars")
            return improved_text
            
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return text
    
    async def generate_interview_question(self, question_number: int, previous_answers: list = None) -> str:
        """Generate HR interview question"""
        try:
            context = ""
            if previous_answers:
                context = f"\nПредыдущие ответы кандидата:\n" + "\n".join([
                    f"Вопрос {i+1}: {ans}" for i, ans in enumerate(previous_answers)
                ])
            
            prompt = f"""Ты HR-специалист проводящий интервью. Задай {question_number}-й вопрос для собеседования на позицию разработчика.
            
Требования:
- Вопрос должен быть профессиональным и релевантным
- Избегай слишком технических деталей
- Фокусируйся на опыте, мотивации и soft skills
- Вопрос должен быть коротким и понятным
{context}

Ответь только текстом вопроса без дополнительных комментариев."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            question = response.choices[0].message.content.strip()
            return question
            
        except Exception as e:
            logger.error(f"OpenRouter question generation error: {e}")
            # Fallback questions
            fallback_questions = [
                "Расскажите о себе и своем опыте работы",
                "Почему вы хотите работать в нашей компании?",
                "Какие ваши сильные и слабые стороны?",
                "Расскажите о сложном проекте, над которым вы работали",
                "Как вы справляетесь со стрессом и дедлайнами?"
            ]
            return fallback_questions[min(question_number - 1, len(fallback_questions) - 1)]
    
    async def evaluate_answer(self, question: str, answer: str) -> dict:
        """Evaluate interview answer"""
        try:
            prompt = f"""Оцени ответ кандидата на вопрос интервью как HR-специалист.

Вопрос: {question}
Ответ: {answer}

Дай оценку по критериям:
1. Полнота ответа (1-10)
2. Релевантность (1-10) 
3. Профессионализм (1-10)
4. Коммуникативные навыки (1-10)

Формат ответа (JSON):
{{
    "scores": {{
        "completeness": 8,
        "relevance": 7,
        "professionalism": 9,
        "communication": 8
    }},
    "overall_score": 8.0,
    "feedback": "Краткая обратная связь на русском языке"
}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            logger.error(f"OpenRouter evaluation error: {e}")
            return {
                "scores": {
                    "completeness": 5,
                    "relevance": 5,
                    "professionalism": 5,
                    "communication": 5
                },
                "overall_score": 5.0,
                "feedback": "Не удалось оценить ответ"
            }
