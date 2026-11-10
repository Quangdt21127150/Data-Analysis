# N02 - Hệ thống sàng lọc sớm sinh viên cần hỗ trợ học tập

Đồ án cuối kỳ học phần Khoa học Phân tích Dữ liệu (FIT-HCMUS), lĩnh vực Giáo dục.
Câu hỏi trung tâm: phiếu khảo sát tự báo cáo về thói quen và điều kiện học tập có đủ giá trị sàng lọc
để cố vấn học tập xếp thứ tự ưu tiên tiếp cận sinh viên hay không.

## Báo cáo

| File | Nội dung |
|---|---|
| `N02_Proposal.docx` | Project Proposal (Đề cương dự án) |
| `N02_MilestoneP1.docx` | Requirement Analysis & Project Proposal (v1.1) |
| `N02_MilestoneP2.docx` | From Requirements to Collection (v1.1) |
| `N02_MilestoneP3.docx` | From Understanding to Preparation |
| `N02_MilestoneP4.docx` | From Modeling to Evaluation (Level 1 + Level 2) |
| `N02_MilestoneP5.docx` | Final Integration & Project Report; Phụ lục D-H: EDA + bảng Observation–Insight–Evidence–Limitation, dashboard wireframe + data story, thành phần AI-assist + prototype, kịch bản demo, checklist tự đánh giá theo Đề cương |
| `N02_Slides.pptx` | Slide trình bày (15 slide) |

## Dữ liệu

- Nguồn: Rahman, A. T., Lamia, S., Shishir, A. H., & Barsa, M. M. (2024). *Students_Academic_Performance_Evaluation_Dataset* (Version 1). Mendeley Data. https://doi.org/10.17632/dc3797vf3t.1 - giấy phép CC BY 4.0.
- File gốc: `data/raw/Students_Performance_data_set.xlsx` (bất biến, SHA-256 `04ebaf9f3a047afe96d9bff22dbe65b2a320e6395f230032735495e7e58277cf`).
- Provenance: `data/metadata/source_and_license.md`, `collection_log.md`, `mendeley_metadata_v1.json`.
- Đây là dữ liệu khảo sát sinh viên ngành CSE tại một trường đại học ở Bangladesh, không phải dữ liệu của sinh viên FIT-HCMUS.

## Cấu trúc thư mục

```
data/raw/            file gốc (không chỉnh sửa)
data/interim/        dữ liệu sau định kiểu và làm sạch (tái tạo được)
data/processed/      4 analytic-ready views, prepared dataset v1.0
data/metadata/       data dictionary, lineage/transformation log, validation summary, provenance
src/                 config.py, verify_raw.py (M2), prepare_data.py + profile_data.py (M3), model_experiment.py (M4)
notebooks/           01-04: notebook bọc các script theo từng milestone
reports/milestone3/  bảng profiling (JSON) và 9 biểu đồ
reports/milestone4/  kết quả thực nghiệm (JSON) và 6 biểu đồ
reports/gd4/         dashboard wireframe (Phụ lục E của P5)
reports/build/       mã dựng các báo cáo .docx (template từ N02_Proposal), m5_appendices.py (Phụ lục D-H của P5), build_slides.js (slide)
demo/                prototype hỗ trợ cố vấn: advisor_brief.py (propose / simulate-review / act), check_drafts.py
.claude/skills/student-risk-screening/   skill Claude tổng quát hóa quy trình đồ án (Claude Code tự nạp)
.claude/skill-dev/   đóng gói plugin, bộ test trên 3 bộ dữ liệu, vòng đánh giá, file hướng dẫn skill (xem README bên trong)
```

## Tái lập phân tích

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
.venv/Scripts/python src/verify_raw.py        # M2: kiểm tra cấu trúc raw (chỉ đọc)
.venv/Scripts/python src/prepare_data.py      # M3: raw -> interim -> processed (v1.0)
.venv/Scripts/python src/profile_data.py      # M3: bảng và hình profiling
.venv/Scripts/python src/model_experiment.py  # M4: Level 2 prototype (khoảng 2 phút)
```

Demo (Giai đoạn 7, 10):

```bash
.venv/Scripts/python demo/advisor_brief.py propose          # hàng đợi đề xuất + bằng chứng + nhật ký
.venv/Scripts/python demo/check_drafts.py                   # kiểm tra bản nháp câu mở lời (16 ca kiểm thử)
.venv/Scripts/python demo/advisor_brief.py simulate-review  # chỉ để demo: giả lập cố vấn duyệt
.venv/Scripts/python demo/advisor_brief.py act              # xuất danh sách đã duyệt (từ chối nếu còn dòng chưa duyệt)
```

Seed cố định 2026; test set (203 bản ghi) được tách ở M3 và chỉ dùng một lần ở M4.
Kết quả chính được lưu tại `reports/milestone4/experiment_results.json`.

## Dựng lại báo cáo Word (tùy chọn, cần Microsoft Word trên Windows)

```bash
.venv/Scripts/python reports/build/build_m3.py      # tương tự build_m4.py, build_m5.py, rebuild_m1.py, rebuild_m2.py
# rebuild_m1.py / rebuild_m2.py áp bản vá v1.2 (patch_m1_v12.py, patch_m2_v12.py); build_m5.py gọi m5_appendices.py (Phụ lục D-K)
.venv/Scripts/python reports/build/verify_format.py # kiểm tra Times New Roman, cỡ chữ >= 13
```

Mục lục được cập nhật bằng Word thông qua `docbuilder.finalize()`.

## Giới hạn chính

Dữ liệu cắt ngang và tự báo cáo; mọi kết luận là liên hệ quan sát, chỉ áp dụng cho sinh viên đã có điểm tích lũy,
và không chuyển giao trực tiếp sang bối cảnh FIT-HCMUS (xem Mục 12 của báo cáo Milestone 5).
