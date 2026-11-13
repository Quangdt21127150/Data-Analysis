# -*- coding: utf-8 -*-
"""Bộ dựng tài liệu Word (python-docx) cho báo cáo học thuật: tiêu đề đánh số, bảng, chú thích, hình, mục lục, tham chiếu chéo, trích dẫn đánh số.

Ghi chú: mô-đun này chỉ phục vụ việc trình bày báo cáo; không chứa logic phân tích dữ liệu.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor, Twips

FONT = "Times New Roman"
HEADER_LEFT_LOGO = None    # đường dẫn logo trái (tùy chọn)
HEADER_RIGHT_LOGO = None   # đường dẫn logo phải (tùy chọn)
HEADER_TEXT = ""           # dòng chữ đầu trang (tùy chọn)
FOOTER_TEXT = "BÁO CÁO PHÂN TÍCH DỮ LIỆU"
BODY_PT = 13
LINE_SP = 1.15
HEAD_SCALE = 1.0
TABLE_PT = 11
BLUE_DARK = "1F4D78"
BLUE_MID = "2E74B5"
HDR_FILL = "DAE9F7"
HDR_TEXT = "1F4E79"
ZEBRA = "F2F2F2"
COVER_BLUE = "4F81BD"
CALLOUT_FILL = "EAF2FB"
BORDER = "BFBFBF"

PORTRAIT_W = 9026      # twips: A4 trừ lề 2,54 cm hai bên
LANDSCAPE_W = 13958

STATUS_FILL = {"GREEN": "C6E7C6", "YELLOW": "FFE9A8", "RED": "F7C1C1",
               "Ready": "C6E7C6", "Revise": "FFE9A8", "High": "F7C1C1", "Medium": "FFE9A8", "Low": "C6E7C6", "Đạt": "C6E7C6", "Còn mở": "FFE9A8", "Không đạt": "F7C1C1",
               "Answered": "C6E7C6", "Partial": "FFE9A8", "Deferred": "F7C1C1", "Dropped": "F7C1C1"}


def vi(x: float, nd: int = 1) -> str:
    """Định dạng số theo quy ước Việt Nam: dấu chấm phân tách nghìn, dấu phẩy thập phân."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float, nd: int = 1) -> str:
    return vi(x * 100, nd) + "%"


def _set_cell_shade(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def _set_cell_borders(cell, **kw) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge, (sz, color, val) in kw.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)


def _set_cell_margins(cell, top=50, bottom=50, left=90, right=90) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{k}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def _set_run_font(run, size=None, bold=None, italic=None, color=None, name=FONT, small_caps=None) -> None:
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(a), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if small_caps is not None:
        run.font.small_caps = small_caps


_MARK = re.compile(r"(\*\*.+?\*\*|__.+?__)")


def add_rich(par, text: str, size=None, color=None, bold=None, italic=None) -> None:
    """Chèn văn bản có định dạng nhẹ: **đậm** và __nghiêng__."""
    for tok in _MARK.split(text):
        if not tok:
            continue
        b, i = bold, italic
        if tok.startswith("**") and tok.endswith("**"):
            tok, b = tok[2:-2], True
        elif tok.startswith("__") and tok.endswith("__"):
            tok, i = tok[2:-2], True
        r = par.add_run(tok)
        _set_run_font(r, size=size, bold=b, italic=i, color=color)


def _field(par, instr: str, size=None, color=None, cached="1") -> None:
    def mk(t):
        r = par.add_run()
        _set_run_font(r, size=size, color=color)
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), t)
        r._element.append(el)
        return r
    mk("begin")
    r = par.add_run()
    _set_run_font(r, size=size, color=color)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r._element.append(it)
    mk("separate")
    r = par.add_run(cached)
    _set_run_font(r, size=size, color=color)
    mk("end")


TOC_L1 = 13
TOC_L2 = 12.5


