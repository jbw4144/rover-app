import streamlit as st
from utils.supabase_client import get_supabase

st.set_page_config(
    page_title="ROVER 봉사활동 관리",
    page_icon="🏕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

supabase = get_supabase()

def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🏕️ ROVER 봉사활동 관리")
        st.caption("대학생 성인지도자 봉사자 통합 관리 시스템")
        st.markdown("---")
        with st.form("login_form"):
            email = st.text_input("📧 이메일", placeholder="admin@example.com")
            pw = st.text_input("🔑 비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
            if submitted:
                if not email or not pw:
                    st.error("이메일과 비밀번호를 입력하세요.")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                        st.session_state["user"] = res.user
                        st.rerun()
                    except Exception:
                        st.error("❌ 이메일 또는 비밀번호가 올바르지 않습니다.")

def main_page():
    from utils.auth import logout_button
    logout_button(supabase)

    st.title("🏕️ ROVER 봉사활동 관리 시스템")
    st.markdown("왼쪽 메뉴에서 원하는 페이지를 선택하세요.")
    st.markdown("---")

    try:
        col1, col2, col3, col4 = st.columns(4)
        v_cnt = len(supabase.table("volunteers").select("id", count="exact").execute().data)
        a_cnt = len(supabase.table("activities").select("id", count="exact").execute().data)
        p_cnt = len(supabase.table("participation").select("id", count="exact").execute().data)
        sv_cnt = len(supabase.table("semester_volunteers").select("id", count="exact").execute().data)
        col1.metric("👥 전체 봉사자", f"{v_cnt}명")
        col2.metric("📅 전체 활동", f"{a_cnt}건")
        col3.metric("✅ 전체 참여 기록", f"{p_cnt}건")
        col4.metric("📆 학기 등록 수", f"{sv_cnt}건")
    except Exception as e:
        st.warning(f"데이터 로드 중 오류: {e}")

if "user" not in st.session_state or not st.session_state.get("user"):
    login_page()
else:
    main_page()
