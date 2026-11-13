# Quy cách báo cáo, slide và kịch bản

## Mục lục
1. Báo cáo Word chính
2. Tài liệu giải thích mã (tách riêng)
3. Bộ slide
4. Kịch bản đọc
5. Danh sách kiểm tra trước khi giao

## 1. Báo cáo Word chính (`BaoCao_TongHop.docx`)
Do `scripts/make_report.py` sinh tự động qua `docx_kit.Report`. Cấu trúc cố định: Bìa, Mục lục (có số trang), Tóm tắt điều hành, 1 Bối cảnh và giả định, 2 Dữ liệu và kiểm toán, 3 Thiết kế đánh giá và đăng ký trước, 4 Chẩn đoán, 5 Mô hình dự báo, 6 Công bằng, 7 Kết luận theo tiêu chí và hàm ý, 8 Kiểm chứng và tái lập, Tài liệu tham khảo.

Quy cách bắt buộc (đã được lập trình sẵn, kiểm tra lại sau khi sinh):
- Văn phong học thuật tiếng Việt, số thập phân dùng dấu phẩy, dấu chấm ngăn nghìn.
- Không chứa mã thực thi hay lệnh; mã nằm ở tệp riêng.
- Không dùng dấu gạch ngang dài (— hoặc –); `make_report.py` tự quét và báo.
- Mục lục kèm số trang thật: dựng nhiều lượt, đổi sang PDF bằng LibreOffice rồi dò trang tiêu đề. Nếu máy không có `soffice` hoặc `pdftotext`, mục lục không có số trang; khi đó phải nói rõ với người dùng và hướng dẫn nhấn Cập nhật trường trong Word.
- Trích dẫn đánh số [x] theo thứ tự xuất hiện lần đầu, danh mục cuối bài khớp tuyệt đối. Khóa tài liệu nằm ở `references/refs.json`; muốn thêm tài liệu thì thêm khóa vào tệp này và gọi `r.C("khóa")`.
- Mọi bảng có chú thích "Bảng n." bên dưới, mọi hình có chú thích "Hình n.", tham chiếu chéo dùng bộ đăng ký số tự động.
- Con số trong văn bản lấy từ tệp kết quả, không gõ tay.

Khi cần viết thêm chương (ví dụ thảo luận theo bối cảnh riêng của người dùng), thêm hàm `sec_xxx(r, R)` vào `make_report.py` rồi gọi trong `build()`. Mọi lựa chọn kỹ thuật phải kèm lập luận khoa học và trích dẫn. Không bao giờ tự thêm tài liệu tham khảo mà chưa kiểm chứng trên nguồn chính thức (DOI, nhà xuất bản).

## 2. Tài liệu giải thích mã (`GiaiThich_MaNguon_va_HoTro.docx`)
Tách riêng theo yêu cầu "không thấy mã thực thi trong báo cáo chính". Gồm kiến trúc mã, giải thích từng giai đoạn, các quyết định thống kê, phân định trách nhiệm giữa trợ lý và nhóm, hướng dẫn chạy lại. Phần phân định trách nhiệm nhằm minh bạch về việc dùng trợ lý; không được xóa.

## 3. Bộ slide
Nguồn nội dung là `deck_outline.json` (12 slide: mở đầu, bối cảnh, dữ liệu, đăng ký trước, chẩn đoán, mô hình, năng lực gắn cờ, hiệu chuẩn, công bằng, bảng điểm, hàm ý và hạn chế, bước tiếp theo). Mỗi phần tử có `title`, `kicker`, `points`, `figure` (đường dẫn ảnh nếu có) và `script`.

Nếu công cụ Artifact liệt kê loại Slides: tạo bộ slide từ loại đó, làm theo hướng dẫn trả về cùng loại (thường là `deck.json` cộng `slides/*.html` khổ 1920×1080, chữ không nhỏ hơn 24 px). Nếu người dùng muốn PowerPoint: dùng skill pptx. Không dựng slide trước khi có kết quả cuối.

Quy tắc nội dung slide (rút từ lần rà soát tiêu đề trong đồ án gốc):
- Tiêu đề là một câu kết luận tự nhiên bằng tiếng Việt, ngắn gọn (khoảng 50 ký tự), không phải nhãn máy móc hay ghép từ. Đọc to từng tiêu đề; nếu nghe gượng thì viết lại.
- Mỗi slide một thông điệp; con số lớn nêu thông điệp, hình hoặc biểu đồ minh chứng.
- Mọi con số trên slide phải khớp báo cáo; sau khi dựng, đối chiếu từng con số với `results.json`.
- Biểu đồ dựng bằng HTML phải có nhãn trục hoặc nhãn giá trị trực tiếp; không để màu là phương tiện duy nhất mang nghĩa.

## 4. Kịch bản đọc
Ghi vào ghi chú diễn giả của từng slide một bản đọc đầy đủ thành câu, không ghi ý gạch đầu dòng. Mỗi slide khoảng 40 đến 70 giây đọc (12 slide cho khoảng 10 phút). Câu văn nói rõ ràng, tránh ký hiệu khó đọc (viết "p Holm" thay vì ký hiệu), đọc số theo cách tự nhiên. Một bản Word độc lập `KichBan_ThuyetTrinh.docx` được sinh sẵn làm dự phòng. Nếu người dùng yêu cầu thời lượng khác, rút gọn hoặc mở rộng câu chữ, đừng bỏ slide cốt lõi (kết quả, hạn chế, bước tiếp theo).

## 5. Danh sách kiểm tra trước khi giao
- [ ] `verify.json` có `all_passed` bằng true và chạy ở chế độ đầy đủ (không `--fast`).
- [ ] Tóm tắt điều hành khớp bảng điểm S1 đến S5.
- [ ] Mục lục có số trang; số trang đúng khi mở PDF.
- [ ] Không có mã, không có dấu gạch ngang dài, không có "?" ở tham chiếu chéo (ví dụ "Bảng ?").
- [ ] Mọi trích dẫn [x] có mặt trong danh mục; mọi mục danh mục được trích dẫn.
- [ ] Giả định và hạn chế quan trọng đã nêu (nhãn tạm thời, tự khai, cắt ngang, một nguồn, EPV thấp, nhu cầu giả định).
- [ ] Phản hồi cuối cho người dùng có dự báo bước kỹ thuật tiếp theo.
