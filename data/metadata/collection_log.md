# Collection log - Raw Data Package

| Ngày | Hành động | Kết quả / bằng chứng |
|---|---|---|
| 03/11/2026 | Truy cập landing page qua DOI 10.17632/dc3797vf3t.1; xác nhận Version 1, giấy phép CC BY 4.0 | Thông tin ghi vào `source_and_license.md` |
| 03/11/2026 | Tải gói dữ liệu bằng "Download All", giữ nguyên file Excel trong thư mục "Students Performance data set" | `Students_Performance_data_set.xlsx`, 187.253 byte |
| 03/11/2026 | Tính SHA-256 của file gốc | `04ebaf9f3a047afe96d9bff22dbe65b2a320e6395f230032735495e7e58277cf` |
| 03/11/2026 | Chạy `src/verify_raw.py` ở chế độ chỉ đọc | `structural_summary_m2.csv`, `structural_summary_m2.json` |
| 10/11/2026 | Tái lập Raw Data Package (Milestone 3): tải lại qua liên kết `download_url` của public API Mendeley (`/public-api/datasets/dc3797vf3t/files?folder_id=root&version=1`) và lưu metadata API | SHA-256 trùng khớp với giá trị 03/11/2026 và với `sha256_hash` do Mendeley công bố; lưu `mendeley_metadata_v1.json` |

Quy tắc: không chỉnh sửa, đổi tên hay ghi đè file trong `data/raw/`. Mọi xử lý tạo file mới trong `data/interim/` hoặc `data/processed/`.
