import json
import os
import tempfile
from typing import Any, Callable

from aiohttp import web

from ad_ctf_apis import AttackInfo
from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.server.docs import docs_html, openapi_path


class AdCtfServer(web.Application):
    def __init__(self, api: AdCtfApiAsync, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._api = api
        self.add_routes([
            web.get("/", self.docs),
            web.get("/api.yaml", self.api_spec),
            web.get("/api/v1/raw", self.get_raw),
            web.get("/api/v1/services", self.get_services),
            web.get("/api/v1/teams", self.get_teams),
            web.get("/api/v1/attack_info/{service}/{team}", self.get_attack_info),
            web.get("/api/v1/attack_info_raw/{service}/{team}", self.get_attack_info_raw),
        ])

    async def docs(self, request: web.Request) -> web.Response:
        docs = docs_html()
        docs = docs.replace('"http://localhost:14320"', json.dumps("http://" + request.host))
        try:
            info = await self._api.attack_info()
            if len(info.services) > 0:
                docs = docs.replace('"RCEaaS"', json.dumps(list(info.services)[0]))
            if len(info.teams) > 0:
                docs = docs.replace('"10.32.1.2"', json.dumps(info.teams[0].ip))
                docs = docs.replace('"example": 1', '"example": ' + json.dumps(info.teams[0].id))
                docs = docs.replace('"NOP"', json.dumps(info.teams[0].name))
                if len(info.services) > 0:
                    s = list(info.services)[0]
                    raw = info.flag_id_raw(s, info.teams[0])
                    flat = info.flag_id_flat(s, info.teams[0])
                    if raw:
                        docs = docs.replace(
                            json.dumps({"227": "username1", "228": "username2", "229": "username3"}),
                            json.dumps(raw)
                        )
                        docs = docs.replace(
                            json.dumps(["username1", "username2", "username3"]),
                            json.dumps(flat)
                        )
        except:  # noqa
            pass
        return web.Response(text=docs, content_type="text/html")

    async def api_spec(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(openapi_path())

    async def get_raw(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.Response(body=info.raw, content_type="application/json")

    async def get_teams(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"teams": [team.to_dict() for team in info.teams]})

    async def get_services(self, request: web.Request) -> web.Response:
        info = await self._api.attack_info()
        return web.json_response({"services": list(info.services)})

    async def _attack_info_common(self, request: web.Request,
                                  cb: Callable[[AttackInfo, str, str], Any]) -> web.Response:
        service = request.match_info["service"]
        team = request.match_info["team"]
        if not service or not team:
            raise web.HTTPBadRequest(reason="Invalid team or service")
        info = await self._api.attack_info()
        if service.lower() not in info.flag_ids:
            raise web.HTTPBadRequest(reason=f"Unknown service, or service has no attack info: {service}")
        flag_ids = cb(info, service, team)
        return web.json_response(
            {"attack_info": flag_ids}
        )

    async def get_attack_info(self, request: web.Request) -> web.Response:
        def _cb(info: AttackInfo, service: str, team: str) -> Any:
            return info.flag_id_flat(service, team)

        return await self._attack_info_common(request, _cb)

    async def get_attack_info_raw(self, request: web.Request) -> web.Response:
        def _cb(info: AttackInfo, service: str, team: str) -> Any:
            return info.flag_id_raw(service, team)

        return await self._attack_info_common(request, _cb)


async def create_app() -> web.Application:
    """Create the app for gunicorn"""
    api = AdCtfApiAsync(
        url=os.environ["CTF_API"],
        tmp_directory=os.environ.get("CTF_API_TMP_DIR", tempfile.gettempdir()),
        lifetime=float(os.environ.get("CTF_API_LIFETIME", 30.0)),
        timeout=float(os.environ.get("CTF_API_TIMEOUT", 10.0))
    )
    return AdCtfServer(api)
