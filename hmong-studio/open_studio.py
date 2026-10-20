"""Open the local Studio page after this server has successfully started."""
import threading
import webbrowser

import uvicorn

URL = 'http://127.0.0.1:8090'


def open_page():
    try:
        if webbrowser.open(URL):
            return
    except Exception:
        pass
    print('Mo trinh duyet va truy cap: ' + URL, flush=True)


class StudioServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        if self.started:
            threading.Thread(target=open_page, daemon=True).start()


def main():
    server = StudioServer(uvicorn.Config('app:app', host='127.0.0.1', port=8090,
                                       access_log=False, timeout_graceful_shutdown=10))
    server.run()
    return 0 if server.started else 1


if __name__ == '__main__':
    raise SystemExit(main())
