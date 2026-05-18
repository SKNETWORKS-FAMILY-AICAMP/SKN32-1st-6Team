-- sql/schema.sql
-- car_dashboard DB 전체 스키마
-- MySQL 8.x 이상 권장

CREATE DATABASE IF NOT EXISTS car_dashboard
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE car_dashboard;

-- 기업 목록 테이블
CREATE TABLE IF NOT EXISTS faq_companies (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    company_code VARCHAR(50)  UNIQUE NOT NULL COMMENT '영문 코드 (hyundai, kia 등)',
    company_name VARCHAR(100) NOT NULL,
    faq_url      VARCHAR(500) NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4;

-- FAQ 데이터 테이블
-- company_code 에 '현대자동차' 같은 한글 company 값도 허용 (크롤러 호환)
CREATE TABLE IF NOT EXISTS faq_items (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    company_code VARCHAR(50)  NOT NULL COMMENT 'faq_companies.company_code 또는 팀원 크롤러의 company 값',
    category     VARCHAR(200),
    question     TEXT         NOT NULL,
    answer       LONGTEXT,
    crawled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id   VARCHAR(100) COMMENT 'Streamlit GUI 크롤 세션 ID',
    INDEX idx_company (company_code),
    INDEX idx_session (session_id),
    INDEX idx_crawled (crawled_at)
) CHARACTER SET utf8mb4;

-- 크롤 세션 이력 테이블
CREATE TABLE IF NOT EXISTS crawl_sessions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(100) UNIQUE NOT NULL,
    company_code VARCHAR(50),
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at     TIMESTAMP NULL,
    total_count  INT DEFAULT 0,
    status       VARCHAR(50) DEFAULT 'running'
) CHARACTER SET utf8mb4;

-- 기본 기업 데이터 삽입
INSERT IGNORE INTO faq_companies (company_code, company_name, faq_url) VALUES
    ('hyundai', '현대자동차', 'https://www.hyundai.com/kr/ko/e/customer/center/faq'),
    ('kia',     '기아자동차', 'https://www.kia.com/kr/customer-service/center/faq');
