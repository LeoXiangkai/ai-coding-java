---
paths:
  - "**/*.java"
  - "**/pom.xml"
  - "**/build.gradle*"
---

# Java 17+ / Spring Boot 3 差异层

先读 `pom.xml` / `build.gradle*` 判定版本；仅 Java≥17 或 Spring Boot≥3 时适用，否则按 Java 8/Spring Boot 2 习惯。

- Spring Boot 3 / Spring Framework 6 使用 `jakarta.*` 命名空间；迁移时检查 Servlet、Validation、Persistence、注解处理器和测试依赖的一致性。
- `record` 可作稳定的 DTO/VO 边界，但先验证 Jackson、MyBatis 映射、校验注解和框架构造方式；不要把可变实体职责塞进 record。
- 文本块、switch 表达式、模式匹配等语法须符合项目编译级别，并保持异常、null 和可读性约定。
- 虚拟线程启用前检查 `synchronized` pinning、ThreadLocal 生命周期、阻塞调用和连接池大小；线程数变化不能替代数据库容量评估。
- Spring Boot 3 检查自动配置注册文件从 `spring.factories` 到 `AutoConfiguration.imports` 的变化，以及配置属性和 actuator 行为。
- Hibernate 6 迁移检查 SQL 方言、类型映射、查询语义、分页、Lazy 加载和自定义类型；不要仅凭编译通过判断兼容。
