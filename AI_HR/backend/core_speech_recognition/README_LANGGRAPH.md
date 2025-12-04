# LangGraph Interview System Refactoring

## Overview

This refactoring migrates the HR interview logic from procedural state management to a **LangGraph-based state machine**. This provides:

- ✅ **Clear state transitions** - Explicit graph structure
- ✅ **Better testability** - Each node is independently testable
- ✅ **Easier debugging** - Visual graph representation
- ✅ **Maintainability** - Separation of concerns
- ✅ **Extensibility** - Easy to add new interview flows

---

## Architecture

### New Files

```
core_speech_recognition/
├── interview_state.py       # State definitions (TypedDict)
├── interview_nodes.py       # Node functions for graph
├── interview_graph.py       # LangGraph state machine
└── hr_interviewer.py        # Refactored wrapper (backwards compatible)
```

### State Machine Flow

```
[START]
   |
   v
[generate_greeting] --> [END] (wait for answer)
   
(answer received)
   |
   v
[improve_answer]
   |
   v
[evaluate_answer]
   |
   v
[decide_next_action]
   |
   v
[save_to_history]
   |
   +---> [should_move_to_next_topic?]
   |        |
   |        +--YES--> [move_to_next_topic]
   |        |              |
   |        |              v
   |        +---------> [generate_next_question] --> [END]
   |        |
   |        +--NO--> [generate_next_question] --> [END]
   |
   +---> [all topics done?] --> [generate_final_report] --> [END]
```

---

## Key Components

### 1. InterviewState (interview_state.py)

Typed state dictionary that tracks:
- Job profile
- Current stage (initialized, greeting, asking_question, etc.)
- Topic tracking (current_topic_index, questions_in_current_topic)
- Question tracking (current_question_number, total_questions)
- Answer processing (improved answer, evaluation, flags)
- Conversation history
- Final report

### 2. InterviewNodes (interview_nodes.py)

Node functions that operate on state:
- `generate_greeting()` - Create initial greeting
- `improve_answer()` - Use LLM to improve transcribed text
- `evaluate_answer()` - Score and provide feedback
- `decide_next_action()` - Route to clarification or next topic
- `save_to_history()` - Persist Q&A pair
- `generate_next_question()` - Create follow-up question
- `move_to_next_topic()` - Progress through topics
- `generate_final_report()` - Create summary report

### 3. InterviewGraph (interview_graph.py)

LangGraph state machine that:
- Defines nodes and edges
- Handles conditional routing
- Manages state transitions
- Provides async interface

### 4. HRInterviewer (hr_interviewer.py)

Simplified wrapper that:
- Maintains backwards compatibility
- Uses InterviewGraph internally
- Provides clean API for WebSocket handler

---

## Interview Flow Logic

### Topic-Based Structure

3 topics × 2 questions max = **6 total questions**

**Topics:**
1. Технические навыки (Technical Skills)
2. Опыт работы (Work Experience)
3. Софт скиллы (Soft Skills)

### Decision Logic

**For each answer:**
1. Improve text using LLM
2. Evaluate (score 0-100)
3. Check if unclear (score < 40 or too short)

**Routing:**
- **First question unclear** → Ask clarification (2nd question same topic)
- **First question clear OR second question** → Move to next topic
- **All topics done** → Generate final report

---

## Usage

### Starting Interview

```python
from core_speech_recognition.hr_interviewer import HRInterviewer

interviewer = HRInterviewer()
result = await interviewer.start_interview(job_profile="Python Developer")

print(result)
# {
#   "type": "question",
#   "question_number": 1,
#   "total_questions": 6,
#   "question": "Добро пожаловать...",
#   "topic_display": "Тема 1: Технические навыки",
#   "reset_timer": True
# }
```

### Processing Answer

```python
result = await interviewer.process_answer("Мой ответ на вопрос...")

if result['type'] == 'answer_processed':
    print("Next question:", result['next_question']['question'])
    print("Evaluation:", result['evaluation'])
elif result['type'] == 'interview_finished':
    print("Final report:", result['final_report'])
```

---

## Benefits of LangGraph Approach

