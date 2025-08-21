import re
import httpx
from utils.db_access import search_housing_by_condition
from utils.region_map import get_region_code
from api.lh_api import get_notices_by_house_ids
from utils.vectordb_search import search_notice_in_vectordb
import markdown  # 파일 상단 import 부분에 추가

QUESTION_TEXT = {
    "계층": "신청자의 계층(예: 일반, 신혼부부 등)을 입력해주세요",
    "소득": "월소득을 숫자로 입력해주세요 (단위: 원)",
    "가구원수": "가구원 수를 입력해주세요 (숫자)",
    "무주택": "무주택 여부를 입력해주세요 (예/아니오)",
    "세대주": "세대주 여부를 입력해주세요 (예/아니오)",
    "희망거주지": "희망하는 거주 지역을 입력해주세요",
    "총자산": "총 자산 금액을 입력해주세요 (숫자)",
    "자동차가액": "자동차 가액을 입력해주세요 (숫자)"
}

# FastAPI로 데이터를 비동기적으로 보내는 함수
async def send_to_fastapi(data):
    url = "http://localhost:8000/housing-data" 
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return response.json()

def is_reset_command(text):
    triggers = ["new", "새로", "다시", "다른 조건"]
    text = text.lower()
    return any(word in text for word in triggers)

def is_exit_command(text):
    return text.strip().lower() == "exit"

def parse_bool(text):
    return text.strip().lower() in ["예", "yes", "y", "true", "1"]

def extract_number(text):
    numbers = re.findall(r"\d+", text.replace(",", ""))
    if numbers:
        return int(numbers[0])
    return None

def housing_agent(state, llm):
    # ✅ 'exit' 명령 → 상태 초기화 및 상담 종료 처리
    if is_exit_command(state["query"]):
        state.clear()  # 상태 초기화
        return {
            **state,
            "result": "주택 상담을 종료합니다."
        }

    # ✅ NEW 명령 → intent 유지한 채 상태 초기화
    if is_reset_command(state["query"]):
        preserved_intent = state.get("intent")
        state.clear()
        state["intent"] = preserved_intent
        return {
            **state,
            "result": QUESTION_TEXT["계층"]
        }

    if "housing_history" not in state or not state["housing_history"]:
        state["housing_history"] = [
            {"role": "system", "content": "너는 친절한 주택 청약 상담사야. 사용자가 이해하기 쉽게 설명해 줘."}
        ]

    if "housing_user_data" not in state:
        # ✅ 처음 진입이면 상태 준비만 하고 질문 유도
        state["housing_user_data"] = {
            "계층": None,
            "소득": None,
            "가구원수": None,
            "무주택": None,
            "세대주": None,
            "희망거주지": None,
            "총자산": None,
            "자동차가액": None
        }
        state["result"] = QUESTION_TEXT["계층"]
        return state

    # ✅ 여기부터는 진짜 답변 입력 처리
    for key, value in state["housing_user_data"].items():
        if value is None:
            user_input = state["query"].strip()
            if key in ["무주택", "세대주"]:
                state["housing_user_data"][key] = parse_bool(user_input)
            elif key in ["가구원수", "총자산", "자동차가액", "소득"]:
                state["housing_user_data"][key] = extract_number(user_input)
            else:
                state["housing_user_data"][key] = user_input

            # 다음 질문 리턴
            for k, v in state["housing_user_data"].items():
                if v is None:
                    return {
                        **state,
                        "result": QUESTION_TEXT[k]
                    }
            break

    # ✅ 사용자 정보 다 받으면 → 한 번에 유형 + 공고 출력
    if not state.get("housing_recommended"):
        user_data = state["housing_user_data"]
        house_list = search_housing_by_condition(user_data)
        if not house_list:
            return {**state, "result": "❌ 조건에 맞는 임대주택 유형이 없습니다. 다른 조건을 입력해주세요."}

        region_code = get_region_code(user_data.get("희망거주지"))
        notices = get_notices_by_house_ids([row["house_id"] for row in house_list], region_code)
        if not notices:
            return {**state, "result": "❌ 현재 신청 가능한 공고가 없습니다. 다른 조건을 입력해주세요."}

        state["housing_notices"] = notices
        state["housing_recommended"] = True

     # ✅ 임대주택 유형 안내 (HTML 리스트)
        types_text = "<ul>" + "".join(
            f"<li>{row['house_name']} ({row['supply_type']})</li>" for row in house_list
        ) + "</ul>"

        # ✅ 공고 리스트 안내 (HTML 번호 매긴 리스트)
        notice_list_text = "<ol>" + "".join(
            f"<li>{n['PAN_NM']}</li>" for n in notices
        ) + "</ol>"

        state["result"] = (
            f"✅ 신청 가능한 임대주택 유형:\n{types_text}\n\n"
            f"✅ 진행 중인 추천 공고:\n{notice_list_text}\n\n"
            "원하는 공고 번호를 입력해주세요.\n"
            # "👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요."
        )
        return state

    # ✅ 사용자가 공고 선택
    if state.get("housing_recommended"):
        if "change" in state["query"].lower():
            state["housing_selected_notice"] = None
            return {
                **state,
                "result": "공고를 다시 선택해주세요. 번호를 입력해주세요."
            }

        if not state.get("housing_selected_notice"):
            notices = state.get("housing_notices", [])
            try:
                idx = int(state["query"].strip()) - 1
                if 0 <= idx < len(notices):
                    state["housing_selected_notice"] = notices[idx]
                    return {
                        **state,
                        "result": f"✅ 선택한 공고: {notices[idx]['PAN_NM']}\n이제 궁금한 점을 입력해주세요!"
                    }
                else:
                    return {**state, "result": "⚠️ 올바른 번호를 입력해주세요."}
            except:
                return {**state, "result": "⚠️ 번호를 입력해주세요."}

        # ✅ 선택된 공고에 대한 Q&A (벡터검색 → LLM이 답변 생성)
        notice_id = state["housing_selected_notice"]["PAN_ID"]
        query = state["query"]
        print(query,notice_id)
        results = search_notice_in_vectordb(query=query, notice_id=notice_id)

        print(results)

        if not results:
            state["result"] = (
                "❌ 관련 정보를 찾을 수 없습니다.\n\n"
                # "👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요."
            )
            return state

            


        # ✅ 벡터 검색 결과를 LLM에게 주고 답변 생성
        chunks_text = "\n".join(
            f"- {doc.page_content.strip()}" for doc in results
        )


        pages = [docs.metadata.get('page') for docs in results]
        notice_id = results[0].metadata.get('notice_id')

        print("페이지번호 중복제거:", pages)
        print("notice_id: ", notice_id)


        state["pages"] = pages[0]
        state["pages_flag"] = True
        state["notice_id"] = notice_id

        data_to_send = {
            "pages": pages,
            "notice_id": notice_id
        }


        prompt = (
            f"너는 주택 청약 상담사야. 아래 [자료]를 참고해 [질문]에 친절하고 쉽게 답변해 줘.\n\n"
            f"[자료]\n{chunks_text}\n\n"
            f"[질문]\n{query}"
        )

        answer = llm.invoke(prompt)
        state["result"] = markdown.markdown(answer)
        # state["result"] = answer + "\n\n👉 새로운 조건으로 검색하려면 'new', 대화를 종료하려면 'exit'를 입력해주세요."
        return state

    return state
