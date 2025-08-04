import logging
from collections.abc import Iterable
# from copy import deepcopy
from pathlib import Path
from typing import Any

import xmltodict

# from utils.utils import strip_ns_keys


class WMDR10:
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
                self.data = xmltodict.parse(f.read(), process_namespaces=True)

        elif source_type == "xml":
            self.data = xmltodict.parse(source, process_namespaces=True)

        elif source_type == "dict":
            if not isinstance(source, dict):
                raise ValueError("When using source_type='dict', source must be a dict.")
            self.data = source

        else:
            raise ValueError(f"Invalid source_type: {source_type!r}. Must be 'file', 'xml', or 'dict'.")

        if simplify:
            self.simplify()


    # def __init__(self, path: Path):
    #     self.path = path
    #     self.logger = logging.getLogger(__name__)
    #     with path.open("rb") as f:
    #         raw = xmltodict.parse(f, process_namespaces=False)
    #     self.data = self.simplify(raw)

    def simplify(self, delimiter: str = ":") -> dict:
        """
        Simplify the internal metadata dictionary by:
        - Stripping namespace prefixes from keys
        - Removing unwanted fields ('schemaLocation', '@xmlns', 'boundedBy', {'type': 'simple'})

        Args:
            delimiter (str): Delimiter separating namespace prefixes. Defaults to ':'.

        Returns:
            dict: The simplified metadata dictionary.
        """
        def _simplify(obj: Any) -> Any:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    key = k.split(delimiter)[-1] if delimiter in k else k
                    if key in {"schemaLocation", "@xmlns"} or (key == "type" and v == "simple") or key == "boundedBy":
                        continue
                    simplified_value = _simplify(v)
                    if simplified_value is not None:
                        result[key] = simplified_value
                return result
            elif isinstance(obj, list):
                return [_simplify(item) for item in obj]
            else:
                return obj

        self.data = _simplify(self.data)
        return self.data


    # def simplify(self, raw: dict[str, Any]) -> dict[str, Any]:
    #     simplified = strip_ns_keys(raw)
    #     unwanted_keys = {"schemaLocation", "@xmlns"}

    #     def clean(obj):
    #         if isinstance(obj, dict):
    #             return {
    #                 k: clean(v)
    #                 for k, v in obj.items()
    #                 if k not in unwanted_keys and not (isinstance(v, dict) and v.get("nil") == "true")
    #             }
    #         elif isinstance(obj, list):
    #             return [clean(i) for i in obj]
    #         return obj

    #     return clean(simplified)

    def _resolve_path_recursive(self, data: Any, path: list[str]) -> Any:
        if not path:
            return data
        key = path[0]
        rest = path[1:]
        if isinstance(data, dict):
            if key in data:
                return self._resolve_path_recursive(data[key], rest)
            else:
                return []
        elif isinstance(data, list):
            results = []
            for item in data:
                resolved = self._resolve_path_recursive(item, path)
                if isinstance(resolved, list):
                    results.extend(resolved)
                else:
                    results.append(resolved)
            return results
        return []

    def _flatten_periods(self, d: dict) -> None:
        for key in list(d.keys()):
            if key in {"TimePeriod", "ReportingPeriod"} and isinstance(d[key], dict):
                inner = d.pop(key)
                for k, v in inner.items():
                    d[k] = v
            elif isinstance(d[key], dict):
                self._flatten_periods(d[key])

    def _flatten_href_fields(self, d: dict) -> None:
        for key, val in list(d.items()):
            if isinstance(val, dict) and set(val.keys()) == {"href"}:
                d[key] = val["href"]
            elif isinstance(val, dict):
                self._flatten_href_fields(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        self._flatten_href_fields(item)

    def _extract_json_stub(self, mapping_row: dict[str, str]) -> dict[str, Any]:
        wmdr_path = mapping_row["wmdr10_path"].strip().split("/")
        subpaths = [p.strip() for p in mapping_row["wmdr10_subpath"].split(",") if p.strip()]

        if len(wmdr_path) < 2:
            return {}

        container_key = wmdr_path[-2]
        leaf_key = wmdr_path[-1]

        containers = self._resolve_path_recursive(self.data, wmdr_path[:-1])
        if not containers:
            return {container_key: []}

        results = []
        for container in containers:
            if not isinstance(container, dict):
                continue  # skip non-dict containers

            branch = container.get(leaf_key)
            if not branch:
                continue

            branches = branch if isinstance(branch, list) else [branch]

            for b in branches:
                if not isinstance(b, dict):
                    continue  # skip non-dict branches

                item = {}
                for subpath in subpaths:
                    sp = subpath.split("/")
                    val = self._resolve_path_recursive(b, sp)
                    if isinstance(val, list):
                        val = val[0] if val else None

                    if isinstance(val, dict):
                        self._flatten_periods(val)
                        self._flatten_href_fields(val)

                    if isinstance(val, dict) and set(val.keys()) == {"href"}:
                        val = val["href"]

                    default_val = mapping_row.get("default", "").strip() or None
                    if (val is None or val == "") and default_val is not None:
                        val = default_val

                    item[sp[-1]] = val
                results.append(item)
        return {container_key: results}

    def facility_to_acdd(self, mapping_rows: list[dict[str, str]]) -> dict[str, Any]:
        acdd = {}
        for row in mapping_rows:
            attr = row["acdd_attribute"].strip()
            if not attr:
                continue

            if not row["wmdr10_path"].strip():
                default_val = row.get("default", "").strip()
                if default_val:
                    acdd[attr] = default_val
                continue

            stub = self._extract_json_stub(row)
            if not stub:
                continue

            val = stub.get(row["wmdr10_path"].split("/")[-2], [])
            if isinstance(val, list):
                val = [v for v in val if v not in (None, "")]
                if len(val) == 1:
                    val = val[0]
            acdd[attr] = val

        return acdd


    # def _extract_json_stub(self, mapping_row: dict[str, str]) -> dict[str, Any]:
    #     """
    #     General JSON stub extractor that handles both historical and non-historical WMDR10 mapping rows.

    #     Returns:
    #         dict[str, Any]: structured ACDD-compatible attribute
    #     """
    #     wmdr_path = mapping_row["wmdr10_path"].strip().split("/")
    #     subpaths = [p.strip() for p in mapping_row["wmdr10_subpath"].split(",") if p.strip()]

    #     if len(wmdr_path) < 2:
    #         return {}

    #     container_key = wmdr_path[-2]  # e.g., 'programAffiliation', 'surfaceCover', 'facilityType'
    #     leaf_key = wmdr_path[-1]       # e.g., 'ProgramAffiliation', 'SurfaceCover', 'FacilityType'

    #     containers = self._resolve_path_recursive(self.data, wmdr_path[:-1])
    #     if not containers:
    #         return {container_key: []}

    #     # Ensure containers are dicts
    #     if isinstance(containers, dict):
    #         containers = [containers]
    #     elif isinstance(containers, list):
    #         containers = [c for c in containers if isinstance(c, dict)]
    #     else:
    #         return {container_key: []}

    #     results = []
    #     for container in containers:
    #         branch = container.get(leaf_key)
    #         if not branch:
    #             continue
    #         if isinstance(branch, list):
    #             branches = branch
    #         else:
    #             branches = [branch]

    #         for b in branches:
    #             item = {}
    #             for subpath in subpaths:
    #                 sp = subpath.split("/")
    #                 val = self._resolve_path_recursive(b, sp)
    #                 if isinstance(val, list):
    #                     val = val[0] if val else None

    #                 # Flatten validPeriod and reportingPeriod
    #                 if sp[-1] in {"validPeriod", "reportingPeriod"} and isinstance(val, dict):
    #                     if "TimePeriod" in val:
    #                         tp = val.pop("TimePeriod")
    #                         val.update(tp)
    #                     elif "ReportingPeriod" in val:
    #                         rp = val.pop("ReportingPeriod")
    #                         val.update(rp)

    #                 # Replace {'href': val} with val
    #                 if isinstance(val, dict) and set(val) == {"href"}:
    #                     val = val["href"]

    #                 # Apply default if val is None or empty
    #                 default_val = mapping_row.get("default", "").strip() or None
    #                 if (val is None or val == "") and default_val is not None:
    #                     val = default_val

    #                 item[sp[-1]] = val
    #             results.append(item)

    #     return {container_key: results}

    # def facility_to_acdd(self, mapping_rows: list[dict[str, str]]) -> dict[str, Any]:
    #     acdd = {}
    #     for row in mapping_rows:
    #         attr = row["acdd_attribute"].strip()
    #         if not attr:
    #             continue

    #         if not row["wmdr10_path"].strip():
    #             # No path defined, use default directly
    #             default_val = row.get("default", "").strip()
    #             if default_val:
    #                 acdd[attr] = default_val
    #             continue

    #         stub = self._extract_json_stub(row)
    #         if not stub:
    #             continue

    #         # Flatten single-element lists
    #         val = stub.get(row["wmdr10_path"].split("/")[-2], [])
    #         if isinstance(val, list):
    #             val = [v for v in val if v not in (None, "")]
    #             if len(val) == 1:
    #                 val = val[0]
    #         acdd[attr] = val

    #     return acdd


    # def facility_to_acdd(self, mapping_rows: list[dict[str, str]]) -> dict[str, Any]:
    #     acdd = {}

    #     for row in mapping_rows:
    #         attr = row["acdd_attribute"].strip()
    #         if not attr:
    #             continue

    #         wmdr_path = row["wmdr10_path"].strip()
    #         subpath = row["wmdr10_subpath"].strip()
    #         default_val = row.get("default", "").strip() or None

    #         if attr == "keywords" or "programAffiliation" in wmdr_path or "surfaceCover" in wmdr_path:
    #             stub = self._extract_json_stub(row)
    #             container_key = wmdr_path.split("/")[-2]
    #             val = stub.get(container_key, [])
    #             if isinstance(val, list) and len(val) == 1:
    #                 val = val[0]
    #             acdd[attr] = val
    #         else:
    #             # Directly resolve the full path
    #             path = wmdr_path.split("/") if wmdr_path else []
    #             val = self._resolve_path_recursive(self.data, path)

    #             if isinstance(val, list):
    #                 val = [v for v in val if v not in (None, "")]
    #                 if len(val) == 1:
    #                     val = val[0]

    #             if val in ([], None, "") and default_val is not None:
    #                 val = default_val

    #             acdd[attr] = val

    #     return acdd

