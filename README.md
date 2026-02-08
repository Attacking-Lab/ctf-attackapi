AD CTF API - Cached and Unified!
================================

Gather attack information quickly in your attack-defense CTF exploits!

During [attack-defense CTF competitions](https://wiki.attacking-lab.com/attack-defense/), you have to write exploits
quickly and run them on a large scale.
These exploits often require information about the targets to attack (teams and sometimes usernames).
This attack info is available as a big JSON file which is updated every few minutes.
Downloading that file for every exploit you're firing is costing time and bandwidth.

This package fetches, parses, and caches attack info for you, so you can focus on writing exploits!

Features
--------

- Efficient caching between threads, processes, or containers
- Direct access from your Python exploits ([sync](./examples/basic.py) or [async](./examples/basic_async.py))
- Optional REST API for exploits in other languages (with [OpenAPI spec](./api.yaml))
- Unifies team, IP, and flag info lookup between different CTFs:
    - Supports [ENOwars](https://enowars.com)
    - Supports [FaustCTF](https://faustctf.net)
    - Supports [saarCTF](https://ctf.saarland) (including ECSC gameserver)

Quick-Start
-----------
See [examples](./examples) directory for more full scripts.

Install the package (possibly in a virtual environment):

```shell
pip install ad-ctf-apis
```

Get attack infos for your python exploit:

```python
from ad_ctf_apis import *

# 1. Set the API URL in code (or use CTF_API environment variable)
configure("https://scoreboard.ctf.saarland/api/attack.json")
# 2. Get attack infos!
for username in attack_info().flag_id_flat("no-service", "10.32.1.2"):
    pwn("10.32.1.2", username)
```

List all teams that you can attack:

```python
from ad_ctf_apis import *

configure("https://scoreboard.ctf.saarland/api/attack.json")
for team in attack_info().teams:
    print(team.id, team.ip, team.name)
```

Get attack infos from REST API if you're not pwning in Python:

```shell
python -m ad_ctf_apis.server --url "https://scoreboard.ctf.saarland/api/attack.json"
curl "http://localhost:14320/api/v1/teams"
```

The server has documentation on its frontpage, and here is [the OpenAPI specification](./api.yaml).

If you're not pwning in Python and dislike pip, try docker:
```shell
# edit compose.yaml and insert your CTF API URL
docker compose up -d
# visit http://localhost:14320/
```


Structure
---------

- Attack info data is retrieved and cached twice: in-memory and on disk (`/tmp` by default)
- Each request goes to the caches. If the cached data is outdated, it is refreshed in the background.
- No concurrent requests are made to the game API.
- Game-specific decoders process the game APIs data and make it accessible.
- You can query the data via python API from your exploits, or via REST API from other languages.
- Relying on the disk cache is good enough for typical exploitation scenarios.

Python Library Documentation
----------------------------
There are different ways to get an `AttackInfo` object:

```python
# 1. Functional
from ad_ctf_apis import *

# Set the API URL in code (or use CTF_API environment variable)
configure("https://scoreboard.ctf.saarland/api/attack.json")
# sync:
info: AttackInfo = attack_info()
# async
info: AttackInfo = await attack_info_async()

# 2. By manually using the classes
from ad_ctf_apis.sync_api import AdCtfApiSync
from ad_ctf_apis.async_api import AdCtfApiAsync

api = AdCtfApiSync("https://scoreboard.ctf.saarland/api/attack.json")
info = api.attack_info()
api2 = AdCtfApiAsync("https://scoreboard.ctf.saarland/api/attack.json")
info = await api2.attack_info()
```

Optional parameters can be passed to the `configure` function or the API constructors:

- `url: str` (default: `CTF_API` environment variable)
- `tmp_directory: str | Path` (default: `/tmp` or OS-specific alternative)
- `lifetime: float` (default: 30 seconds) - after this time, cached data is invalidated and refreshed
- `timeout: float` (default: 10 seconds) - abort game API requests after this duration
- `decoder: Decoder` (default: generic decoder) - custom decoder, if your game's format is different from what we've
  seen so far
- `aiohttp_arguments: dict` - additional arguments passed to the aiohttp Session which contacts the game API

The `AttackInfo` class itself has these methods:

```python
info: AttackInfo

# Get attackable teams
print(info.teams)  # list of Team objects
print(info.teams[0].id, info.teams[0].ip, info.teams[0].name)  # Team is ID, IP, and optional name
print(info.team("10.32.1.2"))  # query Team object by ID, IP, or name

# set of service names
print(info.services)

# raw flag IDs for a service and team.
# team can be ID, IP, or name. 
# Return data format is determined by game API.
print(info.flag_id_raw("servicename", "10.32.1.2"))
# => {"227": "abc", "228": "def", ...}

# Get flag IDs as string list (independent of game API format, but less precise)
print(info.flag_id_flat("servicename", "10.32.1.2"))
# => ["abc", "def"]
```

Server Documentation
--------------------

```shell
# Simple usage:
python -m ad_ctf_apis.server --help
```

Options:

- `--port PORT`
- `--url URL`: API url to get CTF info from.
- `--tmp-directory TMP_DIRECTORY`: Cache directory
- `--lifetime LIFETIME`: Lifetime of cached data in seconds
- `--timeout TIMEOUT`: Timeout for API calls in seconds

```shell
# Usage for higher load scenarios:
pip install ad-ctf-apis[gunicorn]
gunicorn ad_ctf_apis.server:create_app --bind :14320 --worker-class ad_ctf_apis.server.worker.MyGunicornWebWorker --workers 4
```

Environment variables:

- `CTF_API`: URL to get CTF info from.
- `CTF_API_TMP_DIR`: Cache directory (gunicorn only)
- `CTF_API_LIFETIME`: Lifetime of cached data in seconds (gunicorn only)
- `CTF_API_TIMEOUT`: Timeout for API calls in seconds (gunicorn only)

You can also use docker to run the server:
```shell
# edit compose.yaml and insert your CTF API URL before!
docker compose up -d
```