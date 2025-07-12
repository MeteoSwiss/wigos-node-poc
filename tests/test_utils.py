import json
from pathlib import Path

import pytest

from utils.utils import (load_mapping_csv,
                         parse_geolocation_to_acdd_fields)


@pytest.mark.parametrize("mapping_name", [
    "wmdr10_facility_to_acdd13",
    # Add additional mappings here as needed
])
def test_load_real_mapping_csv(mapping_name):
    """
    Test that the specified mapping CSV can be loaded and contains required columns.
    """
    try:
        df = load_mapping_csv(mapping_name)
    except FileNotFoundError as e:
        raise AssertionError(
            f"\n❌ Mapping file not found: '{mapping_name}.csv'\n"
            f"🔍 Expected under 'mappings/' directory.\n"
            f"💡 Make sure the file exists and is correctly named.\n"
            f"Original error: {e}"
        )

    if df.shape[0] == 0:
        raise AssertionError(
            f"\n❌ Mapping file '{mapping_name}.csv' is empty.\n"
            f"💡 Add at least one mapping row with valid WMDR1.0 and ACDD13 keys."
        )

    required_columns = ["wmdr10_path", "acdd_attribute"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise AssertionError(
            f"\n❌ Mapping file '{mapping_name}.csv' is missing required columns: {missing}\n"
            f"💡 Ensure the CSV includes these columns exactly: {required_columns}"
        )


def test_parse_geolocation_to_acdd_fields_valid():
    pos = "1.23 4.56 789"
    result = parse_geolocation_to_acdd_fields(pos)
    assert result["geospatial_lat_min"] == pytest.approx(1.229)
    assert result["geospatial_lat_max"] == pytest.approx(1.231)
    assert result["geospatial_lon_min"] == pytest.approx(4.559)
    assert result["geospatial_lon_max"] == pytest.approx(4.561)
    assert result["geospatial_vertical_min"] == 789
    assert result["geospatial_vertical_max"] == 789


def test_parse_geolocation_to_acdd_fields_invalid():
    with pytest.raises(ValueError) as e:
        parse_geolocation_to_acdd_fields("1.0 2.0")  # Missing third value
    assert "Invalid gml:pos value" in str(e.value)




# def test_build_acdd_comment_field():
#     data = {"id": "abc", "note": "xyz"}
#     result = build_acdd_comment_field(data)
#     parsed = json.loads(result)
#     assert parsed["id"] == "abc"
#     assert parsed["note"] == "xyz"
