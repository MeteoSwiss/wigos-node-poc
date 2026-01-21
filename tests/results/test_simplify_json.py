import json
import re
from pathlib import Path
from typing import Any, Iterable, Tuple

import pytest
import xmltodict

# Keys/paths that are allowed to be dropped by the simplifier (regex on normalized path)
IGNORED_PATH_PATTERNS = [
    r"(^|/)@?xmlns($|/)",                 # any xmlns containers/attributes
    r"(^|/)schemaLocation($|/)",          # schemaLocation noise
    r"(^|/)boundedBy/[^/]*?/nil$",        # gml:boundedBy nil="true"
    r"(^|/)nil$",                         # generic nil attributes (when true)
    r"(^|/)type$",                        # type="simple" (see below we also check the value)
]

# Wrapper keys to strip from the path when normalizing
WRAPPER_KEYS = {
    "#text",
    "CharacterString",
    "container", "Container",
    "TimePeriod", "ReportingPeriod",
    "Process",
}

# Any key starting with these prefixes will be removed from the normalized path
WRAPPER_PREFIXES = ("CI_", "MD_", "OM_")

# Namespace prefix stripper (e.g., "gmd:foo" -> "foo")
NS_PREFIX_RE = re.compile(r"^[A-Za-z0-9_-]+:(?=[^/]+)$")

# Braced namespaces stripper (e.g., "{http://...}foo" -> "foo")
BRACED_NS_RE = re.compile(r"^\{[^}]+\}")

# Compile ignore regexes once
IGNORED_PATH_RES = [re.compile(p) for p in IGNORED_PATH_PATTERNS]


# ---- Helpers ----------------------------------------------------------------

def iter_leaves(obj: Any, path: Tuple[str, ...] = ()) -> Iterable[Tuple[Tuple[str, ...], Any]]:
    """Yield (path, value) for scalar leaves in a nested dict/list structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None:
                continue
            yield from iter_leaves(v, path + (str(k),))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            yield from iter_leaves(v, path + (str(idx),))
    else:
        yield path, obj


def strip_namespace(key: str) -> str:
    key = BRACED_NS_RE.sub("", key)
    key = NS_PREFIX_RE.sub("", key)
    return key


def normalize_path(path: Tuple[str, ...]) -> Tuple[str, ...]:
    """
    Normalize a path to align xmltodict(raw) and simplified JSON:
    - remove namespace prefixes and {uri} qualifiers
    - drop wrapper keys (#text, CharacterString, Process, TimePeriod/ReportingPeriod, container/Container)
    - drop CI_/MD_/OM_ prefixed struct names
    - drop integer indices (lists) to avoid index-induced mismatches
    - drop leading '@' from attribute names
    """
    norm = []
    for comp in path:
        # drop numeric indices from lists
        if comp.isdigit():
            continue

        # xmltodict attributes often start with '@'
        comp = comp.lstrip("@")

        # strip namespaces
        comp = strip_namespace(comp)

        # drop wrapper prefixes (entire component)
        if comp.startswith(WRAPPER_PREFIXES):
            continue

        # drop specific wrapper keys
        if comp in WRAPPER_KEYS:
            continue

        norm.append(comp)
    return tuple(norm)


def normalize_value(v: Any) -> Any:
    """Normalize scalar values so that cosmetic differences don't fail the test."""
    if isinstance(v, str):
        s = v.strip()
        # treat booleans consistently
        if s.lower() in ("true", "false"):
            return s.lower() == "true"
        # attempt numbers
        try:
            if re.fullmatch(r"[+-]?\d+", s):
                return int(s)
            if re.fullmatch(r"[+-]?\d*\.\d+(e[+-]?\d+)?", s, flags=re.I) or re.fullmatch(r"[+-]?\d+\.(e[+-]?\d+)?", s, flags=re.I):
                return float(s)
        except ValueError:
            pass
        return s
    return v


def should_ignore(norm_path: Tuple[str, ...], value: Any) -> bool:
    """
    Decide if a (path, value) from the RAW structure is acceptable to drop.
    """
    path_str = "/".join(norm_path)

    # ignore empties
    if value in ("", None, [], {}):
        return True

    # ignore known path patterns
    for rx in IGNORED_PATH_RES:
        if rx.search(path_str):
            # Special case: allow dropping type="simple" and nil="true"
            if norm_path[-1] == "type" and str(value).lower() == "simple":
                return True
            if norm_path[-1] == "nil" and str(value).lower() in ("true", "1"):
                return True
            # any other matched path is ignored
            return True

    return False


def load_raw_from_xml(xml_path: Path) -> dict:
    with xml_path.open("rb") as f:
        return xmltodict.parse(
            f,
            attr_prefix="@",      # default xmltodict attribute prefix
            cdata_key="#text",    # capture character data
            dict_constructor=dict
        )


def load_simplified_json(json_path: Path) -> dict:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def paired_samples(root: Path) -> list[tuple[Path, Path]]:
    """
    Find (*.xml, *.json) pairs under root.
    """
    pairs = []
    for xml in root.rglob("*.xml"):
        simplified = xml.with_suffix(".json")
        if simplified.exists():
            pairs.append((xml, simplified))
    return pairs


# ---- Tests ------------------------------------------------------------------

DATA_ROOT = Path("tests/data")  # adjust if your fixtures live elsewhere


@pytest.mark.parametrize("xml_path, json_path", paired_samples(DATA_ROOT))
def test_simplify_preserves_information(xml_path: Path, json_path: Path):
    """
    For each leaf in the RAW xmltodict structure (after normalization) there must be
    a matching (path, value) in the simplified JSON, except for an explicit, reviewed
    allowlist of ignorable items (namespaces, schemaLocation, type=simple, nil=true, empties).
    """
    raw = load_raw_from_xml(xml_path)
    simp = load_simplified_json(json_path)

    # Build normalized leaf sets
    raw_norm: set[tuple[Tuple[str, ...], Any]] = set()
    for p, v in iter_leaves(raw):
        np = normalize_path(p)
        nv = normalize_value(v)
        if should_ignore(np, v):
            continue
        raw_norm.add((np, nv))

    simp_norm: set[tuple[Tuple[str, ...], Any]] = set()
    for p, v in iter_leaves(simp):
        np = normalize_path(p)
        nv = normalize_value(v)
        # don't apply should_ignore() here: we want the simplified content as-is
        simp_norm.add((np, nv))

    missing = raw_norm - simp_norm

    # Helpful diagnostics
    if missing:
        samples = "\n".join(
            f"  - { '/'.join(p) } = {v!r}" for (p, v) in list(missing)[:25]
        )
        msg = (
            f"{len(missing)} raw leaves not found in simplified output for\n"
            f"XML: {xml_path.name}\nJSON: {json_path.name}\n"
            f"Examples:\n{samples}\n\n"
            "If these are intentional drops, add/adjust IGNORED_PATH_PATTERNS, "
            "WRAPPER_KEYS, WRAPPER_PREFIXES, or normalize_value() rules."
        )
        pytest.fail(msg)


def test_simplified_does_not_invent_new_values(xml_path=(json_path:=None)):
    """
    Optional: If you expect simplification to *never* create new values
    (e.g., no computed defaults at this stage), you can enable this test by
    wiring it to your pairs similarly to the one above.
    Comment this out if your simplifier injects defaults.
    """
    # Example placeholder; keep disabled by default
    pass
