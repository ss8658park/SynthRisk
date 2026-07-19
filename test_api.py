from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# 사용 가능한 모델 목록에서 5.6 계열 찾기
models = client.models.list()
for m in models.data:
    if "5.6" in m.id or "5-6" in m.id:
        print(m.id)
print("---")
# 그냥 전체에서 gpt 계열도 몇 개 확인
gpt_models = sorted(m.id for m in models.data if m.id.startswith("gpt"))
for mid in gpt_models[:30]:
    print(mid)