import json
from pathlib import Path

import pytest

from utils.utils import (load_mapping_csv)


@pytest.mark.parametrize("mappings_file", [
    "mappings/wmdr10_facility_to_acdd13.csv",
    # Add additional mappings here as needed
])
def test_load_real_mapping_csv(mappings_file):
    """
    Test that the specified mapping CSV can be loaded and contains required columns.
    """
    try:
        lst = load_mapping_csv(mappings_file)
    except FileNotFoundError as e:
        raise AssertionError(
            f"\n❌ Mapping file not found: '{mappings_file}'\n"
            f"🔍 Expected under 'mappings/' directory.\n"
            f"💡 Make sure the file exists and is correctly named.\n"
            f"Original error: {e}"
        )

    if len(lst) == 0:
        raise AssertionError(
            f"\n❌ Mapping file '{mappings_file}' is empty.\n"
            f"💡 Add at least one mapping row with valid WMDR1.0 and ACDD13 keys."
        )

    required_columns = ["wmdr10_simplified_path", "acdd_attribute"]
    missing = [col for col in required_columns if col not in lst[0].keys()]
    if missing:
        raise AssertionError(
            f"\n❌ Mapping file '{mappings_file}' is missing required columns: {missing}\n"
            f"💡 Ensure the CSV includes these columns exactly: {required_columns}"
        )

