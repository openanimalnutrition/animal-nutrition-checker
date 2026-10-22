"""The MCP tools: list_requirements, describe_inputs, get_limits and check_diet (MCP Python
SDK 2.x, server/requirements.lock).

Each tool returns the whole Result (oan.result) twice: as structured content, and as a text
block whose first lines are the caveats, followed by the Result's JSON in the one byte form
the GUI's "download JSON" gives (oan.result.to_json). The caveats are also in each tool's
description and in the server's instructions.
"""

import json
import os

import mcp.types as types
from mcp.server.lowlevel import Server

from oan import caveats, inputs, result

JSON_MARKER = "RESULT (JSON, schema oan-check-result/1):"
MAX_DEPTH = 4
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "docs", "result.schema.json")


def caveat_lines(data_version):
    return ["CAVEATS (read before using this result):"] + [
        "%d. %s" % (i, c["text"]) for i, c in enumerate(caveats.caveats(data_version), 1)]


def text_block(res):
    return "\n".join(caveat_lines(res["data_version"]) + ["", JSON_MARKER,
                                                           result.to_json(res)])


def depth(value):
    if isinstance(value, dict):
        return 1 + max((depth(v) for v in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((depth(v) for v in value), default=0)
    return 0


def animal_schema(data):
    props = {}
    for name, (kind, rule) in inputs.FACTS.items():
        if name == "requirement":
            continue
        if kind in ("number", "whole", "restriction"):
            props[name] = {"type": "number", "description": "range %s to %s%s" % (
                rule[0], rule[1], " (or 0 for none)" if kind == "restriction" else "")}
        elif kind == "life-stage":
            props[name] = {"type": "string", "enum": list(rule)}
        else:
            props[name] = {"type": "string", "enum": list(rule(data.tables))}
    return {"type": "object", "properties": props, "additionalProperties": False}


def tools(data):
    requirement = {"type": "string",
                   "description": "a requirement's id or name (list_requirements)"}
    entry = {"oneOf": [
        {"type": "number"},
        {"type": "object", "properties": {"low": {"type": "number"},
                                          "high": {"type": "number"}},
         "additionalProperties": False, "minProperties": 1}]}
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        output_schema = json.load(f)
    head = "\n".join(caveat_lines(data.version)) + "\n\n"
    specs = [
        ("list_requirements", "The 21 requirements (standard, edition, species, life stage) "
         "and the animal facts each reads.", {}, []),
        ("describe_inputs", "The animal facts and the nutrient entries the checker takes, with "
         "their units and allowed ranges.", {}, []),
        ("get_limits", "Every nutrient's minimum, maximum, range high and the kind of maximum, "
         "with conditions and note ids, for a requirement and animal.",
         {"requirement": requirement, "animal": animal_schema(data)}, ["requirement"]),
        ("check_diet", "Compares nutrient values (per Mcal, or per kg of metabolic body weight "
         "on MBW rows) of a diet or a requirement range with a requirement: band, proposed "
         "verdict (deficient, excess or none), conditions and notes per nutrient.",
         {"requirement": requirement, "animal": animal_schema(data),
          "entries": {"type": "object", "additionalProperties": entry,
                      "description": "{nutrient id: number, or {low, high}} (describe_inputs)"},
          "subject": {"type": "string", "enum": list(result.SUBJECTS)}},
         ["requirement", "entries"]),
    ]
    return [types.Tool(name=name, description=head + text,
                       input_schema={"type": "object", "properties": props,
                                     "required": required, "additionalProperties": False},
                       output_schema=output_schema)
            for name, text, props, required in specs]


def run_tool(data, name, arguments):
    """The Result of one tool call, or an exception for a tool error."""
    arguments = arguments or {}
    if depth(arguments) > MAX_DEPTH:
        raise ValueError("the arguments are nested too deeply")
    if name == "list_requirements":
        return result.list_requirements(data)
    if name == "describe_inputs":
        return result.describe_inputs(data)
    if name == "get_limits":
        return result.get_limits(data, arguments)
    if name == "check_diet":
        res = result.check(data, arguments)
        missing = [i for i in res["input_report"] if i["status"] == "missing"]
        if missing:
            raise ValueError("Missing inputs, needed for the nutrients entered: " + "; ".join(
                "%s (%s)" % (i["input"], i["text"]) for i in missing))
        return res
    raise ValueError("unknown tool %r" % name)


def _error(text):
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)],
                                is_error=True)


def build(data):
    """The MCP server (SDK 2.x low-level Server): the tools above, arguments checked against
    each tool's input schema, then by the core."""
    tool_list = tools(data)
    schemas = {t.name: t.input_schema for t in tool_list}

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(tools=tool_list)

    async def on_call_tool(ctx, params):
        try:
            res = run_tool(data, params.name, params.arguments)
        except (ValueError, result.RequestError) as err:
            return _error(str(err))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text_block(res))],
            structured_content=res)

    return Server("open-animal-nutrition", version=result.CODE_RELEASE,
                  instructions="\n".join(caveat_lines(data.version)),
                  get_tool_input_schema=schemas.get, on_list_tools=on_list_tools,
                  on_call_tool=on_call_tool)
