# Hướng dẫn bộ skill của nhóm N02

Plugin `edu-analytics` phiên bản 1.2.0 (marketplace `n02-skills`), gồm 2 skill. Nền tảng: Claude Code và claude.ai.

## GIỚI THIỆU BỘ SKILL

Bộ skill đóng gói quy trình phân tích của đồ án thành công cụ dùng lại được trên Claude. Plugin edu-analytics (phiên bản 1.2.0, marketplace n02-skills) gồm hai skill bổ sung cho nhau: một skill chuyên về sàng lọc người học cần hỗ trợ có trách nhiệm, một skill chạy trọn quy trình đồ án từ dữ liệu đến báo cáo Word và dàn ý slide.

| Skill | Mục đích | Đầu ra chính | Nên dùng khi |
|---|---|---|---|
| student-risk-screening | Sàng lọc người học cần hỗ trợ từ dữ liệu điểm, LMS, khảo sát; kiểm soát rò rỉ, baseline, công bằng, đánh đổi ngưỡng | Báo cáo Markdown có số liệu, 4 biểu đồ, cấu hình đã rà soát | Cần một phân tích sàng lọc chặt chẽ, có tập kiểm tra độc lập |
| analytics-capstone-pipeline | Chạy trọn quy trình đồ án khoa học dữ liệu trên bảng dữ liệu bất kỳ có biến mục tiêu, có đăng ký trước tiêu chí | Báo cáo Word có mục lục và trích dẫn, tài liệu giải thích mã, kịch bản thuyết trình, dàn ý slide, 9 hình | Cần sản phẩm đồ án trọn gói theo milestone 1-5 |

*Bảng 1. Hai skill trong plugin edu-analytics*


## BỘ SKILL CÓ THỂ LÀM ĐƯỢC GÌ?


### Skill student-risk-screening

| Thành phần | Chức năng |
|---|---|
| profile | Đọc CSV/XLSX, tính SHA-256, mô tả schema; gắn cờ cột số lẫn chuỗi, giá trị dồn đống nghi điền khuyết, số 0 ở cột điểm; sàng lọc biến rò rỉ và thuộc tính nhạy cảm; sinh cấu hình gợi ý |
| prepare | Làm sạch theo cấu hình, tạo nhãn, loại nhãn không quan sát được, khóa giả danh, chia train/test phân tầng; ghi validation và transformation log |
| analyze | Chẩn đoán trên train (kiểm định có hiệu chỉnh Holm, logit điều chỉnh); baseline; LR và RF trong Pipeline với quy tắc chọn đặt trước; CV lặp; test một lần kèm bootstrap CI; rút gọn tín hiệu; công bằng; đánh đổi ngưỡng; độ nhạy |
| report | Báo cáo Markdown có số liệu và phần giới hạn, governance |
| run | Chạy liền prepare, analyze, report với một cấu hình đã rà soát |
| SKILL.md | Quy trình 6 bước cho Claude: làm rõ quyết định và mốc dự báo, profile, chốt vai trò biến bằng lập luận domain, chạy, diễn giải có trách nhiệm, bàn giao theo milestone |

*Bảng 2. Chức năng của student-risk-screening*


### Skill analytics-capstone-pipeline

