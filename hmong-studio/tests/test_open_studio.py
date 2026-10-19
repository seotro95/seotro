"""The browser must follow a successfully bound local server."""
import asyncio
from contextlib import suppress
import socket
import threading
import urllib.request

import uvicorn

import open_studio


async def ready_app(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        await send({'type': 'http.response.start', 'status': 200,
                    'headers': [(b'content-type', b'text/plain')]})
        await send({'type': 'http.response.body', 'body': b'Studio is ready'})


def test_browser_callback_can_reach_this_started_server(monkeypatch):
    async def exercise():
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        listener.setblocking(False)
        url = 'http://127.0.0.1:' + str(listener.getsockname()[1])
        server = open_studio.StudioServer(uvicorn.Config(
            ready_app, lifespan='on', access_log=False, log_config=None,
            timeout_graceful_shutdown=1,
        ))
        called = threading.Event()
        observations = {}

        def browser_callback():
            observations['started'] = server.started
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    observations['status'] = response.status
                    observations['body'] = response.read()
            except Exception as exc:
                observations['error'] = repr(exc)
            finally:
                called.set()

        monkeypatch.setattr(open_studio, 'open_page', browser_callback)
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            assert await asyncio.to_thread(called.wait, 5), 'browser callback was not called'
            assert observations == {
                'started': True, 'status': 200, 'body': b'Studio is ready',
            }
        finally:
            server.should_exit = True
            try:
                await asyncio.wait_for(task, timeout=5)
            finally:
                listener.close()
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    asyncio.run(exercise())


def test_failed_application_startup_never_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(open_studio, 'open_page', lambda: opened.append(True))

    async def failed_app(scope, receive, send):
        assert scope['type'] == 'lifespan'
        assert (await receive())['type'] == 'lifespan.startup'
        await send({'type': 'lifespan.startup.failed', 'message': 'Test startup failure'})

    server = open_studio.StudioServer(uvicorn.Config(
        failed_app, host='127.0.0.1', port=0, lifespan='on',
        access_log=False, log_config=None,
    ))
    try:
        asyncio.run(server.serve())
    except SystemExit as exc:
        # Uvicorn 0.54 exits with code 3; older supported versions return
        # after marking startup as failed instead.
        assert exc.code != 0

    assert not server.started
    assert opened == []
