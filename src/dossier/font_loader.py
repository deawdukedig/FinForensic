"""
Thai Font Loader and Registrar for ReportLab PDF Generation.
Automatically discovers and registers official Thai government fonts:
- TH Sarabun New (THSarabunNew)
- TH Sarabun IT๙ (THSarabunIT๙ / THSarabunIT9)
Ensures full TrueType embedding with Normal, Bold, Italic, and BoldItalic variants.
"""

from __future__ import annotations
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def get_project_font_dir(explicit_dir: Optional[Union[str, Path]] = None) -> Path:
    """Resolves font directory from explicit path, cwd, or project root."""
    if explicit_dir:
        p = Path(explicit_dir)
        if p.exists() and p.is_dir():
            return p

    cwd_fonts = Path("fonts")
    if cwd_fonts.exists() and cwd_fonts.is_dir():
        return cwd_fonts

    proj_root_fonts = Path(__file__).resolve().parent.parent.parent / "fonts"
    if proj_root_fonts.exists() and proj_root_fonts.is_dir():
        return proj_root_fonts

    return Path("fonts")


def register_thai_fonts(fonts_dir: Optional[Union[str, Path]] = None) -> Dict[str, str]:
    """
    Registers THSarabunNew and THSarabunIT๙ font families into ReportLab pdfmetrics.
    Returns a dictionary of registered font family names and their primary file paths.
    """
    fdir = get_project_font_dir(fonts_dir)
    registered: Dict[str, str] = {}
    if not fdir.exists():
        return registered

    # 1. Register THSarabunNew Family
    new_norm = fdir / "THSarabunNew.ttf"
    new_bold = fdir / "THSarabunNew Bold.ttf"
    new_italic = fdir / "THSarabunNew Italic.ttf"
    new_bi = fdir / "THSarabunNew BoldItalic.ttf"

    if new_norm.exists():
        try:
            pdfmetrics.registerFont(TTFont("THSarabunNew", str(new_norm)))
            if new_bold.exists():
                pdfmetrics.registerFont(TTFont("THSarabunNew-Bold", str(new_bold)))
            if new_italic.exists():
                pdfmetrics.registerFont(TTFont("THSarabunNew-Italic", str(new_italic)))
            if new_bi.exists():
                pdfmetrics.registerFont(TTFont("THSarabunNew-BoldItalic", str(new_bi)))

            pdfmetrics.registerFontFamily(
                "THSarabunNew",
                normal="THSarabunNew",
                bold="THSarabunNew-Bold" if new_bold.exists() else "THSarabunNew",
                italic="THSarabunNew-Italic" if new_italic.exists() else "THSarabunNew",
                boldItalic="THSarabunNew-BoldItalic" if new_bi.exists() else "THSarabunNew",
            )
            registered["THSarabunNew"] = str(new_norm)
        except Exception:
            pass

    # 2. Register THSarabunIT๙ Family
    it_norm: Optional[Path] = None
    it_bold: Optional[Path] = None
    it_italic: Optional[Path] = None
    it_bi: Optional[Path] = None

    for item in fdir.iterdir():
        fname = item.name
        if fname.startswith("THSarabunIT"):
            if "BoldItalic" in fname:
                it_bi = item
            elif "Bold" in fname:
                it_bold = item
            elif "Italic" in fname:
                it_italic = item
            elif fname.endswith(".ttf"):
                it_norm = item

    if it_norm and it_norm.exists():
        try:
            for base_name in ("THSarabunIT๙", "THSarabunIT9"):
                pdfmetrics.registerFont(TTFont(base_name, str(it_norm)))
                b_name = f"{base_name}-Bold"
                i_name = f"{base_name}-Italic"
                bi_name = f"{base_name}-BoldItalic"

                if it_bold and it_bold.exists():
                    pdfmetrics.registerFont(TTFont(b_name, str(it_bold)))
                if it_italic and it_italic.exists():
                    pdfmetrics.registerFont(TTFont(i_name, str(it_italic)))
                if it_bi and it_bi.exists():
                    pdfmetrics.registerFont(TTFont(bi_name, str(it_bi)))

                pdfmetrics.registerFontFamily(
                    base_name,
                    normal=base_name,
                    bold=b_name if (it_bold and it_bold.exists()) else base_name,
                    italic=i_name if (it_italic and it_italic.exists()) else base_name,
                    boldItalic=bi_name if (it_bi and it_bi.exists()) else base_name,
                )
            registered["THSarabunIT๙"] = str(it_norm)
            registered["THSarabunIT9"] = str(it_norm)
        except Exception:
            pass

    return registered


