from logging import basicConfig, getLogger

import httpx

from .players import make_code
from .protocol import VersionInfo

logger = getLogger(__name__)
info = logger.info
debug = logger.debug
error = logger.error

basicConfig(level="INFO")


class BotClient:
    def __init__(self, token: str, bot_cls, dispatcher_url):
        debug(f"Initializing BotClient with token: {token}")

        self.bot_token = token
        self.bot_cls = bot_cls

        self.dispatcher_url = dispatcher_url

        self.code = make_code(self.bot_cls)

        self.set_up_http_client()

        info("Initialization complete")

    def set_up_http_client(self):
        debug("Setting up HTTP client")
        headers = {"Authorization": f"Bearer {self.bot_token}"}
        self.http_client = httpx.Client(base_url=self.dispatcher_url, headers=headers)

    def get(self, path, **kwargs):
        return self.http_client.get(path, **kwargs)

    def post(self, path, **kwargs):
        return self.http_client.post(path, **kwargs)

    def run(self):
        info("Running")
        self.send_code()
        self.get_latest_versions_info()

    def send_code(self):
        info("Sending code to the server")

        result = self.post("/update_code", json=self.code.dict())
        result.raise_for_status()

        if result.json()["updated"]:
            info("Code updated, new games scheduled")
        else:
            info("Code hasn't changed")

    def get_latest_versions_info(self):
        info("Listing latest versions")

        response = self.get("/latest_versions_info/")
        response.raise_for_status()

        versions = [VersionInfo(**row) for row in response.json()]

        for version in versions:
            beginning = f"{version.created_at.strftime('%Y-%m-%d %H:%M:%S')}, {version.loc:3} loc:"

            if version.exception:
                content = "crashed"
            else:
                stats = version.stats
                total = stats.victories + stats.losses + stats.ties
                if total:
                    content = (
                        f"wins={stats.victories:3}({stats.victories/total:3.0%}), "
                        f"losses={stats.losses:3}({stats.losses/total:3.0%}), "
                        f"ties={stats.ties:3}({stats.ties/total:3.0%})"
                    )
                else:
                    content = "no games played"

            info(f"{beginning}: {content}")

        if versions[-1].exception:
            info(
                f"The latest version raised an exception:\n"
                f"{versions[-1].exception.msg}\n"
                f"The move was '{versions[-1].exception.move}'"
            )
