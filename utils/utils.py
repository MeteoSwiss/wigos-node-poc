import csv
from pathlib import Path


def load_mapping_csv(path: str | Path) -> list[dict]:
    """
    Load the WMDR10-to-ACDD mapping file into a list of dictionaries.

    Supports BOM-skipped UTF-8 files and ensures required keys are present.

    Returns:
        list of dict: each dict corresponds to one mapping row
    """
    required_keys = {"acdd_attribute", "wmdr10_simplified_path"}
    mappings = []

    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not required_keys.issubset(row):
                raise ValueError(f"Missing required column(s) in row: {row}")
            mappings.append(row)

    return mappings


def flatten_single_item_lists(d: dict[str, list[str]]) -> dict[str, str | list[str]]:
    """
    Convert single-element lists to strings to simplify JSON encoding.

    Args:
        d (dict): Input dictionary with values as list[str].

    Returns:
        dict: Cleaned dictionary with string or list values.
    """
    return {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in d.items()}
