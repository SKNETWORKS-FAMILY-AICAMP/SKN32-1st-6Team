"""
자동차 대시보드 메인 앱
- 전국 자동차 등록 현황
- 기업 FAQ 조회
- 정비소 조회
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="자동차 등록 & FAQ 대시보드",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS 스타일 (보내주신 고유 테마 유지)
st.markdown("""
<style>
    /* 사이드바 스타일 */
    .sidebar-title {
        font-size: 20px;
        font-weight: 700;
        color: #1a1a2e;
        padding: 10px 0;
    }
    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        background-color: #f0f4ff;
        border: 1px solid #d0d8ff;
        border-radius: 10px;
        padding: 10px 15px;
    }
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    /* 헤더 */
    h1 { color: #1a1a2e; }
    h2 { color: #16213e; }
    h3 { color: #0f3460; }
    /* expander */
    .streamlit-expanderHeader {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# 사이드바 네비게이션 & 제어 패널
# =========================================================================
with st.sidebar:
    st.markdown("## 🚗 자동차 대시보드")
    st.markdown("---")

    page = st.radio(
        "메뉴",
        ["🚗 전국 자동차 등록 현황", "🔍 기업 FAQ 조회", "🛠️ 현대/기아 정비소 조회"],
        label_visibility="collapsed",
    )

    # 🌟 [새로 추가] 크롤러 컨트롤 패널 (실시간 수집 범위 조절 제어 바)
    st.markdown("---")
    st.markdown("### ⚙️ 크롤러 컨트롤 패널")
    
    # 세션 상태 초기화 및 슬라이더 생성
    if "crawling_limit" not in st.session_state:
        st.session_state["crawling_limit"] = 1500

    st.session_state["crawling_limit"] = st.slider(
        "실시간 수집 범위 설정",
        min_value=100,
        max_value=5000,
        value=st.session_state["crawling_limit"],
        step=100,
        help="크롤링 및 DB 분석에 반영될 실시간 데이터 개수의 상한선을 지정합니다."
    )
    st.caption(f"🎯 수집 상한선: `{st.session_state['crawling_limit']:,}` 개 항목")

    # 시스템 정보 영역 시작
    st.markdown("---")
    st.markdown("### 📌 시스템 정보")

    # DB 상태 1 (FAQ)
    db_ok = False
    try:
        from utils.database import get_connection
        conn = get_connection()
        conn.close()
        db_ok = True
    except Exception:
        pass

    st.markdown(f"**MySQL (FAQ)**: {'🟢 연결됨' if db_ok else '🔴 미연결'}")

    # DB 상태 2 (정비소)
    repair_db_ok = False
    repair_db_msg = ""
    try:
        from utils.repairshop_service import test_connection as repair_db_test
        repair_db_ok, repair_db_msg = repair_db_test()
    except Exception as e:
        repair_db_msg = str(e)
    st.markdown(f"**MySQL (정비소)**: {'🟢 연결됨' if repair_db_ok else '🔴 미연결'}")
    if not repair_db_ok and repair_db_msg:
        st.caption(repair_db_msg[:120])

    # 크롤러 엔진 라이브러리 상태
    crawler_ok = False
    try:
        import selenium
        from bs4 import BeautifulSoup
        crawler_ok = True
    except ImportError:
        pass

    st.markdown(f"**크롤러**: {'🟢 준비됨' if crawler_ok else '🔴 미설치'}")

    # 데이터 파일 수 체크 (폴더 자동생성 방어코드 포함)
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True) # 없으면 만듦
    xlsx_count = len(list(data_dir.glob("*.xlsx")))
    st.markdown(f"**데이터 파일**: {xlsx_count}개")

    st.markdown("---")
    st.markdown(
        "<small>📦 필요 패키지<br>"
        "• streamlit<br>"
        "• pandas, openpyxl<br>"
        "• plotly<br>"
        "• selenium<br>"
        "• beautifulsoup4<br>"
        "• mysql-connector-python</small>",
        unsafe_allow_html=True
    )


# =========================================================================
# 페이지 라우팅 실행
# =========================================================================
if "전국 자동차" in page:
    from pages.car_page import render
    render()
elif "정비소" in page:
    from pages.repairshop_page import render
    render()
else:
    from pages.faq_page import render
    render()