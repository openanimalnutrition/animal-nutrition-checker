"""Contract tests of the GUI and MCP server (plan, "Verification"), run in the test image:

- the GUI's JSON and the MCP's check_diet are byte-identical for the same inputs, and both
  carry the caveats (the test fails if they are removed);
- no excess above a non-authoritative maximum;
- oversize and malformed requests are rejected, and so are unknown fields, other hosts and
  other origins;
- an MCP client lists the tools and calls each one;
- the pages escape what they echo and send the security headers.

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


def mcp_json_part(text):
    marker = mcp_tools.JSON_MARKER + "\n"
    return text[text.index(marker) + len(marker):]


async def mcp_calls(calls):
    out = {}
    async with Client(BASE + "/mcp") as client:
        out["tools"] = await client.list_tools()
        for key, name, args in calls:
            out[key] = await client.call_tool(name, args)
    return out


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, OAN_ORIGINS="http://127.0.0.1:%d" % PORT)
        cls.proc = subprocess.Popen(
            [sys.executable, "-I", "-B", "-m", "uvicorn", "--app-dir",
             os.path.join(ROOT, "server"), "app:app", "--host", "127.0.0.1", "--port",
             str(PORT), "--no-access-log"], env=env)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", PORT), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.http = httpx.Client(base_url=BASE, timeout=10)
        cls.mcp = asyncio.run(mcp_calls([
            ("list_requirements", "list_requirements", {}),
            ("describe_inputs", "describe_inputs", {}),
            ("get_limits", "get_limits", {"requirement": "nrc-kitten",
                                          "animal": {"body_weight_kg": 1,
                                                     "mature_weight_kg": 4}}),
            ("check_diet", "check_diet", REQUEST), ("check_diet#2", "check_diet", FEDIAF),
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
        self.assertEqual(names, ["check_diet", "describe_inputs", "get_limits",
                                 "list_requirements"])
        for t in self.mcp["tools"].tools:
            for c in caveats.caveats(D.version):
                self.assertIn(c["text"], t.description, t.name)
        for name in ("list_requirements", "describe_inputs", "get_limits", "check_diet"):
            r = self.mcp[name]
            self.assertFalse(r.is_error, name)
            text = r.content[0].text
            self.assertTrue(text.startswith("CAVEATS (read before using this result):"), name)
            self.assertEqual(json.loads(mcp_json_part(text)), r.structured_content, name)
            self.assertEqual([c["id"] for c in r.structured_content["caveats"]],
                             [cid for cid, _ in caveats.CAVEATS])

    def test_missing_facts_are_a_tool_error(self):
        r = self.mcp["missing"]
        self.assertTrue(r.is_error)
        self.assertIn("animal.body_weight_kg", r.content[0].text)
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
        first = page.index("Caveats")
        for c in caveats.caveats(D.version):
            self.assertIn(c["text"].replace("'", "&#x27;"), page)
        self.assertLess(first, page.index("Input report"))

    # No excess above a non-authoritative maximum.

    def test_no_excess_above_non_authoritative(self):
        seen = 0
        for key in ("check_diet", "check_diet#2"):
            for n in self.mcp[key].structured_content["nutrients"]:
                for side in ("low", "high"):
                    entry = n[side]
                    if entry and entry["comparison_to_max"] == "above_non_authoritative_max":
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
        self.assertNotIn("access-control-allow-origin", r.headers)

    def test_steps(self):
        self.assertIn("Choose a requirement", self.http.get("/").text)
        page = self.http.get("/", params={"requirement": "nrc-puppy-4-14-wk"}).text
        self.assertIn("animal.puppy_body_weight_kg", page)
        self.assertNotIn("animal.adult_cat_type", page)
        r = self.http.post("/parse", data={"requirement": "nrc-dog-adult",
                                           "paste": "Calcium, Ca, 1.2, 3\nprotein,30,\n"
                                                    "no such thing,1,2"})
        self.assertIn("2 rows parsed", r.text)
        self.assertIn("Not understood (1)", r.text)
        self.assertIn('name="low.calcium" value="1.2"', r.text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