### 1. **Explicit State Transitions**

**Before:**
```python
# Hidden state changes scattered in methods
self.current_question += 1
self.questions_in_current_topic += 1
self.current_topic_index += 1
```

**After:**
```python
# Clear state updates in node returns
return {
    "current_question_number": state['current_question_number'] + 1,
    "stage": "asking_question"
}
```

### 2. **Testable Nodes**

**Before:** Large methods with side effects

**After:** Pure functions that transform state

```python
# Easy to test
async def test_evaluate_answer():
    state = {"current_answer_improved": "Good answer", ...}
    result = await nodes.evaluate_answer(state)
    assert result['current_answer_evaluation']['score'] > 50
```

### 3. **Visual Debugging**

LangGraph provides visualization tools:

```python
# Generate graph diagram
from langgraph.graph import visualize
visualize(interview_graph.compiled_graph)
```

### 4. **Conditional Routing**

**Before:** Complex if/else chains

**After:** Declarative routing

```python
workflow.add_conditional_edges(
    "save_to_history",
    route_function,
    {
        "move_to_next_topic": "move_to_next_topic",
        "generate_followup": "generate_next_question",
        "finish": "generate_final_report"
    }
)
```

---

## Migration Notes

### Backwards Compatibility

The `HRInterviewer` class maintains the same API:

```python
# Old code still works
interviewer = HRInterviewer()
result = await interviewer.start_interview("Python Developer")
result = await interviewer.process_answer("My answer")
```

### Internal Changes

- State is now managed by `InterviewState` TypedDict
- Logic is distributed across node functions
- Graph handles transitions automatically

### No Changes Required in:

- `vosk_handler.py` - Uses same `HRInterviewer` API
- `main.py` - WebSocket endpoints unchanged
- Frontend - Same message format

---

## Testing

### Unit Tests for Nodes

```python
import pytest
from interview_nodes import InterviewNodes
from interview_state import create_initial_state

@pytest.mark.asyncio
async def test_improve_answer():
    nodes = InterviewNodes(mock_openrouter)
    state = create_initial_state("Developer")
    state['current_answer_text'] = "test answer"
    
    result = await nodes.improve_answer(state)
    assert result['current_answer_improved'] is not None
    assert result['stage'] == 'evaluating_answer'
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_interview_flow():
    interviewer = HRInterviewer()
    
    # Start
    start_result = await interviewer.start_interview("Developer")
    assert start_result['type'] == 'question'
    
    # Process answers
    for _ in range(6):
        result = await interviewer.process_answer("Good answer")
        if result['type'] == 'interview_finished':
            break
    
    assert result['type'] == 'interview_finished'
    assert result['final_report'] is not None
```

---

## Future Enhancements

### Easy to Add:

1. **Dynamic topic selection** based on job profile
2. **Skill-based routing** (ask harder questions if doing well)
3. **Multi-language support** (add language node)
4. **Pause/resume** (serialize state to DB)
5. **Human-in-the-loop** (add approval nodes)
6. **A/B testing** (different question generation strategies)

### Example: Adding Pause/Resume

```python
# Serialize state
import json
state_json = json.dumps(interviewer.current_state)

# Resume later
interviewer.current_state = json.loads(state_json)
result = await interviewer.process_answer("continuation...")
```

---

## Dependencies

```txt
langgraph>=0.0.20
langchain-core>=0.1.0
langchain-openai>=0.0.5
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### Issue: State not updating

**Solution:** Ensure node functions return state updates as dictionaries

### Issue: Graph routing errors

**Solution:** Check conditional edge functions return valid node names

### Issue: Async errors

**Solution:** All node functions must be async if they call async operations

---

## Performance

- **Latency:** Same as before (LangGraph overhead is negligible)
- **Memory:** Slightly higher due to state tracking
- **Scalability:** Better (state can be externalized)

---

## Summary

This refactoring provides a **robust, maintainable, and extensible** foundation for the interview system while maintaining **full backwards compatibility** with existing code.

The LangGraph approach makes the interview flow **explicit, testable, and easy to reason about** - critical for production AI systems.
