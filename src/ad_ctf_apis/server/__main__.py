import argparse
import tempfile

from aiohttp import web

from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.server.server import AdCtfServer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=14320)
    parser.add_argument("--url", type=str, default="",
                        help="API url to get CTF info from.")
    parser.add_argument("--tmp-directory", type=str, default=tempfile.gettempdir(),
                        help="Cache directory")
    args = parser.parse_args()

    api = AdCtfApiAsync(args.url, args.tmp_directory)
    app = AdCtfServer(api)
    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
