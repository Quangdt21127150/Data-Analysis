# Báo cáo phân tích sàng lọc người học: UCI Student Performance (tiếng Bồ Đào Nha) - sàng lọc đầu năm học sinh có nguy cơ trượt môn (G3 < 10)

> Sinh tự động bởi skill student-risk-screening (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `uci_student_por.csv` (SHA-256 `a7594a11d7771c0e…`), 649 dòng.
- Nhãn dương: **G3 < 10**; tập có nhãn 649 dòng, 100 ca dương (tỷ lệ nền 15.4%).
- Trạng thái nhãn: {'observed': 649}. Train 519 (80 dương) / test 130 (20 dương), phân tầng, seed 2026.
- 14 đặc trưng hợp lệ; biến bị loại: leakage: G1, G2, absences, schoolsup; sensitive: sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, guardian, romantic, Dalc, Walc, health; other: -.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| label | {"column": "G3", "type": "threshold_below", "threshold": 10, "zero_is_missing": false, "sensitivity_thresholds": [8, 12]} | 649 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| failures | Mann-Whitney U | rank-biserial r = 0.378 | 4.64e-16 | Có |
| school | Chi-square | Cramér's V = 0.294 | 2.61e-10 | Có |
| higher | Chi-square | Cramér's V = 0.286 | 8.14e-10 | Có |
| studytime | Mann-Whitney U | rank-biserial r = -0.249 | 0.00143 | Có |
| reason | Chi-square | Cramér's V = 0.176 | 0.0109 | Có |
| internet | Chi-square | Cramér's V = 0.097 | 0.241 | Không |
| paid | Fisher exact | Cramér's V = 0.1 | 0.272 | Không |
| activities | Chi-square | Cramér's V = 0.081 | 0.449 | Không |
| freetime | Mann-Whitney U | rank-biserial r = 0.1 | 0.818 | Không |
| goout | Mann-Whitney U | rank-biserial r = 0.102 | 0.818 | Không |
| traveltime | Mann-Whitney U | rank-biserial r = 0.075 | 0.911 | Không |
| famrel | Mann-Whitney U | rank-biserial r = -0.056 | 1 | Không |
| famsup | Chi-square | Cramér's V = 0.035 | 1 | Không |
| nursery | Chi-square | Cramér's V = 0.017 | 1 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.2575; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- failures: OR 1.785 (CI 95% 1.423-2.239)
- school_MS: OR 4.739 (CI 95% 2.541-8.841)
- higher_no: OR 2.764 (CI 95% 1.346-5.676)
- paid_yes: OR 3.096 (CI 95% 1.177-8.147)
- studytime: OR 0.714 (CI 95% 0.513-0.993)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **failures**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.499 ± 0.000 | 0.154 | 17.8% | - | - |
| B1_best_single | 0.665 ± 0.007 | 0.327 | 52.5% | 0.750 [0.629; 0.864] | 55.0% |
| LR | 0.799 ± 0.012 | 0.436 | 69.2% | 0.833 [0.740; 0.914] | 60.0% |
| RF | 0.816 ± 0.008 | 0.442 | 69.4% | 0.860 [0.764; 0.940] | 65.0% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.864 | 75.0% |

Hiệu chỉnh: xác suất TB 0.3773 so với tỷ lệ nền 0.1541 (Brier 0.1776 vs hằng số 0.1304). Điểm chỉ nên dùng để xếp hạng.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.7988.
- Quy tắc 95%: 2 biến (failures, school).
- AUC CV cao nhất: 0.8164 với 7 biến (traveltime, studytime, failures, freetime, school, paid, higher).
- Permutation importance (top 5): school (0.103), failures (0.0742), higher (0.0243), studytime (0.0137), paid (0.0075).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- sex (train_oof): F: recall 72.7%, gắn cờ 30.2% (n=305, dương=44); M: recall 63.9%, gắn cờ 29.9% (n=214, dương=36) → chênh lệch recall 8.8% (CI [0.008, 0.307])
- sex (test): F: recall 66.7%, gắn cờ 23.1% (n=78, dương=6); M: recall 57.1%, gắn cờ 26.9% (n=52, dương=14) → chênh lệch recall 9.6% (CI [0.005, 0.578])
- address (train_oof): U: recall 65.9%, gắn cờ 22.9% (n=362, dương=44); R: recall 72.2%, gắn cờ 46.5% (n=157, dương=36) → chênh lệch recall 6.3% (CI [0.004, 0.292])
- address (test): U: recall 66.7%, gắn cờ 18.9% (n=90, dương=12); R: recall 50.0%, gắn cờ 37.5% (n=40, dương=8) → chênh lệch recall 16.7% (CI [0.0, 0.604])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 17.5% | 53.8% | 3.5 | 25.0% | 100.0% |
| 10% | 32.5% | 50.0% | 3.25 | 35.0% | 63.6% |
| 15% | 42.5% | 43.6% | 2.83 | 45.0% | 50.0% |
| 20% | 52.5% | 40.4% | 2.62 | 50.0% | 43.5% |
| 25% | 62.5% | 38.5% | 2.5 | 50.0% | 38.5% |
| 30% | 68.8% | 35.3% | 2.29 | 60.0% | 37.5% |
| 35% | 73.8% | 32.4% | 2.11 | 70.0% | 35.0% |
| 40% | 78.8% | 30.3% | 1.97 | 75.0% | 30.0% |
| 50% | 86.2% | 26.5% | 1.73 | 95.0% | 30.2% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 25%.

## 7. Độ nhạy

- threshold_8: AUC CV 0.770 ± 0.019; recall@capacity 78.0%; ca dương 20
- threshold_12: AUC CV 0.788 ± 0.005; recall@capacity 53.7%; ca dương 242

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.799; test 0.833 | Đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 69.2%; test 60.0% | Đạt |
| Vượt baseline ≥ 0.02 AUC | 0.799 vs 0.665 | Đạt |
| Rút gọn ≥ 33% số biến | 85.7% | Đạt |
| Chênh lệch recall ≤ 10% | [0.088, 0.063] | Đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.