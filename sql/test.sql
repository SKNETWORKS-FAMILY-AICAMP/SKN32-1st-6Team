CREATE DATABASE car_faq_db
DEFAULT CHARACTER SET utf8mb4;

USE car_faq_db;

CREATE TABLE hyundai_faq (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100),
    question TEXT,
    answer TEXT
);

SHOW DATABASES;

SELECT * FROM hyundai_faq;

drop table hyundai_faq;

ALTER TABLE hyundai_faq
ADD UNIQUE(question(255));

SELECT LENGTH(answer)
FROM hyundai_faq;