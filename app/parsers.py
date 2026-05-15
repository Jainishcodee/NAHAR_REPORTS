"""Smart-paste parser: turn raw user input into matched template values.

Supported input forms:
  - JSON (flat or nested; leaf wrappers like {"value": 12.5, "unit": "g/dL"} are
    unwrapped to just the value)
  - Tab-separated rows (e.g. pasted from Excel): `Hemoglobin<TAB>12.5<TAB>g/dL`
  - "name: value" / "name = value" lines
  - "name  value" lines (split on >=2 spaces, or on the space before a digit)

Matching is deterministic — no ML. We build an alias index per template
(normalized parameter names + parenthesised abbreviations + a small
hand-curated synonym table) and resolve source keys against it via
exact / substring / `difflib` fallback.
"""
import json
import re
from difflib import get_close_matches

from app.templates import Param


# ---- hand-curated synonyms (param.name -> list of extra aliases) ----------
# The full name + paren content are picked up automatically; this list adds
# the abbreviations / alternate spellings that don't appear in the name.
EXTRA_SYNONYMS: dict[str, list[str]] = {
    "Hemoglobin (Hb)": ["hgb", "haemoglobin"],
    "Total RBC count": ["rbc", "rbccount", "erythrocytes"],
    "Total WBC count": ["wbc", "tlc", "wbccount", "leukocytes"],
    "Platelet count": ["plt", "platelets", "thrombocytes"],
    "Packed Cell Volume (PCV)": ["hct", "hematocrit", "haematocrit"],

    "Fasting Blood Sugar (FBS)": ["fasting", "fbg"],
    "Post-Prandial Blood Sugar (PPBS)": ["pp", "postprandial", "ppbg"],
    "Random Blood Sugar (RBS)": ["random", "rbg"],
    "HbA1c": ["a1c", "glycatedhemoglobin", "ghb"],

    "Total Cholesterol": ["cholesterol", "tc"],
    "HDL Cholesterol": ["hdl"],
    "LDL Cholesterol": ["ldl"],
    "VLDL Cholesterol": ["vldl"],
    "Triglycerides": ["tg"],

    "Blood Urea": ["urea", "bun"],
    "Serum Creatinine": ["creatinine", "creat"],
    "Uric Acid": ["uric"],
    "Sodium (Na+)": ["na", "sodium"],
    "Potassium (K+)": ["potassium"],
    "Chloride (Cl-)": ["chloride"],
    "Calcium": ["calcium"],
    "Phosphorus": ["phos", "phosphate"],

    "Total Bilirubin": ["bilirubin", "totalbili", "tbil"],
    "Direct Bilirubin": ["directbili", "dbil"],
    "Indirect Bilirubin": ["indirectbili", "ibil"],
    "SGOT / AST": ["aspartate"],
    "SGPT / ALT": ["alanine"],
    "Alkaline Phosphatase": ["alp", "alkphos"],
    "Total Protein": ["totalprot", "protein"],
    "Albumin": ["alb"],
    "Globulin": ["glob"],
    "A / G Ratio": ["agratio", "albgloratio"],

    "TSH (Thyroid Stimulating Hormone)": ["thyrotropin"],
    "Total T3 (Triiodothyronine)": ["triiodothyronine"],
    "Total T4 (Thyroxine)": ["thyroxine"],

    "Colour": ["color"],
    "Appearance": ["clarity"],
    "Reaction (pH)": ["urinephp", "urineph"],
    "Specific Gravity": ["sg"],
    "Pus cells (WBC)": ["puscells", "wbcurine"],
    "Epithelial cells": ["epicells", "epithelial"],
}


