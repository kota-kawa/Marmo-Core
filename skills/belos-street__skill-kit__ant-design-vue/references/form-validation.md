---
name: form-validation
description: Ant Design Vue Form 表单验证的完整指南，包括规则定义、异步验证和自定义验证器。
official_doc: https://www.antdv.com/components/form
---

# Form 表单验证

> Ant Design Vue 表单验证的完整指南。

## 基础结构

```vue
<script setup>
import { reactive, ref } from 'vue';
import { message } from 'ant-design-vue';

const formRef = ref();

const formState = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
});

const rules = {
  username: [
    { required: true, message: '请输入用户名' },
    { min: 3, max: 20, message: '用户名 3-20 个字符' },
  ],
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '请输入有效的邮箱地址' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, message: '密码至少 6 个字符' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码' },
    {
      validator: (_rule, value) => {
        if (value !== formState.password) {
          return Promise.reject('两次输入的密码不一致');
        }
        return Promise.resolve();
      },
    },
  ],
};

const onFinish = (values) => {
  console.log('Success:', values);
  message.success('提交成功！');
};

const onFinishFailed = (errorInfo) => {
  console.log('Failed:', errorInfo);
  message.error('请检查表单填写');
};

const resetForm = () => {
  formRef.value.resetFields();
};
</script>

<template>
  <a-form
    ref="formRef"
    :model="formState"
    :rules="rules"
    layout="vertical"
    @finish="onFinish"
    @finishFailed="onFinishFailed"
  >
    <a-form-item label="用户名" name="username">
      <a-input v-model:value="formState.username" placeholder="请输入用户名" />
    </a-form-item>

    <a-form-item label="邮箱" name="email">
      <a-input v-model:value="formState.email" placeholder="请输入邮箱" />
    </a-form-item>

    <a-form-item label="密码" name="password">
      <a-input-password v-model:value="formState.password" placeholder="请输入密码" />
    </a-form-item>

    <a-form-item label="确认密码" name="confirmPassword">
      <a-input-password v-model:value="formState.confirmPassword" placeholder="请确认密码" />
    </a-form-item>

    <a-form-item>
      <a-button type="primary" html-type="submit">提交</a-button>
      <a-button style="margin-left: 10px" @click="resetForm">重置</a-button>
    </a-form-item>
  </a-form>
</template>
```

## 常用验证规则

### 必填验证

```js
const rules = {
  name: [
    { required: true, message: '此字段必填' },
  ],
};
```

### 格式验证

```js
const rules = {
  email: [
    { type: 'email', message: '请输入有效的邮箱' },
  ],
  url: [
    { type: 'url', message: '请输入有效的 URL' },
  ],
  number: [
    { type: 'number', message: '请输入数字' },
  ],
};
```

### 长度验证

```js
const rules = {
  name: [
    { min: 2, message: '至少 2 个字符' },
    { max: 10, message: '最多 10 个字符' },
  ],
  description: [
    { min: 10, max: 200, message: '10-200 个字符' },
  ],
};
```

### 正则验证

```js
const rules = {
  phone: [
    { required: true, message: '请输入手机号' },
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入有效的手机号',
    },
  ],
  idCard: [
    {
      pattern: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/,
      message: '请输入有效的身份证号',
    },
  ],
};
```

## 自定义验证器

### 异步验证

```js
const checkUsername = async (_rule, value) => {
  if (!value) return Promise.reject('请输入用户名');

  // 模拟 API 调用
  const response = await fetch(`/api/check-username?username=${value}`);
  const data = await response.json();

  if (data.exists) {
    return Promise.reject('用户名已存在');
  }
  return Promise.resolve();
};

const rules = {
  username: [{ validator: checkUsername, trigger: 'blur' }],
};
```

### 组合验证

```js
const rules = {
  password: [
    { required: true, message: '请输入密码' },
    {
      pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/,
      message: '密码至少包含大写字母、小写字母和数字',
    },
  ],
};
```

## 动态字段验证

```vue
<script setup>
import { reactive } from 'vue';

const formState = reactive({
  users: [
    { name: '', email: '' },
  ],
});

const addUser = () => {
  formState.users.push({ name: '', email: '' });
};

const removeUser = (index) => {
  formState.users.splice(index, 1);
};

const validateUsers = async (_rule, value) => {
  if (!value || value.length === 0) {
    return Promise.reject('请至少添加一个用户');
  }
  for (const user of value) {
    if (!user.name || !user.email) {
      return Promise.reject('每个用户的信息必须完整');
    }
  }
  return Promise.resolve();
};
</script>

<template>
  <a-form :model="formState">
    <div v-for="(user, index) in formState.users" :key="index">
      <a-form-item label="姓名">
        <a-input v-model:value="user.name" />
      </a-form-item>
      <a-form-item label="邮箱">
        <a-input v-model:value="user.email" />
      </a-form-item>
      <a-button type="link" @click="removeUser(index)">删除</a-button>
    </div>
    <a-button type="dashed" @click="addUser">添加用户</a-button>
  </a-form>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：没有使用 a-form-item 包裹 -->
<a-input v-model:value="formState.username" />

<!-- ✅ 正确：使用 a-form-item 包裹 -->
<a-form-item name="username">
  <a-input v-model:value="formState.username" />
</a-form-item>

<!-- ❌ 错误：没有指定 name 属性 -->
<a-form-item label="用户名">
  <a-input v-model:value="formState.username" />
</a-form-item>

<!-- ✅ 正确：指定 name 属性 -->
<a-form-item label="用户名" name="username">
  <a-input v-model:value="formState.username" />
</a-form-item>

<!-- ❌ 错误：忘记在 a-form 上指定 :model 和 :rules -->
<a-form>
  <a-input v-model:value="formState.username" />
</a-form>

<!-- ✅ 正确：指定 :model 和 :rules -->
<a-form :model="formState" :rules="rules">
  <a-input v-model:value="formState.username" />
</a-form>
```

## Key Points

- 使用 `a-form` + `a-form-item` 结构
- 在 `a-form-item` 上指定 `name` 属性
- 使用 `rules` 属性定义验证规则
- 使用 `@finish` 处理表单提交
- 验证失败自动显示错误信息
