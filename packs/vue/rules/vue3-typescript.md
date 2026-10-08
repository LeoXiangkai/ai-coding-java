---
paths:
  - "**/*.vue"
  - "**/*.ts"
  - "**/*.tsx"
---

# Vue 3 + TypeScript 规则

## 组件与类型

- 主线按 Vue 3、Vite、TypeScript、Element Plus、Pinia 处理；项目已有约定优先，组件命名和目录布局沿用项目。
- 使用 `<script setup lang="ts">`。`defineProps`、`defineEmits` 必须使用明确的类型声明，公共导出也要有可读类型。
- `ref`、`reactive` 解构时确认响应性没有丢失；需要解构时使用 `toRefs`，Pinia store 解构使用 `storeToRefs`。
- 组件保持单一职责，局部交互状态留在组件；跨组件共享状态进入 Pinia store，store 负责业务状态和操作，不把纯组件状态塞入 store。

## 响应式与模板

- `watch` 明确监听源、清理函数和 `immediate` 是否符合业务初始加载语义；副作用必须在失效时取消或释放。
- `computed` 只做派生计算，不在 getter 中发请求、写状态或执行其他副作用。
- `v-for` 使用稳定且唯一的业务 key，不使用数组下标；不要把 `v-for` 和 `v-if` 放在同一元素上，先在计算属性中过滤数据。
- `v-html` 只接受经过可信净化的内容；用户输入不得直接拼接 HTML。前端不保存密钥，敏感凭据由后端代理。

## 依赖与接口

- Element Plus 按项目既有方式按需引入；表单校验集中定义 `rules`，提交前后都处理校验结果和服务端错误。
- API 请求统一通过项目的客户端封装，组件不散写原始 URL。错误码按统一约定处理；blob 下载失败时检查响应 `Content-Type` 是否以 `application/json` 开头，再解析错误体，不能只做全等比较。
- 路由守卫和前端权限判断只改善体验，后端必须重新校验身份、权限和数据范围。
- 避免渲染阶段重计算，稳定派生值使用 `computed`；不无故引入第二套状态、样式或请求库。

## 可维护性与验证

- 关键用户路径覆盖行为测试，不用快照替代业务断言；按钮、链接和表单控件保留可访问名称与焦点状态。
- 规则只约束 Vue/TypeScript 文件；项目级 `eslint`、`vue-tsc` 和既有构建约定优先。
