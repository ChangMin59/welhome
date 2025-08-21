import os
import torch
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pdf2image import convert_from_path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from graph.main_graph import app as chatbot_app  # 주택/대출 챗봇
# from PEFT.naver import ask_clovax_clean  ❌ 이름 충돌로 사용 불가

# ✅ Clova X QnA 함수 정의 (직접 포함)
base_model_path = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B"
adapter_path = "/home/alpaco/test/fine/finetuned_hyperclovax30"

base_model = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
model = PeftModel.from_pretrained(base_model, adapter_path).eval()
tokenizer = AutoTokenizer.from_pretrained(base_model_path)


def ask_clovax_clean(question: str, max_new_tokens=256) -> str:
    messages = [
        {"role": "tool_list", "content": ""},
        {"role": "system", "content": "- AI 언어모델의 이름은 \"CLOVA X\" 이며 네이버에서 만들었다.\n- 오늘은 2025년 04월 24일(목)이다."},
        {"role": "user", "content": question}
    ]
    enc = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
    input_ids = enc["input_ids"].to(model.device) if isinstance(enc, dict) else enc.to(model.device)
    attention_mask = enc["attention_mask"].to(model.device) if isinstance(enc, dict) else torch.ones_like(input_ids)
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=False,
            repetition_penalty=1.2,
            eos_token_id=tokenizer.eos_token_id
        )
    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=False)
    if "<|im_start|>assistant" in decoded:
        response = decoded.split("<|im_start|>assistant")[-1]
        return response.replace("<|im_end|>", "").split("<|")[0].strip()
    return decoded.strip()


# ✅ FastAPI 앱 설정
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ QnA 전역 히스토리 (임시)
qna_history = []


# ✅ Chat API 모델 정의 (JSON 기반)
class ChatRequest(BaseModel):
    query: str
    state: dict


class ChatResponse(BaseModel):
    result: str
    state: dict


# ✅ PDF → PNG 변환 함수
def convert_pdf_to_page_png(pdf_path: str, output_dir: str, page_number: int):
    output_path = os.path.join(output_dir, f"page_{page_number}.png")
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"🗑 기존 파일 삭제: {output_path}")
    os.makedirs(output_dir, exist_ok=True)
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
    if images:
        images[0].save(output_path, "PNG")
        print(f"✅ PNG 저장됨: {output_path}")
    else:
        print("⚠️ PDF에서 페이지 변환 실패")


# ✅ 메인 페이지
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ✅ 주택/대출 챗봇: GET (UI 페이지)
@app.get("/chat", response_class=HTMLResponse)
async def serve_chat_ui(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


# ✅ 주택/대출 챗봇: POST (API 처리)
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    state = request.state or {}
    query = request.query.strip()

    if query.startswith("페이지") and query[3:].strip().isdigit():
        page_number = int(query[3:].strip())
        state["pages"] = page_number
        state["current_page"] = page_number
        notice_id = state.get("notice_id")
        if notice_id:
            convert_pdf_to_page_png(f"static/{notice_id}.pdf", "static/pages", page_number)
        return ChatResponse(result=f"(페이지 {page_number})", state=state)

    state["query"] = query
    new_state = chatbot_app.invoke(state)

    try:
        notice_id = new_state.get("notice_id")
        pages = new_state.get("pages")
        if notice_id and pages:
            page_number = int(pages[0] if isinstance(pages, list) else pages)
            new_state["current_page"] = page_number
            convert_pdf_to_page_png(f"static/{notice_id}.pdf", "static/pages", page_number)
    except Exception as e:
        print("❌ 페이지 이미지 처리 실패:", e)

    return ChatResponse(result=new_state.get("result", ""), state=new_state)


# ✅ Q&A 챗봇 (ClovaX 기반)
@app.get("/qna", response_class=HTMLResponse)
async def get_qna(request: Request):
    return templates.TemplateResponse("qna.html", {
        "request": request,
        "chat_history": qna_history
    })


@app.post("/qna", response_class=HTMLResponse)
async def post_qna(request: Request, user_input: str = Form(...)):
    qna_history.append({"user": user_input, "bot": None})
    answer = ask_clovax_clean(user_input)
    qna_history[-1]["bot"] = answer
    return templates.TemplateResponse("qna.html", {
        "request": request,
        "chat_history": qna_history
    })


# ✅ 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8111)
