"""
USAGE:
python basic_async.py            # attack all teams
python basic_async.py 10.32.1.2  # attack IP
python basic_async.py 1          # attack team by ID (if API has team IDs)
python basic_async.py NOP        # attack team by name (if API has team names)
"""
import asyncio
import sys

from attackapi import configure, attack_info_async

# Configure the caching API:
configure("https://ctf.saarland/static/scoreboard/api/attack.json")  # or use CTF_API environment variable


async def attack(ip: str) -> None:
    service_name = "Licenser"  # print((await api.attack_info()).services)
    # Request attack info / flag IDs for the service/team you want to exploit
    for username in (await attack_info_async()).flag_id_flat(service_name, ip):
        print(f"Attacking {ip!r} / {username!r} ...")
        ...


async def attack_all() -> None:
    # Request a list of attackable teams
    info = await attack_info_async()
    print(f"Attacking {info.teams} teams ...")
    tasks = [asyncio.create_task(attack(team.ip)) for team in info.teams]
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(attack(sys.argv[1]))
    else:
        asyncio.run(attack_all())
