plugins {
    kotlin("jvm") version "2.2.21"
    id("com.gradleup.shadow") version "9.3.0"
}

group = "com.jetbrains.intellij.mcpserver"

repositories {
    mavenCentral()
    maven("https://www.jetbrains.com/intellij-repository/releases")
    maven("https://packages.jetbrains.team/maven/p/ij/intellij-dependencies")
}

val mcpVersion: String = findProperty("mcpVersion") as? String
    ?: error("Missing -PmcpVersion=... (example: -PmcpVersion=253.28294.334)")

dependencies {
    runtimeOnly("com.jetbrains.intellij.mcpserver:mcpserver-stdio:${mcpVersion}")
}

tasks {
    jar {
        enabled = false
    }
    shadowJar {
        isZip64 = true
        archiveBaseName.set("mcpserver-stdio")
        archiveClassifier.set("bundle")
        archiveVersion.set(mcpVersion)
        mergeServiceFiles()
        manifest {
            attributes["Main-Class"] = "com.intellij.mcpserver.stdio.McpStdioRunnerKt"
        }
    }
    test {
        useJUnitPlatform()
    }
    build {
        dependsOn(shadowJar)
    }
}

kotlin {
    jvmToolchain(21)
}
