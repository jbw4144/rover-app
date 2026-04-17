import streamlit as st

def check_auth():
    if "user" not in st.session_state or not st.session_state.get("user"):
        st.error("🔒 로그인이 필요합니다.")
        st.page_link("app.py", label="🔑 로그인 페이지로 이동")
        st.stop()

def logout_button(supabase):
    with st.sidebar:
        user = st.session_state.get("user")
        if user:
            st.markdown(f"👤 **{user.email}**")
            st.markdown("---")
        if st.button("🚪 로그아웃", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
