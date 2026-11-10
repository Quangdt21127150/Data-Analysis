---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Phòng công tác sinh viên trường mình muốn có danh sách sinh viên có nguy cơ bỏ học để cố vấn gặp sớm. Thời điểm dùng danh sách là ngay sau khi có kết quả học kỳ 1 năm nhất, và cố vấn chỉ gặp được tối đa khoảng 30% sinh viên. File students_dropout.csv là dữ liệu các khóa trước (cột Target: Dropout / Enrolled / Graduate). Bạn phân tích giúp xem có xây được công cụ sàng lọc đáng tin không, nó bắt được bao nhiêu phần trăm sinh viên bỏ học, có công bằng không, và viết cho mình một báo cáo ngắn (report.md) kèm khuyến nghị.

Input files: students_dropout.csv
