import streamlit as st
import datetime
import re
from utils.db import get_supabase, get_profile
import extra_streamlit_components as stx

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

    # 쿠키 매니저 초기화
    cookie_manager = stx.CookieManager()
    
    # 자동 로그인 로직 (새로고침 시 세션 복구)
    if st.session_state.user is None:
        all_cookies = cookie_manager.get_all()
        if all_cookies:
            access_token = all_cookies.get("sb-access-token")
            refresh_token = all_cookies.get("sb-refresh-token")
            
            if access_token and refresh_token:
                try:
                    supabase = get_supabase()
                    res = supabase.auth.set_session(access_token, refresh_token)
                    if res.user:
                        st.session_state.user = res.user
                        st.session_state.profile = get_profile(res.user.id)
                        st.rerun()
                except Exception:
                    pass

    supabase = get_supabase()

    # 사이드바 로그인 상태 관리
    if not st.session_state.user:
        show_login_page(cookie_manager)
    else:
        show_sidebar_nav(cookie_manager)

def show_login_page(cookie_manager):
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
                
                # 쿠키에 세션 정보 저장
                if response.session:
                    cookie_manager.set("sb-access-token", response.session.access_token, key="set_access")
                    cookie_manager.set("sb-refresh-token", response.session.refresh_token, key="set_refresh")
                
                # 쿠키가 브라우저에 기록될 수 있도록 아주 잠시 대기 후 리런
                import time
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"로그인 실패: {str(e)}")

    with tab2:
        # DB에서 설정값 및 약관 불러오기
        supabase = get_supabase()
        settings_res = supabase.table("settings").select("*").in_("key", ["privacy_policy", "privacy_disagree_message", "max_grade", "max_class", "max_student_number"]).execute()
        settings_dict = {r['key']: r['value'] for r in settings_res.data}
        
        max_grade_val = int(settings_dict.get('max_grade', 3))
        max_class_val = int(settings_dict.get('max_class', 15))
        max_student_val = int(settings_dict.get('max_student_number', 40))

        # 1. 가입 유형 선택 (맨 위로 이동)
        role_type = st.radio("가입 유형", ["학생", "교사/관리자"], horizontal=True)
        
        if role_type == "학생":
            st.caption("💡 학년, 반, 번호 정보를 선택해 주세요.")
            col_g, col_c, col_n = st.columns(3)
            with col_g: grade = st.selectbox("학년", options=list(range(1, max_grade_val + 1)))
            with col_c: class_room = st.selectbox("반", options=list(range(1, max_class_val + 1)))
            with col_n: student_number = st.selectbox("번호", options=list(range(1, max_student_val + 1)))
            signup_code = None
        else:
            st.caption("💡 선생님이나 관리자는 발급받은 '가입 코드'가 반드시 필요합니다.")
            signup_code = st.text_input("가입 코드")
            grade, class_room, student_number = None, None, None

        st.divider()
        
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
            
            # 가입 코드 및 역할 결정 로직
            role = "student" # 기본값
            if role_type == "교사/관리자":
                if not signup_code:
                    st.error("교사/관리자로 가입하려면 가입 코드가 필요합니다.")
                    return
                
                code_check = supabase.table("signup_codes").select("*").eq("code", signup_code).eq("is_active", True).execute()
                if not code_check.data:
                    st.error("유효하지 않거나 비활성화된 가입 코드입니다.")
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
                profile_data = {
                    "id": auth_resp.user.id,
                    "email": new_email,
                    "full_name": full_name,
                    "role": role,
                    "birth_date": str(birth_date),
                    "phone_number": phone,
                    "privacy_consent": True
                }
                
                # 학생인 경우 학년/반/번호 추가 (DB 컬럼명: grade, class_room, student_number)
                if role == "student":
                    profile_data.update({
                        "grade": grade,
                        "class_room": class_room,
                        "student_number": student_number
                    })
                
                supabase.table("profiles").insert(profile_data).execute()
                
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

