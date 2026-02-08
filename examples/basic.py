"""
USAGE:
python basic.py            # attack all teams
python basic.py 10.32.1.2  # attack IP
python basic.py 1          # attack team by ID (if API has team IDs)
python basic.py NOP        # attack team by name (if API has team names)
"""
import sys

from attackapi import configure, attack_info

# Configure the caching API:
configure("https://ctf.saarland/static/scoreboard/api/attack.json")  # or use CTF_API environment variable


def attack(ip: str) -> None:
    service_name = "Licenser"  # print((await api.attack_info()).services)
    # Request attack info / flag IDs for the service/team you want to exploit
    for username in attack_info().flag_id_flat(service_name, ip):
        print(f"Attacking {ip!r} / {username!r} ...")
        ...


def attack_all() -> None:
    # Request a list of attackable teams
    info = attack_info()
    print(f"Attacking {info.teams} teams ...")
    for team in info.teams:
        attack(team.ip)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        attack(sys.argv[1])
    else:
        attack_all()