| Bước | Nội dung | Lệnh / tệp |
|---|---|---|
| 1. Khởi tạo cấu hình | Đọc dữ liệu, đếm dòng hợp lệ và tỷ lệ ca dương, gợi ý cột rò rỉ và vấn đề chất lượng | dspipe.py init |
| 2. Xác nhận cấu hình | Con người chốt đặc trưng, nhóm đặc trưng, cột công bằng, baseline, cột rò rỉ, tiêu chí thành công | config.json |
| 3. Chạy thử nhanh | Phát hiện lỗi cấu hình trong vài chục giây; số liệu không dùng để báo cáo | dspipe.py all --fast |
| 4. Chạy đầy đủ | Kiểm toán, chuẩn bị, đăng ký trước tiêu chí S1-S5 (băm SHA-256), chẩn đoán, mô hình (LR L2, LR L1, Random Forest, Gradient Boosting) kiểm định chéo 5×10, bootstrap 2.000 lần, hiệu chuẩn, rút gọn, ablation, công bằng, mẫu độ nhạy, 13 phép kiểm chứng | dspipe.py all |
| 5. Đọc kết quả | results.json, audit.json, bảng trong tables/, 9 hình trong figures/ | references/methodology.md |
| 6. Dựng sản phẩm | Báo cáo Word (không chứa mã, có mục lục, trích dẫn đánh số), tài liệu giải thích mã, kịch bản thuyết trình, dàn ý slide | make_report.py |
| 7. Kiểm tra sản phẩm | Số trang mục lục, không có mã trong báo cáo, không có dấu gạch ngang dài, số liệu khớp bảng, trích dẫn khớp danh mục | make_report.py tự quét |
| 8. Giao kết quả | Nêu số tiêu chí đạt, mô hình giữ lại, giả định và hạn chế | SKILL.md |
| Mở rộng | SEM/CFA (semopy), SHAP và LIME cho mô hình cây, so sánh công cụ trực quan hóa, sổ tay Colab tự chứa | scripts/extensions/, build_notebook.py |

*Bảng 3. Quy trình tám bước của analytics-capstone-pipeline*


## MỨC ĐỘ

| Khía cạnh | student-risk-screening | analytics-capstone-pipeline |
|---|---|---|
| Theo Đề cương | Mức 3 - Predictive / Explanatory (bao gồm Mức 1-2) | Mức 3 - Predictive / Explanatory, thêm sản phẩm trình bày (báo cáo, slide) phục vụ Giai đoạn 9-10 |
| Mức tự động hóa | Bán tự động: vai trò biến, ngưỡng nhãn, mốc dự báo do người phân tích chốt | Bán tự động: bước 2 (xác nhận cấu hình) bắt buộc có con người; các bước còn lại tự động |
| Thiết kế đánh giá | Tập kiểm tra độc lập dùng một lần + CV lặp trên train | Kiểm định chéo lặp 5×10 trên toàn mẫu + đăng ký trước tiêu chí có mã băm |
| Không thuộc phạm vi | KG/RAG/Agent, suy luận nhân quả, tự liên hệ người học | Như bên trái; phần mở rộng SEM/SHAP chỉ chạy khi có thư viện và được yêu cầu |
| Yêu cầu kỹ thuật | Python 3.9+ (đã kiểm thử 3.12), pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib, openpyxl | Như bên trái + python-docx; LibreOffice để điền số trang mục lục (tùy chọn) |

*Bảng 4. Mức độ của hai skill*


## ĐÃ CHẠY TEST TRÊN BỘ DỮ LIỆU NÀO?

Cả hai skill được chạy trên cùng ba bộ dữ liệu mở, khác nhau về bậc học, quy mô, định dạng và kiểu nhãn, với cùng lựa chọn đặc trưng, biến loại trừ và cột công bằng để kết quả so sánh được.

| Bộ dữ liệu | Nguồn / giấy phép | Quy mô | Bài toán |
|---|---|---|---|
| SAPE - Students_Academic_Performance_Evaluation_Dataset | Mendeley Data, DOI 10.17632/dc3797vf3t.1, CC BY 4.0 | 1.194 sinh viên CSE (Bangladesh), 31 biến | CGPA < 2,75 (sàng lọc đồng thời) |
| UCI Student Performance (môn tiếng Bồ Đào Nha) | UCI ML Repository, DOI 10.24432/C5TG7T, CC BY 4.0 | 649 học sinh THPT, 33 biến | G3 < 10 (trượt môn), mốc đầu năm học |
| UCI Predict Students' Dropout and Academic Success | UCI ML Repository, DOI 10.24432/C5MC89, CC BY 4.0 | 4.424 sinh viên đại học (Bồ Đào Nha), 37 biến | Target = Dropout, mốc cuối học kỳ 1 |

