from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from .schemas import WMDR2_CORE_CONFORMANCE, WMDR2_RECORD_SCHEMA

WSI_RE = re.compile(r"^(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$")
PREFIXED_WSI_RE = re.compile(r"^(?:wsi|facility|record):(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$")
INSTRUMENT_PREFIX = "instrument:"

VOCAB_URL_BASES = {
    "facilityType": "http://codes.wmo.int/wmdr/FacilityType/",
    "wmoRegion": "http://codes.wmo.int/wmdr/WMORegion/",
    "territory": "http://codes.wmo.int/wmdr/TerritoryName/",
    "observedProperty": "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/",
    "observedGeometry": "http://codes.wmo.int/wmdr/Geometry/",
    "domain": "http://codes.wmo.int/wmdr/Domain/",
    "programAffiliation": "http://codes.wmo.int/wmdr/ProgramAffiliation/",
    "reportingStatus": "http://codes.wmo.int/wmdr/ReportingStatus/",
    "applicationAreas": "http://codes.wmo.int/wmdr/ApplicationArea/",
    "observingMethod": "http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/",
    "operatingStatus": "http://codes.wmo.int/wmdr/InstrumentOperatingStatus/",
    "sourceOfObservation": "http://codes.wmo.int/wmdr/SourceOfObservation/",
    "exposure": "http://codes.wmo.int/wmdr/Exposure/",
    "referenceSurface": "http://codes.wmo.int/wmdr/ReferenceSurfaceType/",
    "unit": "http://codes.wmo.int/wmdr/unit/",
    "observingMethods": "http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/",
    "dataFormat": "http://codes.wmo.int/wmdr/DataFormat/",
    "dataPolicy": "http://codes.wmo.int/wmdr/DataPolicy/",
    "levelOfData": "http://codes.wmo.int/wmdr/LevelOfData/",
    "surfaceRoughness": "http://codes.wmo.int/wmdr/SurfaceRoughnessDavenport/",
    "climateZone": "http://codes.wmo.int/wmdr/ClimateZone/",
    "surfaceCoverScheme": "http://codes.wmo.int/wmdr/SurfaceCoverClassification/",
    "localTopography": "http://codes.wmo.int/wmdr/LocalTopography/",
    "relativeElevation": "http://codes.wmo.int/wmdr/RelativeElevation/",
    "topographicContext": "http://codes.wmo.int/wmdr/TopographicContext/",
    "altitudeOrDepth": "http://codes.wmo.int/wmdr/AltitudeOrDepth/",
}

SURFACE_COVER_SCHEME_TO_REGISTER = {
    "globCover2009": "SurfaceCoverGlobCover2009",
    "igbp": "SurfaceCoverIGBP",
    "lccs": "SurfaceCoverLCCS",
    "pft": "SurfaceCoverPFT",
    "umd": "SurfaceCoverUMD",
    "laiFpar": "SurfaceCoverLAIFPAR",
    "npp": "SurfaceCoverNPP",
}


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
    """Return a copy normalized to the current WMDR2 v0.4.0 record shape."""
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
    normalized.setdefault("geometry", None)

    props = normalized.setdefault("properties", {})
    props.setdefault("type", "facility")
    props.setdefault("title", normalized.get("id", "Untitled facility"))
    props.setdefault("facilityType", None)

    legacy_deployments = props.get("deployments") if isinstance(props.get("deployments"), list) else []
    deployment_by_uid = {
        str(dep.get("uid") or dep.get("id")): dep
        for dep in legacy_deployments
        if isinstance(dep, dict) and (dep.get("uid") or dep.get("id"))
    }

    _migrate_facility_properties(props, normalized)
    props.setdefault("contacts", [])
    props.setdefault("observations", [])
    props.setdefault("instruments", [])
    props.setdefault("schedules", [])

    props["facilityType"] = _concept_or_null(props.get("facilityType"), "facilityType")
    if props.get("wmoRegion") not in (None, ""):
        props["wmoRegion"] = _concept(props.get("wmoRegion"), "wmoRegion")

    props["contacts"] = [_normalize_contact(item) for item in _as_list(props.get("contacts"))]
    props["instruments"] = [_normalize_instrument(item) for item in _as_list(props.get("instruments"))]
    props["observations"] = [
        _normalize_observation(item, deployment_by_uid, index)
        for index, item in enumerate(_as_list(props.get("observations")))
    ]
    _migrate_nested_contact_references(props)

    props.pop("deployments", None)
    props.pop("reporting", None)
    props.pop("observationSeries", None)
    props.pop("programAffiliation", None)
    props.pop("programAffiliations", None)
    props.pop("territory", None)
    props.pop("links", None)
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


