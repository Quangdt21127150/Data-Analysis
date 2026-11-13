# Hướng dẫn tệp cấu hình `config.json`

Tệp cấu hình là hợp đồng giữa người dùng và quy trình: mọi lựa chọn có ảnh hưởng đến kết luận đều nằm ở đây, nên báo cáo luôn truy được về cấu hình. Giá trị bị bỏ trống sẽ lấy mặc định trong `DEFAULT_CFG` của `scripts/dspipe.py`. Mẫu đầy đủ: `assets/config_example_sape.json`.

## Mục lục
1. Dữ liệu và nhãn
2. Đặc trưng, loại trừ, rò rỉ
3. Nhóm đặc trưng, baseline, công bằng
4. Tiêu chí thành công
5. Kiểm định chéo
6. Bối cảnh và nội dung báo cáo

## 1. Dữ liệu và nhãn
| Trường | Ý nghĩa |
|---|---|
| `data_path`, `sheet`, `id_col` | Đường dẫn tương đối so với thư mục chứa cấu hình; `sheet` chỉ dùng cho Excel; `id_col` để kiểm tra trùng lặp |
| `target.column` | Cột nhãn |
| `target.type` | `threshold` (biến liên tục + ngưỡng) hoặc `binary` (nhãn có sẵn) |
| `target.positive_if`, `target.threshold` | Chỉ với `threshold`. Ví dụ `"<"` và `2.75` nghĩa là ca dương khi giá trị nhỏ hơn 2,75 |
| `target.positive_values` | Chỉ với `binary`. Danh sách giá trị tính là ca dương, ví dụ `[0]` hoặc `["M"]` |
| `target.missing_codes` | Giá trị đại diện cho thiếu dữ liệu (ví dụ `0` ở cột điểm chưa có). Dòng này bị loại khỏi mẫu có nhãn, không điền khuyết nhãn |
| `target.positive_name` | Tên nhóm dương dùng trong văn bản, ví dụ "nhóm cần hỗ trợ" |

Ngưỡng nhãn là quyết định nghiệp vụ, không phải quyết định thống kê. Nếu chưa được chuyên gia xác nhận, ghi "nhãn tạm thời" vào `context.notes`.

## 2. Đặc trưng, loại trừ, rò rỉ
- `features`: danh sách tường minh các cột đầu vào. Nên khai báo; nếu để `null` thì dùng mọi cột trừ nhãn, id và cột bị loại.
- `exclude.leakage`: cột chắc chắn không có tại thời điểm dự báo (điểm kỳ sau, trạng thái cuối khóa, biến suy ra từ nhãn).
- `exclude.sensitive_for_model`: thuộc tính nhạy cảm không đưa vào mô hình nhưng vẫn dùng để đánh giá công bằng.
- `auto_exclude_leakage_auc` (mặc định 0,85): cột bị tự động loại tạm thời chỉ khi vừa có AUC đơn biến từ ngưỡng này vừa có tên gợi ý hệ quả của nhãn (prev, gpa, grade, status, result...). Cột mạnh nhưng tên vô hại chỉ bị cảnh báo trong `strong_features_unconfirmed`.
- `keep_despite_leakage_flag`: cột người dùng đã xác nhận hợp lệ về thời điểm thu thập dù bị gắn cờ.

Cách hỏi người dùng khi cột bị gắn cờ: "Cột X có được ghi nhận trước thời điểm cần dự báo không?" Nếu có, đưa vào `keep_despite_leakage_flag`; nếu không, đưa vào `exclude.leakage`.

## 3. Nhóm đặc trưng, baseline, công bằng
- `groups`: `{"Tên nhóm": [cột, ...]}` để ablation (bỏ từng nhóm và đo mức giảm AUC). Nhóm nên có ý nghĩa nghiệp vụ, 3 đến 6 nhóm.
- `baseline_feature`: đặc trưng đơn dùng làm baseline. Chọn đặc trưng mà một cố vấn thực tế sẽ dùng bằng trực giác. Nếu để `null`, hệ thống chọn đặc trưng đơn tốt nhất nên baseline lạc quan và báo cáo ghi cảnh báo.
- `fairness_cols`: thuộc tính nhóm (giới tính, nơi ở, dân tộc...) để so sánh recall. Có thể không nằm trong `features`.
- `flag_rates`: tỷ lệ gắn cờ cần xét, ví dụ `[0.15, 0.30]`; phải chứa `criteria.recall_rate`.

## 4. Tiêu chí thành công (`criteria`)
| Trường | Mặc định | Tiêu chí |
|---|---|---|
| `auc`, `recall`, `recall_rate` | 0,70; 0,60; 0,30 | S1: AUC và recall tại tỷ lệ gắn cờ `recall_rate` |
| `delta_auc` | 0,03 | S2: AUC mô hình hơn baseline tối thiểu, và cận dưới KTC ghép cặp lớn hơn 0 |
| `max_items`, `ablation_tolerance` | tự tính 2/3, 0,02 | S3: số đặc trưng gốc giữ lại tối đa và mức giảm AUC cho phép |
| `calib_slope`, (Brier thấp hơn tỷ lệ nền) | [0,8; 1,2] | S4 |
| `fair_gap`, `fair_ci_width` | 0,10; 0,20 | S5: chênh lệch recall tối đa và độ rộng KTC tối đa để kết luận |
| `switch_delta` | 0,02 | Mô hình cây phải hơn M1 ít nhất mức này (và KTC ghép cặp > 0) mới thay M1 |

Ngưỡng phụ thuộc lĩnh vực: sàng lọc giáo dục có thể chấp nhận AUC 0,70; chẩn đoán y khoa thường đòi 0,95. Hãy hỏi người dùng nếu không chắc, và ghi lý do vào báo cáo. Đổi tiêu chí sau khi đã thấy kết quả là vi phạm quy tắc đăng ký trước.

## 5. Kiểm định chéo (`cv`)
`splits` 5, `repeats` 10, `seed` 42, `n_boot` 2000, `n_jobs` -1. Giữ nguyên trừ khi cỡ mẫu rất nhỏ (dưới 100 ca dương: giảm `splits` xuống 3 và ghi chú) hoặc rất lớn (giảm `repeats` để tiết kiệm thời gian).

## 6. Bối cảnh và nội dung báo cáo
- `context`: `data_source`, `self_reported`, `cross_sectional`, `single_site` (true, false hoặc null), `notes` (danh sách câu). Đặt `false` chỉ khi chắc chắn; mặc định báo cáo coi các hạn chế này là có.
- `stakeholders_source`: `"assumed"` nếu vai trò và nỗi đau do nhóm giả định, `"interviewed"` nếu có phỏng vấn thật. Báo cáo tự ghi chú tương ứng. Không bao giờ đánh dấu `interviewed` khi chưa phỏng vấn.
- `stakeholders`: `[{"role","pain","decision"}]`; `analysis_questions`: `[{"id","level","question"}]` với level là Descriptive, Diagnostic, Predictive hoặc Prescriptive.
- `team`: `name`, `members`, `advisor`, `course`; `project_name` hiện trên bìa và chân trang.
- `out_dir`: thư mục đầu ra; dùng tên khác nhau cho chạy nhanh và chạy đầy đủ để khỏi lẫn.
