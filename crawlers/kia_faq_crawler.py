"""
기아자동차 FAQ 크롤러
Beautiful Soup + Selenium 활용
"""
# kia_crawler.py

import time
import re

from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager


COMPANY_CODE = "기아자동차"
COMPANY_NAME = "기아자동차"

FAQ_URL = "https://www.kia.com/kr/customer-service/center/faq"


def crawl_kia_faq(progress_callback=None):

    driver = None

    results = []

    try:

        # =========================
        # 크롬 옵션
        # =========================

        options = Options()

        options.add_argument("--start-maximized")
        options.add_argument("window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # =========================
        # 크롬 실행
        # =========================

        driver = wd.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        driver.maximize_window()

        # =========================
        # 페이지 접속
        # =========================

        if progress_callback:
            progress_callback("기아 FAQ 페이지 접속 중...")

        driver.get(FAQ_URL)

        time.sleep(3)

        # =========================
        # 탭 가져오기
        # =========================

        tabs = driver.find_elements(
            By.CSS_SELECTOR,
            '#tab-list .tabs__btn'
        )

        skip_tabs = [
            'TOP 10',
            '전체'
        ]

        # =========================
        # 탭 반복
        # =========================

        for tab_index in range(len(tabs)):

            try:

                tabs = driver.find_elements(
                    By.CSS_SELECTOR,
                    '#tab-list .tabs__btn'
                )

                current_tab = tabs[tab_index]

                tab_name = current_tab.find_element(
                    By.CSS_SELECTOR,
                    '.name'
                ).text.strip()

                # 제외 탭 스킵
                if tab_name in skip_tabs:

                    continue

                if progress_callback:
                    progress_callback(f"[{tab_name}] 수집 중...")

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
                            '.paging-list li.is-active'
                        ).text.strip()

                    except:

                        active_page = "1"

                    # =========================
                    # FAQ 가져오기
                    # =========================

                    faq_items = driver.find_elements(
                        By.CSS_SELECTOR,
                        '.cmp-accordion__item'
                    )

                    for i in range(len(faq_items)):

                        try:

                            faq_items = driver.find_elements(
                                By.CSS_SELECTOR,
                                '.cmp-accordion__item'
                            )

                            item = faq_items[i]

                            button = item.find_element(
                                By.CSS_SELECTOR,
                                '.cmp-accordion__button'
                            )

                            # 스크롤
                            driver.execute_script(
                                "arguments[0].scrollIntoView(true);",
                                button
                            )

                            time.sleep(1)

                            # 펼침 여부
                            button_class = button.get_attribute("class")

                            if 'cmp-accordion__button--expanded' not in button_class:

                                driver.execute_script(
                                    "arguments[0].click();",
                                    button
                                )

                                WebDriverWait(driver, 5).until(
                                    lambda d: item.find_element(
                                        By.CSS_SELECTOR,
                                        '.cmp-accordion__panel'
                                    ).is_displayed()
                                )

                                time.sleep(1)

                            # =========================
                            # 데이터 추출
                            # =========================

                            question = item.find_element(
                                By.CSS_SELECTOR,
                                '.cmp-accordion__title'
                            ).text.strip()

                            answer = item.find_element(
                                By.CSS_SELECTOR,
                                '.cmp-accordion__panel'
                            ).text.strip()

                            # =========================
                            # 데이터 정제
                            # =========================

                            answer = re.sub(
                                r'https?://\S+',
                                '',
                                answer
                            )

                            answer = re.sub(
                                r'www\.\S+',
                                '',
                                answer
                            )

                            answer = answer.replace(
                                '바로가기',
                                ''
                            )

                            answer = answer.strip()

                            # =========================
                            # 결과 저장
                            # =========================

                            results.append({

                                "category": tab_name,

                                "question": question,

                                "answer": answer

                            })

                        except Exception:

                            continue

                    # =========================
                    # 다음 페이지 이동
                    # =========================

                    try:

                        current_page = int(active_page)

                        try:

                            next_page = driver.find_element(
                                By.XPATH,
                                f'//a[text()="{current_page + 1}"]'
                            )

                            driver.execute_script(
                                "arguments[0].click();",
                                next_page
                            )

                            time.sleep(3)

                        except:

                            next_group = driver.find_element(
                                By.CSS_SELECTOR,
                                '.pagigation-btn-next'
                            )

                            driver.execute_script(
                                "arguments[0].click();",
                                next_group
                            )

                            time.sleep(3)

                    except:

                        break

            except Exception:

                continue

        # =========================
        # 중복 제거
        # =========================

        unique_results = []

        seen_questions = set()

        for item in results:

            question = item["question"]

            if question not in seen_questions:

                seen_questions.add(question)

                unique_results.append(item)

        if progress_callback:
            progress_callback(
                f"{len(unique_results)}개 FAQ 수집 완료"
            )

        return unique_results

    finally:

        if driver:
            driver.quit()



# =========================
# Streamlit 범용 크롤러용
# =========================

# def crawl_generic_faq(
#     url=None,
#     company_code=None,
#     company_name=None,
#     progress_callback=None
# ):

#     return crawl_kia_faq(
#         progress_callback=progress_callback
#     )