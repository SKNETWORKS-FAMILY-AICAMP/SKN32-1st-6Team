"""
repairshop_service.py
- 기존 config, address_parser, repairshop_db, repairshop_data를 하나로 통합한 파일입니다.
"""

from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text

# ==========================================
# 1. CONFIG 설정 (기존 repairshop_config.py)
# ==========================================
DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = "student", "student80", "localhost", "3306", "repairshopdb"
ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / "data" / "전국자동차정비업체표준데이터.csv"
VERSION_FILE = ROOT / ".repairshop_data_version"

BRANDS = ["현대자동차", "기아자동차"]
SHOP_NAME_FILTER = r"현대|기아|블루핸즈|오토큐"
HYUNDAI_IN_NAME = ["현대", "블루핸즈"]
KIA_IN_NAME = ["기아", "오토큐"]
DATA_VERSION = 3

TABLE_COLUMNS = ["자동차정비업체명", "브랜드", "시도", "시", "구", "소재지도로명주소", "자동차정비업체종류"]
DISPLAY_COLUMNS = TABLE_COLUMNS.copy()

# ==========================================
# 2. 주소 파서 (기존 address_parser.py)
# ==========================================
def parse_address(address):
    """주소 문자열을 (도/시도, 시/군, 구)로 분리"""
    text = str(address).strip()
    if not text or text.lower() in ("nan", "none"):
        return "", "", ""
    
    words = text.split()
    if not words:
        return "", "", ""
    
    # 1단계: 도/시도 판별
    do = words[0]
    si, gu = "", ""
    
    # 2단계: 시/군/구 추출 구문 간소화
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
    return "(시·군 없음)" if not str(si).strip() else str(si)

# ==========================================
# 3. DB 연동 및 조회 (기존 repairshop_db.py)
# ==========================================
def _get_engine(use_db=True):
    user, pw = quote_plus(DB_USER), quote_plus(DB_PASSWORD)
    url = f"mysql+pymysql://{user}:{pw}@{DB_HOST}:{DB_PORT}"
    if use_db:
        url += f"/{DB_NAME}"
    return create_engine(f"{url}?charset=utf8mb4")

def test_connection():
    try:
        import pymysql  # 검증용
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
    where = [f"`브랜드` IN ({','.join(repr(b) for b in BRANDS)})"]
    params = {}

    if brand:
        where.append("`브랜드` = :brand"); params["brand"] = brand
    if do:
        where.append("`시도` = :do"); params["do"] = do
    if si is not None:
        if si == "":
            where.append("(`시` IS NULL OR `시` = '')")
        else:
            where.append("`시` = :si"); params["si"] = si
    if gu:
        where.append("`구` = :gu"); params["gu"] = gu
    if keyword:
        where.append("(`자동차정비업체명` LIKE :kw OR `소재지도로명주소` LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    sql = f"SELECT * FROM repairshop WHERE {' AND '.join(where)}"
    return pd.read_sql(text(sql), _get_engine(), params=params)

def get_region_lists():
    """도 > 시/군 > 구 트리 구조 반환 (필터 박스용)"""
    df = pd.read_sql(
        text(f"SELECT DISTINCT `시도`, `시`, `구` FROM repairshop WHERE `브랜드` IN ({','.join(repr(b) for b in BRANDS)}) ORDER BY `시도`, `시`, `구`"),
        _get_engine()
    )
    tree = {}
    for _, row in df.iterrows():
        do = str(row["시도"] or "").strip()
        si = str(row["시"] or "").strip()
        gu = str(row["구"] or "").strip()
        if do:
            tree.setdefault(do, {}).setdefault(si, set())
            if gu:
                tree[do][si].add(gu)
    return tree

# ==========================================
# 4. DATA ETL 프로세스 (기존 repairshop_data.py)
# ==========================================
def _pick_brand(shop_name):
    name = str(shop_name)
    if any(kw in name for kw in HYUNDAI_IN_NAME):
        return "현대자동차"
    if any(kw in name for kw in KIA_IN_NAME):
        return "기아자동차"
    return ""

def run_etl():
    # CSV 읽기 (인코딩 예외 처리 통합)
    raw_df = None
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            raw_df = pd.read_csv(CSV_PATH, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
    if raw_df is None:
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없거나 읽을 수 없습니다: {CSV_PATH}")

    # 데이터 정제
    df = raw_df[raw_df["자동차정비업체명"].astype(str).str.contains(SHOP_NAME_FILTER, case=False, na=False)].copy()
    df["브랜드"] = df["자동차정비업체명"].apply(_pick_brand)
    df = df[df["브랜드"].isin(BRANDS)]

    # 주소 파싱 적용
    regions = df["소재지도로명주소"].astype(str).apply(parse_address)
    df["시도"] = regions.apply(lambda x: x[0])
    df["시"] = regions.apply(lambda x: x[1])
    df["구"] = regions.apply(lambda x: x[2])

    for col in TABLE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    cleaned_df = df[TABLE_COLUMNS].drop_duplicates()
    
    # DB 저장
    cleaned_df.to_sql("repairshop", _get_engine(), if_exists="replace", index=False)
    return len(cleaned_df)

def prepare_data():
    ok, _ = test_connection()
    if not ok:
        ok2, msg2 = create_db_and_table()
        if not ok2:
            return False, msg2

    # 데이터 건수 및 버전 체크 후 자동 적재
    try:
        count_df = pd.read_sql(text("SELECT COUNT(*) AS n FROM repairshop"), _get_engine())
        count = int(count_df["n"].iloc[0])
    except Exception:
        count = 0

    saved_ver = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    
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