---
paths:
  - "**/*Mapper*.java"
  - "**/*Dao*.java"
  - "**/*.xml"
  - "**/*.sql"
---

# Java SQL / MyBatis 规则

- MyBatis `${}` 只允许经过白名单映射的排序、分组或字段片段；普通值使用 `#{}`，不得把未校验输入直接拼进 SQL。
- `update`、`delete` 必须有业务 `where` 和数据隔离条件；批量 `foreach` 校验空集合、批次大小和参数类型。
- 列表查询使用分页插件或明确的 limit；检查一对多分页结果、关联基数和潜在 N+1，避免无界 `select *`。
- LambdaWrapper 的字段类型与常量类型保持一致，避免 `equals` 恒为 false；逻辑删除字段、租户/组织/区域等隔离条件遵循项目约定。
- DDL、entity、Mapper/XML 的字段、类型、默认值和逻辑删除语义对齐；变更需考虑索引、回滚和目标环境。
- MyBatis-Plus 的分页、批量和逻辑删除使用项目既有配置与拦截器，不能假定插件在所有模块自动生效。
- 检测到 JPA 时按其约定，本规则不展开。