class Report:
    def __init__(self, registry: dict | None = None, pages: dict | None = None):
        self.reg = registry or {}
        self.pages = pages or {}
        self.new_reg: dict = {"tab": {}, "fig": {}, "sec": {}, "ref": [], "refkeys": {}}
        self.toc: list = []
        self.n_h1 = 0
        self.n_h2 = 0
        self.n_tab = 0
        self.n_fig = 0
        self.d = Document()
        self._setup_styles()
        self._setup_page(self.d.sections[0])
        self._toc_anchor = None

    # ------------------------------------------------------------------ styles
    def _setup_styles(self) -> None:
        st = self.d.styles
        n = st["Normal"]
        n.font.name = FONT
        n.font.size = Pt(BODY_PT)
        n.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        n.element.rPr.rFonts.set(qn("w:cs"), FONT)
        pf = n.paragraph_format
        pf.space_after = Pt(6)
        pf.space_before = Pt(0)
        pf.line_spacing = LINE_SP
        for name, size, color, before, after, italic in (("Heading 1", 17, BLUE_DARK, 20, 8, False),
                                                         ("Heading 2", 14.5, BLUE_MID, 14, 6, False),
                                                         ("Heading 3", 13, BLUE_MID, 10, 4, True)):
            h = st[name]
            h.font.name = FONT
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.italic = italic
            h.font.color.rgb = RGBColor.from_string(color)
            rf = h.element.get_or_add_rPr().find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                h.element.get_or_add_rPr().insert(0, rf)
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), FONT)
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.paragraph_format.space_before = Pt(before * HEAD_SCALE)
            h.paragraph_format.space_after = Pt(after * HEAD_SCALE)
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.line_spacing = 1.1
        for nm in ("toc 1", "toc 2"):
            try:
                s = st[nm]
            except KeyError:
                s = st.add_style(nm, 1)
            s.base_style = st["Normal"]
            s.font.name = FONT
            s.font.size = Pt(13 if nm == "toc 1" else 12.5)
            s.font.bold = nm == "toc 1"
            s.paragraph_format.space_after = Pt(2 if nm == "toc 2" else 3)
            s.paragraph_format.space_before = Pt(5 if nm == "toc 1" else 0)
            s.paragraph_format.left_indent = Inches(0 if nm == "toc 1" else 0.3)
            s.paragraph_format.line_spacing = 1.05

    def _setup_page(self, sec, landscape: bool = False) -> None:
        sec.page_width = Twips(16838 if landscape else 11906)
        sec.page_height = Twips(11906 if landscape else 16838)
        sec.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
        sec.left_margin = sec.right_margin = Twips(1440)
        sec.top_margin = Twips(1700)
        sec.bottom_margin = Twips(1300)
        sec.header_distance = Twips(708)
        sec.footer_distance = Twips(500)
        self._build_hf(sec, LANDSCAPE_W if landscape else PORTRAIT_W)

    def _anchor_logo(self, par, path, x, y, cx, cy, crop_r=0) -> None:
        run = par.add_run()
        run.add_picture(path)
        inline = run._r.find(".//" + qn("wp:inline"))
        blip = inline.find(".//" + qn("a:blip"))
        rid = blip.get(qn("r:embed"))
        graphic = inline.find(qn("a:graphic"))
        pic = graphic.find(".//" + qn("pic:pic"))
        # đồng bộ kích thước ảnh trong khối pic
        if crop_r:
            from lxml import etree as _et
            bf = pic.find(qn("pic:blipFill"))
            sr = _et.Element(qn("a:srcRect")); sr.set("r", str(crop_r))
            bf.insert(1, sr)
        ext = pic.find(".//" + qn("a:ext"))
        ext.set("cx", str(cx)); ext.set("cy", str(cy))
        from lxml import etree
        WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        anchor = etree.SubElement(run._r.find(qn("w:drawing")), "{%s}anchor" % WP, nsmap={"wp": WP})
        for k, v in (("distT", "0"), ("distB", "0"), ("distL", "114300"), ("distR", "114300"), ("simplePos", "0"),
                     ("relativeHeight", "0"), ("behindDoc", "0"), ("locked", "0"), ("layoutInCell", "1"), ("allowOverlap", "1")):
            anchor.set(k, v)
        sp = etree.SubElement(anchor, "{%s}simplePos" % WP); sp.set("x", "0"); sp.set("y", "0")
        ph = etree.SubElement(anchor, "{%s}positionH" % WP); ph.set("relativeFrom", "column")
        etree.SubElement(ph, "{%s}posOffset" % WP).text = str(int(x))
        pv = etree.SubElement(anchor, "{%s}positionV" % WP); pv.set("relativeFrom", "paragraph")
        etree.SubElement(pv, "{%s}posOffset" % WP).text = str(int(y))
        e = etree.SubElement(anchor, "{%s}extent" % WP); e.set("cx", str(cx)); e.set("cy", str(cy))
        ee = etree.SubElement(anchor, "{%s}effectExtent" % WP)
        for k in "lrtb": ee.set(k, "0")
        etree.SubElement(anchor, "{%s}wrapNone" % WP)
        dp = etree.SubElement(anchor, "{%s}docPr" % WP); dp.set("id", str(100 + abs(hash(path)) % 900)); dp.set("name", path.split("/")[-1])
        anchor.append(graphic)
        inline.getparent().remove(inline)

    def _build_hf(self, sec, width: int) -> None:
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        hp = sec.header.paragraphs[0]
        for r in list(hp.runs):
            r._element.getparent().remove(r._element)
        hp.paragraph_format.tab_stops.add_tab_stop(Twips(width), WD_TAB_ALIGNMENT.RIGHT)
        hp.paragraph_format.space_after = Pt(0)
        # Logo neo theo đúng vị trí và kích thước của template Milestone 1 và 2
        import os
        if HEADER_LEFT_LOGO and os.path.exists(HEADER_LEFT_LOGO):
            self._anchor_logo(hp, HEADER_LEFT_LOGO, -571498, -278128, 2357438, 740651, crop_r=0)
        if HEADER_RIGHT_LOGO and os.path.exists(HEADER_RIGHT_LOGO):
            self._anchor_logo(hp, HEADER_RIGHT_LOGO, 5181600 + (width - PORTRAIT_W) * 635, -276223, 988060, 541655)
        if HEADER_TEXT:
            hr_ = hp.add_run(HEADER_TEXT)
            _set_run_font(hr_, size=10, color="595959")
        fp = sec.footer.paragraphs[0]
        for r in list(fp.runs):
            r._element.getparent().remove(r._element)
        fp.paragraph_format.tab_stops.add_tab_stop(Twips(width), WD_TAB_ALIGNMENT.RIGHT)
        pPr = fp._p.get_or_add_pPr()
        bd = OxmlElement("w:pBdr")
        top = OxmlElement("w:top")
        top.set(qn("w:val"), "single")
        top.set(qn("w:sz"), "18")
        top.set(qn("w:space"), "4")
        top.set(qn("w:color"), COVER_BLUE)
        bd.append(top)
        pPr.append(bd)
        r = fp.add_run(FOOTER_TEXT)
        _set_run_font(r, size=10, color="595959", small_caps=True)
        fp.add_run("\t")
        _field(fp, "PAGE", size=11, color="404040")

    # ------------------------------------------------------------- sections
    def new_section(self, landscape: bool = False) -> None:
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        self._setup_page(sec, landscape)
        self.width = LANDSCAPE_W if landscape else PORTRAIT_W

    width = PORTRAIT_W

    # ------------------------------------------------------------ headings
    def h1(self, text: str, key: str | None = None, numbered: bool = True, page_break: bool = True) -> None:
        if numbered:
            self.n_h1 += 1
            self.n_h2 = 0
            label = f"{self.n_h1}. {text}"
            if key:
                self.new_reg["sec"][key] = f"{self.n_h1}"
        else:
            label = text
            if key:
                self.new_reg["sec"][key] = text.split(".")[0]
        p = self.d.add_paragraph(style="Heading 1")
        if page_break:
            p.paragraph_format.page_break_before = True
        r = p.add_run(label.upper() if numbered else label)
        _set_run_font(r, size=17, bold=True, color=BLUE_DARK)
        pPr = p._p.get_or_add_pPr()
        bd = OxmlElement("w:pBdr")
        b = OxmlElement("w:bottom")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "8")
        b.set(qn("w:space"), "3")
        b.set(qn("w:color"), BLUE_MID)
        bd.append(b)
        pPr.append(bd)
        self.toc.append((1, label.upper() if numbered else label))

    def h2(self, text: str, key: str | None = None) -> None:
        self.n_h2 += 1
        label = f"{self.n_h1}.{self.n_h2}. {text}"
        if key:
            self.new_reg["sec"][key] = f"{self.n_h1}.{self.n_h2}"
        p = self.d.add_paragraph(style="Heading 2")
        r = p.add_run(label)
        _set_run_font(r, size=14.5, bold=True, color=BLUE_MID)
        self.toc.append((2, label))

    def h3(self, text: str) -> None:
        p = self.d.add_paragraph(style="Heading 3")
        r = p.add_run(text)
        _set_run_font(r, size=13, bold=True, italic=True, color=BLUE_MID)

    # ----------------------------------------------------------- references
    def S(self, key: str) -> str:
        return "Mục " + self.reg.get("sec", {}).get(key, "?")

    def T(self, key: str) -> str:
        return "Bảng " + str(self.reg.get("tab", {}).get(key, "?"))

    def F(self, key: str) -> str:
        return "Hình " + str(self.reg.get("fig", {}).get(key, "?"))

    def C(self, *keys: str) -> str:
        """Trích dẫn tài liệu tham khảo theo thứ tự xuất hiện đầu tiên."""
        out = []
        for k in keys:
            if k not in self.new_reg["refkeys"]:
                self.new_reg["ref"].append(k)
                self.new_reg["refkeys"][k] = len(self.new_reg["ref"])
            n = self.reg.get("refkeys", {}).get(k, self.new_reg["refkeys"][k])
            out.append(str(n))
        return "[" + ", ".join(out) + "]"

    # ------------------------------------------------------------ paragraphs
    def p(self, text: str, align: str = "j", size: float | None = None, italic=None, bold=None, after: float | None = None,
          before: float | None = None, keep_next: bool = False, indent: float | None = None, color: str | None = None):
        par = self.d.add_paragraph()
        par.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                         "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if after is not None:
            par.paragraph_format.space_after = Pt(after)
        if before is not None:
            par.paragraph_format.space_before = Pt(before)
        if indent is not None:
            par.paragraph_format.left_indent = Inches(indent)
        par.paragraph_format.keep_with_next = keep_next
        add_rich(par, text, size=size, italic=italic, bold=bold, color=color)
        return par

    def bullets(self, items: list[str], size: float | None = None, indent: float = 0.25) -> None:
        for it in items:
            par = self.d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            par.paragraph_format.left_indent = Inches(indent + 0.22)
            par.paragraph_format.first_line_indent = Inches(-0.22)
            par.paragraph_format.space_after = Pt(3)
            r = par.add_run("•\t")
            _set_run_font(r, size=size)
            par.paragraph_format.tab_stops.add_tab_stop(Inches(indent + 0.22))
            add_rich(par, it, size=size)

    def numbered(self, items: list[str], size: float | None = None) -> None:
        for i, it in enumerate(items, 1):
            par = self.d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            par.paragraph_format.left_indent = Inches(0.5)
            par.paragraph_format.first_line_indent = Inches(-0.28)
            par.paragraph_format.space_after = Pt(3)
            par.paragraph_format.tab_stops.add_tab_stop(Inches(0.5))
            r = par.add_run(f"{i}.\t")
            _set_run_font(r, size=size)
            add_rich(par, it, size=size)

    def pagebreak(self) -> None:
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def spacer(self, pts: float = 6) -> None:
        par = self.d.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing = Pt(pts)

    # ---------------------------------------------------------------- tables
    def caption(self, kind: str, key: str, text: str, keep_next: bool = False) -> None:
        if kind == "tab":
            self.n_tab += 1
            n = self.n_tab
            self.new_reg["tab"][key] = n
            label = f"Bảng {n}. "
        else:
            self.n_fig += 1
            n = self.n_fig
            self.new_reg["fig"][key] = n
            label = f"Hình {n}. "
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_before = Pt(4)
        par.paragraph_format.space_after = Pt(12)
        par.paragraph_format.keep_with_next = keep_next
        r = par.add_run(label)
        _set_run_font(r, size=11.5, bold=True, italic=True, color="404040")
        add_rich(par, text, size=11.5, italic=True, color="404040")

    def table(self, headers: list[str], rows: list[list], widths: list[int], key: str, caption: str, align: list[str] | None = None,
              fs: float = TABLE_PT, zebra: bool = True, status_cols: list[int] | None = None, bold_first_col: bool = False,
              total_row: bool = False, caption_above: bool = False, keep: bool = False) -> None:
        assert abs(sum(widths) - self.width) < 40, f"Tổng độ rộng cột {sum(widths)} khác {self.width} ({key})"
        if caption_above:
            self.caption("tab", key, caption, keep_next=True)
        t = self.d.add_table(rows=1, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)
        tw = tblPr.find(qn("w:tblW"))
        if tw is None:
            tw = OxmlElement("w:tblW")
            tblPr.append(tw)
        tw.set(qn("w:w"), str(sum(widths)))
        tw.set(qn("w:type"), "dxa")
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(w))
        align = align or ["l"] * len(headers)
        amap = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT,
                "j": WD_ALIGN_PARAGRAPH.LEFT}

        def fill(cell, content, w, hdr=False, shade=None, al="l", bold=False):
            cell.width = Twips(w)
            _set_cell_margins(cell)
            _set_cell_borders(cell, top=(4, BORDER, "single"), bottom=(4, BORDER, "single"), left=(4, BORDER, "single"),
                              right=(4, BORDER, "single"))
            if shade:
                _set_cell_shade(cell, shade)
            cell.vertical_alignment = 1 if hdr else 0
            parts = content if isinstance(content, list) else [content]
            for k, part in enumerate(parts):
                par = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                par.paragraph_format.space_after = Pt(2 if len(parts) > 1 else 0)
                par.paragraph_format.space_before = Pt(0)
                par.paragraph_format.line_spacing = 1.08
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER if hdr else amap[al]
                add_rich(par, str(part), size=fs, color=HDR_TEXT if hdr else None, bold=True if (hdr or bold) else None)

        hr = t.rows[0]
        trPr = hr._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
        for c, h, w in zip(hr.cells, headers, widths):
            fill(c, h, w, hdr=True, shade=HDR_FILL)
        for ri, row in enumerate(rows):
            r = t.add_row()
            trPr = r._tr.get_or_add_trPr()
            trPr.append(OxmlElement("w:cantSplit"))
            for ci, (c, v, w) in enumerate(zip(r.cells, row, widths)):
                shade = ZEBRA if (zebra and ri % 2 == 1) else None
                txt = v[0] if isinstance(v, list) and len(v) == 1 else v
                if status_cols and ci in status_cols:
                    base = txt[0] if isinstance(txt, list) else txt
                    token = str(base).replace("**", "").split()[0] if base else ""
                    if token in STATUS_FILL:
                        shade = STATUS_FILL[token]
                is_total = total_row and ri == len(rows) - 1
                fill(c, v, w, shade=shade if not is_total else HDR_FILL, al=align[ci],
                     bold=(bold_first_col and ci == 0) or is_total)
        if keep:
            for row_ in t.rows[:-1]:
                for cell_ in row_.cells:
                    for par_ in cell_.paragraphs:
                        par_.paragraph_format.keep_with_next = True
        if not caption_above:
            self.caption("tab", key, caption)
        else:
            self.spacer(8)

    def kv_table(self, rows: list[tuple[str, str]], widths: list[int], head: tuple[str, str], fs: float = 12.5) -> None:
        t = self.d.add_table(rows=1, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)
        for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(w))

        def put(cell, text, w, hdr=False, italic=False):
            cell.width = Twips(w)
            _set_cell_margins(cell, 70, 70, 100, 100)
            _set_cell_borders(cell, top=(4, BORDER, "single"), bottom=(4, BORDER, "single"), left=(4, BORDER, "single"),
                              right=(4, BORDER, "single"))
            if hdr:
                _set_cell_shade(cell, HDR_FILL)
            lines = text if isinstance(text, list) else [text]
            for k, ln in enumerate(lines):
                par = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.line_spacing = 1.08
                add_rich(par, ln, size=fs, color=HDR_TEXT if hdr else None, bold=True if hdr else None, italic=italic or None)
        put(t.rows[0].cells[0], head[0], widths[0], hdr=True)
        put(t.rows[0].cells[1], head[1], widths[1], hdr=True)
        for k, v in rows:
            r = t.add_row()
            put(r.cells[0], k, widths[0])
            put(r.cells[1], v, widths[1])
        self.spacer(8)

    # -------------------------------------------------------------- callout
    def callout(self, title: str, lines: list[str], fill: str = CALLOUT_FILL, bar: str = BLUE_MID, size: float = 12.5) -> None:
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        c = t.rows[0].cells[0]
        c.width = Twips(self.width)
        t._tbl.tblGrid.findall(qn("w:gridCol"))[0].set(qn("w:w"), str(self.width))
        _set_cell_shade(c, fill)
        _set_cell_margins(c, 90, 90, 160, 140)
        _set_cell_borders(c, left=(36, bar, "single"), top=(4, fill, "single"), bottom=(4, fill, "single"), right=(4, fill, "single"))
        par = c.paragraphs[0]
        par.paragraph_format.space_after = Pt(3)
        add_rich(par, title, size=size + 0.5, bold=True, color=HDR_TEXT)
        for ln in lines:
            q = c.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            q.paragraph_format.space_after = Pt(3)
            q.paragraph_format.line_spacing = 1.1
            add_rich(q, ln, size=size)
        trPr = t.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        self.spacer(8)

    # --------------------------------------------------------------- figures
    def figure(self, path: str, key: str, caption: str, width_in: float = 6.1) -> None:
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.space_after = Pt(2)
        par.add_run().add_picture(path, width=Inches(width_in))
        self.caption("fig", key, caption)

    # ------------------------------------------------------------------- toc
    def toc_placeholder(self) -> None:
        """Đánh dấu vị trí chèn mục lục; nội dung được dựng ở lượt cuối bằng insert_toc()."""
        self._toc_anchor = self.d.add_paragraph()

    def insert_toc(self) -> None:
        anchor = self._toc_anchor
        entries = self.toc
        width = PORTRAIT_W
        paras = []
        for i, (lvl, text) in enumerate(entries):
            par = copy.deepcopy(anchor._p)
            anchor._p.addprevious(par)
            from docx.text.paragraph import Paragraph
            P = Paragraph(par, anchor._parent)
            P.style = self.d.styles["toc 1" if lvl == 1 else "toc 2"]
            P.paragraph_format.tab_stops.add_tab_stop(Twips(width), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if i == 0:
                self._fld_run(P, "begin")
                self._instr_run(P, ' TOC \\o "1-2" \\h \\z \\u ')
                self._fld_run(P, "separate")
            r = P.add_run(text)
            _set_run_font(r, size=TOC_L1 if lvl == 1 else TOC_L2, bold=lvl == 1)
            r = P.add_run("\t" + str(self.pages.get(text, "")))
            _set_run_font(r, size=TOC_L1 if lvl == 1 else TOC_L2, bold=lvl == 1)
            if i == len(entries) - 1:
                self._fld_run(P, "end")
        anchor._p.getparent().remove(anchor._p)

    def _fld_run(self, par, t: str) -> None:
        r = par.add_run()
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), t)
        r._element.append(el)

    def _instr_run(self, par, instr: str) -> None:
        r = par.add_run()
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = instr
        r._element.append(it)

    def save(self, path: str) -> None:
        self.d.core_properties.language = "vi-VN"
        self.d.save(path)


