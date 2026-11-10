# Khung phương pháp (Data Analytics Methodology - Milestone 1-5)

| Giai đoạn | Câu hỏi | Sản phẩm chính | Công cụ trong skill |
|---|---|---|---|
| M1 Problem → Approach | Quyết định nào cần hỗ trợ? | Stakeholder, Business Goal, SMART Goal, 1 Primary + ≤ 2 Secondary KPI, AQ ladder 4 mức, traceability | Bước 1 (hỏi người dùng) |
| M2 Requirements → Collection | Cần dữ liệu gì, dataset nào đáp ứng? | AQ-Data Requirement Matrix, search log ≥ 3 dataset, selection matrix, provenance (SHA-256, license) | `profile` (SHA-256, schema) |
| M3 Understanding → Preparation | Dữ liệu có phù hợp và sẵn sàng? | DQ Issue Log, AQ-Data Fit (GREEN/YELLOW/RED), Preparation Decision Matrix, pipeline, lineage, readiness | `profile`, `prepare` |
| M4 Modeling → Evaluation | Phương pháp nào, đánh giá ra sao? | Modeling Brief, Candidate Solution Matrix (baseline + 1-2 ứng viên), Evaluation Design Card, risk register, prototype | `analyze` |
| M5 Final Integration | Câu chuyện cuối có bảo vệ được? | Final Traceability Matrix, AQ Revision Log, AQ-by-AQ findings, limitations | `report` + phần viết của Claude |

## Analytical Question ladder
- Descriptive: metric, population, thời gian, phân khúc rõ ràng.
- Diagnostic: yếu tố so sánh rõ; ngôn ngữ liên hệ.
- Predictive: target, đơn vị, mốc dự báo, dữ liệu có sẵn tại mốc; nếu dữ liệu cắt ngang → "sàng lọc đồng thời".
- Prescriptive: decision, action alternatives, objective, constraints; nếu không có dữ liệu can thiệp → hạ claim, giữ làm yêu cầu tương lai hoặc đề xuất thí nghiệm.

## Ánh xạ AQ → technical task (không ép mọi câu hỏi thành ML)
| Loại câu hỏi | Task | Phương pháp mặc định trong skill |
|---|---|---|
| Mô tả | Aggregation | Tỷ lệ, phân bố, CI |
| Chẩn đoán | Group comparison / association | Mann-Whitney U, Chi-square/Fisher, Holm, logit điều chỉnh |
| Sàng lọc | Binary classification | B0, B1 vs LR (primary), RF |
| Tín hiệu tối thiểu | Feature subset | Loại ngược theo AUC CV, permutation importance |
| Công bằng | Subgroup analysis | Recall/precision/tỷ lệ gắn cờ theo nhóm + bootstrap CI |
| Điểm cắt | Threshold trade-off | Bảng recall-precision-lift theo tỷ lệ gắn cờ |

## Final Traceability Matrix (mỗi hàng một AQ)
AQ-ID | Business/SMART + KPI | Final AQ | Analytics Level | Required Data/Unit | Actual Dataset & Variables | Preparation/Feature Logic |
Method + Rationale | Evaluation/Result | Decision Supported | Final Status (Answered/Partial/Deferred/Dropped).
Ô không có bằng chứng ghi GAP/N.A., không điền bằng giả định.

## Tiêu chí thành công mặc định (đặt trước khi chạy)
AUC ≥ 0.70; recall ≥ 60% khi gắn cờ ≤ 30%; vượt baseline ≥ 0.02 AUC (mặc định cố định trong mã, chốt trước khi chạy; muốn đổi phải sửa trước lần chạy đầu và ghi lại); rút gọn ≥ 1/3 số biến với AUC ≥ 95% mô hình đầy đủ;
chênh lệch recall giữa nhóm ≤ 10 điểm %; biến bị cấm trong mô hình = 0. Điều chỉnh theo bối cảnh nhưng không đổi sau khi thấy kết quả.
