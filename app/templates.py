"""Structured-result templates for lab report types.

A template is just a list of `Param` rows: parameter name, unit, the section it
belongs to (used for grouping headers in the form / future tabular PDF), and a
reference range. Ranges may be sex-specific.

Reference values below are commonly-cited ADULT ranges as a starting point —
a clinic should review and adjust them to match the assays / instruments
actually in use. They live in code for now; making them editable from the UI
is planned future work.

A report-type "code" (from the `report_types` table — e.g. "CBC", "LIPID") that
exists in `TEMPLATES` switches the New Report page into structured (tabular)
mode. Codes not listed here fall back to the original free-text editor.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    """One row of a structured report template."""
    name: str
    unit: str = ""
    section: str = ""
    # generic (sex-independent) range
    ref_low: float | None = None
    ref_high: float | None = None
    # sex-specific overrides; if set, they win over the generic range
    ref_low_male: float | None = None
    ref_high_male: float | None = None
    ref_low_female: float | None = None
    ref_high_female: float | None = None
    # qualitative parameter: value is compared (case-insensitively) to this
    expected: str | None = None
    # optional small caption shown under the parameter name (e.g. "Calculated")
    note: str = ""


# ---------------------------------------------------------------- helpers
def ranges_for(p: Param, sex: str | None) -> tuple[float | None, float | None]:
    """Return (low, high) appropriate for the patient's sex; falls back gracefully."""
    s = (sex or "").lower()
    if s.startswith("f") and p.ref_low_female is not None:
        return (p.ref_low_female, p.ref_high_female)
    if s.startswith("m") and p.ref_low_male is not None:
        return (p.ref_low_male, p.ref_high_male)
    if p.ref_low is not None or p.ref_high is not None:
        return (p.ref_low, p.ref_high)
    if p.ref_low_male is not None:
        return (p.ref_low_male, p.ref_high_male)
    if p.ref_low_female is not None:
        return (p.ref_low_female, p.ref_high_female)
    return (None, None)


def _fmt(n: float) -> str:
    if n is None:
        return ""
    # show whole-number-ish values without trailing .0
    if float(n).is_integer():
        return str(int(n))
    return f"{n:g}"


def reference_text(p: Param, sex: str | None) -> str:
    """Human-readable reference string, e.g. '13.0 - 17.0' or 'Negative' or '< 200'."""
    if p.expected:
        return p.expected
    low, high = ranges_for(p, sex)
    if low is not None and high is not None:
        return f"{_fmt(low)} - {_fmt(high)}"
    if high is not None:
        return f"< {_fmt(high)}"
    if low is not None:
        return f"> {_fmt(low)}"
    return ""


def _try_number(value: str) -> float | None:
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    # strip a leading <, > or = if present (e.g. "<150")
    if s[0] in "<>=":
        s = s[1:].strip()
    try:
        return float(s)
    except ValueError:
        pass
    first = s.split()[0] if s.split() else ""
    try:
        return float(first)
    except ValueError:
        return None


def compute_flag(value: str, p: Param, sex: str | None) -> str:
    """Return '' / 'Normal' / 'Low' / 'High' / 'Abnormal' for the given value."""
    if value is None or str(value).strip() == "":
        return ""
    s = str(value).strip()
    if p.expected:
        return "Normal" if s.lower() == p.expected.strip().lower() else "Abnormal"
    num = _try_number(s)
    if num is None:
        return ""
    low, high = ranges_for(p, sex)
    if low is not None and num < low:
        return "Low"
    if high is not None and num > high:
        return "High"
    if low is None and high is None:
        return ""
    return "Normal"


# ================================================================
#                      TEMPLATES
# ================================================================

