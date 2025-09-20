import asyncio
import logging
from . import settings
from .openrouter_processor import OpenRouterProcessor
from .hr_prompts import HRPrompts

logger = logging.getLogger(__name__)

class HRInterviewer:
    def __init__(self):
        self.openrouter = OpenRouterProcessor()
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = False
        self.job_profile = ""
        self.current_question_text = ""
        
        # Topic-based interview structure
        self.topics = [
            "Технические навыки",
            "Опыт работы", 
            "Софт скиллы"
        ]
        self.current_topic_index = 0
        self.questions_in_current_topic = 0
        self.max_questions_per_topic = 2
        self.total_questions = len(self.topics) * self.max_questions_per_topic  # 3 topics * 2 = 6 max
    
    def start_interview(self, job_profile: str = "Python Developer"):
        """Start interview with job profile"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = True
        self.job_profile = job_profile
        self.current_topic_index = 0
        self.questions_in_current_topic = 0
        
        # Generate initial greeting and first question
        initial_greeting = HRPrompts.INITIAL_GREETING.format(job_profile=job_profile)
        
        self.current_question_text = initial_greeting
        
        # Add topic display for first question
        topic_name = self.topics[self.current_topic_index]
        topic_display = f"Тема {self.current_topic_index + 1}: {topic_name}"
        
        result = {
            "type": "question",
            "question_number": self.current_question + 1,
            "total_questions": self.total_questions,
            "question": initial_greeting,
            "topic_display": topic_display,
            "reset_timer": True
        }
        
        logger.info(f"Started interview for {job_profile}")
        return result
    
    def get_current_question(self):
        """Return current question"""
        if self.current_question >= self.total_questions:
            return self.finish_interview()
            
        return {
            "type": "question",
            "question_number": self.current_question + 1,
            "total_questions": self.total_questions,
            "question": self.current_question_text
        }
    
    async def process_answer(self, answer_text: str):
        """Process candidate answer"""
        
        if not self.interview_active or self.current_question >= self.total_questions:
            logger.warning("Interview not active or questions exceeded")
            return {"type": "error", "message": "Интервью не активно"}
        
        # 1. Improve answer through OpenRouter
        # logger.info("Improving answer via OpenRouter...")
        try:
            improved_answer = await self.openrouter.process_text(answer_text)
            # logger.info(f"Answer improved: '{improved_answer}'")
        except Exception as e:
            logger.error(f"Error improving answer: {e}")
            improved_answer = answer_text
        
        # 2. Evaluate answer
        # logger.info("Evaluating answer...")
        try:
            evaluation = await self.openrouter.evaluate_answer(
                self.current_question_text, 
                improved_answer, 
                self.job_profile
            )
            # logger.info(f"Answer evaluated: {evaluation}")
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            evaluation = {"score": 50, "feedback": "Не удалось оценить ответ"}
        
        # 3. Add to conversation history
        self.conversation_history.append({
            "question": self.current_question_text,
            "answer": improved_answer,
            "raw_answer": answer_text,
            "evaluation": evaluation
        })
        # logger.info(f"Added to history: Q{self.current_question + 1}")
        
        # 4. SIMPLE TOPIC LOGIC: Each topic = max 2 questions
        score = evaluation.get('score', 0)
        feedback_message = ""
        is_unclear = score < 40 or self._is_unclear_answer(improved_answer)
        
        # Increment questions in current topic
        self.questions_in_current_topic += 1
        current_topic_name = self.topics[self.current_topic_index]
        
        logger.info(f"TOPIC: '{current_topic_name}' - Question {self.questions_in_current_topic}/2 - Score: {score} - Unclear: {is_unclear}")
        
        # Decision logic
        if self.questions_in_current_topic == 1 and is_unclear:
            # First question unclear -> stay in topic for question 2
            feedback_message = f"Ответ неясен. Уточняющий вопрос по теме '{current_topic_name}'"
            logger.info(f"STAYING in topic '{current_topic_name}' for question 2")
        else:
            # Move to next topic (either: 2 questions done OR first question was clear)
            self.current_topic_index += 1
            self.questions_in_current_topic = 0
            logger.info(f"MOVING to next topic. Completed: '{current_topic_name}'")
        
        # 5. Move to next question
        self.current_question += 1
        # logger.info(f"Moving to question {self.current_question + 1}/{self.total_questions}")
        
        # Check if interview should continue (more topics available)
        if self.current_topic_index < len(self.topics):
            # 5. Generate next question
            # logger.info("Generating next question...")
            try:
                current_topic = self.topics[self.current_topic_index]
                is_clarification = self.questions_in_current_topic == 1  # Second question on same topic
                
                next_interaction = await self.openrouter.generate_hr_interaction(
                    self.job_profile, 
                    self.conversation_history,
                    current_topic,
                    is_clarification
                )
                self.current_question_text = next_interaction
                # logger.info(f"Next question generated: '{next_interaction}'")
            except Exception as e:
                logger.error(f"Error generating next question: {e}")
                self.current_question_text = f"Расскажите подробнее о вашем опыте (вопрос {self.current_question + 1})"
            
            # Add topic to question text (check bounds)
            if self.current_topic_index < len(self.topics):
                topic_name = self.topics[self.current_topic_index]
                question_with_topic = f"[ТЕМА: {topic_name}] {self.current_question_text}"
            else:
                question_with_topic = self.current_question_text
            
            # Simple total calculation: current + remaining topics (max 2 each)
            remaining_topics = len(self.topics) - self.current_topic_index
            max_remaining = remaining_topics * 2
            estimated_total = self.current_question + 1 + max_remaining - self.questions_in_current_topic
            
            # Display as "Тема X: Название темы" instead of "Вопрос X"
            topic_display = f"Тема {self.current_topic_index + 1}: {topic_name}" if self.current_topic_index < len(self.topics) else f"Вопрос {self.current_question + 1}"
            
            next_question = {
                "type": "question", 
                "question_number": self.current_question + 1,
                "total_questions": min(estimated_total, 10),
                "question": question_with_topic,
                "topic_display": topic_display,
                "reset_timer": True
            }
            
            result = {
                "type": "answer_processed",
                "improved_answer": improved_answer,
                "evaluation": evaluation,
                "next_question": next_question,
                "feedback_message": feedback_message,
                "total_questions_updated": self.total_questions
            }
            # logger.info("Returning answer_processed with next question")
            return result
        else:
            # Interview finished
            # logger.info("Interview finished, generating final result")
            return await self.finish_interview()
    
    async def finish_interview(self):
        """Finish interview and generate final feedback"""
        self.interview_active = False
        
        # Generate closing remarks
        closing_remarks = HRPrompts.CLOSING_REMARKS
        
        # Generate final feedback report
        # logger.info("Generating final feedback report...")
        try:
            final_report = await self.openrouter.generate_final_feedback(
                self.conversation_history, 
                self.job_profile
            )
            # logger.info("Final report generated")
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            final_report = "Не удалось сгенерировать итоговый отчет"
        
        return {
            "type": "interview_finished",
            "message": closing_remarks,
            "final_report": final_report,
            "conversation_history": self.conversation_history
        }
    
    def create_interview_summary(self):
        """Create interview summary"""
        summary = f"=== ИТОГИ HR-ИНТЕРВЬЮ ({self.job_profile}) ===\n\n"
        
        total_score = 0
        for i, entry in enumerate(self.conversation_history, 1):
            evaluation = entry.get('evaluation', {})
            score = evaluation.get('score', 0)
            feedback = evaluation.get('feedback', 'N/A')
            total_score += score
            
            summary += f"Вопрос {i}: {entry['question']}\n"
            summary += f"Ответ: {entry['answer']}\n"
            summary += f"Оценка: {score}/100. Фидбэк: {feedback}\n\n"
        
        if self.conversation_history:
            average_score = total_score / len(self.conversation_history)
            summary += f"Средняя оценка: {average_score:.1f}/100\n"
        
        return summary
    
    def _is_unclear_answer(self, answer: str) -> bool:
        """Check if answer is unclear or evasive"""
        unclear_phrases = [
            "не понял", "не поняла", "повторите", "что вы имеете в виду",
            "не знаю", "затрудняюсь ответить", "можете повторить",
            "не расслышал", "не расслышала", "простите", "извините",
            "что", "а", "хм", "эм", "ну", "это", "да", "нет"
        ]
        
        answer_lower = answer.lower().strip()
        
        # Check if answer is too short (less than 10 characters)
        if len(answer_lower) < 10:
            return True
            
        # Check if answer contains unclear phrases
        for phrase in unclear_phrases:
            if phrase in answer_lower:
                return True
                
        # Check if answer is mostly punctuation or single words
        words = answer_lower.split()
        if len(words) < 3:
            return True
            
        return False
    
    def reset_interview(self):
        """Reset interview state"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = False
        self.job_profile = ""
        self.current_question_text = ""
        self.clarification_attempts = {}