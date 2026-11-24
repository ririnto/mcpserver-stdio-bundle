import json
import os
import re
import shlex
import subprocess
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Final

_WORKFLOWS: Final = Path(__file__).resolve().parents[1] / ".github" / "workflows"
_TAG: Final = "v1.2.3"
_JAR: Final = "mcpserver-stdio-1.2.3-bundle.jar"
_DIGEST: Final = "sha256:" + "a" * 64
_RELEASES: Final = "/repos/fixture/repo/releases"
_DISPATCH: Final = "/repos/fixture/repo/actions/workflows/release-on-tag.yaml/dispatches"
_OUTPUT_REF: Final = re.compile(r"steps\.(?P<step>[\w-]+)\.outputs\.(?P<key>\w+)")


def _workflow(name: str) -> dict:
    return json.loads(subprocess.check_output([
        "ruby", "-r", "yaml", "-r", "json", "-e",
        "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0))))",
        str(_WORKFLOWS / name),
    ]))


class _ReleaseDispatchTest(unittest.TestCase):
    def test_dispatch_and_recovery(self):
        auto_steps = _workflow("auto-tag-upstream.yaml")["jobs"]["tag-if-new"]["steps"]
        dispatch = next(step["run"] for step in auto_steps if "/dispatches" in step.get("run", ""))
        workflow = _workflow("release-on-tag.yaml")
        prepare, *release_steps = workflow["jobs"]["build-and-release"]["steps"]
        push = next(step["name"] for step in release_steps if step.get("with", {}).get("push") is True)
        create = next(step["name"] for step in release_steps if "action-gh-release" in step.get("uses", ""))
        repair = next(step for step in release_steps if "UPLOAD_URL" in step.get("env", {}))
        retag = next(step for step in release_steps if "ALIASES" in step.get("env", {}))

        release = None
        hide_draft = False
        release_error = None
        manifest_error = None
        dispatch_status = 503
        manifests = {}
        dispatches = []
        writes = []

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status, body=None, **headers):
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                if body is not None:
                    self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                if self.path == f"{_RELEASES}/tags/{_TAG}":
                    if release_error:
                        self._send(release_error)
                    elif release is None or (hide_draft and release["draft"]):
                        self._send(404)
                    else:
                        self._send(200, release)
                elif self.path == f"{_RELEASES}?per_page=100&page=1":
                    self._send(200, [release] if release is not None else [])
                elif self.path.startswith("/token?"):
                    self._send(200, {"token": "fixture-pull-token"})
                elif self.path.startswith("/v2/fixture/repo/manifests/"):
                    ref = self.path.rsplit("/", 1)[-1]
                    if manifest_error:
                        self._send(manifest_error)
                    elif ref in manifests:
                        self._send(200, **{"Docker-Content-Digest": manifests[ref]})
                    else:
                        self._send(404, {"errors": [{"code": "MANIFEST_UNKNOWN"}]})
                else:
                    self._send(400)

            def do_POST(self):
                data = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path == _DISPATCH:
                    dispatches.append(json.loads(data))
                    self._send(dispatch_status, "fixture: dispatch unavailable" if dispatch_status == 503 else None)
                elif self.path == f"/upload/42?name={_JAR}":
                    writes.append(("upload", data))
                    if release["assets"]:
                        self._send(422)
                    else:
                        asset = {"name": _JAR, "state": "uploaded", "size": len(data), "id": 7}
                        release["assets"].append(asset)
                        self._send(201, asset)
                else:
                    self._send(400)

            def do_DELETE(self):
                writes.append(("delete", self.path))
                if self.path == f"{_RELEASES}/assets/7" and release["assets"][0]["state"] == "starter":
                    release["assets"].clear()
                    self._send(204)
                else:
                    self._send(400)

            def do_PATCH(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                writes.append(("publish", data))
                if self.path == f"{_RELEASES}/42" and data == {"draft": False} and release["assets"]:
                    release["draft"] = False
                    self._send(200, release)
                else:
                    self._send(400)

            def log_message(self, format, *args):
                pass

        with TemporaryDirectory() as directory, HTTPServer(("127.0.0.1", 0), Handler) as server:
            root = Path(directory)
            gh_output = root / "output"
            (root / "git").write_text("""#!/bin/sh
set -eu
printf '%s\\n' "$*" >> git.log
case "$1" in
  ls-remote)
    if [ ! -f tagged ]; then
      exit 2
    fi
    ;;
  config|tag) ;;
  push) touch tagged ;;
  *) exit 99 ;;
esac
""")
            (root / "docker").write_text("""#!/bin/sh
set -eu
printf '%s\\n' "$*" >> docker.log
""")
            (root / "git").chmod(0o700)
            (root / "docker").chmod(0o700)
            bundle = root / "build" / "libs" / _JAR
            bundle.parent.mkdir(parents=True)
            bundle.write_bytes(b"fixture-bundle")
            api = f"http://127.0.0.1:{server.server_port}"
            thread = Thread(target=server.serve_forever)
            thread.start()

            def run(step: str, **variables):
                gh_output.write_text("")
                return subprocess.run(
                    ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step],
                    cwd=root,
                    env={
                        **workflow["env"],
                        "PATH": f"{root}:{os.environ['PATH']}",
                        "HOME": directory,
                        "GITHUB_API_URL": api,
                        "GITHUB_REPOSITORY": "fixture/repo",
                        "GITHUB_OUTPUT": str(gh_output),
                        "GITHUB_ACTOR": "fixture",
                        "GH_TOKEN": "fixture-token",
                        "REGISTRY_URL": api,
                        "http_proxy": "http://127.0.0.1:1",
                        "https_proxy": "http://127.0.0.1:1",
                        "no_proxy": "127.0.0.1",
                        **variables,
                    },
                    text=True, capture_output=True, timeout=10,
                )

            def plan(event="workflow_dispatch"):
                result = run(prepare["run"], GITHUB_EVENT_NAME=event,
                             INPUT_TAG=_TAG if event == "workflow_dispatch" else "",
                             GITHUB_REF_NAME="main" if event == "workflow_dispatch" else _TAG)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs = dict(line.split("=", 1) for line in gh_output.read_text().splitlines())
                self.assertEqual(outputs["tag"], _TAG)
                self.assertEqual(outputs["jar"], _JAR)

                def output_value(match):
                    self.assertEqual(match["step"], prepare["id"])
                    return outputs.get(match["key"], "")

                selected = set()
                for step in release_steps:
                    condition = _OUTPUT_REF.sub(lambda match: shlex.quote(output_value(match)), step["if"][3:-2])
                    checked = run(f"[[ {condition} ]]")
                    self.assertIn(checked.returncode, (0, 1), checked.stderr)
                    if checked.returncode == 0:
                        selected.add(step["name"])
                return selected, outputs

            def run_step(step, outputs):
                env = {
                    key: _OUTPUT_REF.sub(lambda match: outputs.get(match["key"], ""), value[3:-2].strip())
                    for key, value in step["env"].items() if value.startswith("${{ steps.")
                }
                checked = run(step["run"], **env)
                self.assertEqual(checked.returncode, 0, checked.stderr)

            try:
                failed = run(dispatch, TAG=_TAG)
                self.assertNotEqual(failed.returncode, 0, "HTTP 503 must fail the dispatch step")
                self.assertIn("503", failed.stderr)
                self.assertIn("fixture: dispatch unavailable", failed.stdout)
                self.assertTrue((root / "tagged").exists())

                dispatch_status = 204
                retried = run(dispatch, TAG=_TAG)
                self.assertEqual(retried.returncode, 0, retried.stderr)
                self.assertEqual(dispatches, [{"ref": "main", "inputs": {"tag": _TAG}}] * 2)
                selected, _ = plan()
                self.assertTrue({push, create} <= selected)

                manifests.update({"1.2.3": _DIGEST, _TAG: _DIGEST, "latest": _DIGEST})
                selected, _ = plan()
                self.assertIn(create, selected)
                self.assertNotIn(push, selected)

                for draft, hide_draft, asset_state, expected_writes in (
                    (True, False, None, ["upload", "publish"]),
                    (True, True, "uploaded", ["publish"]),
                    (True, True, "starter", ["delete", "upload", "publish"]),
                    (False, False, None, ["upload"]),
                ):
                    with self.subTest(draft=draft, hidden=hide_draft, asset=asset_state):
                        manifests["latest"] = _DIGEST if draft else "sha256:" + "b" * 64
                        release = {
                            "id": 42, "tag_name": _TAG, "draft": draft, "immutable": False,
                            "upload_url": api + "/upload/42{?name,label}", "assets": [],
                        }
                        if asset_state:
                            release["assets"].append({
                                "name": _JAR, "state": asset_state, "id": 7,
                                "size": 10 if asset_state == "uploaded" else 0,
                            })
                        before = len(dispatches)
                        retried = run(dispatch, TAG=_TAG)
                        self.assertEqual(retried.returncode, 0, retried.stderr)
                        self.assertEqual(len(dispatches), before + 1)

                        selected, outputs = plan("push")
                        self.assertIn(repair["name"], selected)
                        self.assertNotIn(create, selected)
                        self.assertNotIn(push, selected)
                        self.assertNotIn(retag["name"], selected)
                        writes.clear()
                        run_step(repair, outputs)
                        self.assertEqual([operation for operation, _ in writes], expected_writes)
                        self.assertFalse(release["draft"])
                        self.assertEqual(release["assets"][0]["state"], "uploaded")

                        self.assertEqual(plan()[0], set())
                        after_publish = run(dispatch, TAG=_TAG)
                        self.assertEqual(after_publish.returncode, 0, after_publish.stderr)
                        self.assertEqual(len(dispatches), before + 1)

                release = None
                manifests["latest"] = _DIGEST
                manifests.pop("1.2.3")
                selected, outputs = plan()
                self.assertNotIn(push, selected)
                self.assertIn(retag["name"], selected)
                run_step(retag, outputs)
                self.assertEqual((root / "docker.log").read_text().splitlines(), [
                    f"buildx imagetools create --tag ghcr.io/fixture/repo:1.2.3 ghcr.io/fixture/repo@{_DIGEST}",
                ])

                for state, error in (
                    ("lookup", "403"),
                    ("conflict", "point to different digests"),
                    ("latest", "registry state cannot show"),
                    ("immutable", "Immutable GitHub release 42"),
                ):
                    with self.subTest(blocker=state):
                        manifest_error = 403 if state == "lookup" else None
                        other = "sha256:" + "b" * 64
                        manifests["1.2.3"] = other if state == "conflict" else _DIGEST
                        manifests["latest"] = other if state == "latest" else _DIGEST
                        if state == "immutable":
                            release = {
                                "id": 42, "tag_name": _TAG, "draft": False, "immutable": True, "assets": [],
                            }
                        blocked = run(prepare["run"], GITHUB_EVENT_NAME="workflow_dispatch", INPUT_TAG=_TAG)
                        self.assertNotEqual(blocked.returncode, 0)
                        self.assertIn(error, blocked.stderr)
                        self.assertEqual(gh_output.read_text(), "")

                release_error = 403
                lookup_failed = run(dispatch, TAG=_TAG)
                self.assertNotEqual(lookup_failed.returncode, 0)
                self.assertIn("403", lookup_failed.stderr)
            finally:
                server.shutdown()
                thread.join()

            git_calls = (root / "git.log").read_text().splitlines()
            self.assertEqual([call.split()[2] for call in git_calls if call.startswith("tag -a ")], [_TAG])
            self.assertEqual([call for call in git_calls if call.startswith("push ")],
                             [f"push origin refs/tags/{_TAG}"])


if __name__ == "__main__":
    for workflow in sorted(_WORKFLOWS.glob("*.yml")):
        raise SystemExit(f".github/workflows/{workflow.name}: workflow filenames must use .yaml")
    unittest.main(verbosity=2)