_CBC = [
    Param("Hemoglobin (Hb)", unit="g/dL", section="HEMOGLOBIN",
          ref_low_male=13.0, ref_high_male=17.0,
          ref_low_female=12.0, ref_high_female=15.5),

    Param("Total RBC count", unit="mill/cumm", section="RBC COUNT",
          ref_low_male=4.5, ref_high_male=5.9,
          ref_low_female=4.1, ref_high_female=5.1),

    Param("Packed Cell Volume (PCV)", unit="%", section="BLOOD INDICES",
          ref_low_male=40, ref_high_male=50,
          ref_low_female=36, ref_high_female=44,
          note="Calculated"),
    Param("Mean Corpuscular Volume (MCV)", unit="fL", section="BLOOD INDICES",
          ref_low=80, ref_high=101, note="Calculated"),
    Param("MCH", unit="pg", section="BLOOD INDICES",
          ref_low=27, ref_high=32, note="Calculated"),
    Param("MCHC", unit="g/dL", section="BLOOD INDICES",
          ref_low=32.5, ref_high=34.5, note="Calculated"),
    Param("RDW", unit="%", section="BLOOD INDICES",
          ref_low=11.6, ref_high=14.0),

    Param("Total WBC count", unit="/cumm", section="WBC COUNT",
          ref_low=4000, ref_high=11000),

    Param("Neutrophils", unit="%", section="DIFFERENTIAL WBC COUNT",
          ref_low=40, ref_high=70),
    Param("Lymphocytes", unit="%", section="DIFFERENTIAL WBC COUNT",
          ref_low=20, ref_high=40),
    Param("Eosinophils", unit="%", section="DIFFERENTIAL WBC COUNT",
          ref_low=1, ref_high=6),
    Param("Monocytes", unit="%", section="DIFFERENTIAL WBC COUNT",
          ref_low=2, ref_high=10),
    Param("Basophils", unit="%", section="DIFFERENTIAL WBC COUNT",
          ref_low=0, ref_high=2),

    Param("Platelet count", unit="/cumm", section="PLATELET COUNT",
          ref_low=150_000, ref_high=410_000),

    Param("ESR", unit="mm/hr", section="ESR",
          ref_low_male=0, ref_high_male=15,
          ref_low_female=0, ref_high_female=20,
          note="Capillary photometry"),
]


_LIPID = [
    Param("Total Cholesterol", unit="mg/dL", section="LIPID PROFILE",
          ref_high=200, note="Desirable: < 200"),
    Param("Triglycerides", unit="mg/dL", section="LIPID PROFILE",
          ref_high=150, note="Normal: < 150"),
    Param("HDL Cholesterol", unit="mg/dL", section="LIPID PROFILE",
          ref_low_male=40, ref_low_female=50,
          note="Higher is better"),
    Param("LDL Cholesterol", unit="mg/dL", section="LIPID PROFILE",
          ref_high=100, note="Optimal: < 100"),
    Param("VLDL Cholesterol", unit="mg/dL", section="LIPID PROFILE",
          ref_low=5, ref_high=40),
    Param("Total Cholesterol / HDL Ratio", unit="", section="LIPID PROFILE",
          ref_high=5),
]


_BSUGAR = [
    Param("Fasting Blood Sugar (FBS)", unit="mg/dL", section="BLOOD SUGAR",
          ref_low=70, ref_high=100),
    Param("Post-Prandial Blood Sugar (PPBS)", unit="mg/dL", section="BLOOD SUGAR",
          ref_low=70, ref_high=140, note="2 hours after meal"),
    Param("Random Blood Sugar (RBS)", unit="mg/dL", section="BLOOD SUGAR",
          ref_low=70, ref_high=140),
    Param("HbA1c", unit="%", section="GLYCATED HEMOGLOBIN",
          ref_high=5.7, note="Non-diabetic: < 5.7"),
]


_LFT = [
    Param("Total Bilirubin", unit="mg/dL", section="BILIRUBIN",
          ref_low=0.2, ref_high=1.2),
    Param("Direct Bilirubin", unit="mg/dL", section="BILIRUBIN",
          ref_low=0.0, ref_high=0.3),
    Param("Indirect Bilirubin", unit="mg/dL", section="BILIRUBIN",
          ref_low=0.1, ref_high=0.9, note="Calculated"),

    Param("SGOT / AST", unit="U/L", section="ENZYMES",
          ref_low_male=0, ref_high_male=40,
          ref_low_female=0, ref_high_female=32),
    Param("SGPT / ALT", unit="U/L", section="ENZYMES",
          ref_low_male=0, ref_high_male=41,
          ref_low_female=0, ref_high_female=33),
    Param("Alkaline Phosphatase", unit="U/L", section="ENZYMES",
          ref_low=40, ref_high=129),

    Param("Total Protein", unit="g/dL", section="PROTEINS",
          ref_low=6.4, ref_high=8.3),
    Param("Albumin", unit="g/dL", section="PROTEINS",
          ref_low=3.5, ref_high=5.0),
    Param("Globulin", unit="g/dL", section="PROTEINS",
          ref_low=2.3, ref_high=3.5, note="Calculated"),
    Param("A / G Ratio", unit="", section="PROTEINS",
          ref_low=1.2, ref_high=2.2, note="Calculated"),
]


