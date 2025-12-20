# mcpserver-stdio-bundle

Single shadowJar build that bundles the JetBrains MCP stdio server so you can communicate with the
JetBrains MCP server over stdio. Built on `com.jetbrains.intellij.mcpserver:mcpserver-stdio` from
https://mvnrepository.com/artifact/com.jetbrains.intellij.mcpserver/mcpserver-stdio.

## Requirements

- JDK 21

## Build

Build the bundle (you must provide `-PmcpVersion`):

```bash
./gradlew -PmcpVersion=253.28294.334 shadowJar
````

## Output

The bundled artifact is written to:

```
build/libs/mcpserver-stdio-<mcpVersion>-bundle.jar
```

## Run

The JAR runs the stdio MCP server entry point:

```bash
java -jar build/libs/mcpserver-stdio-<mcpVersion>-bundle.jar
```

## License

Distributed under the Apache License, Version 2.0, in accordance with the license of the
[https://github.com/JetBrains/intellij-community](https://github.com/JetBrains/intellij-community) repository.
