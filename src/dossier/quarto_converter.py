"""
Quarto Document Converter & Typography Engine.
Converts Markdown analysis reports and dossiers into court-admissible Word (.docx)
and PDF (.pdf) documents utilizing Quarto with official Thai government fonts:
- Primary Font: TH Sarabun New (Text, Headings, Tables)
- Equations & Mathematical Symbols: Cambria Math / STIX Two Math
- Monospace / Code Blocks: Consolas / Cascadia Code
- Diagram Rendering: Headless Chrome / Edge Mermaid image compilation
"""

from __future__ import annotations
import os
import re
import sys
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List


MAIN_FONT = "TH Sarabun New"
DOCX_MATH_FONT = "Cambria Math"
TYPST_MATH_FONT = "STIX Two Math"
CODE_FONT = "Consolas"

# Directory constants
TEMPLATES_DIR = Path("templates")
FONTS_DIR = Path("fonts")


class QuartoNotInstalledError(RuntimeError):
    """Raised when Quarto is not found on the host system."""
    def __init__(self, message: str = "Quarto CLI is not installed or not found in system PATH."):
        super().__init__(message)


def get_quarto_bin() -> Optional[str]:
    """Finds Quarto executable in PATH or standard installation directories."""
    q = shutil.which("quarto")
    if q:
        return q
    default_candidates = [
        Path(r"C:\Program Files\Quarto\bin\quarto.exe"),
        Path(r"C:\Program Files (x86)\Quarto\bin\quarto.exe"),
        Path(os.path.expanduser(r"~\AppData\Local\Programs\Quarto\bin\quarto.exe")),
    ]
    for cand in default_candidates:
        if cand.exists():
            bin_dir = str(cand.parent)
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return str(cand)
    return None


def is_quarto_installed() -> bool:
    """Checks whether the Quarto CLI executable is available in PATH or standard paths."""
    return get_quarto_bin() is not None


