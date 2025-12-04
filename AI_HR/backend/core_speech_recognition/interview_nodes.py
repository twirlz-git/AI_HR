"""Node functions for interview LangGraph"""

import logging
from typing import Dict
from .interview_state import InterviewState, INTERVIEW_TOPICS
from .openrouter_processor import OpenRouterProcessor
from .hr_prompts import HRPrompts

logger = logging.getLogger(__name__)


class InterviewNodes:
    """Collection of node functions for interview graph"""
    
    def __init__(self, openrouter: OpenRouterProcessor):
        self.openrouter = openrouter
    
    async def generate_greeting(self, state: InterviewState) -> Dict:
        """Generate initial greeting and first question"""
        logger.info(f"Generating greeting for {state['job_profile']}")
        greeting = HRPrompts.INITIAL_GREETING.format(job_profile=state['job_profile'])
        return {
            "stage": "greeting",
            "current_question_text": greeting,
            "current_question_number": 1
        }
    
    async def improve_answer(self, state: InterviewState) -> Dict:
        """Improve candidate answer using LLM"""
        answer_text = state['current_answer_text']
        if not answer_text or not answer_text.strip():
            return {"current_answer_improved": "Кандидат промолчал", "stage": "evaluating_answer"}
        try:
            improved = await self.openrouter.process_text(answer_text)
            return {"current_answer_improved": improved, "stage": "evaluating_answer"}
        except Exception as e:
            logger.error(f"Error improving answer: {e}")
            return {"current_answer_improved": answer_text, "stage": "evaluating_answer"}
    
    async def evaluate_answer(self, state: InterviewState) -> Dict:
        """Evaluate candidate answer"""
        try:
            evaluation = await self.openrouter.evaluate_answer(
                state['current_question_text'], 
                state['current_answer_improved'], 
                state['job_profile']
            )
            score = evaluation.get('score', 0)
            is_unclear = score < 40 or self._is_unclear_answer(state['current_answer_improved'])
            return {
                "current_answer_evaluation": evaluation,
                "is_answer_unclear": is_unclear,
                "stage": "deciding_next_action"
            }
        except Exception as e:
            logger.error(f"Error evaluating: {e}")
            return {
                "current_answer_evaluation": {"score": 50, "feedback": "Не удалось оценить"},
                "is_answer_unclear": False,
                "stage": "deciding_next_action"
            }
    
    def decide_next_action(self, state: InterviewState) -> Dict:
        """Decide whether to ask clarification or move to next topic"""
        is_unclear = state['is_answer_unclear']
        questions_in_topic = state['questions_in_current_topic']
        if questions_in_topic == 0 and is_unclear:
            return {
                "should_ask_clarification": True,
                "should_move_to_next_topic": False,
                "questions_in_current_topic": 1,
                "stage": "generating_followup"
            }
        else:
            return {
                "should_ask_clarification": False,
                "should_move_to_next_topic": True,
                "stage": "moving_to_next_topic"
            }
    
    def save_to_history(self, state: InterviewState) -> Dict:
        """Save current Q&A to conversation history"""
        entry = {
            "question": state['current_question_text'],
            "answer": state['current_answer_improved'],
            "raw_answer": state['current_answer_text'],
            "evaluation": state['current_answer_evaluation']
        }
        return {"conversation_history": state['conversation_history'] + [entry]}
    
    async def generate_next_question(self, state: InterviewState) -> Dict:
        """Generate next interview question"""
        if state['current_topic_index'] >= len(INTERVIEW_TOPICS):
            return {"stage": "finishing"}
        try:
            question = await self.openrouter.generate_hr_interaction(
                state['job_profile'],
                state['conversation_history'],
                INTERVIEW_TOPICS[state['current_topic_index']],
                state.get('should_ask_clarification', False)
            )
            return {
                "current_question_text": question,
                "current_question_number": state['current_question_number'] + 1,
                "stage": "asking_question"
            }
        except Exception as e:
            logger.error(f"Error generating question: {e}")
            return {
                "current_question_text": f"Расскажите подробнее ({state['current_question_number'] + 1})",
                "current_question_number": state['current_question_number'] + 1,
                "stage": "asking_question"
            }
    
    def move_to_next_topic(self, state: InterviewState) -> Dict:
        """Move to next topic"""
        return {
            "current_topic_index": state['current_topic_index'] + 1,
            "questions_in_current_topic": 0,
            "stage": "generating_followup"
        }
    
    async def generate_final_report(self, state: InterviewState) -> Dict:
        """Generate final report"""
        try:
            report = await self.openrouter.generate_final_feedback(
                state['conversation_history'], state['job_profile']
            )
            return {"final_report": report, "stage": "finished"}
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"final_report": "Не удалось сгенерировать отчет", "stage": "finished"}
    
    def _is_unclear_answer(self, answer: str) -> bool:
        """Check if answer is unclear"""
        unclear = ["не понял", "не поняла", "повторите", "не знаю", "что", "а", "хм"]
        answer_lower = answer.lower().strip()
        if len(answer_lower) < 10 or len(answer_lower.split()) < 3:
            return True
        return any(phrase in answer_lower for phrase in unclear)
