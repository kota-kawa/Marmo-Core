---
name: space-usage
description: Ant Design Vue Space 间距组件的用法，用于设置元素之间的间距。
official_doc: https://www.antdv.com/components/space
---

# Space 间距组件

> Ant Design Vue Space 组件的正确用法。

## 基础用法

```vue
<template>
  <a-space>
    <a-button type="primary">Primary</a-button>
    <a-button>Default</a-button>
    <a-button type="dashed">Dashed</a-button>
  </a-space>
</template>
```

## 方向

```vue
<template>
  <a-space direction="vertical">
    <a-button>Button 1</a-button>
    <a-button>Button 2</a-button>
    <a-button>Button 3</a-button>
  </a-space>
</template>
```

## 间距大小

```vue
<template>
  <a-space size="small">
    <a-button>Small</a-button>
    <a-button>Gap</a-button>
  </a-space>

  <a-space size="middle">
    <a-button>Middle</a-button>
    <a-button>Gap</a-button>
  </a-space>

  <a-space size="large">
    <a-button>Large</a-button>
    <a-button>Gap</a-button>
  </a-space>
</template>
```

## 自定义间距

```vue
<template>
  <a-space :size="24">
    <a-button>Custom 24px</a-button>
    <a-button>Gap</a-button>
  </a-space>
</template>
```

## 换行

```vue
<template>
  <a-space wrap>
    <a-button v-for="i in 10" :key="i">Button {{ i }}</a-button>
  </a-space>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：使用空格字符串 -->
<a-space size=" ">

<!-- ✅ 正确：使用预设值或数字 -->
<a-space size="small">
<a-space :size="24">
```

## Key Points

- 使用 `direction` 设置方向（vertical/horizontal）
- 使用 `size` 设置间距大小（small/middle/large/数字）
- 使用 `wrap` 让元素换行
- 优先于 `margin` 方式管理间距