def show_sidebar_nav(cookie_manager):
    profile = st.session_state.profile
    
    # 사이드바 스타일 커스텀 CSS
    st.markdown("""
        <style>
            /* 1. 라디오 버튼의 원형 아이콘 완전 숨기기 (더 강력한 선택자) */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] ~ div {
                display: none !important;
            }
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child:not([data-testid="stMarkdownContainer"]) {
                display: none !important;
            }
            
            /* 2. 라디오 그룹 내 레이블을 블록 버튼 스타일로 변경 */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label {
                padding: 0.8rem 1.2rem !important;
                border-radius: 12px !important;
                margin-bottom: 8px !important;
                border: 1px solid transparent !important;
                transition: all 0.25s ease !important;
                width: 100% !important;
                cursor: pointer !important;
                background-color: transparent !important;
            }
            
            /* 3. 마우스 호버 시 스타일 */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
                background-color: rgba(102, 126, 234, 0.08) !important;
                border: 1px solid rgba(102, 126, 234, 0.2) !important;
            }
            
            /* 4. 선택된 항목(Checked) 스타일 - 블록 배경 및 테두리 강조 */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label[aria-checked="true"] {
                background-color: rgba(102, 126, 234, 0.15) !important;
                border: 1px solid rgba(102, 126, 234, 0.5) !important;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1) !important;
            }
            
            /* 5. 텍스트 스타일 (폰트 크기 및 정렬) */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label p {
                font-size: 1.15rem !important;
                font-weight: 500 !important;
                color: #31333F !important;
                margin: 0 !important;
            }
            
            /* 6. 선택된 항목의 텍스트 강조 */
            div[data-testid="stSidebar"] div[data-testid="stRadio"] label[aria-checked="true"] p {
                font-weight: 700 !important;
                color: #4c51bf !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        # 사용자 프로필 영역 (고급스럽게)
        role_labels = {"admin": "최고 관리자", "teacher": "교사", "student": "학생"}
        role_display = role_labels.get(profile['role'], profile['role'].capitalize())
        
        st.markdown(f"""
            <div style="padding: 1.2rem; border-radius: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 0.3rem;">어서오세요!</div>
                <div style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem;">{profile['full_name']} {role_display}님</div>
                <div style="font-size: 0.8rem; background: rgba(255,255,255,0.2); padding: 3px 10px; border-radius: 20px; display: inline-block;">
                    {profile['email']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 메뉴 구성 (아이콘 추가)
        menu_items = []
        if profile['role'] == 'admin':
            menu_map = {
                "🏠 대시보드": "대시보드",
                "🔑 관리자 코드 관리": "관리자 코드 관리",
                "⚙️ 시스템 설정": "시스템 설정"
            }
        elif profile['role'] == 'teacher':
            menu_map = {
                "🏠 대시보드": "대시보드",
                "🏫 수업 관리": "수업 관리",
                "📅 출결 관리": "출결 관리",
                "📝 과제/루브릭 관리": "과제/루브릭 관리",
                "📊 평가 및 내보내기": "평가 및 내보내기"
            }
        else: # student
            menu_map = {
                "🏠 대시보드": "대시보드",
                "📤 과제 제출": "과제 제출",
                "📂 마이 포트폴리오": "마이 포트폴리오"
            }
            
        choice_label = st.radio("메뉴", list(menu_map.keys()), label_visibility="collapsed")
        choice = menu_map[choice_label]
        
        st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True) # 여백 채우기
        st.divider()
        
        if st.sidebar.button("🚪 로그아웃", use_container_width=True, type="secondary"):
            get_supabase().auth.sign_out()
            st.session_state.user = None
            st.session_state.profile = None
            
            # 쿠키 삭제
            cookie_manager.delete("sb-access-token")
            cookie_manager.delete("sb-refresh-token")
            
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
    
    elif profile['role'] == 'admin':
        from views.admin_view import show_admin_dashboard, show_signup_code_management
        if choice == "대시보드":
            st.header("📍 관리자 대시보드")
            st.info("시스템 전체 현황을 파악할 수 있는 대시보드입니다. 현재 준비 중입니다.")
        elif choice == "관리자 코드 관리":
            show_signup_code_management()
        elif choice == "시스템 설정":
            show_admin_dashboard()

if __name__ == "__main__":
    main()
