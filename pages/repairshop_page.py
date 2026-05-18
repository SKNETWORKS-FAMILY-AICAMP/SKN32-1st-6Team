"""
정비소 조회 화면 (Streamlit)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# 통합 파일에서 필요한 함수를 한 번에 가져옴
from utils.repairshop_service import (
    prepare_data, 
    search_shops, 
    get_region_lists, 
    si_display_name, 
    DISPLAY_COLUMNS,
    BRANDS 
)

# 시/군이 없는 지역(서울 등) 선택용 — 내부 값
NO_SI = "__NO_SI__"


def _to_query_value(selected, all_label="전체"):
    """'전체'면 None, 아니면 그대로"""
    return None if selected == all_label else selected


def _si_choices(region_tree, do):
    if do == "전체":
        return ["전체"]
    keys = sorted(region_tree.get(do, {}).keys(), key=lambda k: (k != "", k))
    out = ["전체"]
    for k in keys:
        out.append(NO_SI if k == "" else k)
    return out


def _gu_choices(region_tree, do, si):
    if do == "전체":
        return ["전체"]
    by_si = region_tree.get(do, {})
    gus = set()
    if si == "전체":
        for gset in by_si.values():
            gus |= gset
    elif si == NO_SI:
        gus |= by_si.get("", set())
    else:
        gus |= by_si.get(si, set())
    return ["전체"] + sorted(gus)


def _si_for_db(si):
    if si == "전체" or si is None:
        return None
    if si == NO_SI:
        return ""
    return si


def render():
    st.header("🛠️ 현대/기아 정비소 조회")

    # DB + CSV 준비 (최초 1회, 백그라운드)
    if not st.session_state.get("repair_loaded"):
        with st.spinner("데이터 준비 중..."):
            ok, err = prepare_data()
        st.session_state.repair_loaded = True
        if not ok:
            st.error(err)
            return

    try:
        region_tree = get_region_lists()
    except Exception as e:
        st.error(f"지역 목록 오류: {e}")
        region_tree = {}

    # ---------- 필터 ----------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        brand = st.selectbox("브랜드", ["전체"] + BRANDS)
    with c2:
        do = st.selectbox("도", ["전체"] + sorted(region_tree.keys()), key="r_do")
    with c3:
        si = st.selectbox(
            "시/군",
            _si_choices(region_tree, do),
            key=f"r_si_{do}",
            format_func=lambda x: "전체" if x == "전체" else si_display_name("" if x == NO_SI else x),
        )
    with c4:
        gu = st.selectbox("구", _gu_choices(region_tree, do, si), key=f"r_gu_{do}_{si}")

    c_search, c_btn = st.columns([4, 1])
    with c_search:
        keyword = st.text_input("검색", placeholder="업체명, 주소")
    with c_btn:
        st.write("")
        clicked = st.button("조회", type="primary", use_container_width=True)

    if not clicked:
        st.info("조건 선택 후 **조회**를 누르세요.")
        return

# ---------- 조회 ----------
    try:
        df = search_shops(
            brand=_to_query_value(brand),
            do=_to_query_value(do),
            si=_si_for_db(si),
            gu=_to_query_value(gu),
            keyword=keyword or None,
        )
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

    # 1. 사용자가 '시/군'에서 NO_SI(빈값)를 선택했는지 처리
    display_si = "전체" if si == "전체" else si_display_name("" if si == NO_SI else si)
    if not display_si or display_si.strip() == "":
        display_si = "전체"

    # 2. 동적 안내 문구 생성
    status_text = f"{do} {display_si} {gu}에 위치한 {brand} 정비소 조회 결과"
    st.subheader(status_text) # 목록 탭 바로 위에 문구 표시

    # 3. 기존 총 정비소 개수 메트릭 표시
    st.metric("총 정비소 개수", f"{len(df):,}곳")

    # '목록' 탭 딱 하나만 만들고, 그 탭 객체를 tab1 변수에 바로 쏙 담습니다.
    tab1 = st.tabs(["목록"])[0]

    with tab1:
        if df.empty:
            st.info("검색 결과가 없습니다.")
        else:
            cols = [c for c in DISPLAY_COLUMNS if c in df.columns]
            show = df
            st.dataframe(show[cols], use_container_width=True, hide_index=True)