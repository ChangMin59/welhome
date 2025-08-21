import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

#  병합된 모델 경로
merged_model_path = "/home/alpaco/test/fine/merged_model"
base_tokenizer_path = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B"

#  병합된 모델 로드 (PeftModel ❌)
model = AutoModelForCausalLM.from_pretrained(
    merged_model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto"
).eval()

# ✅ 토크나이저는 원본 모델의 것을 그대로 사용
tokenizer = AutoTokenizer.from_pretrained(base_tokenizer_path)

# ✅ 추론 함수
def ask_clovax_clean(question: str, max_new_tokens=128) -> str:
    messages = [
        {"role": "tool_list", "content": ""},
        {"role": "system", "content": "- AI 언어모델의 이름은 \"CLOVA X\" 이며 네이버에서 만들었다.\n- 오늘은 2025년 04월 24일(목)이다."},
        {"role": "user", "content": question}
    ]

    enc = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
    input_ids = enc.to(model.device) if isinstance(enc, torch.Tensor) else enc["input_ids"].to(model.device)
    attention_mask = enc["attention_mask"].to(model.device) if isinstance(enc, dict) else None

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=False,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id
        )

    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=False)

    # 🧹 응답 파싱
    if "<|im_start|>assistant" in decoded:
        response = decoded.split("<|im_start|>assistant")[-1]
        return response.replace("<|im_end|>", "").split("<|")[0].strip()

    return decoded.strip()