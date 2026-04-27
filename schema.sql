-- 1. Profiles Table (사용자 정보)
CREATE TABLE public.profiles (
    id uuid REFERENCES auth.users ON DELETE CASCADE NOT NULL PRIMARY KEY,
    email text UNIQUE NOT NULL,
    full_name text NOT NULL,
    role text CHECK (role IN ('admin', 'teacher', 'student')) NOT NULL,
    birth_date date,
    phone_number text,
    privacy_consent boolean DEFAULT false,
    class_id uuid, -- 학생인 경우 소속 수업
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Signup Codes Table (그룹 가입 코드)
CREATE TABLE public.signup_codes (
    code text PRIMARY KEY,
    role text CHECK (role IN ('teacher', 'student')) NOT NULL,
    group_name text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Classes Table (수업 정보)
CREATE TABLE public.classes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    academic_year integer NOT NULL,
    semester text NOT NULL,
    teacher_id uuid REFERENCES public.profiles(id) NOT NULL,
    join_code text UNIQUE NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Assignments Table (과제 및 루브릭)
CREATE TABLE public.assignments (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    class_id uuid REFERENCES public.classes(id) ON DELETE CASCADE NOT NULL,
    title text NOT NULL,
    content text,
    rubric_data jsonb,
    deadline timestamp with time zone,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Submissions Table (제출 및 평가)
CREATE TABLE public.submissions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    assignment_id uuid REFERENCES public.assignments(id) ON DELETE CASCADE NOT NULL,
    student_id uuid REFERENCES public.profiles(id) NOT NULL,
    text_report text,
    source_code text,
    file_url text,
    feedback text,
    score integer,
    is_verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(assignment_id, student_id)
);

-- 6. Attendance Table (출결)
CREATE TABLE public.attendance (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    class_id uuid REFERENCES public.classes(id) ON DELETE CASCADE NOT NULL,
    student_id uuid REFERENCES public.profiles(id) NOT NULL,
    status text CHECK (status IN ('출석', '지각', '결석', '조퇴')) NOT NULL,
    attendance_date date NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(class_id, student_id, attendance_date)
);

-- RLS (Row Level Security) 기본 설정
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signup_codes ENABLE ROW LEVEL SECURITY; -- 추가됨

-- 정책: 본인 프로필만 수정 가능
CREATE POLICY "Users can view their own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 정책: 수업 정보 조회 (교사는 전체, 학생은 소속 수업만)
CREATE POLICY "Everyone can view classes" ON public.classes FOR SELECT USING (true);
CREATE POLICY "Teachers can create/update their own classes" ON public.classes 
    FOR ALL USING (auth.uid() = teacher_id);

-- 정책: 과제 조회
CREATE POLICY "Everyone can view assignments" ON public.assignments FOR SELECT USING (true);

-- 정책: 가입 코드 보안 (누구나 조회 가능, 관리는 관리자만)
CREATE POLICY "Everyone can check signup codes" ON public.signup_codes FOR SELECT USING (true);
CREATE POLICY "Admins can manage signup codes" ON public.signup_codes 
    FOR ALL USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- 정책: 제출물 보안 (매우 중요)
CREATE POLICY "Students can view/create their own submissions" ON public.submissions 
    FOR ALL USING (auth.uid() = student_id);
CREATE POLICY "Teachers can view all submissions in their classes" ON public.submissions 
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM public.assignments a 
        JOIN public.classes c ON a.class_id = c.id 
        WHERE a.id = submissions.assignment_id AND c.teacher_id = auth.uid()
    ));

-- 7. Settings Table (시스템 설정 및 약관)
CREATE TABLE public.settings (
    key text PRIMARY KEY,
    value text NOT NULL
);

INSERT INTO public.settings (key, value) VALUES ('privacy_policy', '여기에 개인정보 수집 및 이용 약관 내용을 입력하세요.');

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view settings" ON public.settings FOR SELECT USING (true);
CREATE POLICY "Admins can update settings" ON public.settings 
    FOR UPDATE USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- Storage Bucket 설정 안내
-- 1. 'submissions' 버킷을 'Public' 혹은 RLS 기반으로 생성해야 함.
