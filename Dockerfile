FROM gcr.io/distroless/java21-debian13:nonroot

WORKDIR /app

ENV IJ_MCP_SERVER_PORT=64342

ARG JAR_FILE=build/libs/mcpserver-stdio-bundle.jar
COPY ${JAR_FILE} /app/app.jar

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
