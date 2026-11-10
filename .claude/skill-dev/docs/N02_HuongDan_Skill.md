# Hướng dẫn bộ skill student-risk-screening (nhóm N02)

Plugin `edu-analytics` (marketplace `n02-skills`), phiên bản 1.1.0. Nền tảng: Claude Code và claude.ai.

## 1. Bộ skill có thể làm được gì?

- **profile**: Đọc CSV/XLSX, tính SHA-256, mô tả schema; gắn cờ cột số lẫn chuỗi ('94-98'), giá trị dồn đống nghi điền khuyết, số 0 ở cột điểm, hằng số, văn bản tự do; sàng lọc biến rò rỉ (theo tên và AUC đơn biến ≥ 0.80), thuộc tính nhạy cảm; gợi ý luật nhãn nghi vấn và lớp dương; sinh suggested_config.json
- **prepare**: Làm sạch theo cấu hình (trung điểm khoảng, mã khuyết, khoảng hợp lệ), tạo nhãn (ngưỡng hoặc lớp), loại nhãn không quan sát/nghi vấn, khóa giả danh, split phân tầng; chặn cấu hình nếu biến vừa là đặc trưng vừa bị loại; ghi validation và transformation log
- **analyze**: Chẩn đoán trên train (Mann-Whitney/Chi-square/Fisher + Holm, hiệu ứng, logit điều chỉnh); baseline tỷ lệ nền và tín hiệu đơn tốt nhất (chọn trên train); LR và RF trong Pipeline (fit trên train), quy tắc chọn đặt trước; CV phân tầng lặp; test một lần kèm bootstrap CI; rút gọn bộ tín hiệu; permutation importance; công bằng theo nhóm kèm CI; hiệu chỉnh; bảng đánh đổi ngưỡng; độ nhạy; đối chiếu tiêu chí thành công; 4 biểu đồ
- **report**: Báo cáo Markdown có số liệu: dữ liệu, nhật ký biến đổi, chẩn đoán, hiệu năng vs baseline, rút gọn, công bằng, ngưỡng, độ nhạy, tiêu chí, giới hạn/governance
- **run**: Chạy liền prepare → analyze → report với một config đã được rà soát
- **SKILL.md**: Quy trình 6 bước cho Claude: làm rõ quyết định và mốc dự báo, profile, chốt vai trò biến bằng lập luận domain, chạy, diễn giải có trách nhiệm, bàn giao theo milestone

## 2. Mức độ

- Mức 3 (Predictive / Explanatory) theo Đề cương, bao gồm Mức 1-2.
- Bán tự động có kiểm soát: vai trò biến, ngưỡng nhãn, mốc dự báo do Claude/người phân tích chốt bằng lập luận domain.
- Không thuộc phạm vi: KG/RAG/Agent, suy luận nhân quả, tự liên hệ người học.

## 3. Cài đặt

Giải nén n02-skills-marketplace.zip trước, rồi trong Claude Code:

```
/plugin marketplace add ./n02-skills-marketplace
/plugin install edu-analytics@n02-skills
```
Hoặc chép `.claude/skills/student-risk-screening/` vào `.claude/skills/` của dự án hoặc `~/.claude/skills/`.
claude.ai: Customize > Skills > tải `student-risk-screening.zip` (cần bật Code execution).

## 4. Dữ liệu test

| Bộ dữ liệu | Nguồn | Quy mô | Bài toán |
|---|---|---|---|
| SAPE - Students_Academic_Performance_Evaluation_Dataset | Mendeley Data, DOI 10.17632/dc3797vf3t.1, CC BY 4.0 | 1.194 sinh viên CSE (Bangladesh), 31 biến khảo sát | CGPA < 2.75 (sàng lọc đồng thời) |
| UCI Student Performance (môn tiếng Bồ Đào Nha) | UCI ML Repository, DOI 10.24432/C5TG7T, CC BY 4.0 | 649 học sinh THPT, 33 biến | G3 < 10 (trượt môn), mốc đầu năm học |
| UCI Predict Students' Dropout and Academic Success | UCI ML Repository, DOI 10.24432/C5MC89, CC BY 4.0 | 4.424 sinh viên đại học (Bồ Đào Nha), 37 biến | Target = Dropout, mốc cuối học kỳ 1 |

