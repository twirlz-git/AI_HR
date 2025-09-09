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
        self.total_questions = 5
        self.job_profile = ""
        self.current_question_text = ""
    
    def start_interview(self, job_profile: str = "Python Developer"):
        """Start interview with job profile"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = True
        self.job_profile = job_profile
        
        # Generate initial greeting and first question
        initial_greeting = HRPrompts.INITIAL_GREETING.format(job_profile=job_profile)
        
        self.current_question_text = initial_greeting
        
        result = {
            "type": "question",
            "question_number": self.current_question + 1,
            "total_questions": self.total_questions,
            "question": initial_greeting,
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
        
        # 4. Move to next question
        self.current_question += 1
        # logger.info(f"Moving to question {self.current_question + 1}/{self.total_questions}")
        
        if self.current_question < self.total_questions:
            # 5. Generate next question
            # logger.info("Generating next question...")
            try:
                next_interaction = await self.openrouter.generate_hr_interaction(
                    self.job_profile, 
                    self.conversation_history
                )
                self.current_question_text = next_interaction
                # logger.info(f"Next question generated: '{next_interaction}'")
            except Exception as e:
                logger.error(f"Error generating next question: {e}")
                self.current_question_text = f"Расскажите подробнее о вашем опыте (вопрос {self.current_question + 1})"
            
            next_question = {
                "type": "question",
                "question_number": self.current_question + 1,
                "total_questions": self.total_questions,
                "question": self.current_question_text,
                "reset_timer": True
            }
            
            result = {
                "type": "answer_processed",
                "improved_answer": improved_answer,
                "evaluation": evaluation,
                "next_question": next_question
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
    
    def reset_interview(self):
        """Reset interview state"""
        self.current_question = 0
        self.conversation_history = []
        self.interview_active = False
        self.job_profile = ""
        self.current_question_text = ""