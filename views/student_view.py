import streamlit as st
import pandas as pd
from utils.db import get_supabase

def show_student_dashboard():
    supabase = get_supabase()
    user_id = st.session_state.user.id
    profile = st.session_state.profile
    
    st.subheader(f"🚀 {profile['full_name']} 학생의 대시보드")
    
    # 소속 수업 정보 확인
    if not profile.get('class_id'):
        st.warning("아직 소속된 수업이 없습니다. 수업 참여 코드를 입력하세요.")
        join_code = st.text_input("수업 참여 코드 (6자리)")
        if st.button("수업 참여"):
            class_data = supabase.table("classes").select("*").eq("join_code", join_code).execute()
            if class_data.data:
                class_id = class_data.data[0]['id']
                supabase.table("profiles").update({"class_id": class_id}).eq("id", user_id).execute()
                st.session_state.profile['class_id'] = class_id
                st.success(f"'{class_data.data[0]['name']}' 수업에 참여되었습니다!")
                st.rerun()
            else:
                st.error("유효하지 않은 코드입니다.")
    else:
        class_info = supabase.table("classes").select("*").eq("id", profile['class_id']).single().execute()
        st.info(f"현재 참여 중인 수업: **{class_info.data['name']}** ({class_info.data['academic_year']}년 {class_info.data['semester']})")

def show_assignment_submission():
    from utils.db import verify_code_consistency, upload_file_to_storage
    supabase = get_supabase()
    user_id = st.session_state.user.id
    profile = st.session_state.profile
    
    if not profile.get('class_id'):
        st.warning("먼저 대시보드에서 수업 참여 코드를 입력하세요.")
        return

    st.title("📝 과제 제출 센터")
    st.markdown("---")
    
    # 해당 수업의 과제 목록 가져오기
    assignments = supabase.table("assignments").select("*").eq("class_id", profile['class_id']).execute()
    
    if not assignments.data:
        st.info("현재 진행 중인 과제가 없습니다.")
        return

    assign_options = {a['title']: a['id'] for a in assignments.data}
    selected_title = st.selectbox("제출할 과제를 선택하세요", list(assign_options.keys()))
    assign_id = assign_options[selected_title]
    
    # 과제 상세 정보 표시
    selected_assign = next(a for a in assignments.data if a['id'] == assign_id)
    with st.expander("📌 과제 지시사항 및 루브릭 확인", expanded=True):
        st.info(selected_assign['content'])
        st.write("**평가 항목 (Rubric):**")
        for item in selected_assign['rubric_data']:
            st.write(f"- {item['name']}: {item['max_score']}점 만점")

    # 기존 제출물 확인
    existing = supabase.table("submissions").select("*").eq("assignment_id", assign_id).eq("student_id", user_id).execute()

    st.subheader("📤 제출물 작성")
    with st.container():
        st.write("1. 설계 및 결과 보고서 (텍스트)")
        st.caption("보고서 내에 소스코드를 포함할 때는 ```python ... ``` 형식을 사용하세요.")
        report_text = st.text_area("보고서 내용을 입력하세요", height=300, value=existing.data[0]['text_report'] if existing.data else "", placeholder="알고리즘 설계 및 문제 해결 과정을 서술하세요...")
        
        st.write("2. 실제 실행 소스코드")
        source_code = st.text_area("Python 코드 원본", height=200, value=existing.data[0]['source_code'] if existing.data else "", placeholder="실제 실행한 Python 코드를 복사해서 붙여넣으세요.")
        
        st.write("3. 추가 증빙 자료 (PDF, HWP, 이미지 등)")
        uploaded_file = st.file_uploader("파일 선택 (기존 파일이 있으면 덮어씌워집니다)", type=['pdf', 'png', 'jpg', 'hwp', 'zip'])
        
        if st.button("과제 제출 및 검증", use_container_width=True, type="primary"):
            if not report_text or not source_code:
                st.error("보고서 내용과 소스코드는 필수 항목입니다.")
                return

            with st.status("제출 처리 및 코드 검증 중...", expanded=True) as status:
                # 1. 파일 업로드 처리
                file_url = existing.data[0]['file_url'] if existing.data else None
                if uploaded_file:
                    st.write("📁 파일을 서버에 업로드 중...")
                    uploaded_path = upload_file_to_storage(uploaded_file, user_id, uploaded_file.name)
                    if uploaded_path:
                        file_url = uploaded_path
                        st.write("✅ 파일 업로드 완료!")
                
                # 2. 코드 교차 검증 (Strict Verify)
                st.write("🔍 보고서와 소스코드 일치 여부 검증 중...")
                is_valid, message = verify_code_consistency(report_text, source_code)
                
                if not is_valid:
                    st.error(f"❌ 검증 실패: {message}")
                else:
                    st.success("✅ 검증 완료: 보고서와 소스코드가 정확히 일치합니다.")

                # 3. DB 저장
                sub_data = {
                    "assignment_id": assign_id,
                    "student_id": user_id,
                    "text_report": report_text,
                    "source_code": source_code,
                    "file_url": file_url,
                    "is_verified": is_valid
                }
                
                try:
                    if existing.data:
                        supabase.table("submissions").update(sub_data).eq("id", existing.data[0]['id']).execute()
                    else:
                        supabase.table("submissions").insert(sub_data).execute()
                    
                    status.update(label="🚀 과제 제출 완료!", state="complete", expanded=False)
                    st.toast("과제가 성공적으로 제출되었습니다!")
                except Exception as e:
                    st.error(f"DB 저장 중 오류 발생: {str(e)}")

def show_my_portfolio():
    supabase = get_supabase()
    user_id = st.session_state.user.id
    
    st.subheader("📂 마이 포트폴리오")
    st.write("학기가 끝나도 내가 제출한 과제와 선생님의 피드백을 확인할 수 있습니다.")
    
    submissions = supabase.table("submissions").select("*, assignments(title, rubric_data)").eq("student_id", user_id).execute()
    
    if not submissions.data:
        st.info("아직 제출된 과제가 없습니다.")
        return

    for sub in submissions.data:
        with st.expander(f"📌 {sub['assignments']['title']} (제출일: {sub['created_at'][:10]})"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 내 보고서")
                st.write(sub['text_report'])
                st.markdown("### 제출 코드")
                st.code(sub['source_code'], language='python')
            with col2:
                st.markdown("### 선생님 피드백")
                if sub['feedback']:
                    st.info(sub['feedback'])
                else:
                    st.write("아직 피드백이 없습니다.")
                
                st.markdown("### 최종 점수")
                if sub['score'] is not None:
                    st.metric("Score", f"{sub['score']}점")
                else:
                    st.write("채점 전입니다.")
                
                if sub['is_verified']:
                    st.success("✅ 코드 검증 완료")
                else:
                    st.error("⚠️ 코드 불일치 발견")
