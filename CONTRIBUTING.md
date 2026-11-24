# Contributing

Issues are optional for implementation, pull requests, and integration.
Without an issue, record the problem, scope, and acceptance in the task or PR.
Use the [bug report](.github/ISSUE_TEMPLATE/bug_report.yaml) or [maintenance template](.github/ISSUE_TEMPLATE/maintenance.yaml).
Keep changes focused on the agreed scope.
Use synthetic examples and remove credentials, personal paths, and private logs before publishing.

## Build and checks

Install JDK 21, set `JAVA_HOME` to its installation directory, and use the checked-in Gradle wrapper.
Install Python 3.11 or later for the stdio smoke check.
Set `MCP_VERSION` to a published dependency version, such as `253.28294.334`.

```sh
MCP_VERSION=253.28294.334
./gradlew --no-daemon clean build -PmcpVersion="$MCP_VERSION"
test -f "build/libs/mcpserver-stdio-${MCP_VERSION}-bundle.jar"
python3 tests/stdio_smoke.py --java "$JAVA_HOME/bin/java" "build/libs/mcpserver-stdio-${MCP_VERSION}-bundle.jar"
git diff --check
```

This repository bundles an upstream runtime.
The smoke check runs the built JAR against a loopback SSE fixture.
It checks MCP initialization and a clean process exit after stdin closes.
Report commands, outcomes, tested versions, and coverage in the [PR template](.github/pull_request_template.md).
Mark unavailable or excluded checks as NOTRUN with a reason.
Use the [README](README.md#build-from-source) for local JAR and Docker build commands.

For documentation changes, check:

- Relative links
- JSON examples
- Rendered headings, lists, and tables

For workflow edits, parse YAML and inspect expressions and embedded scripts without executing publication steps.
Run `python3 tests/release_dispatch.py` with Ruby, Bash, curl, and jq installed to check release dispatch and partial-publication recovery against a loopback fixture.
Unless the task authorizes a change, preserve these release settings:

- Triggers and schedules
- Permissions
- Tag formats
- Artifact names
- Image tags

Keep workflow filename consumers consistent when renaming files.
GitHub supports `.yaml` and `.yml` workflow extensions, so use `.yaml` for this repository’s workflows.
See [GitHub’s workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#about-yaml-syntax-for-workflows).
Do not dispatch releases or publish images as a documentation check.

## Writing

Put each complete prose sentence on its own source line.
Separate paragraphs with blank lines and preserve spaces between words.
Keep independent sentences separate instead of joining them with punctuation.
Preserve required content and syntax:

- Code
- Metadata
- Quotations
- URLs
- Table syntax
- Licenses

Exclude generated files and the Gradle wrapper from mechanical writing changes.
Apply these rules to maintained documentation, contributor guidance, issue and PR prose, and commit bodies.

## Commits and pull requests

Use a short commit title followed by a blank line and a substantive body.
Explain the reason, changes, actual checks, and material limitations.

```text
docs: explain versioned bundle builds

Readers need the required dependency property and the generated artifact path.
Document JDK 21 and the versioned Docker build argument.
Validate relative links and JSON examples.
Live IDE and Docker integration checks are NOTRUN because this change covers documentation.
```

Fill the PR template, record acceptance evidence, and link an issue when one exists.
Open an ordinary PR from a feature branch and obtain review of the complete posted changes.
Resolve blockers and satisfy current repository protection requirements before merging.
Confirm the changes on `main` before closing any related issue.
Remove completed task branches after verifying that `main` preserves their changes.
