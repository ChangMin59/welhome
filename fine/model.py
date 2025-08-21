import torch
from transformers import AutoModelForCausalLM
from peft import PeftModel

# 경로 설정
base_model_path = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B"  # 원본 모델
adapter_path = "/home/alpaco/test/fine/finetuned_hyperclovax30"            # LoRA 어댑터 경로
merged_output_path = "/home/alpaco/test/fine/merged_model"                 # 병합 결과 저장 경로

# 1. 원본 모델 로드
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# 2. LoRA 어댑터 로드 및 병합
print("🚀 LoRA 어댑터 병합 중...")
lora_model = PeftModel.from_pretrained(base_model, adapter_path)
merged_model = lora_model.merge_and_unload()

# 3. 병합된 모델 저장
merged_model.save_pretrained(merged_output_path)
print(f"✅ 병합된 모델 저장 완료: {merged_output_path}")
