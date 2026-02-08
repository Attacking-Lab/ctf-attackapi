import re
import tempfile
from pathlib import Path

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.server.docs import docs_json
from ad_ctf_apis.server.server import AdCtfServer
from tests.utils import BaseTestCase


class MyAppTestCase(AioHTTPTestCase, BaseTestCase):

    def setUp(self) -> None:
        from ad_ctf_apis.async_api.api import _api_response_cache
        _api_response_cache._cache.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)
        self.ctx = self.patch_request(self._res / "saarctf2025.json")
        self.mock = self.ctx.__enter__()
        super().setUp()

    def tearDown(self) -> None:
        if self.ctx:
            self.ctx.__exit__(None, None, None)
        self.tempdir.cleanup()
        super().tearDown()

    async def get_application(self) -> web.Application:
        return AdCtfServer(self.api)

    def test_version(self) -> None:
        api_version = docs_json()["info"]["version"]
        text = (Path(__file__).parent.parent / "pyproject.toml").read_text()
        package_version = re.findall(r'version = "(.*?)"', text)[0]
        self.assertEqual(api_version, package_version)

    async def test_docs(self) -> None:
        async with self.client.request("GET", "/") as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
            self.assertIn("AD CTF API", text)
        async with self.client.request("GET", "/api.yaml") as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
            self.assertIn("AD CTF API", text)

    async def test_services(self) -> None:
        async with self.client.request("GET", "/api/v1/services") as resp:
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertIn("Licenser", data["services"])

    async def test_teams(self) -> None:
        async with self.client.request("GET", "/api/v1/teams") as resp:
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertEqual(131, len(data["teams"]))
            self.assertIn("10.32.1.2", [team["ip"] for team in data["teams"]])

    nop_ref = {
        "227": "NecessaryHatefulMotel8424",
        "228": "SecondhandNaiveArtificer424",
        "229": "SleepyNonchalantResale945",
        "230": "WoozyUnderwire4918",
        "231": "AbundantOutgoingGelding8283",
        "232": "JealousOutgoingWaistband7947",
        "233": "UttermostIntelligentSpot6463",
        "234": "BrownUgliestLemur377",
        "235": "JealousJudiciousPolice9128",
        "236": "GamyVersedSpider3593",
        "237": "StingyWideCarpet9739"
    }

    async def test_attack_info(self) -> None:
        ref = [self.nop_ref[k] for k in sorted(self.nop_ref.keys())]
        for team in ("1", "nop", "10.32.1.2"):
            async with self.client.request("GET", f"/api/v1/attack_info/licenser/{team}") as resp:
                self.assertEqual(resp.status, 200)
                data = await resp.json()
                self.assertEqual(ref, data["attack_info"])

    async def test_attack_info_raw(self) -> None:
        for team in ("1", "nop", "10.32.1.2"):
            async with self.client.request("GET", f"/api/v1/attack_info_raw/licenser/{team}") as resp:
                self.assertEqual(resp.status, 200)
                data = await resp.json()
                self.assertEqual(self.nop_ref, data["attack_info"])

    async def test_raw(self) -> None:
        async with self.client.request("GET", "/api/v1/raw") as resp:
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertIn("flag_regex", data)
