# Kết quả test skill student-risk-screening

**28/28 kiểm tra đạt.**

| Bộ dữ liệu | Dòng (nhãn) | Ca dương | Primary | AUC CV (baseline) | AUC test [CI] | Recall test @30% |
|---|---|---|---|---|---|---|
| sape | 1194 (1015) | 167 (16.5%) | LR | 0.620 (0.615, Average attendance on class) | 0.614 [0.502, 0.7239] | 48.5% |
| uci_student_por | 649 (649) | 100 (15.4%) | LR | 0.799 (0.665, failures) | 0.833 [0.7399, 0.9137] | 60.0% |
| uci_dropout | 4424 (4424) | 1421 (32.1%) | LR | 0.873 (0.810, Curricular units 1st sem (approved)) | 0.876 [0.8488, 0.8986] | 67.6% |

| Bộ dữ liệu | Kiểm tra | Kết quả | Chi tiết |
|---|---|---|---|
| sape | Không có biến bị cấm trong tập đặc trưng | PASS |  |
| sape | Khóa duy nhất, split phân tầng (chênh tỷ lệ dương train/test < 2 điểm %) | PASS | train 134/812, test 33/203 |
| sape | Đủ các phần kết quả | PASS |  |
| sape | Baseline B1 được chọn chỉ trên train và có mặt trong CV + test | PASS | Average attendance on class |
| sape | Báo cáo và hình được sinh | PASS |  |
| sape | Mọi biến được profile gắn cờ rò rỉ đều nằm ngoài tập đặc trưng hoặc được giữ có chủ đích | PASS | profile gợi ý: ['Do you have meritorious scholarship ?', 'Did you ever fall in probation?', 'Did you ever got suspension?', 'Do you attend in teacher consultancy for any kind of academical problems?', 'What was your previous SGPA?'] |
| sape | Tái lập Milestone 4: AUC CV của LR trong khoảng ±0.01 so với 0.619 | PASS | 0.6198 |
| sape | Profile tự phát hiện luật nhãn nghi điền khuyết (CGPA 3.15 / SGPA 2.68) | PASS |  |
| sape | Profile gợi ý đúng 5 biến rò rỉ như nhóm xác định thủ công ở M2/M3 | PASS |  |
| sape | Phát hiện cột số lẫn chuỗi '94-98' | PASS |  |
| sape | Loại 39 CGPA = 0 và 140 nhãn nghi vấn | PASS |  |
| uci_student_por | Không có biến bị cấm trong tập đặc trưng | PASS |  |
| uci_student_por | Khóa duy nhất, split phân tầng (chênh tỷ lệ dương train/test < 2 điểm %) | PASS | train 80/519, test 20/130 |
| uci_student_por | Đủ các phần kết quả | PASS |  |
| uci_student_por | Baseline B1 được chọn chỉ trên train và có mặt trong CV + test | PASS | failures |
| uci_student_por | Báo cáo và hình được sinh | PASS |  |
| uci_student_por | Mọi biến được profile gắn cờ rò rỉ đều nằm ngoài tập đặc trưng hoặc được giữ có chủ đích | PASS | profile gợi ý: ['G1', 'G2'] |
| uci_student_por | Profile gắn cờ G1, G2 là biến rò rỉ | PASS |  |
| uci_student_por | Loại biến tích lũy trong chính năm học (absences, schoolsup) - sửa sau vòng đánh giá iteration-1 | PASS |  |
| uci_dropout | Không có biến bị cấm trong tập đặc trưng | PASS |  |
| uci_dropout | Khóa duy nhất, split phân tầng (chênh tỷ lệ dương train/test < 2 điểm %) | PASS | train 1137/3539, test 284/885 |
| uci_dropout | Đủ các phần kết quả | PASS |  |
| uci_dropout | Baseline B1 được chọn chỉ trên train và có mặt trong CV + test | PASS | Curricular units 1st sem (approved) |
| uci_dropout | Báo cáo và hình được sinh | PASS |  |
| uci_dropout | Mọi biến được profile gắn cờ rò rỉ đều nằm ngoài tập đặc trưng hoặc được giữ có chủ đích | PASS | profile gợi ý: ['Previous qualification (grade)', 'Admission grade', 'Scholarship holder', 'Curricular units 1st sem (credited)', 'Curricular units 1st sem (evaluations)', 'Curricular units 1st sem (approved)', 'Curricular units 1st sem (grade)', 'Curricular units 1st sem (without evaluations)', 'Curricular units 2nd sem (credited)', 'Curricular units 2nd sem (enrolled)', 'Curricular units 2nd sem (evaluations)', 'Curricular units 2nd sem (approved)', 'Curricular units 2nd sem (grade)', 'Curricular units 2nd sem (without evaluations)'] |
| uci_dropout | Profile gợi ý đúng lớp dương 'Dropout' (hồi quy lỗi chọn lớp hiếm nhất 'Enrolled') | PASS |  |
| uci_dropout | Tên cột chứa ký tự tab được chuẩn hóa | PASS |  |
| uci_dropout | Kiểm định công bằng phát hiện chênh lệch recall > 10 điểm % (theo tuổi) | PASS |  |