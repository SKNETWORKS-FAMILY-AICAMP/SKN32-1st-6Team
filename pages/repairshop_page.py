"""
정비소 조회 화면 (Streamlit)
"""
import streamlit as st
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils.repairshop_service import (
    prepare_data, 
    search_shops, 
    get_region_lists, 
    DISPLAY_COLUMNS,
    BRANDS 
)

NO_SI = "__NO_SI__"

def _to_query_value(selected, all_label="전체"):
    return None if selected == all_label else selected

def _si_choices(region_tree, do):
    if do == "전체":
        return ["전체"]
    
    sub_data = region_tree.get(do, {})
    if not isinstance(sub_data, dict):
        return ["전체", NO_SI]
        
    keys = sorted(sub_data.keys(), key=lambda k: (k != "", k))
    return ["전체"] + [NO_SI if k == "" else k for k in keys]

def _gu_choices(region_tree, do, si):
    if do == "전체":
        return ["전체"]
        
    by_si = region_tree.get(do, {})
    raw_gus = set()
    
    # 데이터 구조에 따른 구 정보 통합 추출
    if isinstance(by_si, (set, list, tuple)):
        raw_gus = set(by_si)
    elif isinstance(by_si, dict):
        if si == "전체":
            for gset in by_si.values():
                raw_gus |= set(gset.keys()) if isinstance(gset, dict) else set(gset)
        else:
            target_si = "" if si == NO_SI else si
            gset = by_si.get(target_si, set())
            raw_gus = set(gset)
            
    # 주소 전체에서 "구" 이름만 첫 단어로 추출 및 중복 제거
    refined_gus = {g.strip().split()[0] for g in raw_gus if g and isinstance(g, str)}
    return ["전체"] + sorted(list(refined_gus))

def render():
    st.image("정비소배너.png", use_container_width=True)
    st.markdown("---")
    st.header("🛠️ 정비소 조회")
    st.caption("현대(블루핸즈) · 기아(오토큐)") 

    # 데이터 초기화 (1회 실행)
    if not st.session_state.get("repair_loaded"):
        with st.spinner("데이터 준비 중..."):
            ok, err = prepare_data()
        st.session_state.repair_loaded = True
        if not ok:
            st.error(err)
            return

    region_tree = get_region_lists() if isinstance(get_region_lists(), dict) else {}

    # ---------- 검색 필터 UI ----------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        brand = st.selectbox("브랜드", ["전체"] + BRANDS)
    with c2:
        do = st.selectbox("시/도", ["전체"] + sorted(region_tree.keys()), key="r_do")
    with c3:
        si = st.selectbox(
            "시/군", _si_choices(region_tree, do), key=f"r_si_{do}",
            format_func=lambda x: "전체" if x == NO_SI else x
        )
    with c4:
        gu = st.selectbox("구", _gu_choices(region_tree, do, si), key=f"r_gu_{do}_{si}")

    c_search, c_btn = st.columns([4, 1])
    with c_search:
        keyword = st.text_input("검색", placeholder="업체명, 주소")
    with c_btn:
        clicked = st.button("조회", type="primary", use_container_width=True)

    if not clicked:
        st.info("조건 선택 후 **조회**를 누르세요.")
        return

    # ---------- 데이터 조회 및 결과 출력 ----------
    try:
        df = search_shops(
            brand=_to_query_value(brand),
            do=_to_query_value(do),
            sigungu=_to_query_value(gu),
            keyword=keyword or None,
        )
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

    display_si = "전체" if si in ["전체", None, NO_SI] else si
    st.subheader(f"{do} {display_si} {gu}에 위치한 {brand} 정비소 조회 결과") 
    st.metric("총 정비소 개수", f"{len(df):,}곳")

    tab1 = st.tabs(["목록"])[0]
    with tab1:
        if df.empty:
            st.info("검색 결과가 없습니다.")
        else:
            cols = [c for c in DISPLAY_COLUMNS if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)