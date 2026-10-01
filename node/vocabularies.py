from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WMO_WMDR_BASE_URL = "https://codes.wmo.int/wmdr"
_CACHE_TTL_SECONDS = int(os.environ.get("OSCAR_NODE_VOCABULARY_CACHE_TTL", "86400"))
_REMOTE_TIMEOUT_SECONDS = float(os.environ.get("OSCAR_NODE_VOCABULARY_TIMEOUT", "2.5"))
_REMOTE_OVERALL_TIMEOUT_SECONDS = float(os.environ.get("OSCAR_NODE_VOCABULARY_OVERALL_TIMEOUT", "6.0"))


@dataclass(frozen=True)
class VocabularySpec:
    name: str
    title: str
    register: str | None
    fallback: tuple[dict[str, str], ...]
    multiple: bool = False

    @property
    def register_url(self) -> str | None:
        return f"{WMO_WMDR_BASE_URL}/{self.register}" if self.register else None


VOCABULARY_SPECS: tuple[VocabularySpec, ...] = (
    VocabularySpec(
        "wmoRegion",
        "WMO region",
        "WMORegion",
        (
            {"value": "africa", "label": "Africa"},
            {"value": "asia", "label": "Asia"},
            {"value": "southAmerica", "label": "South America"},
            {"value": "northCentralAmericaCaribbean", "label": "North America, Central America and the Caribbean"},
            {"value": "southWestPacific", "label": "South-West Pacific"},
            {"value": "europe", "label": "Europe"},
            {"value": "antarctica", "label": "Antarctica"},
        ),
    ),
    VocabularySpec(
        "observedGeometry",
        "Observed geometry",
        "Geometry",
        (
            {"value": "point", "label": "Point"},
            {"value": "line", "label": "Line"},
            {"value": "area", "label": "Area"},
            {"value": "grid", "label": "Grid"},
            {"value": "volume", "label": "Volume"},
        ),
    ),
    VocabularySpec(
        "domain",
        "Observed feature domain",
        "Domain",
        (
            {"value": "atmosphere", "label": "Atmosphere"},
            {"value": "ocean", "label": "Ocean"},
            {"value": "terrestrial", "label": "Terrestrial and hydrological"},
            {"value": "earth", "label": "Earth"},
            {"value": "outerSpace", "label": "Outer space"},
        ),
    ),
    VocabularySpec(
        "applicationAreas",
        "Application areas",
        "ApplicationArea",
        (
            {"value": "weatherForecasting", "label": "Weather forecasting"},
            {"value": "climateMonitoring", "label": "Climate monitoring"},
            {"value": "climateApplications", "label": "Climate applications"},
            {"value": "atmosphericComposition", "label": "Atmospheric composition"},
            {"value": "hydrology", "label": "Hydrology"},
            {"value": "oceanApplications", "label": "Ocean applications"},
            {"value": "aeronauticalMeteorology", "label": "Aeronautical meteorology"},
        ),
        multiple=True,
    ),
    VocabularySpec(
        "programAffiliations",
        "Programme/network affiliation",
        "ProgramAffiliation",
        (
            {"value": "GOSGeneral", "label": "GOS general"},
            {"value": "GAWGlobal", "label": "GAW global"},
            {"value": "GAWRegional", "label": "GAW regional"},
            {"value": "GCOSSurfaceNetwork", "label": "GCOS surface network"},
            {"value": "GCOSUpperAirNetwork", "label": "GCOS upper-air network"},
            {"value": "BSRN", "label": "Baseline Surface Radiation Network"},
        ),
        multiple=True,
    ),
    VocabularySpec(
        "sourceOfObservation",
        "Source of observation",
        "SourceOfObservation",
        (
            {"value": "automaticReading", "label": "Automatic reading"},
            {"value": "manualReading", "label": "Manual reading"},
            {"value": "humanObservation", "label": "Human observation"},
            {"value": "remoteSensing", "label": "Remote sensing"},
        ),
    ),
    VocabularySpec(
        "referenceSurface",
        "Type of reference surface",
        "ReferenceSurfaceType",
        (
            {"value": "localGround", "label": "Local ground"},
            {"value": "meanSeaLevel", "label": "Mean sea level"},
            {"value": "stationGround", "label": "Station ground"},
            {"value": "waterSurface", "label": "Water surface"},
        ),
    ),
    VocabularySpec(
        "exposure",
        "Exposure of instrument",
        "Exposure",
        (
            {"value": "unknown", "label": "Unknown"},
            {"value": "openTerrain", "label": "Open terrain"},
            {"value": "urban", "label": "Urban"},
            {"value": "roof", "label": "Roof"},
        ),
    ),
    VocabularySpec(
        "operatingStatus",
        "Instrument operating status",
        "InstrumentOperatingStatus",
        (
            {"value": "operational", "label": "Operational"},
            {"value": "partlyOperational", "label": "Partly operational"},
            {"value": "notOperational", "label": "Not operational"},
            {"value": "unknown", "label": "Unknown"},
        ),
    ),
    VocabularySpec(
        "observingMethodAtmosphere",
        "Observing method, atmosphere",
        "ObservingMethodAtmosphere",
        (
            {"value": "24", "label": "Human observation"},
            {"value": "95", "label": "Cup anemometer"},
            {"value": "266", "label": "Pyranometer (global solar, broadband)"},
            {"value": "340", "label": "Wet-bulb thermometer"},
        ),
    ),
    VocabularySpec(
        "observedVariableAtmosphere",
        "Observed variable, atmosphere",
        "ObservedVariableAtmosphere",
        (
            {"value": "216", "label": "Air temperature"},
            {"value": "224", "label": "Atmospheric pressure"},
            {"value": "240", "label": "Relative humidity"},
            {"value": "260", "label": "Wind direction"},
            {"value": "261", "label": "Wind speed"},
        ),
    ),
    VocabularySpec(
        "unit",
        "Measurement unit",
        "unit",
        (
            {"value": "m", "label": "metre"},
            {"value": "deg", "label": "degree"},
            {"value": "K", "label": "kelvin"},
            {"value": "Cel", "label": "degree Celsius"},
            {"value": "Pa", "label": "pascal"},
        ),
    ),
    VocabularySpec(
        "facilityType",
        "Facility type",
        "FacilityType",
        (
            {"value": "landFixed", "label": "Land fixed"},
            {"value": "landMobile", "label": "Land mobile"},
            {"value": "seaFixed", "label": "Sea fixed"},
            {"value": "seaMobile", "label": "Sea mobile"},
            {"value": "airborne", "label": "Airborne"},
        ),
    ),
    VocabularySpec(
        "territory",
        "Territory",
        None,
        (
            {"value": "CHE", "label": "Switzerland"},
            {"value": "GRC", "label": "Greece"},
            {"value": "KEN", "label": "Kenya"},
            {"value": "USA", "label": "United States of America"},
            {"value": "DEU", "label": "Germany"},
            {"value": "FRA", "label": "France"},
            {"value": "ITA", "label": "Italy"},
        ),
    ),
    VocabularySpec(
        "climateZone",
        "Climate zone",
        "ClimateZone",
        (
            {"value": "polar", "label": "Polar"},
            {"value": "temperate", "label": "Temperate"},
            {"value": "subtropical", "label": "Subtropical"},
            {"value": "tropical", "label": "Tropical"},
            {"value": "arid", "label": "Arid"},
        ),
    ),
    VocabularySpec(
        "surfaceCoverClassification",
        "Surface cover classification scheme",
        "SurfaceCoverClassification",
        (),
    ),
    VocabularySpec(
        "surfaceCoverGlobCover2009",
        "Surface cover types (GlobCover2009)",
        "SurfaceCoverGlobCover2009",
        (),
    ),
    VocabularySpec(
        "surfaceCoverIGBP",
        "Surface cover types (IGBP)",
        "SurfaceCoverIGBP",
        (),
    ),
    VocabularySpec(
        "surfaceCoverLCCS",
        "Surface cover types (LCCS)",
        "SurfaceCoverLCCS",
        (),
    ),
    VocabularySpec(
        "surfaceCoverPFT",
        "Surface cover types (PFT)",
        "SurfaceCoverPFT",
        (),
    ),
    VocabularySpec(
        "surfaceCoverUMD",
        "Surface cover types (UMD)",
        "SurfaceCoverUMD",
        (),
    ),
    VocabularySpec(
        "surfaceCoverLAIFPAR",
        "Surface cover types (LAI/fPAR)",
        "SurfaceCoverLAIFPAR",
        (),
    ),
    VocabularySpec(
        "surfaceCoverNPP",
        "Surface cover types (NPP)",
        "SurfaceCoverNPP",
        (),
    ),
    VocabularySpec(
        "surfaceRoughness",
        "Surface roughness (Davenport)",
        "SurfaceRoughnessDavenport",
        (),
    ),
    VocabularySpec(
        "localTopography",
        "Local topography",
        "LocalTopography",
        (),
    ),
    VocabularySpec(
        "relativeElevation",
        "Relative elevation",
        "RelativeElevation",
        (),
    ),
    VocabularySpec(
        "topographicContext",
        "Topographic context",
        "TopographicContext",
        (),
    ),
    VocabularySpec(
        "altitudeOrDepth",
        "Altitude/depth",
        "AltitudeOrDepth",
        (),
    ),
    VocabularySpec(
        "observingStrategy",
        "Observing strategy",
        "ObservingStrategy",
        (
            {"value": "continuous", "label": "Continuous"},
            {"value": "periodic", "label": "Periodic"},
            {"value": "eventDriven", "label": "Event driven"},
            {"value": "onDemand", "label": "On demand"},
        ),
    ),
    VocabularySpec(
        "dataPolicy",
        "Data policy",
        "DataPolicy",
        (
            {"value": "noLimitation", "label": "No limitation"},
            {"value": "essential", "label": "Essential"},
            {"value": "additional", "label": "Additional"},
            {"value": "restricted", "label": "Restricted"},
        ),
    ),
    VocabularySpec(
        "levelOfData",
        "Level of data",
        "LevelOfData",
        (
            {"value": "level0", "label": "Level 0"},
            {"value": "level1", "label": "Level 1"},
            {"value": "level2", "label": "Level 2"},
            {"value": "level3", "label": "Level 3"},
        ),
    ),
    VocabularySpec(
        "referenceTimeSource",
        "Reference time source",
        "ReferenceTimeSource",
        (
            {"value": "timeServer", "label": "Time server"},
            {"value": "gps", "label": "GPS"},
            {"value": "localClock", "label": "Local clock"},
        ),
        multiple=True,
    ),
    VocabularySpec(
        "timeStampMeaning",
        "Timestamp meaning",
        "TimestampMeaning",
        (
            {"value": "beginning", "label": "Beginning of interval"},
            {"value": "middle", "label": "Middle of interval"},
            {"value": "end", "label": "End of interval"},
        ),
    ),
    VocabularySpec(
        "dataFormat",
        "Data format",
        "DataFormat",
        (
            {"value": "BUFR", "label": "BUFR"},
            {"value": "CREX", "label": "CREX"},
            {"value": "netCDF", "label": "netCDF"},
            {"value": "csv", "label": "CSV"},
            {"value": "json", "label": "JSON"},
        ),
        multiple=True,
    ),
)

