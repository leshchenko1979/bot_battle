import inspect
import httpx

from logging import info, debug


class BotClient:
    def __init__(self, token: str, bot_cls, dispatcher_url):
        info(f"Initializing BotClient with token: {token}")

        self.bot_token = token
        self.bot_cls = bot_cls

        self.dispatcher_url = dispatcher_url

        self.set_up_http_client()

        info("Initialization complete")

    def set_up_http_client(self):
        info("Setting up HTTP client")
        headers = {"Authorization": f"Bearer {self.bot_token}"}
        self.http_client = httpx.Client(base_url=self.dispatcher_url, headers=headers)

    def get(self, path, **kwargs):
        return self.http_client.get(path, **kwargs)

    def post(self, path, **kwargs):
        return self.http_client.post(path, **kwargs)

    def run(self):
        info("Running")
        try:
            self.send_code()
            self.monitor_logs()
        except KeyboardInterrupt:
            info("Interrupted by user")

    def send_code(self):
        info("Sending code to the server")
        self.post(
            "/update_code",
            json={
                "source": inspect.getsource(self.bot_cls),
                "cls_name": self.bot_cls.__name__,
            },
        )

    def monitor_logs(self):
        ...
