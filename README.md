AD CTF Common API
=================

Gather attack information quickly in your attack-defense CTF exploits!

During [attack-defense CTF competitions](https://wiki.attacking-lab.com/attack-defense/), you have to write exploits quickly and run them on a large scale.
These exploits often require information about the targets to attack (teams and sometimes usernames).
This attack info is available as a big JSON file which is updated every few minutes.
Downloading that file for every exploit you're firing is costing time and bandwidth.

This package fetches, parses, and caches attack info for you, so you can focus on writing exploits!

Features
--------
- Efficient caching between threads or processes
- Direct access from your Python exploits (sync or async)
- Optional REST API for exploits in other languages
- Unifies team, IP, and flag info lookup between different CTFs:
  - Supports [ENOwars](https://enowars.com)
  - Supports [FaustCTF](https://faustctf.net)
  - Supports [saarCTF](https://ctf.saarland) (including ECSC gameserver)


Quick-Start
-----------
See [examples](./examples) for more full scripts.

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

Get attack infos from REST API:
```shell
python -m ad_ctf_apis.server --url "https://scoreboard.ctf.saarland/api/attack.json"
curl "http://localhost:14320/api/v1/teams"
```
