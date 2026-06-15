---
name: modal-patterns
description: Ant Design Vue Modal 对话框的用法，包括基础用法、异步关闭、自定义页脚和确认框。
official_doc: https://www.antdv.com/components/modal
---

# Modal 对话框

> Ant Design Vue Modal 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';

const visible = ref(false);

const showModal = () => {
  visible.value = true;
};

const handleOk = () => {
  visible.value = false;
};

const handleCancel = () => {
  visible.value = false;
};
</script>

<template>
  <a-button type="primary" @click="showModal">Open Modal</a-button>

  <a-modal
    v-model:open="visible"
    title="Basic Modal"
    @ok="handleOk"
    @cancel="handleCancel"
  >
    <p>Some contents...</p>
    <p>Some contents...</p>
    <p>Some contents...</p>
  </a-modal>
</template>
```

## 异步关闭

```vue
<script setup>
import { ref } from 'vue';
import { message } from 'ant-design-vue';

const visible = ref(false);
const loading = ref(false);

const showModal = () => {
  visible.value = true;
};

const handleOk = async () => {
  loading.value = true;

  try {
    // 模拟异步操作
    await fetch('/api/submit', {
      method: 'POST',
    });
    message.success('提交成功');
    visible.value = false;
  } catch (error) {
    message.error('提交失败');
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <a-button type="primary" @click="showModal">Async Modal</a-button>

  <a-modal
    v-model:open="visible"
    title="Async Modal"
    :confirm-loading="loading"
    @ok="handleOk"
  >
    <p>点击确定后会异步关闭...</p>
  </a-modal>
</template>
```

## 自定义页脚

```vue
<script setup>
import { ref } from 'vue';

const visible = ref(false);

const showModal = () => {
  visible.value = true;
};
</script>

<template>
  <a-button type="primary" @click="showModal">Custom Footer</a-button>

  <a-modal
    v-model:open="visible"
    title="Custom Footer"
  >
    <template #footer>
      <a-button key="back" @click="visible = false">返回</a-button>
      <a-button key="submit" type="primary" @click="visible = false">提交</a-button>
    </template>

    <p>自定义页脚按钮</p>
  </a-modal>
</template>
```

## 确认框

```vue
<script setup>
import { Modal } from 'ant-design-vue';
import { ExclamationCircleOutlined } from '@ant-design/icons-vue';

const showConfirm = () => {
  Modal.confirm({
    title: '确认删除?',
    icon: <ExclamationCircleOutlined />,
    content: '删除后无法恢复，确定要删除吗?',
    okText: '确认',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      console.log('OK');
    },
    onCancel() {
      console.log('Cancel');
    },
  });
};

const showDeleteConfirm = () => {
  Modal.confirm({
    title: '删除确认',
    icon: <ExclamationCircleOutlined />,
    content: '此操作不可撤销，是否继续?',
    okText: '删除',
    okType: 'danger',
  });
};
</script>

<template>
  <a-button type="primary" @click="showConfirm">Confirm</a-button>
  <a-button danger @click="showDeleteConfirm">Delete Confirm</a-button>
</template>
```

## 信息提示

```vue
<script setup>
import { Modal } from 'ant-design-vue';

Modal.info({
  title: '提示',
  content: '这是一条提示信息',
  onOk() {},
});

Modal.success({
  title: '成功',
  content: '操作成功完成',
});

Modal.error({
  title: '错误',
  content: '操作失败，请重试',
});

Modal.warning({
  title: '警告',
  content: '请注意操作风险',
});
```

## 条件关闭

```vue
<script setup>
import { ref } from 'vue';

const visible = ref(false);
const formValid = ref(false);

const handleOk = () => {
  if (!formValid.value) {
    return; // 不关闭
  }
  visible.value = false;
};
</script>

<template>
  <a-modal
    v-model:open="visible"
    title="Form Modal"
    @ok="handleOk"
  >
    <p>只有表单验证通过才能关闭</p>
  </a-modal>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：使用 open 而不是 v-model:open -->
<a-modal :open="visible">

<!-- ✅ 正确：使用 v-model:open -->
<a-modal v-model:open="visible">

<!-- ❌ 错误：忘记处理异步关闭 -->
<a-button @click="visible = true; submit()">确定</a-button>

<!-- ✅ 正确：async/await 处理 -->
const handleOk = async () => {
  await submit();
  visible.value = false;
};
```

## Key Points

- 使用 `v-model:open` 控制显示
- 异步关闭使用 `confirmLoading`
- 确认框使用 `Modal.confirm()`
- 使用 `#footer` slot 自定义页脚
- 条件关闭在 `handleOk` 中控制
