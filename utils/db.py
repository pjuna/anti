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

def upload_file_to_storage(file, user_id, file_name):
    """Supabase Storage에 파일을 업로드하고 URL을 반환"""
    supabase = get_supabase()
    bucket_name = "submissions"
    
    # 보안 정책에 따라 유저 ID를 폴더명으로 사용 (예: user_id/filename)
    file_path = f"{user_id}/{file_name}"
    
    try:
        # 파일 업로드 (기존 파일이 있으면 덮어쓰기)
        res = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file.getvalue(),
            file_options={"upsert": "true", "content-type": file.type}
        )
        
        # 파일의 서명된 URL 생성 (60분 유효) 또는 공용 URL 획득
        # 여기서는 RLS를 사용하므로 signed url 방식을 권장하지만, 간편함을 위해 public url 혹은 경로 반환
        return file_path
    except Exception as e:
        st.error(f"파일 업로드 중 오류 발생: {str(e)}")
        return None
