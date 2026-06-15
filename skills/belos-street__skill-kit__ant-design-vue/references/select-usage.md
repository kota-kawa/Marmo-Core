---
name: select-usage
description: Ant Design Vue Select 选择器的用法，包括单选、多选、搜索和远程数据。
official_doc: https://www.antdv.com/components/select
---

# Select 选择器

> Ant Design Vue Select 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';

const value = ref('lucy');

const options = [
  { value: 'jack', label: 'Jack' },
  { value: 'lucy', label: 'Lucy' },
  { value: 'tom', label: 'Tom' },
];
</script>

<template>
  <a-select v-model:value="value" :options="options" placeholder="请选择" />
</template>
```

## 单选

```vue
<script setup>
import { ref } from 'vue';

const value = ref(null);

const options = [
  { value: 'china', label: '中国' },
  { value: 'usa', label: '美国' },
  { value: 'japan', label: '日本' },
  { value: 'korea', label: '韩国' },
];
</script>

<template>
  <a-select v-model:value="value" :options="options" placeholder="请选择国家" />
</template>
```

## 多选

```vue
<script setup>
import { ref } from 'vue';

const value = ref(['china', 'japan']);

const options = [
  { value: 'china', label: '中国' },
  { value: 'usa', label: '美国' },
  { value: 'japan', label: '日本' },
  { value: 'korea', label: '韩国' },
];
</script>

<template>
  <a-select v-model:value="value" mode="multiple" :options="options" placeholder="请选择国家" />
</template>
```

## 带搜索

```vue
<script setup>
import { ref } from 'vue';

const value = ref(null);
const options = [
  { value: 'beijing', label: '北京' },
  { value: 'shanghai', label: '上海' },
  { value: 'guangzhou', label: '广州' },
  { value: 'shenzhen', label: '深圳' },
];
</script>

<template>
  <a-select
    v-model:value="value"
    :options="options"
    show-search
    placeholder="搜索城市"
    :filter-option="(input, option) =>
      option.label.toLowerCase().includes(input.toLowerCase())
    "
  />
</template>
```

## 远程搜索

```vue
<script setup>
import { ref, watch } from 'vue';
import { Select } from 'ant-design-vue';

const value = ref(null);
const options = ref([]);
const loading = ref(false);

const fetchOptions = async (search) => {
  if (!search) {
    options.value = [];
    return;
  }

  loading.value = true;
  try {
    const response = await fetch(`/api/search?q=${search}`);
    const data = await response.json();
    options.value = data.map(item => ({
      value: item.id,
      label: item.name,
    }));
  } finally {
    loading.value = false;
  }
};

watch(value, (val) => {
  console.log('Selected:', val);
});
</script>

<template>
  <a-select
    v-model:value="value"
    show-search
    :options="options"
    placeholder="搜索并选择"
    :loading="loading"
    :filter-option="false"
    @search="fetchOptions"
  />
</template>
```

## 分组

```vue
<script setup>
import { ref } from 'vue';

const value = ref(null);

const options = [
  {
    label: '水果',
    options: [
      { value: 'apple', label: '苹果' },
      { value: 'banana', label: '香蕉' },
    ],
  },
  {
    label: '蔬菜',
    options: [
      { value: 'carrot', label: '胡萝卜' },
      { value: 'tomato', label: '番茄' },
    ],
  },
];
</script>

<template>
  <a-select v-model:value="value" :options="options" placeholder="请选择" />
</template>
```

## 允许创建

```vue
<script setup>
import { ref } from 'vue';

const value = ref([]);
const options = [
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
];

const handleKeyDown = (e) => {
  if (e.key === 'Enter') {
    const inputValue = e.target.value;
    if (inputValue && !options.value.find(opt => opt.label === inputValue)) {
      options.value.push({ value: inputValue, label: inputValue });
      value.value.push(inputValue);
    }
    e.target.value = '';
  }
};
</script>

<template>
  <a-select v-model:value="value" mode="tags" :options="options" placeholder="输入并按 Enter">
    <template #dropdownRender="{ menuNode: menu }">
      <component :is="menu" />
      <a-divider style="margin: 4px 0" />
      <div style="padding: 8px" @click="handleKeyDown">
        <a-input placeholder="输入新选项并按 Enter" />
      </div>
    </template>
  </a-select>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：忘记指定 v-model -->
<a-select :options="options" />

<!-- ✅ 正确：指定 v-model -->
<a-select v-model:value="value" :options="options" />

<!-- ❌ 错误：多选时 v-model 类型不对 -->
<!-- value 应该是数组 -->
<a-select v-model:value="value" mode="multiple" />

<!-- ❌ 错误：options 结构不对 -->
<!-- options 应该是 { value, label } 数组 -->
```

## Key Points

- 使用 `v-model:value` 绑定值
- `options` 格式：`{ value, label }[]`
- 多选使用 `mode="multiple"`
- 搜索使用 `show-search` + `filter-option`
- 远程搜索结合 `@search` + `:filter-option="false"`
