import json
import re
import subprocess
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Final

_WORKFLOWS: Final = Path(__file__).resolve().parents[1] / ".github" / "workflows"
_TAG: Final = "v1.2.3"


def _workflow(name: str) -> dict:
    return json.loads(subprocess.check_output([
        "ruby", "-r", "yaml", "-r", "json", "-e",
        "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0))))",
        str(_WORKFLOWS / name),
    ]))


class _ReleaseDispatchTest(unittest.TestCase):
    def test_recovers_after_dispatch_failure_and_skips_published_release(self):
        auto_steps = _workflow("auto-tag-upstream.yaml")["jobs"]["tag-if-new"]["steps"]
        dispatch = next(step["run"] for step in auto_steps if "/dispatches" in step.get("run", ""))
        release_workflow = _workflow("release-on-tag.yaml")
        prepare, *publish = release_workflow["jobs"]["build-and-release"]["steps"]
        conditions = {step.get("if", "") for step in publish}
        self.assertEqual(len(conditions), 1, "All publication steps must use the same gate")
        gate = re.fullmatch(
            r"\$\{\{\s*steps\.(?P<step>\w+)\.outputs\.(?P<output>\w+) == '(?P<value>\w+)'\s*\}\}",
            conditions.pop(),
        )
        self.assertIsNotNone(gate, "Publication must depend on a release lookup output")
        self.assertEqual(gate["step"], prepare["id"])

        release_status = 404
        dispatch_status = 503
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(release_status)
                self.end_headers()

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, payload))
                self.send_response(dispatch_status)
                self.end_headers()
                if dispatch_status == 503:
                    self.wfile.write(b"fixture: dispatch unavailable")

            def log_message(self, format, *args):
                pass

        with TemporaryDirectory() as directory, HTTPServer(("127.0.0.1", 0), Handler) as server:
            gh_output = Path(directory) / "output"
            git = Path(directory) / "git"
            git.write_text("""#!/bin/sh
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
            git.chmod(0o700)
            thread = Thread(target=server.serve_forever)
            thread.start()

            def run(step: str, **variables):
                gh_output.write_text("")
                return subprocess.run(
                    ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step],
                    cwd=directory,
                    env={
                        "PATH": f"{directory}:/usr/bin:/bin",
                        "HOME": directory,
                        "GITHUB_API_URL": f"http://127.0.0.1:{server.server_port}",
                        "GITHUB_REPOSITORY": "fixture/repo",
                        "GITHUB_OUTPUT": str(gh_output),
                        "GH_TOKEN": "fixture-token",
                        "http_proxy": "http://127.0.0.1:1",
                        "https_proxy": "http://127.0.0.1:1",
                        "no_proxy": "127.0.0.1",
                        **variables,
                    },
                    text=True, capture_output=True, timeout=10,
                )

            try:
                failed = run(dispatch, TAG=_TAG)
                self.assertNotEqual(failed.returncode, 0, "HTTP 503 must fail the dispatch step")
                self.assertIn("503", failed.stderr)
                self.assertIn("fixture: dispatch unavailable", failed.stdout)
                self.assertTrue((Path(directory) / "tagged").exists())

                dispatch_status = 204
                retried = run(dispatch, TAG=_TAG)
                self.assertEqual(retried.returncode, 0, retried.stderr)

                for release_status, event, input_tag, ref in (
                    (404, "workflow_dispatch", _TAG, "main"),
                    (200, "push", "", _TAG),
                ):
                    checked = run(
                        prepare["run"], **release_workflow["env"],
                        GITHUB_EVENT_NAME=event, INPUT_TAG=input_tag, GITHUB_REF_NAME=ref,
                    )
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    outputs = dict(line.split("=", 1) for line in gh_output.read_text().splitlines())
                    self.assertEqual(outputs["tag"], _TAG)
                    self.assertEqual(outputs["jar"], "mcpserver-stdio-1.2.3-bundle.jar")
                    self.assertEqual(outputs[gate["output"]] == gate["value"], release_status == 404)

                after_publish = run(dispatch, TAG=_TAG)
                self.assertEqual(after_publish.returncode, 0, after_publish.stderr)

                release_status = 403
                lookup_failed = run(dispatch, TAG=_TAG)
                self.assertNotEqual(lookup_failed.returncode, 0)
                self.assertIn("403", lookup_failed.stderr)
            finally:
                server.shutdown()
                thread.join()

            lookup = f"/repos/fixture/repo/releases/tags/{_TAG}"
            post = ("/repos/fixture/repo/actions/workflows/release-on-tag.yaml/dispatches",
                    {"ref": "main", "inputs": {"tag": _TAG}})
            self.assertEqual(requests, [lookup, post, lookup, post, lookup, lookup, lookup, lookup])
            git_calls = (Path(directory) / "git.log").read_text().splitlines()
            self.assertEqual([call.split()[2] for call in git_calls if call.startswith("tag -a ")], [_TAG])
            self.assertEqual([call for call in git_calls if call.startswith("push ")],
                             [f"push origin refs/tags/{_TAG}"])


if __name__ == "__main__":
    for workflow in sorted(_WORKFLOWS.glob("*.yml")):
        raise SystemExit(f".github/workflows/{workflow.name}: workflow filenames must use .yaml")
    unittest.main(verbosity=2)
