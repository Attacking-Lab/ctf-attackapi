from typing import Any

from aiohttp import web

from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.server.docs import docs_html, openapi_path


class AdCtfServer(web.Application):
    def __init__(self, api: AdCtfApiAsync, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._api = api
        self.add_routes([
            web.get("/", self.docs),
            web.get("/api.yaml", self.api_spec),
            web.get("/api/v1/services", self.get_services),
            web.get("/api/v1/teams", self.get_teams),
        ])

    async def docs(self, request: web.Request) -> web.Response:
        return web.Response(text=docs_html(), content_type="text/html")

    async def api_spec(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(openapi_path())

    async def get_teams(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"teams": [team.to_dict() for team in info.teams]})

    async def get_services(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"services": list(info.services)})
