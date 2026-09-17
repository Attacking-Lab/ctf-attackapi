Changelog
=========

0.3.0
-----

- `flag_id_flat()` is now `flag_ids()`, and `flag_id_raw()` is `flag_ids_raw()`. The list of
  strings is what an exploit wants essentially every time, so it gets the plain name, and only the
  one that hands back the game's own structure carries a suffix. The `attack_info_*` aliases are
  gone with them: flag IDs is what most games call these, so the package calls them that once.
  The REST API follows -- `/api/v1/flag_ids/...` and `/api/v1/flag_ids_raw/...`, returning a
  `flag_ids` key.
- Lookups never raise. `flag_ids()` returns `[]` and `flag_ids_raw()` returns `None` for
  anything they cannot answer, including a `None` team -- so the common
  `flag_ids(service, info.team(name))` no longer dies on a name that did not resolve.
- The mistakes that are wrong on *every* call -- an unknown service or team, a team that never
  resolved, a team of a type the API never took -- now raise a `UserWarning` pointing at your
  line, instead of being indistinguishable from a team that simply has no flag IDs yet. The
  ordinary case stays silent: a known team with nothing published this round is not your mistake.
  Silence the warnings with `warnings.simplefilter("ignore")` if your exploit prefers it.
- Both take an optional `round`, counting back from the newest published round when negative
  (`-1` is the newest). The default is unchanged and still returns every round the game API
  published -- it only publishes the rounds whose flags are still valid, so narrowing by default
  would cost you flags. The selector is public as `attackapi.select_round()`, next to
  `flatten_flag_ids()`.
- New `has_service()`, for the case-insensitive "does this game have that service?" check that
  previously meant reaching into the `flag_ids` field. That field is now private.

0.2.0
-----

- New `atklab` dialect for the ATKLAB gameserver (ECSC 2026): attack info under `attack_info`
  instead of `flag_ids`, and rounds instead of ticks. The `saarctf`, `faustctf` and `enowars`
  dialects are unchanged.
- `AttackInfo` gained `flag_regex` and `current_round`, filled in for the games that report them.
- The helper behind `flag_id_flat()` (now `flag_ids()`) is public as
  `attackapi.flatten_flag_ids()`, for callers that flatten a subset of the raw structure
  themselves.
- `flag_id_flat()` drops `null` flag IDs instead of returning them as `None` -- a flag store with
  no ID for a round is a hole, not a value.
- `GenericAdCtfApiAsync` accepts a plain callable decoder, a `progress` hook, and an injectable
  `memory_cache`, so it can back a whole game API rather than just `attack.json`.
