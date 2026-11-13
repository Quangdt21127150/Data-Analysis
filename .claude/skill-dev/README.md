# Phát triển bộ skill của nhóm N02 (plugin `edu-analytics` 1.2.0)

Hai skill:
- `student-risk-screening`: sàng lọc người học cần hỗ trợ từ dữ liệu điểm/LMS/khảo sát (profiling → kiểm soát rò rỉ → chẩn đoán →
  mô hình so với baseline → công bằng → đánh đổi ngưỡng → báo cáo Markdown).
- `analytics-capstone-pipeline`: quy trình đồ án trọn gói trên bảng dữ liệu bất kỳ (kiểm toán → đăng ký trước tiêu chí → chẩn đoán →
  mô hình kiểm định chéo 5×10 → hiệu chuẩn, công bằng → báo cáo Word, tài liệu giải thích mã, kịch bản, dàn ý slide).

## Bố cục thư mục `.claude/`

```
.claude/
├── skills/
│   ├── student-risk-screening/        # SKILL GỐC 1 - nguồn duy nhất; Claude Code tự nạp khi mở dự án
│   └── analytics-capstone-pipeline/   # SKILL GỐC 2 - scripts/dspipe.py, make_report.py, docx_kit.py, build_notebook.py, extensions/
│       ├── SKILL.md                   # quy trình 6 bước cho Claude
│       ├── scripts/risk_screening.py  # CLI: profile | prepare | analyze | report | run
│       ├── references/                # config-schema.md, methodology.md, responsible-analytics.md
│       ├── assets/config-template.json
│       └── evals/                     # 2 test case (định dạng claude plugin eval; không đóng gói lên claude.ai)
└── skill-dev/                         # mọi thứ phục vụ phát triển và phát hành
    ├── packaging/
    │   ├── marketplace/               # manifest: .claude-plugin/marketplace.json, plugins/edu-analytics/.claude-plugin/plugin.json
    │   ├── build_package.py           # kiểm tra theo quy tắc chính thức, dựng plugin từ 2 skill gốc, nén vào dist/
    │   └── dist/                      # student-risk-screening.zip, analytics-capstone-pipeline.zip (claude.ai), n02-skills-marketplace.zip (Claude Code), checksums.txt
    ├── testing/
    │   ├── run_tests.py               # chạy skill trên 3 bộ dữ liệu, kiểm tra 28 tính chất
    │   ├── datasets/                  # SAPE (Mendeley), UCI Student Performance, UCI Dropout - CC BY 4.0
    │   ├── configs/                   # cấu hình đã rà soát domain cho từng bộ
    │   └── results/                   # profile, kết quả, report.md, hình; test_summary.md
    ├── evaluation/                    # vòng đánh giá skill-creator: Claude làm cùng nhiệm vụ có/không có skill
    │   ├── iteration-1/               # đầu ra, grading.json, timing.json, benchmark.json/.md
    │   └── eval_review.html           # trình xem kết quả
    └── docs/
        ├── build_guide.py             # dựng hướng dẫn từ _template_guide.docx và kết quả test
        └── N02_HuongDan_Skill.docx / .md
```

Plugin trong `packaging/marketplace/` không chứa bản sao skill: `build_package.py` chép hai skill gốc vào lúc đóng gói,
nên chỉ cần sửa ở `.claude/skills/<tên-skill>/`.

## Lệnh thường dùng (từ thư mục gốc dự án)

```bash
python .claude/skill-dev/testing/run_tests.py            # ~5 phút; ghi testing/results/test_summary.md
python .claude/skill-dev/packaging/build_package.py      # tạo packaging/dist/
python .claude/skill-dev/docs/build_guide.py             # sinh file hướng dẫn cho cả hai skill
# test skill 2 (mỗi bộ dữ liệu, chạy trong testing/capstone/<bộ>/):
python ../../../skills/analytics-capstone-pipeline/scripts/dspipe.py all --config config.json
```

## Cài đặt

- **Claude Code, theo dự án/cá nhân:** chép `skills/student-risk-screening/` và `skills/analytics-capstone-pipeline/` vào `.claude/skills/` của dự án hoặc `~/.claude/skills/`.
- **Claude Code, plugin:** giải nén `n02-skills-marketplace.zip`, rồi `/plugin marketplace add ./n02-skills-marketplace` và `/plugin install edu-analytics@n02-skills`.
- **claude.ai:** tải `student-risk-screening.zip` và `analytics-capstone-pipeline.zip` lên Customize > Skills (cần bật Code execution).

Phụ thuộc: Python 3.9+, pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib, openpyxl.

## Lịch sử
- 1.2.0: thêm skill `analytics-capstone-pipeline` (giải nén từ tệp .skill của nhóm, tệp gốc không giữ lại); rút mô tả còn 176 ký tự; sửa lỗi in tiếng Việt trên Windows (UTF-8);
  test trên 3 bộ dữ liệu (13/13 kiểm chứng mỗi bộ); hướng dẫn viết lại cho cả hai skill.
- 1.1.0: đổi tên skill từ `education-data-analytics` thành `student-risk-screening`, script `edu_analytics.py` thành `risk_screening.py`;
  tổ chức lại vào `.claude/`. Kết quả trong `evaluation/iteration-1/` được tạo với tên cũ (nội dung skill không đổi).
- 1.0.0: bản đầu, test trên 3 bộ dữ liệu và đánh giá có/không có skill.
