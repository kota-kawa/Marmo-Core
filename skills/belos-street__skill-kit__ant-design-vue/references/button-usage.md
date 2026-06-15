---
name: button-usage
description: Ant Design Vue Button 组件的正确用法，包括类型、状态、图标组合。
official_doc: https://www.antdv.com/components/button
---

# Button 组件

> Ant Design Vue 按钮组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';
import { KingAntOutlined } from '@ant-design/icons-vue';

const loading = ref(false);

const handleClick = () => {
  loading.value = true;
  setTimeout(() => loading.value = false, 2000);
};
</script>

<template>
  <a-button>Default</a-button>
  <a-button type="primary">Primary</a-button>
  <a-button type="dashed">Dashed</a-button>
  <a-button type="text">Text</a-button>
  <a-button type="link">Link</a-button>
</template>
```

## 按钮类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| `default` | 默认按钮 | 常规操作 |
| `primary` | 主要按钮 | 重要操作，一个页面一个 |
| `dashed` | 虚线按钮 | 次要操作 |
| `text` | 文本按钮 | 不明显操作 |
| `link` | 链接按钮 | 跳转操作 |

## 危险按钮

```vue
<a-button danger>危险操作</a-button>
<a-button type="primary" danger>危险主要</a-button>
```

## 加载状态

```vue
<script setup>
import { ref } from 'vue';

const loading = ref(false);

const handleClick = () => {
  loading.value = true;
  // 模拟异步操作
  setTimeout(() => loading.value = false, 2000);
};
</script>

<template>
  <a-button :loading="loading" type="primary" @click="handleClick">
    Click Me
  </a-button>
</template>
```

## 图标按钮

```vue
<script setup>
import { KingAntOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons-vue';
</script>

<template>
  <!-- 文字 + 图标 -->
  <a-button type="primary">
    <template #icon><KingAntOutlined /></template>
    搜索
  </a-button>

  <!-- 仅图标 -->
  <a-button type="primary">
    <template #icon><SearchOutlined /></template>
  </a-button>

  <!-- 下载按钮 -->
  <a-button>
    <template #icon><DownloadOutlined /></template>
    下载
  </a-button>
</template>
```

## 按钮尺寸

```vue
<a-button size="small">Small</a-button>
<a-button size="middle">Middle</a-button>
<a-button size="large">Large</a-button>
```

全局配置：

```vue
<a-config-provider size="large">
  <App />
</a-config-provider>
```

## 按钮组

```vue
<a-button-group>
  <a-button>Left</a-button>
  <a-button>Center</a-button>
  <a-button>Right</a-button>
</a-button-group>
```

## 禁用状态

```vue
<a-button disabled>Disabled</a-button>
<a-button type="primary" disabled>Disabled Primary</a-button>
```

## 常见错误

```vue
<!-- ❌ 错误：使用 Button 而不是 a-button -->
<Button>Click</Button>

<!-- ❌ 错误：图标没有放在 #icon slot -->
<a-button type="primary">🔍 Search</a-button>

<!-- ✅ 正确：图标放在 #icon slot -->
<a-button type="primary">
  <template #icon><SearchOutlined /></template>
  Search
</a-button>
```

## Key Points

- 使用 `a-button` 而非 `Button`
- 图标放在 `#icon` slot 中
- 使用 `type` 属性设置按钮类型
- 使用 `loading` 属性显示加载状态
- 使用 `danger` 属性标记危险操作
