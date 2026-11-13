"""Kiểm tra và đóng gói bộ skill của nhóm N02 (plugin edu-analytics).

Nguồn duy nhất của mỗi skill: .claude/skills/<tên-skill>/ (Claude Code tự nạp khi mở dự án).
Script này dựng plugin + marketplace trong dist/_staging rồi nén:

  dist/<tên-skill>.zip              : mỗi skill một gói để tải lên claude.ai (Customize > Skills); thư mục skill ở cấp cao nhất, không kèm evals/
  dist/n02-skills-marketplace.zip   : marketplace cho Claude Code (giải nén rồi /plugin marketplace add ./n02-skills-marketplace)
  dist/checksums.txt                : SHA-256 của các gói

Chạy:  python .claude/skill-dev/packaging/build_package.py
"""
import hashlib
import json
import py_compile
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent                    # .claude/skill-dev/packaging
CLAUDE = HERE.parents[1]                                   # .claude
SKILLS = [CLAUDE / "skills" / n for n in ("student-risk-screening", "analytics-capstone-pipeline")]
MKT_SRC = HERE / "marketplace"                             # manifest marketplace + plugin (không chứa bản sao skill)
DIST = HERE / "dist"
STAGE = DIST / "_staging" / "n02-skills-marketplace"
SKIP_DIRS = {"__pycache__", "node_modules", ".pytest_cache"}
ALLOWED_FM = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
errors, warns = [], []


def frontmatter(md: Path):
    t = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        errors.append(f"{md}: thiếu YAML frontmatter"); return {}
    fm, cur = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z_-]+:", line):
            k, v = line.split(":", 1); cur = k.strip(); fm[cur] = v.strip()
        elif cur and line.startswith(" "):
            fm[cur] = (fm[cur] + " " + line.strip()).strip()
    return fm


def ignore(_, names):
    return [n for n in names if n in SKIP_DIRS or n.endswith(".pyc")]


def stage():
    if STAGE.parent.exists():
        shutil.rmtree(STAGE.parent)
    shutil.copytree(MKT_SRC, STAGE, ignore=ignore)
    plugin_dirs = [p for p in (STAGE / "plugins").iterdir() if p.is_dir()]
    assert len(plugin_dirs) == 1, plugin_dirs
    for sk in SKILLS:
        shutil.copytree(sk, plugin_dirs[0] / "skills" / sk.name, ignore=ignore)
    return plugin_dirs[0]


def validate(plugin):
    pj = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", pj.get("name", "")):
        errors.append("plugin.json: name phải là kebab-case")
    if re.match(r"^(claude-|anthropic-|anthropics-|cc-plugin-)", pj["name"]):
        errors.append("plugin.json: name dùng tiền tố bị cấm")
    if "name" not in pj.get("author", {}):
        errors.append("plugin.json: author phải là object có name")
    mk = json.loads((STAGE / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    for k in ("name", "owner", "plugins"):
        if k not in mk:
            errors.append(f"marketplace.json: thiếu {k}")
    for p in mk["plugins"]:
        src = p["source"]
        if not src.startswith("./") or ".." in src or not (STAGE / src).is_dir():
            errors.append(f"marketplace.json: source không hợp lệ {src}")
        elif p["name"] != json.loads((STAGE / src / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"]:
            errors.append("marketplace.json: tên plugin khác plugin.json")
    fms = [validate_skill(sk) for sk in SKILLS]
    return pj, fms


def validate_skill(sk):
    mds = [p for p in sk.rglob("SKILL.md") if p.relative_to(sk).parts[0] != "evals" and not SKIP_DIRS & set(p.parts)]
    if len(mds) != 1:
        errors.append(f"Skill phải có đúng một SKILL.md (thấy {len(mds)})")
    fm = frontmatter(sk / "SKILL.md")
    if set(fm) - ALLOWED_FM:
        errors.append(f"SKILL.md: khóa frontmatter không được claude.ai chấp nhận: {set(fm) - ALLOWED_FM}")
    name, desc = fm.get("name", ""), fm.get("description", "")
    if name != sk.name:
        errors.append("SKILL.md: name phải trùng tên thư mục")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name) or re.search(r"anthropic|claude", name):
        errors.append("SKILL.md: name không hợp lệ")
    if not desc or len(desc) > 1024 or "<" in desc:
        errors.append("SKILL.md: description rỗng, quá 1024 ký tự hoặc chứa thẻ XML")
    elif len(desc) > 200:
        warns.append(f"{sk.name}: description {len(desc)} ký tự (> 200, có thể bị claude.ai từ chối)")
    if len((sk / "SKILL.md").read_text(encoding="utf-8").splitlines()) > 500:
        warns.append(f"{sk.name}: SKILL.md dài hơn 500 dòng")
    for py in sk.rglob("*.py"):
        py_compile.compile(str(py), doraise=True)
    return fm


def zipdir(src: Path, zpath: Path, arc_root: str, exclude_top=()):
    files = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            rel = f.relative_to(src)
            if f.is_dir() or SKIP_DIRS & set(rel.parts) or f.suffix == ".pyc" or (rel.parts and rel.parts[0] in exclude_top):
                continue
            arc = f"{arc_root}/{rel.as_posix()}"
            z.write(f, arc); files.append(arc)
    return files


def main():
    DIST.mkdir(exist_ok=True)
    plugin = stage()
    pj, fms = validate(plugin)
    if errors:
        print("LỖI:\n- " + "\n- ".join(errors)); sys.exit(1)
    for old in DIST.glob("*.zip"):
        old.unlink()
    out, zips = {}, []
    for sk in SKILLS:
        a = DIST / f"{sk.name}.zip"
        fa = zipdir(sk, a, sk.name, exclude_top=("evals",))
        assert all(x.startswith(f"{sk.name}/") for x in fa) and f"{sk.name}/SKILL.md" in fa
        out[sk.name] = {"claude_ai_zip": a.name, "entries": len(fa)}
        zips.append(a)
    b = DIST / f"{STAGE.name}.zip"
    fb = zipdir(STAGE, b, STAGE.name)
    zips.append(b)
    shutil.rmtree(STAGE.parent)
    sums = [f"{hashlib.sha256(z.read_bytes()).hexdigest()}  {z.name}" for z in zips]
    (DIST / "checksums.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({"plugin": pj["name"], "version": pj["version"],
                      "skills": {fm["name"]: len(fm["description"]) for fm in fms}, "claude_ai_zips": out,
                      "marketplace_zip": {"file": b.name, "entries": len(fb)}, "warnings": warns}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