def register_math_font() -> Optional[str]:
    """
    Discovers and registers a math/symbol font capable of rendering Unicode mathematical glyphs
    such as ∑ (U+2211), ∈ (U+2208), ≤ (U+2264), ε (U+03B5), → (U+2192), · (U+00B7).
    Returns the registered font family name, or None if no suitable font is available.
    """
    if "MathSymbolFont" in pdfmetrics.getRegisteredFontNames():
        return "MathSymbolFont"

    candidate_paths = [
        Path("C:/Windows/Fonts/seguisym.ttf"),
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/eucsym.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansMath-Regular.ttf"),
        Path("fonts/seguisym.ttf"),
        Path("fonts/DejaVuSans.ttf"),
    ]

    for p in candidate_paths:
        if p.exists() and p.is_file():
            try:
                ttf = TTFont("MathSymbolFont", str(p))
                if 0x2211 in ttf.face.charToGlyph and 0x2208 in ttf.face.charToGlyph:
                    pdfmetrics.registerFont(ttf)
                    return "MathSymbolFont"
            except Exception:
                continue

    return None


def resolve_thai_font(
    font_spec: Optional[str] = None,
    fonts_dir: Optional[Union[str, Path]] = None,
) -> str:
    """
    Resolves and ensures registration of the requested Thai font.
    Priority:
    1. Explicit font_spec matching THSarabunIT๙ / THSarabunIT9
    2. Explicit font_spec matching THSarabunNew
    3. Explicit TTF path
    4. Default: THSarabunNew if present in fonts/
    5. Fallback: THSarabunIT๙ if present in fonts/
    6. System Fallback: C:/Windows/Fonts/tahoma.ttf
    7. Standard Fallback: Helvetica
    """
    registered = register_thai_fonts(fonts_dir)

    # 1. Match specific requested font
    if font_spec:
        spec_lower = font_spec.lower().strip()
        # Direct file path
        if os.path.exists(font_spec) and os.path.isfile(font_spec):
            fname = Path(font_spec).stem
            try:
                pdfmetrics.registerFont(TTFont(fname, font_spec))
                return fname
            except Exception:
                pass

        if "it๙" in spec_lower or "it9" in spec_lower or "thsarabunit" in spec_lower:
            if "THSarabunIT๙" in registered:
                return "THSarabunIT๙"
            if "THSarabunIT9" in registered:
                return "THSarabunIT9"

        if "sarabunnew" in spec_lower or "thsarabunnew" in spec_lower or "sarabun" in spec_lower:
            if "THSarabunNew" in registered:
                return "THSarabunNew"

        if "tahoma" in spec_lower:
            tahoma_p = "C:/Windows/Fonts/tahoma.ttf"
            if os.path.exists(tahoma_p):
                try:
                    pdfmetrics.registerFont(TTFont("Tahoma", tahoma_p))
                    return "Tahoma"
                except Exception:
                    pass

    # 2. Defaults when none specified or not matched
    if "THSarabunNew" in registered:
        return "THSarabunNew"
    if "THSarabunIT๙" in registered:
        return "THSarabunIT๙"
    if "THSarabunIT9" in registered:
        return "THSarabunIT9"

    # 3. System fallback
    tahoma_p = "C:/Windows/Fonts/tahoma.ttf"
    if os.path.exists(tahoma_p):
        try:
            pdfmetrics.registerFont(TTFont("Tahoma", tahoma_p))
            return "Tahoma"
        except Exception:
            pass

    return "Helvetica"


TALL_CONSONANTS = set("ปผฝฟฬ")
UPPER_VOWELS = set("\u0e31\u0e34\u0e35\u0e36\u0e37\u0e47\u0e4d")
TONE_MARKS = set("\u0e48\u0e49\u0e4a\u0e4b\u0e4c")
LOWER_VOWELS = set("\u0e38\u0e39\u0e3a")

