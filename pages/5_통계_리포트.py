import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="통계 리포트", page_icon="📊", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("📊 통계 리포트")

try:
    part_data = supabase.table("participation")\
        .select("*, volunteers(name, affiliation, gender), activities(title, semester, activity_date)")\
        .execute().data

    if not part_data:
        st.info("아직 참여 기록이 없습니다.")
        st.stop()

    rows = []
    for d in part_data:
        v = d.get("volunteers") or {}
        a = d.get("activities") or {}
        rows.append({
            "이름": v.get("name",""),
            "소속": v.get("affiliation",""),
            "성별": v.get("gender",""),
            "활동명": a.get("title",""),
            "학기": a.get("semester",""),
            "날짜": a.get("activity_date","")
        })
    df = pd.DataFrame(rows)

    semesters = ["전체"] + sorted(df["학기"].dropna().unique().tolist(), reverse=True)
    sel_sem = st.selectbox("📆 학기 선택", semesters)
    if sel_sem != "전체":
        df = df[df["학기"] == sel_sem]

    c1, c2, c3 = st.columns(3)
    c1.metric("총 참여 건수", len(df))
    c2.metric("참여 봉사자 수", df["이름"].nunique())
    c3.metric("봉사활동 수", df["활동명"].nunique())

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("👤 개인별 참여 횟수")
        person_cnt = df.groupby(["이름","소속","성별"]).size().reset_index(name="참여횟수")
        person_cnt = person_cnt.sort_values("참여횟수", ascending=False)
        st.dataframe(person_cnt, use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("⚥ 성별 분포")
        unique_persons = df.drop_duplicates("이름")
        gcnt = unique_persons.groupby("성별").size().reset_index(name="인원")
        fig = px.pie(gcnt, names="성별", values="인원",
                     color_discrete_map={"남":"#4C8BF5","여":"#FF6B9D"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📅 활동별 참여 현황")
    act_cnt = df.groupby("활동명").size().reset_index(name="참여자수")
    act_cnt = act_cnt.sort_values("참여자수", ascending=True)
    fig2 = px.bar(act_cnt, x="참여자수", y="활동명", orientation="h",
                  color="참여자수", color_continuous_scale="Greens")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("🏫 소속별 참여 현황")
    aff_cnt = df.groupby("소속").size().reset_index(name="참여횟수")
    aff_cnt = aff_cnt.sort_values("참여횟수", ascending=False)
    fig3 = px.bar(aff_cnt, x="소속", y="참여횟수", color="참여횟수", color_continuous_scale="Blues")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("📥 데이터 다운로드")
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("참여 기록 전체 CSV 다운로드", csv, "rover_report.csv", "text/csv",
                       use_container_width=True)

except Exception as e:
    st.error(f"오류 발생: {e}")
