import json
import time
import unittest

from attackapi.async_api.decoders import Decoder
from attackapi.models import Team
from .utils import BaseTestCase


class DecoderTestCase(BaseTestCase):
    def test_saarctf(self) -> None:
        info = Decoder().parse((self._res / "saarctf2025.json").read_bytes())
        self.assertEqual(131, len(info.teams))
        self.assertEqual(131 * 3, len(info.team_lookup))
        self.assertEqual(Team(1, "10.32.1.2", "NOP"), info.team_lookup["1"])
        self.assertEqual(Team(1, "10.32.1.2", "NOP"), info.team_lookup["10.32.1.2"])
        self.assertEqual(Team(1, "10.32.1.2", "NOP"), info.team_lookup["nop"])
        self.assertEqual(Team(114, "10.32.114.2", "脆骨"), info.team_lookup["114"])
        self.assertSetEqual({"Licenser", "RCEaaS", "Routerploit", "SSSG", "no-service"}, info.services)
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
        self.assertEqual(nop_ref, info.flag_id_raw("Licenser", "nop"))
        self.assertEqual(nop_ref, info.flag_id_raw("Licenser", "1"))
        self.assertEqual(nop_ref, info.flag_id_raw("Licenser", "10.32.1.2"))

    def test_enowars(self) -> None:
        info = Decoder().parse((self._res / "enowars9.json").read_bytes())
        self.assertEqual(112, len(info.teams))
        self.assertEqual(Team(15, "10.1.15.1", "10.1.15.1"), info.team_lookup["15"])
        self.assertEqual(Team(15, "10.1.15.1", "10.1.15.1"), info.team_lookup["10.1.15.1"])
        self.assertSetEqual({"timetype", "only-leveling", "quiztraction", "memorAIse", "facepalm", "shetcode",
                             "syncryn1z3", "parceroTV"}, info.services)
        ref = {
            "469": {"1": ["wLWrOIlL"], "2": ["AIZG6VIQAE"]},
            "470": {"1": ["utnVafMMqptRfsl"], "2": ["CD65Q74OCB"]},
            "471": {"1": ["LJvsVguZ2AW"], "2": ["GBC6VFJJK0"]},
            "472": {"1": ["7pJkrH3Jy"], "2": ["NJ0R7NSFRF"]},
            "473": {"1": ["vwsVZyFwwGZdl"], "2": ["DPH14I465S"]},
            "474": {"1": ["U5FXcsuj"], "2": ["M7RFVC6B8A"]},
            "475": {"1": ["iZ1hzS7ucr"], "2": ["JB0RT26F9D"]},
            "476": {"1": ["p86QWH8r"], "2": ["UKGT3O27RO"]},
            "477": {"1": ["8EdFEQWgHwEERr"], "2": ["R46Z910SMC"]},
            "478": {"1": ["C2MkxdY0"], "2": ["D00CNNTA1U"]}
        }
        self.assertEqual(ref, info.flag_id_raw("timetype", "15"))
        self.assertEqual(ref, info.flag_id_raw("timetype", "10.1.15.1"))
        flat_ref = [s for team in ref.values() for store in team.values() for s in store]
        self.assertEqual(flat_ref, info.flag_id_flat("timetype", "15"))

    def test_faust(self) -> None:
        info = Decoder().parse((self._res / "faust2024.json").read_bytes())
        self.assertEqual(244, len(info.teams))
        self.assertEqual(Team(42, "fd66:666:42::2", "Team #42"), info.team_lookup["42"])
        self.assertEqual(Team(42, "fd66:666:42::2", "Team #42"), info.team_lookup["fd66:666:42::2"])
        self.assertSetEqual({"FAUST Vault", "asm_chat", "SecretChannel", "todo-list-service", "QuickR Maps", "lvm"},
                            info.services)
        ref = [
            "NXgyrDfCfWRPuess",
            "DcypHqxVeJhkTbaY",
            "IzukGsKvMXIrSVqg",
            "SgudxnsFKKBvAGZc",
            "nSHVYBpYeAgVnnSA",
            "AcSKiYgoCVIjkYNM"
        ]
        self.assertEqual(ref, info.flag_id_raw("asm_chat", "57"))
        self.assertEqual(ref, info.flag_id_raw("asm_chat", "fd66:666:57::2"))
        self.assertEqual(ref, info.flag_id_flat("asm_chat", "57"))

    def _bench(self, fname: str) -> float:
        times = []
        for _ in range(10):
            t = time.monotonic()
            Decoder().parse((self._res / fname).read_bytes())
            times.append((time.monotonic() - t) * 1000.0)
        print(f"{fname:16s}: {min(times):5.2f}ms - {max(times):5.2f}ms / avg. {sum(times) / len(times):5.2f}ms")
        return sum(times) / len(times)

    def test_bench(self) -> None:
        print("Benchmarking ...")
        self._bench("saarctf2025.json")
        self._bench("enowars9.json")
        self._bench("faust2024.json")

    def test_dialect(self) -> None:
        decoder = Decoder()
        dialect = decoder._get_dialect(json.loads((self._res / "saarctf2025.json").read_bytes()))
        self.assertEqual("saarctf", dialect.name)
        dialect = decoder._get_dialect(json.loads((self._res / "enowars9.json").read_bytes()))
        self.assertEqual("enowars", dialect.name)
        dialect = decoder._get_dialect(json.loads((self._res / "faust2024.json").read_bytes()))
        self.assertEqual("faustctf", dialect.name)


if __name__ == '__main__':
    unittest.main()