_CACHE: dict[str, Any] | None = None
_CACHE_TIME = 0.0


class _VocabularyTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_tr = False
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_tr = True
            self._current_row = []
        if self._in_tr and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_cell and tag in {"td", "th"}:
            text = " ".join(" ".join(self._current_cell).split())
            self._current_row.append(text)
            self._current_cell = []
            self._in_cell = False
        if tag == "tr" and self._in_tr:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []
            self._in_tr = False


def get_all_vocabularies(*, live: bool = True, refresh: bool = False) -> dict[str, Any]:
    """Return cached vocabulary options for UI controls.

    The backend tries to fetch selected WMDR registers from the WMO Codes
    Registry, but every vocabulary has a small static fallback so the PoC remains
    usable offline or behind a firewall.
    """
    global _CACHE, _CACHE_TIME
    now = time.time()
    if not refresh and _CACHE is not None and now - _CACHE_TIME < _CACHE_TTL_SECONDS:
        return _CACHE

    if os.environ.get("OSCAR_NODE_VOCABULARY_LIVE", "1").lower() in {"0", "false", "no", "off"}:
        live = False

    vocabularies: dict[str, Any] = {}
    remote_results: dict[str, list[dict[str, str]]] = {}
    errors: dict[str, str] = {}

    if live:
        with ThreadPoolExecutor(max_workers=min(8, len(VOCABULARY_SPECS))) as executor:
            futures = {executor.submit(_fetch_remote_options, spec): spec for spec in VOCABULARY_SPECS if spec.register_url}
            done, not_done = wait(futures, timeout=_REMOTE_OVERALL_TIMEOUT_SECONDS)
            for future in done:
                spec = futures[future]
                try:
                    options = future.result()
                except Exception as exc:  # noqa: BLE001 - use fallback for UI vocabulary
                    errors[spec.name] = str(exc)
                    continue
                if options:
                    remote_results[spec.name] = options
            for future in not_done:
                spec = futures[future]
                errors[spec.name] = f"Timed out after {_REMOTE_OVERALL_TIMEOUT_SECONDS:g} s"

    for spec in VOCABULARY_SPECS:
        options = remote_results.get(spec.name) or [_normalize_option(option) for option in spec.fallback]
        vocabularies[spec.name] = {
            "name": spec.name,
            "title": spec.title,
            "register": spec.register,
            "register_url": spec.register_url,
            "multiple": spec.multiple,
            "source": "wmo-codes-registry" if spec.name in remote_results else "static-fallback",
            "error": errors.get(spec.name),
            "options": options,
        }

    _CACHE = {
        "source": "mixed" if remote_results else "static-fallback",
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "vocabularies": vocabularies,
    }
    _CACHE_TIME = now
    return _CACHE


