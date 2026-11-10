# Báo cáo phân tích sàng lọc người học: SAPE - sàng lọc sinh viên CGPA < 2.75 (tái lập Milestone 3-4 của N02)

> Sinh tự động bởi skill student-risk-screening (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `sape_students_performance.xlsx` (SHA-256 `04ebaf9f3a047afe…`), 1194 dòng.
- Nhãn dương: **What is your current CGPA? < 2.75**; tập có nhãn 1015 dòng, 167 ca dương (tỷ lệ nền 16.4%).
- Trạng thái nhãn: {'observed': 1015, 'suspect': 140, 'no_target': 39}. Train 812 (134 dương) / test 203 (33 dương), phân tầng, seed 2026.
- 11 đặc trưng hợp lệ; biến bị loại: leakage: What was your previous SGPA?, Did you ever fall in probation?, Did you ever got suspension?, Do you have meritorious scholarship ?, Do you attend in teacher consultancy for any kind of academical problems?; sensitive: Gender, Age, What is your relationship status?, With whom you are living with?, Do you have any health issues?, Do you have any physical disabilities?, What is your monthly family income?; other: Program, What are the skills do you have ?, What is you interested area?, Do you use smart phone?, How many Credit did you have completed?, University Admission year, H.S.C passing year.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| type | Average attendance on class: giá trị dạng khoảng -> trung điểm | 1 |
| missing | Average attendance on class: mã [0] -> NaN | 1 |
| invalid | How many hour do you spent daily in social media?: ngoài [0, 16] -> NaN | 1 |
| label | {"column": "What is your current CGPA?", "type": "threshold_below", "threshold": 2.75, "zero_is_missing": true, "sensitivity_thresholds": [2.5, 3.0]} | 1015 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| Average attendance on class | Mann-Whitney U | rank-biserial r = -0.237 | 0.000117 | Có |
| Status of your English language proficiency | Chi-square | Cramér's V = 0.119 | 0.0322 | Có |
| How many hour do you study daily? | Mann-Whitney U | rank-biserial r = -0.057 | 1 | Không |
| How many times do you seat for study in a day? | Mann-Whitney U | rank-biserial r = 0.008 | 1 | Không |
| How many hour do you spent daily in social media? | Mann-Whitney U | rank-biserial r = 0.075 | 1 | Không |
| How many hour do you spent daily on your skill development? | Mann-Whitney U | rank-biserial r = -0.028 | 1 | Không |
| Current Semester | Mann-Whitney U | rank-biserial r = 0.061 | 1 | Không |
| What is your preferable learning mode? | Chi-square | Cramér's V = 0.029 | 1 | Không |
| Do you have personal Computer? | Chi-square | Cramér's V = 0.037 | 1 | Không |
| Do you use University transportation? | Chi-square | Cramér's V = 0.054 | 1 | Không |
| Are you engaged with any co-curriculum activities? | Chi-square | Cramér's V = 0.054 | 1 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.0645; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- Average attendance on class: OR 0.661 (CI 95% 0.559-0.781)
- Status of your English language proficiency_Basic: OR 2.327 (CI 95% 1.457-3.717)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **Average attendance on class**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.496 ± 0.000 | 0.164 | 28.9% | - | - |
| B1_best_single | 0.615 ± 0.005 | 0.269 | 45.7% | 0.557 [0.434; 0.673] | 33.3% |
| LR | 0.620 ± 0.009 | 0.262 | 44.4% | 0.614 [0.502; 0.724] | 48.5% |
| RF | 0.620 ± 0.010 | 0.234 | 42.7% | 0.623 [0.516; 0.719] | 42.4% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.621 | 45.5% |

Hiệu chỉnh: xác suất TB 0.4658 so với tỷ lệ nền 0.165 (Brier 0.2331 vs hằng số 0.1378). Điểm chỉ nên dùng để xếp hạng.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.6198.
- Quy tắc 95%: 1 biến (Average attendance on class).
- AUC CV cao nhất: 0.6468 với 4 biến (Average attendance on class, Do you use University transportation?, Status of your English language proficiency, Are you engaged with any co-curriculum activities?).
- Permutation importance (top 5): Average attendance on class (0.0773), Status of your English language proficiency (0.0648), Are you engaged with any co-curriculum activities? (0.0101), Do you use University transportation? (0.0089), Do you have personal Computer? (0.0057).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- Gender (train_oof): Male: recall 42.1%, gắn cờ 30.1% (n=449, dương=76); Female: recall 44.8%, gắn cờ 30.0% (n=363, dương=58) → chênh lệch recall 2.7% (CI [0.003, 0.204])
- Gender (test): Male: recall 55.0%, gắn cờ 31.9% (n=113, dương=20); Female: recall 38.5%, gắn cờ 31.1% (n=90, dương=13) → chênh lệch recall 16.5% (CI [0.013, 0.524])
- With whom you are living with? (train_oof): Family: recall 44.3%, gắn cờ 28.6% (n=433, dương=61); Bachelor: recall 42.5%, gắn cờ 31.7% (n=379, dương=73) → chênh lệch recall 1.8% (CI [0.004, 0.219])
- With whom you are living with? (test): Family: recall 40.0%, gắn cờ 25.2% (n=107, dương=10); Bachelor: recall 52.2%, gắn cờ 38.5% (n=96, dương=23) → chênh lệch recall 12.2% (CI [0.004, 0.48])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 12.7% | 41.5% | 2.54 | 9.1% | 25.0% |
| 10% | 22.4% | 36.6% | 2.24 | 21.2% | 31.8% |
| 15% | 25.4% | 27.9% | 1.69 | 24.2% | 28.6% |
| 20% | 31.3% | 25.8% | 1.57 | 33.3% | 28.2% |
| 25% | 38.8% | 25.6% | 1.55 | 42.4% | 26.9% |
| 30% | 43.3% | 23.8% | 1.44 | 48.5% | 25.0% |
| 35% | 46.3% | 21.8% | 1.32 | 48.5% | 21.9% |
| 40% | 50.7% | 20.9% | 1.27 | 57.6% | 23.2% |
| 50% | 60.5% | 20.0% | 1.21 | 60.6% | 21.3% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 50%.

## 7. Độ nhạy

- threshold_2.5: AUC CV 0.641 ± 0.012; recall@capacity 53.0%; ca dương 43
- threshold_3.0: AUC CV 0.658 ± 0.004; recall@capacity 45.4%; ca dương 251
- include_suspect_labels: AUC CV 0.628 ± 0.006; recall@capacity 46.0%; n = 924

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.620; test 0.614 | Không đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 44.4%; test 48.5% | Không đạt |
| Vượt baseline ≥ 0.02 AUC | 0.620 vs 0.615 | Không đạt |
| Rút gọn ≥ 33% số biến | 90.9% | Đạt |
| Chênh lệch recall ≤ 10% | [0.027, 0.018] | Đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.