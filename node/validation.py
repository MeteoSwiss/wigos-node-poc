from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from .schemas import WMDR2_CORE_CONFORMANCE, WMDR2_RECORD_SCHEMA

WSI_RE = re.compile(r"^(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$")
PREFIXED_WSI_RE = re.compile(r"^(?:wsi|facility|record):(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$")


@dataclass(frozen=True)
class ValidationMessage:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    errors: list[ValidationMessage]
    warnings: list[ValidationMessage]

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [m.__dict__ for m in self.errors],
            "warnings": [m.__dict__ for m in self.warnings],
        }


_validator = Draft202012Validator(WMDR2_RECORD_SCHEMA)


def _path(error_path: Any) -> str:
    parts = [str(part) for part in error_path]
    return "$" if not parts else "$" + "".join(f"[{p}]" if p.isdigit() else f".{p}" for p in parts)


def validate_record(record: dict[str, Any]) -> ValidationReport:
    errors = [
        ValidationMessage(path=_path(error.path), message=error.message)
        for error in sorted(_validator.iter_errors(record), key=lambda err: list(err.path))
    ]
    warnings = _semantic_warnings(record)
    return ValidationReport(valid=not errors, errors=errors, warnings=warnings)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with safe UI defaults and current WMDR2 v0.3.x names.

    The normalizer is deliberately conservative. It migrates obsolete names and
    copies existing deployment context into current observing configurations when
    a legacy PoC record provides that context. It avoids inventing substantive
    metadata. Dated structures are represented as ``time.interval``.
    """
    normalized = deepcopy(record)
    normalized.setdefault("type", "Feature")
    normalized["id"] = _normalize_facility_id(normalized.get("id"))

    conforms_to = normalized.get("conformsTo")
    if isinstance(conforms_to, list):
        if WMDR2_CORE_CONFORMANCE not in conforms_to:
            normalized["conformsTo"] = [WMDR2_CORE_CONFORMANCE, *conforms_to]
    else:
        normalized["conformsTo"] = [WMDR2_CORE_CONFORMANCE]

    normalized.setdefault("time", {"interval": ["..", ".."], "resolution": "P1D"})
    normalized.setdefault("geometry", {"type": "Point", "coordinates": [0.0, 0.0]})

    props = normalized.setdefault("properties", {})
    props.setdefault("type", "facility")
    props.setdefault("title", normalized.get("id", "Untitled facility"))

    legacy_deployments = props.get("deployments") if isinstance(props.get("deployments"), list) else []
    deployment_by_uid = {
        str(dep.get("uid") or dep.get("id")): dep
        for dep in legacy_deployments
        if isinstance(dep, dict) and (dep.get("uid") or dep.get("id"))
    }

    _migrate_facility_properties(props)
    props.setdefault("contacts", [])
    props.setdefault("observationSeries", [])
    props.setdefault("instruments", [])
    props.setdefault("schedules", [])

    props["observationSeries"] = [
        _normalize_observation_series(item, deployment_by_uid)
        for item in _as_list(props.get("observationSeries"))
    ]
    props["contacts"] = [_normalize_contact(item) for item in _as_list(props.get("contacts"))]
    props["instruments"] = [_normalize_instrument(item) for item in _as_list(props.get("instruments"))]

    # v0.3.x has no facility-level deployments or reporting registry.
    props.pop("deployments", None)
    props.pop("reporting", None)
    return normalized


def _normalize_facility_id(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if WSI_RE.match(text):
            return text
        prefixed = PREFIXED_WSI_RE.match(text)
        if prefixed:
            return "-".join(prefixed.groups())
        return text
    return "0-1-0-UNKNOWN"


def _migrate_facility_properties(props: dict[str, Any]) -> None:
    if "observationSeries" not in props and isinstance(props.get("observations"), list):
        props["observationSeries"] = props.pop("observations")
    else:
        props.pop("observations", None)

    if "programAffiliations" not in props:
        if isinstance(props.get("programAffiliation"), list):
            props["programAffiliations"] = [_normalize_program_affiliation(item) for item in props["programAffiliation"]]
        elif isinstance(props.get("temporalProgramAffiliation"), list):
            props["programAffiliations"] = [_normalize_program_affiliation(item) for item in props["temporalProgramAffiliation"]]
    else:
        props["programAffiliations"] = [_normalize_program_affiliation(item) for item in _as_list(props.get("programAffiliations"))]
    props.pop("programAffiliation", None)
    props.pop("temporalProgramAffiliation", None)

    if isinstance(props.get("environment"), dict):
        props["environment"] = [props["environment"]]
    if isinstance(props.get("environment"), list):
        props["environment"] = [_date_to_time_interval(item) for item in props["environment"]]
    if isinstance(props.get("territory"), list):
        props["territory"] = [_date_to_time_interval(item) for item in props["territory"]]


def _normalize_program_affiliation(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    item = _date_to_time_interval(value)
    if "program" not in item and "programAffiliation" in item:
        item["program"] = item.pop("programAffiliation")
    return item


def _date_to_time_interval(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    item = dict(value)
    begin = item.pop("validFrom", None)
    end = item.pop("validTo", None)
    if begin is None:
        begin = item.pop("date", None)
    else:
        item.pop("date", None)
    existing_time = item.get("time") if isinstance(item.get("time"), dict) else None
    if existing_time is not None:
        interval = existing_time.get("interval")
        if isinstance(interval, list) and len(interval) == 2:
            return item
    if begin is not None or end is not None:
        item["time"] = {"interval": [str(begin or ".."), str(end or "..")]}
    return item


def _normalize_observation_series(value: Any, deployment_by_uid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    obs = dict(value) if isinstance(value, dict) else {"id": "observationSeries:unknown"}

    if "id" not in obs and isinstance(obs.get("uid"), str):
        # Keep uid-only legacy records valid; new examples commonly use id.
        pass
    elif "id" in obs and isinstance(obs["id"], str):
        obs["id"] = obs["id"].replace("observation:", "observationSeries:", 1)
    elif "uid" not in obs:
        obs["id"] = "observationSeries:unknown"

    # Current v0.3.x uses observedFeature. Older examples used observedDomain;
    # normalize that alias away so the UI/export follows the current schema.
    if "observedFeature" not in obs and isinstance(obs.get("observedDomain"), dict):
        obs["observedFeature"] = dict(obs["observedDomain"])
    obs.pop("observedDomain", None)

    if "programAffiliations" not in obs and isinstance(obs.get("programAffiliation"), list):
        obs["programAffiliations"] = obs.pop("programAffiliation")

    if "applicationAreas" not in obs:
        if isinstance(obs.get("applicationArea"), list):
            obs["applicationAreas"] = obs.pop("applicationArea")
        elif obs.get("applicationArea") not in (None, ""):
            obs["applicationAreas"] = [obs.pop("applicationArea")]
    else:
        obs.pop("applicationArea", None)

    if "observedProperty" not in obs and "observedVariable" in obs:
        obs["observedProperty"] = obs.pop("observedVariable")
    if "observedGeometry" not in obs and "observedGeometryType" in obs:
        obs["observedGeometry"] = obs.pop("observedGeometryType")

    if "reportingProcedures" not in obs and isinstance(obs.get("reporting"), list):
        obs["reportingProcedures"] = obs.pop("reporting")

    if "observingConfigurations" not in obs and isinstance(obs.get("deployments"), list):
        obs["observingConfigurations"] = [
            {"deployment": ref} for ref in obs["deployments"] if isinstance(ref, str) and ref
        ]
    obs.pop("deployments", None)

    if "observingConfigurations" in obs:
        obs["observingConfigurations"] = [
            _normalize_observing_configuration(item, deployment_by_uid)
            for item in _as_list(obs.get("observingConfigurations"))
        ]
    return obs


def _normalize_observing_configuration(value: Any, deployment_by_uid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    config = _date_to_time_interval(value) if isinstance(value, dict) else {}

    deployment_ref = config.pop("deployment", None)
    deployment = deployment_by_uid.get(str(deployment_ref)) if deployment_ref else None
    if deployment:
        if "instrument" not in config and deployment.get("instrument"):
            inst = deployment["instrument"]
            config["instrument"] = inst[0] if isinstance(inst, list) and inst else inst
        if "sourceOfObservation" not in config and "sourceOfObservation" in deployment:
            config["sourceOfObservation"] = deployment["sourceOfObservation"]
        for source_key, target_key in (
            ("geometry", "geometry"),
            ("referenceSurface", "referenceSurface"),
            ("localReferenceSurface", "referenceSurface"),
            ("relativeLocation", "relativeLocation"),
            ("verticalDistanceFromReferenceSurface", "verticalDistanceFromReferenceSurface"),
        ):
            if target_key not in config and source_key in deployment:
                config[target_key] = deployment[source_key]

    # Flatten the v0.5/v0.6 PoC's obsolete observingLocation wrapper.
    location = config.pop("observingLocation", None)
    if isinstance(location, dict):
        for key in ("geometry", "referenceSurface", "relativeLocation", "verticalDistanceFromReferenceSurface"):
            if key not in config and key in location:
                config[key] = location[key]

    if config.get("time") == {}:
        config.pop("time", None)
    return config


def _normalize_contact(value: Any) -> dict[str, Any]:
    contact = dict(value) if isinstance(value, dict) else {}
    if "identifier" not in contact:
        old_id = contact.get("id") or contact.get("uid")
        if isinstance(old_id, str) and old_id.startswith("contact:"):
            contact["identifier"] = old_id
    return contact


def _normalize_instrument(value: Any) -> dict[str, Any]:
    inst = dict(value) if isinstance(value, dict) else {"id": "instrument:unknown"}
    if "id" not in inst and isinstance(inst.get("uid"), str):
        pass
    elif "id" not in inst and "uid" not in inst:
        inst["id"] = "instrument:unknown"
    inst.pop("serialNumber", None)
    inst.pop("serialNumbers", None)
    return inst


def _ref_id(value: dict[str, Any]) -> str | None:
    ref = value.get("id") or value.get("uid") or value.get("identifier")
    return ref if isinstance(ref, str) and ref else None


def _semantic_warnings(record: dict[str, Any]) -> list[ValidationMessage]:
    warnings: list[ValidationMessage] = []
    props = record.get("properties", {}) if isinstance(record.get("properties"), dict) else {}
    instruments = props.get("instruments", []) if isinstance(props.get("instruments"), list) else []
    series = props.get("observationSeries", []) if isinstance(props.get("observationSeries"), list) else []

    tg = record.get("temporalGeometry") if isinstance(record.get("temporalGeometry"), dict) else None
    if tg:
        coordinates = tg.get("coordinates") if isinstance(tg.get("coordinates"), list) else []
        dates = tg.get("dates") if isinstance(tg.get("dates"), list) else []
        methods = tg.get("methods") if isinstance(tg.get("methods"), list) else []
        if len(coordinates) != len(dates):
            warnings.append(
                ValidationMessage(
                    path="$.temporalGeometry",
                    message="temporalGeometry coordinates and dates should have the same number of entries.",
                )
            )
        if methods and len(methods) != len(coordinates):
            warnings.append(
                ValidationMessage(
                    path="$.temporalGeometry.methods",
                    message="temporalGeometry methods should be parallel to coordinates when present.",
                )
            )
        geometry_coordinates = record.get("geometry", {}).get("coordinates") if isinstance(record.get("geometry"), dict) else None
        if coordinates and isinstance(geometry_coordinates, list):
            latest = coordinates[-1]
            if isinstance(latest, list) and _coordinates_differ(geometry_coordinates, latest):
                warnings.append(
                    ValidationMessage(
                        path="$.geometry.coordinates",
                        message="Current geometry does not match the latest temporalGeometry coordinate.",
                    )
                )

    instrument_ids = {_ref_id(i) for i in instruments if isinstance(i, dict)}
    instrument_ids.discard(None)

    for s_index, obs in enumerate(series):
        if not isinstance(obs, dict):
            continue
        configs = obs.get("observingConfigurations", []) or []
        if not isinstance(configs, list):
            continue
        for c_index, config in enumerate(configs):
            if not isinstance(config, dict):
                continue
            interval = config.get("time", {}).get("interval") if isinstance(config.get("time"), dict) else None
            if isinstance(interval, list) and interval and interval[0] == "..":
                warnings.append(
                    ValidationMessage(
                        path=f"$.properties.observationSeries[{s_index}].observingConfigurations[{c_index}].time.interval[0]",
                        message="The observing configuration start date is explicitly unknown/open ('..'); replace it with the recorded start date when available.",
                    )
                )
            instrument_ref = config.get("instrument")
            if instrument_ref and instrument_ref not in instrument_ids:
                warnings.append(
                    ValidationMessage(
                        path=f"$.properties.observationSeries[{s_index}].observingConfigurations[{c_index}].instrument",
                        message=f"ObservingConfiguration references missing instrument {instrument_ref!r}.",
                    )
                )

    return warnings


def _coordinates_differ(a: list[Any], b: list[Any]) -> bool:
    if len(a) != len(b):
        return True
    for left, right in zip(a, b, strict=True):
        try:
            if abs(float(left) - float(right)) > 1e-9:
                return True
        except (TypeError, ValueError):
            return left != right
    return False


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
