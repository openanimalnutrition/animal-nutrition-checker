"""Contract tests of the GUI and MCP server (plan, "Verification"), run in the test image:

- the GUI's JSON and the MCP's check_diet are byte-identical for the same inputs, and both
  carry the caveats (the test fails if they are removed);
- no excess above a non-authoritative maximum;
- oversize and malformed requests are rejected, and so are unknown fields, other hosts and
  other origins;
- an MCP client lists the tools and calls each one;
- the pages escape what they echo and send the security headers;
- the server's log holds no request content and no client address (the About page says so).

Run (in the test image): python -I -B tests/contract/test_server.py
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import unittest

import httpx2 as httpx
from mcp import Client

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
from oan import caveats, energy, result  # noqa: E402
import mcp_tools  # noqa: E402

PORT = 8791
BASE = "http://127.0.0.1:%d" % PORT
# The uvicorn flags of the Dockerfile's CMD that the About page and the headers rely on.
UVICORN_FLAGS = ["--no-access-log", "--no-server-header"]
D = result.Data(os.path.join(ROOT, "data"))
DOG = energy.dog_type_labels(D.tables)[3]
REQUEST = {"requirement": "nrc-dog-adult",
           "animal": {"body_weight_kg": 20, "adult_dog_type": DOG,
                      "caloric_restriction_percent": 25},
           "entries": {"calcium": {"low": 1.3333333, "high": 3.5}, "protein": {"low": 30},
                       "choline": {"low": 600}, "water": {"high": 2000},
                       "vitamin-e": {"low": 100}, "carbohydrate": {"low": 10},
                       "linoleic-acid": {"low": 3}, "alpha-linolenic-acid": {"low": 0.01},
                       "energy": {"low": 900}},
           "subject": "diet"}
FEDIAF = {"requirement": "fediaf-dog-adult-mer95", "animal": {"body_weight_kg": 20},
          "entries": {"copper": {"low": 50}, "zinc": {"low": 500}, "selenium": {"low": 500},
                      "calcium": {"low": 9}}, "subject": "diet"}


def form_of(request):
    items = [("requirement", request["requirement"]), ("subject", request["subject"])]
    items += [("animal." + k, str(v)) for k, v in request["animal"].items()]
    for nid, sides in request["entries"].items():
        items += [("%s.%s" % (side, nid), str(v)) for side, v in sides.items()]
    return items


def start_server(port, **popen):
    env = dict(os.environ, OAN_ORIGINS="http://127.0.0.1:%d" % port)
    proc = subprocess.Popen(
        [sys.executable, "-I", "-B", "-m", "uvicorn", "--app-dir",
         os.path.join(ROOT, "server"), "app:app", "--host", "127.0.0.1", "--port",
         str(port)] + UVICORN_FLAGS, env=env, **popen)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    return proc


def mcp_json_part(text):
    marker = mcp_tools.JSON_MARKER + "\n"
    return text[text.index(marker) + len(marker):]


def sse_json(text):
    """A JSON-RPC message from a Streamable HTTP response, plain JSON or an event stream."""
    if text.startswith("event:") or "\ndata:" in text or text.startswith("data:"):
        text = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")][-1]
    return json.loads(text)

async def mcp_calls(calls, base=BASE):
    out = {}
    async with Client(base + "/mcp") as client:
        out["tools"] = await client.list_tools()
        out["instructions"] = client.instructions
        for key, name, args in calls:
            out[key] = await client.call_tool(name, args)
    return out


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = start_server(PORT)
        cls.http = httpx.Client(base_url=BASE, timeout=10)
        cls.mcp = asyncio.run(mcp_calls([
            ("list_requirements", "list_requirements", {}),
            ("describe_inputs", "describe_inputs", {}),
            ("get_limits", "get_limits", {"requirement": "nrc-kitten",
                                          "animal": {"body_weight_kg": 1,
                                                     "mature_weight_kg": 4}}),
            ("check_diet", "check_diet", REQUEST), ("check_diet#2", "check_diet", FEDIAF),
            ("get_notes", "get_notes", {"ids": ["n231", "n005"]}),
            ("get_limits#filter", "get_limits", {"requirement": "nrc-kitten",
                                                 "animal": {"body_weight_kg": 1,
                                                            "mature_weight_kg": 4},
                                                 "nutrients": ["calcium"]}),
            ("missing", "check_diet", {"requirement": "nrc-dog-adult",
                                       "entries": {"calcium-mbw": 1}}),
        ]))

    @classmethod
    def tearDownClass(cls):
        cls.http.close()
        cls.proc.terminate()
        cls.proc.wait(10)

    # The MCP client lists the tools and calls each one.

    def test_tools(self):
        names = sorted(t.name for t in self.mcp["tools"].tools)
        self.assertEqual(names, ["check_diet", "describe_inputs", "get_limits", "get_notes",
                                 "list_requirements"])
        for t in self.mcp["tools"].tools:
            for c in caveats.caveats(D.version):
                self.assertIn(c["text"], t.description, t.name)
        for name in ("list_requirements", "describe_inputs", "get_limits", "check_diet",
                     "get_notes"):
            r = self.mcp[name]
            self.assertFalse(r.is_error, name)
            text = r.content[0].text
            self.assertTrue(text.startswith("CAVEATS (read before using this result):"), name)
            self.assertEqual(json.loads(mcp_json_part(text)), r.structured_content, name)
            self.assertEqual([c["id"] for c in r.structured_content["caveats"]],
                             [cid for cid, _ in caveats.CAVEATS])

    # What each tool does and the call order come before the caveats; read-only annotations
    # (live-call test of release 0.7.0, steward, 25 Oct 2026).

    def test_descriptions_annotations_and_instructions(self):
        first_caveat = mcp_tools.caveat_lines(D.version)[0]
        for t in self.mcp["tools"].tools:
            self.assertEqual(t.title, mcp_tools.TITLES[t.name])
            a = t.annotations
            self.assertEqual((a.title, a.read_only_hint, a.destructive_hint, a.idempotent_hint,
                              a.open_world_hint), (t.title, True, False, True, False), t.name)
            self.assertLess(t.description.index(mcp_tools.CALL_ORDER),
                            t.description.index(first_caveat), t.name)
        check = next(t for t in self.mcp["tools"].tools if t.name == "check_diet")
        self.assertTrue(check.description.startswith(caveats.UNITS_TEXT))
        for text in (caveats.WET_DRY_TEXT, caveats.PASTED_TEXT, caveats.UNDER_REPORTED_TEXT,
                     caveats.GUARANTEED_MINIMUM_TEXT):
            self.assertIn(text, check.description)
        self.assertTrue(check.input_schema["properties"]["entries"]["description"].startswith(
            caveats.UNITS_TEXT))
        instructions = self.mcp["instructions"]
        self.assertTrue(instructions.startswith(mcp_tools.CALL_ORDER + "\n" +
                                                caveats.PASTED_TEXT))
        for c in caveats.caveats(D.version):
            self.assertIn(c["text"], instructions)

    def test_get_limits_filter(self):
        r = self.mcp["get_limits#filter"]
        self.assertFalse(r.is_error)
        self.assertEqual([n["id"] for n in r.structured_content["nutrients"]],
                         ["calcium", "calcium-mbw"])

    def test_older_protocol_clients(self):
        headers = {"content-type": "application/json",
                   "accept": "application/json, text/event-stream"}
        for version in ("2024-11-05", "2025-03-26"):
            r = self.http.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": version, "capabilities": {},
                    "clientInfo": {"name": "older-client", "version": "1"}}})
            self.assertEqual(r.status_code, 200, version)
            self.assertEqual(sse_json(r.text)["result"]["protocolVersion"], version)
            r = self.http.post("/mcp", headers=dict(headers, **{"mcp-protocol-version": version}),
                               json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            self.assertEqual(len(sse_json(r.text)["result"]["tools"]), 5, version)

    def test_oauth_discovery_is_a_plain_404(self):
        # No authorization: clients that probe for it get a clean 404, not a page or redirect.
        for path in ("/.well-known/oauth-protected-resource",
                     "/.well-known/oauth-protected-resource/mcp",
                     "/.well-known/oauth-authorization-server",
                     "/.well-known/openid-configuration"):
            r = self.http.get(path)
            self.assertEqual((r.status_code, r.text), (404, "Not Found"), path)
            self.assertNotIn("location", r.headers)

    def test_missing_facts_are_a_tool_error(self):
        r = self.mcp["missing"]
        self.assertTrue(r.is_error)
        self.assertIn("animal.body_weight_kg", r.content[0].text)
        self.assertTrue(r.content[0].text.endswith(". " + caveats.MISSING_INPUTS_ASK))
        self.assertFalse(self.mcp["check_diet"].is_error)

    # The GUI's JSON and the MCP's check_diet: the same bytes.

    def test_gui_json_equals_mcp(self):
        for key, request in (("check_diet", REQUEST), ("check_diet#2", FEDIAF)):
            gui = self.http.post("/check.json", data=dict(form_of(request)))
            self.assertEqual(gui.status_code, 200)
            mcp_text = self.mcp[key].content[0].text
            self.assertEqual(gui.content.decode("utf-8"), mcp_json_part(mcp_text), key)
            self.assertEqual(json.loads(gui.content)["caveats"],
                             self.mcp[key].structured_content["caveats"])

    def test_gui_page_has_the_caveats_first(self):
        page = self.http.post("/check", data=dict(form_of(REQUEST))).text
        self.assertIn("<details><summary>Notes (", page)
        self.assertIn("<h3>Animal and energy</h3>", page)
        self.assertIn("Current body weight (kg): 20", page)
        self.assertIn("Energy used, kcal/day:", page)
        self.assertIn("NRC RA Dog Maintenance sets no calcium maximum", page)
        first = page.index("Caveats")
        for c in caveats.caveats(D.version):
            self.assertIn(c["text"].replace("'", "&#x27;"), page)
        self.assertLess(first, page.index("Input report"))

    # No excess above a non-authoritative maximum.

    def test_no_excess_above_non_authoritative(self):
        seen = 0
        for key in ("check_diet", "check_diet#2"):
            for n in self.mcp[key].structured_content["nutrients"]:
                for side in ("entry", "low", "high"):
                    entry = n[side]
                    if entry and entry["comparison_to_max"] in (
                            "above_non_authoritative_max", "above_range_high"):
                        seen += 1
                        self.assertIsNone(entry["verdict"], n["id"])
                    if entry and entry["verdict"] == "excess":
                        self.assertEqual(n["max_provenance"], "authoritative", n["id"])
        self.assertGreaterEqual(seen, 4)

    # Rejections.

    def test_oversize(self):
        big = [("paste", "x" * 40000), ("requirement", "nrc-dog-adult")]
        self.assertEqual(self.http.post("/parse", data=dict(big)).status_code, 413)
        r = self.http.post("/mcp", content=b"{" + b" " * 40000 + b"}",
                           headers={"content-type": "application/json",
                                    "accept": "application/json, text/event-stream"})
        self.assertEqual(r.status_code, 413)

    def test_malformed(self):
        r = self.http.post("/mcp", content=b"{not json",
                           headers={"content-type": "application/json",
                                    "accept": "application/json, text/event-stream"})
        self.assertGreaterEqual(r.status_code, 400)
        r = self.http.post("/check", data={"requirement": "nrc-dog-adult", "colour": "red"})
        self.assertEqual(r.status_code, 400)
        r = self.http.post("/check.json", data={"low.calcium": "1" * 100})
        self.assertEqual(r.status_code, 400)

    def test_unknown_tool_arguments(self):
        r = asyncio.run(mcp_calls([("x", "check_diet", {
            "requirement": "nrc-dog-adult", "entries": {"calcium": 1}, "colour": "red"})]))["x"]
        self.assertTrue(r.is_error)

    def test_host_and_origin(self):
        r = self.http.get("/", headers={"host": "evil.example"})
        self.assertEqual(r.status_code, 400)
        r = self.http.post("/check", data=dict(form_of(REQUEST)),
                           headers={"origin": "http://evil.example"})
        self.assertEqual(r.status_code, 403)
        r = self.http.post("/mcp", content=b"{}", headers={
            "origin": "http://evil.example", "content-type": "application/json",
            "accept": "application/json, text/event-stream"})
        self.assertEqual(r.status_code, 403)

    # Output safety.

    def test_escaping_and_headers(self):
        attack = "<script>alert(1)</script>"
        r = self.http.post("/check", data={"requirement": "nrc-dog-adult",
                                           "low.calcium": attack,
                                           "animal.adult_dog_type": attack})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(attack, r.text)
        self.assertIn("&lt;script&gt;", r.text)
        csp = r.headers["content-security-policy"]
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn("script-src", csp)
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        # Under no-referrer, browsers send "Origin: null" with a form and every check fails.
        self.assertEqual(r.headers["referrer-policy"], "same-origin")
        self.assertEqual(r.headers["strict-transport-security"], "max-age=31536000")
        self.assertNotIn("server", r.headers)
        r = self.http.post("/check", data=dict(form_of(REQUEST)), headers={"origin": "null"})
        self.assertEqual(r.status_code, 403)
        r = self.http.post("/check", data=dict(form_of(REQUEST)), headers={"origin": BASE})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("access-control-allow-origin", r.headers)

    def test_about(self):
        self.assertIn('<a href="/about">', self.http.get("/").text)
        page = self.http.get("/about").text
        self.assertLess(page.index("Caveats"), page.index("<h3>Privacy</h3>"))
        for text in ("<h3>Hosting</h3>", "<h3>Contact</h3>", "mailto:"):
            self.assertIn(text, page)

    def test_steps(self):
        self.assertIn("Choose a requirement", self.http.get("/").text)
        page = self.http.get("/", params={"requirement": "nrc-puppy-4-14-wk"}).text
        # The large-breed puppy calcium row uses the current body weight (steward, 24 Oct 2026).
        self.assertIn("animal.mature_weight_kg", page)
        self.assertNotIn("animal.puppy_body_weight_kg", page)
        self.assertNotIn("animal.adult_cat_type", page)
        r = self.http.post("/parse", data={"requirement": "nrc-dog-adult",
                                           "paste": "Calcium, Ca, 1.2, 3\nprotein,30,\n"
                                                    "no such thing,1,2"})
        self.assertIn("2 rows parsed", r.text)
        self.assertIn("Not understood (1)", r.text)
        self.assertIn('name="low.calcium" value="1.2"', r.text)



class Log(unittest.TestCase):
    """What the server writes while answering requests that carry a marker everywhere."""

    def test_no_request_content_or_address_in_the_log(self):
        port, mark = PORT + 1, "ZQXMARK"
        base = "http://127.0.0.1:%d" % port
        proc = start_server(port, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            with httpx.Client(base_url=base, timeout=10,
                              headers={"user-agent": mark}) as http:
                http.get("/%s?q=%s" % (mark, mark))
                http.get("/", params={"requirement": mark})
                http.get("/", headers={"host": mark + ".example"})
                http.post("/check", data=dict(form_of(REQUEST), **{"low.calcium": mark}))
                http.post("/check", data={"requirement": "nrc-dog-adult", mark: "1"})
                http.post("/check.json", data=dict(form_of(REQUEST)))
                http.post("/parse", data={"requirement": "nrc-dog-adult",
                                          "paste": "Calcium %s 1" % mark})
                http.post("/check", data={"x": "1"}, headers={"origin": "http://" + mark})
                http.post("/mcp", content=("{" + mark).encode(), headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream"})
            asyncio.run(mcp_calls([
                ("ok", "check_diet", REQUEST),
                ("bad", "check_diet", {"requirement": mark, "entries": {mark: {"low": 1}}}),
                ("tool", "get_limits", {"requirement": "nrc-kitten", "nutrients": [mark]}),
            ], base))
            with socket.create_connection(("127.0.0.1", port)) as raw:
                raw.sendall(("GARBAGE %s\r\n\r\n" % mark).encode())
                raw.recv(100)
        finally:
            proc.terminate()
            out, _ = proc.communicate(timeout=10)
        self.assertIn("Application startup complete", out)
        self.assertNotIn(mark, out)
        self.assertNotRegex(out, r"127\.0\.0\.1:\d+ - ")


if __name__ == "__main__":
    unittest.main(verbosity=1)
