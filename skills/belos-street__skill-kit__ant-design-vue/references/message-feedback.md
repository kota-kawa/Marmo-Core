---
name: message-feedback
description: Ant Design Vue Message 全局提示的用法，包括基础用法、加载状态、手动关闭等。
official_doc: https://www.antdv.com/components/message
---

# Message 全局提示

> Ant Design Vue Message 组件的正确用法。

## 基础用法

```ts
import { message } from 'ant-design-vue';

// 成功
message.success('操作成功');

// 失败
message.error('操作失败');

// 警告
message.warning('请注意');

// 信息
message.info('这是一条信息');
```

## 组件中使用

```vue
<script setup>
import { message } from 'ant-design-vue';

const handleSubmit = async () => {
  try {
    await fetch('/api/submit', { method: 'POST' });
    message.success('提交成功');
  } catch (error) {
    message.error('提交失败');
  }
};
</script>

<template>
  <a-button type="primary" @click="handleSubmit">提交</a-button>
</template>
```

## 加载状态

```ts
// 显示加载
const hide = message.loading('处理中...', 0);

// 模拟异步操作
setTimeout(() => {
  hide();
  message.success('处理完成');
}, 2000);
```

## 配置时长

```ts
// 自定义时长（默认 3 秒）
message.success('3秒后消失', 3);

// 永不消失（需要手动关闭）
const hide = message.loading('加载中...', 0);

// 手动关闭
hide();
```

## 常见错误

```ts
// ❌ 错误：在 setup 外使用
// message.success() 只能在 setup 或 methods 中使用

// ❌ 错误：忘记解构 message
// const msg = require('ant-design-vue');
// msg.message.success(); // 错误

// ✅ 正确：从 ant-design-vue 导入
import { message } from 'ant-design-vue';
message.success('成功');
```

## Key Points

- 从 `ant-design-vue` 导入 `message`
- 使用 `message.success/error/warning/info`
- `message.loading()` 返回关闭函数
- 组件中直接使用，无需注册
