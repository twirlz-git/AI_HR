"""Interview State Definitions for LangGraph State Machine"""

from typing import TypedDict, List, Dict, Optional, Literal
from dataclasses import dataclass


# Interview Topics
INTERVIEW_TOPICS = [
    "Технические навыки",
    "Опыт работы",
    "Софт скиллы"
]

# Interview stages
InterviewStage = Literal[
    "initialized",
    "greeting",
    "asking_question",
    "evaluating_answer",
    "deciding_next_action",
    "generating_followup",
    "moving_to_next_topic",
    "finishing",
    "finished"
]


@dataclass
class QuestionAnswerPair:
    """Single Q&A pair in interview history"""
    question: str
    answer: str
    raw_answer: str
    evaluation: Dict[str, any]
    topic: str
    is_clarification: bool = False


class InterviewState(TypedDict):
    """State for interview graph"""
    
    # Job and candidate info
    job_profile: str
    
    # Current stage
    stage: InterviewStage
    
    # Topic tracking
    current_topic_index: int
    questions_in_current_topic: int
    max_questions_per_topic: int
    
    # Question tracking
    current_question_number: int
    total_questions: int
    current_question_text: str
    
    # Answer processing
    current_answer_text: str
    current_answer_improved: str
    current_answer_evaluation: Optional[Dict]
    
    # Decision flags
    is_answer_unclear: bool
    should_ask_clarification: bool
    should_move_to_next_topic: bool
    
    # Conversation history
    conversation_history: List[Dict]
    
    # Final report
    final_report: Optional[str]
    
    # Error tracking
    error: Optional[str]


def create_initial_state(job_profile: str) -> InterviewState:
    """Create initial state for interview"""
    return InterviewState(
        job_profile=job_profile,
        stage="initialized",
        current_topic_index=0,
        questions_in_current_topic=0,
        max_questions_per_topic=2,
        current_question_number=0,
        total_questions=len(INTERVIEW_TOPICS) * 2,  # 3 topics * 2 questions
        current_question_text="",
        current_answer_text="",
        current_answer_improved="",
        current_answer_evaluation=None,
        is_answer_unclear=False,
        should_ask_clarification=False,
        should_move_to_next_topic=False,
        conversation_history=[],
        final_report=None,
        error=None
    )
