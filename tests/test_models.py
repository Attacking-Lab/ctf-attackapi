import warnings
from typing import Any, List, Tuple

from attackapi.async_api.decoders import Decoder
from attackapi.models import AttackInfo, Team, select_round
from .utils import BaseTestCase


class LookupTestCase(BaseTestCase):
    """
    Exploits are written in a hurry and run unattended, so a lookup that cannot be answered must
    not take the round down with it. Everything here asserts a value came back, and that the
    mistakes worth knowing about announced themselves on the side.
    """

    def setUp(self) -> None:
        self.info = Decoder().parse((self._res / "atklab2026.json").read_bytes())

    def test_no_lookup_raises(self) -> None:
        nop = self.info.team("nop")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lookups: List[Tuple[str, Any]] = [
                ("ServiceA", None),                 # info.team(...) that found nothing
                ("ServiceA", "does-not-exist"),
                ("nope", "nop"),
                ("nope", None),
                ("ServiceA", 4.0),                  # a type the API never promised to take
                ("ServiceA", nop),
            ]
            for service, team in lookups:
                self.assertIsInstance(self.info.flag_id_flat(service, team), list)
                self.assertIsInstance(self.info.attack_info_flat(service, team), list)
                self.info.flag_id_raw(service, team)
                self.info.attack_info_raw(service, team)

    def test_unresolved_team_warns_instead_of_raising(self) -> None:
        # the shape a hurried exploit actually writes: team() missed, and its None went straight on
        with self.assertWarns(UserWarning) as caught:
            self.assertEqual([], self.info.flag_id_flat("ServiceA", self.info.team("typo")))
        self.assertIn("did an earlier team() lookup fail?", str(caught.warning))
        # blamed on this file rather than on a line inside the library
        self.assertEqual(__file__, caught.filename)

    def test_unknown_service_warns(self) -> None:
        with self.assertWarns(UserWarning) as caught:
            self.assertEqual([], self.info.flag_id_flat("nope", "nop"))
        self.assertIn("Unknown service 'nope'", str(caught.warning))
        self.assertIn("ServiceA", str(caught.warning))
        self.assertEqual(__file__, caught.filename)

    def test_unknown_team_warns(self) -> None:
        with self.assertWarns(UserWarning) as caught:
            self.assertEqual([], self.info.flag_id_flat("ServiceA", "does-not-exist"))
        self.assertIn("Unknown team 'does-not-exist'", str(caught.warning))
        self.assertEqual(__file__, caught.filename)

    def test_invalid_team_type_warns(self) -> None:
        with self.assertWarns(UserWarning) as caught:
            self.assertEqual([], self.info.flag_id_flat("ServiceA", 4.0))  # type: ignore[arg-type]
        self.assertIn("Invalid team type", str(caught.warning))

    def test_known_team_without_flag_ids_stays_quiet(self) -> None:
        # the service is down, or this round's info is not out yet: ordinary, and not the
        # exploit's mistake. Only the errors that are wrong on every call are worth a warning.
        info = AttackInfo(
            teams=[Team(1, "10.0.0.1", "nop")],
            team_lookup={"1": Team(1, "10.0.0.1", "nop"), "nop": Team(1, "10.0.0.1", "nop")},
            services={"ServiceA"},
            flag_ids={"servicea": {}},
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.assertEqual([], info.flag_id_flat("ServiceA", "nop"))
            self.assertIsNone(info.flag_id_raw("ServiceA", info.team("nop")))

    def test_resolvable_lookups_stay_quiet(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            teams: List[Any] = ["nop", "1", 1, "10.32.1.2", self.info.team("nop")]
            for team in teams:
                self.assertEqual(["alice", "bob", "carol"], self.info.flag_id_flat("ServiceA", team))


class SelectRoundTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.info = Decoder().parse((self._res / "atklab2026.json").read_bytes())

    def test_round_selects_one_round(self) -> None:
        self.assertEqual({"5": {"0": "alice", "1": "bob"}}, self.info.flag_id_raw("ServiceA", "nop", 5))
        self.assertEqual(["alice", "bob"], self.info.flag_id_flat("ServiceA", "nop", 5))
        self.assertEqual(["carol"], self.info.flag_id_flat("ServiceA", "nop", 6))
        self.assertEqual(["alice", "bob"], self.info.attack_info_flat("ServiceA", "nop", 5))

    def test_negative_round_counts_back_from_the_newest(self) -> None:
        self.assertEqual(["carol"], self.info.flag_id_flat("ServiceA", "nop", -1))
        self.assertEqual(["alice", "bob"], self.info.flag_id_flat("ServiceA", "nop", -2))

    def test_default_is_every_published_round(self) -> None:
        # the game API already publishes only the rounds whose flags are still valid, so narrowing
        # by default would cost an exploit flags it could have had
        self.assertEqual(["alice", "bob", "carol"], self.info.flag_id_flat("ServiceA", "nop"))

    def test_round_outside_the_published_window_is_empty(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # which rounds are published changes constantly
            self.assertEqual([], self.info.flag_id_flat("ServiceA", "nop", 9999))
            self.assertEqual([], self.info.flag_id_flat("ServiceA", "nop", -99))

    def test_rounds_are_ordered_numerically_not_as_published(self) -> None:
        self.assertEqual({"10": "j"}, select_round({"9": "i", "10": "j"}, -1))

    def test_a_game_without_rounds_is_left_alone(self) -> None:
        # FAUST CTF has no round dimension, so there is nothing to slice and a list of flag IDs
        # must not be mistaken for one
        faust = Decoder().parse((self._res / "faust2024.json").read_bytes())
        service = sorted(faust.services)[0]
        team = faust.teams[0]
        every = faust.flag_id_flat(service, team)
        self.assertTrue(every)
        self.assertEqual(every, faust.flag_id_flat(service, team, 3))