def get_vocabulary(name: str, *, live: bool = True, refresh: bool = False) -> dict[str, Any]:
    vocabularies = get_all_vocabularies(live=live, refresh=refresh)["vocabularies"]
    if name not in vocabularies:
        raise KeyError(name)
    return vocabularies[name]


def _fetch_remote_options(spec: VocabularySpec) -> list[dict[str, str]]:
    if not spec.register_url:
        return []
    errors: list[str] = []
    for url, accept in (
        (f"{spec.register_url}?_format=jsonld", "application/ld+json, application/json;q=0.9, text/html;q=0.5"),
        (spec.register_url, "text/html, application/xhtml+xml;q=0.9, application/ld+json;q=0.5"),
    ):
        try:
            raw, content_type = _read_url(url, accept=accept)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        if "json" in content_type or raw.lstrip().startswith((b"{", b"[")):
            try:
                options = _options_from_jsonld(json.loads(raw.decode("utf-8")))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: invalid JSON-LD: {exc}")
                continue
        else:
            options = _options_from_html(raw.decode("utf-8", errors="replace"))
        if options:
            return _dedupe_options(options)
    raise RuntimeError("; ".join(errors) if errors else f"No options found for {spec.register_url}")


def _read_url(url: str, *, accept: str) -> tuple[bytes, str]:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "wigos-node-poc/0.4.0 (+https://github.com/MeteoSwiss)",
        },
    )
    with urlopen(request, timeout=_REMOTE_TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed public registry URLs
        return response.read(), response.headers.get_content_type()


def _options_from_html(html: str) -> list[dict[str, str]]:
    parser = _VocabularyTableParser()
    parser.feed(html)
    options: list[dict[str, str]] = []
    for cells in parser.rows:
        if len(cells) < 4:
            continue
        notation, label, description, status = cells[:4]
        if notation.lower() in {"notation", "uri", "category", "description", "label", "member", "subregister"}:
            continue
        if not notation or not label:
            continue
        if status and status.lower() not in {"stable", "deprecated", "experimental", "draft", "valid"}:
            continue
        options.append(_normalize_option({"value": notation, "label": label, "description": description, "status": status}))
    return options


def _options_from_jsonld(data: Any) -> list[dict[str, str]]:
    nodes = _iter_json_nodes(data)
    options: list[dict[str, str]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        notation = _first_literal(
            node.get("notation")
            or node.get("skos:notation")
            or node.get("http://www.w3.org/2004/02/skos/core#notation")
        )
        label = _first_literal(
            node.get("prefLabel")
            or node.get("skos:prefLabel")
            or node.get("label")
            or node.get("rdfs:label")
            or node.get("http://www.w3.org/2004/02/skos/core#prefLabel")
            or node.get("http://www.w3.org/2000/01/rdf-schema#label")
        )
        if not notation or not label:
            continue
        description = _first_literal(
            node.get("description")
            or node.get("skos:definition")
            or node.get("http://www.w3.org/2004/02/skos/core#definition")
        )
        status = _first_literal(node.get("status") or node.get("reg:status") or node.get("http://purl.org/linked-data/registry#status"))
        uri = _first_literal(node.get("@id") or node.get("id"))
        options.append(_normalize_option({"value": notation, "label": label, "description": description, "status": status, "uri": uri}))
    return options


def _iter_json_nodes(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [node for item in value for node in _iter_json_nodes(item)]
    if isinstance(value, dict):
        nodes = [value]
        for key in ("@graph", "graph", "member", "members", "contains", "contents"):
            if key in value:
                nodes.extend(_iter_json_nodes(value[key]))
        return nodes
    return []


def _first_literal(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    if isinstance(value, dict):
        for key in ("@value", "value", "label", "@id"):
            if key in value:
                return _first_literal(value[key])
        return ""
    if isinstance(value, list):
        for item in value:
            text = _first_literal(item)
            if text:
                return text
    return ""


def _dedupe_options(options: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for option in options:
        value = option.get("value", "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(option)
    return sorted(result, key=lambda item: (item.get("label", "").lower(), _numeric_sort_key(item.get("value", ""))))


def _numeric_sort_key(value: str) -> tuple[int, str]:
    return (int(value), "") if str(value).isdigit() else (10**9, str(value))


def _normalize_option(option: dict[str, Any]) -> dict[str, str]:
    value = str(option.get("value") or option.get("notation") or "").strip()
    label = str(option.get("label") or option.get("name") or value).strip()
    normalized = {"value": value, "label": label}
    for key in ("description", "status", "uri"):
        raw = option.get(key)
        if raw not in (None, ""):
            normalized[key] = str(raw).strip()
    return normalized
