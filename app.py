import streamlit as st
import datetime
import re
from utils.db import get_supabase, get_profile

st.set_page_config(
    page_title="AI/정보 통합 수업 관리 시스템",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (프리미엄 디자인 적용)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .card {
        padding: 1.5rem;
        border-radius: 12px;
        background-color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "profile" not in st.session_state:
        st.session_state.profile = None

    supabase = get_supabase()

    # 사이드바 로그인 상태 관리
    if not st.session_state.user:
        show_login_page()
    else:
        show_sidebar_nav()

def show_login_page():
    st.title("🎓 AI/정보 통합 수업 관리")
    st.subheader("로그인하여 수업을 시작하세요")
    
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True):
            try:
                response = get_supabase().auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.session_state.profile = get_profile(response.user.id)
                st.rerun()
            except Exception as e:
                st.error(f"로그인 실패: {str(e)}")

    with tab2:
        st.info("선생님께 받은 '가입 코드'가 필요합니다.")
        new_email = st.text_input("이메일", key="reg_email")
        new_password = st.text_input("비밀번호", type="password", key="reg_pass", help="한글 및 영어 대문자는 사용하실 수 없습니다.")
        
        # 실시간 유효성 체크 로직
        if new_password:
            has_korean = re.search("[ㄱ-ㅎㅏ-ㅣ가-힣]", new_password)
            has_upper = re.search("[A-Z]", new_password)
            
            if has_korean:
                st.error("❌ 한글을 포함할 수 없습니다.")
            if has_upper:
                st.error("❌ 영어 대문자를 포함할 수 없습니다.")
            if not has_korean and not has_upper:
                st.success("✅ 사용 가능한 비밀번호 형식입니다.")
        else:
            st.caption("⚠️ 영어 소문자, 숫자, 특수문자만 사용 가능합니다.")

        confirm_password = st.text_input("비밀번호 확인", type="password", key="reg_pass_conf")
        
        # 실시간 일치 여부 체크 로직
        if confirm_password:
            if new_password == confirm_password:
                st.success("✅ 비밀번호가 일치합니다.")
            else:
                st.error("❌ 비밀번호가 일치하지 않습니다.")
        full_name = st.text_input("이름")
        birth_date = st.date_input("생년월일", min_value=datetime.date(1950, 1, 1), max_value=datetime.date.today())
        phone = st.text_input("핸드폰 번호")
        signup_code = st.text_input("가입 코드")
        
        # DB에서 약관 및 안내문구 불러오기
        supabase = get_supabase()
        settings_res = supabase.table("settings").select("*").in_("key", ["privacy_policy", "privacy_disagree_message"]).execute()
        settings_dict = {r['key']: r['value'] for r in settings_res.data}
        
        policy_text = settings_dict.get('privacy_policy', "약관 내용이 없습니다.")
        disagree_msg = settings_dict.get('privacy_disagree_message', "⚠️ 동의가 필요합니다.")

        with st.expander("📄 개인정보 수집 및 이용 약관 보기"):
            st.write(policy_text)

        consent_opt = st.radio("개인정보 수집 및 이용 동의", ["동의함", "동의하지 않음"], index=1, horizontal=True)
        
        if consent_opt == "동의하지 않음":
            st.warning(disagree_msg)

        if st.button("회원가입", use_container_width=True):
            if consent_opt == "동의하지 않음":
                st.error(disagree_msg)
                return
            
            if new_password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
                return
            
            # 한글 및 대문자 검증
            if re.search("[ㄱ-ㅎㅏ-ㅣ가-힣]", new_password):
                st.error("비밀번호에 한글을 포함할 수 없습니다.")
                return
            if re.search("[A-Z]", new_password):
                st.error("비밀번호에 영어 대문자를 포함할 수 없습니다.")
                return
            
            # 가입 코드 확인 로직
            supabase = get_supabase()
            code_check = supabase.table("signup_codes").select("*").eq("code", signup_code).eq("is_active", True).execute()
            
            if not code_check.data:
                st.error("유효하지 않은 가입 코드입니다.")
                return
            
            role = code_check.data[0]['role']
            
            try:
                # 1. Auth 가입 시도
                auth_resp = supabase.auth.sign_up({"email": new_email, "password": new_password})
                
                if auth_resp.user is None:
                    # 이메일 확인이 켜져 있거나 중복 계정일 때의 처리
                    st.error("이미 사용 중인 이메일이거나 가입이 제한된 이메일입니다.")
                    return

                # 2. Profile 생성
                supabase.table("profiles").insert({
                    "id": auth_resp.user.id,
                    "email": new_email,
                    "full_name": full_name,
                    "role": role,
                    "birth_date": str(birth_date),
                    "phone_number": phone,
                    "privacy_consent": True
                }).execute()
                
                st.balloons() # 축하 효과
                st.success(f"🎉 {full_name}님, 회원가입이 완료되었습니다! 이제 로그인 탭에서 접속해 주세요.")
                
            except Exception as e:
                error_str = str(e).lower()
                if "user already registered" in error_str:
                    st.error("이미 사용 중인 이메일입니다. 다른 이메일을 사용하거나 로그인을 시도해 주세요.")
                elif "password" in error_str:
                    st.error("비밀번호 보안 정책에 위반되었습니다. (최소 6자 이상)")
                elif "email" in error_str:
                    st.error("유효하지 않은 이메일 형식입니다.")
                else:
                    st.error(f"가입 중 오류가 발생했습니다: {str(e)}")

def show_sidebar_nav():
    profile = st.session_state.profile
    st.sidebar.title(f"👋 {profile['full_name']}님")
    st.sidebar.write(f"역할: {profile['role'].capitalize()}")
    
    menu = []
    if profile['role'] == 'admin':
        menu = ["대시보드", "가입 코드 관리", "시스템 설정"]
    elif profile['role'] == 'teacher':
        menu = ["대시보드", "수업 관리", "출결 관리", "과제/루브릭 관리", "평가 및 내보내기"]
    elif profile['role'] == 'student':
        menu = ["대시보드", "과제 제출", "마이 포트폴리오"]
        
    choice = st.sidebar.radio("메뉴 선택", menu)
    
    if st.sidebar.button("로그아웃"):
        get_supabase().auth.sign_out()
        st.session_state.user = None
        st.session_state.profile = None
        st.rerun()
        
    # 역할별 페이지 렌더링
    if profile['role'] == 'teacher':
        from views.teacher_view import show_teacher_dashboard, show_class_management, show_attendance_management, show_assignment_management, show_evaluation_export
        if choice == "대시보드": show_teacher_dashboard()
        elif choice == "수업 관리": show_class_management()
        elif choice == "출결 관리": show_attendance_management()
        elif choice == "과제/루브릭 관리": show_assignment_management()
        elif choice == "평가 및 내보내기": show_evaluation_export()
    
    elif profile['role'] == 'student':
        from views.student_view import show_student_dashboard, show_assignment_submission, show_my_portfolio
        if choice == "대시보드": show_student_dashboard()
        elif choice == "과제 제출": show_assignment_submission()
        elif choice == "마이 포트폴리오": show_my_portfolio()
    
    else:
        st.header(f"📍 {choice}")
        st.write(f"{choice} 페이지 준비 중입니다.")

if __name__ == "__main__":
    main()
