import streamlit as st
import pandas as pd
from utils.auth import check_auth, logout_button
from utils.supabase_client import get_supabase

st.set_page_config(page_title="엑셀 업로드", page_icon="📥", layout="wide")
check_auth()
supabase = get_supabase()
logout_button(supabase)

st.title("📥 엑셀 일괄 업로드")
st.caption("기존 봉사활동내역 DB 엑셀 파일을 그대로 업로드하면 자동으로 DB에 등록됩니다.")

# ── 컬럼 매핑 안내 ─────────────────────────────────────────────
with st.expander("📋 엑셀 컬럼 매핑 확인", expanded=False):
    st.markdown("""
    | 엑셀 컬럼 | DB 저장 위치 | 비고 |
    |---|---|---|
    | 대등록기준 | semester_volunteers.semester | 학기 구분 (예: 26-1) |
    | 소속 | volunteers.affiliation | 소속 단체/학교 |
    | 이름 | volunteers.name | 필수값 |
    | 생년월일 | volunteers.birth_date | 1997.01.05 형식 자동 변환 |
    | 회원번호 | volunteers.member_number | 중복 시 업데이트 |
    | 성별 | volunteers.gender | 남/여 |
    | 연락처 | volunteers.phone | |
    | 두볼아이디 | volunteers.dubbol_id | 참고용 |
    | 경고횟수 | semester_volunteers.warning_count | |
    | 활동참여현황 | semester_volunteers.activity_status | |
    | 초급교육 이수여부 | semester_volunteers.basic_edu_done | O/X → True/False 자동변환 |
    | 봉사활동 참여횟수 | semester_volunteers.activity_count | |
    | 비고 | semester_volunteers.notes | |
    """)

st.markdown("---")

# ── 파일 업로드 ────────────────────────────────────────────────
uploaded = st.file_uploader(
    "엑셀 파일 선택 (.xlsx)",
    type=["xlsx"],
    help="ROVER_2026_봉사활동내역_DB.xlsx 형식의 파일을 올려주세요."
)

