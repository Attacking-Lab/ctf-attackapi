"""
An example with all config options available.

USAGE:
python full.py            # attack all teams
python full.py 10.32.1.2  # attack IP
python full.py 1          # attack team by ID (if API has team IDs)
python full.py NOP        # attack team by name (if API has team names)
"""
import asyncio
import sys

from ad_ctf_apis.async_api import AdCtfApiAsync

# Configure the caching API:
api = AdCtfApiAsync(
    "https://ctf.saarland/static/scoreboard/api/attack.json",
    tmp_directory="/dev/shm",
    lifetime=20.0,
    timeout=7.0,
    aiohttp_arguments={"verify_ssl": False}
)


async def attack(ip: str) -> None:
    service_name = "Licenser"  # print((await api.attack_info()).services)
    # Request attack info / flag IDs for the service/team you want to exploit
    for username in (await api.attack_info()).flag_id_flat(service_name, ip):
        print(f"Attacking {ip!r} / {username!r} ...")
        ...


async def attack_all() -> None:
    # Request a list of attackable teams
    info = await api.attack_info()
    print(f"Attacking {info.teams} teams ...")
    tasks = [asyncio.create_task(attack(team.ip)) for team in info.teams]
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(attack(sys.argv[1]))
    else:
        asyncio.run(attack_all())
