# Kết quả test skill analytics-capstone-pipeline

Chạy đầy đủ `dspipe.py all` (kiểm định chéo phân tầng 5×10, bootstrap 2.000 lần, seed 42) trên 3 bộ dữ liệu, ngày 13/11/2026, Windows 11, Python 3.12.
Cấu hình trong `testing/capstone/<bộ>/config.json` (cùng đặc trưng, biến loại trừ và cột công bằng như khi test skill student-risk-screening).

| Bộ dữ liệu | Mẫu / ca dương | AUC M1 [KTC 95%] | AUC baseline | Recall @30% | S1 / S2 / S3 / S4 / S5 | Mô hình giữ | Rò rỉ tự phát hiện | Kiểm chứng | Thời gian |
|---|---|---|---|---|---|---|---|---|---|
| SAPE (Mendeley, khảo sát sinh viên CSE Bangladesh) | 1015 / 167 (16.5%) | 0.619 [0.572; 0.666] | 0.603 | 45.2% | Không đạt / Không đạt / Đạt / Đạt / Chưa kết luận | M1 | What was your previous SGPA? | 13/13 đạt | 74 s |
| UCI Student Performance (tiếng Bồ Đào Nha) | 649 / 100 (15.4%) | 0.804 [0.758; 0.850] | 0.683 | 68.2% | Đạt (độ tin cậy cao) / Đạt / Đạt / Không đạt / Chưa kết luận | M2 | không | 13/13 đạt | 61 s |
| UCI Predict Students' Dropout | 4424 / 1421 (32.1%) | 0.865 [0.853; 0.876] | 0.817 | 68.3% | Đạt (độ tin cậy cao) / Đạt / Không đạt / Đạt / Không đạt | M1 | không | 13/13 đạt | 190 s |

S1: AUC ≥ 0,70 và recall ≥ 60% khi gắn cờ 30%. S2: AUC hơn baseline ≥ 0,03 và KTC ghép cặp > 0. S3: rút gọn đặc trưng. S4: hiệu chuẩn. S5: công bằng (chỉ kết luận khi KTC hẹp).
