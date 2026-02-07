from dataclasses import dataclass, field
from typing import Optional, Union
from typing_extensions import TypeAlias

RawFlagIds: TypeAlias = Union[list, dict[str, Union[str, list, dict]]]


@dataclass
class Team:
    id: Optional[int] = None
    ip: Optional[str] = None
    name: Optional[str] = None


@dataclass
class AttackInfo:
    teams: dict[str, Team] = field(default_factory=dict)
    services: set[str] = field(default_factory=set)
    flag_ids: dict[str, dict[str, RawFlagIds]] = field(default_factory=dict)

    def team(self, name: Union[str, int]) -> Optional[Team]:
        """
        Find a team.

        :param name: Team ID, IP, or name (as far as supported by the API)
        :return:
        """
        return self.teams.get(str(name).lower())

    def flag_id(self, service: str, team: Union[str, int, Team]) -> Optional[RawFlagIds]:
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
            elif team in self.teams:
                return self.flag_id(service, self.teams[team])
            return None
        elif isinstance(team, int):
            if str(team) in flag_ids:
                return flag_ids.get(str(team))
            elif str(team) in self.teams:
                return self.flag_id(service, self.teams[str(team)])
            return None

        raise ValueError(f"Invalid team type: {type(team)}: {team!r}")

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"AttackInfo(services={self.services!r}, {len(self.teams)} teams)"
