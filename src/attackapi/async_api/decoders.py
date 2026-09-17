"""
Summary of different API formats:
saarctf: flag_ids    => {service_name => {ip => data}}   {tick: a, tick2: [b, c]}
atklab:  attack_info => {service_name => {ip => data}}   {round: {store_index: a}}
faust:   flag_ids    => {service_name => {ID => data}}   [a, b]
enowars: services    => {service_name => {ip => data}}   {tick: {X: [a], Y: [b]}}

Additional team list:
saarctf: teams => [0 => {id: ..., name: ..., logo: ...}]
faust:   teams => [ID1, ID2, ...]
enowars: availableTeams: [IP1, IP2, ...]
"""
import json
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Callable, Optional, Generic, TypeVar

from attackapi.models import AttackInfo, Team


@dataclass
class Dialect(ABC):
    """ID/IP foo for the different games."""
    name: str
    ip_pattern: Optional[str] = None  # format string to get IP from ID

    @abstractmethod
    def matches(self, data: dict) -> bool:
        raise NotImplementedError

    def id_from_ip(self, ip: str) -> int:
        return 0

    def ip_from_id(self, team_id: int) -> str:
        if self.ip_pattern is None:
            raise Exception(f"ID to IP conversion required, but no IP pattern defined for dialect {self.name!r}")
        return self.ip_pattern.format(team_id)


class DefaultDialect(Dialect):
    def matches(self, data: dict) -> bool:
        return True


class SaarctfDialect(Dialect):
    def matches(self, data: dict) -> bool:
        return "flag_ids" in data and "teams" in data and len(data["teams"]) > 0 and isinstance(data["teams"][0], dict)

    def id_from_ip(self, ip: str) -> int:
        return int(ip.split(".")[2])  # actually not needed, saarCTF API exposes full team info

    def ip_from_id(self, team_id: int) -> str:
        return f"10.{32 + (team_id // 200)}.{team_id % 200}.2"  # actually not needed, saarCTF API exposes full team info


class AtklabDialect(Dialect):
    """
    ATKLAB gameserver (ECSC 2026). Team entries are shaped like saarCTF's, but the attack info
    sits under "attack_info" and rounds are called rounds, not ticks.
    """

    def matches(self, data: dict) -> bool:
        return "attack_info" in data and "teams" in data \
            and len(data["teams"]) > 0 and isinstance(data["teams"][0], dict)


class FaustDialect(Dialect):
    def matches(self, data: dict) -> bool:
        return "flag_ids" in data and "teams" in data and len(data["teams"]) > 0 and isinstance(data["teams"][0], int)

    def id_from_ip(self, ip: str) -> int:
        return int(ip.split(":")[2])


class EnowarsDialect(Dialect):
    def matches(self, data: dict) -> bool:
        return "services" in data and "availableTeams" in data

    def id_from_ip(self, ip: str) -> int:
        """Actually, IDs don't matter for enowars format"""
        return int(ip.split(".")[2])


DIALECTS = [
    AtklabDialect("atklab"),
    SaarctfDialect("saarctf"),
    FaustDialect("faustctf", "fd66:666:{:d}::2"),
    EnowarsDialect("enowars", "10.1.{:d}.1"),
    DefaultDialect("none")
]

T = TypeVar("T")


class GenericDecoder(ABC, Generic[T]):
    @abstractmethod
    def parse(self, raw: bytes) -> T:
        raise NotImplementedError()


class JSONDecoder(GenericDecoder[dict]):
    def parse(self, raw: bytes) -> dict:
        return json.loads(raw)


class FunctionDecoder(GenericDecoder[T]):
    """Adapts a plain ``bytes -> T`` callable to the decoder interface."""

    def __init__(self, parse: Callable[[bytes], T]) -> None:
        self._parse = parse

    def parse(self, raw: bytes) -> T:
        return self._parse(raw)


class Decoder(GenericDecoder[AttackInfo]):
    """
    A decoder converts the game APIs response (in bytes) into teams, services, and attack information.
    """

    def __init__(self, dialect: Optional[Dialect] = None) -> None:
        """
        :param dialect: auto-inferred by default
        """
        self._dialect = dialect

    def parse(self, raw: bytes) -> AttackInfo:
        """
        Converts game API response to attack infos.
        :param raw:
        :raises ValueError: If data is invalid
        :return:
        """
        data = json.loads(raw)
        dialect = self._get_dialect(data)
        info = AttackInfo(
            flag_regex=data.get("flag_regex"),
            # saarCTF counts ticks, the ATKLAB gameserver counts rounds; same number
            current_round=data.get("current_round", data.get("current_tick")),
            raw=raw
        )

        if "flag_ids" in data:
            self._parse_services(info, data["flag_ids"])
        elif "attack_info" in data:
            self._parse_services(info, data["attack_info"])
        elif "services" in data:
            self._parse_services(info, data["services"])
        else:
            raise ValueError("Unknown format - no flag_ids, attack_info or services key found")

        if "teams" in data:
            self._parse_teams(dialect, info, data["teams"])
        elif "availableTeams" in data:
            self._parse_teams(dialect, info, data["availableTeams"])
        else:
            raise ValueError("Unknown format - no teams or availableTeams key found")

        return info

    def _get_dialect(self, data: dict) -> Dialect:
        if self._dialect is not None:
            return self._dialect
        for dialect in DIALECTS:
            if dialect.matches(data):
                return dialect
        return DefaultDialect("none")

    def _parse_services(self, info: AttackInfo, services: dict) -> None:
        for service_name, flag_ids in services.items():
            if not isinstance(flag_ids, dict):
                raise ValueError(f"Invalid flag_ids format for service {service_name!r}: {type(flag_ids)}")
            info.services.add(service_name)
            info._flag_ids[service_name.lower()] = flag_ids

    def _parse_teams(self, dialect: Dialect, info: AttackInfo, teams: list) -> None:
        for team in teams:
            if isinstance(team, int):
                team = Team(
                    id=team,
                    ip=dialect.ip_from_id(team),
                    name=f"Team #{team}"
                )
            elif isinstance(team, str):
                team = Team(id=dialect.id_from_ip(team), ip=team, name=team)
            elif isinstance(team, dict):
                if not team.get("online", True):
                    continue
                team = Team(
                    id=team["id"],
                    ip=team["ip"] if "ip" in team else dialect.ip_from_id(team["id"]),
                    name=team["name"]
                )
            else:
                raise ValueError(f"Unknown team type: {type(team)}: {json.dumps(team)}")

            info.teams.append(team)
            if team.id is not None:
                info.team_lookup[str(team.id)] = team
            if team.ip is not None:
                info.team_lookup[team.ip.lower()] = team
            if team.name is not None:
                info.team_lookup[team.name.lower()] = team
