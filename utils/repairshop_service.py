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
TABLE_COLUMNS = ["자동차정비업체명", "브랜드", "시도", "시", "구", "소재지도로명주소", "자동차정비업체종류"]
DISPLAY_COLUMNS = TABLE_COLUMNS.copy()

# ==========================================
# 2. 도로명 주소 잘라내기 규칙
# ==========================================
def parse_address(address):
    """긴 주소 문장을 받아서 (시·도 / 시·군 / 구) 3단계로 쪼개주는 기능"""
    text = str(address).strip()
    if not text or text.lower() in ("nan", "none"):
        return "", "", ""
    
    words = text.split()
    if not words:
        return "", "", ""
    
    # 첫 번째 단어는 무조건 '서울시', '경기도' 같은 시·도 단위로 지정
    do = words[0]
    si, gu = "", ""
    
    # 두 번째 단어부터 돌면서 '시', '군', '구'로 끝나는 단어를 찾아 분류
    i = 1
    while i < len(words):
        w = words[i]
        if w.endswith("구"):
            gu = w
            break
        if (w.endswith("시") or w.endswith("군")) and not si:
            si = w
            i += 1
            continue
        break
        
    if do and not si and not gu and i < len(words) and words[i].endswith("구"):
        gu = words[i]
        
    return do, si, gu

def si_display_name(si):
    """시·군 항목이 없으면 빈칸으로 두고, 있으면 그대로 보여주는 기능"""
    return "" if not str(si).strip() else str(si)

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
    sql_create_table = f"""
    CREATE TABLE IF NOT EXISTS repairshop (
        자동차정비업체명 VARCHAR(150) NOT NULL,
        브랜드 VARCHAR(50),
        시도 VARCHAR(50),
        시 VARCHAR(50),
        구 VARCHAR(50),
        소재지도로명주소 VARCHAR(255),
        자동차정비업체종류 INT
    ) CHARACTER SET utf8mb4;
    """
    try:
        engine = _get_engine(use_db=False)
        with engine.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.execute(text(f"USE {DB_NAME}"))
            conn.execute(text("DROP TABLE IF EXISTS repairshop"))
            conn.execute(text(sql_create_table))
        return True, "DB·테이블 생성 완료"
    except Exception as e:
        return False, str(e)

def search_shops(brand=None, do=None, si=None, gu=None, keyword=None):
    """사용자가 고른 브랜드, 지역, 검색어를 바탕으로 정비소를 찾아주는 기능"""
    where = f"`브랜드` IN ({','.join(repr(b) for b in BRANDS)})"
    
    # 주소가 제대로 입력 안 된 정상적이지 않은 데이터는 검색 대상에서 제외
    where_clauses = [where, "`시도` != ''", "`시도` IS NOT NULL"]
    params = {}

    if brand:
        where_clauses.append("`브랜드` = :brand"); params["brand"] = brand
    if do:
        where_clauses.append("`시도` = :do"); params["do"] = do
    if si:
        where_clauses.append("`시` = :si"); params["si"] = si
    if gu:
        where_clauses.append("`구` = :gu"); params["gu"] = gu
    if keyword:
        where_clauses.append("(`자동차정비업체명` LIKE :kw OR `소재지도로명주소` LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    sql = f"SELECT * FROM repairshop WHERE {' AND '.join(where_clauses)}"
    return pd.read_sql(text(sql), _get_engine(), params=params)

def get_region_lists():
    """웹 화면의 필터(선택 박스)에 띄워줄 '시도 > 시군 > 구' 목록을 계층 구조로 만드는 기능"""
    # 데이터베이스에서 '시도'와 '시' 항목이 둘 다 명확하게 채워진 깨끗한 데이터만 골라옴
    sql = f"""
        SELECT DISTINCT `시도`, `시`, `구` 
        FROM repairshop 
        WHERE `브랜드` IN ({','.join(repr(b) for b in BRANDS)})
          AND `시도` IS NOT NULL AND `시도` != ''
          AND `시` IS NOT NULL AND `시` != ''
        ORDER BY `시도`, `시`, `구`
    """
    df = pd.read_sql(text(sql), _get_engine())
    tree = {}
    for _, row in df.iterrows():
        do = str(row["시도"]).strip()
        si = str(row["시"]).strip()
        gu = str(row["구"] or "").strip()
        
        # 주소에 구멍(빈 곳)이 없는 데이터만 골라 트리 구조(도 안의 시, 시 안의 구)로 조립
        if do and si:
            tree.setdefault(do, {}).setdefault(si, set())
            if gu:
                tree[do][si].add(gu)
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
    """엑셀(CSV) 원본 파일을 열어서 정제한 뒤 데이터베이스에 집어넣는 핵심 기능"""
    raw_df = None
    # 한글 깨짐을 방지하기 위해 여러 인코딩 방식으로 파일 읽기 시도
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            raw_df = pd.read_csv(CSV_PATH, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
    if raw_df is None:
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없거나 읽을 수 없습니다: {CSV_PATH}")

    # 현대/기아 관련 정비소만 필터링하여 남기기
    df = raw_df[raw_df["자동차정비업체명"].astype(str).str.contains(SHOP_NAME_FILTER, case=False, na=False)].copy()
    df["브랜드"] = df["자동차정비업체명"].apply(_pick_brand)
    df = df[df["브랜드"].isin(BRANDS)]

    # 위에서 만든 주소 잘라내기 기능을 이용해 주소를 쪼개서 새 칸에 입력
    regions = df["소재지도로명주소"].astype(str).apply(parse_address)
    df["시도"] = regions.apply(lambda x: x[0])
    df["시"] = regions.apply(lambda x: x[1])
    df["구"] = regions.apply(lambda x: x[2])

    # [요청 반영] 주소에 '시도'와 '시' 항목이 비어 있거나 누락된 행은 아예 버리기 (필터에 안 나오게 처리)
    df = df[(df["시도"] != "") & (df["시도"].notna())]
    df = df[(df["시"] != "") & (df["시"].notna())]

    # 혹시 누락된 데이터 칸이 있다면 빈 문자열로 채워주기
    for col in TABLE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # 중복 데이터 제거
    cleaned_df = df[TABLE_COLUMNS].drop_duplicates()
    
    # 최종 정리된 데이터를 데이터베이스 테이블에 덮어쓰기 형태로 저장
    cleaned_df.to_sql("repairshop", _get_engine(), if_exists="replace", index=False)
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