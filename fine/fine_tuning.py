import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer,
    DataCollatorForLanguageModeling
)
from peft import get_peft_model, LoraConfig, TaskType

# ✅ 모델명 및 경로
model_name = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B"
output_dir = "/home/alpaco/lcmtest/naver/finetuned_hyperclovax30"

# ✅ 토크나이저 / 모델 로드
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.bfloat16
)

# ✅ PEFT (LoRA) 설정
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False,
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none"
)
model = get_peft_model(model, peft_config)

# ✅ 데이터 로드
with open("/home/alpaco/welhome/PEFT/fine_data.json", encoding="utf-8") as f:
    raw_data = json.load(f)

dataset = Dataset.from_list([
    {"instruction": item["instruction"], "output": item["output"]}
    for item in raw_data
])

# ✅ 전처리 함수
def preprocess(example):
    prompt_text = tokenizer.apply_chat_template(
        [
            {"role": "tool_list", "content": ""},
            {"role": "system", "content": "- AI 언어모델의 이름은 \"CLOVA X\" 이며 네이버에서 만들었다.\n- 오늘은 2025년 04월 24일(목)이다."},
            {"role": "user", "content": example["instruction"]}
        ],
        add_generation_prompt=True,
        tokenize=False
    )
    full_text = prompt_text + example["output"]

    tokenized = tokenizer(
        full_text,
        return_tensors="pt",
        max_length=1024,
        truncation=True,
        padding="max_length"
    )

    input_ids = tokenized["input_ids"][0]
    attention_mask = tokenized["attention_mask"][0]
    labels = input_ids.clone()

    prompt_len = len(tokenizer(prompt_text, return_tensors="pt")["input_ids"][0])
    labels[:prompt_len] = -100

    return {
        "input_ids": input_ids.tolist(),
        "attention_mask": attention_mask.tolist(),
        "labels": labels.tolist()
    }

# ✅ 데이터 분할
dataset_split = dataset.train_test_split(test_size=0.2, seed=42)
train_data = dataset_split["train"].map(preprocess)
val_data = dataset_split["test"].map(preprocess)

# ✅ 디버깅용 샘플 출력
print("\n🧪 [DEBUG SAMPLE 2개]")
for i in range(2):
    sample = train_data[i]
    decoded_input = tokenizer.decode(sample["input_ids"], skip_special_tokens=False)
    decoded_label = tokenizer.decode(
        [id if id != -100 else tokenizer.pad_token_id for id in sample["labels"]],
        skip_special_tokens=False
    )
    prompt_len = sample["labels"].index(
        next(label for label in sample["labels"] if label != -100)
    )

    print(f"\n🔹 [Sample {i+1}]")
    print(f"🔸 instruction : {dataset_split['train'][i]['instruction']}")
    print(f"🔸 output      : {dataset_split['train'][i]['output']}")
    print(f"🔸 prompt_len  : {prompt_len}")
    print(f"🔸 input_ids[:30]: {sample['input_ids'][:30]}")
    print(f"🔸 labels[:30]   : {sample['labels'][:30]}")
    print(f"🔸 decoded_input:\n{decoded_input}")
    print(f"🔸 decoded_label:\n{decoded_label}")

# ✅ 데이터 콜레이터
collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# ✅ 학습 설정
training_args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=30,
    learning_rate=5e-5,
    logging_dir="./logs",
    logging_steps=10,
    save_strategy="epoch",
    bf16=True,
    report_to="none"
)

# ✅ Trainer 구성
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=val_data,
    tokenizer=tokenizer,
    data_collator=collator
)

# ✅ 학습 시작
print("\n🚀 학습 시작")
trainer.train()

# ✅ 최종 평가
print("\n🧪 최종 검증:")
metrics = trainer.evaluate()
print(metrics)

# ✅ 모델 저장
print("\n✅ 학습 완료 - 모델 저장 중...")
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
model.config.save_pretrained(output_dir)
print(f"✅ 저장 완료: {output_dir}")
