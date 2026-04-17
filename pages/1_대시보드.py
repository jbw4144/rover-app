import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="대시보드", page_icon="🏠", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("🏠 대시보드")

try:
    sv_raw = supabase.table("semester_volunteers").select("semester").execute().data
    semesters = sorted(list(set(d["semester"] for d in sv_raw)), reverse=True) if sv_raw else []
    if not semesters:
        st.info("아직 등록된 학기 데이터가 없습니다. 봉사자를 먼저 학기에 등록해주세요.")
        st.stop()

    selected = st.selectbox("📆 학기 선택", semesters)

    sv_data = supabase.table("semester_volunteers")\
        .select("*, volunteers(name, affiliation, gender)")\
        .eq("semester", selected).execute().data
    act_data = supabase.table("activities").select("*").eq("semester", selected).execute().data

    male = sum(1 for d in sv_data if (d.get("volunteers") or {}).get("gender") == "남")
    female = sum(1 for d in sv_data if (d.get("volunteers") or {}).get("gender") == "여")
    edu_done = sum(1 for d in sv_data if d.get("basic_edu_done"))

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 등록 봉사자", f"{len(sv_data)}명")
    col2.metric("📅 봉사활동 수", f"{len(act_data)}건")
    col3.metric("👨 남성", f"{male}명")
    col4.metric("👩 여성", f"{female}명")
    col5.metric("📚 초급교육 이수", f"{edu_done}명")

    st.markdown("---")

    if sv_data:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("성별 분포")
            gdf = pd.DataFrame({"성별": ["남", "여"], "인원": [male, female]})
            fig = px.pie(gdf, names="성별", values="인원",
                         color_discrete_map={"남": "#4C8BF5", "여": "#FF6B9D"})
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("소속별 분포")
            affiliations = [(d.get("volunteers") or {}).get("affiliation") or "미입력" for d in sv_data]
            adf = pd.Series(affiliations).value_counts().reset_index()
            adf.columns = ["소속", "인원"]
            fig2 = px.bar(adf, x="소속", y="인원", color="인원", color_continuous_scale="Greens")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("활동참여현황 분포")
        statuses = [(d.get("activity_status") or "미입력") for d in sv_data]
        sdf = pd.Series(statuses).value_counts().reset_index()
        sdf.columns = ["상태", "인원"]
        fig3 = px.bar(sdf, x="상태", y="인원", color="인원", color_continuous_scale="Blues")
        st.plotly_chart(fig3, use_container_width=True)

except Exception as e:
    st.error(f"오류 발생: {e}")
