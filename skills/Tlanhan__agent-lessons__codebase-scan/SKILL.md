---
name: "codebase-scan"
description: "当用户说'扫描项目'、'分析代码现状'、'摸底'、'先看看项目'时触发。扫描 Vue 项目并输出组件健康度清单。"
---

# Vue 项目现状扫描

## 目标

扫描整个 Vue 项目，生成一份结构化的组件清单，为后续定标准和制定重构计划提供数据依据。

> 这一步只做分析，不做任何修改，不给任何建议。把事实摆出来就够了。

---

## 第一步：确认扫描根目录

如果用户未指定，默认扫描当前工作目录。
询问用户确认：「我将扫描 [目录]，确认吗？」

---

## 第二步：收集 Vue 组件清单

用 Glob 工具找出所有 `.vue` 文件，排除：
`node_modules` `dist` `build` `.nuxt` `coverage`

对每个 `.vue` 文件，用 Read 工具读取内容，收集以下数据：

| 指标 | 收集方式 |
|------|---------|
| 总行数 | 统计文件行数 |
| template 行数 | `<template>` 到 `</template>` 之间的行数 |
| script 行数 | `<script>` 到 `</script>` 之间的行数 |
| style 行数 | `<style>` 到 `</style>` 之间的行数 |
| API 风格 | script 中含 `setup` → Composition API，否则 → Options API |
| props 数量 | 统计 `props:` 或 `defineProps` 中的字段数 |
| emit 数量 | 统计 `emits:` 或 `defineEmits` 中的事件数 |
| 外部依赖 | import 的非 Vue 核心包（axios、pinia、router 等） |

---

## 第三步：识别重复逻辑

用 Grep 工具在所有 `.vue` 文件中搜索以下模式，记录出现次数和位置：

- `axios.get` / `axios.post` / `fetch(` — 直接在组件里调 API
- `localStorage` / `sessionStorage` — 直接读写存储
- `setTimeout` / `setInterval` — 定时器逻辑
- `v-loading` / `isLoading` — 加载状态管理
- `try { ... } catch` — 错误处理逻辑

出现 3 次以上的模式，标记为「重复逻辑候选」。

---

## 第四步：目录结构分析

用 Glob 工具列出 `src/` 下的目录结构（只到第二层），判断组织方式：
- 按类型组织：`components/` `views/` `utils/` `api/`
- 按功能组织：`user/` `order/` `product/`
- 混乱：无明显规律

---

## 第五步：输出扫描报告

输出格式如下，同时用 Write 工具写入 `codebase-scan-report.md`：

```markdown
# 项目现状扫描报告

## 概览
- 扫描文件数：N 个 .vue 文件
- 目录组织方式：[按类型 / 按功能 / 混乱]
- API 风格分布：Options API N 个 / Composition API N 个 / 混用

## 组件规模分布

### 🔴 超大组件（script > 300 行，需要优先处理）
| 文件 | 总行数 | template | script | style | API风格 | props数 |
|------|--------|----------|--------|-------|---------|---------|

### 🟡 偏大组件（script 150-300 行，建议处理）
| 文件 | 总行数 | template | script | style | API风格 | props数 |
|------|--------|----------|--------|-------|---------|---------|

### 🟢 正常组件（script < 150 行）
共 N 个，此处不逐一列出。

## 重复逻辑分析
| 模式 | 出现次数 | 涉及文件 |
|------|---------|---------|

## 目录结构
[输出 src/ 的两层目录树]
```

---

## 约束

- 只统计数据，不做好坏评判，不给建议（那是下一个 Skill 的事）
- 文件太多时（>100个）先输出超大和偏大的，正常组件只计数
- 如果项目用 TypeScript（`.vue` 里有 `lang="ts"`），在报告中注明
