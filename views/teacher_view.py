import streamlit as st
import pandas as pd
from utils.db import get_supabase, generate_random_code

def show_teacher_dashboard():
    st.write("담당 수업 현황 및 공지사항을 확인하세요.")
    # 실제 요약 데이터 쿼리 로직이 들어갈 자리

def show_class_management():
    supabase = get_supabase()
    teacher_id = st.session_state.user.id
    
    st.subheader("🆕 새 수업 생성")
    with st.form("new_class_form"):
        name = st.text_input("수업 명", placeholder="예: 2026-1 정보")
        year = st.number_input("연도", value=2026)
        semester = st.selectbox("학기", ["1학기", "2학기", "여름방학", "겨울방학"])
        desc = st.text_area("수업 설명")
        
        if st.form_submit_button("수업 생성"):
            join_code = generate_random_code()
            try:
                supabase.table("classes").insert({
                    "name": name,
                    "academic_year": year,
                    "semester": semester,
                    "teacher_id": teacher_id,
                    "join_code": join_code,
                    "description": desc
                }).execute()
                st.success(f"수업이 생성되었습니다! 참여 코드: {join_code}")
            except Exception as e:
                st.error(f"생성 실패: {str(e)}")

    st.divider()
    st.subheader("📚 내 수업 목록")
    classes = supabase.table("classes").select("*").eq("teacher_id", teacher_id).execute()
    
    if classes.data:
        df = pd.DataFrame(classes.data)
        st.dataframe(df[['name', 'academic_year', 'semester', 'join_code', 'created_at']], use_container_width=True)
    else:
        st.info("생성된 수업이 없습니다.")

def show_attendance_management():
    supabase = get_supabase()
    teacher_id = st.session_state.user.id
    
    classes = supabase.table("classes").select("*").eq("teacher_id", teacher_id).execute()
    if not classes.data:
        st.warning("수업을 먼저 생성하세요.")
        return
        
    selected_class = st.selectbox("출결 관리 수업 선택", [c['name'] for c in classes.data])
    class_id = next(c['id'] for c in classes.data if c['name'] == selected_class)
    
    date = st.date_input("날짜 선택")
    
    # 해당 수업 수강생 목록 가져오기
    students = supabase.table("profiles").select("*").eq("class_id", class_id).eq("role", "student").execute()
    
    if not students.data:
        st.info("해당 수업에 등록된 학생이 없습니다.")
        return
        
    st.write(f"### 📅 {date} 출결 체크")
    
    # 기존 출결 데이터 가져오기
    existing_att = supabase.table("attendance").select("*").eq("class_id", class_id).eq("attendance_date", str(date)).execute()
    att_map = {a['student_id']: a for a in existing_att.data}
    
    for student in students.data:
        col1, col2, col3 = st.columns([2, 2, 3])
        with col1:
            st.write(student['full_name'])
        with col2:
            current_status = att_map.get(student['id'], {}).get('status', '출석')
            status = st.selectbox(f"상태", ["출석", "지각", "결석", "조퇴"], 
                                 index=["출석", "지각", "결석", "조퇴"].index(current_status),
                                 key=f"att_{student['id']}")
        with col3:
            note = st.text_input("비고", value=att_map.get(student['id'], {}).get('note', ''), key=f"note_{student['id']}")
            
        # 개별 저장 버튼 대신 하단 일괄 저장 권장 (여기서는 즉시 업데이트 로직 예시)
        if st.button("저장", key=f"btn_{student['id']}"):
            att_data = {
                "class_id": class_id,
                "student_id": student['id'],
                "status": status,
                "attendance_date": str(date),
                "note": note
            }
            try:
                if student['id'] in att_map:
                    supabase.table("attendance").update(att_data).eq("id", att_map[student['id']]['id']).execute()
                else:
                    supabase.table("attendance").insert(att_data).execute()
                st.toast(f"{student['full_name']} 출결 저장 완료")
            except Exception as e:
                st.error(f"저장 실패: {str(e)}")

def show_assignment_management():
    supabase = get_supabase()
    teacher_id = st.session_state.user.id
    
    classes = supabase.table("classes").select("*").eq("teacher_id", teacher_id).execute()
    if not classes.data:
        st.warning("먼저 수업을 생성하세요.")
        return

    st.subheader("📝 새 과제 등록")
    class_options = {c['name']: c['id'] for c in classes.data}
    selected_class_name = st.selectbox("대상 수업", list(class_options.keys()))
    class_id = class_options[selected_class_name]

    with st.form("assignment_form"):
        title = st.text_input("과제 제목")
        content = st.text_area("과제 설명 및 지시사항")
        deadline = st.date_input("마감 기한")
        
        st.write("📊 루브릭(평가 항목) 설정")
        rubric_count = st.number_input("평가 항목 개수", min_value=1, max_value=5, value=2)
        
        rubrics = []
        for i in range(int(rubric_count)):
            col1, col2 = st.columns([3, 1])
            with col1:
                item_name = st.text_input(f"항목 {i+1} 이름", value=f"항목 {i+1}", key=f"r_name_{i}")
            with col2:
                item_score = st.number_input(f"배점 {i+1}", min_value=0, value=10, key=f"r_score_{i}")
            rubrics.append({"name": item_name, "max_score": item_score})

        if st.form_submit_button("과제 배포"):
            try:
                supabase.table("assignments").insert({
                    "class_id": class_id,
                    "title": title,
                    "content": content,
                    "rubric_data": rubrics,
                    "deadline": str(deadline)
                }).execute()
                st.success(f"'{title}' 과제가 배포되었습니다!")
            except Exception as e:
                st.error(f"과제 배포 실패: {str(e)}")

    st.divider()
    st.subheader("📋 등록된 과제 목록")
    assignments = supabase.table("assignments").select("*, classes(name)").execute()
    if assignments.data:
        for assign in assignments.data:
            with st.expander(f"[{assign['classes']['name']}] {assign['title']}"):
                st.write(assign['content'])
def show_evaluation_export():
    supabase = get_supabase()
    teacher_id = st.session_state.user.id
    
    st.subheader("📊 평가 데이터 내보내기 (CSV)")
    
    # 모든 제출물 및 학생 정보 조인해서 가져오기
    query = supabase.table("submissions").select("*, profiles(full_name, email), assignments(title, class_id, classes(name))")
    results = query.execute()
    
    if not results.data:
        st.info("내보낼 평가 데이터가 없습니다.")
        return
        
    data = []
    for r in results.data:
        data.append({
            "수업": r['assignments']['classes']['name'],
            "과제": r['assignments']['title'],
            "이름": r['profiles']['full_name'],
            "이메일": r['profiles']['email'],
            "점수": r['score'],
            "코드검증": "일치" if r['is_verified'] else "불일치",
            "피드백": r['feedback'],
            "제출일": r['created_at'][:10]
        })
        
    df = pd.DataFrame(data)
    st.dataframe(df)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="evaluation_data.csv",
        mime="text/csv"
    )
