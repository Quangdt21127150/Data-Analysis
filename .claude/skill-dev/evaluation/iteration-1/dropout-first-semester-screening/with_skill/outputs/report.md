# Báo cáo: Công cụ sàng lọc sinh viên cần hỗ trợ sớm sau học kỳ 1 năm nhất

*Phòng Công tác Sinh viên · Dữ liệu: `students_dropout.csv` (4.424 sinh viên các khóa trước) · Ngày 10/11/2026*

## 1. Trả lời ngắn

- **Có xây được công cụ sàng lọc dùng được không?** Có. Từ hồ sơ tuyển sinh và kết quả học kỳ 1, mô hình hồi quy logistic xếp hạng sinh viên khá tốt: AUC 0,87 (kiểm định chéo), 0,88 trên tập kiểm tra độc lập.
- **Bắt được bao nhiêu sinh viên bỏ học?** Khi cố vấn gặp **30% sinh viên** có điểm rủi ro cao nhất, danh sách chứa khoảng **67–68% số sinh viên sau này bỏ học** (test 66,9%; CV 68,6%). Khoảng **73%** sinh viên trong danh sách thực sự bỏ học, gấp 2,3 lần so với chọn ngẫu nhiên.
- **Mô hình hơn một luật đơn giản bao nhiêu?** Chỉ riêng *số học phần đạt ở HK1* đã bắt được khoảng 65–66% ca bỏ học ở mức 30%. Mô hình đầy đủ tốt hơn rõ về xếp hạng tổng thể (AUC 0,87 so với 0,81), nhưng ở đúng mức 30% chỉ hơn **khoảng 1–3 điểm %** recall. Phần lớn tín hiệu đến từ kết quả HK1.
- **Có công bằng không?** **Chưa đạt** tiêu chí đặt trước (chênh lệch recall ≤ 10 điểm %). Công cụ bỏ sót nhiều hơn ở **sinh viên nhập học ≤ 20 tuổi** (recall 55% so với 77% ở nhóm > 20 tuổi) và, ở mức nhẹ hơn, ở **nữ** (63% so với 74%). Tuổi và giới tính không nằm trong mô hình. Chênh lệch này đến từ các biến đại diện gián tiếp và từ việc sinh viên trẻ bỏ học thường có kết quả HK1 "bình thường" hơn.
- **Khuyến nghị:** dùng công cụ như **danh sách gợi ý để cố vấn chủ động gặp**, kèm theo dõi chênh lệch theo nhóm và một kênh bổ sung cho sinh viên trẻ (mục 6). Không dùng để gán nhãn hay ra quyết định tự động.

## 2. Thiết lập phân tích

| Nội dung | Lựa chọn |
|---|---|
| Mốc dự báo | Ngay sau khi có kết quả HK1 năm nhất. Chỉ dùng thông tin có tại thời điểm này |
| Nhãn dương | `Target = Dropout` (1.421/4.424 = 32,1%). **Giả định:** `Enrolled` (còn đang học) tính là không bỏ học |
| Đặc trưng (13) | Hồ sơ tuyển sinh: phương thức xét tuyển, thứ tự nguyện vọng, ngành, học ngày/tối, văn bằng trước, điểm văn bằng trước, điểm xét tuyển. Kết quả HK1: số học phần được công nhận/đăng ký/có đánh giá/đạt/không có đánh giá, điểm TB HK1 |
| Loại vì rò rỉ | 6 biến học kỳ 2: chưa có tại mốc dự báo, và sinh viên bỏ học thì HK2 = 0, nên các biến này gần như là nhãn |
| Loại vì nhạy cảm (chỉ dùng để kiểm định công bằng) | Giới tính, tuổi, hôn nhân, quốc tịch, du học sinh, chuyển chỗ ở, nhu cầu giáo dục đặc biệt, học vấn/nghề nghiệp cha mẹ, nợ học phí, đóng học phí đúng hạn, học bổng. Ba biến tài chính sau cùng còn **không rõ thời điểm ghi nhận** và có thể là hệ quả của kết quả học tập |
| Loại khác | Thất nghiệp, lạm phát, GDP: mỗi giá trị tương ứng một khóa, nên với một khóa mới chúng là hằng số |
| Quy trình | Chia train/test 80/20 phân tầng trước mọi phép fit. Tiền xử lý nằm trong pipeline. Chọn mô hình bằng CV 5 fold × 5 lần lặp theo quy tắc đặt trước. Tập test chỉ xem một lần |

Chi tiết từng quyết định: `notes.md`.

## 3. Hiệu năng so với baseline

| Mô hình | AUC CV | Recall @30% (CV) | AUC test [CI 95%] | Recall @30% (test) |
|---|---|---|---|---|
| B0: chọn ngẫu nhiên | 0,50 | 28,9% | – | – |
| B1: chỉ số học phần đạt HK1 | 0,81 | 65,3% | 0,84 [0,81–0,87] | 66,2% |
| **Logistic (mô hình chính)** | **0,87** | **68,6%** | **0,88 [0,85–0,90]** | **66,9%** |
| Random Forest | 0,86 | 66,9% | 0,88 [0,86–0,91] | 70,8% |