if uploaded:
    try:
        df = pd.read_excel(uploaded, sheet_name="MASTER_DB")
        df.columns = df.columns.str.replace("\n", " ").str.strip()

        col_map = {
            "대등록기준": "semester",
            "소속": "affiliation",
            "이름": "name",
            "생년월일": "birth_date",
            "회원번호": "member_number",
            "성별": "gender",
            "연락처": "phone",
            "두볼아이디": "dubbol_id",
            "경고횟수": "warning_count",
            "활동참여현황": "activity_status",
            "초급교육 이수여부": "basic_edu_done",
            "봉사활동 참여횟수": "activity_count",
            "비고": "notes"
        }
        df = df.rename(columns=col_map)
        df = df[df["name"].notna() & (df["name"].astype(str).str.strip() != "")]

        st.success(f"✅ 파일 읽기 완료 — 총 **{len(df)}명** 데이터 감지")

        st.subheader("📋 미리보기 (상위 5개)")
        preview_cols = ["semester","affiliation","name","birth_date","member_number","gender","phone"]
        st.dataframe(df[preview_cols].head(5), use_container_width=True, hide_index=True)

        st.markdown("---")

        col1, col2 = st.columns(2)
        duplicate_option = col1.radio(
            "중복 회원번호 처리",
            ["건너뛰기 (기존 데이터 유지)", "덮어쓰기 (새 데이터로 업데이트)"],
            help="같은 회원번호가 이미 DB에 있을 때 처리 방법"
        )
        semester_dup = col2.radio(
            "동일 학기 중복 처리",
            ["건너뛰기", "덮어쓰기"],
            help="같은 봉사자가 동일 학기에 이미 배정되어 있을 때"
        )

        if st.button("🚀 업로드 시작", use_container_width=True, type="primary"):
            progress = st.progress(0, text="업로드 준비 중...")
            total = len(df)
            added_v, updated_v, added_sv, skipped, errors = 0, 0, 0, 0, []

            for i, row in df.iterrows():
                try:
                    # ── 생년월일 변환 ──────────────────────────
                    birth_date = None
                    if pd.notna(row.get("birth_date")):
                        bd = str(row["birth_date"]).strip()
                        birth_date = bd.replace(".", "-")

                    # ── 초급교육 이수여부 변환 ─────────────────
                    edu_raw = str(row.get("basic_edu_done", "")).strip().upper()
                    basic_edu = edu_raw in ["O", "TRUE", "1", "완료", "이수"]

                    # ── 회원번호 처리 ──────────────────────────
                    member_num = str(int(row["member_number"])) if pd.notna(row.get("member_number")) else None

                    volunteer_data = {
                        "name": str(row["name"]).strip(),
                        "affiliation": str(row["affiliation"]).strip() if pd.notna(row.get("affiliation")) else None,
                        "birth_date": birth_date,
                        "member_number": member_num,
                        "gender": str(row["gender"]).strip() if pd.notna(row.get("gender")) else None,
                        "phone": str(row["phone"]).strip() if pd.notna(row.get("phone")) else None,
                        "dubbol_id": str(row["dubbol_id"]).strip() if pd.notna(row.get("dubbol_id")) else None,
                    }

                    # ── volunteers 테이블 처리 ─────────────────
                    existing = supabase.table("volunteers")
                    if member_num:
                        existing = existing.select("id").eq("member_number", member_num).execute().data
                    else:
                        existing = existing.select("id").eq("name", volunteer_data["name"]).execute().data

                    if existing:
                        vol_id = existing[0]["id"]
                        if duplicate_option == "덮어쓰기 (새 데이터로 업데이트)":
                            supabase.table("volunteers").update(volunteer_data).eq("id", vol_id).execute()
                            updated_v += 1
                    else:
                        res = supabase.table("volunteers").insert(volunteer_data).execute()
                        vol_id = res.data[0]["id"]
                        added_v += 1

                    # ── semester_volunteers 테이블 처리 ───────
                    semester = str(row["semester"]).strip() if pd.notna(row.get("semester")) else None
                    if semester:
                        sv_data = {
                            "volunteer_id": vol_id,
                            "semester": semester,
                            "activity_status": str(row["activity_status"]).strip() if pd.notna(row.get("activity_status")) else None,
                            "basic_edu_done": basic_edu,
                            "warning_count": int(row["warning_count"]) if pd.notna(row.get("warning_count")) else 0,
                            "activity_count": int(row["activity_count"]) if pd.notna(row.get("activity_count")) else 0,
                            "notes": str(row["notes"]).strip() if pd.notna(row.get("notes")) else None,
                        }

                        sv_existing = supabase.table("semester_volunteers")\
                            .select("id").eq("volunteer_id", vol_id).eq("semester", semester).execute().data

                        if sv_existing:
                            if semester_dup == "덮어쓰기":
                                supabase.table("semester_volunteers").update(sv_data)\
                                    .eq("id", sv_existing[0]["id"]).execute()
                                added_sv += 1
                            else:
                                skipped += 1
                        else:
                            supabase.table("semester_volunteers").insert(sv_data).execute()
                            added_sv += 1

                except Exception as e:
                    errors.append(f"행 {i+2}: {row.get('name','?')} — {str(e)[:80]}")

                progress.progress((i + 1) / total, text=f"처리 중... {i+1}/{total}명")

            progress.progress(1.0, text="완료!")

            st.markdown("---")
            st.subheader("📊 업로드 결과")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("신규 봉사자 등록", f"{added_v}명")
            r2.metric("봉사자 정보 업데이트", f"{updated_v}명")
            r3.metric("학기 배정 완료", f"{added_sv}건")
            r4.metric("건너뜀 / 오류", f"{skipped + len(errors)}건")

            if errors:
                with st.expander(f"⚠️ 오류 목록 ({len(errors)}건)"):
                    for e in errors:
                        st.text(e)
            else:
                st.success("🎉 모든 데이터가 성공적으로 업로드되었습니다!")

    except Exception as e:
        st.error(f"파일 읽기 오류: {e}\n\n시트 이름이 'MASTER_DB'인지 확인해주세요.")

st.markdown("---")
st.subheader("📥 업로드용 템플릿 다운로드")
st.caption("새 데이터를 입력할 때 이 템플릿을 사용하세요.")

template_data = {
    "대등록기준": ["26-1"],
    "소속": ["직할대"],
    "이름": ["홍길동"],
    "생년월일": ["2000.01.01"],
    "회원번호": ["123456"],
    "성별": ["남"],
    "연락처": ["010-0000-0000"],
    "두볼아이디": ["honggildong"],
    "경고횟수": [0],
    "활동참여현황": ["활동중"],
    "초급교육\n이수여부": ["O"],
    "봉사활동\n참여횟수": [0],
    "비고": [""]
}
import io
template_df = pd.DataFrame(template_data)
buffer = io.BytesIO()
template_df.to_excel(buffer, index=False, sheet_name="MASTER_DB")
buffer.seek(0)
st.download_button(
    "📄 템플릿 엑셀 다운로드",
    buffer,
    "rover_template.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
