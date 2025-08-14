from __future__ import annotations

import json
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, List, Optional, Union

import polars as pl
import yaml
from datetime import datetime, timezone


@dataclass
class ACDD:
    """
    Hybrid ACDD class that separates attribute specification from metadata storage.
    Loads templates from a CSV if not explicitly defined.

    - Validates ACDD keys
    - Stores user attributes
    - Supports export to JSON, YAML, GeoJSON, and ZIP bundle

    Author: joerg.klausen@meteoswiss.ch, together with ChatGPT
    
    Developer Notes - Method Usage in ACDD Class
    ============================================

    This class uses a mix of `@classmethod` and instance methods for clarity and best practice:

    1. @classmethod
    - Used for alternate constructors such as `from_json_file()`, `from_yaml_file()`, and `from_geojson_file()`.
    - These methods return a *new* instance of ACDD and do not mutate an existing instance.
    - Preferred usage:
        acdd = ACDD.from_json_file("example.json")

    2. Instance Methods
    - Used for operations on existing instances, such as `to_geojson()`, `to_json()`, and `to_yaml()`.
    - These rely on `self.attributes` being populated, typically via one of the class-level loaders.

    3. Why not do `acdd = ACDD(); acdd.from_json_file(...)`?
    - `from_json_file()` returns a new object and does *not* update the existing one.
    - Always assign the returned object: `acdd = ACDD.from_json_file(...)`

    4. Summary

    | Method Type         | Decorator      | Purpose                              | Call Form                           |
    |---------------------|----------------|--------------------------------------|-------------------------------------|
    | Alternate constructor | @classmethod | Create new instance from a file      | ACDD.from_json_file(...)            |
    | Operation on instance | none         | Convert/export instance data         | acdd.to_geojson(), acdd.to_yaml()   |
    | Static utility        | @staticmethod (unused) | Stateless helpers              | ACDD.helper_function(...)           |
    """
    highly_recommended_template: ClassVar[dict] = {}
    recommended_template: ClassVar[dict] = {}
    suggested_template: ClassVar[dict] = {}
    highly_recommended_variable_template: ClassVar[dict] = {}

    attributes: dict[str, str] = field(default_factory=dict)

    def __init__(self, attributes: dict[str, str] | None = None, csv_path: Path | None = None) -> None:
        if not (
            ACDD.highly_recommended_template
            or ACDD.recommended_template
            or ACDD.suggested_template
            or ACDD.highly_recommended_variable_template
        ):
            default_path = csv_path or Path(__file__).parent / "acdd_attributes.csv"
            self.load_templates_from_csv(default_path)

        attributes = attributes or {}
        self._invalid_keys = self._validate_keys(attributes)
        self.attributes = attributes

    @classmethod
    def load_templates_from_csv(cls, csv_path: str | Path) -> None:
        """
        Load ACDD attribute templates from a CSV file with columns:
        category, name, default, description
        """
        csv_path = Path(csv_path)
        df = pl.read_csv(csv_path)

        cls.highly_recommended_template = {
            row["name"]: None if row["default"] in [None, ""] else row["default"]
            for row in df.filter(pl.col("category") == "highly_recommended").to_dicts()
        }
        cls.recommended_template = {
            row["name"]: None if row["default"] in [None, ""] else row["default"]
            for row in df.filter(pl.col("category") == "recommended").to_dicts()
        }
        cls.suggested_template = {
            row["name"]: None if row["default"] in [None, ""] else row["default"]
            for row in df.filter(pl.col("category") == "suggested").to_dicts()
        }
        cls.highly_recommended_variable_template = {
            row["name"]: None if row["default"] in [None, ""] else row["default"]
            for row in df.filter(pl.col("category") == "highly_recommended_variable").to_dicts()
        }

    def _validate_keys(self, d: dict) -> list[str]:
        """Return invalid keys not found in ACDD templates, issuing a warning."""
        valid_keys = (
            list(self.highly_recommended_template)
            + list(self.recommended_template)
            + list(self.suggested_template)
            + list(self.highly_recommended_variable_template)
        )
        invalid = [key for key in d if key not in valid_keys]
        if invalid:
            warnings.warn(f"Invalid ACDD keys: {invalid}", UserWarning)
        return invalid

    def to_json(self) -> str:
        """Serialize attributes to formatted JSON string."""
        return json.dumps(self.attributes, indent=2)

    def to_yaml(self) -> str:
        """Serialize attributes to YAML string."""
        return yaml.dump(self.attributes, sort_keys=False)

    def to_geojson(self) -> dict:
        """Convert spatial ACDD attributes to a GeoJSON Feature."""
        lat_min = self.attributes.get("geospatial_lat_min")
        lat_max = self.attributes.get("geospatial_lat_max")
        lon_min = self.attributes.get("geospatial_lon_min")
        lon_max = self.attributes.get("geospatial_lon_max")

        if lat_min and lat_max and lon_min and lon_max:
            lat_center = (float(lat_min) + float(lat_max)) / 2
            lon_center = (float(lon_min) + float(lon_max)) / 2
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lat_center, lon_center]
                },
                "properties": self.attributes
            }
        else:
            raise ValueError("Missing lat/lon bounds for GeoJSON export")

    def to_oasis(
        self,
        href: str = "dummy",
        version: str = "v04",
        *,
        content_encoding: str = "utf-8",
        content_standard_name: str = "air_temperature",
        content_unit: str = "degC",
        content_size: int = 5,
        content_value: str = "1",
    ) -> dict:
        feature = self.to_geojson()

        # Convert Point coords: [lon, lat] -> {"lon": lon, "lat": lat}
        geom = feature.get("geometry")
        if isinstance(geom, dict) and geom.get("type") == "Point":
            coords = geom.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lat, lon = coords[0], coords[1]
                try:
                    lon = float(lon); lat = float(lat)
                except (TypeError, ValueError):
                    pass
                geom["coordinates"] = {"lat": lat, "lon": lon}

        feature["properties"]["content"] = {
            "encoding": content_encoding,
            "standard_name": content_standard_name,
            "unit": content_unit,
            "size": content_size,
            "value": content_value,
        }
        feature["properties"] |= {
            "datetime": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "function": "sum",
            "period": "PT1M",
            "level": "1",
        }
        
        feature["links"] = [{"href": href, "rel": "canonical"}]
        feature["version"] = version
        return feature


    def export(self, path: Path, fmt: str = "json") -> Path:
        """Export the ACDD record to JSON, YAML, or GeoJSON file."""
        path = Path(path)
        content = {
            "json": self.to_json,                                    # unchanged
            "yaml": self.to_yaml,                                    # unchanged
            "geojson": lambda: json.dumps(self.to_geojson(), indent=2),
            # OASIS: minified, no newlines, no spaces around commas/colons
            "oasis":  lambda: json.dumps(self.to_oasis(),
                                        ensure_ascii=False,
                                        separators=(",", ":")),
        }
        ext = {"json": ".json", "yaml": ".yaml", "geojson": ".geojson", "oasis": ".json"}[fmt]
        output_path = path.with_suffix(ext)
        output_path.write_text(content[fmt](), encoding="utf-8")
        return output_path


    def export_bundle(self, bundle_path: Path) -> Path:
        """Export all supported formats to a ZIP bundle."""
        bundle_path = Path(bundle_path)
        with zipfile.ZipFile(bundle_path, "w") as zf:
            zf.writestr("acdd.json", self.to_json())
            zf.writestr("acdd.yaml", self.to_yaml())
            try:
                zf.writestr("acdd.geojson", json.dumps(self.to_geojson(), indent=2))
            except Exception as e:
                warnings.warn(f"Skipping GeoJSON export: {e}")
        return bundle_path

    def from_geojson(self, geojson: dict) -> None:
        """Initialize attributes from a GeoJSON Feature."""
        if "properties" in geojson:
            self.attributes.update(geojson["properties"])

    @classmethod
    def to_feature_collection(cls, features: list[dict]) -> dict:
        """Wrap multiple GeoJSON features into a FeatureCollection."""
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> ACDD:
        """Create ACDD from dictionary."""
        return cls(attributes=d)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> ACDD:
        """Create ACDD from YAML string."""
        d = yaml.safe_load(yaml_str)
        return cls.from_dict(d)

    @classmethod
    def from_json(cls, json_str: str) -> ACDD:
        """Create ACDD from JSON string."""
        d = json.loads(json_str)
        return cls.from_dict(d)

    @classmethod
    def from_json_file(cls, path: str | Path) -> ACDD:
        """Load ACDD metadata from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> ACDD:
        """Load ACDD metadata from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())

    @classmethod
    def from_geojson_file(cls, path: str | Path) -> ACDD:
        """Load ACDD metadata from a GeoJSON Feature file."""
        with open(path, "r", encoding="utf-8") as f:
            geo = json.load(f)
            acdd = cls()
            acdd.from_geojson(geo)
            return acdd
        