def get_quarto_version() -> Optional[str]:
    """Retrieves the installed Quarto version, or None if not installed."""
    qb = get_quarto_bin()
    if not qb:
        return None
    try:
        res = subprocess.run(
            [qb, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def ensure_docx_reference_template(template_path: Optional[Path] = None, landscape: bool = False) -> Path:
    """
    Creates or ensures a Word reference document (.docx) with TH Sarabun New
    as the primary font (Normal, Headings, Tables) and Cambria Math for equations.
    Supports landscape orientation when landscape=True.
    """
    if template_path is None:
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        template_name = "custom-reference-landscape.docx" if landscape else "custom-reference.docx"
        template_path = TEMPLATES_DIR / template_name

    if template_path.exists() and template_path.stat().st_size > 5000:
        return template_path

    # Step 1: Export base pandoc reference doc
    raw_ref = TEMPLATES_DIR / "pandoc-base-reference.docx"
    try:
        subprocess.run(
            [get_quarto_bin() or "quarto", "pandoc", "-o", str(raw_ref), "--print-default-data-file", "reference.docx"],
            check=True,
            capture_output=True,
            timeout=15,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to extract base pandoc reference doc: {exc}") from exc

    # Step 2: Inject TH Sarabun New into styles.xml and theme1.xml
    with zipfile.ZipFile(raw_ref, "r") as zin:
        with zipfile.ZipFile(template_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename == "word/styles.xml":
                    xml_str = data.decode("utf-8")
                    # Replace standard fonts with TH Sarabun New
                    for old_f in ["Calibri Light", "Calibri", "Times New Roman", "Arial"]:
                        xml_str = xml_str.replace(f'w:ascii="{old_f}"', f'w:ascii="{MAIN_FONT}"')
                        xml_str = xml_str.replace(f'w:hAnsi="{old_f}"', f'w:hAnsi="{MAIN_FONT}"')
                        xml_str = xml_str.replace(f'w:cs="{old_f}"', f'w:cs="{MAIN_FONT}"')
                        xml_str = xml_str.replace(f'w:eastAsia="{old_f}"', f'w:eastAsia="{MAIN_FONT}"')

                    # Ensure complex script font is set to TH Sarabun New across rFonts
                    xml_str = re.sub(r'w:asciiTheme="[^"]+"', f'w:ascii="{MAIN_FONT}"', xml_str)
                    xml_str = re.sub(r'w:hAnsiTheme="[^"]+"', f'w:hAnsi="{MAIN_FONT}"', xml_str)
                    xml_str = re.sub(r'w:cstheme="[^"]+"', f'w:cs="{MAIN_FONT}"', xml_str)

                    # Enforce minimum 14pt (28 half-points) in docDefaults and all styles
                    xml_str = re.sub(r'(<w:rPrDefault>\s*<w:rPr>.*?<w:sz\s+w:val=")\d+(")', r'\g<1>28\g<2>', xml_str, flags=re.DOTALL)
                    xml_str = re.sub(r'(<w:rPrDefault>\s*<w:rPr>.*?<w:szCs\s+w:val=")\d+(")', r'\g<1>28\g<2>', xml_str, flags=re.DOTALL)
                    
                    def _raise_sz(m: re.Match) -> str:
                        tag, val, suffix = m.group(1), int(m.group(2)), m.group(3)
                        return f'{tag}"{max(val, 28)}"{suffix}'

                    xml_str = re.sub(r'(<w:sz\s+w:val=)"(\d+)"([^>]*>)', _raise_sz, xml_str)
                    xml_str = re.sub(r'(<w:szCs\s+w:val=)"(\d+)"([^>]*>)', _raise_sz, xml_str)

                    # Enforce solid table grid borders on Table style
                    table_border_xml = (
                        '<w:tblBorders>'
                        '<w:top w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
                        '<w:left w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
                        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
                        '<w:right w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
                        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
                        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
                        '</w:tblBorders>'
                    )
                    if "<w:tblBorders>" in xml_str:
                        xml_str = re.sub(r'<w:tblBorders>.*?</w:tblBorders>', table_border_xml, xml_str, flags=re.DOTALL)
                    else:
                        xml_str = re.sub(r'(<w:style\s+w:type="table"[^>]*w:styleId="Table"[^>]*>.*?<w:tblPr>)', r'\g<1>' + table_border_xml, xml_str, flags=re.DOTALL)

                    data = xml_str.encode("utf-8")

                elif item.filename == "word/theme/theme1.xml":
                    xml_str = data.decode("utf-8")
                    # Update theme font scheme for major and minor fonts
                    xml_str = re.sub(r'typeface="Calibri Light"', f'typeface="{MAIN_FONT}"', xml_str)
                    xml_str = re.sub(r'typeface="Calibri"', f'typeface="{MAIN_FONT}"', xml_str)
                    xml_str = re.sub(r'typeface="Times New Roman"', f'typeface="{MAIN_FONT}"', xml_str)
                    data = xml_str.encode("utf-8")

                zout.writestr(item, data)

    # Clean up intermediate raw ref
    if raw_ref.exists():
        raw_ref.unlink(missing_ok=True)

    # Step 3: If landscape requested, modify page orientation via docx
    if landscape:
        try:
            import docx
            d = docx.Document(str(template_path))
            if d.sections:
                s = d.sections[0]
                s.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
                s.page_width = docx.shared.Mm(297)
                s.page_height = docx.shared.Mm(210)
                d.save(str(template_path))
        except Exception:
            pass

    return template_path


def _apply_beneficiary_table_widths(tbl, is_landscape: bool) -> None:
    """
    Applies custom column widths to the Top Beneficiaries Ledger table:
    Minimizes 'ลำดับ' (Col 0) and 'สัดส่วน' down to ~6 characters,
    allocating the remaining width to account names, banks, channels, and amounts.
    Supports both 7-column (without recommended action) and 8-column variants.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    col_count = len(tbl.columns)
    if col_count == 7:
        # 7 columns: [ลำดับ, ธนาคาร/เลขบัญชี, ชื่อบัญชีปลายทาง, ช่องทาง, ยอดเงินออก (฿), สิทธิขอคืน (฿), สัดส่วน]
        # Landscape total ~10.5 in, Portrait total ~7.15 in
        if is_landscape:
            widths = [0.50, 1.80, 2.70, 1.20, 1.80, 1.80, 0.70]
        else:
            widths = [0.45, 1.25, 1.70, 0.85, 1.15, 1.20, 0.55]
    elif col_count == 8:
        # 8 columns variant (with recommended action)
        if is_landscape:
            widths = [0.50, 1.50, 2.10, 1.00, 1.40, 1.40, 0.70, 1.90]
        else:
            widths = [0.45, 1.05, 1.25, 0.70, 0.95, 0.95, 0.55, 1.25]
    else:
        return

    grids = tbl._tbl.xpath(".//w:tblGrid")
    if grids:
        grid = grids[0]
        for col_elem in list(grid.xpath(".//w:gridCol")):
            grid.remove(col_elem)
        for w in widths:
            col = OxmlElement("w:gridCol")
            col.set(qn("w:w"), str(int(w * 1440)))
            grid.append(col)

    for r in tbl.rows:
        for i, c in enumerate(r.cells):
            tcPr = c._tc.get_or_add_tcPr()
            tcW = tcPr.xpath(".//w:tcW")
            if tcW:
                node = tcW[0]
            else:
                node = OxmlElement("w:tcW")
                tcPr.append(node)
            node.set(qn("w:w"), str(int(widths[i] * 1440)))
            node.set(qn("w:type"), "dxa")


def _post_process_landscape_docx(docx_path: Union[str, Path]) -> None:
    """
    Optimizes landscape DOCX document to visually align with PDF landscape layout:
    1. Sets standard 1.5cm page margins (top, bottom, left, right).
    2. Removes duplicated Title paragraph if Heading 1 immediately follows with the same text.
    3. Resizes embedded Sankey / topology diagram images to 9.0 x 4.0 inches, ensuring
       Page 1 content fits completely within printable height without premature page spill.
    4. Compacts vertical paragraph spacing (space_before / space_after) on Page 1 and Table heading.
    5. Inserts a clean page break before Section 2 / Table header so the table starts neatly on Page 2.
    6. Compacts table cell padding, enables w:cantSplit on table rows, minimizes Col 0 & Col 6 widths,
       and repeats header row, guaranteeing seamless multi-page continuation.
    """
    try:
        import docx
        from docx.shared import Inches, Cm, Pt
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        doc = docx.Document(str(docx_path))
        if not doc.sections:
            return

        # 1. Margins: 1.5 cm all around
        for sec in doc.sections:
            sec.top_margin = Cm(1.5)
            sec.bottom_margin = Cm(1.5)
            sec.left_margin = Cm(1.5)
            sec.right_margin = Cm(1.5)

        # 2. Remove duplicated Title if followed by Heading 1
        if len(doc.paragraphs) >= 2:
            p0 = doc.paragraphs[0]
            p1 = doc.paragraphs[1]
            if p0.style.name.lower() == "title" and p0.text.strip() == p1.text.strip():
                p0._p.getparent().remove(p0._p)

        # 3. Resize embedded diagram images to fit safely within Page 1 (9.0 x 4.0 inches)
        for inline in doc.inline_shapes:
            try:
                inline.width = Inches(9.0)
                inline.height = Inches(4.0)
            except Exception:
                pass

        # 4. Compact vertical spacing on Page 1 paragraphs & center alignment
        page1_end_idx = 0
        for i, p in enumerate(doc.paragraphs):
            if "สรุปปลายทางผู้รับผลประโยชน์หลัก" in p.text or "Top Beneficiaries Ledger" in p.text:
                page1_end_idx = i
                break

        for p in doc.paragraphs[:page1_end_idx]:
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.0
            if p.runs and any(r._r.xpath('.//a:blip') for r in p.runs):
                p.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER
            elif p.style.name.lower() in ("image caption", "captioned figure"):
                p.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER

        # 5. Insert clean page break before the top beneficiaries ledger table & compact heading
        for p in doc.paragraphs:
            if "สรุปปลายทางผู้รับผลประโยชน์หลัก" in p.text or "Top Beneficiaries Ledger" in p.text:
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.0
                if not p._p.xpath('.//w:br[@w:type="page"]'):
                    br = OxmlElement("w:br")
                    br.set(qn("w:type"), "page")
                    p._p.insert(0, br)
                break

        # 6. Format table: compact cell padding, cantSplit rows, column widths, center alignment, repeat header
        for tbl in doc.tables:
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            _apply_beneficiary_table_widths(tbl, is_landscape=True)
            for r in tbl.rows:
                trPr = r._tr.get_or_add_trPr()
                if not trPr.xpath('./w:cantSplit'):
                    trPr.append(OxmlElement('w:cantSplit'))
                for c in r.cells:
                    tcPr = c._tc.get_or_add_tcPr()
                    tcMar = OxmlElement('w:tcMar')
                    for side in ('top', 'bottom'):
                        node = OxmlElement(f'w:{side}')
                        node.set(qn('w:w'), '40')
                        node.set(qn('w:type'), 'dxa')
                        tcMar.append(node)
                    tcPr.append(tcMar)
                    for cp in c.paragraphs:
                        cp.paragraph_format.space_before = Pt(1)
                        cp.paragraph_format.space_after = Pt(1)
                        cp.paragraph_format.line_spacing = 1.0
            if tbl.rows:
                header_trPr = tbl.rows[0]._tr.get_or_add_trPr()
                if not header_trPr.xpath("./w:tblHeader"):
                    header_trPr.append(OxmlElement("w:tblHeader"))

        doc.save(str(docx_path))
    except Exception:
        pass


def _ensure_docx_table_borders(docx_path: Union[str, Path]) -> None:
    """Injects explicit table borders into every table in the document XML."""
    target_path = Path(docx_path)
    if not target_path.exists():
        return

    with zipfile.ZipFile(target_path, "r") as zin:
        entries = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    if "word/document.xml" not in entries:
        return

    doc_xml = entries["word/document.xml"].decode("utf-8")
    border_tag = (
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '</w:tblBorders>'
    )

    def repl_tbl_pr(m: re.Match) -> str:
        tbl_pr = m.group(0)
        if "<w:tblBorders>" in tbl_pr:
            return re.sub(r"<w:tblBorders>.*?</w:tblBorders>", border_tag, tbl_pr, flags=re.DOTALL)
        return tbl_pr[:-10] + border_tag + "</w:tblPr>"

    doc_xml_mod = re.sub(r"<w:tblPr>.*?</w:tblPr>", repl_tbl_pr, doc_xml, flags=re.DOTALL)
    entries["word/document.xml"] = doc_xml_mod.encode("utf-8")

    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in entries.items():
            zout.writestr(fname, data)


def transform_mermaid_blocks(markdown_content: str) -> str:
    """
    Transforms standard Markdown mermaid blocks (```mermaid) or existing ({mermaid})
    into Quarto computational chunks with:
    1. Mandatory font: TH Sarabun New for Thai language labels
    2. Explicit page constraint: fig-width: 6.5 (inches) and layout-align: center
       to prevent diagram overflowing page boundaries in PDF/DOCX.
    """
    pattern = re.compile(r"```(?:\{mermaid\}|[ \t]*mermaid\b)(.*?)(?=```)", re.DOTALL | re.IGNORECASE)

    def replacer(match: re.Match) -> str:
        body = match.group(1).lstrip("\r\n")

        headers: List[str] = []
        if "fig-width" not in body:
            headers.append("%%| fig-width: 6.5")
        if "layout-align" not in body:
            headers.append("%%| layout-align: center")
        if "%%{init:" not in body:
            headers.append('%%{init: { "theme": "default", "themeVariables": { "fontFamily": "TH Sarabun New, Tahoma, sans-serif", "fontSize": "16px" } }}%%')

        header_str = "\n".join(headers) + "\n" if headers else ""
        return "```{mermaid}\n" + header_str + body

    return pattern.sub(replacer, markdown_content)


def generate_frontmatter(
    title: str,
    output_format: str,
    reference_doc: Optional[Path] = None,
    toc: bool = True,
    toc_depth: int = 3,
    landscape: bool = False,
) -> str:
    """Generates YAML frontmatter configured with TH Sarabun New and mathematical font settings."""
    if output_format.lower() == "docx":
        ref_path = reference_doc.resolve().as_posix() if reference_doc else "templates/custom-reference.docx"
        return (
            "---\n"
            f'title: "{title}"\n'
            "format:\n"
            "  docx:\n"
            f'    reference-doc: "{ref_path}"\n'
            f"    toc: {'true' if toc else 'false'}\n"
            f"    toc-depth: {toc_depth}\n"
            "    number-sections: false\n"
            "---\n\n"
        )
    elif output_format.lower() in ("pdf", "typst"):
        typst_include = [
            '        #set text(size: 14pt, font: "TH Sarabun New")',
            "        #show table: set text(size: 14pt)",
            "        #set table(stroke: 0.5pt + rgb(148, 163, 184))",
            '        #show image: set image(width: 100%, height: auto, fit: "contain")',
        ]
        if landscape:
            typst_include.insert(0, '        #set page(paper: "a4", flipped: true)')
        include_str = "\n".join(typst_include)

        margin_x = "1.5cm" if landscape else "2cm"
        margin_y = "1.5cm" if landscape else "2cm"

        return (
            "---\n"
            f'title: "{title}"\n'
            "format:\n"
            "  typst:\n"
            f'    mainfont: "{MAIN_FONT}"\n'
            f'    mathfont: "{TYPST_MATH_FONT}"\n'
            "    fontsize: 14pt\n"
            "    papersize: a4\n"
            f"    toc: {'true' if toc else 'false'}\n"
            f"    toc-depth: {toc_depth}\n"
            "    margin:\n"
            f"      x: {margin_x}\n"
            f"      y: {margin_y}\n"
            "    include-before:\n"
            "      - |\n"
            f"{include_str}\n"
            "---\n\n"
        )
    else:
        raise ValueError(f"Unsupported format '{output_format}'. Use 'docx' or 'pdf'.")


def convert_document(
    input_md_path: Union[str, Path],
    output_format: str = "docx",
    output_path: Optional[Union[str, Path]] = None,
    title: Optional[str] = None,
    toc: bool = True,
    toc_depth: int = 3,
    landscape: bool = False,
) -> Path:
    """
    Converts a Markdown (.md) document into a court-admissible Word (.docx) or PDF (.pdf)
    file with TH Sarabun New and math symbol fonts using Quarto.

    Args:
        input_md_path: Path to the input markdown file.
        output_format: Output format ('docx' or 'pdf').
        output_path: Optional destination path. If omitted, uses output/ with matching stem.
        title: Optional document title. Inferred from # Heading if not provided.
        toc: Whether to include a Table of Contents.
        toc_depth: Depth of Table of Contents headings.
        landscape: Whether to render document in landscape orientation (A4 flipped).

    Returns:
        Path to the generated document (relative to workspace).
    """
    if not is_quarto_installed():
        raise QuartoNotInstalledError(
            "Quarto is required for DOCX/PDF rendering with TH Sarabun New and Mermaid support, "
            "but is not installed on this system. Please ask user confirmation to install Quarto "
            "(e.g., via 'winget install Posit.Quarto' or https://quarto.org/docs/get-started/)."
        )

    in_p = Path(input_md_path)
    if not in_p.exists():
        raise FileNotFoundError(f"Input Markdown file not found: {in_p}")

    content = in_p.read_text(encoding="utf-8")

    # Infer title if not supplied
    if not title:
        m = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        title = m.group(1).strip() if m else in_p.stem.replace("_", " ").title()

    # Determine output path
    fmt = output_format.lower()
    if fmt in ("typst", "pdf"):
        ext = ".pdf"
        target_fmt = "typst"
    elif fmt == "docx":
        ext = ".docx"
        target_fmt = "docx"
    else:
        raise ValueError(f"Unsupported output_format: '{output_format}'. Expected 'docx' or 'pdf'.")

    if output_path is None:
        out_p = in_p.parent / f"{in_p.stem}{ext}"
    else:
        out_p = Path(output_path)

    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Reference doc for docx
    ref_doc: Optional[Path] = None
    if target_fmt == "docx":
        ref_doc = ensure_docx_reference_template(landscape=landscape)

    # Transform mermaid blocks to Quarto executable blocks
    transformed_content = transform_mermaid_blocks(content)

    # If landscape, adjust fig-width to wider printable canvas (e.g. 9.5 inches)
    if landscape:
        transformed_content = transformed_content.replace("%%| fig-width: 6.5", "%%| fig-width: 9.5")

    # Remove existing frontmatter if any, then prepend styled frontmatter
    if transformed_content.startswith("---"):
        parts = transformed_content.split("---", 2)
        if len(parts) >= 3:
            transformed_content = parts[2].lstrip()

    frontmatter = generate_frontmatter(
        title=title,
        output_format=target_fmt,
        reference_doc=ref_doc,
        toc=toc,
        toc_depth=toc_depth,
        landscape=landscape,
    )
    final_qmd_content = frontmatter + transformed_content

    # Write temporary .qmd
    temp_qmd = in_p.parent / f"__temp_{in_p.stem}_{target_fmt}.qmd"
    try:
        temp_qmd.write_text(final_qmd_content, encoding="utf-8")

        # Run Quarto with target filename
        cmd = [
            get_quarto_bin() or "quarto",
            "render",
            str(temp_qmd.as_posix()),
            "--to",
            target_fmt,
            "--output",
            out_p.name,
        ]

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )

        if res.returncode != 0:
            err = res.stderr or res.stdout
            raise RuntimeError(f"Quarto render failed (exit code {res.returncode}):\n{err}")

        # Check if Quarto placed the generated file at root or temporary location, and move to out_p
        candidates = [
            Path(out_p.name),
            in_p.parent / f"__temp_{in_p.stem}_{target_fmt}{ext}",
            Path(f"__temp_{in_p.stem}_{target_fmt}{ext}"),
        ]
        for cand in candidates:
            if cand.exists() and cand.resolve() != out_p.resolve():
                shutil.move(str(cand), str(out_p))
                break

        if not out_p.exists():
            raise FileNotFoundError(f"Expected output file not generated: {out_p}")

        # Post-process docx to guarantee table grid borders and column width alignment
        if target_fmt == "docx":
            try:
                _ensure_docx_table_borders(out_p)
                if landscape:
                    _post_process_landscape_docx(out_p)
                else:
                    # Also apply optimized column widths to portrait tables
                    import docx
                    d_doc = docx.Document(str(out_p))
                    modified = False
                    for tbl in d_doc.tables:
                        if len(tbl.columns) in (7, 8):
                            _apply_beneficiary_table_widths(tbl, is_landscape=False)
                            modified = True
                    if modified:
                        d_doc.save(str(out_p))
            except Exception:
                pass

        # Post-process landscape PDF to remove orphaned portrait title page if present
        if target_fmt == "typst" and landscape and out_p.exists():
            try:
                import pypdf
                reader = pypdf.PdfReader(out_p)
                if len(reader.pages) > 1:
                    first_page = reader.pages[0]
                    # Check if first page is portrait while subsequent pages are landscape
                    if first_page.mediabox.width < first_page.mediabox.height:
                        writer = pypdf.PdfWriter()
                        for p in reader.pages[1:]:
                            writer.add_page(p)
                        with open(out_p, "wb") as f_out:
                            writer.write(f_out)
            except Exception:
                pass

        return out_p

    finally:
        # Clean up temporary .qmd and intermediate files / directories
        if temp_qmd.exists():
            temp_qmd.unlink(missing_ok=True)
        # Quarto creates an intermediate .typ file for typst
        temp_typ = in_p.parent / f"__temp_{in_p.stem}_{target_fmt}.typ"
        if temp_typ.exists():
            temp_typ.unlink(missing_ok=True)
        # Quarto creates temporary *_files directories
        temp_dir = in_p.parent / f"__temp_{in_p.stem}_{target_fmt}_files"
        if temp_dir.exists() and temp_dir.is_dir():
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert Markdown to DOCX/PDF via Quarto with TH Sarabun New.")
    parser.add_argument("input_md", nargs="?", help="Input Markdown file path.")
    parser.add_argument("--format", choices=["docx", "pdf", "both"], default="docx", help="Target output format.")
    parser.add_argument("--output", help="Custom output path.")
    parser.add_argument("--check", action="store_true", help="Check Quarto installation status.")
    parser.add_argument("--no-toc", action="store_true", help="Disable Table of Contents.")
    args = parser.parse_args()

    if args.check:
        installed = is_quarto_installed()
        version = get_quarto_version()
        print(f"Quarto Installed: {installed}")
        if installed:
            print(f"Quarto Version: {version}")
        else:
            print("Quarto is NOT installed on this machine.")
        return

    if not args.input_md:
        parser.print_help()
        return

    in_file = Path(args.input_md)
    if not in_file.exists():
        print(f"Error: File not found: {in_file}")
        sys.exit(1)

    formats = ["docx", "pdf"] if args.format == "both" else [args.format]
    for fmt in formats:
        try:
            res = convert_document(in_file, output_format=fmt, toc=not args.no_toc)
            print(f"Converted ({fmt.upper()}): {res}")
        except QuartoNotInstalledError as e:
            print(f"Quarto Not Installed: {e}")
            sys.exit(2)
        except Exception as e:
            print(f"Conversion error ({fmt}): {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