*Bảng 5. Ba bộ dữ liệu dùng để test*


## KẾT QUẢ


### Kết quả của student-risk-screening

| Bộ dữ liệu | Dòng (có nhãn) | Ca dương | AUC CV (baseline) | AUC test [CI] | Recall test @30% |
|---|---|---|---|---|---|
| SAPE | 1194 (1015) | 167 (16.5%) | 0.620 (0.615, Average attendance on class) | 0.614 [0.502, 0.7239] | 48.5% |
| UCI Student Performance | 649 (649) | 100 (15.4%) | 0.799 (0.665, failures) | 0.833 [0.7399, 0.9137] | 60.0% |
| UCI Dropout | 4424 (4424) | 1421 (32.1%) | 0.873 (0.810, Curricular units 1st sem (approved)) | 0.876 [0.8488, 0.8986] | 67.6% |

*Bảng 6. Hiệu năng của student-risk-screening (LR là mô hình chính ở cả ba bộ)*

- **Bộ test tự động: **28/28 kiểm tra đạt (testing/run_tests.py).
- **Đánh giá có/không có skill (skill-creator): **pass rate 100% so với 83%; chạy trên phiên bản 1.0.0, mỗi cấu hình một lần.


### Kết quả của analytics-capstone-pipeline

| Bộ dữ liệu | Mẫu / ca dương | AUC LR [KTC 95%] | AUC baseline | Recall @30% | Tiêu chí đạt | Mô hình giữ | Kiểm chứng |
|---|---|---|---|---|---|---|---|
| SAPE | 1.015 / 167 (16.5%) | 0,619 [0,572; 0,666] | 0,603 | 45,2% | 2/5 | Logistic L2 (chính) | 13/13 |
| UCI Student Performance | 649 / 100 (15.4%) | 0,804 [0,758; 0,850] | 0,683 | 68,2% | 3/5 | Random Forest | 13/13 |
| UCI Dropout | 4.424 / 1.421 (32.1%) | 0,865 [0,853; 0,876] | 0,817 | 68,3% | 3/5 | Logistic L2 (chính) | 13/13 |

*Bảng 7. Hiệu năng của analytics-capstone-pipeline (kiểm định chéo 5×10, seed 42)*

| Bộ dữ liệu | S1 hiệu năng | S2 hơn baseline | S3 rút gọn | S4 hiệu chuẩn | S5 công bằng |
|---|---|---|---|---|---|
| SAPE | Không đạt | Không đạt | Đạt | Đạt | Chưa kết luận |
| UCI Student Performance | Đạt (độ tin cậy cao) | Đạt | Đạt | Không đạt | Chưa kết luận |
| UCI Dropout | Đạt (độ tin cậy cao) | Đạt | Không đạt | Đạt | Không đạt |

*Bảng 8. Kết quả từng tiêu chí đăng ký trước*

- **Thời gian chạy đầy đủ: **74 giây (SAPE), 61 giây (UCI Student Performance), 190 giây (UCI Dropout) trên máy Windows 11.
- **Kiểm chứng tự động: **cả ba bộ qua đủ 13/13 phép kiểm chứng (mã băm, tính nhất quán, chế độ chạy đầy đủ).
- **Rò rỉ tự phát hiện: **trên SAPE, skill tự loại cột điểm SGPA kỳ trước (vừa có tên gợi ý hệ quả của nhãn, vừa có AUC đơn biến rất cao), đúng kết luận của đồ án.
- **Dựng sản phẩm (SAPE): **make_report.py sinh đủ 4 tệp trong 5 giây: báo cáo tổng hợp (18 bảng, 8 hình, 25 tài liệu tham khảo, không thiếu trích dẫn), tài liệu giải thích mã, kịch bản thuyết trình 12 slide, dàn ý slide (JSON); không còn dấu gạch ngang dài.
- **Tái lập đồ án: **trên SAPE, AUC LR 0.619 và Random Forest 0,635, gần với notebook Milestone 4 của nhóm (0,621 và 0,638; khác 1 đặc trưng mã hóa); cùng kết luận 2/5 tiêu chí đạt.


