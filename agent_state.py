from typing import TypedDict

class AgentState(TypedDict):
    question: str
    business_context: str
    plan: str
    genie_result: str
    ticket_result: str
    doc_result: str
    evidence_sufficient: bool
    evidence_reason: str       # NEW: why the evaluator judged sufficient or not
    attempts: int
    refined_query: str
    final_answer: str