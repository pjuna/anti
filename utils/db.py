import streamlit as st
from supabase import create_client, Client
import random
import string

# Supabase 클라이언트 초기화
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def generate_random_code(length=6):
    """6자리 랜덤 대문자+숫자 코드 생성"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_profile(user_id):
    supabase = get_supabase()
    result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    return result.data

def normalize_smart_quotes(text):
    """스마트 따옴표를 표준 따옴표로 변환"""
    if not text:
        return ""
    quotes_map = {
        '‘': "'", '’': "'", '‚': "'", '‛': "'",
        '“': '"', '”': '"', '„': '"', '‟': '"'
    }
    for k, v in quotes_map.items():
        text = text.replace(k, v)
    return text

def verify_code_consistency(report_text, source_code):
    """보고서 내의 코드 조각이 소스코드와 일치하는지 검증"""
    import re
    # 마크다운 코드 블록 추출 (```python ... ```)
    snippets = re.findall(r'```(?:python)?\s*(.*?)\s*```', report_text, re.DOTALL)
    
    if not snippets:
        return True, "코드 블록이 보고서에 없습니다."
    
    source_clean = normalize_smart_quotes(source_code).strip()
    
    for i, snippet in enumerate(snippets):
        snippet_clean = normalize_smart_quotes(snippet).strip()
        if snippet_clean not in source_clean:
            return False, f"코드 조각 {i+1}이 제출된 소스코드와 일치하지 않습니다."
            
    return True, "모든 코드 조각이 소스코드와 일치합니다."
