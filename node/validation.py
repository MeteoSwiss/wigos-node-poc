from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from .schemas import WMDR2_CORE_CONFORMANCE, WMDR2_RECORD_SCHEMA


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
    """Return a copy with safe PoC-level defaults and current WMDR2 names.

    The function avoids inventing substantive metadata. It only fills technical shells
    needed by the UI and migrates older PoC field names to the current draft shape.
    """
    normalized = deepcopy(record)
    normalized.setdefault("type", "Feature")
    normalized.setdefault("conformsTo", [WMDR2_CORE_CONFORMANCE])
    if WMDR2_CORE_CONFORMANCE not in normalized["conformsTo"]:
        normalized["conformsTo"] = [WMDR2_CORE_CONFORMANCE, *normalized["conformsTo"]]
    normalized.setdefault("time", {"interval": ["..", ".."]})
    normalized.setdefault("geometry", None)

    props = normalized.setdefault("properties", {})
    props.setdefault("type", "facility")
    props.setdefault("title", normalized.get("id", "Untitled facility"))

    _migrate_facility_properties(props)
    props.setdefault("contacts", [])
    props.setdefault("observationSeries", [])
    props.setdefault("deployments", [])
    props.setdefault("instruments", [])
    props.setdefault("reporting", [])
    props.setdefault("schedules", [])

    props["observationSeries"] = [
        _normalize_observation_series(item) for item in _as_list(props.get("observationSeries"))
    ]
    props["deployments"] = [_normalize_deployment(item) for item in _as_list(props.get("deployments"))]
    props["contacts"] = [_normalize_contact(item) for item in _as_list(props.get("contacts"))]
    props["instruments"] = [_normalize_instrument(item) for item in _as_list(props.get("instruments"))]
    return normalized


def _migrate_facility_properties(props: dict[str, Any]) -> None:
    if "observationSeries" not in props and isinstance(props.get("observations"), list):
        props["observationSeries"] = props.pop("observations")
    else:
        props.pop("observations", None)

    if "programAffiliation" not in props and isinstance(props.get("temporalProgramAffiliation"), list):
        props["programAffiliation"] = props.pop("temporalProgramAffiliation")
    else:
        props.pop("temporalProgramAffiliation", None)

    if isinstance(props.get("environment"), dict):
        props["environment"] = [props["environment"]]


def _normalize_observation_series(value: Any) -> dict[str, Any]:
    obs = dict(value) if isinstance(value, dict) else {"id": "observationSeries:unknown", "observedProperty": ""}

    if isinstance(obs.get("id"), str) and obs["id"].startswith("observation:"):
        obs["id"] = "observationSeries:" + obs["id"].split(":", 1)[1]

    if "observedFeature" not in obs and isinstance(obs.get("observedDomain"), dict):
        obs["observedFeature"] = obs.pop("observedDomain")
    else:
        obs.pop("observedDomain", None)

    if "programAffiliation" not in obs and isinstance(obs.get("programAffiliations"), list):
        obs["programAffiliation"] = obs.pop("programAffiliations")
    else:
        obs.pop("programAffiliations", None)

    if "observedProperty" not in obs and "observedVariable" in obs:
        obs["observedProperty"] = obs.pop("observedVariable")

    if "observedGeometry" not in obs and "observedGeometryType" in obs:
        obs["observedGeometry"] = obs.pop("observedGeometryType")

    if "observingConfigurations" not in obs and isinstance(obs.get("deployments"), list):
        obs["observingConfigurations"] = [
            {"date": "..", "deployment": dep, "observingMethod": {"nilReason": "unknown"}}
            for dep in obs["deployments"]
            if isinstance(dep, str) and dep
        ]
    obs.pop("deployments", None)

    obs.setdefault("id", "observationSeries:unknown")
    obs.setdefault("observedProperty", "")
    return obs


def _normalize_deployment(value: Any) -> dict[str, Any]:
    dep = dict(value) if isinstance(value, dict) else {"id": "deployment:unknown"}
    instrument = dep.get("instrument")
    if isinstance(instrument, list):
        dep["instrument"] = instrument[0] if instrument else ""
    dep.pop("localReferenceSurface", None)
    dep.pop("temporalGeometry", None)
    return dep


def _normalize_contact(value: Any) -> dict[str, Any]:
    contact = dict(value) if isinstance(value, dict) else {}
    for key in ("emails", "phones"):
        items = contact.get(key)
        if isinstance(items, list):
            contact[key] = [item.get("value") if isinstance(item, dict) and "value" in item else item for item in items]
    return contact


def _normalize_instrument(value: Any) -> dict[str, Any]:
    inst = dict(value) if isinstance(value, dict) else {"id": "instrument:unknown"}
    if "observingMethods" not in inst and isinstance(inst.get("observableVariables"), list):
        # Older PoC field. Keep it as an extension if present, but do not promote it
        # to observingMethods because observed variables and methods are not equivalent.
        pass
    inst.pop("serialNumber", None)
    inst.pop("serialNumbers", None)
    return inst


def _semantic_warnings(record: dict[str, Any]) -> list[ValidationMessage]:
    warnings: list[ValidationMessage] = []
    props = record.get("properties", {}) if isinstance(record.get("properties"), dict) else {}
    deployments = props.get("deployments", []) if isinstance(props.get("deployments"), list) else []
    instruments = props.get("instruments", []) if isinstance(props.get("instruments"), list) else []
    series = props.get("observationSeries", []) if isinstance(props.get("observationSeries"), list) else []

    deployment_ids = {d.get("id") for d in deployments if isinstance(d, dict)}
    instrument_ids = {i.get("id") for i in instruments if isinstance(i, dict)}

    for s_index, obs in enumerate(series):
        if not isinstance(obs, dict):
            continue
        configs = obs.get("observingConfigurations", []) or []
        if not isinstance(configs, list):
            continue
        for c_index, config in enumerate(configs):
            if not isinstance(config, dict):
                continue
            dep_ref = config.get("deployment")
            if dep_ref and dep_ref not in deployment_ids:
                warnings.append(
                    ValidationMessage(
                        path=f"$.properties.observationSeries[{s_index}].observingConfigurations[{c_index}].deployment",
                        message=f"ObservationSeries references missing deployment {dep_ref!r}.",
                    )
                )

    for index, deployment in enumerate(deployments):
        if not isinstance(deployment, dict):
            continue
        instrument_ref = deployment.get("instrument")
        if instrument_ref and instrument_ref not in instrument_ids:
            warnings.append(
                ValidationMessage(
                    path=f"$.properties.deployments[{index}].instrument",
                    message=f"Deployment references missing instrument {instrument_ref!r}.",
                )
            )

    return warnings


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
