"""A small JSON Schema checker, standard library only, for the keywords that
docs/result.schema.json uses: type, required, properties, additionalProperties, items, enum,
const, minItems, minLength, pattern, minimum, oneOf and local $ref. It is not a general
validator; a test fails if the schema uses any other keyword."""

import re

KEYWORDS = {"$schema", "$id", "title", "description", "$defs", "type", "required",
            "properties", "additionalProperties", "items", "enum", "const", "minItems",
            "minLength", "pattern", "minimum", "oneOf", "$ref"}
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "null": type(None)}


def keywords(schema, found=None):
    """Every keyword the schema uses (to check that this checker knows them all)."""
    found = set() if found is None else found
    if isinstance(schema, dict):
        for k, v in schema.items():
            found.add(k)
            if k in ("properties", "$defs"):
                for sub in v.values():
                    keywords(sub, found)
            elif k in ("items", "additionalProperties") and isinstance(v, dict):
                keywords(v, found)
            elif k == "oneOf":
                for sub in v:
                    keywords(sub, found)
    return found


def _type_ok(value, name):
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, TYPES[name])


def errors(value, schema, root=None, path="$"):
    """The list of problems of a value against a schema (empty when it conforms)."""
    root = schema if root is None else root
    out = []
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return errors(value, root["$defs"][name], root, path)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, n) for n in names):
            return ["%s: %r is not of type %s" % (path, value, names)]
    if "const" in schema and value != schema["const"]:
        out.append("%s: %r is not %r" % (path, value, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        out.append("%s: %r is not one of %r" % (path, value, schema["enum"]))
    if "oneOf" in schema:
        n = sum(1 for sub in schema["oneOf"] if not errors(value, sub, root, path))
        if n != 1:
            out.append("%s: matches %d of oneOf" % (path, n))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append("%s: too short" % path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append("%s: %r does not match %s" % (path, value, schema["pattern"]))
    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        out.append("%s: below %r" % (path, schema["minimum"]))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append("%s: fewer than %d items" % (path, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                out += errors(item, schema["items"], root, "%s[%d]" % (path, i))
    if isinstance(value, dict):
        for k in schema.get("required", ()):
            if k not in value:
                out.append("%s: %s is required" % (path, k))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                out += errors(v, props[k], root, "%s.%s" % (path, k))
            elif extra is False:
                out.append("%s: unknown field %s" % (path, k))
            elif isinstance(extra, dict):
                out += errors(v, extra, root, "%s.%s" % (path, k))
    return out
