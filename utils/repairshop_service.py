"""
정비소 서비스 데이터 관리 (repairshop_service.py)
- 여러 개로 흩어져 있던 설정, 주소 분석, 데이터베이스 연결, 데이터 정리 코드를 하나로 합친 파일
"""

from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text

from dotenv import load_dotenv
load_dotenv()
import os

# ==========================================
# 1. 기본 설정 및 환경 정보
# ==========================================

# 데이터베이스 연결에 필요한 비밀 정보들 (보안 파일에서 읽어옴)
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = int(os.getenv("MYSQL_PORT"))
DB_NAME = os.getenv("MYSQL_DATABASE")

# 파일 저장 위치 및 데이터 경로 설정
ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / "data" / "전국자동차정비업체표준데이터.csv"
VERSION_FILE = ROOT / ".repairshop_data_version"

# 다룰 자동차 브랜드와 주소 필터링을 위한 검색 키워드 기준
BRANDS = ["현대자동차", "기아자동차"]
SHOP_NAME_FILTER = r"현대|기아|블루핸즈|오토큐"
HYUNDAI_IN_NAME = ["현대", "블루핸즈"]
KIA_IN_NAME = ["기아", "오토큐"]
DATA_VERSION = 4  # 주소 정제 규칙이 바뀌었으므로 버전을 올려서 다시 저장되도록 유도

# 화면이나 표에 보여줄 항목 이름들
TABLE_COLUMNS = ["자동차정비업체명", "브랜드", "시도", "시군구", "소재지도로명주소", "자동차정비업체종류"]
DISPLAY_COLUMNS = TABLE_COLUMNS.copy()

# ==========================================
# 2. 도로명 주소 잘라내기 규칙
# ==========================================
def parse_address(address):
    text = str(address).strip()
    if not text or text.lower() in ("nan", "none"):
        return "", ""

    words = text.split()
    if not words:
        return "", ""

    # 시도
    sido = words[0]

    # 나머지 전부 시군구 통합 (서울/세종 포함 안정 처리)
    sigungu = " ".join(words[1:]).strip()

    return sido, sigungu

# ==========================================
# 3. 데이터베이스(DB) 연결 및 검색 기능
# ==========================================
def _get_engine(use_db=True):
    """데이터베이스와 파이썬을 안전하게 연결해주는 통로를 만드는 기능"""
    user, pw = quote_plus(DB_USER), quote_plus(DB_PASSWORD)
    url = f"mysql+pymysql://{user}:{pw}@{DB_HOST}:{DB_PORT}"
    if use_db:
        url += f"/{DB_NAME}"
    return create_engine(f"{url}?charset=utf8mb4")

def test_connection():
    """데이터베이스가 현재 잘 켜져 있고 연결되는지 점검하는 기능"""
    try:
        import pymysql
        with _get_engine(True).connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "연결됨"
    except Exception as e:
        msg = str(e)
        if "1049" in msg or "Unknown database" in msg:
            return False, "database 없음 → 자동 생성 시도"
        if "1045" in msg or "Access denied" in msg:
            return False, "DB 계정 및 비밀번호 확인 필요"
        return False, "MySQL 서버 상태 확인 필요"

def create_db_and_table():
    """저장 공간(데이터베이스와 표)이 없을 때 새로 만들어주는 기능"""
    sql_create_table = """
    CREATE TABLE IF NOT EXISTS repairshop (
        자동차정비업체명 VARCHAR(150) NOT NULL,
        브랜드 VARCHAR(50),
        시도 VARCHAR(50),
        시군구 VARCHAR(255),
        소재지도로명주소 VARCHAR(255),
        자동차정비업체종류 INT
    ) CHARACTER SET utf8mb4;
    """
    try:
        engine = _get_engine(use_db=False)
        with engine.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        return True, "DB·테이블 생성 완료"
    except Exception as e:
        return False, str(e)

