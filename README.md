# N02 - Hệ thống sàng lọc sớm sinh viên cần hỗ trợ học tập

Đồ án cuối kỳ học phần Khoa học Phân tích Dữ liệu (FIT-HCMUS), lĩnh vực Giáo dục.
Câu hỏi trung tâm: phiếu khảo sát tự báo cáo về thói quen và điều kiện học tập có đủ giá trị sàng lọc
để cố vấn học tập xếp thứ tự ưu tiên liên hệ sinh viên hay không.

## Sản phẩm nộp

| File | Nội dung |
|---|---|
| `requirements/N02_Proposal.docx` | Proposal (đề cương dự án) đã duyệt |
| `N02_MilestoneP1.docx` | Requirement Analysis & Project Proposal |
| `N02_MilestoneP2.docx` | From Requirements to Collection |
| `N02_MilestoneP3.docx` | From Understanding to Preparation |
| `N02_MilestoneP4.docx` | From Modeling to Evaluation (Level 1 và Level 2) |
| `N02_MilestoneP5.docx` | Final Integration & Project Report: OIEL, data story, dashboard wireframe, kịch bản demo, risk register, governance plan, checklist tự đánh giá, mẫu Peer Review Form |
| `N02_Slides.pptx` | Slide trình bày (15 slide) |
| `N02_Demo_CoVan.ipynb` | Demo cho cố vấn học tập theo kịch bản bảy bước (câu hỏi → đầu vào → xử lý → đầu ra kèm reason code → bằng chứng → cố vấn duyệt → xuất danh sách và nhật ký); chạy trên Colab, khoảng 1–2 phút |

## Mã nguồn: bốn notebook Google Colab

Toàn bộ mã nằm trong `notebooks/`; không có tệp `.py` riêng. Mỗi notebook nhúng sẵn file dữ liệu gốc,
kiểm tra SHA-256 trước khi đọc, và có ô hướng dẫn ở đầu.

| Notebook | Milestone | Đầu ra chính (ghi vào `/content/N02_MilestoneX` trên Colab) |
|---|---|---|
| `N02_Milestone2_ThuThap_KiemTraCauTruc.ipynb` | M2 | `data/metadata/` (collection log, nguồn và giấy phép, data dictionary, tóm tắt cấu trúc) |
| `N02_Milestone3_ChuanBiDuLieu_EDA.ipynb` | M3 | `data/interim/`, `data/processed/` (Prepared Dataset v1.0), từ điển, lineage, 15 hình và 21 bảng EDA |
| `N02_Milestone4_MoHinh_DanhGia.ipynb` | M4 | Kế hoạch đăng ký trước (SHA-256 `6544eb…`), 9 hình, 17 bảng, `oof_predictions_m4.csv` |
| `N02_Milestone5_TichHop_KiemTra.ipynb` | M5 | Chạy lại M2 đến M4, kiểm tra nhất quán, Final Traceability Matrix (Excel) |

Cách chạy: mở notebook trên Google Colab, chọn **Runtime → Run all**. Thư mục `/content` bị xóa khi hết phiên,
nên cần tải thư mục kết quả về nếu muốn lưu. Thư viện dùng (pandas, numpy, scipy, scikit-learn, matplotlib) có sẵn trên Colab.
Lần chạy Colab gần nhất dùng Python 3.13.18, pandas 2.2.3, numpy 2.4.6, scipy 1.16.3, scikit-learn 1.6.1;
các chỉ số chính khớp số trong báo cáo với sai lệch không quá 0,005.

## Dữ liệu

- Nguồn: Rahman, A. T., Lamia, S., Shishir, A. H., & Barsa, M. M. (2024). *Students_Academic_Performance_Evaluation_Dataset* (Version 1). Mendeley Data. https://doi.org/10.17632/dc3797vf3t.1, giấy phép CC BY 4.0.
- File gốc: `data/raw/Students_Performance_data_set.xlsx` (chỉ đọc; 187.253 byte; SHA-256 `04ebaf9f3a047afe96d9bff22dbe65b2a320e6395f230032735495e7e58277cf`).
- Provenance và metadata Milestone 2: `data/metadata/` (`source_and_license.md`, `collection_log.md`, `mendeley_metadata_v1.json`, `data_dictionary_m2.csv`, `structural_summary_m2.*`).
- Đây là dữ liệu khảo sát sinh viên BCSE của một trường đại học tư thục ở Bangladesh, không phải dữ liệu của sinh viên FIT-HCMUS. Dữ liệu không có họ tên hay mã số; nhóm không tái định danh và chỉ báo cáo kết quả gộp.

## Cấu trúc thư mục

```
data/raw/            file gốc (không chỉnh sửa)
data/metadata/       provenance, data dictionary và tóm tắt cấu trúc của Milestone 2
notebooks/           bốn notebook Colab (M2 đến M5)
requirements/        yêu cầu của học phần và Proposal đã duyệt
.claude/skills/      bộ skill Claude của nhóm (student-risk-screening, analytics-capstone-pipeline)
.claude/skill-dev/   đóng gói plugin, bộ test, file hướng dẫn skill
```

## Giới hạn chính

Dữ liệu cắt ngang và tự báo cáo, nên dự án chỉ làm sàng lọc đồng thời, không dự báo; mọi kết luận chẩn đoán là liên hệ quan sát.
Kết quả không chuyển giao trực tiếp sang bối cảnh FIT-HCMUS (xem Mục 12 của báo cáo Milestone 5).
