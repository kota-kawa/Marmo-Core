---
name: "standards-gen"
description: "当用户说'生成规范'、'定标准'、'我们的组件规范是什么'时触发。基于扫描报告，为当前项目生成具体可执行的 Vue 组件规范文档。"
---

# Vue 组件规范生成器

## 目标

读取扫描报告，结合 Vue 3 最佳实践，为**这个具体项目**生成一份落地的规范文档。

> 规范不是照搬官方文档，而是基于项目现状做出的取舍。
> 脱离现状的规范没人遵守。

---

## 第零步：读取扫描报告

用 Read 工具读取 `codebase-scan-report.md`。

如果文件不存在，告知用户：「请先运行 /codebase-scan 获取项目现状数据。」

从报告中提取：
- 当前主流 API 风格（Options / Composition / 混用）
- 超大组件的典型规模（用于定义合理的大小上限）
- 重复逻辑类型（用于决定提取哪些 composable）
- 目录组织方式

---

## 第一步：确定迁移策略

根据 API 风格分布，决定规范的基调：

| 现状 | 建议策略 |
|------|---------|
| 全部 Options API | 新文件用 Composition API，旧文件逐步迁移 |
| 已有部分 Composition | 统一向 Composition API 靠拢，禁止新增 Options API |
| 已全部 Composition | 直接定标准，无需迁移策略 |

---

## 第二步：生成六项核心规范

### 规范一：组件大小限制

根据扫描报告中超大组件的现状，设定合理的上限：
- `<template>` 不超过 **150 行**（超出考虑拆子组件）
- `<script setup>` 不超过 **200 行**（超出考虑提取 composable）
- 单个组件文件总行数不超过 **400 行**

给出判断方法：「用 `wc -l` 或编辑器行数统计快速评估」

---

### 规范二：组件分层（原子化标准）

按职责定义四层，每层有明确的判断标准：

```
atoms/          ← 原子：无业务逻辑，纯 UI，可跨项目复用
                  判断：没有 API 调用，没有 store 引用，只有 props/emits
                  例：Button、Input、Tag、Badge、Icon

molecules/      ← 分子：由多个原子组合，有简单交互逻辑
                  判断：组合 2+ 个原子，自身有状态，但无 API 调用
                  例：SearchBar、FormField、UserAvatar

organisms/      ← 有机体：承载业务逻辑，可调用 API 或 store
                  判断：有 API 调用 或 有 store 引用
                  例：UserForm、OrderList、ProductCard

pages/          ← 页面：只做布局组合，逻辑下沉到 organisms 和 composables
                  判断：只包含 <router-view> 和 organism 组件的组合
```

---

### 规范三：Composable 提取标准

以下情况**必须**提取为 composable：

| 场景 | composable 命名 |
|------|----------------|
| 相同的 API 调用逻辑出现在 2+ 个组件 | `useXxxApi()` |
| 分页逻辑 | `usePagination()` |
| 表单验证逻辑 | `useXxxForm()` |
| 加载状态 + 错误状态管理 | `useAsync()` |
| localStorage / sessionStorage 读写 | `useStorage()` |
| 定时器逻辑 | `useInterval()` / `useTimeout()` |

Composable 文件放在 `src/composables/` 下，命名以 `use` 开头。

---

### 规范四：Props / Emits 约定

```vue
<!-- Props：明确类型，提供默认值，必填项标注 required -->
const props = defineProps<{
  userId: string           // 必填，不给默认值
  size?: 'sm' | 'md' | 'lg'  // 可选，给默认值
}>()

withDefaults(defineProps<Props>(), {
  size: 'md'
})

<!-- Emits：动词命名，参数类型明确 -->
const emit = defineEmits<{
  update: [value: string]
  submit: [formData: UserForm]
  close: []
}>()
```

Props 数量超过 **5 个**时，考虑是否职责过多，需要拆分。

---

### 规范五：文件命名与目录结构

```
src/
├── components/
│   ├── atoms/          ← PascalCase，例：BaseButton.vue
│   ├── molecules/      ← PascalCase，例：SearchBar.vue
│   └── organisms/      ← PascalCase，例：UserForm.vue
├── composables/        ← camelCase，例：useUserApi.ts
├── views/              ← 对应路由，PascalCase，例：UserListView.vue
├── stores/             ← Pinia store，camelCase，例：userStore.ts
└── api/                ← API 封装，camelCase，例：userApi.ts
```

---

### 规范六：禁止项清单

这是最重要的一项——明确什么**不能做**：

```
❌ 在组件 script 里直接写 axios.get / fetch
   → 必须封装到 src/api/ 下

❌ 在 template 里写复杂逻辑（三目嵌套、方法调用链）
   → 抽成 computed 或 method

❌ 组件间通过 $parent / $root 通信
   → 改用 props/emits 或 provide/inject

❌ 在 organisms 以上层级使用 $emit 层层传递
   → 改用 Pinia store

❌ 新文件使用 Options API
   → 统一使用 Composition API + script setup
```

---

## 第三步：输出规范文档

用 Write 工具写入 `COMPONENT-STANDARDS.md`，内容包含上述六项规范。

文档开头加一段说明：

```markdown
# 组件规范文档

> 本规范基于项目现状扫描（见 codebase-scan-report.md）生成。
> 迁移策略：[根据第一步的判断填写]
> 生成时间：[当前日期]
>
> 新代码立即执行；存量代码按重构计划逐步迁移，不要一次性全改。
```

最后告知用户：「规范已生成，下一步运行 /refactor-plan 获取重构路线图。」