Mô hình chính là logistic, chọn theo CV. RF không vượt LR trên CV, và con số test cao hơn của RF không được dùng để đổi lựa chọn. Bốn tiêu chí đặt trước đều đạt: AUC ≥ 0,70, recall ≥ 60% ở mức 30%, vượt baseline ≥ 0,02 AUC, và rút gọn được biến.

**Đánh đổi theo năng lực gặp** (dự đoán ngoài mẫu trên tập train / tập test):

| Tỷ lệ được gặp | Recall | Precision (tỷ lệ thực sự bỏ học trong danh sách) |
|---|---|---|
| 15% | 43% / 44% | 92% / 89% |
| 20% | 54% / 52% | 86% / 85% |
| 25% | 63% / 60% | 81% / 79% |
| **30%** | **68% / 67%** | **73% / 73%** |
| 40% | 80% / 82% | 64% / 65% |

Lưu ý: tỷ lệ bỏ học khoảng 32%, nên dù có mô hình hoàn hảo thì danh sách 30% cũng không thể chứa hết sinh viên bỏ học. Mức trần lý thuyết là khoảng 93%.

Trong danh sách 30%, ngoài 73% sinh viên bỏ học còn 17% là sinh viên "Enrolled" (học chậm tiến độ). Nhóm này nhiều khả năng cũng cần hỗ trợ, nên đây không hẳn là cảnh báo sai. Chỉ khoảng 9% là sinh viên sau này tốt nghiệp đúng hạn.

## 4. Tín hiệu nào quan trọng (liên hệ, không phải nhân quả)

- **Số học phần đạt ở HK1** là tín hiệu mạnh nhất, vượt xa các biến khác. Tỷ lệ bỏ học theo số học phần đạt (tập train): 0 học phần → 80%; 1–2 → 73%; 3–4 → 41%; 5–6 → 14%; ≥ 7 → 11%.
- Các tín hiệu bổ sung: số học phần đăng ký và được công nhận (khi cùng mức số học phần đạt, đăng ký nhiều mà đạt ít gắn với rủi ro cao hơn), ngành học, phương thức xét tuyển.
- Bộ rút gọn 6 biến (học phần HK1 được công nhận/đăng ký/đạt/không đánh giá, phương thức xét tuyển, ngành) đạt AUC tương đương mô hình đầy đủ (0,873). Chỉ với 2 biến (học phần được công nhận và đạt) đã đạt khoảng 95% hiệu năng. Điều này có nghĩa là có thể vận hành bằng một bộ dữ liệu tối thiểu.
- Đây là quan hệ thống kê trên dữ liệu quan sát. Kết quả HK1 thấp có thể là *dấu hiệu* của khó khăn (tài chính, sức khỏe, chọn sai ngành), không nhất thiết là nguyên nhân. Dữ liệu không cho biết can thiệp nào hiệu quả.

## 5. Công bằng (gắn cờ 30%, dự đoán ngoài mẫu trên train; test cho kết quả tương tự)

| Nhóm | Tỷ lệ bỏ học thật | Tỷ lệ được gắn cờ | Recall | Chênh lệch recall [CI 95%] |
|---|---|---|---|---|
| Tuổi nhập học ≤ 20 | 21% | 19% | 55% | **22 điểm % [17–28]** (test 26 [14–36]) |
| Tuổi nhập học > 20 | 47% | 46% | 77% | |
| Giới tính = 0 (nữ, theo mã của bộ dữ liệu gốc) | 25% | 23% | 63% | **11 điểm % [6–16]** (test 9 [1–20]) |
| Giới tính = 1 (nam) | 46% | 43% | 74% | |
| Không nợ học phí | 28% | 28% | 69% | 2 điểm % (test 0,3) |
| Có nợ học phí | 63% | 49% | 67% | |

Diễn giải:
- Tỷ lệ gắn cờ theo nhóm gần bằng tỷ lệ bỏ học thật của nhóm, nên danh sách **không gắn cờ quá mức** cho nhóm nào. Vấn đề nằm ở chỗ khác: **sinh viên trẻ bỏ học bị bỏ sót nhiều hơn**.
- Baseline chỉ dùng số học phần đạt cũng có chênh lệch theo tuổi (58% so với 69%). Như vậy chênh lệch chủ yếu đến từ dữ liệu: nhiều sinh viên trẻ bỏ học vẫn đạt khá ở HK1, nên không có tín hiệu sớm trong dữ liệu hiện có. Mô hình đầy đủ làm khoảng cách này rộng thêm, nhiều khả năng qua phương thức xét tuyển (ví dụ diện trên 23 tuổi) và hình thức học buổi tối, vốn là các biến đại diện gián tiếp cho tuổi.
- Thử kịch bản tham khảo: chia chỉ tiêu 30% riêng cho mỗi nhóm tuổi. Khi đó recall nhóm trẻ lên 72%, nhưng nhóm > 20 tuổi giảm còn 58% và recall tổng giảm từ 68% xuống 63%. Cân bằng tuyệt đối có chi phí. Đây là lựa chọn chính sách của Phòng, không phải lựa chọn kỹ thuật.

