---
paths:
  - "**/*.vue"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
---

# Vue 2 兼容规则

先读 `package.json` 判定：仅 Vue 主版本为 2 时适用。不要因为命中本文件就主动迁移到 Vue 3。

- 沿用项目的 Options API、生命周期和组件目录约定；不要在同一改动中混入 Composition API，除非项目已有兼容方案。
- Vue 2 对新增/删除对象属性和数组索引的响应性有限，使用 `Vue.set`、`this.$set` 或返回新对象/数组，避免静默失去更新。
- Vuex 按现有模块边界组织 state、getters、mutations、actions；组件局部状态不为迁移方便而塞入 Vuex。
- 使用 Element-UI 的既有 API 和样式约定；核对它与 Element Plus 在表单、弹层、分页和事件名上的差异，不直接复制 Vue 3 示例。
- 遵循 vue-cli 的配置、代理和构建脚本；不要把 Vite 配置写入 Vue 2 项目。
- Vue 2 过滤器在迁移到 Vue 3 时已移除；新增代码优先使用方法或计算属性，但当前维护仍需保持既有行为。
- 仍应使用稳定 `v-for` key、统一 API 封装、输入净化和后端权限校验；这些安全与数据边界不因 Vue 版本改变。
