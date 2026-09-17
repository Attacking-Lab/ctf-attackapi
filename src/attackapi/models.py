import warnings
from dataclasses import dataclass, field, asdict
from typing import Optional, Union, Any
from typing_extensions import TypeAlias

RawFlagIds: TypeAlias = Union[list, dict[str, Union[str, list, dict]]]


def flatten_flag_ids(flag_ids: Any) -> list[str]:
    """
    Collect every non-null scalar flag ID out of an arbitrarily nested flag-ID structure.
    Independent of the game API's exact nesting, but loses the round / flag-store structure.
    """
    if flag_ids is None:  # a flag store with no ID for this round/team
        return []
    if isinstance(flag_ids, str):
        return [flag_ids]
    if isinstance(flag_ids, list):
        result = []
        for value in flag_ids:
            result += flatten_flag_ids(value)
        return result
    if isinstance(flag_ids, dict):
        result = []
        for value in flag_ids.values():
            result += flatten_flag_ids(value)
        return result
    return [str(flag_ids)]


def select_round(flag_ids: Any, round: int) -> Any:
    """
    Restrict flag IDs to a single round. Every game that reports a round keys its per-team attack
    info by it; FAUST CTF does not have the dimension at all, and its plain list is returned
    unchanged rather than sliced into something that only looks like a round.

    :param flag_ids: raw flag IDs for one service and team, as returned by flag_ids_raw()
    :param round: a round number, or an offset from the newest published round (-1 = newest)
    :return: the same structure, holding at most the requested round
    """
    if not isinstance(flag_ids, dict):
        return flag_ids
    keys = list(flag_ids.keys())
    if round < 0:
        # the game API publishes a window of recent rounds, in no guaranteed order
        if all(isinstance(key, str) and key.lstrip("-").isdigit() for key in keys):
            keys.sort(key=int)
        if -round > len(keys):
            return {}
        key = keys[round]
    else:
        key = str(round)
    return {key: flag_ids[key]} if key in flag_ids else {}


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
    Use methods team(), flag_ids(), and flag_ids_raw() to look up data.
    Fields teams and services can be iterated.
    """

    teams: list[Team] = field(default_factory=list)
    team_lookup: dict[str, Team] = field(default_factory=dict)
    services: set[str] = field(default_factory=set)
    _flag_ids: dict[str, dict[str, RawFlagIds]] = field(default_factory=dict)
    flag_regex: Optional[str] = None
    current_round: Optional[int] = None
    raw: bytes = b""  # everything, as given by the game API

    def team(self, name: Union[str, int]) -> Optional[Team]:
        """
        Find a team.

        :param name: Team ID, IP, or name (as far as supported by the API)
        :return:
        """
        return self.team_lookup.get(str(name).lower())

    def has_service(self, service: str) -> bool:
        """
        Whether this game has a service by that name (case insensitive).

        :param service: Name of a service
        :return:
        """
        return service.lower() in self._flag_ids

    def flag_ids(self, service: str, team: Union[str, int, Team, None],
                 round: Optional[int] = None) -> list[str]:
        """
        Find flag IDs for a service and team, as a simple string list -- the same list whatever
        game you are playing, and what an exploit almost always wants.

        Never raises: a lookup that cannot be answered warns and returns [], so a typo in an
        exploit costs a warning on stderr rather than the round it was in the middle of.

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :param round: Restrict the result to one round, or to an offset from the newest published
            round (-1 = newest). Defaults to every round the game API published.
        :return:
        """
        flag_ids = self._lookup(service, team, round)
        return flatten_flag_ids(flag_ids) if flag_ids is not None else []

    def flag_ids_raw(self, service: str, team: Union[str, int, Team, None],
                     round: Optional[int] = None) -> Optional[RawFlagIds]:
        """
        Find flag IDs for a service and team, in the game API's own format -- for callers that
        need the structure flag_ids() flattens away. That format differs per game.

        Never raises, and returns None for anything it cannot answer -- see flag_ids().

        :param service: Name of a service (case insensitive, see field "services" for a list of valid names)
        :param team: Team ID, IP, name, or instance (from .team(...))
        :param round: Restrict the result to one round, or to an offset from the newest published
            round (-1 = newest). Defaults to every round the game API published.
        :return:
        """
        return self._lookup(service, team, round)

    def _lookup(self, service: str, team: Union[str, int, Team, None],
                round: Optional[int], stacklevel: int = 3) -> Optional[RawFlagIds]:
        """
        The lookup behind both accessors. Warns rather than raises on the mistakes that are wrong
        on every call -- an unknown service or team, a team that never resolved -- and stays quiet
        about the ones that are a normal part of a running game.

        :param stacklevel: frames between this method and the caller to blame in a warning
        """
        if team is None:
            warnings.warn(f"No team given for service {service!r} - did an earlier team() lookup fail?",
                          stacklevel=stacklevel)
            return None
        flag_ids = self._flag_ids.get(service.lower())
        if flag_ids is None:
            warnings.warn(f"Unknown service {service!r}, this game has: {', '.join(sorted(self.services))}",
                          stacklevel=stacklevel)
            return None
        raw = self._team_flag_ids(service, flag_ids, team, stacklevel + 1)
        if raw is None or round is None:
            return raw
        return select_round(raw, round)

    def _team_flag_ids(self, service: str, flag_ids: dict, team: Union[str, int, Team],
                       stacklevel: int) -> Optional[RawFlagIds]:
        """Pick one team out of a service's flag IDs, which the game API keys by ID, IP, or name."""
        if isinstance(team, Team):
            for key in (str(team.id), team.ip, team.name):
                if key is not None and key.lower() in flag_ids:
                    return flag_ids[key.lower()]
            # a team the game knows about but has no flag IDs for: the service may be down, or the
            # round's info may not be out yet. Both are ordinary, and neither is worth a warning.
            return None
        if isinstance(team, (str, int)):
            key = str(team).lower()
            if key in flag_ids:
                return flag_ids[key]
            if key in self.team_lookup:
                return self._team_flag_ids(service, flag_ids, self.team_lookup[key], stacklevel)
            warnings.warn(f"Unknown team {team!r} for service {service!r} - not in this attack info "
                          f"(a typo, or a team that is offline or banned)", stacklevel=stacklevel)
            return None
        warnings.warn(f"Invalid team type for service {service!r}: {type(team).__name__}: {team!r}",
                      stacklevel=stacklevel)
        return None

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"AttackInfo(services={self.services!r}, {len(self.teams)} teams)"
