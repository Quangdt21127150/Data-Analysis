"""Cấu hình dùng chung cho pipeline N02 (Milestone 3-5).

Mọi quyết định ở đây đều được ghi trong báo cáo Milestone 3 (Preparation Decision Matrix,
Data Lineage) và Controlled Change Log. Không sửa giá trị mà không cập nhật Change Log.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "Students_Performance_data_set.xlsx"
RAW_SHA256 = "04ebaf9f3a047afe96d9bff22dbe65b2a320e6395f230032735495e7e58277cf"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
META = ROOT / "data" / "metadata"
REPORTS = ROOT / "reports"

PREPARED_VERSION = "v1.0"
SEED = 2026
TEST_SIZE = 0.20

# Ngưỡng biến mục tiêu (chốt ở M3, quyết định DQ/PD-T1). 2.50 và 3.00 là kịch bản độ nhạy.
TARGET_THRESHOLD = 2.75
SENSITIVITY_THRESHOLDS = (2.50, 3.00)

# Tên cột gốc -> tên ngắn (thứ tự đúng như file gốc)
RENAME = {
    "University Admission year": "admission_year",
    "Gender": "gender",
    "Age": "age",
    "H.S.C passing year": "hsc_year",
    "Program": "program",
    "Current Semester": "current_semester",
    "Do you have meritorious scholarship ?": "merit_scholarship",
    "Do you use University transportation?": "uni_transport",
    "How many hour do you study daily?": "study_hours",
    "How many times do you seat for study in a day?": "study_sessions",
    "What is your preferable learning mode?": "learning_mode",
    "Do you use smart phone?": "smartphone",
    "Do you have personal Computer?": "personal_computer",
    "How many hour do you spent daily in social media?": "social_media_hours",
    "Status of your English language proficiency": "english_level",
    "Average attendance on class": "attendance_pct",
    "Did you ever fall in probation?": "probation_ever",
    "Did you ever got suspension?": "suspension_ever",
    "Do you attend in teacher consultancy for any kind of academical problems?": "teacher_consultancy",
    "What are the skills do you have ?": "skills_text",
    "How many hour do you spent daily on your skill development?": "skill_dev_hours",
    "What is you interested area?": "interest_area_text",
    "What is your relationship status?": "relationship_status",
    "Are you engaged with any co-curriculum activities?": "co_curricular",
    "With whom you are living with?": "living_with",
    "Do you have any health issues?": "health_issue",
    "What was your previous SGPA?": "prev_sgpa",
    "Do you have any physical disabilities?": "physical_disability",
    "What is your current CGPA?": "cgpa",
    "How many Credit did you have completed?": "credits_completed",
    "What is your monthly family income?": "family_income",
}

# ---- Vai trò biến -------------------------------------------------------------------------
HABIT_FEATURES = ["study_hours", "study_sessions", "attendance_pct", "social_media_hours", "skill_dev_hours"]  # AQ2
CONDITION_FEATURES = ["learning_mode", "personal_computer", "uni_transport", "english_level",
                      "co_curricular", "current_semester"]                                          # AQ3
MODEL_FEATURES = HABIT_FEATURES + CONDITION_FEATURES                                                # AQ4-AQ7
NUMERIC_FEATURES = HABIT_FEATURES + ["current_semester"]
BINARY_FEATURES = ["learning_mode", "personal_computer", "uni_transport", "co_curricular"]
ORDINAL_FEATURES = ["english_level"]

DIAGNOSTIC_ONLY = ["credits_completed", "smartphone", "teacher_consultancy"]   # không vào mô hình
LEAKAGE_BANNED = ["prev_sgpa", "probation_ever", "suspension_ever", "merit_scholarship", "teacher_consultancy"]
SENSITIVE_EXCLUDED = ["family_income", "health_issue", "physical_disability", "relationship_status"]
FAIRNESS_AUDIT = ["gender", "living_with"]
CONTEXT_EXCLUDED = ["age", "admission_year", "hsc_year", "program", "skills_text", "interest_area_text"]

BANNED_FROM_MODEL = sorted(set(LEAKAGE_BANNED + SENSITIVE_EXCLUDED + FAIRNESS_AUDIT + CONTEXT_EXCLUDED
                               + ["cgpa", "credits_completed", "smartphone"]))

ENGLISH_ORDER = {"Basic": 1, "Intermediate": 2, "Advanced": 3}
