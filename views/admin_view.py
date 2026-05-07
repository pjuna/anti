import streamlit as st
import pandas as pd
from utils.db import get_supabase, generate_random_code

def show_admin_dashboard():
    """최고 관리자 대시보드 - 시스템 설정을 탭별로 분리하여 관리"""
    st.header("⚙️ 시스템 설정 센터")
    
    # 설정 데이터 통합 로드
    supabase = get_supabase()
    settings_res = supabase.table("settings").select("*").execute()
    settings_dict = {r['key']: r['value'] for r in settings_res.data}

    # 탭 메뉴 구성
    tabs = st.tabs(["🔒 보안 및 약관", "🎓 학적 범위 설정", "📊 데이터 통계"])

    with tabs[0]:
        render_privacy_security_settings(settings_dict)
    
    with tabs[1]:
        render_academic_range_settings(settings_dict)
        
    with tabs[2]:
        st.info("실시간 시스템 사용 통계 및 로그 기능이 준비 중입니다.")

def render_privacy_security_settings(settings_dict):
    st.subheader("🔒 개인정보 처리 및 보안 설정")
    
    with st.form("privacy_settings_form"):
        current_policy = settings_dict.get('privacy_policy', "")
        current_disagree = settings_dict.get('privacy_disagree_message', "")
        current_retention = settings_dict.get('data_retention_years', "3")
        
        new_policy = st.text_area("1. 개인정보 처리방침 약관", value=current_policy, height=200)
        new_disagree = st.text_input("2. 동의 거부 시 안내 문구", value=current_disagree)
        new_retention = st.number_input("3. 개인정보 자동 파기 기간 (연 단위)", min_value=1, max_value=10, value=int(current_retention))
        
        if st.form_submit_button("보안 설정 저장", use_container_width=True):
            save_settings({
                "privacy_policy": new_policy,
                "privacy_disagree_message": new_disagree,
                "data_retention_years": str(new_retention)
            })

def render_academic_range_settings(settings_dict):
    st.subheader("🎓 학적 정보 입력 범위 설정")
    st.caption("회원가입 시 학생들이 선택할 수 있는 학년, 반, 번호의 최대치를 설정합니다.")
    
    with st.form("academic_range_form"):
        current_max_grade = settings_dict.get('max_grade', "3")
        current_max_class = settings_dict.get('max_class', "15")
        current_max_student = settings_dict.get('max_student_number', "40")
        
        col1, col2, col3 = st.columns(3)
        with col1: new_max_grade = st.number_input("최대 학년", min_value=1, max_value=6, value=int(current_max_grade))
        with col2: new_max_class = st.number_input("최대 반", min_value=1, max_value=30, value=int(current_max_class))
        with col3: new_max_student = st.number_input("최대 번호", min_value=1, max_value=60, value=int(current_max_student))
        
        if st.form_submit_button("범위 설정 저장", use_container_width=True):
            save_settings({
                "max_grade": str(new_max_grade),
                "max_class": str(new_max_class),
                "max_student_number": str(new_max_student)
            })

def save_settings(settings_to_save):
    """설정값을 DB에 업서트하고 페이지를 새로고침"""
    supabase = get_supabase()
    try:
        data = [{"key": k, "value": v} for k, v in settings_to_save.items()]
        supabase.table("settings").upsert(data).execute()
        st.success("설정이 성공적으로 반영되었습니다.")
        st.rerun()
    except Exception as e:
        st.error(f"설정 저장 중 오류가 발생했습니다: {str(e)}")

def show_signup_code_management():
    """관리자 코드 관리 모듈"""
    supabase = get_supabase()
    
    st.header("🔑 관리자용 가입 코드 관리")
    st.caption("선생님이나 새로운 관리자를 초대하기 위한 전용 코드를 생성하고 관리합니다. (학생은 코드 없이 가입합니다.)")
    
    # 1. 새로운 코드 생성 섹션
    with st.expander("➕ 새 관리자/교사 코드 생성", expanded=False):
        if "random_code" not in st.session_state:
            st.session_state.random_code = generate_random_code(8)
            
        col1, col2 = st.columns([3, 1])
        with col1:
            code_input = st.text_input("가입 코드", value=st.session_state.random_code)
        with col2:
            st.write("")
            st.write("")
            if st.button("랜덤", key="gen_code_btn", use_container_width=True):
                st.session_state.random_code = generate_random_code(8)
                st.rerun()

        with st.form("new_signup_code"):
            role = st.selectbox("부여할 권한", ["teacher", "admin"])
            group_name = st.text_input("그룹 이름 (예: 2026학년도 교사용 코드)")
            
            if st.form_submit_button("코드 등록", use_container_width=True):
                if not code_input or not group_name:
                    st.error("가입 코드와 그룹 이름을 모두 입력해주세요.")
                else:
                    try:
                        supabase.table("signup_codes").insert({
                            "code": code_input,
                            "role": role,
                            "group_name": group_name,
                            "is_active": True
                        }).execute()
                        st.success(f"'{code_input}' 코드가 성공적으로 등록되었습니다.")
                        st.session_state.random_code = generate_random_code(8)
                        st.rerun()
                    except Exception as e:
                        st.error(f"등록 실패: {str(e)}")

    st.divider()
    
    # 2. 코드 목록 및 관리 섹션
    st.subheader("📋 발급된 코드 리스트")
    codes = supabase.table("signup_codes").select("*").order("created_at", desc=True).execute()
    
    if codes.data:
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2, 1.2, 3, 1.2, 0.8])
        h_col1.markdown("**가입 코드**")
        h_col2.markdown("**권한**")
        h_col3.markdown("**그룹명**")
        h_col4.markdown("**상태**")
        h_col5.markdown("**삭제**")
        st.write("---")

        for item in codes.data:
            c1, c2, c3, c4, c5 = st.columns([2, 1.2, 3, 1.2, 0.8])
            c1.code(item['code'])
            c2.write(f"👤 {item['role']}")
            c3.write(item['group_name'])
            
            status_text = "✅ 활성" if item['is_active'] else "❌ 비활성"
            if c4.button(status_text, key=f"tg_{item['code']}", use_container_width=True):
                supabase.table("signup_codes").update({"is_active": not item['is_active']}).eq("code", item['code']).execute()
                st.rerun()
            
            if c5.button("🗑️", key=f"del_{item['code']}", use_container_width=True):
                supabase.table("signup_codes").delete().eq("code", item['code']).execute()
                st.rerun()
    else:
        st.info("발급된 코드가 없습니다.")
