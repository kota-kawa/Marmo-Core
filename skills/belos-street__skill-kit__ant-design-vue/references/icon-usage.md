---
name: icon-usage
description: Ant Design Vue Icon 组件的用法，包括图标引入、组合使用和常见错误。
official_doc: https://www.antdv.com/components/icon
---

# Icon 组件

> Ant Design Vue 图标组件的正确用法。

## 安装

```bash
npm install @ant-design/icons-vue
```

## 基础用法

```vue
<script setup>
import {
  HomeOutlined,
  UserOutlined,
  SettingsOutlined,
  SearchOutlined
} from '@ant-design/icons-vue';
</script>

<template>
  <HomeOutlined />
  <UserOutlined />
  <SettingsOutlined />
  <SearchOutlined />
</template>
```

## 图标分类

### 方向性图标

```vue
<template>
  <StepForwardOutlined />  <!-- 下一步 -->
  <StepBackwardOutlined /> <!-- 上一步 -->
  <UpOutlined />
  <DownOutlined />
  <LeftOutlined />
  <RightOutlined />
</template>
```

### 提示性图标

```vue
<template>
  <InfoCircleOutlined />   <!-- 信息 -->
  <QuestionCircleOutlined /> <!-- 帮助 -->
  <CheckCircleOutlined />  <!-- 成功 -->
  <ExclamationCircleOutlined /> <!-- 警告 -->
  <CloseCircleOutlined />   <!-- 错误 -->
</template>
```

### 操作类图标

```vue
<template>
  <SearchOutlined />       <!-- 搜索 -->
  <EditOutlined />         <!-- 编辑 -->
  <DeleteOutlined />       <!-- 删除 -->
  <CopyOutlined />         <!-- 复制 -->
  <DownloadOutlined />     <!-- 下载 -->
  <UploadOutlined />       <!-- 上传 -->
</template>
```

## 与 Button 组合

```vue
<script setup>
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue';
</script>

<template>
  <a-button type="primary">
    <template #icon><SearchOutlined /></template>
    搜索
  </a-button>

  <a-button>
    <template #icon><ReloadOutlined /></template>
    刷新
  </a-button>
</template>
```

## 在菜单中使用

```vue
<script setup>
import { DashboardOutlined, UserOutlined } from '@ant-design/icons-vue';

const menuItems = [
  {
    key: 'dashboard',
    icon: () => <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: 'user',
    icon: () => <UserOutlined />,
    label: '用户',
  },
];
</script>

<template>
  <a-menu v-model:selectedKeys="selectedKeys" mode="horizontal">
    <a-menu-item v-for="item in menuItems" :key="item.key">
      <component :is="item.icon" />
      {{ item.label }}
    </a-menu-item>
  </a-menu>
</template>
```

## 自定义图标组件

```vue
<script setup>
import { createFromIconfontCN } from '@ant-design/icons-vue';

const IconFont = createFromIconfontCN({
  scriptUrl: '//at.alicdn.com/t/font_xxx.js',
});
</script>

<template>
  <IconFont type="icon-xxx" />
</template>
```

## 旋转动画

```vue
<template>
  <LoadingOutlined />
  <SyncOutlined spin />
  <ReloadOutlined spin />
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：直接渲染字符串 -->
<HomeOutlined>"home"</HomeOutlined>

<!-- ❌ 错误：使用图片路径 -->
<img src="@/assets/icon.svg" />

<!-- ✅ 正确：直接使用组件 -->
<HomeOutlined />
```

## 按需引入

使用 unplugin-vue-components 自动导入：

```bash
npm install unplugin-vue-components -D
```

```js
// vite.config.js
import Components from 'unplugin-vue-components/vite';
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers';

export default {
  plugins: [
    Components({
      resolvers: [
        AntDesignVueResolver({
          importStyle: false,
          icons: true,
        }),
      ],
    }),
  ],
};
```

## Key Points

- 图标是组件，直接使用 `<IconName />`
- 图标放在 `#icon` slot 中
- 使用 `@ant-design/icons-vue` 包
- 使用 `spin` 属性添加旋转动画
- 使用 `createFromIconfontCN` 加载自定义字体图标
