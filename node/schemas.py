"""Local WMDR2 v0.3.x schema fragment for the OSCAR nextGen Node PoC.

This is intentionally a pragmatic UI validator, not the final normative WMDR2
schema. It follows the current wmdr2-devt v0.3.x record shape closely enough to
avoid rejecting generated examples: bare WSI record ids, ObservationSeries with
`id` or `uid`, optional/empty observingConfigurations, and time-varying objects
represented with `time.interval` rather than legacy `validFrom`/`date`.
"""

WMDR2_CORE_CONFORMANCE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"

WSI_PATTERN = r"^(0|1|2|3)-([1-9]\d*)-([0-9]+)-([A-Za-z0-9._-]+)$"

WMDR2_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/oscar-nextgen-poc/schemas/wmdr2-v03-record-poc.schema.json",
    "title": "WMDR2 v0.3.x full record PoC schema",
    "type": "object",
    "required": ["type", "id", "conformsTo", "geometry", "properties"],
    "additionalProperties": True,
    "properties": {
        "type": {"const": "Feature"},
        "id": {"type": "string", "pattern": WSI_PATTERN},
        "conformsTo": {
            "type": "array",
            "contains": {"const": WMDR2_CORE_CONFORMANCE},
        },
        "geometry": {
            "anyOf": [
                {"$ref": "#/$defs/pointGeometry"},
                {"type": "null"},
            ]
        },
        "temporalGeometry": {"$ref": "#/$defs/temporalGeometry"},
        "time": {
            "anyOf": [
                {"$ref": "#/$defs/timeObject"},
                {"type": "null"},
            ]
        },
        "properties": {"$ref": "#/$defs/facilityProperties"},
    },
    "$defs": {
        "dateOrOpen": {
            "type": "string",
            "anyOf": [
                {"const": ".."},
                {"pattern": r"^\d{4}-\d{2}-\d{2}$"},
                {"pattern": r"^\d{4}-\d{2}$"},
                {"pattern": r"^\d{4}$"},
            ],
        },
        "timestamp": {
            "type": "string",
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?$",
        },
        "codeValue": {
            "type": ["string", "number", "integer", "object", "array", "boolean", "null"],
        },
        "singleCodeValue": {
            "type": ["string", "number", "integer", "object", "boolean", "null"],
        },
        "quantity": {
            "type": "object",
            "required": ["value"],
            "additionalProperties": True,
            "properties": {
                "value": {"type": ["number", "integer", "string"]},
                "uom": {"$ref": "#/$defs/codeValue"},
            },
        },
        "pointGeometry": {
            "type": "object",
            "required": ["type", "coordinates"],
            "additionalProperties": True,
            "properties": {
                "type": {"const": "Point"},
                "coordinates": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 3,
                    "items": {"type": "number"},
                },
            },
        },
        "temporalGeometry": {
            "type": "object",
            "required": ["type", "coordinates", "dates"],
            "additionalProperties": True,
            "properties": {
                "type": {"const": "MovingPoint"},
                "coordinates": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 3,
                        "items": {"type": "number"},
                    },
                },
                "dates": {"type": "array", "items": {"$ref": "#/$defs/dateOrOpen"}},
                "methods": {"type": "array"},
            },
        },
        "timeObject": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "date": {"$ref": "#/$defs/dateOrOpen"},
                "timestamp": {"$ref": "#/$defs/timestamp"},
                "interval": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"$ref": "#/$defs/dateOrOpen"},
                },
                "resolution": {"type": "string"},
            },
        },
        "datedItem": {
            "type": "object",
            "required": ["time"],
            "additionalProperties": True,
            "properties": {
                "time": {"$ref": "#/$defs/timeObject"},
                "date": False,
                "validFrom": False,
            },
        },
        "contactAssignment": {
            "type": "object",
            "required": ["contact", "roles"],
            "additionalProperties": False,
            "properties": {
                "contact": {"type": "string", "pattern": "^contact:"},
                "roles": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            },
        },
        "contact": {
            "type": "object",
            "additionalProperties": True,
            "anyOf": [
                {"required": ["organization"]},
                {"required": ["name"]},
                {"required": ["identifier"]},
                {"required": ["uid"]},
            ],
            "properties": {
                "identifier": {"type": "string"},
                "uid": {"type": "string", "pattern": "^contact:"},
                "name": {"type": "string"},
                "organization": {"type": "string"},
                "roles": {"type": "array", "items": {"type": "string"}},
                "emails": {"type": "array"},
                "phones": {"type": "array"},
                "addresses": {"type": "array"},
                "links": {"type": "array"},
            },
        },
        "facilityProperties": {
            "type": "object",
            "required": ["type", "title"],
            "additionalProperties": True,
            "properties": {
                "type": {"const": "facility"},
                "title": {"type": "string", "minLength": 1},
                "additionalTitles": {"type": "array", "items": {"type": "string"}},
                "additionalIds": {"type": "array", "items": {"type": "string", "pattern": WSI_PATTERN}},
                "description": {"type": "string"},
                "created": {"type": "string"},
                "updated": {"type": "string"},
                "facilityType": {"type": "string"},
                "wmoRegion": {"type": "string"},
                "contacts": {"type": "array", "items": {"$ref": "#/$defs/contact"}},
                "contactAssignments": {"type": "array", "items": {"$ref": "#/$defs/contactAssignment"}},
                "keywords": {"type": "array"},
                "links": {"type": "array"},
                "facilitySets": {"type": "array"},
                "environment": {"type": "array", "items": {"$ref": "#/$defs/datedItem"}},
                "territory": {"type": "array", "items": {"$ref": "#/$defs/datedItem"}},
                "programAffiliations": {"type": "array", "items": {"$ref": "#/$defs/datedItem"}},
                "programAffiliation": {"type": "array", "items": {"$ref": "#/$defs/datedItem"}},
                "observationSeries": {"type": "array", "items": {"$ref": "#/$defs/observationSeries"}},
                "instruments": {"type": "array", "items": {"$ref": "#/$defs/instrument"}},
                "schedules": {"type": "array", "items": {"$ref": "#/$defs/schedule"}},
                "deployments": False,
                "reporting": False,
            },
        },
        "observedFeature": {
            "type": "object",
            "required": ["domain"],
            "additionalProperties": True,
            "properties": {
                "domain": {"$ref": "#/$defs/codeValue"},
                "domainFeature": {"$ref": "#/$defs/codeValue"},
                "featureName": {"type": ["string", "null"]},
            },
        },
        "observingConfiguration": {
            "type": "object",
            "required": ["observingMethod"],
            "additionalProperties": True,
            "properties": {
                "observingMethod": {"$ref": "#/$defs/codeValue"},
                "operatingStatus": {"$ref": "#/$defs/singleCodeValue"},
                "sourceOfObservation": {"$ref": "#/$defs/codeValue"},
                "instrument": {"type": ["string", "null"], "pattern": "^instrument:"},
                "serialNumber": {"type": "string", "minLength": 1},
                "exposure": {"$ref": "#/$defs/codeValue"},
                "time": {"$ref": "#/$defs/timeObject"},
                "geometry": {"$ref": "#/$defs/pointGeometry"},
                "referenceSurface": {"$ref": "#/$defs/codeValue"},
                "relativeLocation": {"type": "string"},
                "verticalDistanceFromReferenceSurface": {"$ref": "#/$defs/quantity"},
                "date": False,
                "validFrom": False,
                "observingLocation": False,
                "deployment": False,
                "temporalGeometry": False,
            },
        },
        "observingProcedure": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "strategy": {"$ref": "#/$defs/codeValue"},
                "observingSchedules": {"type": "array", "items": {"type": "string"}},
                "time": {"$ref": "#/$defs/timeObject"},
                "date": False,
                "validFrom": False,
            },
        },
        "reportingProcedure": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "internationalExchange": {"type": ["boolean", "null"]},
                "uom": {"$ref": "#/$defs/codeValue"},
                "spatialReportingInterval": {"$ref": "#/$defs/codeValue"},
                "timeliness": {"type": ["string", "null"]},
                "dataPolicy": {"$ref": "#/$defs/codeValue"},
                "levelOfData": {"$ref": "#/$defs/codeValue"},
                "numberOfObservationsInReportingInterval": {"type": ["integer", "number", "string", "null"]},
                "referenceDatum": {"$ref": "#/$defs/codeValue"},
                "referenceTimeSource": {"type": "array", "items": {"$ref": "#/$defs/codeValue"}},
                "strategy": {"$ref": "#/$defs/codeValue"},
                "timeStampMeaning": {"$ref": "#/$defs/codeValue"},
                "reportingSchedules": {"type": "array", "items": {"type": "string"}},
                "links": {"type": "array"},
                "time": False,
                "date": False,
                "validFrom": False,
            },
        },
        "observationSeries": {
            "type": "object",
            "anyOf": [{"required": ["id"]}, {"required": ["uid"]}],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "pattern": "^observationSeries:"},
                "uid": {"type": "string", "pattern": "^observationSeries:"},
                "title": {"type": "string"},
                "observedProperty": {"$ref": "#/$defs/codeValue"},
                "observedGeometry": {"$ref": "#/$defs/codeValue"},
                "observedFeature": {"$ref": "#/$defs/observedFeature"},
                "observedDomain": {"$ref": "#/$defs/observedFeature"},
                "applicationAreas": {"type": "array", "items": {"$ref": "#/$defs/codeValue"}},
                "applicationArea": {"type": ["array", "string", "number", "integer", "object", "null"]},
                "programAffiliations": {"type": "array"},
                "programAffiliation": {"type": "array"},
                "observingConfigurations": {"type": "array", "items": {"$ref": "#/$defs/observingConfiguration"}},
                "observingProcedures": {"type": "array", "items": {"$ref": "#/$defs/observingProcedure"}},
                "reportingProcedures": {"type": "array", "items": {"$ref": "#/$defs/reportingProcedure"}},
                "reporting": {"type": "array", "items": {"$ref": "#/$defs/reportingProcedure"}},
                "officialStatus": {"type": "array"},
                "contactAssignments": {"type": "array", "items": {"$ref": "#/$defs/contactAssignment"}},
                "contacts": {"type": "array", "items": {"$ref": "#/$defs/contact"}},
                "keywords": {"type": "array"},
                "links": {"type": "array"},
            },
        },
        "instrument": {
            "type": "object",
            "anyOf": [{"required": ["id"]}, {"required": ["uid"]}],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "pattern": "^instrument:"},
                "uid": {"type": "string", "pattern": "^instrument:"},
                "serialNumber": False,
                "serialNumbers": False,
                "manufacturer": {"type": ["string", "null"]},
                "model": {"type": ["string", "null"]},
                "observingMethods": {"type": "array", "items": {"$ref": "#/$defs/codeValue"}},
            },
        },
        "schedule": {
            "type": "object",
            "required": ["uid"],
            "additionalProperties": True,
            "properties": {
                "uid": {"type": "string", "pattern": "^schedule_"},
                "@type": {"type": "string"},
                "start": {"type": "string"},
                "duration": {"type": "string"},
                "recurrenceRules": {"type": "array"},
            },
        },
    },
}
