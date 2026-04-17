import streamlit as st
import pandas as pd
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="봉사자 관리", page_icon="👥", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("👥 봉사자 관리")

tab1, tab2, tab3, tab4 = st.tabs(["📋 전체 목록", "➕ 신규 등록", "📆 학기 배정", "🔍 학기별 조회"])

# ── 탭1: 전체 목록 ──────────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns(3)
    search = col1.text_input("🔍 이름 검색")
    gender_f = col2.selectbox("성별", ["전체", "남", "여"])
    affil_f = col3.text_input("소속 검색")

    data = supabase.table("volunteers").select("*").order("name").execute().data

    if data:
        df = pd.DataFrame(data)
        df = df.rename(columns={
            "affiliation":"소속","name":"이름","birth_date":"생년월일",
            "member_number":"회원번호","gender":"성별","phone":"연락처",
            "dubbol_id":"두볼아이디","created_at":"등록일"
        })
        if search:
            df = df[df["이름"].str.contains(search, na=False)]
        if gender_f != "전체":
            df = df[df["성별"] == gender_f]
        if affil_f:
            df = df[df["소속"].str.contains(affil_f, na=False)]

        cols = ["소속","이름","생년월일","회원번호","성별","연락처","두볼아이디"]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.caption(f"총 {len(df)}명")
    else:
        st.info("등록된 봉사자가 없습니다.")

# ── 탭2: 신규 등록 ──────────────────────────────────────────────
with tab2:
    st.subheader("새 봉사자 등록")
    with st.form("add_vol"):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름 *")
        affiliation = c2.text_input("소속", placeholder="한양대학교")
        c3, c4 = st.columns(2)
        gender = c3.selectbox("성별", ["남", "여"])
        birth_date = c4.date_input("생년월일", value=None)
        c5, c6 = st.columns(2)
        member_number = c5.text_input("회원번호")
        phone = c6.text_input("연락처", placeholder="010-0000-0000")
        dubbol_id = st.text_input("두볼 아이디 (선택사항)")

        if st.form_submit_button("등록하기", use_container_width=True, type="primary"):
            if not name:
                st.error("이름은 필수입니다.")
            else:
                try:
                    supabase.table("volunteers").insert({
                        "name": name,
                        "affiliation": affiliation or None,
                        "gender": gender,
                        "birth_date": str(birth_date) if birth_date else None,
                        "member_number": member_number or None,
                        "phone": phone or None,
                        "dubbol_id": dubbol_id or None
                    }).execute()
                    st.success(f"✅ {name}님이 등록되었습니다!")
                    st.rerun()
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error("이미 존재하는 회원번호입니다.")
                    else:
                        st.error(f"오류: {e}")

# ── 탭3: 학기 배정 ──────────────────────────────────────────────
with tab3:
    st.subheader("학기별 봉사자 배정")
    st.caption("기존 봉사자를 특정 학기에 등록합니다. 이전 학기 참여자도 새 학기로 재배정 가능합니다.")

    vols = supabase.table("volunteers").select("id, name, affiliation").order("name").execute().data
    if vols:
        vol_map = {f"{v['name']} ({v.get('affiliation','소속없음')})": v['id'] for v in vols}

        with st.form("sem_assign"):
            selected_vol = st.selectbox("봉사자 선택", list(vol_map.keys()))
            c1, c2 = st.columns(2)
            semester = c1.text_input("학기 *", placeholder="26-1")
            activity_status = c2.selectbox("활동참여현황", ["활동중", "휴면", "수료", "탈퇴"])
            c3, c4 = st.columns(2)
            basic_edu = c3.checkbox("초급교육 이수 완료")
            warning_count = c4.number_input("경고횟수", min_value=0, max_value=10, value=0)
            notes = st.text_area("비고")

            if st.form_submit_button("학기 배정", use_container_width=True, type="primary"):
                if not semester:
                    st.error("학기를 입력하세요. (예: 26-1)")
                else:
                    try:
                        supabase.table("semester_volunteers").insert({
                            "volunteer_id": vol_map[selected_vol],
                            "semester": semester,
                            "activity_status": activity_status,
                            "basic_edu_done": basic_edu,
                            "warning_count": warning_count,
                            "notes": notes or None
                        }).execute()
                        st.success(f"✅ [{semester}] 학기 배정 완료!")
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.warning("⚠️ 이미 해당 학기에 배정된 봉사자입니다.")
                        else:
                            st.error(f"오류: {e}")
    else:
        st.info("먼저 봉사자를 등록해주세요.")

# ── 탭4: 학기별 조회 ────────────────────────────────────────────
with tab4:
    semester_q = st.text_input("조회할 학기", placeholder="예: 26-1")
    if semester_q:
        sv = supabase.table("semester_volunteers")\
            .select("*, volunteers(name, affiliation, gender, phone, member_number)")\
            .eq("semester", semester_q).execute().data
        if sv:
            rows = []
            for d in sv:
                v = d.get("volunteers") or {}
                rows.append({
                    "이름": v.get("name",""),
                    "소속": v.get("affiliation",""),
                    "성별": v.get("gender",""),
                    "회원번호": v.get("member_number",""),
                    "연락처": v.get("phone",""),
                    "활동참여현황": d.get("activity_status",""),
                    "초급교육": "✅" if d.get("basic_edu_done") else "❌",
                    "경고횟수": d.get("warning_count", 0),
                    "봉사활동횟수": d.get("activity_count", 0),
                    "비고": d.get("notes","")
                })
            df2 = pd.DataFrame(rows)
            st.metric(f"[{semester_q}] 등록 인원", f"{len(df2)}명")
            st.dataframe(df2, use_container_width=True, hide_index=True)

            csv = df2.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                f"📥 [{semester_q}] 명단 CSV 다운로드",
                csv, f"rover_{semester_q}.csv", "text/csv"
            )
        else:
            st.info(f"[{semester_q}] 학기에 배정된 봉사자가 없습니다.")