### So sánh hai skill trên cùng dữ liệu

| Bộ dữ liệu | student-risk-screening: AUC CV | student-risk-screening: AUC test | analytics-capstone-pipeline: AUC CV | Kết luận chung về tiêu chí hiệu năng |
|---|---|---|---|---|
| SAPE | 0.620 | 0.614 | 0,619 | Không đạt |
| UCI Student Performance | 0.799 | 0.833 | 0,804 | Đạt |
| UCI Dropout | 0.873 | 0.876 | 0,865 | Đạt |

*Bảng 9. Hai skill cho kết luận giống nhau trên cùng dữ liệu*

Hai skill dùng hai thiết kế đánh giá khác nhau (tập kiểm tra độc lập so với kiểm định chéo lặp trên toàn mẫu) nhưng cho AUC gần nhau và cùng kết luận: phiếu khảo sát SAPE không đạt tiêu chí hiệu năng, hai bộ UCI đạt. Sự nhất quán này là bằng chứng các con số không phụ thuộc vào một cách triển khai.


## NHẬN XÉT CHUNG


### student-risk-screening

**Mặt được**

- Tổng quát: chạy trên 3 bộ dữ liệu khác nhau về bậc học, kích thước (649-4.424 dòng), định dạng (xlsx, csv dấu ';'), kiểu nhãn chỉ bằng file cấu hình.
- Tái lập đúng kết luận phủ định của đồ án trên SAPE; tự phát hiện 140 nhãn nghi điền khuyết, biến rò rỉ, biến nhạy cảm.
- Kỷ luật đánh giá: baseline bắt buộc, chia dữ liệu trước khi fit, test một lần, CI bootstrap, quy tắc chọn mô hình và tiêu chí thành công đặt trước.
- Governance tích hợp: biến nhạy cảm bị loại khỏi mô hình nhưng giữ lại để kiểm định; phát hiện chênh lệch công bằng theo tuổi ở bộ Dropout.
- Đánh giá có/không có skill: pass rate 100% so với 83%.

**Chưa được**

- Không làm mô hình mạnh hơn; giá trị nằm ở quy trình, không ở độ chính xác.
- Gợi ý vai trò biến dựa trên từ khóa và thống kê, vẫn cần người rà soát (ví dụ bộ Dropout).
- Chỉ hỗ trợ dữ liệu một bảng; chưa có chia theo thời gian hoặc theo nhóm; báo cáo chỉ ở dạng Markdown.
- Chưa hiệu chỉnh xác suất và chưa có giải thích cấp cá nhân tự động; tốn token và thời gian hơn khi không dùng skill.


### analytics-capstone-pipeline

**Mặt được**

- Chạy được trên cả 3 bộ dữ liệu chỉ bằng file cấu hình, qua đủ 13/13 phép kiểm chứng ở mỗi bộ.
- Đăng ký trước tiêu chí S1-S5 có mã băm SHA-256; so sánh 4 mô hình bằng KTC ghép cặp; chỉ đổi mô hình khi hơn rõ (UCI Student Performance chuyển sang Random Forest đúng quy tắc).
- Trung thực với kết quả: SAPE chỉ đạt 2/5 tiêu chí và công bằng được ghi 'chưa kết luận' khi khoảng tin cậy rộng, thay vì kết luận quá mức.
- Tự phát hiện cột rò rỉ SGPA trên SAPE; có mẫu độ nhạy giữ cụm giá trị lặp nghi điền khuyết.
- Sinh đủ sản phẩm trình bày (báo cáo Word có mục lục và trích dẫn, tài liệu giải thích mã, kịch bản, dàn ý slide) trong vài giây, số liệu lấy trực tiếp từ kết quả.