# --------------------------------------------------------------------------------------------
# Dựng nhiều lượt: đánh số bảng, hình, mục ổn định rồi điền số trang mục lục
# --------------------------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().upper()


def _heading_pages(docx_path: str, toc: list, workdir: Path):
    """Đổi sang PDF bằng LibreOffice rồi tìm trang của từng tiêu đề. Trả về ({}, 0) nếu không có soffice."""
    import shutil
    import subprocess
    if shutil.which("soffice") is None or shutil.which("pdftotext") is None:
        return {}, 0
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(workdir), str(docx_path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = workdir / (Path(docx_path).stem + ".pdf")
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    texts = [_norm(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"], capture_output=True, text=True).stdout)
             for i in range(1, n + 1)]
    pages, prev = {}, 1
    for lvl, label in toc:
        key = _norm(label)
        found = [i + 1 for i, t in enumerate(texts) if key in t and ".........." not in t and i + 1 >= prev]
        pages[label] = found[0] if found else ""
        if found:
            prev = found[0]
    return pages, n


def build_with_toc(build_fn, out_path: str, workdir: str = "/tmp/docx_kit_work"):
    """build_fn(registry, pages) -> Report đã dựng xong (đã gọi save). Trả về (Report cuối, số trang).

    Lượt 1 và 2 ổn định số bảng, hình, mục và thứ tự trích dẫn; các lượt sau điền số trang vào mục lục.
    """
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    tmp = str(wd / "pass.docx")
    r0 = build_fn({}, {}, tmp)
    r1 = build_fn(r0.new_reg, {}, tmp)
    reg, pages, n = r1.new_reg, {}, 0
    r2 = r1
    for _ in range(4):
        r2 = build_fn(reg, pages, tmp)
        newp, n = _heading_pages(tmp, r2.toc, wd)
        if newp == pages:
            break
        pages = newp
    r3 = build_fn(r2.new_reg, pages, out_path)
    return r3, n
