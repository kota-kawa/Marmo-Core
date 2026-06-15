---
name: menu-usage
description: Ant Design Vue Menu 菜单组件的用法，包括水平菜单、垂直菜单、内联折叠等。
official_doc: https://www.antdv.com/components/menu
---

# Menu 菜单组件

> Ant Design Vue Menu 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';
import { HomeOutlined, UserOutlined, SettingOutlined } from '@ant-design/icons-vue';

const selectedKeys = ref(['1']);

const menuItems = [
  { key: '1', icon: () => <HomeOutlined />, label: '首页' },
  { key: '2', icon: () => <UserOutlined />, label: '用户管理' },
  { key: '3', icon: () => <SettingOutlined />, label: '系统设置' },
];

const handleClick = ({ key }) => {
  console.log('Selected:', key);
};
</script>

<template>
  <a-menu
    v-model:selectedKeys="selectedKeys"
    mode="horizontal"
    :items="menuItems"
    @click="handleClick"
  />
</template>
```

## 垂直菜单

```vue
<script setup>
import { ref } from 'vue';

const selectedKeys = ref(['1']);
const openKeys = ref(['sub1']);

const menuItems = [
  {
    key: 'sub1',
    label: '用户管理',
    children: [
      { key: '1', label: '用户列表' },
      { key: '2', label: '添加用户' },
    ],
  },
  {
    key: 'sub2',
    label: '系统设置',
    children: [
      { key: '3', label: '基本设置' },
      { key: '4', label: '安全设置' },
    ],
  },
];
</script>

<template>
  <a-menu
    v-model:selectedKeys="selectedKeys"
    v-model:openKeys="openKeys"
    mode="inline"
    :items="menuItems"
  />
</template>
```

## 内联折叠

```vue
<script setup>
import { ref } from 'vue';

const selectedKeys = ref(['1']);
const openKeys = ref(['sub1']);

const menuItems = [
  {
    key: 'sub1',
    label: 'Navigation One',
    children: [
      { key: '1', label: 'Option 1' },
      { key: '2', label: 'Option 2' },
    ],
  },
];
</script>

<template>
  <a-menu
    v-model:selectedKeys="selectedKeys"
    v-model:openKeys="openKeys"
    mode="inline"
    :inline-collapsed="collapsed"
    :items="menuItems"
  />
</template>
```

## 主题

```vue
<template>
  <a-menu
    mode="horizontal"
    theme="dark"
    :items="menuItems"
  />

  <a-menu
    mode="horizontal"
    theme="light"
    :items="menuItems"
  />
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：直接在 template 写 JSX -->
<a-menu>
  <a-menu-item key="1">{{ '首页' }}</a-menu-item>
</a-menu>

<!-- ✅ 正确：使用 :items 或 v-for -->
<a-menu :items="menuItems" />

<!-- 或 -->
<a-menu>
  <a-menu-item v-for="item in menuItems" :key="item.key">
    {{ item.label }}
  </a-menu-item>
</a-menu>
```

## Key Points

- 使用 `v-model:selectedKeys` 控制选中
- 使用 `v-model:openKeys` 控制展开（inline 模式）
- 使用 `mode` 设置方向（horizontal/vertical/inline）
- 使用 `theme` 设置主题（light/dark）
- 使用 `:items` 或 `v-for` 渲染菜单项
- 图标使用 `icon: () => <Icon />` 方式
