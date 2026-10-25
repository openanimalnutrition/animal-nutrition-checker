"""The MCP tools: list_requirements, describe_inputs, get_limits, check_diet and get_notes (MCP Python
SDK 2.x, server/requirements.lock).

Each tool returns the whole Result (oan.result) twice: as structured content, and as a text
block whose first lines are the caveats, followed by the Result's JSON in the one byte form
the GUI's "download JSON" gives (oan.result.to_json). The caveats are also in each tool's
description and in the server's instructions, after what the tool does and the call order.
"""

import json
import os

import mcp.types as types
from mcp.server.lowlevel import Server

from oan import caveats, inputs, result

JSON_MARKER = "RESULT (JSON, schema oan-check-result/2):"
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
            props[name] = {"type": "number", "description": "range %s to %s%s%s" % (
                rule[0], rule[1], " (or 0 for none)" if kind == "restriction" else "",
                ". " + caveats.FACT_TEXTS[name][1] if name in caveats.FACT_TEXTS else "")}
        elif kind == "life-stage":
            props[name] = {"type": "string", "enum": list(rule)}
        else:
            props[name] = {"type": "string", "enum": list(rule(data.tables))}
    return {"type": "object", "properties": props, "additionalProperties": False}


# The call order, in every tool's description and in the server's instructions (steward, 25
# Oct 2026: purpose and call order before the caveats; one model in the live-call test of
# release 0.7.0 answered from its own knowledge without calling a tool, another skipped
# describe_inputs). The steward approved this wording, the titles and get_limits' sentence on
# 25 Oct 2026.
CALL_ORDER = ("Call order: list_requirements to choose a requirement; describe_inputs for the "
              "animal facts and the nutrient ids, units and ranges; then check_diet. get_notes "
              "gives the texts of the note ids a result names; get_limits gives a requirement's "
              "limits without a diet.")
TITLES = {"list_requirements": "List requirements", "describe_inputs": "Describe inputs",
          "get_limits": "Get limits", "check_diet": "Check diet", "get_notes": "Get notes"}


def instructions(data_version):
    return "\n".join([CALL_ORDER, caveats.PASTED_TEXT, ""] + caveat_lines(data_version))


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
    tail = "\n\n" + CALL_ORDER + "\n\n" + "\n".join(caveat_lines(data.version))
    specs = [
        ("list_requirements", "The 21 requirements (standard, edition, species, life stage) "
         "and the animal facts each reads.", {}, []),
        ("describe_inputs", "The animal facts and the nutrient entries the checker takes, with "
         "their units and allowed ranges.", {}, []),
        ("get_limits", "Every nutrient's minimum, maximum, range high and the kind of maximum, "
         "with conditions and note ids, for a requirement and animal. With nutrients (ids from "
         "describe_inputs), only those rows, each with its MBW row.",
         {"requirement": requirement, "animal": animal_schema(data),
          "nutrients": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                        "description": "optional: only these nutrient ids (describe_inputs), "
                                       "each with its MBW row"}},
         ["requirement"]),
        ("check_diet", caveats.UNITS_TEXT + " Compares nutrient values of a diet or a "
         "requirement range with a requirement, every entry per Mcal, on metabolic body weight "
         "(MBW) rows too (their limits are converted to per Mcal): band, proposed verdict "
         "(deficient, excess or none), conditions and notes per nutrient. " +
         caveats.WET_DRY_TEXT + " " + caveats.PASTED_TEXT + " " + caveats.ENTRIES_TEXT +
         " The energy entry is " + caveats.ENERGY_ENTRY_TEXT,
         {"requirement": requirement, "animal": animal_schema(data),
          "entries": {"type": "object", "additionalProperties": entry,
                      "description": caveats.UNITS_TEXT + " {nutrient id: number, or {low, "
                                     "high}} (describe_inputs)"},
          "subject": {"type": "string", "enum": list(result.SUBJECTS)}},
         ["requirement", "entries"]),
        ("get_notes", "The texts of the checker's notes, by the note ids a result gives, with "
         "the template tab and cell each comes from or was adapted from.",
         {"ids": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                  "maxItems": result.MAX_NOTE_IDS}}, ["ids"]),
    ]
    # Read-only, idempotent, closed-world tools (steward's plan for hosting, 25 Oct 2026).
    return [types.Tool(name=name, title=TITLES[name], description=text + tail,
                       input_schema={"type": "object", "properties": props,
                                     "required": required, "additionalProperties": False},
                       output_schema=output_schema,
                       annotations=types.ToolAnnotations(
                           title=TITLES[name], read_only_hint=True, destructive_hint=False,
                           idempotent_hint=True, open_world_hint=False))
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
    if name == "get_notes":
        return result.get_notes(data, arguments)
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
    """The MCP server (SDK 2.x low-level Server): the tools above. The core checks the
    arguments (oan.inputs, oan.result): what it cannot use is a tool error or an input-report
    line saying why. The SDK does not check them against the input schemas, which clients
    read (get_tool_input_schema serves only its Mcp-Param header validation; found in the
    live-call test of release 0.7.0)."""
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
                  instructions=instructions(data.version),
                  get_tool_input_schema=schemas.get, on_list_tools=on_list_tools,
                  on_call_tool=on_call_tool)