## 6. Khuyến nghị

**Cho Phòng CTSV**
1. Triển khai thử một học kỳ theo hình thức **danh sách gợi ý**: xếp hạng sinh viên năm nhất ngay sau khi có điểm HK1, mời 30% đầu danh sách gặp cố vấn. Nếu nguồn lực chỉ đủ 15% thì vẫn bắt được khoảng 43% ca bỏ học, với độ chính xác khoảng 90%.
2. Nếu cần một công cụ **đơn giản, dễ giải thích**, luật "số học phần đạt HK1 thấp", kết hợp tỷ lệ đạt/đăng ký, cho hiệu quả gần bằng mô hình ở mức 30%. Mô hình đầy đủ có lợi hơn khi cần xếp hạng chi tiết hoặc khi nguồn lực thấp hơn 30%.
3. Bổ sung **kênh riêng cho sinh viên trẻ**, vì nhóm này bị bỏ sót nhiều nhất. Có thể dành một phần nhỏ chỉ tiêu cho nhóm ≤ 20 tuổi kế tiếp trong bảng xếp hạng, hoặc thêm kênh tự đăng ký và giới thiệu từ giảng viên. Cách làm cụ thể nên quyết định sau khi xem số liệu đợt thử.
4. **Theo dõi mỗi kỳ:** recall, tỷ lệ gắn cờ và chênh lệch theo tuổi/giới. Kiểm định lại mô hình khi đổi chương trình đào tạo hoặc quy chế.

**Cho cố vấn học tập**
- Điểm rủi ro chỉ dùng để **xếp thứ tự ưu tiên**. Xác suất của mô hình đang cao hơn thực tế (trung bình 42% so với tỷ lệ thật 32%, do mô hình cân bằng lớp), nên **không đọc điểm là "x% sẽ bỏ học"**.
- Lý do gợi ý nên trình bày trung tính và theo hướng hỗ trợ, ví dụ "số học phần đạt ở HK1 thấp hơn số đã đăng ký". Không dùng các cụm như "sinh viên yếu" hay "có nguy cơ bỏ học" khi trao đổi với sinh viên.
- Cố vấn quyết định có liên hệ hay không. Không gửi thông báo tự động.

**Về dữ liệu và quản trị**
- Danh sách chỉ hiển thị cho cố vấn có thẩm quyền. Biến nhạy cảm chỉ dùng cho kiểm định công bằng.
- Cần thu thập thêm: **ghi nhận cố vấn đã gặp ai và hỗ trợ gì** (để sau này đánh giá hiệu quả can thiệp), tín hiệu sớm trong HK1 (chuyên cần, LMS), và thời điểm ghi nhận chính xác của các biến học phí/học bổng. Các tín hiệu sớm này có thể giúp phát hiện sinh viên trẻ bỏ học mà kết quả HK1 chưa phản ánh.

## 7. Độ nhạy và giới hạn

- **Nhãn Enrolled:** nếu bỏ sinh viên "Enrolled" ra và chỉ so Dropout với Graduate, AUC lên 0,92 và recall ở mức 30% khoảng 70%. Con số này **lạc quan hơn thực tế**, vì khi triển khai không thể biết trước ai sẽ thuộc nhóm "Enrolled". Con số dùng để ra quyết định là của kịch bản chính (AUC 0,87, recall khoảng 67–68%). Chênh lệch theo tuổi vẫn tồn tại trong kịch bản này (22–33 điểm %).
- Dữ liệu là ảnh chụp của các khóa trước, không có thông tin năm học để kiểm định theo thời gian ("train khóa cũ, test khóa mới"). Hiệu năng trên khóa mới có thể thấp hơn.
- Điểm TB HK1 = 0 ở 718 sinh viên không đạt học phần nào. Đây không phải điểm thật, nhưng thông tin này đã được biến số học phần đạt phản ánh.
- Dữ liệu không có thông tin can thiệp, nên báo cáo **không kết luận** rằng gặp cố vấn sẽ làm giảm bỏ học. Cần theo dõi sau triển khai để đánh giá.
- Các mã danh mục (ngành, phương thức xét tuyển) cần đối chiếu với từ điển dữ liệu của trường trước khi dùng làm lý do gợi ý.

## Tệp kèm theo

- `config.json`: cấu hình phân tích chính. `config_sensitivity_no_enrolled.json`: cấu hình kịch bản độ nhạy.
- `output/`: kết quả của công cụ, gồm `results.json`, `report.md` (báo cáo kỹ thuật tự động), `validation.json`, `transformation_log.json`, `prepared.csv` và `figures/` (ROC/PR, recall theo tỷ lệ gắn cờ, rút gọn biến, hiệu chỉnh).
- `output_sens_no_enrolled/`: kết quả kịch bản độ nhạy.
- `supplementary/`: kiểm tra bổ sung về công bằng (baseline so với LR), tỷ lệ bỏ học theo số học phần đạt, kịch bản chỉ tiêu theo nhóm tuổi.
- `work/`: profile dữ liệu ban đầu. `notes.md`: nhật ký quyết định.
