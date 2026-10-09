# mcpserver-stdio-bundle

Use this bundled `shadowJar` artifact to connect MCP clients to the **JetBrains IDE MCP Server** over **stdio**.

## How it works

MCP Client ⇄ (stdio) ⇄ `mcpserver-stdio-bundle` ⇄ (SSE/HTTP) ⇄ JetBrains IDE MCP Server

Enable the IDE MCP Server in your JetBrains IDE before starting this bundle.
The bundle connects to that server and opens no IDE MCP Server port.

Based on:

* `com.jetbrains.intellij.mcpserver:mcpserver-stdio`
* [https://mvnrepository.com/artifact/com.jetbrains.intellij.mcpserver/mcpserver-stdio](https://mvnrepository.com/artifact/com.jetbrains.intellij.mcpserver/mcpserver-stdio)

---

## Quick Start (MCP Config)

Minimal MCP config examples for running this bundle via **stdio**.

### Local JAR (recommended for direct exec)

Run a prebuilt artifact directly.

* Set `IJ_MCP_SERVER_PORT` to the **JetBrains IDE MCP Server** port.
* Use an **absolute path** to the JAR.
* Java runtime must be **JDK 21+**.
* Check [GitHub Releases](https://github.com/ririnto/mcpserver-stdio-bundle/releases) for `mcpserver-stdio-<MCP_VERSION>-bundle.jar`.

```json
{
  "server": {
    "jetbrains": {
      "type": "stdio",
      "command": "java",
      "env": {
        "IJ_MCP_SERVER_PORT": "64342"
      },
      "args": [
        "-jar",
        "/absolute/path/to/mcpserver-stdio-<MCP_VERSION>-bundle.jar"
      ]
    }
  }
}
```

### Docker (GHCR)

* `--network host` is required so the container can reach the **JetBrains IDE MCP Server** on the host.
* Use Docker Engine on Linux, or enable host networking in Docker Desktop 4.34 or later.
* Follow the [Docker host networking setup and limitations](https://docs.docker.com/engine/network/drivers/host/).
* Without host networking, `127.0.0.1` refers to the container and cannot reach your host IDE.
* Prefer the Local JAR configuration if your Docker setup cannot share host networking.
* Set `IJ_MCP_SERVER_PORT` explicitly to match your IDE configuration.
* `TZ` and `LANG` are optional but help with consistent timestamps and UTF-8 output.

```json
{
  "server": {
    "jetbrains": {
      "type": "stdio",
      "command": "docker",
      "env": {
        "IJ_MCP_SERVER_PORT": "64342",
        "TZ": "Asia/Seoul",
        "LANG": "en_US.UTF-8"
      },
      "args": [
        "run",
        "--rm",
        "-i",
        "--network",
        "host",
        "-e",
        "IJ_MCP_SERVER_PORT",
        "-e",
        "TZ",
        "-e",
        "LANG",
        "ghcr.io/ririnto/mcpserver-stdio-bundle:latest"
      ]
    }
  }
}
```

Avoid setting `LC_ALL` unless you need to override the other locale settings.
That override can cause unexpected behavior.

---

## What is `IJ_MCP_SERVER_PORT`?

`IJ_MCP_SERVER_PORT` identifies your running **JetBrains IDE MCP Server** port, for example in IntelliJ IDEA, PyCharm, or WebStorm.
This bundle opens no port of its own.

You can confirm the port in your IDE:

* **Settings > Tools > MCP Server**

    * **Enable MCP Server:** `http://127.0.0.1:64342/sse`

If your IDE shows a different port, use that value for `IJ_MCP_SERVER_PORT`.

### Important behavior difference (Docker vs Local JAR)

* **Docker image:** `IJ_MCP_SERVER_PORT` defaults to `64342` if you don’t provide it.
* **Local JAR via MCP config:** set `IJ_MCP_SERVER_PORT` because the configuration supplies no default.

---

## Requirements

* **JDK 21+** (required for the Local JAR config)

---

## Troubleshooting

### 1) `UnsupportedClassVersionError` / Java version mismatch

Symptoms:

* `UnsupportedClassVersionError`
* Startup fails due to class file version

Fix:

* Ensure the runtime is **JDK 21+**.

### 2) JAR path not found (Local JAR)

Symptoms:

* `Error: Unable to access jarfile ...`
* `NoSuchFileException`

Fix:

* Use an absolute path in your MCP config.
* Confirm the file name matches what you built: `mcpserver-stdio-<MCP_VERSION>-bundle.jar`

### 3) Wrong `IJ_MCP_SERVER_PORT` (most common)

Symptoms:

* The bundle starts but cannot communicate with the **JetBrains IDE MCP Server**.
* Connection errors or immediate exit (depending on client behavior).

Fix:

* Verify the port in your IDE:

    * **Settings > Tools > MCP Server**
    * **Enable MCP Server:** `http://127.0.0.1:64342/sse`
* Set `IJ_MCP_SERVER_PORT` to that port (e.g., `64342`).

### 4) Docker networking issues

Symptoms:

* Works locally, fails in Docker.
* Container cannot reach the **JetBrains IDE MCP Server**.

Fix:

* Ensure `--network host` is present (required for this setup).
* Check the platform requirements and fallback in [Docker configuration](#docker-ghcr).

### 5) “It runs but nothing happens”

Checklist:

* MCP config uses `"type": "stdio"`.
* Include Docker’s `-i` option to connect stdin and stdout.

---

## Build from source

Install JDK 21 and use the checked-in Gradle wrapper.
Choose a published `mcpserver-stdio` dependency version, such as `253.28294.334`.
The build requires `-PmcpVersion` and has no default dependency version.

```sh
MCP_VERSION=253.28294.334
./gradlew --no-daemon clean shadowJar -PmcpVersion="$MCP_VERSION"
test -f "build/libs/mcpserver-stdio-${MCP_VERSION}-bundle.jar"
```

Gradle writes `build/libs/mcpserver-stdio-<MCP_VERSION>-bundle.jar` with its dependencies and merged service files.
Run that JAR using the Local JAR configuration above.

For a local Docker build, pass the versioned JAR path to `JAR_FILE`:

```sh
docker build \
  --build-arg "JAR_FILE=build/libs/mcpserver-stdio-${MCP_VERSION}-bundle.jar" \
  -t "mcpserver-stdio-bundle:${MCP_VERSION}" .
```

The Dockerfile’s default `JAR_FILE` omits the version and differs from the Gradle output.
The release workflow supplies this build argument.
A successful build does not verify a live IDE connection.

---

## Release

Use Git tags named `v<MCP_VERSION>`, for example `v253.28294.334`.
The release workflow removes `v` before passing the dependency version to Gradle.
It publishes the versioned bundle JAR and Linux amd64/arm64 Docker images.

| Reference | Meaning |
| :--- | --- |
| Git tag `v<MCP_VERSION>` | The release workflow builds this tagged source. |
| Image tag `<MCP_VERSION>` | Use this tag for the bundled dependency version. |
| Image tag `v<MCP_VERSION>` | Use this alias matching the Git tag. |
| Image tag `latest` | The release workflow updates this alias on each successful image publication. |

The [auto-tag workflow](.github/workflows/auto-tag-upstream.yaml) checks upstream metadata every 12 hours.
For a new version, it creates a Git tag and dispatches the [release workflow](.github/workflows/release-on-tag.yaml).
The release workflow also accepts tag pushes and manual dispatch with a tag input.
Inspect [GitHub Releases](https://github.com/ririnto/mcpserver-stdio-bundle/releases) for published versions and artifact names.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for checks, writing conventions, and issue and PR templates.

---

## License

Distributed under the Apache License, Version 2.0, in accordance with the license of the JetBrains `intellij-community` repository:

* [https://github.com/JetBrains/intellij-community](https://github.com/JetBrains/intellij-community)
