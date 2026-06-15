---
name: drawer-patterns
description: Ant Design Vue Drawer 抽屉组件的用法，包括基础用法、 placement、宽高控制和表单抽屉。
official_doc: https://www.antdv.com/components/drawer
---

# Drawer 抽屉组件

> Ant Design Vue Drawer 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';

const visible = ref(false);

const showDrawer = () => {
  visible.value = true;
};

const onClose = () => {
  visible.value = false;
};
</script>

<template>
  <a-button type="primary" @click="showDrawer">Open</a-button>

  <a-drawer
    v-model:open="visible"
    title="Basic Drawer"
    placement="right"
    @close="onClose"
  >
    <p>Some contents...</p>
    <p>Some contents...</p>
    <p>Some contents...</p>
  </a-drawer>
</template>
```

## Placement 位置

```vue
<template>
  <a-drawer v-model:open="visible" title="Right" placement="right">
    <p>Right side drawer</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Left" placement="left">
    <p>Left side drawer</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Top" placement="top" height="50%">
    <p>Top drawer</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Bottom" placement="bottom" height="50%">
    <p>Bottom drawer</p>
  </a-drawer>
</template>
```

## 宽度控制

```vue
<template>
  <a-drawer v-model:open="visible" title="Small" :width="320">
    <p>320px width</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Medium" :width="500">
    <p>500px width</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Large" :width="800">
    <p>800px width</p>
  </a-drawer>

  <a-drawer v-model:open="visible" title="Responsive" :width="720" :breakpoint="'lg'">
    <p>Responsive width</p>
  </a-drawer>
</template>
```

## 表单抽屉

```vue
<script setup>
import { ref, reactive } from 'vue';
import { message } from 'ant-design-vue';

const visible = ref(false);
const formRef = ref();
const loading = ref(false);

const formState = reactive({
  name: '',
  email: '',
  description: '',
});

const rules = {
  name: [{ required: true, message: '请输入名称' }],
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '请输入有效邮箱' },
  ],
};

const showDrawer = () => {
  visible.value = true;
};

const onClose = () => {
  visible.value = false;
  formRef.value.resetFields();
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
    loading.value = true;
    // 模拟 API 调用
    await fetch('/api/create', {
      method: 'POST',
      body: JSON.stringify(formState),
    });
    message.success('创建成功');
    onClose();
  } catch (error) {
    // 验证失败
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <a-button type="primary" @click="showDrawer">
    New User
  </a-button>

  <a-drawer
    v-model:open="visible"
    title="Create User"
    :width="400"
    @close="onClose"
  >
    <a-form
      ref="formRef"
      :model="formState"
      :rules="rules"
      layout="vertical"
    >
      <a-form-item label="Name" name="name">
        <a-input v-model:value="formState.name" />
      </a-form-item>

      <a-form-item label="Email" name="email">
        <a-input v-model:value="formState.email" />
      </a-form-item>

      <a-form-item label="Description" name="description">
        <a-textarea v-model:value="formState.description" :rows="4" />
      </a-form-item>
    </a-form>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 8px">
        <a-button @click="onClose">Cancel</a-button>
        <a-button type="primary" :loading="loading" @click="handleSubmit">
          Submit
        </a-button>
      </div>
    </template>
  </a-drawer>
</template>
```

## 多层抽屉

```vue
<script setup>
import { ref } from 'vue';

const visible = ref(false);
const secondVisible = ref(false);

const showSecond = () => {
  secondVisible.value = true;
};
</script>

<template>
  <a-button type="primary" @click="visible = true">Open First</a-button>

  <a-drawer v-model:open="visible" title="First Drawer" :width="400">
    <a-button type="primary" @click="showSecond">
      Open Second
    </a-button>

    <a-drawer
      v-model:open="secondVisible"
      title="Second Drawer"
      :width="300"
    >
      <p>This is second drawer</p>
    </a-drawer>
  </a-drawer>
</template>
```

## 隐藏关闭按钮

```vue
<template>
  <a-drawer
    v-model:open="visible"
    :closable="false"
  >
    <p>No close button</p>
  </a-drawer>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：使用 open 而不是 v-model:open -->
<a-drawer :open="visible">

<!-- ✅ 正确：使用 v-model:open -->
<a-drawer v-model:open="visible">

<!-- ❌ 错误：忘记在表单提交时阻止默认行为 -->
<!-- a-form 没有使用 @finish，而是用了 @submit -->

<!-- ✅ 正确：使用 @finish 或手动验证 -->
```

## Key Points

- 使用 `v-model:open` 控制显示
- 使用 `placement` 控制位置（right/left/top/bottom）
- 使用 `width` / `height` 控制尺寸
- 使用 `#footer` slot 自定义底部
- 表单抽屉结合 Form 组件使用
- 多层抽屉可以嵌套