def search_shops(brand=None, do=None, sigungu=None, keyword=None):

    where = f"`브랜드` IN ({','.join(repr(b) for b in BRANDS)})"
    clauses = [where, "`시도` != ''"]
    params = {}

    if brand:
        clauses.append("브랜드 = :brand")
        params["brand"] = brand

    if do:
        clauses.append("시도 = :do")
        params["do"] = do

    if sigungu:
        clauses.append("시군구 LIKE :sigungu")
        params["sigungu"] = f"%{sigungu}%"

    if keyword:
        clauses.append("(자동차정비업체명 LIKE :kw OR 소재지도로명주소 LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    sql = f"SELECT * FROM repairshop WHERE {' AND '.join(clauses)}"
    return pd.read_sql(text(sql), _get_engine(), params=params)

def get_region_lists():

    sql = f"""
        SELECT DISTINCT 시도, 시군구
        FROM repairshop
        WHERE 브랜드 IN ({','.join(repr(b) for b in BRANDS)})
          AND 시도 IS NOT NULL AND 시도 != ''
        ORDER BY 시도, 시군구
    """

    df = pd.read_sql(text(sql), _get_engine())

    tree = {}

    for _, row in df.iterrows():
        do = row["시도"].strip()
        sg = (row["시군구"] or "").strip()

        tree.setdefault(do, set())
        if sg:
            tree[do].add(sg)

    return tree

# ==========================================
# 4. 원본 파일 가져와서 깨끗하게 정리하고 저장하기
# ==========================================
def _pick_brand(shop_name):
    """정비소 이름에 포함된 글자를 보고 현대인지 기아인지 판별해주는 기능"""
    name = str(shop_name)
    if any(kw in name for kw in HYUNDAI_IN_NAME):
        return "현대자동차"
    if any(kw in name for kw in KIA_IN_NAME):
        return "기아자동차"
    return ""

def run_etl():

    raw_df = None

    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            raw_df = pd.read_csv(CSV_PATH, encoding=enc, low_memory=False)
            break
        except:
            continue

    if raw_df is None:
        raise FileNotFoundError("CSV 로드 실패")

    df = raw_df[
        raw_df["자동차정비업체명"]
        .astype(str)
        .str.contains(SHOP_NAME_FILTER, case=False, na=False)
    ].copy()

    df["브랜드"] = df["자동차정비업체명"].apply(_pick_brand)
    df = df[df["브랜드"].isin(BRANDS)]

    # 주소 파싱 (핵심 변경)
    regions = df["소재지도로명주소"].astype(str).apply(parse_address)
    df["시도"] = regions.apply(lambda x: x[0])
    df["시군구"] = regions.apply(lambda x: x[1])

    # ❗ 핵심: 서울 안 날아가게 최소 조건만 유지
    df = df[df["시도"].notna() & (df["시도"] != "")]
    df = df.dropna(subset=["시도"])

    for col in TABLE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    cleaned_df = df[TABLE_COLUMNS].drop_duplicates()

    cleaned_df.to_sql(
        "repairshop",
        _get_engine(),
        if_exists="replace",
        index=False
    )

    return len(cleaned_df)

def prepare_data():
    """프로그램을 시작할 때 데이터가 정상적으로 들어있는지 확인하고 알아서 채워두는 기능"""
    # 데이터베이스 연결 상태를 점검하고 없으면 새로 만듦
    ok, _ = test_connection()
    if not ok:
        ok2, msg2 = create_db_and_table()
        if not ok2:
            return False, msg2

    # 현재 데이터베이스에 저장된 정비소 데이터 개수 파악
    try:
        count_df = pd.read_sql(text("SELECT COUNT(*) AS n FROM repairshop"), _get_engine())
        count = int(count_df["n"].iloc[0])
    except Exception:
        count = 0

    # 마지막으로 저장했던 데이터의 버전 체크
    saved_ver = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    
    # 데이터가 아예 없거나 프로그램 버전이 바뀌었다면 원본 CSV를 다시 읽어서 데이터 최신화
    if count == 0 or saved_ver != str(DATA_VERSION):
        if not CSV_PATH.exists():
            return False, f"CSV 없음: data/{CSV_PATH.name}"
        run_etl()
        VERSION_FILE.write_text(str(DATA_VERSION), encoding="utf-8")

    return True, ""

if __name__ == "__main__":
    print("단독 ETL 테스트 시작...")
    try:
        inserted = run_etl()
        print(f"성공! DB 적재 완료 ({inserted}건)")
    except Exception as e:
        print(f"실패: {e}")