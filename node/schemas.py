"""Local WMDR2 v0.4.0 schema fragment for the WIGOS Node PoC.

This is intentionally a pragmatic UI validator, not a verbatim copy of the
normative wmdr2-devt schema. It tracks the v0.4.0 public record shape closely
for the parts edited by the PoC: Facility records use ``properties.observations``;
Observations use ``configurations``; controlled values are Concept-like objects
with an ``id``; Configuration serial numbers are held in
``instrumentSerialNumber``; and vertical distance is represented by the
``verticalDistance`` compound object.
"""

WMDR2_CORE_CONFORMANCE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"

WSI_PATTERN = r"^(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$"

CONCEPT = {"type": "object", "required": ["id"], "additionalProperties": True, "properties": {"id": {"type": "string", "minLength": 1}, "url": {"type": "string"}}}
CONCEPT_OR_NULL = {"anyOf": [CONCEPT, {"type": "null"}]}

WMDR2_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/wigos-node-poc/schemas/wmdr2-v04-record-poc.schema.json",
    "title": "WMDR2 v0.4.0 full record PoC schema",
    "type": "object",
    "required": ["type", "id", "conformsTo", "geometry", "properties"],
    "additionalProperties": True,
    "properties": {
        "type": {"const": "Feature"},
        "id": {"type": "string", "pattern": WSI_PATTERN},
        "conformsTo": {"type": "array", "contains": {"const": WMDR2_CORE_CONFORMANCE}},
        "geometry": {"anyOf": [{"$ref": "#/$defs/pointGeometry"}, {"type": "null"}]},
        "temporalGeometry": {"$ref": "#/$defs/temporalGeometry"},
        "time": {"anyOf": [{"$ref": "#/$defs/timeObject"}, {"type": "null"}]},
        "properties": {"$ref": "#/$defs/facilityProperties"},
        "links": {"type": "array"},
    },
    "$defs": {
        "dateOrOpen": {"type": "string", "anyOf": [{"const": ".."}, {"pattern": r"^\d{4}-\d{2}-\d{2}$"}, {"pattern": r"^\d{4}-\d{2}$"}, {"pattern": r"^\d{4}$"}]},
        "timestamp": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?$"},
        "concept": CONCEPT,
        "conceptOrNull": CONCEPT_OR_NULL,
        "pointGeometry": {"type": "object", "required": ["type", "coordinates"], "additionalProperties": True, "properties": {"type": {"const": "Point"}, "coordinates": {"type": "array", "minItems": 2, "maxItems": 3, "items": {"type": "number"}}}},
        "temporalGeometry": {"type": "object", "required": ["type", "coordinates", "dates"], "additionalProperties": False, "properties": {"type": {"const": "MovingPoint"}, "coordinates": {"type": "array", "items": {"type": "array", "minItems": 2, "maxItems": 3, "items": {"type": "number"}}}, "dates": {"type": "array", "items": {"$ref": "#/$defs/dateOrOpen"}}, "methods": {"type": "array"}}},
        "timeObject": {"type": "object", "additionalProperties": True, "anyOf": [{"required": ["date"]}, {"required": ["timestamp"]}, {"required": ["interval"]}], "properties": {"date": {"$ref": "#/$defs/dateOrOpen"}, "timestamp": {"$ref": "#/$defs/timestamp"}, "interval": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"$ref": "#/$defs/dateOrOpen"}}, "resolution": {"type": "string"}}},
        "timePeriod": {"type": "object", "required": ["interval"], "additionalProperties": True, "properties": {"interval": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"$ref": "#/$defs/dateOrOpen"}}, "resolution": {"type": "string"}}},
        "dates": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"$ref": "#/$defs/dateOrOpen"}},
        "contact": {"type": "object", "additionalProperties": True, "anyOf": [{"required": ["organization"]}, {"required": ["name"]}, {"required": ["identifier"]}], "properties": {"identifier": {"type": "string"}, "name": {"type": "string"}, "organization": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string"}}, "emails": {"type": "array"}, "phones": {"type": "array"}, "addresses": {"type": "array"}, "links": {"type": "array"}}},
        "facilityProperties": {"type": "object", "required": ["type", "title", "facilityType"], "additionalProperties": True, "properties": {"type": {"const": "facility"}, "title": {"type": "string", "minLength": 1}, "description": {"type": "string"}, "additionalTitles": {"type": "array", "items": {"type": "string"}}, "additionalIds": {"type": "array", "items": {"type": "string", "pattern": WSI_PATTERN}}, "created": {"type": "string"}, "updated": {"type": "string"}, "facilityType": {"$ref": "#/$defs/conceptOrNull"}, "wmoRegion": {"$ref": "#/$defs/concept"}, "contacts": {"type": "array", "items": {"$ref": "#/$defs/contact"}}, "keywords": {"type": "array"}, "facilitySets": {"type": "array"}, "territories": {"type": "array", "items": {"$ref": "#/$defs/territory"}}, "environment": {"type": "array", "items": {"$ref": "#/$defs/environment"}}, "observations": {"type": "array", "items": {"$ref": "#/$defs/observation"}}, "instruments": {"type": "array", "items": {"$ref": "#/$defs/instrument"}}, "schedules": {"type": "array", "items": {"$ref": "#/$defs/schedule"}}, "links": False, "territory": False, "observationSeries": False, "programAffiliations": False, "programAffiliation": False, "deployments": False, "reporting": False}},
        "territory": {"type": "object", "required": ["territory"], "additionalProperties": False, "properties": {"territory": {"$ref": "#/$defs/conceptOrNull"}, "dates": {"$ref": "#/$defs/dates"}, "time": False, "date": False}},
        "surfaceCover": {"type": "object", "required": ["value", "scheme"], "additionalProperties": False, "properties": {"value": {"$ref": "#/$defs/concept"}, "scheme": {"$ref": "#/$defs/concept"}}},
        "topographyBathymetry": {"type": "object", "additionalProperties": False, "anyOf": [{"required": ["localTopography"]}, {"required": ["relativeElevation"]}, {"required": ["topographicContext"]}, {"required": ["altitudeOrDepth"]}], "properties": {"localTopography": {"$ref": "#/$defs/concept"}, "relativeElevation": {"$ref": "#/$defs/concept"}, "topographicContext": {"$ref": "#/$defs/concept"}, "altitudeOrDepth": {"$ref": "#/$defs/concept"}}},
        "environment": {"type": "object", "additionalProperties": True, "properties": {"time": {"$ref": "#/$defs/timePeriod"}, "climateZone": {"$ref": "#/$defs/concept"}, "surfaceCover": {"$ref": "#/$defs/surfaceCover"}, "surfaceRoughness": {"$ref": "#/$defs/concept"}, "population": {"type": "array", "minItems": 2, "maxItems": 2}, "perimeter_km": {"type": "array", "minItems": 2, "maxItems": 2}, "topographyBathymetry": {"$ref": "#/$defs/topographyBathymetry"}, "date": False}},
        "observedFeature": {"type": "object", "required": ["domain"], "additionalProperties": False, "properties": {"domain": {"$ref": "#/$defs/conceptOrNull"}, "domainFeature": {"$ref": "#/$defs/concept"}, "featureName": {"type": "string"}}},
        "programAffiliation": {"type": "object", "required": ["programAffiliation"], "additionalProperties": False, "properties": {"programAffiliation": {"$ref": "#/$defs/concept"}, "reportingStatus": {"$ref": "#/$defs/conceptOrNull"}, "dates": {"$ref": "#/$defs/dates"}, "program": False, "time": False, "date": False}},
        "observation": {"type": "object", "required": ["id", "observedProperty", "observedGeometry", "observedFeature", "programAffiliations", "configurations"], "additionalProperties": True, "properties": {"id": {"type": "string", "minLength": 1}, "title": {"type": "string"}, "description": {"type": "string"}, "observedProperty": {"$ref": "#/$defs/concept"}, "observedGeometry": {"$ref": "#/$defs/concept"}, "observedFeature": {"$ref": "#/$defs/observedFeature"}, "programAffiliations": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/programAffiliation"}}, "applicationAreas": {"type": "array", "items": {"$ref": "#/$defs/concept"}}, "representativeness": {"$ref": "#/$defs/concept"}, "configurations": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/configuration"}}, "observingProcedures": {"type": "array", "items": {"$ref": "#/$defs/observingProcedure"}}, "reportingProcedures": {"type": "array", "items": {"$ref": "#/$defs/reportingProcedure"}}, "contacts": {"type": "array", "items": {"$ref": "#/$defs/contact"}}, "observationSeries": False, "observingConfigurations": False, "observedDomain": False, "applicationArea": False, "programAffiliation": False, "time": False, "uid": False, "validFrom": False, "validTo": False}},
        "configuration": {"type": "object", "required": ["id", "time"], "additionalProperties": True, "properties": {"id": {"type": "string", "minLength": 1}, "time": {"$ref": "#/$defs/timePeriod"}, "geometry": {"$ref": "#/$defs/pointGeometry"}, "observingMethod": {"$ref": "#/$defs/conceptOrNull"}, "operatingStatus": {"$ref": "#/$defs/conceptOrNull"}, "sourceOfObservation": {"$ref": "#/$defs/conceptOrNull"}, "instrument": {"type": ["string", "integer", "null"]}, "instrumentSerialNumber": {"type": "string"}, "verticalDistance": {"type": "object", "required": ["distances", "unit", "referenceSurface"], "additionalProperties": True, "properties": {"distances": {"type": "array", "minItems": 1, "items": {"type": ["number", "integer", "string"]}}, "unit": {"$ref": "#/$defs/conceptOrNull"}, "referenceSurface": {"$ref": "#/$defs/conceptOrNull"}}}, "exposure": {"$ref": "#/$defs/concept"}, "relativeLocation": {"type": "string"}, "description": {"type": "string"}, "deployment": False, "observingLocation": False, "serialNumber": False, "referenceSurface": False, "verticalDistanceFromReferenceSurface": False, "validFrom": False, "validTo": False}},
        "observingProcedure": {"type": "object", "required": ["time", "observingSchedules"], "additionalProperties": True, "properties": {"strategy": {"$ref": "#/$defs/concept"}, "observingSchedules": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^schedule_"}}, "time": {"$ref": "#/$defs/timePeriod"}, "date": False, "validFrom": False}},
        "reportingProcedure": {"type": "object", "required": ["internationalExchange", "dataPolicy"], "additionalProperties": True, "properties": {"internationalExchange": {"type": "boolean"}, "dataFormat": {"type": "array", "items": {"$ref": "#/$defs/concept"}}, "dataPolicy": {"$ref": "#/$defs/conceptOrNull"}, "levelOfData": {"$ref": "#/$defs/concept"}, "uom": {"$ref": "#/$defs/concept"}, "temporalReportingInterval": {"type": "string"}, "temporalAggregate": {"type": "string"}, "reportingSchedules": {"type": "array", "items": {"type": "string", "pattern": "^schedule_"}}, "spatialReportingInterval": False, "time": False, "date": False, "validFrom": False}},
        "instrument": {"type": "object", "anyOf": [{"required": ["id"]}, {"required": ["uid"]}], "additionalProperties": True, "properties": {"id": {"type": "string", "pattern": "^instrument:"}, "uid": {"type": "string", "pattern": "^instrument:"}, "manufacturer": {"type": ["string", "null"]}, "model": {"type": ["string", "null"]}, "observingMethods": {"type": "array", "items": {"$ref": "#/$defs/concept"}}, "verticalRange": {"type": "object"}, "serialNumber": False, "instrumentSerialNumber": False}},
        "schedule": {"type": "object", "required": ["uid", "start"], "additionalProperties": True, "properties": {"uid": {"type": "string", "pattern": "^schedule_"}, "@type": {"type": "string"}, "start": {"type": "string"}, "duration": {"type": "string"}, "recurrenceRules": {"type": "array"}}},
    },
}
