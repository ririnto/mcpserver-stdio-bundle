# mcpserver-stdio-bundle

Single bundled `shadowJar` artifact that embeds the JetBrains MCP stdio server so MCP clients can talk to the
**JetBrains IDE MCP Server** over **stdio**.

## How it works

MCP Client ⇄ (stdio) ⇄ `mcpserver-stdio-bundle` ⇄ (SSE/HTTP) ⇄ JetBrains IDE MCP Server

This bundle does **not** open its own IDE MCP Server port. It connects to the IDE MCP Server that is already
enabled in your JetBrains IDE.

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
* `mcpserver-stdio-<MCP_VERSION>-bundle.jar`: check `MCP_VERSION` and naming in GitHub Releases.

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

Note: Avoid setting `LC_ALL` unless you have a specific reason. `LC_ALL` overrides other locale settings and can
cause unexpected behavior.

---

## What is `IJ_MCP_SERVER_PORT`?

`IJ_MCP_SERVER_PORT` is the port where your **JetBrains IDE MCP Server** is running (IntelliJ IDEA / PyCharm /
WebStorm / etc.). It is **not** a port opened by this bundle.

You can confirm the port in your IDE:

* **Settings > Tools > MCP Server**

    * **Enable MCP Server:** `http://127.0.0.1:64342/sse`

If your IDE shows a different port, use that value for `IJ_MCP_SERVER_PORT`.

### Important behavior difference (Docker vs Local JAR)

* **Docker image:** `IJ_MCP_SERVER_PORT` defaults to `64342` if you don’t provide it.
* **Local JAR via MCP config:** there is no default. You must set `IJ_MCP_SERVER_PORT` explicitly.

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

### 5) “It runs but nothing happens”

Checklist:

* MCP config uses `"type": "stdio"`.
* (Docker) `-i` is present so stdin/stdout are connected.

---

## Release

Suggested tag scheme:

* `latest`: most recent stable
* `<MCP_VERSION>`: bundled `com.jetbrains.intellij.mcpserver:mcpserver-stdio` dependency version

Where to verify release/tag versioning and artifact naming:

* GitHub Releases: https://github.com/ririnto/mcpserver-stdio-bundle/releases

---

## License

Distributed under the Apache License, Version 2.0, in accordance with the license of the JetBrains
`intellij-community` repository:

* [https://github.com/JetBrains/intellij-community](https://github.com/JetBrains/intellij-community)