# PUA mapping tables for TH Sarabun
LOW_TONE = {
    "\u0e48": "\uf705",  # ไม้เอกล่าง
    "\u0e49": "\uf706",  # ไม้โทล่าง
    "\u0e4a": "\uf707",  # ไม้ตรีล่าง
    "\u0e4b": "\uf708",  # ไม้จัตวาล่าง
    "\u0e4c": "\uf709",  # การันต์ล่าง
}
TALL_LOW_TONE = {
    "\u0e48": "\uf70a",
    "\u0e49": "\uf70b",
    "\u0e4a": "\uf70c",
    "\u0e4b": "\uf70d",
    "\u0e4c": "\uf70e",
}
TALL_UPPER_VOWEL = {
    "\u0e31": "\uf713",
    "\u0e34": "\uf70f",
    "\u0e35": "\uf710",
    "\u0e36": "\uf711",
    "\u0e37": "\uf712",
    "\u0e47": "\uf715",
    "\u0e4d": "\uf714",
}
TALL_HIGH_TONE = {
    "\u0e48": "\uf701",
    "\u0e49": "\uf702",
    "\u0e4a": "\uf703",
    "\u0e4b": "\uf704",
}
LOW_LOWER_VOWEL = {
    "\u0e38": "\uf718",
    "\u0e39": "\uf719",
}
HTML_TAG_PATTERN = re.compile(r"(<[^>]+>)")


@lru_cache(maxsize=4096)
def shape_thai_text(text: str) -> str:
    """
    Shapes Thai text by mapping contextual vowels and tone marks to standard PUA glyphs
    in Thai National Fonts (TH Sarabun New, TH Sarabun IT๙, TH Sarabun PSK).
    Eliminates floating tone marks (วรรณยุกต์ลอย) and tall consonant collisions.
    Safely preserves embedded HTML tags (<b/i/code/font/br>).
    """
    if not text:
        return text

    # Split by HTML tags to preserve them untouched
    parts = HTML_TAG_PATTERN.split(text)
    shaped_parts = []
    prev_consonant = None
    prev_upper_vowel = False

    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            shaped_parts.append(part)
            continue

        chars = list(part)
        res = []
        for idx, c in enumerate(chars):
            # Check if this tone mark is immediately followed by \u0e33 (Sara Am ำ)
            # e.g. น + ้ + ำ -> tone mark stays at Level 3 above Nikhahit
            is_before_sara_am = (idx + 1 < len(chars) and chars[idx + 1] == "\u0e33")

            if "\u0e01" <= c <= "\u0e2e":
                prev_consonant = c
                prev_upper_vowel = False
                res.append(c)
            elif c in UPPER_VOWELS:
                prev_upper_vowel = True
                if prev_consonant in TALL_CONSONANTS:
                    res.append(TALL_UPPER_VOWEL.get(c, c))
                else:
                    res.append(c)
            elif c in TONE_MARKS:
                if prev_upper_vowel or is_before_sara_am:
                    # Level 3 (above upper vowel or above sara am circle)
                    if prev_consonant in TALL_CONSONANTS:
                        res.append(TALL_HIGH_TONE.get(c, c))
                    else:
                        res.append(c)
                else:
                    # Level 2 (no upper vowel) -> LOWERED TO ELIMINATE FLOATING TONE MARKS
                    if prev_consonant in TALL_CONSONANTS:
                        res.append(TALL_LOW_TONE.get(c, c))
                    else:
                        res.append(LOW_TONE.get(c, c))
                prev_upper_vowel = False
            elif c in LOWER_VOWELS:
                if prev_consonant in set("ฎฏ"):
                    res.append(LOW_LOWER_VOWEL.get(c, c))
                elif prev_consonant == "ญ" and c in ("\u0e38", "\u0e39"):
                    if len(res) > 0 and res[-1] == "ญ":
                        res[-1] = "\uf71a"
                    res.append(c)
                elif prev_consonant == "ฐ" and c in ("\u0e38", "\u0e39"):
                    if len(res) > 0 and res[-1] == "ฐ":
                        res[-1] = "\uf700"
                    res.append(c)
                else:
                    res.append(c)
                prev_upper_vowel = False
            else:
                if c not in (" ", "\t", "\n", "(", ")", '"', "'", "-"):
                    prev_consonant = None
                    prev_upper_vowel = False
                res.append(c)
        shaped_parts.append("".join(res))

    return "".join(shaped_parts)
