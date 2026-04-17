import streamlit as st
import pandas as pd
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="봉사활동 관리", page_icon="📅", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("📅 봉사활동 관리")

tab1, tab2 = st.tabs(["📋 활동 목록", "➕ 활동 생성"])

# ── 탭1: 목록 ───────────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns([1, 3])
    sem_f = c1.text_input("학기 필터", placeholder="예: 26-1")
    type_f = c2.selectbox("유형 필터", ["전체", "환경", "교육", "복지", "행사지원", "기타"])

    query = supabase.table("activities").select("*").order("activity_date", desc=True)
    if sem_f:
        query = query.eq("semester", sem_f)
    data = query.execute().data

    if data:
        df = pd.DataFrame(data)
        if type_f != "전체":
            df = df[df["activity_type"] == type_f]
        df = df.rename(columns={
            "title":"활동명","activity_date":"날짜","location":"장소",
            "activity_type":"유형","semester":"학기","description":"설명"
        })
        st.dataframe(df[["학기","활동명","날짜","장소","유형","설명"]], use_container_width=True, hide_index=True)
        st.caption(f"총 {len(df)}건")
    else:
        st.info("등록된 봉사활동이 없습니다.")

# ── 탭2: 활동 생성 ──────────────────────────────────────────────
with tab2:
    st.subheader("새 봉사활동 생성")
    with st.form("add_act"):
        title = st.text_input("활동명 *", placeholder="00공원 환경정화 봉사")
        c1, c2 = st.columns(2)
        activity_date = c1.date_input("활동 날짜")
        semester = c2.text_input("학기 *", placeholder="26-1")
        c3, c4 = st.columns(2)
        location = c3.text_input("장소", placeholder="서울 00공원")
        activity_type = c4.selectbox("활동 유형", ["환경", "교육", "복지", "행사지원", "기타"])
        description = st.text_area("활동 설명")

        if st.form_submit_button("활동 생성", use_container_width=True, type="primary"):
            if not title or not semester:
                st.error("활동명과 학기는 필수입니다.")
            else:
                try:
                    supabase.table("activities").insert({
                        "title": title,
                        "activity_date": str(activity_date),
                        "semester": semester,
                        "location": location or None,
                        "activity_type": activity_type,
                        "description": description or None
                    }).execute()
                    st.success(f"✅ '{title}' 활동이 생성되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")
