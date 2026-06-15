---
name: upload-usage
description: Ant Design Vue Upload 上传组件的用法，包括基本上传、拖拽上传、图片预览等。
official_doc: https://www.antdv.com/components/upload
---

# Upload 上传组件

> Ant Design Vue Upload 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';
import { UploadOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

const fileList = ref([]);

const handleChange = (info) => {
  if (info.file.status === 'done') {
    message.success(`${info.file.name} 上传成功`);
  } else if (info.file.status === 'error') {
    message.error(`${info.file.name} 上传失败`);
  }
};
</script>

<template>
  <a-upload
    v-model:file-list="fileList"
    action="/api/upload"
    @change="handleChange"
  >
    <a-button>
      <template #icon><UploadOutlined /></template>
      上传文件
    </a-button>
  </a-upload>
</template>
```

## 拖拽上传

```vue
<script setup>
import { ref } from 'vue';
import { InboxOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

const dragFileList = ref([]);

const props = {
  name: 'file',
  multiple: true,
  action: '/api/upload',
  onChange(info) {
    const { fileList } = info;
    const newList = fileList.slice(-3);
    dragFileList.value = newList;

    if (info.file.status === 'done') {
      message.success(`${info.file.name} 上传成功`);
    } else if (info.file.status === 'error') {
      message.error(`${info.file.name} 上传失败`);
    }
  },
};
</script>

<template>
  <a-upload-dragger
    v-model:file-list="dragFileList"
    v-bind="props"
  >
    <p class="ant-upload-drag-icon">
      <InboxOutlined />
    </p>
    <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
    <p class="ant-upload-hint">支持单个或批量上传</p>
  </a-upload-dragger>
</template>
```

## 图片上传预览

```vue
<script setup>
import { ref } from 'vue';
import { UploadOutlined, DeleteOutlined } from '@ant-design/icons-vue';

const fileList = ref([
  {
    uid: '-1',
    name: 'image.png',
    status: 'done',
    url: 'https://www.example.com/image.png',
  },
]);

const handleChange = ({ fileList: newFileList }) => {
  fileList.value = newFileList;
};

const handlePreview = async (file) => {
  const url = file.url || await createPreviewUrl(file.originFileObj);
  window.open(url);
};

const createPreviewUrl = (file) => {
  return URL.createObjectURL(file);
};
</script>

<template>
  <a-upload
    v-model:file-list="fileList"
    action="/api/upload"
    list-type="picture-card"
    @preview="handlePreview"
    @change="handleChange"
  >
    <div v-if="fileList.length < 8">
      <UploadOutlined />
      <div class="ant-upload-text">上传</div>
    </div>
  </a-upload>
</template>
```

## 手动上传

```vue
<script setup>
import { ref } from 'vue';
import { UploadOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

const fileList = ref([]);
const uploading = ref(false);

const handleUpload = () => {
  const formData = new FormData();
  fileList.value.forEach((file) => {
    formData.append('files[]', file);
  });

  uploading.value = true;

  fetch('/api/upload', {
    method: 'POST',
    body: formData,
  })
    .then((response) => response.json())
    .then(() => {
      message.success('上传成功');
      fileList.value = [];
    })
    .catch(() => {
      message.error('上传失败');
    })
    .finally(() => {
      uploading.value = false;
    });
};
</script>

<template>
  <a-upload
    v-model:file-list="fileList"
    :before-upload="() => false"
  >
    <a-button>
      <template #icon><UploadOutlined /></template>
      选择文件
    </a-button>
  </a-upload>

  <a-button
    type="primary"
    :loading="uploading"
    :disabled="fileList.length === 0"
    style="margin-top: 16px"
    @click="handleUpload"
  >
    {{ uploading ? '上传中' : '开始上传' }}
  </a-button>
</template>
```

## 限制上传

```vue
<script setup>
import { ref } from 'vue';
import { UploadOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

const fileList = ref([]);

const beforeUpload = (file) => {
  const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
  if (!isJpgOrPng) {
    message.error('只能上传 JPG/PNG 文件!');
    return false;
  }

  const isLt2M = file.size / 1024 / 1024 < 2;
  if (!isLt2M) {
    message.error('图片必须小于 2MB!');
    return false;
  }

  // 返回 false 阻止自动上传，手动处理
  return true;
};

const handleChange = (info) => {
  if (info.file.status === 'done') {
    message.success(`${info.file.name} 上传成功`);
  }
};
</script>

<template>
  <a-upload
    v-model:file-list="fileList"
    :before-upload="beforeUpload"
    :max-count="3"
    @change="handleChange"
  >
    <a-button>
      <template #icon><UploadOutlined /></template>
      上传 (最多3张)
    </a-button>
  </a-upload>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：手动上传时返回 true 但没有手动处理 -->
<!-- 返回 true 会自动上传，需要返回 false -->

<!-- ❌ 错误：使用 v-model 而不是 v-model:file-list -->
<!-- <a-upload v-model="fileList"> -->

<!-- ✅ 正确：使用 v-model:file-list -->
<a-upload v-model:file-list="fileList">

<!-- ❌ 错误：beforeUpload 返回 Promise 但 reject -->
<!-- 应该返回 false 阻止上传，或返回 true 继续 -->
const beforeUpload = async (file) => {
  const valid = await validate(file);
  return valid; // true 继续，false 阻止
};
```

## Key Points

- 使用 `v-model:file-list` 绑定文件列表
- 手动上传返回 `false` 在 `beforeUpload`
- 使用 `action` 指定上传地址
- 使用 `before-upload` 验证文件
- 使用 `list-type` 控制显示样式
- 使用 `@change` 处理状态变化