## 5. Kết quả

| Bộ dữ liệu | AUC CV (baseline) | AUC test [CI] | Recall @30% test | Tiêu chí |
|---|---|---|---|---|
| sape | 0.620 (0.615) | 0.614 [0.502, 0.7239] | 48,5% | 3/6 |
| uci_student_por | 0.799 (0.665) | 0.833 [0.7399, 0.9137] | 60,0% | 6/6 |
| uci_dropout | 0.873 (0.810) | 0.876 [0.8488, 0.8986] | 67,6% | 5/6 |

- Bộ test tự động: **28/28 đạt**.
- Đánh giá skill-creator: pass rate có skill 100%, không có skill 83%.

## 6. Nhận xét chung

### Mặt được

- Tổng quát: chạy được trên 3 bộ dữ liệu khác nhau về bậc học, kích thước (649-4.424 dòng), định dạng (xlsx/csv dấu ';'), kiểu nhãn (ngưỡng điểm, nhiều lớp) chỉ bằng file cấu hình.
- Tái lập đúng đồ án: trên SAPE cho AUC CV 0.620 so với 0.619 của Milestone 4, cùng recall 48,5% trên test và cùng kết luận phủ định. Các chênh lệch nhỏ (ví dụ AUC test 0.614 so với 0.611) là do skill chạy pipeline tổng quát của chính nó (mã hóa, impute, làm tròn mặc định), không dùng lại mã của đồ án.
- Tự phát hiện các vấn đề mà nhóm mất nhiều công tìm thủ công: 140 nhãn nghi điền khuyết (3.15/2.68), 5 biến rò rỉ, 7 biến nhạy cảm, ô '94-98', G1/G2 ở bộ UCI.
- Kỷ luật đánh giá: baseline bắt buộc, split trước khi fit, test một lần, CI bootstrap, quy tắc chọn mô hình đặt trước, tiêu chí thành công đặt trước; trung thực với kết quả phủ định.
- Governance tích hợp: biến nhạy cảm bị loại khỏi mô hình nhưng giữ lại để kiểm định; phát hiện chênh lệch công bằng do biến đại diện gián tiếp (tuổi ở bộ Dropout: 21,9 điểm).
- Đánh giá có/không có skill: pass rate 100% so với 83%; khác biệt nằm ở việc không dùng thuộc tính nhạy cảm làm đặc trưng.
- Đóng gói chuẩn: qua validator chính thức của skill-creator, mô tả 190 ký tự (dưới giới hạn 200 của claude.ai), plugin + marketplace cho Claude Code; 28/28 kiểm tra tự động đạt.

### Chưa được

- Không làm mô hình mạnh hơn: hiệu năng tương đương khi Claude tự làm không có skill; giá trị nằm ở quy trình, không ở độ chính xác.
- Gợi ý vai trò biến dựa trên từ khóa và thống kê, cần người rà soát: bộ Dropout bị gắn cờ cả biến học kỳ 1 (hợp lệ ở mốc cuối học kỳ 1); trước khi sửa, lớp dương được đoán sai là 'Enrolled'.
- Chỉ hỗ trợ dữ liệu một bảng, mỗi dòng một người học; chưa có split theo thời gian/nhóm (khóa, trường) - với dữ liệu nhiều khóa nên kiểm định theo khóa như lượt chạy không skill đã làm.
- Báo cáo tự sinh bằng tiếng Việt; báo cáo cho người dùng ngôn ngữ khác do Claude viết lại.
- Chưa hiệu chỉnh xác suất (điểm LR class_weight cân bằng bị thổi phồng) và chưa có giải thích cấp cá nhân (reason code) tự động.
- Tốn token hơn (TB ~87k so với ~64k) và chậm hơn ~98 giây mỗi lần do đọc hướng dẫn và chạy thêm phân tích độ nhạy.
- Cấu hình test Dropout giữ 3 biến vĩ mô cấp khóa (thất nghiệp, lạm phát, GDP); cả hai lượt đánh giá đều loại chúng vì hằng số trong một khóa - nên loại khi triển khai thật.