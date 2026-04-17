import streamlit as st
import pandas as pd
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="학기 이월", page_icon="🔁", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("🔁 학기 이월 관리")
st.caption("이전 학기 봉사자를 새 학기로 복사합니다. 기존 활동 기록은 유지되고 새 학기 정보만 초기화됩니다.")

tab1, tab2 = st.tabs(["📋 이월 실행", "🔍 학기별 인원 비교"])

# ── 탭1: 이월 실행 ──────────────────────────────────────────────
with tab1:
    # 등록된 학기 목록 가져오기
    sv_raw = supabase.table("semester_volunteers").select("semester").execute().data
    semesters = sorted(list(set(d["semester"] for d in sv_raw)), reverse=True) if sv_raw else []

    if not semesters:
        st.info("등록된 학기 데이터가 없습니다. 먼저 엑셀 업로드로 데이터를 넣어주세요.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    from_sem = col1.selectbox("📤 이월할 학기 (원본)", semesters)
    to_sem = col2.text_input("📥 새 학기 (대상)", placeholder="예: 26-2, 27-1")

    # 원본 학기 인원 미리보기
    from_data = supabase.table("semester_volunteers")\
        .select("*, volunteers(name, affiliation, gender)")\
        .eq("semester", from_sem).execute().data

    col3.metric(f"[{from_sem}] 인원", f"{len(from_data)}명")

    if from_data:
        st.markdown("---")
        st.subheader(f"📋 [{from_sem}] 이월 대상 명단")

        rows = []
        for d in from_data:
            v = d.get("volunteers") or {}
            rows.append({
                "이름": v.get("name", ""),
                "소속": v.get("affiliation", ""),
                "성별": v.get("gender", ""),
                "활동참여현황": d.get("activity_status", ""),
                "초급교육": "✅" if d.get("basic_edu_done") else "❌",
                "경고횟수": d.get("warning_count", 0),
                "이월": True
            })
        df = pd.DataFrame(rows)

        # 이월할 인원 선택
        st.caption("이월하지 않을 인원은 체크 해제하세요.")

        # 전체 선택/해제
        col_a, col_b = st.columns([1, 4])
        select_all = col_a.checkbox("전체 선택", value=True)

        edited_df = st.data_editor(
            df,
            column_config={
                "이월": st.column_config.CheckboxColumn("이월 여부", default=True)
            },
            use_container_width=True,
            hide_index=True,
            key="rollover_editor"
        )

        selected_count = edited_df["이월"].sum()
        st.info(f"선택된 이월 인원: **{selected_count}명** / 전체 {len(df)}명")

        st.markdown("---")
        st.subheader("⚙️ 이월 옵션")
        c1, c2 = st.columns(2)
        reset_edu = c1.checkbox("초급교육 이수여부 초기화", value=False,
                                help="새 학기에서 초급교육 이수여부를 미이수로 초기화")
        reset_warning = c2.checkbox("경고횟수 초기화", value=True,
                                    help="새 학기에서 경고횟수를 0으로 초기화")
        default_status = st.selectbox("새 학기 기본 활동참여현황", 
                                       ["활동중", "이전학기유지", "미정"])

        st.markdown("---")

        if st.button("🚀 이월 실행", use_container_width=True, type="primary",
                     disabled=not to_sem or selected_count == 0):
            if not to_sem.strip():
                st.error("새 학기를 입력하세요.")
            else:
                # 이미 새 학기에 등록된 인원 확인
                to_existing = supabase.table("semester_volunteers")\
                    .select("volunteer_id").eq("semester", to_sem.strip()).execute().data
                existing_ids = set(d["volunteer_id"] for d in to_existing)

                progress = st.progress(0, text="이월 중...")
                selected_rows = edited_df[edited_df["이월"] == True]
                total = len(selected_rows)
                added, skipped, errors = 0, 0, []

                for idx, (i, row) in enumerate(selected_rows.iterrows()):
                    try:
                        orig = from_data[i]
                        vol_id = orig["volunteer_id"]

                        if vol_id in existing_ids:
                            skipped += 1
                            progress.progress((idx + 1) / total, text=f"처리 중... {idx+1}/{total}")
                            continue

                        # 활동참여현황 결정
                        if default_status == "이전학기유지":
                            status = orig.get("activity_status", "활동중")
                        else:
                            status = default_status

                        sv_data = {
                            "volunteer_id": vol_id,
                            "semester": to_sem.strip(),
                            "activity_status": status,
                            "basic_edu_done": False if reset_edu else orig.get("basic_edu_done", False),
                            "warning_count": 0 if reset_warning else orig.get("warning_count", 0),
                            "activity_count": 0,
                            "notes": None
                        }
                        supabase.table("semester_volunteers").insert(sv_data).execute()
                        added += 1

                    except Exception as e:
                        errors.append(f"{row.get('이름','?')}: {str(e)[:60]}")

                    progress.progress((idx + 1) / total, text=f"처리 중... {idx+1}/{total}")

                progress.progress(1.0, text="완료!")
                st.markdown("---")
                r1, r2, r3 = st.columns(3)
                r1.metric("✅ 이월 완료", f"{added}명")
                r2.metric("⏭️ 이미 등록됨 (건너뜀)", f"{skipped}명")
                r3.metric("❌ 오류", f"{len(errors)}건")

                if errors:
                    with st.expander("⚠️ 오류 목록"):
                        for e in errors:
                            st.text(e)
                else:
                    st.success(f"🎉 [{from_sem}] → [{to_sem}] 이월 완료! {added}명이 새 학기에 등록되었습니다.")
                    st.balloons()

# ── 탭2: 학기별 인원 비교 ────────────────────────────────────────
with tab2:
    st.subheader("📊 학기별 인원 현황 비교")

    sv_all = supabase.table("semester_volunteers")\
        .select("semester, basic_edu_done, warning_count, activity_status, volunteers(gender)")\
        .execute().data

    if not sv_all:
        st.info("데이터가 없습니다.")
    else:
        sem_stats = {}
        for d in sv_all:
            sem = d["semester"]
            if sem not in sem_stats:
                sem_stats[sem] = {"총인원": 0, "남": 0, "여": 0, "초급교육이수": 0, "경고보유": 0}
            sem_stats[sem]["총인원"] += 1
            g = (d.get("volunteers") or {}).get("gender", "")
            if g == "남": sem_stats[sem]["남"] += 1
            if g == "여": sem_stats[sem]["여"] += 1
            if d.get("basic_edu_done"): sem_stats[sem]["초급교육이수"] += 1
            if (d.get("warning_count") or 0) > 0: sem_stats[sem]["경고보유"] += 1

        stats_df = pd.DataFrame(sem_stats).T.reset_index()
        stats_df.columns = ["학기", "총인원", "남", "여", "초급교육이수", "경고보유"]
        stats_df = stats_df.sort_values("학기")

        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        import plotly.express as px
        fig = px.bar(stats_df, x="학기", y="총인원",
                     color="총인원", color_continuous_scale="Greens",
                     title="학기별 등록 인원")
        st.plotly_chart(fig, use_container_width=True)
