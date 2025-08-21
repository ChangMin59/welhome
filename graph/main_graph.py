from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from agents.loan_agent import loan_agent
from agents.housing_agent import housing_agent

from typing import TypedDict

class AgentState(TypedDict, total=False):
    query: str
    intent: str
    done: bool
    loan_amount: int
    loan_year: int
    loan_table_text: str
    loan_history: list
    housing_history: list
    housing_user_data: dict
    housing_notices: list
    housing_selected_notice: dict
    housing_recommended: bool
    notice_id: str
    pages: list
    pages_flag: bool
    result: str

from langchain_ollama import OllamaLLM
llm = OllamaLLM(model="exaone3.5:7.8b")


def intent_router(state: AgentState):
    if state.get("intent"):
        return state

    prompt = PromptTemplate.from_template("""
아래 사용자의 질문을 읽고 intent를 'loan' 또는 'housing' 중 하나로 출력하세요.
설명 없이 한 단어만 출력하세요.

질문: {query}
""")
    chain = prompt | llm
    intent = chain.invoke({"query": state["query"]}).strip().lower()
    state["intent"] = intent
    return state


graph = StateGraph(AgentState)

# 주택 대출

graph.add_node("intent_router", intent_router)
graph.add_node("loan_agent", lambda state: loan_agent(state, llm))
graph.add_node("housing_agent", lambda state: housing_agent(state, llm))

graph.set_entry_point("intent_router")

graph.add_conditional_edges(
    "intent_router",
    lambda state: state.get("intent"),
    {
        "loan": "loan_agent",
        "housing": "housing_agent"
    }
)

# ✅ 상담 노드에서 분기
graph.add_conditional_edges(
    "loan_agent",
    lambda state: "loan_agent" if state.get("query") and "new" in state["query"].lower() else END,
    {"loan_agent": "loan_agent", END: END}
)

graph.add_conditional_edges(
    "housing_agent",
    lambda state: "housing_agent" if state.get("query") and "new" in state["query"].lower() else END,
    {"housing_agent": "housing_agent", END: END}
)

graph.add_edge("intent_router", END)

app = graph.compile()
