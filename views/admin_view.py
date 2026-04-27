import streamlit as st
import pandas as pd
from utils.db import get_supabase

def show_admin_dashboard():
    st.subheader("⚙️ 시스템 설정")
    supabase = get_supabase()
    
    # 설정 불러오기
    res_policy = supabase.table("settings").select("*").eq("key", "privacy_policy").single().execute()
    res_disagree = supabase.table("settings").select("*").eq("key", "privacy_disagree_message").single().execute()
    res_retention = supabase.table("settings").select("*").eq("key", "data_retention_years").single().execute()
    
    current_policy = res_policy.data['value'] if res_policy.data else ""
    current_disagree = res_disagree.data['value'] if res_disagree.data else ""
    current_retention = res_retention.data['value'] if res_retention.data else "3"
    
    with st.form("edit_settings_form"):
        new_policy = st.text_area("1. 개인정보 처리방침 약관 수정", value=current_policy, height=200)
        new_disagree = st.text_input("2. 동의 거부 시 안내 문구 수정", value=current_disagree)
        new_retention = st.number_input("3. 개인정보 자동 파기 기간 (연 단위)", min_value=1, max_value=10, value=int(current_retention))
        
        if st.form_submit_button("설정 저장"):
            try:
                supabase.table("settings").update({"value": new_policy}).eq("key", "privacy_policy").execute()
                supabase.table("settings").update({"value": new_disagree}).eq("key", "privacy_disagree_message").execute()
                supabase.table("settings").update({"value": str(new_retention)}).eq("key", "data_retention_years").execute()
                st.success("모든 설정이 성공적으로 저장되었습니다.")
            except Exception as e:
                st.error(f"저장 실패: {str(e)}")

def show_signup_code_management():
    supabase = get_supabase()
    
    st.subheader("🔑 그룹 가입 코드 생성")
    with st.form("new_signup_code"):
        code = st.text_input("가입 코드 (예: CLASS2026_1A)")
        role = st.selectbox("부여할 권한", ["student", "teacher"])
        group_name = st.text_input("그룹 이름 (예: 2026학년도 1학년 1반)")
        
        if st.form_submit_button("코드 생성"):
            try:
                supabase.table("signup_codes").insert({
                    "code": code,
                    "role": role,
                    "group_name": group_name,
                    "is_active": True
                }).execute()
                st.success(f"'{code}' 코드가 성공적으로 생성되었습니다.")
            except Exception as e:
                st.error(f"생성 실패: {str(e)}")

    st.divider()
    st.subheader("📋 생성된 가입 코드 목록")
    codes = supabase.table("signup_codes").select("*").execute()
    if codes.data:
        df = pd.DataFrame(codes.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("생성된 코드가 없습니다.")
