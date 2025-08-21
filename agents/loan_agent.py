import re
from utils.loan_calculator import get_table_text
import markdown

DB_PATH = "/home/alpaco/lyj0622/project_real/data/loan_type.db"

def is_reset_command(text):
    triggers = ["new", "새로", "다시", "다른 조건"]
    text = text.lower()
    return any(word in text for word in triggers)

def extract_number(text):
    numbers = re.findall(r"\d+", text.replace(",", ""))
    if numbers:
        return int(numbers[0])
    return None

def loan_agent(state, llm):
    # ✅ NEW 명령 → intent 유지한 채 상태 초기화
    if is_reset_command(state["query"]):
        preserved_intent = state.get("intent")
        state.clear()
        state["intent"] = preserved_intent
        return {
            **state,
            "result": "좋습니다! 새로운 대출 상담을 시작합니다.\n대출금액을 입력해주세요.'"
        }

    # `exit` 명령어 처리 - 상담 종료
    if state["query"].lower() == "exit":
        state.clear()  # 상태 초기화
        return {
            **state,
            "result": "대출 상담을 종료합니다."
        }

    if "loan_history" not in state or not state["loan_history"]:
        state["loan_history"] = [
            {"role": "system", "content": "너는 친절한 금융 상담사야. 사용자가 이해하기 쉽게 설명해 줘."}
        ]

    if not state.get("loan_amount"):
        amount = extract_number(state["query"])
        if amount:
            state["loan_amount"] = amount
            return {
                **state,
                "result": "대출기간(년)을 입력해주세요."
            }
        else:
            return {
                **state,
                "result": "대출금액을 입력해주세요."
            }

    if not state.get("loan_year"):
        years = extract_number(state["query"])
        if years and years < 100:
            state["loan_year"] = years
        else:
            return {
                **state,
                "result": "대출기간(년)을 입력해주세요."
            }

    if state.get("loan_table_text"):
        state["loan_history"].append({"role": "user", "content": state["query"]})
        response = llm.invoke(state["loan_history"])
        state["loan_history"].append({"role": "assistant", "content": response})
        state["result"] = response + "\n\n👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요."
        return state

    loan_amount = state["loan_amount"]
    loan_years = state["loan_year"]
    table_text = get_table_text(loan_amount, loan_years, DB_PATH)
    print("====table_text====:", table_text)
    if not table_text:
        return {
            **state,
            "result": "조건에 맞는 대출 상품이 없습니다. 다른 금액이나 기간으로 시도해 보세요.\n👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요."
        }

    state["loan_tablet_text"] = table_text
    prompt = (
        f"표 컬럼 설명: 은행명(bank), 상품명(product), 상환유형(repay_type), 평균금리(rate_avg_prev), 한도금액(limit_amt), 총 상환비용(cost_total)\n"
        f"표의 내용을 참고해서 사용자에게 대출 가능한 상품에 대해 간결하고 가독성 좋게 설명해\n"
        f"{table_text}"
    )
    state["loan_history"].append({"role": "user", "content": prompt})
    response = llm.invoke(state["loan_history"])
    state["loan_history"].append({"role": "assistant", "content": response})
    state["result"] = markdown.markdown(response + "\n\n👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요.")
    return state
