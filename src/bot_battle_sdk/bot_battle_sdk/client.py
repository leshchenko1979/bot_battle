import inspect
import httpx

from logging import info, debug

class BotClient:
    def __init__(
        self,
        token: str,
        func,
        dispatcher_url
    ):
        info(f"Initializing BotClient with token: {token}")

        self.bot_id = None
        self.bot_token = token
        self.func = func

        self.dispatcher_url = dispatcher_url

        self.set_up_http_client()

    def __repr__(self):
        return f"<BotClient(id={self.bot_id})>"

    def set_up_http_client(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.http_client = httpx.Client(
            base_url=self.dispatcher_url, header=headers
        )

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
        info ("Sending code to the server")
        self.post("/update_code", {"code": inspect.getsource(self.func.make_move)})

    def monitor_logs(self):
        ...
