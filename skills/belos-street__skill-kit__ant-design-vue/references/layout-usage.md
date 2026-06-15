---
name: layout-usage
description: Ant Design Vue Layout 布局组件的用法，包括 Header、Sider、Content、Footer 的经典页面布局。
official_doc: https://www.antdv.com/components/layout
---

# Layout 布局组件

> Ant Design Vue Layout 组件的正确用法，经典后台布局。

## 基础结构

```vue
<script setup>
import { ref } from 'vue';

const collapsed = ref(false);
</script>

<template>
  <a-layout>
    <a-layout-header>Header</a-layout-header>
    <a-layout-content>Content</a-layout-content>
    <a-layout-footer>Footer</a-layout-footer>
  </a-layout>
</template>
```

## 经典后台布局

```vue
<script setup>
import { ref } from 'vue';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons-vue';

const collapsed = ref(false);

const menuItems = [
  { key: '1', icon: '📊', label: 'Dashboard' },
  { key: '2', icon: '👥', label: 'Users' },
  { key: '3', icon: '📦', label: 'Products' },
];
</script>

<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible>
      <div class="logo" />
      <a-menu theme="dark" mode="inline">
        <a-menu-item v-for="item in menuItems" :key="item.key">
          {{ item.label }}
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header style="background: #fff; padding: 0 16px">
        <component
          :is="collapsed ? MenuUnfoldOutlined : MenuFoldOutlined"
          @click="collapsed = !collapsed"
        />
      </a-layout-header>

      <a-layout-content style="margin: 16px">
        <div :style="{ padding: '24px', background: '#fff', minHeight: '360px' }">
          Content
        </div>
      </a-layout-content>

      <a-layout-footer style="text-align: center">
        Ant Design Vue ©2024
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>
```

## Sider 折叠

```vue
<script setup>
import { ref } from 'vue';

const collapsed = ref(false);
</script>

<template>
  <a-layout>
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
    >
      <div class="logo" />
      <a-menu theme="dark" mode="inline">
        <a-menu-item key="1">Nav 1</a-menu-item>
        <a-menu-item key="2">Nav 2</a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-content>Content</a-layout-content>
    </a-layout>
  </a-layout>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：a-layout-content 放错位置 -->
<a-layout>
  <a-layout-content> <!-- 应该在 a-layout 内 -->>
</a-layout>

<!-- ✅ 正确结构 -->
<a-layout>
  <a-layout-header />
  <a-layout>
    <a-layout-sider />
    <a-layout-content />
  </a-layout>
</a-layout>
```

## Key Points

- 使用 `a-layout` 作为根容器
- `a-layout-header/footer` 放顶层
- `a-layout-sider` 放侧边栏
- `a-layout-content` 放主要内容
- 可嵌套使用
- `v-model:collapsed` 控制折叠状态
