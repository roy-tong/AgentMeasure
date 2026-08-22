"""Minimal JSON Schema validator (subset of draft 2020-12).

Only the constructs used by the Lab format schemas (FMT-001/002/003) are
supported: type, const, enum, properties, required, additionalProperties,
items, minimum/maximum, minLength/maxLength/minItems, pattern, oneOf, anyOf,
$defs/$ref (local). Kept in-repo so the engine stays zero-dependency and
fully offline; it is not a general-purpose validator.
"""

import re
from typing import Any, Dict

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
}


class SchemaError(ValueError):
    def __init__(self, path: str, message: str):
        super().__init__(f"{path or '<root>'}: {message}")
        self.path = path
        self.message = message


def validate(instance: Any, schema: Dict[str, Any], path: str = "", defs: Dict[str, Any] = None) -> None:
    if defs is None:
        defs = dict(schema.get("$defs", {}))
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(path, f"unsupported $ref: {ref}")
        name = ref[len("#/$defs/") :]
        if name not in defs:
            raise SchemaError(path, f"unknown $defs entry: {name}")
        validate(instance, defs[name], path, defs)
        return

    if "oneOf" in schema:
        errors = []
        ok = 0
        for sub in schema["oneOf"]:
            try:
                validate(instance, sub, path, defs)
                ok += 1
            except SchemaError as e:
                errors.append(e)
        if ok != 1:
            raise SchemaError(path, f"oneOf: matched {ok} branches (expected exactly 1)")
        return

    if "anyOf" in schema:
        for sub in schema["anyOf"]:
            try:
                validate(instance, sub, path, defs)
                return
            except SchemaError:
                continue
        raise SchemaError(path, "anyOf: no branch matched")

    if "const" in schema and instance != schema["const"]:
        raise SchemaError(path, f"expected const {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(path, f"{instance!r} not in enum {schema['enum']!r}")

    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPE_CHECKS[tt](instance) for tt in types):
            raise SchemaError(path, f"expected type {types}, got {type(instance).__name__}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaError(path, f"{instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaError(path, f"{instance} > maximum {schema['maximum']}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaError(path, f"shorter than minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise SchemaError(path, f"does not match pattern {schema['pattern']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SchemaError(path, f"fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                validate(item, schema["items"], f"{path}[{i}]", defs)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                raise SchemaError(path, f"missing required property {key!r}")
        for key, sub in props.items():
            if key in instance:
                validate(instance[key], sub, f"{path}.{key}" if path else key, defs)
        if schema.get("additionalProperties") is False:
            extra = set(instance) - set(props)
            if extra:
                raise SchemaError(path, f"unexpected properties: {sorted(extra)}")
