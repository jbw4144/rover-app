import streamlit as st
import pandas as pd
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="참여 기록", page_icon="✅", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("✅ 참여 기록")

tab1, tab2 = st.tabs(["➕ 참여자 등록", "📋 참여 현황 조회"])

# ── 탭1: 참여자 등록 ────────────────────────────────────────────
with tab1:
    acts = supabase.table("activities").select("id, title, activity_date, semester")\
        .order("activity_date", desc=True).execute().data

    if not acts:
        st.info("먼저 봉사활동을 생성해주세요.")
        st.stop()

    act_map = {f"[{a['semester']}] {a['title']} ({a['activity_date']})": a['id'] for a in acts}
    selected_act_name = st.selectbox("활동 선택", list(act_map.keys()))
    act_id = act_map[selected_act_name]

    already = supabase.table("participation").select("volunteer_id").eq("activity_id", act_id).execute().data
    already_ids = set(d["volunteer_id"] for d in already)

    vols = supabase.table("volunteers").select("id, name, affiliation, gender")\
        .order("name").execute().data

    if not vols:
        st.info("먼저 봉사자를 등록해주세요.")
        st.stop()

    st.metric("현재 참여자 수", f"{len(already_ids)}명")
    st.markdown("---")

    vol_map = {f"{v['name']} ({v.get('affiliation','')}/{v.get('gender','')})": v['id'] for v in vols}
    default_selected = [name for name, vid in vol_map.items() if vid in already_ids]

    selected_names = st.multiselect(
        "참여자 선택 (복수 선택 가능)",
        list(vol_map.keys()),
        default=default_selected
    )
    notes = st.text_area("특이사항", placeholder="당일 특이사항을 메모하세요.")

    if st.button("💾 참여 기록 저장", use_container_width=True, type="primary"):
        selected_ids = {vol_map[n] for n in selected_names}
        new_ids = selected_ids - already_ids
        removed_ids = already_ids - selected_ids

        added, removed = 0, 0
        for vid in new_ids:
            try:
                supabase.table("participation").insert({
                    "volunteer_id": vid, "activity_id": act_id, "notes": notes or None
                }).execute()
                added += 1
            except Exception:
                pass

        for vid in removed_ids:
            try:
                supabase.table("participation")\
                    .delete().eq("volunteer_id", vid).eq("activity_id", act_id).execute()
                removed += 1
            except Exception:
                pass

        msgs = []
        if added: msgs.append(f"✅ {added}명 추가")
        if removed: msgs.append(f"🗑️ {removed}명 제거")
        if msgs:
            st.success(" / ".join(msgs) + " 완료!")
        else:
            st.info("변경사항이 없습니다.")
        st.rerun()

# ── 탭2: 참여 현황 조회 ─────────────────────────────────────────
with tab2:
    acts2 = supabase.table("activities").select("id, title, activity_date, semester")\
        .order("activity_date", desc=True).execute().data

    if not acts2:
        st.info("활동 데이터가 없습니다.")
        st.stop()

    act_map2 = {f"[{a['semester']}] {a['title']} ({a['activity_date']})": a['id'] for a in acts2}
    sel2 = st.selectbox("활동 선택", list(act_map2.keys()), key="view2")
    act_id2 = act_map2[sel2]

    part = supabase.table("participation")\
        .select("*, volunteers(name, affiliation, gender, phone)")\
        .eq("activity_id", act_id2).execute().data

    if part:
        rows = []
        for d in part:
            v = d.get("volunteers") or {}
            rows.append({
                "이름": v.get("name",""),
                "소속": v.get("affiliation",""),
                "성별": v.get("gender",""),
                "연락처": v.get("phone",""),
                "특이사항": d.get("notes",""),
                "기록일시": (d.get("recorded_at","")[:16] if d.get("recorded_at") else "")
            })
        df = pd.DataFrame(rows)

        c1, c2, c3 = st.columns(3)
        c1.metric("총 참여", f"{len(df)}명")
        c2.metric("남", f"{(df['성별']=='남').sum()}명")
        c3.metric("여", f"{(df['성별']=='여').sum()}명")

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 참여자 명단 CSV 다운로드", csv,
                           f"participation_{act_id2[:8]}.csv", "text/csv")
    else:
        st.info("참여 기록이 없습니다.")
