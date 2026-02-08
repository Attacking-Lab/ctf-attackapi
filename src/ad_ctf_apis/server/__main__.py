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
    parser.add_argument("--lifetime", type=float, default=30.0, help="Lifetime of cached data in seconds")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout for API calls in seconds")
    args = parser.parse_args()

    api = AdCtfApiAsync(args.url, args.tmp_directory, lifetime=args.lifetime, timeout=args.timeout)
    app = AdCtfServer(api)
    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
