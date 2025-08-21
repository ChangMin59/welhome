from langchain_core.prompts import PromptTemplate

def intent_router(state, llm):
    if "intent" in state and state["intent"]:
        return state

    prompt = PromptTemplate.from_template("""
다음 사용자의 질문을 읽고 intent를 loan 또는 housing 중 하나로 출력하세요.
설명 없이 한 단어만 출력하세요.

질문: {query}
""")
    chain = prompt | llm
    intent = chain.invoke({"query": state["query"]}).strip().lower()
    return {**state, "intent": intent}
