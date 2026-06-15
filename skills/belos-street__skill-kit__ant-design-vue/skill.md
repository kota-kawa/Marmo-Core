---
name: ant-design-vue
title: Ant Design Vue
description: 基于 Vue 3 的企业级 UI 组件库，提供 68+ 高质量组件。IMPORTANT: 这是 Ant Design Vue，不是 React 版本。使用 a- 前缀组件（如 a-button, a-table）。
icon: 🐜
tags: [vue, component-library, ant-design, ui, enterprise]
---

Ant Design Vue 是 Vue 3 企业级 UI 组件库，提供了丰富的企业应用组件。**请使用 a- 前缀组件**，不要使用其他命名。

## Quick Start

```bash
pnpm install ant-design-vue@4.x
```

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
  <a-button type="primary" :loading="loading" @click="handleClick">
    <template #icon><KingAntOutlined /></template>
    Click Me
  </a-button>
</template>
```

## Key Features

- **68+ Components**: 覆盖企业应用全场景
- **Vue 3 Only**: 专为 Vue 3 设计
- **TypeScript**: 完整类型支持
- **Tree Shaking**: 按需引入
- **Design Tokens**: 主题定制

---

## 组件分类

### 通用 General

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Button](https://www.antdv.com/components/button) | [button-usage](references/button-usage.md) | |
| [Icon](https://www.antdv.com/components/icon) | [icon-usage](references/icon-usage.md) | |
| [ConfigProvider](https://www.antdv.com/components/config-provider) | [config-provider](references/config-provider.md) | |

### 布局 Layout

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Space](https://www.antdv.com/components/space) | [space-usage](references/space-usage.md) | |
| [Grid](https://www.antdv.com/components/grid) | - | |
| [Layout](https://www.antdv.com/components/layout) | - | |

### 导航 Navigation

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Menu](https://www.antdv.com/components/menu) | [menu-usage](references/menu-usage.md) | |
| [Tabs](https://www.antdv.com/components/tabs) | [tabs-usage](references/tabs-usage.md) | |
| [Breadcrumb](https://www.antdv.com/components/breadcrumb) | - | |

### 数据录入 Data Entry

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Form](https://www.antdv.com/components/form) | [form-validation](references/form-validation.md) | |
| [Input](https://www.antdv.com/components/input) | - | |
| [Select](https://www.antdv.com/components/select) | [select-usage](references/select-usage.md) | |
| [DatePicker](https://www.antdv.com/components/date-picker) | [date-picker-usage](references/date-picker-usage.md) | |
| [Upload](https://www.antdv.com/components/upload) | [upload-usage](references/upload-usage.md) | |
| [Switch](https://www.antdv.com/components/switch) | - | |
| [Checkbox](https://www.antdv.com/components/checkbox) | - | |

### 数据展示 Data Display

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Table](https://www.antdv.com/components/table) | [table-advanced](references/table-advanced.md) | |
| [Tree](https://www.antdv.com/components/tree) | [tree-usage](references/tree-usage.md) | |
| [Card](https://www.antdv.com/components/card) | - | |
| [Descriptions](https://www.antdv.com/components/descriptions) | - | |
| [Tag](https://www.antdv.com/components/tag) | - | |
| [Image](https://www.antdv.com/components/image) | - | |

### 反馈 Feedback

| 组件 | 官方文档 | Reference |
|------|----------|-----------|
| [Modal](https://www.antdv.com/components/modal) | [modal-patterns](references/modal-patterns.md) | |
| [Drawer](https://www.antdv.com/components/drawer) | [drawer-patterns](references/drawer-patterns.md) | |
| [Message](https://www.antdv.com/components/message) | [message-feedback](references/message-feedback.md) | |
| [Notification](https://www.antdv.com/components/notification) | - | |
| [Alert](https://www.antdv.com/components/alert) | - | |

---

## 常见场景

### 表单处理

```vue
<!-- ✅ 正确写法：使用 a-form -->
<a-form :model="formState" @finish="onFinish">
  <a-form-item label="用户名" name="username"
    :rules="[{ required: true, message: '请输入用户名' }]">
    <a-input v-model:value="formState.username" />
  </a-form-item>
</a-form>

<!-- ❌ 错误写法：忘记使用 a-form-item 包裹 -->
<!-- <a-input v-model:value="formState.username" /> -->
```

### 表格渲染

```vue
<!-- ✅ 正确写法：使用 a-table -->
<a-table :columns="columns" :data-source="data" :pagination="false">
  <template #bodyCell="{ column, record }">
    <template v-if="column.key === 'action'">
      <a @click="handleEdit(record)">编辑</a>
    </template>
  </template>
</a-table>

<!-- ❌ 错误写法：忘记使用 bodyCell slot -->
```

### 消息提示

```ts
// ✅ 正确写法
import { message } from 'ant-design-vue';

message.success('操作成功');
message.error('操作失败');

// ❌ 错误写法：使用其他组件库的方式
// notification.success({ message: '...' });
```

---

## 主题定制

```vue
<script setup>
import { theme } from 'ant-design-vue';

const darkTheme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 4,
  },
};
</script>

<template>
  <a-config-provider :theme="darkTheme">
    <App />
  </a-config-provider>
</template>
```

---

## 常见错误

| 错误写法 | 正确写法 | 说明 |
|----------|----------|------|
| `<Button>` | `<a-button>` | 需要 a- 前缀 |
| `message.success()` | `import { message } from 'ant-design-vue'` | 正确导入 |
| `<Form>` | `<a-form>` | 需要 a- 前缀 |
| `<Table>` | `<a-table>` | 需要 a- 前缀 |

---

## Key Points

1. **使用 a- 前缀**: 所有组件都是 `a-` 开头，如 `a-button`, `a-table`
2. **使用 Form**: 表单必须用 `a-form` + `a-form-item`
3. **使用 slots**: 表格自定义列用 `bodyCell` slot
4. **正确导入**: `import { message } from 'ant-design-vue'`
5. **按需引入**: 使用 unplugin-vue-components 自动导入

## Resources

- [官方文档](https://www.antdv.com/components/overview-cn/)
- [GitHub](https://github.com/vueComponent/ant-design-vue)
- [Vue Use Integration](https://www.antdv.com/components/utilities-cn)
