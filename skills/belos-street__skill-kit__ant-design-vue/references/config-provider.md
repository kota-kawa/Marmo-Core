---
name: config-provider
description: Ant Design Vue ConfigProvider 全局配置，用于主题定制、国际化、组件属性默认值的设置。
official_doc: https://www.antdv.com/components/config-provider
---

# ConfigProvider

> Ant Design Vue 全局配置组件。

## 基础用法

```vue
<script setup>
import { ConfigProvider } from 'ant-design-vue';
</script>

<template>
  <a-config-provider>
    <App />
  </a-config-provider>
</template>
```

## 主题配置

### 基础主题

```vue
<script setup>
import { theme } from 'ant-design-vue';

const token = {
  colorPrimary: '#1890ff',
  borderRadius: 4,
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
};
</script>

<template>
  <a-config-provider :theme="theme">
    <App />
  </a-config-provider>
</template>
```

### 深色主题

```vue
<script setup>
import { theme } from 'ant-design-vue';

const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#1890ff',
  },
};
</script>

<template>
  <a-config-provider :theme="darkTheme">
    <App />
  </a-config-provider>
</template>
```

### 紧凑主题

```vue
<script setup>
import { theme } from 'ant-design-vue';

const compactTheme = {
  algorithm: theme.compactAlgorithm,
  token: {
    colorPrimary: '#1890ff',
  },
};
</script>

<template>
  <a-config-provider :theme="compactTheme">
    <App />
  </a-config-provider>
</template>
```

## 组件尺寸

```vue
<template>
  <!-- 全局小尺寸 -->
  <a-config-provider size="small">
    <App />
  </a-config-provider>

  <!-- 全局中等尺寸 -->
  <a-config-provider size="middle">
    <App />
  </a-config-provider>
</template>
```

## 国际化配置

```vue
<script setup>
import { ConfigProvider } from 'ant-design-vue';
import Dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import zhCN from 'ant-design-vue/es/locale/zh_CN';

dayjs.locale('zh-cn');

const locale = zhCN;
</script>

<template>
  <a-config-provider :locale="locale">
    <App />
  </a-config-provider>
</template>
```

## 表单配置

```vue
<script setup>
const formConfig = {
  colon: true,
  requiredMark: true,
  validateOnRuleChange: true,
};
</script>

<template>
  <a-config-provider :form="formConfig">
    <App />
  </a-config-provider>
</template>
```

## 提示配置

```vue
<script setup>
const messageConfig = {
  top: '100px',
  duration: 3,
  maxCount: 3,
};
</script>

<template>
  <a-config-provider :message="messageConfig">
    <App />
  </a-config-provider>
</template>
```

## 自定义类名前缀

```vue
<template>
  <a-config-provider prefix-cls="custom">
    <App />
  </a-config-provider>
</template>

<!-- 输出: <div class="custom-btn"> -->
```

## 完整示例

```vue
<script setup>
import { theme } from 'ant-design-vue';
import zhCN from 'ant-design-vue/es/locale/zh_CN';

const themeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 4,
  },
};

const locale = zhCN;
</script>

<template>
  <a-config-provider
    :theme="themeConfig"
    :locale="locale"
    :form="{ requiredMark: true }"
  >
    <App />
  </a-config-provider>
</template>
```

## Key Points

- 使用 `theme` 属性定制主题
- 使用 `locale` 属性设置国际化
- 使用 `size` 属性设置全局尺寸
- 使用 `form` 属性配置表单默认行为
- 嵌套使用可以覆盖部分配置
