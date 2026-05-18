# faq_model.py

import mysql.connector


class FAQModel:

    # =========================
    # DB 연결
    # =========================

    def connect_db(self):

        return mysql.connector.connect(
            host='localhost',
            user='student',
            password='student80',
            database='car_faq_db'
        )

    # =========================
    # FAQ 저장
    # =========================

    def insert_faq(self, faq_info):

        conn = self.connect_db()

        cursor = conn.cursor()

        sql = """
        INSERT INTO faq
        (
            company,
            category,
            question,
            answer
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """

        cursor.execute(sql, faq_info)

        conn.commit()

        cursor.close()
        conn.close()

    # =========================
    # 전체 삭제
    # =========================

    def delete_all(self):

        conn = self.connect_db()

        cursor = conn.cursor()

        sql = "DELETE FROM faq"

        cursor.execute(sql)

        conn.commit()

        cursor.close()
        conn.close()

    # =========================
    # 전체 조회
    # =========================

    def select_all(self):

        conn = self.connect_db()

        cursor = conn.cursor()

        sql = "SELECT * FROM faq"

        cursor.execute(sql)

        result = cursor.fetchall()

        cursor.close()
        conn.close()

        return result