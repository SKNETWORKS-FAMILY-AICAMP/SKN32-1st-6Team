-- repairshopdb: 정비소 (Streamlit + repairshop_data.py)
CREATE DATABASE IF NOT EXISTS repairshopdb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE repairshopdb;

DROP TABLE IF EXISTS repairshop;

CREATE TABLE repairshop (
    자동차정비업체명      VARCHAR(150) NOT NULL,
    브랜드                VARCHAR(50),
    시도                  VARCHAR(50),
    시군구                VARCHAR(255),
    소재지도로명주소      VARCHAR(255),
    자동차정비업체종류    INT
) CHARACTER SET utf8mb4;