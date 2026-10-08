plugins {
    id("org.springframework.boot") version "3.2.5"
}
java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }
dependencies { implementation("com.baomidou:mybatis-plus-spring-boot3-starter:3.5.5") }