**Chưa được**

- Trên Windows, bản gốc lỗi bảng mã khi in tiếng Việt (cp1252) ở bước cuối; nhóm đã sửa trong cả 3 script bằng cách buộc đầu ra UTF-8.
- Không có LibreOffice thì mục lục của báo cáo sinh ra chưa có số trang (cần mở bằng Word và cập nhật mục lục).
- Bảng và chú thích trong báo cáo sinh ra dùng cỡ chữ 9-12,5, thấp hơn mức 13 nhóm áp dụng cho báo cáo milestone.
- Mô tả gốc dài 704 ký tự, vượt giới hạn khuyến nghị của claude.ai; nhóm đã rút còn 176 ký tự và chuyển các câu kích hoạt xuống thân SKILL.md.
- Chưa có bộ test tự động (evals) và chưa chạy vòng đánh giá có/không có skill; phần mở rộng SHAP, LIME, SEM chưa chạy thử vì máy chưa cài shap, lime, semopy.
- Báo cáo sinh ra là khung chung; phần bối cảnh, bên liên quan và câu hỏi phân tích vẫn cần nhóm viết trong file cấu hình.


## CÀI ĐẶT VÀ SỬ DỤNG


### Claude Code - theo dự án

Hai thư mục .claude/skills/student-risk-screening/ và .claude/skills/analytics-capstone-pipeline/ được Claude Code tự nạp khi mở dự án. Muốn dùng ở mọi dự án, chép hai thư mục này vào ~/.claude/skills/.


### Claude Code - plugin

```
# giải nén n02-skills-marketplace.zip, rồi gõ trong ô chat của Claude Code:
/plugin marketplace add ./n02-skills-marketplace
/plugin install edu-analytics@n02-skills
```


### claude.ai

Bật Code execution trong Settings > Capabilities; vào Customize > Skills, tải lên student-risk-screening.zip và analytics-capstone-pipeline.zip (mỗi gói có thư mục skill ở cấp cao nhất).


### Chạy trực tiếp công cụ

```
python scripts/risk_screening.py profile students.xlsx --target CGPA --out work      # student-risk-screening
python scripts/risk_screening.py run --config work/config.json
python scripts/dspipe.py init --data data.xlsx --target CGPA --threshold 2.75 --positive-if "<" --out config.json   # analytics-capstone-pipeline
python scripts/dspipe.py all --config config.json
python scripts/make_report.py --config config.json
```


## CẤU TRÚC MÃ NGUỒN VÀ ĐÓNG GÓI

| Đường dẫn | Nội dung |
|---|---|
| .claude/skills/student-risk-screening/ | Mã nguồn skill 1: SKILL.md, scripts/risk_screening.py, references/, assets/, evals/ |
| .claude/skills/analytics-capstone-pipeline/ | Mã nguồn skill 2: SKILL.md, scripts/ (dspipe.py, make_report.py, docx_kit.py, build_notebook.py, extensions/), references/, assets/ |
| .claude/skill-dev/packaging/build_package.py | Kiểm tra theo quy tắc chính thức, dựng plugin từ hai skill gốc, nén vào dist/ |
| .claude/skill-dev/packaging/dist/ | student-risk-screening.zip, analytics-capstone-pipeline.zip (claude.ai), n02-skills-marketplace.zip (Claude Code), checksums.txt |
| .claude/skill-dev/testing/ | run_tests.py, datasets/, configs/ và results/ (skill 1); capstone/ với cấu hình, kết quả và test_summary của skill 2 |
| .claude/skill-dev/evaluation/ | Vòng đánh giá có/không có skill (skill 1) |
| .claude/skill-dev/docs/ | build_guide.py, _template_guide.docx, file hướng dẫn này (.docx, .md) |

*Bảng 10. Cấu trúc mã nguồn và gói phát hành*
