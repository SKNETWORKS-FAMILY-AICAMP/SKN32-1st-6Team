# model/faq_model.py
# hyundai_faq_crawling.py에서 사용하는 DB 모델
# utils/database.py와 동일한 접속 정보를 공유합니다.

import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (어디서 실행해도 동작)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mysql.connector
from mysql.connector import Error

from dotenv import load_dotenv
load_dotenv()


def _get_db_config():

    return {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": os.getenv("MYSQL_CHARSET"),
    }


class FAQModel:
    """
    현대자동차 FAQ MySQL CRUD 모델
    hyundai_faq_crawling.py에서 직접 사용합니다.
    """

    def __init__(self):
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        try:
            self.conn = mysql.connector.connect(**_get_db_config())
            self.cursor = self.conn.cursor()
        except Error as e:
            raise ConnectionError(f"DB 연결 실패: {e}\n"
                                  f"model/faq_model.py의 .env 파일을 확인하세요.")

    def _create_table(self):
        """faq_items 테이블이 없으면 생성"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq_items (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                company_code VARCHAR(50)  NOT NULL,
                category    VARCHAR(200),
                question    TEXT         NOT NULL,
                answer      LONGTEXT,
                crawled_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                session_id  VARCHAR(100),
                INDEX idx_company (company_code),
                INDEX idx_session (session_id),
                INDEX idx_crawled (crawled_at)
            ) CHARACTER SET utf8mb4
        """)
        self.conn.commit()

    # --------------------------------------------------
    # 크롤러가 사용하는 메서드
    # (company, category, question, answer) 튜플을 받습니다.
    # --------------------------------------------------

    def insert_faq(self, faq_info: tuple):
        """
        faq_info = (company, category, question, answer)
        company 값은 company_code 컬럼에 저장합니다.
        """
        company, category, question, answer = faq_info
        self.cursor.execute(
            """INSERT INTO faq_items
               (company_code, category, question, answer)
               VALUES (%s, %s, %s, %s)""",
            (company, category, question, answer)
        )
        self.conn.commit()

    def delete_all(self):
        """현대자동차 FAQ 전체 삭제 (크롤링 시작 전 초기화)"""
        self.cursor.execute(
            "DELETE FROM faq_items WHERE company_code = '현대자동차'"
        )
        self.conn.commit()

    def select_all(self):
        """현대자동차 FAQ 전체 조회"""
        self.cursor.execute(
            "SELECT * FROM faq_items WHERE company_code = '현대자동차'"
        )
        return self.cursor.fetchall()

    def select_by_category(self, category: str):
        self.cursor.execute(
            "SELECT * FROM faq_items WHERE company_code='현대자동차' AND category=%s",
            (category,)
        )
        return self.cursor.fetchall()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()
