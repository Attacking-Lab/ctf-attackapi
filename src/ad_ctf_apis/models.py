from dataclasses import dataclass, field, asdict
from typing import Optional, Union, Any, cast
from typing_extensions import TypeAlias

RawFlagIds: TypeAlias = Union[list, dict[str, Union[str, list, dict]]]


def _flat(flag_ids: Any) -> list[str]:
    if isinstance(flag_ids, list):
        return flag_ids[0]
    if isinstance(flag_ids, dict):
        result = []
        for value in flag_ids.values():
            result += _flat(value)
        return result
    return [cast(str, flag_ids)]


@dataclass(frozen=True)
class Team:
    """
    An attackable team.
    IP is given for every game, ID is given or inferred for all known CTFs.
    Name is not present everywhere.
    """
    id: int
    ip: str
    name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AttackInfo:
    """
    Container for all attack info parsed from the game API.
    Use methods team(), flag_id_raw(), and flag_id_flat() to look up data.
    Fields teams and services can be iterated.
    """

    teams: list[Team] = field(default_factory=list)
    team_lookup: dict[str, Team] = field(default_factory=dict)
    services: set[str] = field(default_factory=set)
    flag_ids: dict[str, dict[str, RawFlagIds]] = field(default_factory=dict)
    raw: bytes = b""  # everything, as given by the game API

    def team(self, name: Union[str, int]) -> Optional[Team]:
        """
        Find a team.

        :param name: Team ID, IP, or name (as far as supported by the API)
        :return:
        """
        return self.team_lookup.get(str(name).lower())

    def flag_id_raw(self, service: str, team: Union[str, int, Team]) -> Optional[RawFlagIds]:
        """
        Find flag IDs for a service and team. Flag IDs are returned in the APIs raw format.

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :return:
        """
        flag_ids = self.flag_ids.get(service.lower(), {})
        if isinstance(team, Team):
            if str(team.id) in flag_ids:
                return flag_ids[str(team.id)]
            if team.ip is not None and team.ip.lower() in flag_ids:
                return flag_ids[team.ip.lower()]
            if team.name is not None and team.name.lower() in flag_ids:
                return flag_ids[team.name.lower()]
            return None
        elif isinstance(team, str):
            team = team.lower()
            if team in flag_ids:
                return flag_ids.get(team.lower())
            elif team in self.team_lookup:
                return self.flag_id_raw(service, self.team_lookup[team])
            return None
        elif isinstance(team, int):
            if str(team) in flag_ids:
                return flag_ids.get(str(team))
            elif str(team) in self.team_lookup:
                return self.flag_id_raw(service, self.team_lookup[str(team)])
            return None

        raise ValueError(f"Invalid team type: {type(team)}: {team!r}")

    def flag_id_flat(self, service: str, team: Union[str, int, Team]) -> list[str]:
        """
        Find flag IDs for a service and team.
        Flag IDs are returned as a simple string list, containing all attack info for all flag stores.

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :return:
        """
        flag_ids = self.flag_id_raw(service, team)
        return _flat(flag_ids) if flag_ids is not None else []

    def attack_info_raw(self, service: str, team: Union[str, int, Team]) -> Optional[RawFlagIds]:
        """
        Find attack info for a service and team. Attack info is returned in the APIs raw format.

        This is an alias for flag_id_raw(...).

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :return:
        """
        return self.flag_id_raw(service, team)

    def attack_info_flat(self, service: str, team: Union[str, int, Team]) -> list[str]:
        """
        Find attack info for a service and team.
        Attack info is returned as a simple string list, containing all attack info for all flag stores.

        This is an alias for flag_id_flat(...).

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :return:
        """
        return self.flag_id_flat(service, team)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"AttackInfo(services={self.services!r}, {len(self.teams)} teams)"
