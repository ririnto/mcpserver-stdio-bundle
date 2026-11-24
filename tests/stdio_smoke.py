import json
import subprocess
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Event, Thread
from typing import Final

_TIMEOUT: Final = 15
_PROTOCOL_VERSION: Final = "2024-11-05"
_SERVER_NAME: Final = "loopback-fixture"


def _smoke(jar: Path, java: Path) -> None:
    response = SimpleQueue()
    initialized = Event()
    stop = Event()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(_TIMEOUT)
            super().setup()

        def do_GET(self):
            if self.path != "/sse":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"event: endpoint\ndata: /message\n\n")
            try:
                message = response.get(timeout=_TIMEOUT)
            except Empty:
                return
            if message is not None:
                self.wfile.write(f"event: message\ndata: {json.dumps(message)}\n\n".encode())
                stop.wait()

        def do_POST(self):
            if self.path != "/message":
                self.send_error(404)
                return
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            method = request.get("method")
            if method not in ("initialize", "notifications/initialized"):
                self.send_error(400)
                return
            self.send_response(202)
            self.end_headers()
            if method == "initialize":
                response.put({
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "protocolVersion": request["params"]["protocolVersion"],
                        "capabilities": {},
                        "serverInfo": {"name": _SERVER_NAME, "version": "1"},
                    },
                })
            else:
                initialized.set()

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.daemon_threads = False
        thread = Thread(target=server.serve_forever)
        thread.start()
        port = server.server_port
        try:
            command = [str(java), "-jar", str(jar)]
            with ThreadPoolExecutor(max_workers=1) as stdout_reader, subprocess.Popen(
                command,
                env={"IJ_MCP_SERVER_PORT": str(port)},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            ) as process:
                try:
                    print(f"Running {command!r} (PID {process.pid}, fixture 127.0.0.1:{port})", flush=True)
                    process.stdin.write(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": _PROTOCOL_VERSION,
                            "capabilities": {},
                            "clientInfo": {"name": "stdio-smoke", "version": "1"},
                        },
                    }) + "\n")
                    process.stdin.flush()
                    try:
                        line = stdout_reader.submit(process.stdout.readline).result(timeout=_TIMEOUT)
                    except TimeoutError:
                        raise SystemExit(f"{jar}: timed out waiting for the stdio initialize response")
                    try:
                        reply = json.loads(line)
                        initialized_by_fixture = (
                            reply["jsonrpc"] == "2.0"
                            and reply["id"] == 1
                            and "error" not in reply
                            and reply["result"]["protocolVersion"] == _PROTOCOL_VERSION
                            and reply["result"]["serverInfo"]["name"] == _SERVER_NAME
                        )
                    except (KeyError, TypeError, ValueError):
                        initialized_by_fixture = False
                    if not initialized_by_fixture:
                        raise SystemExit(f"{jar}: unexpected stdio initialize response {line!r}")
                    print(f"Received initialize result: {line.strip()}", flush=True)
                    process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                    process.stdin.flush()
                    if not initialized.wait(_TIMEOUT):
                        raise SystemExit(f"{jar}: fixture did not receive notifications/initialized")
                    if process.poll() is not None:
                        raise SystemExit(f"{jar}: exited before stdin EOF")
                    process.stdin.close()
                    try:
                        code = process.wait(timeout=_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        raise SystemExit(f"{jar}: did not exit after stdin EOF within {_TIMEOUT} seconds")
                    if code != 0:
                        raise SystemExit(f"{jar}: exited with status {code} after stdin EOF")
                    print(f"PID {process.pid} exited with status 0 after stdin EOF", flush=True)
                finally:
                    if process.poll() is None:
                        process.kill()
        finally:
            response.put(None)
            stop.set()
            server.shutdown()
            thread.join()
    print(f"Fixture listener 127.0.0.1:{port} closed")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Exercise the bundle's stdio lifecycle against a loopback SSE server."
    )
    parser.add_argument("jar", type=Path)
    parser.add_argument("--java", type=Path, required=True)
    args = parser.parse_args()
    if not args.jar.is_file():
        parser.error(f"bundle JAR does not exist: {args.jar}")
    _smoke(args.jar.resolve(), args.java.resolve())
