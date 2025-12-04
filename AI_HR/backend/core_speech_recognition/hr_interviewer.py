"""HR Interviewer - Refactored to use LangGraph State Machine"""

import logging
from .openrouter_processor import OpenRouterProcessor
from .interview_graph import InterviewGraph
from .interview_state import InterviewState, INTERVIEW_TOPICS

logger = logging.getLogger(__name__)


class HRInterviewer:
    """HR Interviewer using LangGraph for state management"""
    
    def __init__(self):
        self.openrouter = OpenRouterProcessor()
        self.interview_graph = InterviewGraph(self.openrouter)
        self.interview_active = False
        self.current_state: InterviewState = None
        
        # Legacy compatibility properties
        self.current_question = 0
        self.total_questions = 6
        self.job_profile = ""
    
    async def start_interview(self, job_profile: str = "Python Developer") -> dict:
        """Start interview with job profile using LangGraph"""
        logger.info(f"Starting LangGraph-based interview for {job_profile}")
        
        self.interview_active = True
        self.job_profile = job_profile
        
        # Initialize interview through graph
        result = await self.interview_graph.start_interview(job_profile)
        
        # Store state
        self.current_state = result['state']
        self.current_question = result['question_number']
        self.total_questions = result['total_questions']
        
        # Format response for frontend
        topic_name = INTERVIEW_TOPICS[0]
        return {
            "type": "question",
            "question_number": result['question_number'],
            "total_questions": result['total_questions'],
            "question": result['question'],
            "topic_display": f"Тема 1: {topic_name}",
            "reset_timer": True
        }
    
    async def process_answer(self, answer_text: str) -> dict:
        """Process candidate answer using LangGraph"""
        if not self.interview_active or not self.current_state:
            logger.warning("Interview not active")
            return {"type": "error", "message": "Интервью не активно"}
        
        logger.info(f"Processing answer for question {self.current_state['current_question_number']}")
        
        # Process through graph
        result = await self.interview_graph.process_answer(answer_text, self.current_state)
        
        # Update state
        if 'state' in result:
            self.current_state = result['state']
            self.current_question = result['state']['current_question_number']
        
        # Check if interview finished
        if result['type'] == 'interview_finished':
            self.interview_active = False
            return result
        
        # Format next question with topic display
        if 'next_question' in result:
            topic_idx = self.current_state['current_topic_index']
            if topic_idx < len(INTERVIEW_TOPICS):
                topic_name = INTERVIEW_TOPICS[topic_idx]
                result['next_question']['topic_display'] = f"Тема {topic_idx + 1}: {topic_name}"
            else:
                result['next_question']['topic_display'] = f"Вопрос {result['next_question']['question_number']}"
        
        return result
    
    def get_current_question(self) -> dict:
        """Return current question state"""
        if not self.current_state:
            return {"type": "error", "message": "Интервью не инициализировано"}
        
        return {
            "type": "question",
            "question_number": self.current_state['current_question_number'],
            "total_questions": self.current_state['total_questions'],
            "question": self.current_state['current_question_text']
        }
    
    def reset_interview(self):
        """Reset interview state"""
        logger.info("Resetting interview state")
        self.interview_active = False
        self.current_state = None
        self.current_question = 0
        self.job_profile = ""
    
    def create_interview_summary(self) -> str:
        """Create interview summary from current state"""
        if not self.current_state or not self.current_state.get('conversation_history'):
            return "Интервью не проведено"
        
        summary = f"=== ИТОГИ HR-ИНТЕРВЬЮ ({self.job_profile}) ===\n\n"
        
        total_score = 0
        history = self.current_state['conversation_history']
        
        for i, entry in enumerate(history, 1):
            evaluation = entry.get('evaluation', {})
            score = evaluation.get('score', 0)
            feedback = evaluation.get('feedback', 'N/A')
            total_score += score
            
            summary += f"Вопрос {i}: {entry['question']}\n"
            summary += f"Ответ: {entry['answer']}\n"
            summary += f"Оценка: {score}/100. Фидбэк: {feedback}\n\n"
        
        if history:
            average_score = total_score / len(history)
            summary += f"Средняя оценка: {average_score:.1f}/100\n"
        
        return summary
    
    # Legacy compatibility property
    @property
    def conversation_history(self):
        """Get conversation history for backwards compatibility"""
        if self.current_state:
            return self.current_state.get('conversation_history', [])
        return []
