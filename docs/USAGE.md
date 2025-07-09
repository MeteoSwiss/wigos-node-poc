# ACDD Metadata Handling - Usage Guide

This guide explains how to use the `ACDD` class provided in `acdd.py` to manage metadata according to the [Attribute Convention for Data Discovery 1.3](https://wiki.esipfed.org/Attribute_Convention_for_Data_Discovery_1-3).

---

## 📦 Loading Metadata

You can load metadata from various sources. All loader methods return a new `ACDD` instance.

### From JSON
```python
from acdd.acdd import ACDD

acdd = ACDD.from_json_file("data/record.json")
```

### From YAML
```python
acdd = ACDD.from_yaml_file("data/record.yaml")
```

### From GeoJSON
```python
acdd = ACDD.from_geojson_file("data/record.geojson")
```

---

## 📤 Exporting Metadata

You can export ACDD metadata into different formats:

### To JSON
```python
acdd.export("output/record.json", format="json")
```

### To YAML
```python
acdd.export("output/record.yaml", format="yaml")
```

### To GeoJSON
Requires geospatial bounds (`geospatial_lat_min`, etc.)
```python
acdd.export("output/record.geojson", format="geojson")
```

---

## 🌍 GeoJSON Export Notes

To enable `to_geojson()` or `export(..., format="geojson")`, the following attributes must be set:

- `geospatial_lat_min`
- `geospatial_lat_max`
- `geospatial_lon_min`
- `geospatial_lon_max`

These can be strings (e.g. `"5.0"`) or floats (e.g. `5.0`).

---

## ✅ Validation

`ACDD._validate_keys()` checks your metadata for unknown attribute names and returns a dictionary of invalid keys.

```python
warnings = acdd._validate_keys()
if warnings:
    print("Invalid ACDD attributes found:", warnings)
```

---

## 🧪 Testing

Tests are written using `pytest` and assume a test CSV attribute template file in:

```
tests/data/acdd_attributes.csv
```

To run all tests with coverage:

```bash
pytest --cov=acdd
```

---

## 🧱 Developer Notes

See the top of `acdd.py` for developer documentation on method types and design patterns used.
