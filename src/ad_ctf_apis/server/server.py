from typing import Any

from aiohttp import web

from ad_ctf_apis.async_api import AdCtfApiAsync


class AdCtfServer(web.Application):
    def __init__(self, api: AdCtfApiAsync, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._api = api
        self.add_routes([
            web.get("/api/v1/services", self.get_services),
            web.get("/api/v1/teams", self.get_teams),
        ])

    async def get_teams(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"teams": [team.to_dict() for team in info.teams]})

    async def get_services(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"services": info.services})