_KFT = [
    Param("Blood Urea", unit="mg/dL", section="KIDNEY FUNCTION",
          ref_low=17, ref_high=43),
    Param("Serum Creatinine", unit="mg/dL", section="KIDNEY FUNCTION",
          ref_low_male=0.7, ref_high_male=1.3,
          ref_low_female=0.6, ref_high_female=1.1),
    Param("Uric Acid", unit="mg/dL", section="KIDNEY FUNCTION",
          ref_low_male=3.4, ref_high_male=7.0,
          ref_low_female=2.4, ref_high_female=6.0),

    Param("Sodium (Na+)", unit="mEq/L", section="ELECTROLYTES",
          ref_low=136, ref_high=145),
    Param("Potassium (K+)", unit="mEq/L", section="ELECTROLYTES",
          ref_low=3.5, ref_high=5.1),
    Param("Chloride (Cl-)", unit="mEq/L", section="ELECTROLYTES",
          ref_low=98, ref_high=107),
    Param("Calcium", unit="mg/dL", section="ELECTROLYTES",
          ref_low=8.6, ref_high=10.2),
    Param("Phosphorus", unit="mg/dL", section="ELECTROLYTES",
          ref_low=2.5, ref_high=4.5),
]


_THYROID = [
    Param("Total T3 (Triiodothyronine)", unit="ng/mL", section="THYROID PROFILE",
          ref_low=0.8, ref_high=2.0),
    Param("Total T4 (Thyroxine)", unit="µg/dL", section="THYROID PROFILE",
          ref_low=5.1, ref_high=14.1),
    Param("TSH (Thyroid Stimulating Hormone)", unit="µIU/mL", section="THYROID PROFILE",
          ref_low=0.27, ref_high=4.20),
]


_URINE = [
    Param("Colour", section="PHYSICAL EXAMINATION"),
    Param("Appearance", section="PHYSICAL EXAMINATION"),
    Param("Reaction (pH)", unit="", section="PHYSICAL EXAMINATION",
          ref_low=4.5, ref_high=8.0),
    Param("Specific Gravity", unit="", section="PHYSICAL EXAMINATION",
          ref_low=1.005, ref_high=1.030),

    Param("Protein", section="CHEMICAL EXAMINATION", expected="Negative"),
    Param("Sugar", section="CHEMICAL EXAMINATION", expected="Negative"),
    Param("Ketones", section="CHEMICAL EXAMINATION", expected="Negative"),
    Param("Bile Salts", section="CHEMICAL EXAMINATION", expected="Negative"),
    Param("Bile Pigments", section="CHEMICAL EXAMINATION", expected="Negative"),
    Param("Urobilinogen", section="CHEMICAL EXAMINATION", expected="Normal"),
    Param("Nitrites", section="CHEMICAL EXAMINATION", expected="Negative"),

    Param("RBCs", unit="/HPF", section="MICROSCOPIC EXAMINATION",
          ref_low=0, ref_high=2),
    Param("Pus cells (WBC)", unit="/HPF", section="MICROSCOPIC EXAMINATION",
          ref_low=0, ref_high=5),
    Param("Epithelial cells", unit="/HPF", section="MICROSCOPIC EXAMINATION",
          ref_low=0, ref_high=5),
    Param("Casts", section="MICROSCOPIC EXAMINATION", expected="Nil"),
    Param("Crystals", section="MICROSCOPIC EXAMINATION", expected="Nil"),
]


# Templates are keyed by the report-type CODE (from the `report_types` table).
TEMPLATES: dict[str, list[Param]] = {
    "CBC": _CBC,
    "LIPID": _LIPID,
    "BSUGAR": _BSUGAR,
    "LFT": _LFT,
    "KFT": _KFT,
    "THYROID": _THYROID,
    "URINE": _URINE,
}


def has_template(type_code: str | None) -> bool:
    return bool(type_code) and type_code in TEMPLATES


def get_template(type_code: str) -> list[Param]:
    return TEMPLATES.get(type_code, [])


# ---------------------------------------------------------------- text render
def rows_to_text(rows: list[dict]) -> str:
    """Build a human-readable plain-text summary of a structured result set.

    Used as a fallback for the existing free-text PDF renderer while the
    tabular PDF (phase 2) isn't yet implemented. Format roughly matches the
    on-screen table: section headers, then 'param: value unit  Ref: …  [Flag]'.
    """
    lines: list[str] = []
    current = None
    for r in rows:
        section = r.get("section") or ""
        if section != current:
            current = section
            if lines:
                lines.append("")
            if section:
                lines.append(section)
        flag = (r.get("flag") or "").strip()
        flag_part = f"   [{flag}]" if flag in ("Low", "High", "Abnormal") else ""
        ref = r.get("reference") or ""
        ref_part = f"   Ref: {ref}" if ref else ""
        unit = r.get("unit") or ""
        unit_part = f" {unit}" if unit else ""
        lines.append(f"  {r['parameter']}: {r['value']}{unit_part}{ref_part}{flag_part}".rstrip())
    return "\n".join(lines)
