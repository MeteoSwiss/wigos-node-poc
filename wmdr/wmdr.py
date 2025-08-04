from __future__ import annotations

import json
import warnings
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union

import xmltodict
import yaml

from acdd.acdd import ACDD
from utils.utils import load_mapping_csv


@dataclass
class WMDR20:
    """
    WMDR 2.0 metadata wrapper to manage ACDD-based records with hierarchical structure.

    - `record`: an ACDD-compliant metadata record
    - `parent_id`: reference to parent metadata record
    - `children`: list of subordinate records or file paths
    """
    record: ACDD
    parent_id: Optional[str] = None
    children: List[Union[str, 'WMDR20']] = field(default_factory=list)

    def add_child(self, child: Union[str, 'WMDR20']) -> None:
        """Attach a subordinate record or reference."""
        self.children.append(child)

    def set_parent(self, parent_id: str) -> None:
        """Link to a parent record by ID or path."""
        self.parent_id = parent_id

    def to_dict(self) -> dict:
        """Convert to nested dictionary representation."""
        return {
            "record": self.record.to_dict(),
            "parent_id": self.parent_id,
            "children": [
                c if isinstance(c, str) else c.to_dict() for c in self.children
            ]
        }

    def to_json(self) -> str:
        """Export full hierarchy as JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_yaml(self) -> str:
        """Export full hierarchy as YAML string."""
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_dict(cls, d: dict) -> 'WMDR20':
        """Reconstruct hierarchy from dictionary."""
        children = d.get("children", [])
        parsed_children = [
            c if isinstance(c, str) else WMDR20.from_dict(c)
            for c in children
        ]
        return cls(
            record=ACDD.from_dict(d["record"]),
            parent_id=d.get("parent_id"),
            children=parsed_children
        )

    @classmethod
    def from_json_file(cls, path: str) -> 'WMDR20':
        """Load a WMDR20 record from a JSON file."""
        with open(path) as f:
            d = json.load(f)
        return cls.from_dict(d)

    @classmethod
    def from_yaml_file(cls, path: str) -> 'WMDR20':
        """Load a WMDR20 record from a YAML file."""
        with open(path) as f:
            d = yaml.safe_load(f)
        return cls.from_dict(d)

    @staticmethod
    def parse_wmdr10_xml(xml_path: Union[str, Path]) -> dict:
        """
        Parse a WMDR 1.0 XML file into a dictionary using xmltodict.

        Args:
            xml_path (Union[str, Path]): Path to the WMDR XML file.

        Returns:
            dict: Parsed WMDR XML content.
        """
        with open(xml_path, "rb") as f:
            parsed = xmltodict.parse(f, process_namespaces=True)
        return parsed

    @staticmethod
    def strip_ns_keys(d: dict) -> dict:
        """
        Recursively remove XML namespaces from dictionary keys.

        Args:
            d (dict): Input dictionary.

        Returns:
            dict: Dictionary with stripped keys.
        """
        if isinstance(d, dict):
            return {k.split(":")[-1]: WMDR20.strip_ns_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [WMDR20.strip_ns_keys(i) for i in d]
        else:
            return d

    @classmethod
    def from_wmdr10(cls, xml_path: Union[str, Path]) -> 'WMDR20':
        """
        Convert WMDR 1.0 XML to WMDR20 instance with ACDD record.

        Args:
            xml_path (Union[str, Path]): Path to the WMDR 1.0 XML file.

        Returns:
            WMDR20: WMDR20 instance containing mapped ACDD metadata.
        """
        raw_data = cls.parse_wmdr10_xml(xml_path)
        data = cls.strip_ns_keys(raw_data)
        rec = data.get("WIGOSMetadataRecord", {})
        facility = rec.get("facility", {})

        acdd_attrs = {
            "title": facility.get("name"),
            "summary": facility.get("description"),
            "geospatial_lat_min": facility.get("geoLocation", {}).get("latitude"),
            "geospatial_lat_max": facility.get("geoLocation", {}).get("latitude"),
            "geospatial_lon_min": facility.get("geoLocation", {}).get("longitude"),
            "geospatial_lon_max": facility.get("geoLocation", {}).get("longitude"),
        }

        # Remove None values and warn
        acdd_clean = {}
        for k, v in acdd_attrs.items():
            if v is not None:
                acdd_clean[k] = v
            else:
                warnings.warn(f"Missing value for '{k}' in WMDR10 -> ACDD mapping")

        acdd = ACDD.from_dict(acdd_clean)
        return cls(record=acdd)


class WMDR10:
    """
    WMDR10 provides a parser and serializer for WMO WMDR 1.0 metadata records.

    Supports input as a file path, raw XML string, or pre-parsed dictionary.
    """

    def __init__(self, source: str | Path | dict, *, source_type: str = "file", simplify: bool = True):
        """
        Initialize a WMDR10 instance from a file path, XML string, or dictionary.

        Args:
            source (str | Path | dict): The input data. Its interpretation depends on `source_type`:
                - 'file': path to XML file
                - 'xml': raw XML string
                - 'dict': already-parsed metadata dictionary
            source_type (str, optional): One of {'file', 'xml', 'dict'}.
                Determines how `source` is interpreted. Defaults to 'file'.
            simplify (bool, optional): Whether to simplify the parsed metadata. Defaults to True.

        Raises:
            ValueError: If `source_type` is invalid or parsing fails.
        """
        if source_type == "file":
            source = Path(source)
            with source.open("r", encoding="utf-8") as f:
                self.data = xmltodict.parse(f.read(), process_namespaces=False)

        elif source_type == "xml":
            self.data = xmltodict.parse(source, process_namespaces=False)

        elif source_type == "dict":
            if not isinstance(source, dict):
                raise ValueError("When using source_type='dict', source must be a dict.")
            self.data = source

        else:
            raise ValueError(f"Invalid source_type: {source_type!r}. Must be 'file', 'xml', or 'dict'.")

        if simplify:
            self._simplify()

    def _simplify(self) -> None:
        """
        Simplify self.data in place by performing the following steps:

        I. Namespace Handling
        1. Strip all XML namespaces, including known prefixes and @xmlns entries

        II. Structural Pruning
        2. Keep only 'headerInformation' and 'facility' under 'WIGOSMetadataRecord'
        3. Remove any key named 'boundedBy' (case-insensitive)
        4. Remove any 'type': 'simple' or '@xlink:type': 'simple' entries

        III. Flatten Atomic Wrappers
        5. Replace {'CharacterString': value} → value
        6. Replace {'@xlink:href': value} → value
        7. Replace {'@codeSpace': value} → value
        8. Replace {'@codeSpace': ..., '#text': ...} → '#text'
        9. Replace {'@xsi:nil': 'true'} → None
        10. Replace {'@codeList': ..., '@codeListValue': ...} → '@codeList'
        11. Replace {'pos': value} → value

        IV. Structural Unwrapping
        12. Unwrap {'foo': {'Foo': {...}}} and {'Foo': {'foo': {...}}} if key names match case-insensitively
        13. Unwrap ISO containers like {'CI_*': {...}}, {'MD_*': {...}}, etc.
            Note: This step only applies when ISO container is nested under another key
        14. Unwrap {'TimePeriod': {...}} inside 'validPeriod'
        15. Unwrap top-level structures and list entries with single-key containers:
            'Process', 'GeospatialLocation', 'Point', 'DataGeneration', 'ResponsibleParty',
            'ObservingFacility', 'ProgramAffiliation', 'Header', 'ObservingCapability', 'OM_Observation',
            'ReportingStatus', 'linkage'
        16. Rename 'headerInformation' to 'header'
        17. Rename {'linkage': {'URL': value}} to {'url': value}
        18. Unwrap symmetric keys within lists: [{'Foo': {...}}] → [{...}]
        19. Unwrap [{'Foo': value}] → [value] if 'Foo' matches parent key or unwrap to list of dicts otherwise

        V. Cleanup
        20. Recursively simplify nested dictionaries and lists
        21. Replace empty dictionaries {} with None
        """

        NAMESPACES_TO_STRIP = {
            'gml', 'xlink', 'wmdr', 'gco', 'gmd', 'ns6', 'ns7',
            'om', 'ns9', 'sam', 'sams', 'xsi'
        }

        ISO_PREFIXES = ("CI_", "MD_", "OM_", "DQ_", "EX_", "GM_", "LI_", "PT_", "RS_", "SV_")

        UNWRAP_KEYS = {
            'Point', 'GeospatialLocation', 'Process', 'DataGeneration', 'ResponsibleParty',
            'ObservingFacility', 'ProgramAffiliation', 'Header', 'ObservingCapability',
            'OM_Observation', 'ReportingStatus', 'linkage'
        }

        def strip_ns(obj):
            if isinstance(obj, dict):
                new_dict = {}
                for k, v in obj.items():
                    if k.startswith('@xmlns') or k == 'xmlns':
                        continue
                    key_base = k.split(':')[-1] if ':' in k else k
                    ns_prefix = k.split(':')[0] if ':' in k else ''
                    if ns_prefix in NAMESPACES_TO_STRIP:
                        k = key_base
                    elif '}' in k:
                        k = k.split('}')[-1]
                    new_dict[k] = strip_ns(v)
                return new_dict
            elif isinstance(obj, list):
                return [strip_ns(item) for item in obj]
            return obj

        def unwrap_single_key_dict(v, parent_key=None):
            if isinstance(v, dict) and len(v) == 1:
                key, val = next(iter(v.items()))
                if key in UNWRAP_KEYS:
                    return simplify_dict(val)
            if parent_key in UNWRAP_KEYS and isinstance(v, dict):
                return simplify_dict(v)
            return v

        def simplify_atomic_wrappers(k, v):
            if isinstance(v, dict):
                if v.get('@xsi:nil') == 'true':
                    return None
                if '@xlink:href' in v:
                    return v['@xlink:href']
                if '@codeSpace' in v and '#text' in v:
                    return v['#text']
                if set(v.keys()) == {'@codeList', '@codeListValue'}:
                    return v['@codeList']
                if list(v.keys()) == ['pos']:
                    return v['pos']
                if list(v.keys()) == ['CharacterString']:
                    return v['CharacterString']
                if k == 'validPeriod' and isinstance(v.get('TimePeriod'), dict):
                    return simplify_dict(v['TimePeriod'])
                if k == 'linkage' and list(v.keys()) == ['URL']:
                    return {'url': v['URL']}
            return v

        def simplify_dict(d):
            if not isinstance(d, dict):
                return d

            if "WIGOSMetadataRecord" in d:
                d = d["WIGOSMetadataRecord"]
            if '@xsi:schemaLocation' in d:
                d.pop('@xsi:schemaLocation')

            d = {
                k: v for k, v in d.items()
                if not ((k == 'type' or k == '@xlink:type') and v == 'simple') and k.lower() != 'boundedby'
            }

            for k in list(d):
                d[k] = simplify_atomic_wrappers(k, d[k])

            for k in list(d):
                v = d[k]
                if isinstance(v, dict) and len(v) == 1:
                    inner_k = next(iter(v))
                    if inner_k.lower() == k.lower():
                        d[k] = simplify_dict(v[inner_k])

            for k in list(d):
                if isinstance(d[k], dict):
                    d[k] = unwrap_single_key_dict(d[k], parent_key=k)

            for k in list(d):
                v = d[k]
                if isinstance(v, dict) and len(v) == 1:
                    inner_k = next(iter(v))
                    if any(inner_k.startswith(prefix) for prefix in ISO_PREFIXES):
                        d[k] = simplify_dict(v[inner_k])

            for k in list(d):
                v = d[k]
                if isinstance(v, list):
                    new_list = []
                    for item in v:
                        if isinstance(item, dict) and len(item) == 1:
                            inner_k = next(iter(item))
                            inner_val = item[inner_k]
                            if inner_k.lower() == k.lower():
                                item = simplify_dict(inner_val)
                            elif isinstance(inner_val, dict):
                                item = {inner_k.lower(): simplify_dict(inner_val)}
                            else:
                                item = {inner_k.lower(): inner_val}
                        elif isinstance(item, dict):
                            item = simplify_dict(item)
                        new_list.append(item)
                    d[k] = new_list
                elif isinstance(v, dict):
                    d[k] = simplify_dict(v)

            for k in list(d):
                if isinstance(d[k], dict) and not d[k]:
                    d[k] = None

            if 'headerInformation' in d:
                d['header'] = d.pop('headerInformation')

            return d

        self.data = strip_ns(self.data)
        self.data = simplify_dict(self.data)


    def to_xml(self, output_path: str | Path = None, pretty: bool = True, encoding: str = "utf-8") -> str | None:
        """
        Serialize the internal dictionary to XML.

        Args:
            output_path (str | Path, optional): If specified, write to this path. Otherwise return XML as string.
            pretty (bool): Pretty-print the output. Defaults to True.
            encoding (str): Encoding used when writing to file. Defaults to 'utf-8'.

        Returns:
            str | None: XML string if not written to file.
        """
        xml_str = xmltodict.unparse(self.data, pretty=pretty)

        if output_path:
            Path(output_path).write_text(xml_str, encoding=encoding)
            return None
        return xml_str


    def to_json(self) -> str:
        """
        Convert the WMDR metadata to a JSON-formatted string.

        Returns:
            str: JSON string representation of the metadata.
        """
        return json.dumps(self.data, indent=2)


    def to_yaml(self) -> str:
        """
        Convert the WMDR metadata to a YAML-formatted string.

        Returns:
            str: YAML string representation of the metadata.
        """
        return yaml.dump(self.data, allow_unicode=True, sort_keys=False)


    def export(self, base_path: str | Path, formats: list[str] = ["json", "yaml"]) -> list[Path]:
        """
        Export the WMDR metadata to one or more file formats (json, yaml).

        Args:
            base_path (str | Path): Base output path without extension.
            formats (list[str]): List of formats to export ('json', 'yaml').

        Returns:
            list[Path]: Paths to the generated files.

        Raises:
            ValueError: If unsupported format is requested.
        """
        base_path = Path(base_path)
        exported_files = []

        for fmt in formats:
            if fmt == "json":
                path = base_path.with_suffix(".json")
                path.write_text(self.to_json(), encoding="utf-8")
            elif fmt == "yaml":
                path = base_path.with_suffix(".yaml")
                path.write_text(self.to_yaml(), encoding="utf-8")
            else:
                raise ValueError(f"Unsupported format: {fmt}")
            exported_files.append(path)

        return exported_files


    def facility_to_acdd(self, mapping_file: Path | str) -> ACDD:
        """
        Convert the ObservingFacility section of the simplified WMDR10 structure to an ACDD-compliant record.

        Args:
            mapping_file (Path | str): Path to the mapping CSV file.

        Returns:
            ACDD: ACDD-compliant metadata object.
        """
        mappings = load_mapping_csv(mapping_file)

        result: dict[str, Any] = {}
        keywords: list[dict[str, Any]] = []

        for row in mappings:
            attr = row["acdd_attribute"]
            default = row.get("default", "").strip() or None

            # Handle keyword attributes
            if attr == "keywords":
                values = []
                if row["wmdr10_simplified_path"]:
                    value = self._create_json_stub(self.data, row)
                    if value:
                        values.extend(value if isinstance(value, list) else [value])
                if default:
                    try:
                        values.append(json.loads(default))
                    except Exception:
                        values.append(default)
                keywords.extend(values)

            # Handle geospatial attributes
            elif attr.startswith("geospatial_"):
                if row["wmdr10_simplified_path"]:
                    geo = self._create_geospatial_attributes(row)
                    if geo:
                        result.update(geo)
                if default:
                    result[attr] = default

            # Handle regular attributes
            else:
                values = []
                if row["wmdr10_simplified_path"]:
                    value = self._create_json_stub(self.data, row)
                    if value is not None:
                        values.append(value)
                if default:
                    values.append(default)
                if values:
                    if attr in result:
                        if not isinstance(result[attr], list):
                            result[attr] = [result[attr]]
                        result[attr].extend(values)
                    else:
                        result[attr] = values if len(values) > 1 else values[0]

        # Promote selected keyword values to ACDD attributes
        result['project'] = [ele for ele in keywords if 'programAffiliation' in ele]

        # Store remaining keywords as list of JSON stubs
        result["keywords"] = [ele for ele in keywords if 'programAffiliation' not in ele]

        return ACDD(result)


    def observation_to_acdd(self, mapping_file: Path | str) -> ACDD:
        raise NotImplementedError


    def _create_json_stub(self, raw: dict, row: dict) -> dict | str | None:
        """
        Create a JSON-compatible stub from simplified WMDR10 data.

        Args:
            raw (dict): Simplified WMDR10 data (i.e. self.data)
            row (dict): A single row from the mapping file with at least:
                - 'wmdr10_simplified_path': path to value(s) (slash-separated)
                - 'acdd_keywords_key': optional, to group as keyword JSON stub

        Returns:
            dict | str | None: extracted stub, flat value, or None
        """
        path = row["wmdr10_simplified_path"].split("/")
        key = row.get("keywords_key")

        def walk(obj, path):
            if not path:
                return obj

            part, *rest = path

            if isinstance(obj, dict):
                if part not in obj:
                    return None
                return walk(obj[part], rest)

            elif isinstance(obj, list):
                result = []
                for item in obj:
                    walked = walk(item, path)
                    if walked is not None:
                        result.append(walked)
                return result if result else None

            return None

        value = walk(deepcopy(raw), path)
        if value is None:
            return None

        # Handle JSON stubs
        if key:
            def to_stub(entry):
                if isinstance(entry, dict):
                    stub = {k: v for k, v in entry.items() if k not in ("beginPosition", "endPosition")}
                    dates = {k: entry[k] for k in ("beginPosition", "endPosition") if k in entry}
                    if dates:
                        return {dates.get("beginPosition", "unknown"): stub}
                    return stub
                return entry

            if isinstance(value, list):
                grouped = defaultdict(dict)
                for item in value:
                    stub = to_stub(item)
                    if isinstance(stub, dict):
                        for k, v in stub.items():
                            grouped[k] = v
                return {key: grouped if grouped else value}
            return {key: to_stub(value)}

        # Otherwise return flat string or object
        return value


    def _create_geospatial_attributes(self, mapping_row: dict[str, str], delta: float=0.001) -> dict[str, float | str]:
        """
        Extract geolocation bounding box info from pos string in the mapping and convert to ACDD fields.

        Args:
            mapping_rows (list[dict[str, str]]): List of mapping rows.
            delta(float, optional): Slack applied to generate geospatial bounding box from single geolocation

        Returns:
            dict[str, Any]: Geospatial ACDD attributes.
        """
        def geospatial_bounds(lat, lon, d):
            return f"POLYGON(({lat-d} {lon-d}, {lat-d} {lon+d}, {lat+d} {lon+d}, {lat+d} {lon-d}, {lat-d} {lon-d}))"
        
        result = dict()

        required_keys = ["acdd_attribute", "wmdr10_simplified_path", "default"]

        if not all(k in mapping_row for k in required_keys):
            # [TODO] issue warning
            warnings.warn("_create_geospatial_attributes: some required_keys are missing.")
            return  # skip incomplete rows

        if not mapping_row["acdd_attribute"].startswith("geospatial_"):
            return

        # generate geospatial_ elements
        if mapping_row["wmdr10_simplified_path"].endswith("geospatialLocation"):
            path = mapping_row["wmdr10_simplified_path"].split("/")
            val = self._resolve_path_recursive(self.data, path)
            if isinstance(val, list):
                # [TODO] Do not select the first element, but look for the one with the newest beginPosition
                val = val[0]['geoLocation']
            if isinstance(val, str):
                try:
                    lat_str, lon_str, *alt_str = val.strip().split()
                    lat, lon = float(lat_str), float(lon_str)
                    alt = float(alt_str[0]) if alt_str else None
                    result = {
                        "geospatial_lat_min": lat - delta,
                        "geospatial_lat_max": lat + delta,
                        "geospatial_lon_min": lon - delta,
                        "geospatial_lon_max": lon + delta,
                        "geospatial_bounds": geospatial_bounds(lat, lon, delta),
                        "geospatial_bounds_crs": "WGS84",
                        "geospatial_bounds_vertical_crs": "EPSG:5829",
                        "geospatial_lat_units": "degree_north",
                        "geospatial_lon_units": "degree_east",
                        "geospatial_vertical_positive": "up",
                    }
                    if alt is not None:
                        result.update({
                            "geospatial_vertical_min": alt - 5000 * delta,
                            "geospatial_vertical_max": alt + 5000 * delta,
                            "geospatial_bounds_vertical_crs": "EPSG:5829",
                            "geospatial_vertical_units": "EPSG:4979",
                        })
                    return result
                except ValueError:
                    return
        return {}


    def _resolve_path_recursive(self, obj: Any, path_parts: list[str]) -> Any:
        """
        Recursively resolve a list of path segments in a nested dictionary/list structure.

        Args:
            obj (Any): The current node in the traversal.
            path_parts (list[str]): Remaining path segments to resolve.

        Returns:
            Any: The resolved value or None if not found.
        """
        if not path_parts:
            return obj

        if isinstance(obj, list):
            results = []
            for item in obj:
                r = self._resolve_path_recursive(item, path_parts.copy())
                if isinstance(r, list):
                    results.extend(r)
                elif r is not None:
                    results.append(r)
            return results if results else None

        elif isinstance(obj, dict):
            head, *tail = path_parts
            value = obj.get(head)
            if value is None:
                # Handle @key or key@ patterns
                for key in obj.keys():
                    if key.endswith(head) or key.startswith(head):
                        value = obj[key]
                        break
            return self._resolve_path_recursive(value, tail)

        return None
