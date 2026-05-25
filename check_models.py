import os
import google.generativeai as genai
from dotenv import load_dotenv

# 強制讀取你的私人金鑰
load_dotenv(override=True)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("--- 🔍 正在查詢你的 API 金鑰目前真正支援的模型清單 ---")

try:
    # 叫 Google 把所有可以生成內容 (generateContent) 的模型交出來
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ 可用模型：{m.name}")
except Exception as e:
    print(f"❌ 查詢失敗：{e}")