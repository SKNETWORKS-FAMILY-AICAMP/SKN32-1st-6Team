# hyundai_faq_crawling.py

from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import re
import time

from model.faq_model import FAQModel


def run(max_items=None):

    driver = None
    limit_reached = False

    try:

        # =========================
        # 크롬 옵션
        # =========================

        options = Options()

        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # =========================
        # 크롬 실행
        # =========================

        driver = wd.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # =========================
        # 현대 FAQ 페이지 접속
        # =========================

        url = "https://www.hyundai.com/kr/ko/e/customer/center/faq"

        driver.get(url)

        time.sleep(3)

        print(driver.title)

        # =========================
        # DB 모델
        # =========================

        fm = FAQModel()

        # 기존 데이터 삭제
        fm.delete_all()

        # CSV 저장용 리스트
        faq_data = []

        # =========================
        # 탭 가져오기
        # =========================

        tabs = driver.find_elements(
            By.CSS_SELECTOR,
            '.tab-menu__icon button'
        )

        print("탭 개수 :", len(tabs))

        # =========================
        # 탭 반복
        # =========================

        for tab_index in range(len(tabs)):

            try:

                # 탭 다시 가져오기
                tabs = driver.find_elements(
                    By.CSS_SELECTOR,
                    '.tab-menu__icon button'
                )

                current_tab = tabs[tab_index]

                tab_name = current_tab.text.strip()

                print("\n")
                print("=" * 70)
                print(f"현재 탭 : {tab_name}")
                print("=" * 70)

                # 탭 클릭
                driver.execute_script(
                    "arguments[0].click();",
                    current_tab
                )

                time.sleep(3)

                # =========================
                # 페이지 반복
                # =========================

                while True:

                    try:

                        active_page = driver.find_element(
                            By.CSS_SELECTOR,
                            '.el-pager li.active'
                        ).text.strip()

                    except:

                        active_page = "1"

                    print(f"\n===== {active_page} 페이지 =====")

                    time.sleep(2)

                    # =========================
                    # FAQ 리스트 가져오기
                    # =========================

                    faq_items = driver.find_elements(
                        By.CSS_SELECTOR,
                        '.list-item'
                    )

                    print("FAQ 개수 :", len(faq_items))

                    # =========================
                    # FAQ 반복
                    # =========================

                    for i in range(len(faq_items)):

                        try:

                            # DOM 다시 가져오기
                            faq_items = driver.find_elements(
                                By.CSS_SELECTOR,
                                '.list-item'
                            )

                            item = faq_items[i]

                            # 질문 버튼
                            button = item.find_element(
                                By.CSS_SELECTOR,
                                '.list-title'
                            )

                            # 스크롤 이동
                            driver.execute_script(
                                "arguments[0].scrollIntoView(true);",
                                button
                            )

                            time.sleep(1)

                            # =========================
                            # active 여부 확인
                            # =========================

                            item_class = item.get_attribute("class")

                            # 닫혀있으면 클릭
                            if 'active' not in item_class:

                                driver.execute_script(
                                    "arguments[0].click();",
                                    button
                                )

                                # 답변 로딩 대기
                                WebDriverWait(driver, 5).until(
                                    lambda d: item.find_element(
                                        By.CSS_SELECTOR,
                                        '.conts'
                                    ).is_displayed()
                                )

                                time.sleep(1)

                            # =========================
                            # 데이터 추출
                            # =========================

                            company = "현대자동차"

                            category = item.find_element(
                                By.CSS_SELECTOR,
                                '.list-category'
                            ).text.strip()

                            question = item.find_element(
                                By.CSS_SELECTOR,
                                '.list-content'
                            ).text.strip()

                            answer = item.find_element(
                                By.CSS_SELECTOR,
                                '.conts'
                            ).text.strip()

                            # =========================
                            # 데이터 정제
                            # =========================

                            # URL 제거
                            answer = re.sub(
                                r'https?://\S+',
                                '',
                                answer
                            )

                            # www 제거
                            answer = re.sub(
                                r'www\.\S+',
                                '',
                                answer
                            )

                            # 바로가기 제거
                            answer = answer.replace(
                                '바로가기',
                                ''
                            )

                            # 공백 제거
                            answer = answer.strip()

                            print("=" * 50)
                            print("회사 :", company)
                            print("카테고리 :", category)
                            print("질문 :", question)
                            print("답변 :", answer)

                            # =========================
                            # DB 저장
                            # =========================

                            faq_info = (
                                company,
                                category,
                                question,
                                answer
                            )

                            fm.insert_faq(faq_info)

                            # =========================
                            # CSV 저장 리스트 추가
                            # =========================

                            faq_data.append({
                                'company': company,
                                'category': category,
                                'question': question,
                                'answer': answer
                            })

                            if max_items is not None and len(faq_data) >= max_items:
                                limit_reached = True
                                break

                        except Exception as e:

                            print("\nFAQ 수집 실패")
                            print(type(e).__name__)
                            print(e)

                            continue

                    if limit_reached:
                        break

                    # =========================
                    # 다음 페이지 이동
                    # =========================

                    try:

                        current_page = int(active_page)

                        next_page = driver.find_element(
                            By.XPATH,
                            f'//button[text()="{current_page + 1}"]'
                        )

                        driver.execute_script(
                            "arguments[0].click();",
                            next_page
                        )

                        time.sleep(3)

                    except:

                        print("마지막 페이지")
                        break

            except Exception as e:

                print("\n탭 처리 실패")
                print(type(e).__name__)
                print(e)

            if limit_reached:
                break

        # =========================
        # CSV 저장
        # =========================

        df = pd.DataFrame(faq_data)

        df.to_csv(
            'hyundai_faq.csv',
            index=False,
            encoding='utf-8-sig'
        )

        print("\nCSV 저장 완료")

        # =========================
        # 저장 결과 확인
        # =========================

        resultset = fm.select_all()

        print("\n")
        print("=" * 70)
        print("총 저장 데이터 :", len(resultset))
        print("=" * 70)

    # =========================
    # Ctrl + C 종료 처리
    # =========================

    except KeyboardInterrupt:

        print("\n사용자에 의해 크롤링이 중단되었습니다.")

    # =========================
    # 브라우저 종료
    # =========================

    finally:

        if driver:
            driver.quit()


# 실행
if __name__ == "__main__":
    run()