# ---------------------------------------------------------------- helpers
def _norm(text) -> str:
    """Lowercase + strip every non-alphanumeric. Used for fuzzy comparisons."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _aliases_for(p: Param) -> set[str]:
    out: set[str] = set()
    name = p.name
    out.add(_norm(name))
    # contents of parentheses, and the rest of the name without them
    m = re.search(r"\(([^)]+)\)", name)
    if m:
        out.add(_norm(m.group(1)))
        out.add(_norm(re.sub(r"\([^)]+\)", "", name)))
    # split on '/' and ',' for names like "SGOT / AST"
    for token in re.split(r"[/,]", name):
        token = token.strip()
        if not token:
            continue
        out.add(_norm(token))
        tm = re.search(r"\(([^)]+)\)", token)
        if tm:
            out.add(_norm(tm.group(1)))
    for alias in EXTRA_SYNONYMS.get(name, []):
        out.add(_norm(alias))
    out.discard("")
    return out


def build_alias_index(params: list[Param]) -> dict[str, str]:
    """{normalized_alias -> param.name}. First insertion wins on collisions."""
    index: dict[str, str] = {}
    for p in params:
        for alias in _aliases_for(p):
            index.setdefault(alias, p.name)
    return index


# ---------------------------------------------------------------- parsing
def _flatten_json(obj, prefix=""):
    """Walk nested JSON yielding (leaf_key, value_str). Lists are skipped."""
    if isinstance(obj, dict):
        # leaf wrapper: {"value": X, "unit": "..."} -> use the prefix as the key
        if (
            "value" in obj
            and not isinstance(obj["value"], (dict, list))
            and prefix
        ):
            yield (prefix, str(obj["value"]))
            return
        for k, v in obj.items():
            yield from _flatten_json(v, str(k))
    elif isinstance(obj, list):
        return
    else:
        if obj is not None and prefix:
            yield (prefix, str(obj))


def _parse_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "--", "//")):
            continue
        # tab-separated (Excel paste)
        if "\t" in line:
            cells = [c.strip() for c in line.split("\t")]
            if len(cells) >= 2 and cells[0] and cells[1]:
                out[cells[0]] = cells[1]
            continue
        # name: value  or  name = value (use the FIRST occurrence of either)
        sep_idx = -1
        for sep in (":", "="):
            i = line.find(sep)
            if i > 0 and (sep_idx == -1 or i < sep_idx):
                sep_idx = i
        if sep_idx > 0:
            k = line[:sep_idx].strip()
            v = line[sep_idx + 1:].strip()
            if k and v:
                out[k] = v
            continue
        # "name  value"  /  "name -1.5 g/dL"
        m = re.search(r"\s{2,}|\s(?=[-\d])", line)
        if m:
            k = line[: m.start()].strip()
            v = line[m.end():].strip()
            if k and v:
                out[k] = v
    return out


def parse_to_pairs(text: str) -> dict[str, str]:
    """Convert raw pasted input into a flat {key: value_str} dict."""
    text = (text or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return _parse_lines(text)
    out: dict[str, str] = {}
    for k, v in _flatten_json(obj):
        out[k] = v
    return out


# ---------------------------------------------------------------- matching
def match_to_params(pairs: dict[str, str], params: list[Param]) -> dict[str, str]:
    """Return {param.name: value_str} for source keys matched to template params.

    Strategy per source key (normalized):
      1. exact hit in the alias index
      2. longest substring overlap (only if both sides are >= 4 chars — avoids
         "k" matching "kidney" etc.)
      3. difflib fuzzy match (cutoff 0.86)

    Unmatched source keys are silently dropped. Later source keys for the
    same param overwrite earlier ones.
    """
    if not pairs or not params:
        return {}
    index = build_alias_index(params)
    alias_keys = list(index.keys())
    matched: dict[str, str] = {}
    for src_key, raw_value in pairs.items():
        n = _norm(src_key)
        if not n:
            continue
        if n in index:
            matched[index[n]] = str(raw_value).strip()
            continue
        candidates = [
            a for a in alias_keys
            if len(a) >= 4 and len(n) >= 4 and (a in n or n in a)
        ]
        if candidates:
            candidates.sort(key=len, reverse=True)
            matched[index[candidates[0]]] = str(raw_value).strip()
            continue
        close = get_close_matches(n, alias_keys, n=1, cutoff=0.86)
        if close:
            matched[index[close[0]]] = str(raw_value).strip()
    return matched
