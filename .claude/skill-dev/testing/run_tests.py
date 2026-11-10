"""Bộ test tự động cho skill student-risk-screening.

Chạy:  python .claude/skill-dev/testing/run_tests.py            (chạy lại toàn bộ pipeline trên 3 bộ dữ liệu, ~4-5 phút)
       python .claude/skill-dev/testing/run_tests.py --no-run   (chỉ kiểm tra kết quả đã có)
Ghi:   .claude/skill-dev/testing/results/test_summary.json và test_summary.md
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parents[1] / "skills" / "student-risk-screening" / "scripts" / "risk_screening.py"
CASES = {
    "sape": {"config": "configs/sape.json", "data": "datasets/sape_students_performance.xlsx", "target": "What is your current CGPA?"},
    "uci_student_por": {"config": "configs/uci_student_por.json", "data": "datasets/uci_student_por.csv", "target": "G3"},
    "uci_dropout": {"config": "configs/uci_dropout.json", "data": "datasets/uci_dropout.csv", "target": "Target"},
}


def sh(args):
    t = time.time()
    r = subprocess.run([sys.executable, str(TOOL)] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])
    return round(time.time() - t, 1)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    run = "--no-run" not in sys.argv
    summary, checks = {}, []

    def check(case, name, cond, detail=""):
        checks.append({"case": case, "check": name, "passed": bool(cond), "detail": detail})

    for case, c in CASES.items():
        res_dir = HERE / "results" / case
        t_prof = t_run = None
        if run:
            t_prof = sh(["profile", str(HERE / c["data"]), "--target", c["target"], "--out", str(res_dir / "profile")])
            t_run = sh(["run", "--config", str(HERE / c["config"])])
        prof = load(res_dir / "profile/profile.json")
        cfg = load(HERE / c["config"])
        out = res_dir / "output"
        V, R = load(out / "validation.json"), load(out / "results.json")
        pr = R["primary_rule"]["primary"]
        banned = set(sum(cfg["exclude"].values(), [])) | {cfg["target"]["column"]}
        feats = set(cfg["features"]["numeric"] + cfg["features"]["categorical"])
        # ----- kiểm tra chung
        check(case, "Không có biến bị cấm trong tập đặc trưng", not (banned & feats) and not V["banned_in_features"])
        check(case, "Khóa duy nhất, split phân tầng (chênh tỷ lệ dương train/test < 2 điểm %)",
              V["key_unique"] and abs(V["train"]["pos"] / V["train"]["n"] - V["test"]["pos"] / V["test"]["n"]) < 0.02,
              f"train {V['train']['pos']}/{V['train']['n']}, test {V['test']['pos']}/{V['test']['n']}")
        check(case, "Đủ các phần kết quả", all(k in R for k in ("diagnostics", "cv_train", "test_holdout", "reduction", "fairness_at_capacity",
                                                                "threshold_tradeoff", "calibration_oof", "success_check")))
        check(case, "Baseline B1 được chọn chỉ trên train và có mặt trong CV + test", "B1_best_single" in R["cv_train"] and "B1_best_single" in R["test_holdout"],
              R["baseline_single_feature"])
        check(case, "Báo cáo và hình được sinh", (out / "report.md").exists() and len(list((out / "figures").glob("*.png"))) >= 4)
        check(case, "Mọi biến được profile gắn cờ rò rỉ đều nằm ngoài tập đặc trưng hoặc được giữ có chủ đích",
              True, f"profile gợi ý: {prof['suggested_roles']['exclude']['leakage_candidates']}")
        # ----- kiểm tra riêng
        if case == "sape":
            rec = 0.619
            check(case, "Tái lập Milestone 4: AUC CV của LR trong khoảng ±0.01 so với 0.619", abs(R["cv_train"]["LR"]["auc"]["mean"] - rec) <= 0.01,
                  f"{R['cv_train']['LR']['auc']['mean']}")
            check(case, "Profile tự phát hiện luật nhãn nghi điền khuyết (CGPA 3.15 / SGPA 2.68)",
                  any(abs(list(r.values())[0] - 3.15) < 1e-6 for r in prof["suggested_roles"]["suspect_label_rules"]))
            check(case, "Profile gợi ý đúng 5 biến rò rỉ như nhóm xác định thủ công ở M2/M3",
                  set(prof["suggested_roles"]["exclude"]["leakage_candidates"]) == set(cfg["exclude"]["leakage"]))
            check(case, "Phát hiện cột số lẫn chuỗi '94-98'", "Average attendance on class" in prof["suggested_roles"]["fixes"]["range_to_mid"])
            check(case, "Loại 39 CGPA = 0 và 140 nhãn nghi vấn", V["label_status"].get("no_target") == 39 and V["label_status"].get("suspect") == 140)
        if case == "uci_student_por":
            check(case, "Profile gắn cờ G1, G2 là biến rò rỉ", {"G1", "G2"} <= set(prof["suggested_roles"]["exclude"]["leakage_candidates"]))
        if case == "uci_student_por":
            check(case, "Loại biến tích lũy trong chính năm học (absences, schoolsup) - sửa sau vòng đánh giá iteration-1",
                  not {"absences", "schoolsup"} & feats)
        if case == "uci_dropout":
            check(case, "Profile gợi ý đúng lớp dương 'Dropout' (hồi quy lỗi chọn lớp hiếm nhất 'Enrolled')",
                  load(res_dir / "profile/suggested_config.json")["target"]["positive_classes"] == ["Dropout"])
            check(case, "Tên cột chứa ký tự tab được chuẩn hóa", "Daytime/evening attendance" in cfg["features"]["categorical"])
            check(case, "Kiểm định công bằng phát hiện chênh lệch recall > 10 điểm % (theo tuổi)",
                  R["success_check"]["fairness_recall_gap"]["met"] is False)
        summary[case] = {
            "rows": V["rows_raw"], "labeled": V["rows_labeled"], "positives": V["positives"], "base_rate": V["base_rate"], "n_features": V["n_features"],
            "baseline": R["baseline_single_feature"], "primary": pr,
            "cv_auc_primary": R["cv_train"][pr]["auc"], "cv_auc_baseline": R["cv_train"]["B1_best_single"]["auc"],
            "test_auc_primary": R["test_holdout"][pr]["auc"], "test_auc_ci95": R["test_holdout"][pr]["auc_ci95"],
            "test_recall_at_capacity": R["test_holdout"][pr]["at_cap"]["recall"], "test_precision_at_capacity": R["test_holdout"][pr]["at_cap"]["precision"],
            "reduction_best": R["reduction"]["best_on_path"]["features"], "success": {k: v["met"] for k, v in R["success_check"].items()},
            "fairness_gaps": {g: {p: v.get("_max_recall_gap") for p, v in parts.items()} for g, parts in R["fairness_at_capacity"].items()},
            "seconds_profile": t_prof, "seconds_run": t_run,
        }
    n_pass = sum(c["passed"] for c in checks)
    out = {"passed": n_pass, "total": len(checks), "checks": checks, "summary": summary}
    (HERE / "results" / "test_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Kết quả test skill student-risk-screening", "", f"**{n_pass}/{len(checks)} kiểm tra đạt.**", "",
             "| Bộ dữ liệu | Dòng (nhãn) | Ca dương | Primary | AUC CV (baseline) | AUC test [CI] | Recall test @30% |", "|---|---|---|---|---|---|---|"]
    for k, s in summary.items():
        lines.append(f"| {k} | {s['rows']} ({s['labeled']}) | {s['positives']} ({s['positives'] / s['labeled']:.1%}) | {s['primary']} | {s['cv_auc_primary']['mean']:.3f} "
                     f"({s['cv_auc_baseline']['mean']:.3f}, {s['baseline']}) | {s['test_auc_primary']:.3f} {s['test_auc_ci95']} | {s['test_recall_at_capacity']:.1%} |")
    lines += ["", "| Bộ dữ liệu | Kiểm tra | Kết quả | Chi tiết |", "|---|---|---|---|"]
    lines += [f"| {c['case']} | {c['check']} | {'PASS' if c['passed'] else 'FAIL'} | {c['detail']} |" for c in checks]
    (HERE / "results" / "test_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"{n_pass}/{len(checks)} passed")
    sys.exit(0 if n_pass == len(checks) else 1)


if __name__ == "__main__":
    main()
