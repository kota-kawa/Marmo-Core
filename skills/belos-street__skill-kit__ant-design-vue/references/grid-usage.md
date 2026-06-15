---
name: grid-usage
description: Ant Design Vue Grid 栅格组件的用法，基于 24 栅格系统进行布局。
official_doc: https://www.antdv.com/components/grid
---

# Grid 栅格组件

> Ant Design Vue Grid 组件的正确用法，基于 24 栅格系统。

## 基础用法

```vue
<template>
  <a-row :gutter="16">
    <a-col :span="12">
      <div>col-12</div>
    </a-col>
    <a-col :span="12">
      <div>col-12</div>
    </a-col>
  </a-row>
</template>
```

## 栅格间隔

```vue
<template>
  <a-row :gutter="16">
    <a-col :span="8">
      <div>col-8</div>
    </a-col>
    <a-col :span="8">
      <div>col-8</div>
    </a-col>
    <a-col :span="8">
      <div>col-8</div>
    </a-col>
  </a-row>
</template>
```

## 响应式

```vue
<template>
  <a-row :gutter="16">
    <a-col :xs="24" :sm="12" :md="8" :lg="6">
      <div>响应式</div>
    </a-col>
    <a-col :xs="24" :sm="12" :md="8" :lg="6">
      <div>响应式</div>
    </a-col>
    <a-col :xs="24" :sm="12" :md="8" :lg="6">
      <div>响应式</div>
    </a-col>
    <a-col :xs="24" :sm="12" :md="8" :lg="6">
      <div>响应式</div>
    </a-col>
  </a-row>
</template>
```

## Offset

```vue
<template>
  <a-row :gutter="16">
    <a-col :span="8">
      <div>col-8</div>
    </a-col>
    <a-col :span="8" :offset="8">
      <div>col-8 offset-8</div>
    </a-col>
  </a-row>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：忘记 :gutter 是数字 -->
<a-row gutter="16">

<!-- ✅ 正确：使用绑定 -->
<a-row :gutter="16">

<!-- ❌ 错误：span 超过 24 -->
<a-col :span="30">
```

## Key Points

- 使用 `a-row` + `a-col` 结构
- `gutter` 设置间距，单位 px
- `span` 设置宽度，总和不超过 24
- 响应式使用 `xs/sm/md/lg/xl`
- 使用 `offset` 设置偏移
