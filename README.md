# 🚗 자동차 등록 & 기업 FAQ 대시보드

Streamlit 기반 데이터 조회 GUI 애플리케이션

---

## 주요 기능

### 1. 전국 자동차 등록 현황
- KOSIS 자동차등록대수현황 xlsx 자동 파싱
- 시도별 / 차종별 / 용도별 필터링
- 막대 차트, 파이 차트, 스택 차트
- 시군구 상세 조회

### 2. 기업 FAQ 조회
- Selenium + BeautifulSoup 기반 크롤링
- MySQL 누적 저장 및 조회
- 크롤링 세션별 결과 vs 전체 누적 데이터 구분

---

## 설치 및 실행
### 0. 가상환경 구성
```bash
python -m venv .venv
```

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. MySQL 설정 (FAQ 누적 저장 시 필요)
`.env`에서 DB_CONFIG 수정:
```python
# MySQL DB connection settings
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=student
MYSQL_PASSWORD=<패스워드>
MYSQL_DATABASE=car_dashboard
MYSQL_CHARSET=utf8mb4
```

### 3. webdriver-manager 설치 (크롤링 시 필요)
```bash
pip install webdriver-manager
```

### 4. 앱 실행
```bash
cd proto_proj1
streamlit run app.py
```

---

## 프로젝트 구조

```
proto_proj1/
├── app.py                  # 메인 진입점
├── requirements.txt
├── data/                   # xlsx 파일 폴더 (자동 인식)
│   └── 자동차등록대수현황_시도별_*.xlsx
├── pages/
│   ├── car_page.py         # 자동차 등록 현황 페이지
│   └── faq_page.py         # FAQ 조회 페이지
│   └── repairshop_page.py  # 정비소 페이지
├── utils/
│   ├── car_data.py           # xlsx 파싱 유틸
│   └── database.py           # FAQ데이터 MySQL 연동
│   └── repairshop_service.py # 정비소 데이터 MySQL 연동
├── crawlers/
│   └── faq_crawler.py
│   └── hyundai_faq_crawler.py  # 현대자동차 FAQ 크롤러
│   └── kia_faq_crawler.py      # 기아자동차 FAQ 크롤러
├── sql/
│   └── repairshop.sql        # 정비소 데이터 SQL문
│   └── schema.sql            #  FAQ 데이터 SQL문(현대 + 기아.)
├── model/
│   └── faq_model.py          # 크롤링된 데이터를 utils/database.py에서 설정된 스키마로 저장
```
---
![image](./diagram.png)
