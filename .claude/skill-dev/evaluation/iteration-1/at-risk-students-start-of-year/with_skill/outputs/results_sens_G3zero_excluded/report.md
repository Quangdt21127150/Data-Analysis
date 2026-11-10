# Báo cáo phân tích sàng lọc người học: Start-of-year screening: risk of failing Portuguese (G3 < 10)

> Sinh tự động bởi skill education-data-analytics (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `student-por.csv` (SHA-256 `a7594a11d7771c0e…`), 649 dòng.
- Nhãn dương: **G3 < 10**; tập có nhãn 634 dòng, 85 ca dương (tỷ lệ nền 13.4%).
- Trạng thái nhãn: {'observed': 634, 'no_target': 15}. Train 507 (68 dương) / test 127 (17 dương), phân tầng, seed 2026.
- 14 đặc trưng hợp lệ; biến bị loại: leakage: G1, G2, absences, schoolsup; sensitive: sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, guardian, romantic, Dalc, Walc, health; other: -.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| label | {"column": "G3", "type": "threshold_below", "threshold": 10, "zero_is_missing": true, "sensitivity_thresholds": [8, 12]} | 634 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| failures | Mann-Whitney U | rank-biserial r = 0.407 | 1.38e-16 | Có |
| higher | Chi-square | Cramér's V = 0.272 | 1.11e-08 | Có |
| school | Chi-square | Cramér's V = 0.25 | 2.28e-07 | Có |
| studytime | Mann-Whitney U | rank-biserial r = -0.241 | 0.0064 | Có |
| reason | Chi-square | Cramér's V = 0.176 | 0.0127 | Có |
| internet | Chi-square | Cramér's V = 0.103 | 0.189 | Không |
| activities | Chi-square | Cramér's V = 0.099 | 0.209 | Không |
| freetime | Mann-Whitney U | rank-biserial r = 0.151 | 0.249 | Không |
| paid | Fisher exact | Cramér's V = 0.082 | 0.492 | Không |
| goout | Mann-Whitney U | rank-biserial r = 0.113 | 0.604 | Không |
| traveltime | Mann-Whitney U | rank-biserial r = 0.08 | 0.927 | Không |
| famrel | Mann-Whitney U | rank-biserial r = -0.003 | 1 | Không |
| famsup | Chi-square | Cramér's V = 0.007 | 1 | Không |
| nursery | Chi-square | Cramér's V = 0.036 | 1 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.2597; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- failures: OR 1.872 (CI 95% 1.483-2.363)
- school_MS: OR 3.427 (CI 95% 1.781-6.596)
- higher_no: OR 2.485 (CI 95% 1.163-5.309)
- activities_yes: OR 0.518 (CI 95% 0.269-0.997)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **failures**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.490 ± 0.000 | 0.132 | 19.4% | - | - |
| B1_best_single | 0.668 ± 0.009 | 0.327 | 55.3% | 0.648 [0.527; 0.771] | 35.3% |
| LR | 0.799 ± 0.009 | 0.402 | 70.4% | 0.759 [0.605; 0.887] | 70.6% |
| RF | 0.817 ± 0.010 | 0.389 | 69.6% | 0.819 [0.667; 0.941] | 76.5% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.775 | 70.6% |

Hiệu chỉnh: xác suất TB 0.3523 so với tỷ lệ nền 0.1341 (Brier 0.1695 vs hằng số 0.1161). Điểm chỉ nên dùng để xếp hạng.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.7986.
- Quy tắc 95%: 3 biến (failures, freetime, school).
- AUC CV cao nhất: 0.8258 với 8 biến (studytime, failures, freetime, school, reason, paid, activities, higher).
- Permutation importance (top 5): failures (0.0795), school (0.0581), freetime (0.0234), higher (0.0181), reason (0.0113).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- sex (train_oof): F: recall 79.4%, gắn cờ 30.2% (n=295, dương=34); M: recall 64.7%, gắn cờ 29.7% (n=212, dương=34) → chênh lệch recall 14.7% (CI [0.009, 0.355])
- sex (test): F: recall 88.9%, gắn cờ 29.6% (n=81, dương=9); M: recall 50.0%, gắn cờ 23.9% (n=46, dương=8) → chênh lệch recall 38.9% (CI [0.024, 0.8])
- address (train_oof): U: recall 69.0%, gắn cờ 23.1% (n=360, dương=42); R: recall 76.9%, gắn cờ 46.9% (n=147, dương=26) → chênh lệch recall 7.9% (CI [0.004, 0.3])
- address (test): U: recall 66.7%, gắn cờ 17.2% (n=87, dương=9); R: recall 75.0%, gắn cờ 50.0% (n=40, dương=8) → chênh lệch recall 8.3% (CI [0.0, 0.564])
- age (train_oof): <= 17: recall 63.8%, gắn cờ 26.2% (n=367, dương=47); > 17: recall 90.5%, gắn cờ 40.0% (n=140, dương=21) → chênh lệch recall 26.7% (CI [0.072, 0.446])
- age (test): 17: recall 50.0%, gắn cờ 26.3% (n=38, dương=6); 18: recall 80.0%, gắn cờ 28.0% (n=25, dương=5) → chênh lệch recall 30.0% (CI [0.0, 0.846])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 17.6% | 46.2% | 3.53 | 0.0% | 0.0% |
| 10% | 29.4% | 39.2% | 2.94 | 17.6% | 33.3% |
| 15% | 44.1% | 39.0% | 2.94 | 41.2% | 38.9% |
| 20% | 55.9% | 37.2% | 2.79 | 58.8% | 41.7% |
| 25% | 67.7% | 36.2% | 2.71 | 64.7% | 36.7% |
| 30% | 72.1% | 32.0% | 2.4 | 70.6% | 34.3% |
| 35% | 73.5% | 28.1% | 2.1 | 76.5% | 29.5% |
| 40% | 77.9% | 26.1% | 1.95 | 76.5% | 26.0% |
| 50% | 83.8% | 22.4% | 1.68 | 82.3% | 21.5% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 22%.

## 7. Độ nhạy

- threshold_8: AUC CV 0.838 ± 0.037; recall@capacity 73.3%; ca dương 12
- threshold_12: AUC CV 0.791 ± 0.004; recall@capacity 53.9%; ca dương 230

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.799; test 0.759 | Đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 70.4%; test 70.6% | Đạt |
| Vượt baseline ≥ 0.02 AUC | 0.799 vs 0.668 | Đạt |
| Rút gọn ≥ 33% số biến | 78.6% | Đạt |
| Chênh lệch recall ≤ 10% | [0.147, 0.079, 0.267] | Không đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.