def _normalize_instrument_identifier(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return text
    return text if text.startswith(INSTRUMENT_PREFIX) else f"{INSTRUMENT_PREFIX}{text}"


def _migrate_facility_properties(props: dict[str, Any], record: dict[str, Any]) -> None:
    if "observations" not in props and isinstance(props.get("observationSeries"), list):
        props["observations"] = props.get("observationSeries")
    elif "observations" not in props and isinstance(props.get("observations"), list):
        pass

    if "territories" not in props and isinstance(props.get("territory"), list):
        props["territories"] = props.get("territory")
    if isinstance(props.get("territories"), list):
        props["territories"] = [_normalize_territory(item) for item in props["territories"]]

    if isinstance(props.get("environment"), dict):
        props["environment"] = [props["environment"]]
    if isinstance(props.get("environment"), list):
        props["environment"] = [_normalize_environment(item) for item in props["environment"]]

    if "links" in props and "links" not in record:
        record["links"] = props["links"]


def _normalize_territory(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    item = dict(value)
    if "dates" not in item and isinstance(item.get("time"), dict):
        interval = item["time"].get("interval")
        if isinstance(interval, list) and interval:
            item["dates"] = [str(part or "..") for part in interval[:2]]
    if item.get("territory") not in (None, ""):
        item["territory"] = _concept_or_null(item.get("territory"), "territory")
    item.pop("time", None)
    item.pop("date", None)
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


def _dates_from_time_or_default(value: dict[str, Any]) -> list[str] | None:
    if isinstance(value.get("dates"), list) and value["dates"]:
        return [str(part or "..") for part in value["dates"][:2]]
    time = value.get("time") if isinstance(value.get("time"), dict) else None
    interval = time.get("interval") if time else None
    if isinstance(interval, list) and interval:
        return [str(part or "..") for part in interval[:2]]
    return None


def _normalize_observation(value: Any, deployment_by_uid: dict[str, dict[str, Any]], index: int) -> dict[str, Any]:
    obs = dict(value) if isinstance(value, dict) else {"id": f"observation:{index + 1}"}

    if "id" not in obs and isinstance(obs.get("uid"), str):
        obs["id"] = obs.pop("uid")
    elif "id" in obs and isinstance(obs["id"], str):
        obs["id"] = obs["id"].replace("observationSeries:", "observation:", 1)
    elif "id" not in obs:
        obs["id"] = f"observation:{index + 1}"

    if "observedFeature" not in obs and isinstance(obs.get("observedDomain"), dict):
        obs["observedFeature"] = dict(obs["observedDomain"])
    obs.pop("observedDomain", None)

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

    if "configurations" not in obs and isinstance(obs.get("observingConfigurations"), list):
        obs["configurations"] = obs.get("observingConfigurations")
    if "configurations" not in obs and isinstance(obs.get("deployments"), list):
        obs["configurations"] = [{"deployment": ref} for ref in obs["deployments"] if isinstance(ref, str) and ref]
    obs.pop("observingConfigurations", None)
    obs.pop("deployments", None)

    if obs.get("observedProperty") not in (None, ""):
        obs["observedProperty"] = _concept(obs.get("observedProperty"), "observedProperty")
    if obs.get("observedGeometry") not in (None, ""):
        obs["observedGeometry"] = _concept(obs.get("observedGeometry"), "observedGeometry")

    feature = obs.get("observedFeature") if isinstance(obs.get("observedFeature"), dict) else {}
    if feature.get("domain") not in (None, ""):
        feature["domain"] = _concept_or_null(feature.get("domain"), "domain")
    if feature.get("domainFeature") not in (None, ""):
        feature["domainFeature"] = _concept(feature.get("domainFeature"))
    obs["observedFeature"] = feature

    obs["programAffiliations"] = _normalize_program_affiliations(obs.get("programAffiliations") or obs.get("programAffiliation"))
    obs.pop("programAffiliation", None)
    if obs.get("applicationAreas") not in (None, ""):
        obs["applicationAreas"] = [_concept(item, "applicationAreas") for item in _as_list(obs.get("applicationAreas")) if item not in (None, "")]

    obs["configurations"] = [
        _normalize_configuration(item, deployment_by_uid, obs["id"], config_index)
        for config_index, item in enumerate(_as_list(obs.get("configurations")))
    ]
    if obs.get("observingProcedures"):
        obs["observingProcedures"] = [_normalize_observing_procedure(item) for item in _as_list(obs.get("observingProcedures"))]
    if obs.get("reportingProcedures"):
        obs["reportingProcedures"] = [_normalize_reporting_procedure(item) for item in _as_list(obs.get("reportingProcedures"))]
    return obs


def _normalize_program_affiliations(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in _as_list(value):
        if item in (None, ""):
            continue
        if not isinstance(item, dict):
            result.append({"programAffiliation": _concept(item, "programAffiliation")})
            continue
        row = dict(item)
        if "programAffiliation" not in row and "program" in row:
            row["programAffiliation"] = row.pop("program")
        if "programAffiliation" in row:
            row["programAffiliation"] = _concept(row["programAffiliation"], "programAffiliation")
        if row.get("reportingStatus") not in (None, ""):
            row["reportingStatus"] = _concept_or_null(row.get("reportingStatus"), "reportingStatus")
        dates = _dates_from_time_or_default(row)
        if dates:
            row["dates"] = dates
        row.pop("time", None)
        row.pop("date", None)
        result.append(row)
    return result


def _normalize_configuration(value: Any, deployment_by_uid: dict[str, dict[str, Any]], observation_id: str, index: int) -> dict[str, Any]:
    config = _date_to_time_interval(value) if isinstance(value, dict) else {}

    deployment_ref = config.pop("deployment", None)
    deployment = deployment_by_uid.get(str(deployment_ref)) if deployment_ref else None
    if deployment:
        if "instrument" not in config and deployment.get("instrument"):
            inst = deployment["instrument"]
            config["instrument"] = inst[0] if isinstance(inst, list) and inst else inst
        if "sourceOfObservation" not in config and "sourceOfObservation" in deployment:
            config["sourceOfObservation"] = deployment["sourceOfObservation"]
        for source_key in ("geometry", "relativeLocation", "referenceSurface", "verticalDistanceFromReferenceSurface"):
            if source_key not in config and source_key in deployment:
                config[source_key] = deployment[source_key]

    location = config.pop("observingLocation", None)
    if isinstance(location, dict):
        for key in ("geometry", "referenceSurface", "relativeLocation", "verticalDistanceFromReferenceSurface"):
            if key not in config and key in location:
                config[key] = location[key]

    if not config.get("id"):
        config["id"] = f"{observation_id}-configuration-{index + 1}"
    if "time" not in config or not isinstance(config.get("time"), dict):
        config["time"] = {"interval": ["..", ".."]}

    if "instrument" in config:
        config["instrument"] = _normalize_instrument_identifier(config.get("instrument"))

    if "serialNumber" in config and "instrumentSerialNumber" not in config:
        config["instrumentSerialNumber"] = config.pop("serialNumber")
    else:
        config.pop("serialNumber", None)

    _normalize_configuration_concepts(config)
    _normalize_vertical_distance(config)
    _cleanup_configuration(config)
    return config


def _normalize_configuration_concepts(config: dict[str, Any]) -> None:
    for key, register in (
        ("observingMethod", "observingMethod"),
        ("operatingStatus", "operatingStatus"),
        ("sourceOfObservation", "sourceOfObservation"),
        ("exposure", "exposure"),
    ):
        if config.get(key) not in (None, ""):
            config[key] = _concept_or_null(config.get(key), register)


def _normalize_vertical_distance(config: dict[str, Any]) -> None:
    vd = config.get("verticalDistance") if isinstance(config.get("verticalDistance"), dict) else None
    legacy = config.pop("verticalDistanceFromReferenceSurface", None)
    legacy_ref = config.pop("referenceSurface", None)
    if vd is None and isinstance(legacy, dict):
        value = legacy.get("value")
        if value not in (None, ""):
            vd = {"distances": [value], "unit": legacy.get("uom"), "referenceSurface": legacy_ref}
    elif vd is None and legacy_ref not in (None, ""):
        vd = {"distances": [], "unit": None, "referenceSurface": legacy_ref}
    if not isinstance(vd, dict):
        return
    distances = vd.get("distances")
    if not isinstance(distances, list):
        distances = [vd.get("value")] if vd.get("value") not in (None, "") else []
    distances = [item for item in distances if item not in (None, "")]
    if not distances:
        config.pop("verticalDistance", None)
        return
    vd["distances"] = distances
    vd["unit"] = _concept_or_null(vd.get("unit"), "unit")
    vd["referenceSurface"] = _concept_or_null(vd.get("referenceSurface"), "referenceSurface")
    config["verticalDistance"] = vd


def _cleanup_configuration(config: dict[str, Any]) -> None:
    if config.get("time") == {}:
        config.pop("time", None)


def _normalize_observing_procedure(value: Any) -> Any:
    proc = _date_to_time_interval(value) if isinstance(value, dict) else {}
    if proc.get("strategy") not in (None, ""):
        proc["strategy"] = _concept(proc.get("strategy"))
    return proc


def _normalize_reporting_procedure(value: Any) -> Any:
    proc = dict(value) if isinstance(value, dict) else {}

    if "internationalExchange" not in proc:
        proc["internationalExchange"] = False

    if "dataPolicy" not in proc or proc.get("dataPolicy") == "":
        proc["dataPolicy"] = None

    for key, register in (
        ("dataPolicy", "dataPolicy"),
        ("levelOfData", "levelOfData"),
        ("uom", "unit"),
        ("strategy", None),
        ("timeStampMeaning", None),
    ):
        if proc.get(key) not in (None, ""):
            proc[key] = _concept_or_null(proc.get(key), register)

    if proc.get("dataFormat"):
        proc["dataFormat"] = [_concept(item, "dataFormat") for item in _as_list(proc.get("dataFormat"))]

    if proc.get("referenceTimeSource"):
        proc["referenceTimeSource"] = [_concept(item) for item in _as_list(proc.get("referenceTimeSource"))]

    if "spatialReportingInterval" in proc and "temporalReportingInterval" not in proc:
        proc["temporalReportingInterval"] = proc.pop("spatialReportingInterval")

    proc.pop("time", None)
    proc.pop("date", None)
    return proc

def _normalize_environment(value: Any) -> Any:
    item = _date_to_time_interval(value)
    if not isinstance(item, dict):
        return item
    for key, register in (("climateZone", "climateZone"), ("surfaceRoughness", "surfaceRoughness")):
        if item.get(key) not in (None, ""):
            item[key] = _concept(item[key], register)
    item["surfaceCover"] = _normalize_surface_cover(item.get("surfaceCover")) if item.get("surfaceCover") not in (None, "") else item.get("surfaceCover")
    if not item.get("surfaceCover"):
        item.pop("surfaceCover", None)
    topo = item.get("topographyBathymetry")
    if isinstance(topo, dict):
        normalized: dict[str, Any] = {}
        for key in ("localTopography", "relativeElevation", "topographicContext", "altitudeOrDepth"):
            if topo.get(key) not in (None, ""):
                normalized[key] = _concept(topo[key], key)
        if normalized:
            item["topographyBathymetry"] = normalized
        else:
            item.pop("topographyBathymetry", None)
    return item


def _normalize_surface_cover(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    scheme_raw = value.get("scheme") or value.get("classificationScheme")
    cover_raw = value.get("value")
    if cover_raw in (None, "") or scheme_raw in (None, ""):
        return None
    scheme = _concept(scheme_raw, "surfaceCoverScheme")
    scheme_id = scheme.get("id", "")
    register = SURFACE_COVER_SCHEME_TO_REGISTER.get(scheme_id)
    cover_base = f"http://codes.wmo.int/wmdr/{register}/" if register else None
    return {"scheme": scheme, "value": _concept(cover_raw, base_url=cover_base)}


def _migrate_nested_contact_references(props: dict[str, Any]) -> None:
    """Keep Facility contacts full and normalize nested contacts to {ref, roles}."""
    contacts = [_normalize_contact(item) for item in _as_list(props.get("contacts"))]
    by_id: dict[str, dict[str, Any]] = {}
    for contact in contacts:
        identifier = contact.get("identifier")
        if isinstance(identifier, str) and identifier:
            by_id[identifier] = contact

    def register_full(item: dict[str, Any]) -> str | None:
        contact = _normalize_contact(item)
        identifier = contact.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            return None
        roles = contact.pop("roles", None)
        existing = by_id.get(identifier, {})
        merged = dict(existing)
        for key, value in contact.items():
            if value not in (None, "", [], {}):
                merged[key] = value
        by_id[identifier] = merged
        return identifier

    def migrate(container: dict[str, Any]) -> None:
        raw = container.get("contacts")
        legacy = container.pop("contactReferences", None)
        refs: list[dict[str, Any]] = []
        for item in [*_as_list(legacy), *_as_list(raw)]:
            if not isinstance(item, dict):
                continue
            ref = item.get("ref") or item.get("contact")
            looks_embedded = any(key in item for key in ("identifier", "organization", "name", "emails", "phones", "addresses"))
            if ref and not looks_embedded:
                out = {"ref": str(ref)}
                roles = item.get("roles")
                if isinstance(roles, list) and roles:
                    out["roles"] = [str(role) for role in roles if str(role).strip()]
                refs.append(out)
                continue
            identifier = register_full(item)
            if identifier:
                out = {"ref": identifier}
                roles = item.get("roles")
                if isinstance(roles, list) and roles:
                    out["roles"] = [str(role) for role in roles if str(role).strip()]
                refs.append(out)
        if refs:
            container["contacts"] = refs
        elif raw is not None or legacy is not None:
            container.pop("contacts", None)

    for obs in _as_list(props.get("observations")):
        if not isinstance(obs, dict):
            continue
        migrate(obs)
        for config in _as_list(obs.get("configurations")):
            if isinstance(config, dict):
                migrate(config)
        for proc in _as_list(obs.get("reportingProcedures")):
            if isinstance(proc, dict):
                migrate(proc)

    props["contacts"] = [by_id[key] for key in sorted(by_id)]


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
        inst["id"] = _normalize_instrument_identifier(inst.pop("uid"))
    elif "id" not in inst:
        inst["id"] = "instrument:unknown"
    inst["id"] = _normalize_instrument_identifier(inst.get("id"))
    if inst.get("observingMethods"):
        inst["observingMethods"] = [_concept(item, "observingMethods") for item in _as_list(inst.get("observingMethods"))]
    inst.pop("serialNumber", None)
    inst.pop("serialNumbers", None)
    inst.pop("instrumentSerialNumber", None)
    inst.pop("uid", None)
    return inst


def _concept_or_null(value: Any, register: str | None = None) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict) and value.get("nilReason"):
        return None
    return _concept(value, register)


def _concept(value: Any, register: str | None = None, *, base_url: str | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        if "id" in value:
            concept = dict(value)
            concept["id"] = str(concept["id"])
            if "uri" in concept and "url" not in concept:
                concept["url"] = concept.pop("uri")
            return concept
        if "value" in value and len(value) <= 3:
            value = value.get("value")
        elif "url" in value:
            text = str(value["url"])
            return {"id": text.rstrip("/").split("/")[-1], "url": text}
        else:
            return {"id": str(value)}
    text = str(value).strip()
    if text.startswith("http://") or text.startswith("https://"):
        return {"id": text.rstrip("/").split("/")[-1], "url": text}
    url_base = base_url or (VOCAB_URL_BASES.get(register or "") if register else None)
    result = {"id": text}
    if url_base and text:
        result["url"] = f"{url_base}{text}"
    return result


def _ref_id(value: dict[str, Any]) -> str | None:
    ref = value.get("id") or value.get("uid") or value.get("identifier")
    return ref if isinstance(ref, str) and ref else None


def _semantic_warnings(record: dict[str, Any]) -> list[ValidationMessage]:
    warnings: list[ValidationMessage] = []
    props = record.get("properties", {}) if isinstance(record.get("properties"), dict) else {}
    instruments = props.get("instruments", []) if isinstance(props.get("instruments"), list) else []
    observations = props.get("observations", []) if isinstance(props.get("observations"), list) else []

    tg = record.get("temporalGeometry") if isinstance(record.get("temporalGeometry"), dict) else None
    if tg:
        coordinates = tg.get("coordinates") if isinstance(tg.get("coordinates"), list) else []
        dates = tg.get("dates") if isinstance(tg.get("dates"), list) else []
        methods = tg.get("methods") if isinstance(tg.get("methods"), list) else []
        if len(coordinates) != len(dates):
            warnings.append(ValidationMessage(path="$.temporalGeometry", message="temporalGeometry coordinates and dates should have the same number of entries."))
        if methods and len(methods) != len(coordinates):
            warnings.append(ValidationMessage(path="$.temporalGeometry.methods", message="temporalGeometry methods should be parallel to coordinates when present."))
        geometry_coordinates = record.get("geometry", {}).get("coordinates") if isinstance(record.get("geometry"), dict) else None
        if coordinates and isinstance(geometry_coordinates, list):
            latest = coordinates[-1]
            if isinstance(latest, list) and _coordinates_differ(geometry_coordinates, latest):
                warnings.append(ValidationMessage(path="$.geometry.coordinates", message="Current geometry does not match the latest temporalGeometry coordinate."))

    instrument_ids = {_ref_id(i) for i in instruments if isinstance(i, dict)}
    instrument_ids.discard(None)
    contact_ids = {
        str(item.get("identifier"))
        for item in props.get("contacts", [])
        if isinstance(item, dict) and item.get("identifier") not in (None, "")
    }

    def warn_contact_refs(container: dict[str, Any], path: str) -> None:
        for index, ref in enumerate(container.get("contacts", []) or []):
            if not isinstance(ref, dict):
                continue
            identifier = ref.get("ref")
            if identifier and str(identifier) not in contact_ids:
                warnings.append(ValidationMessage(path=f"{path}.contacts[{index}].ref", message=f"Contact reference {identifier!r} is not present in properties.contacts."))

    for s_index, obs in enumerate(observations):
        if not isinstance(obs, dict):
            continue
        warn_contact_refs(obs, f"$.properties.observations[{s_index}]")
        for p_index, proc in enumerate(obs.get("reportingProcedures", []) or []):
            if isinstance(proc, dict):
                warn_contact_refs(proc, f"$.properties.observations[{s_index}].reportingProcedures[{p_index}]")
        configs = obs.get("configurations", []) or []
        if not isinstance(configs, list):
            continue
        for c_index, config in enumerate(configs):
            if not isinstance(config, dict):
                continue
            warn_contact_refs(config, f"$.properties.observations[{s_index}].configurations[{c_index}]")
            interval = config.get("time", {}).get("interval") if isinstance(config.get("time"), dict) else None
            if isinstance(interval, list) and interval and interval[0] == "..":
                warnings.append(ValidationMessage(path=f"$.properties.observations[{s_index}].configurations[{c_index}].time.interval[0]", message="The configuration start date is explicitly unknown/open ('..'); replace it with the recorded start date when available."))
            instrument_ref = config.get("instrument")
            if instrument_ref and instrument_ref not in instrument_ids:
                warnings.append(ValidationMessage(path=f"$.properties.observations[{s_index}].configurations[{c_index}].instrument", message=f"Configuration references missing instrument {instrument_ref!r}."))

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
