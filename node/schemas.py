"""Local WMDR2 schema fragment for the OSCAR nextGen Node PoC.

This schema intentionally validates the current WMDR2 draft *shape* used by
wmo-im/wmdr2-devt v0.2.5.x examples. It is not a complete normative WMDR2
validator and does not validate WMO codelists. Its purpose is to protect the UI
round-trip: upload -> edit -> save -> export.
"""

WMDR2_CORE_CONFORMANCE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"

DATE_OR_OPEN = r"^(\.\.|\d{4}-\d{2}-\d{2})$"
DATE_TIME_OR_OPEN = r"^(\.\.|\d{4}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2}T.*)$"

WMDR2_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/oscar-nextgen-poc/schemas/wmdr2-record-poc.schema.json",
    "title": "WMDR2 full record PoC schema",
    "type": "object",
    "required": ["type", "id", "geometry", "time", "conformsTo", "properties"],
    "additionalProperties": True,
    "properties": {
        "type": {"const": "Feature"},
        "id": {"type": "string", "pattern": "^facility:"},
        "geometry": {
            "anyOf": [
                {"type": "null"},
                {
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
            ]
        },
        "temporalGeometry": {"$ref": "#/$defs/temporalGeometry"},
        "time": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": ["interval"],
                    "properties": {
                        "interval": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {"$ref": "#/$defs/dateOrOpen"},
                        }
                    },
                    "additionalProperties": True,
                },
            ]
        },
        "conformsTo": {
            "type": "array",
            "minItems": 1,
            "contains": {"const": WMDR2_CORE_CONFORMANCE},
        },
        "properties": {
            "type": "object",
            "required": ["type", "title"],
            "additionalProperties": True,
            "properties": {
                "type": {"const": "facility"},
                "title": {"type": "string", "minLength": 1},
                "description": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": ["string", "integer"]}},
                "contacts": {"type": "array", "items": {"$ref": "#/$defs/contact"}},
                "observationSeries": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/observationSeries"},
                },
                "deployments": {"type": "array", "items": {"$ref": "#/$defs/deployment"}},
                "instruments": {"type": "array", "items": {"$ref": "#/$defs/instrument"}},
                "reporting": {"type": "array", "items": {"type": "object"}},
                "schedules": {"type": "array", "items": {"type": "object"}},
                "environment": {"type": "array", "items": {"type": "object"}},
                "programAffiliation": {"type": "array", "items": {"type": "object"}},
                "territory": {"type": "array", "items": {"type": "object"}},
                "facilitySets": {"type": "array", "items": {"type": "string"}},
            },
            "allOf": [
                {"not": {"required": ["wmdr2"]}},
                {"not": {"required": ["themes"]}},
                {"not": {"required": ["temporalContacts"]}},
                {"not": {"required": ["externalIds"]}},
                {"not": {"required": ["facilitySet"]}},
                {"not": {"required": ["temporalGeometry"]}},
                {"not": {"required": ["observations"]}},
                {"not": {"required": ["temporalProgramAffiliation"]}},
            ],
        },
    },
    "$defs": {
        "dateOrOpen": {"type": "string", "pattern": DATE_OR_OPEN},
        "dateTimeOrOpen": {"type": "string", "pattern": DATE_TIME_OR_OPEN},
        "temporalGeometry": {
            "type": "object",
            "required": ["type", "coordinates", "dates"],
            "additionalProperties": False,
            "properties": {
                "type": {"const": "MovingPoint"},
                "coordinates": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 3,
                        "items": {"type": "number"},
                    },
                },
                "dates": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/dateOrOpen"},
                },
                "methods": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "stringOrObject": {
            "anyOf": [
                {"type": "string"},
                {"type": "object", "additionalProperties": True},
            ]
        },
        "nilReasonOrCode": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"},
                {
                    "type": "object",
                    "required": ["nilReason"],
                    "additionalProperties": True,
                    "properties": {"nilReason": {"type": "string"}},
                },
            ]
        },
        "contact": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "name": {"type": "string"},
                "organization": {"type": "string"},
                "position": {"type": "string"},
                "roles": {"type": "array", "items": {"type": "string"}},
                "emails": {"type": "array", "items": {"$ref": "#/$defs/stringOrObject"}},
                "phones": {"type": "array", "items": {"$ref": "#/$defs/stringOrObject"}},
                "addresses": {"type": "array", "items": {"type": "object"}},
                "links": {"type": "array", "items": {"type": "object"}},
            },
        },
        "observationSeries": {
            "type": "object",
            "required": ["id", "observedProperty"],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "pattern": "^observationSeries:"},
                "title": {"type": "string"},
                "observedProperty": {"type": ["string", "integer"]},
                "observedGeometry": {"type": ["string", "integer"]},
                "observedFeature": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "domain": {"type": ["string", "integer"]},
                        "domainFeature": {"type": "string", "minLength": 1},
                        "featureName": {"type": "string", "minLength": 1},
                    },
                },
                "applicationArea": {"type": "array", "items": {"type": ["string", "integer"]}},
                "programAffiliation": {"type": "array", "items": {"type": ["string", "integer"]}},
                "representativeness": {"type": ["string", "integer"]},
                "observingConfigurations": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/observingConfiguration"},
                },
                "observingProcedures": {"type": "array", "items": {"type": "object"}},
                "reporting": {"type": "array", "items": {"type": "object"}},
                "officialStatus": {"type": "array", "items": {"type": "object"}},
            },
            "allOf": [
                {"not": {"required": ["observedVariable"]}},
                {"not": {"required": ["observedGeometryType"]}},
                {"not": {"required": ["observedDomain"]}},
                {"not": {"required": ["programAffiliations"]}},
                {"not": {"required": ["deployments"]}},
                {"not": {"required": ["description"]}},
                {"not": {"required": ["type"]}},
            ],
        },
        "observingConfiguration": {
            "type": "object",
            "required": ["date", "observingMethod"],
            "additionalProperties": True,
            "properties": {
                "date": {"$ref": "#/$defs/dateOrOpen"},
                "deployment": {"type": "string", "pattern": "^deployment:"},
                "observingMethod": {"$ref": "#/$defs/nilReasonOrCode"},
                "operatingStatus": {"type": ["string", "integer"]},
                "exposure": {"type": ["string", "integer"]},
            },
        },
        "deployment": {
            "type": "object",
            "required": ["id"],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "pattern": "^deployment:"},
                "instrument": {"type": "string", "pattern": "^instrument:"},
                "serialNumber": {"type": "string"},
                "sourceOfObservation": {"type": ["string", "integer"]},
                "geometry": {
                    "anyOf": [
                        {"type": "null"},
                        {
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
                    ]
                },
                "referenceSurface": {"type": ["string", "integer"]},
                "verticalDistanceFromReferenceSurface": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {"type": ["number", "string"]},
                        "uom": {"type": ["string", "integer"]},
                    },
                    "additionalProperties": False,
                },
            },
            "allOf": [
                {"not": {"required": ["title"]}},
                {"not": {"required": ["type"]}},
                {"not": {"required": ["manufacturer"]}},
                {"not": {"required": ["model"]}},
                {"not": {"required": ["localReferenceSurface"]}},
                {"not": {"required": ["temporalGeometry"]}},
            ],
        },
        "instrument": {
            "type": "object",
            "required": ["id"],
            "additionalProperties": True,
            "properties": {
                "id": {"type": "string", "pattern": "^instrument:"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "manufacturer": {"type": "string"},
                "model": {"type": "string"},
                "observingMethods": {
                    "type": "array",
                    "items": {"type": ["integer", "string"]},
                },
                "verticalRange": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "min": {"type": ["number", "string"]},
                        "max": {"type": ["number", "string"]},
                    },
                },
            },
            "allOf": [
                {"not": {"required": ["serialNumber"]}},
                {"not": {"required": ["serialNumbers"]}},
            ],
        },
    },
}
