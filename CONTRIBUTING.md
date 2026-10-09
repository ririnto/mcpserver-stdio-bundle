# Contributing

Open an issue describing the problem and acceptance criteria before changing behavior.
Use the [bug report](.github/ISSUE_TEMPLATE/bug_report.md) or [maintenance template](.github/ISSUE_TEMPLATE/maintenance.md).
Keep changes focused on the agreed scope.
Use synthetic examples and remove credentials, personal paths, and private logs before publishing.

## Build and checks

Install JDK 21 and use the checked-in Gradle wrapper.
Set `MCP_VERSION` to a published dependency version, such as `253.28294.334`.

```sh
MCP_VERSION=253.28294.334
./gradlew --no-daemon clean build -PmcpVersion="$MCP_VERSION"
test -f "build/libs/mcpserver-stdio-${MCP_VERSION}-bundle.jar"
git diff --check
```

This repository bundles an upstream runtime and contains no application source or test suite.
Gradle build success proves packaging, without proving a live IDE connection.
Report commands, outcomes, tested versions, and coverage in the [PR template](.github/pull_request_template.md).
Mark unavailable or excluded checks as NOTRUN with a reason.
Use the [README](README.md#build-from-source) for local JAR and Docker build commands.

For documentation changes, check relative links, JSON examples, and rendered headings, lists, and tables.
For workflow edits, parse YAML and inspect expressions and embedded scripts without executing publication steps.
Preserve release triggers, schedules, permissions, tag formats, artifact names, and image tags unless the issue authorizes changes.
Keep workflow filename consumers consistent when renaming files.
GitHub supports `.yaml` and `.yml` workflow extensions, so use `.yaml` for this repository’s workflows.
See [GitHub’s workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#about-yaml-syntax-for-workflows).
Do not dispatch releases or publish images as a documentation check.

## Writing

Put each complete prose sentence on its own source line.
Separate paragraphs with blank lines and preserve spaces between words.
Keep independent sentences separate instead of joining them with punctuation.
Preserve required code, metadata, quotations, URLs, table syntax, and licenses.
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

Fill the PR template and link the issue and acceptance evidence.
Open an ordinary PR from a feature branch and obtain review of the complete posted changes.
Resolve blockers and satisfy current repository protection requirements before merging.
Confirm the changes on `main` before closing the issue.
Remove completed task branches after verifying that `main` preserves their changes.
