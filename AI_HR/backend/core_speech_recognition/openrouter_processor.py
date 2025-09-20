import asyncio
import logging
from openai import AsyncOpenAI
from . import settings
from .hr_prompts import HRPrompts

logger = logging.getLogger(__name__)

class OpenRouterProcessor:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        if self.api_key and self.api_key != "your_openrouter_api_key_here":
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )
            self.model = settings.OPENROUTER_MODEL
            logger.info("OpenRouter initialized")
        else:
            self.client = None
            logger.warning("OpenRouter API key not configured, using fallback mode")
    
    async def process_text(self, text: str) -> str:
        """Process text through OpenRouter API"""
        if not text or not text.strip():
            return text
        
        if not settings.OPENROUTER_ENABLED or not self.client:
            logger.info("OpenRouter disabled or not configured, returning original text")
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
            # logger.info(f"OpenRouter processed text: {len(text)} -> {len(improved_text)} chars")
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
            return HRPrompts.get_fallback_question(question_number)
    
    async def generate_hr_interaction(self, job_profile: str, conversation_history: list, current_topic: str = None, is_clarification: bool = False) -> str:
        """Generate HR interaction based on conversation history"""
        if not self.client:
            return "Следующий вопрос будет сгенерирован"
        
        try:
            context = ""
            previous_questions = [qa['question'] for qa in conversation_history]
            additional_instruction = ""
            
            # Topic-based instruction
            if current_topic:
                if is_clarification:
                    additional_instruction = f"**ВАЖНО:** Задай уточняющий вопрос по теме '{current_topic}'. Предыдущий ответ был неясным, нужно получить более конкретную информацию по этой теме."
                else:
                    additional_instruction = f"**ВАЖНО:** Задай вопрос по теме '{current_topic}'. Это новая тема интервью."
            
            if conversation_history:
                last_qa = conversation_history[-1]
                context = f"Предыдущий вопрос HR: {last_qa['question']}\nПоследний ответ кандидата: {last_qa['answer']}\n"

            stage = len(conversation_history)
            focus = HRPrompts.get_focus_area(stage, job_profile)
            
            import json
            system_prompt = HRPrompts.HR_INTERACTION_SYSTEM.format(
                job_profile=job_profile,
                previous_questions=json.dumps(previous_questions, ensure_ascii=False),
                focus=focus,
                additional_instruction=additional_instruction
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": HRPrompts.HR_INTERACTION_USER.format(context=context)}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenRouter HR interaction error: {e}")
            return "Расскажите подробнее о вашем опыте работы."

    async def evaluate_answer(self, question: str, answer: str, job_profile: str) -> dict:
        """Evaluate interview answer with new format"""
        if not self.client:
            return {"score": 50, "feedback": "Не удалось обработать оценку"}
        
        try:
            user_prompt = HRPrompts.ANSWER_EVALUATION_USER.format(
                job_profile=job_profile,
                question=question,
                answer=answer
            )
            
            messages = [
                {"role": "system", "content": HRPrompts.ANSWER_EVALUATION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=120,
                temperature=0.2
            )
            
            response_text = response.choices[0].message.content.strip()
            try:
                json_part = response_text[response_text.find('{'):response_text.rfind('}')+1]
                import json
                return json.loads(json_part)
            except (json.JSONDecodeError, IndexError):
                return {"score": 0, "feedback": "Не удалось обработать оценку. Ответ мог быть нерелевантным."}
            
        except Exception as e:
            logger.error(f"OpenRouter evaluation error: {e}")
            return {"score": 0, "feedback": "Не удалось обработать оценку"}

    async def generate_final_feedback(self, conversation_history: list, job_profile: str) -> str:
        """Generate final interview feedback"""
        if not self.client:
            return "Итоговый отчет недоступен"
        
        try:
            dialog_summary = ""
            total_score = 0
            for i, qa in enumerate(conversation_history):
                score = qa.get('evaluation', {}).get('score', 0)
                feedback = qa.get('evaluation', {}).get('feedback', 'N/A')
                total_score += score
                dialog_summary += f"{i+1}. Вопрос: {qa['question']}\n   Ответ: {qa['answer']}\n   Оценка: {score}/100. Фидбэк: {feedback}\n\n"
            
            average_score = total_score / len(conversation_history) if conversation_history else 0

            system_prompt = HRPrompts.FINAL_FEEDBACK_SYSTEM.format(job_profile=job_profile)
            user_prompt = HRPrompts.FINAL_FEEDBACK_USER.format(
                dialog_summary=dialog_summary,
                average_score=int(average_score)
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=600,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenRouter final feedback error: {e}")
            return "Не удалось сгенерировать итоговый отчет"
