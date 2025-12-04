"""LangGraph State Machine for HR Interview"""

import logging
from langgraph.graph import StateGraph, END
from .interview_state import InterviewState, create_initial_state
from .interview_nodes import InterviewNodes
from .openrouter_processor import OpenRouterProcessor

logger = logging.getLogger(__name__)


class InterviewGraph:
    """LangGraph-based interview state machine"""
    
    def __init__(self, openrouter: OpenRouterProcessor):
        self.openrouter = openrouter
        self.nodes = InterviewNodes(openrouter)
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Build the interview state graph"""
        workflow = StateGraph(InterviewState)
        
        # Add nodes
        workflow.add_node("generate_greeting", self.nodes.generate_greeting)
        workflow.add_node("improve_answer", self.nodes.improve_answer)
        workflow.add_node("evaluate_answer", self.nodes.evaluate_answer)
        workflow.add_node("decide_next_action", self.nodes.decide_next_action)
        workflow.add_node("save_to_history", self.nodes.save_to_history)
        workflow.add_node("generate_next_question", self.nodes.generate_next_question)
        workflow.add_node("move_to_next_topic", self.nodes.move_to_next_topic)
        workflow.add_node("generate_final_report", self.nodes.generate_final_report)
        
        # Define edges based on state
        workflow.set_entry_point("generate_greeting")
        
        # From greeting -> asking question (initial state)
        workflow.add_edge("generate_greeting", END)
        
        # Answer processing flow
        workflow.add_edge("improve_answer", "evaluate_answer")
        workflow.add_edge("evaluate_answer", "decide_next_action")
        workflow.add_edge("decide_next_action", "save_to_history")
        
        # After saving, decide next step based on state
        workflow.add_conditional_edges(
            "save_to_history",
            self._route_after_save,
            {
                "move_to_next_topic": "move_to_next_topic",
                "generate_followup": "generate_next_question",
                "finish": "generate_final_report"
            }
        )
        
        # Topic movement flows
        workflow.add_edge("move_to_next_topic", "generate_next_question")
        
        # Question generation leads to waiting for answer (END for now)
        workflow.add_edge("generate_next_question", END)
        
        # Final report generation ends the interview
        workflow.add_edge("generate_final_report", END)
        
        return workflow
    
    def _route_after_save(self, state: InterviewState) -> str:
        """Route to next step after saving Q&A to history"""
        # Check if we should finish
        if state['current_topic_index'] >= len(state.get('topics', [])):
            logger.info("All topics completed, routing to finish")
            return "finish"
        
        # Check if we should move to next topic
        if state.get('should_move_to_next_topic', False):
            logger.info("Routing to move_to_next_topic")
            return "move_to_next_topic"
        
        # Otherwise generate followup (clarification or next question in same topic)
        logger.info("Routing to generate_followup")
        return "generate_followup"
    
    async def start_interview(self, job_profile: str) -> dict:
        """Start a new interview"""
        logger.info(f"Starting interview for: {job_profile}")
        initial_state = create_initial_state(job_profile)
        
        # Run greeting generation
        result = await self.compiled_graph.ainvoke(initial_state)
        
        return {
            "type": "question",
            "question_number": result['current_question_number'],
            "total_questions": result['total_questions'],
            "question": result['current_question_text'],
            "topic_display": f"Тема 1: {result.get('topics', [])[0] if result.get('topics') else ''}",
            "reset_timer": True,
            "state": result  # Return full state for tracking
        }
    
    async def process_answer(self, answer_text: str, current_state: InterviewState) -> dict:
        """Process candidate answer through the graph"""
        logger.info(f"Processing answer for question {current_state['current_question_number']}")
        
        # Update state with new answer
        current_state['current_answer_text'] = answer_text
        current_state['stage'] = 'evaluating_answer'
        
        # Start from improve_answer node
        # We'll invoke the graph starting from improve_answer
        temp_graph = StateGraph(InterviewState)
        temp_graph.add_node("improve_answer", self.nodes.improve_answer)
        temp_graph.add_node("evaluate_answer", self.nodes.evaluate_answer)
        temp_graph.add_node("decide_next_action", self.nodes.decide_next_action)
        temp_graph.add_node("save_to_history", self.nodes.save_to_history)
        temp_graph.add_node("generate_next_question", self.nodes.generate_next_question)
        temp_graph.add_node("move_to_next_topic", self.nodes.move_to_next_topic)
        temp_graph.add_node("generate_final_report", self.nodes.generate_final_report)
        
        temp_graph.set_entry_point("improve_answer")
        temp_graph.add_edge("improve_answer", "evaluate_answer")
        temp_graph.add_edge("evaluate_answer", "decide_next_action")
        temp_graph.add_edge("decide_next_action", "save_to_history")
        temp_graph.add_conditional_edges(
            "save_to_history",
            self._route_after_save,
            {
                "move_to_next_topic": "move_to_next_topic",
                "generate_followup": "generate_next_question",
                "finish": "generate_final_report"
            }
        )
        temp_graph.add_edge("move_to_next_topic", "generate_next_question")
        temp_graph.add_edge("generate_next_question", END)
        temp_graph.add_edge("generate_final_report", END)
        
        compiled = temp_graph.compile()
        result = await compiled.ainvoke(current_state)
        
        # Check if interview is finished
        if result['stage'] == 'finished':
            return {
                "type": "interview_finished",
                "message": "Спасибо за уделенное время!",
                "final_report": result['final_report'],
                "conversation_history": result['conversation_history']
            }
        
        # Return next question
        return {
            "type": "answer_processed",
            "improved_answer": result['current_answer_improved'],
            "evaluation": result['current_answer_evaluation'],
            "next_question": {
                "type": "question",
                "question_number": result['current_question_number'],
                "total_questions": result['total_questions'],
                "question": result['current_question_text'],
                "reset_timer": True
            },
            "state": result  # Return updated state
        }
