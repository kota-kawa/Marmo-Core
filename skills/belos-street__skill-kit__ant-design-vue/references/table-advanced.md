---
name: table-advanced
description: Ant Design Vue Table 表格的高级用法，包括自定义列、分页、排序、筛选、行选择等。
official_doc: https://www.antdv.com/components/table
---

# Table 高级用法

> Ant Design Vue Table 组件的高级用法。

## 基础表格

```vue
<script setup>
import { ref } from 'vue';

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Age', dataIndex: 'age', key: 'age' },
  { title: 'Address', dataIndex: 'address', key: 'address' },
];

const data = [
  { key: '1', name: 'John Brown', age: 32, address: 'New York No. 1 Lake Park' },
  { key: '2', name: 'Jim Green', age: 42, address: 'London No. 1 Lake Park' },
  { key: '3', name: 'Joe Black', age: 32, address: 'Sydney No. 1 Lake Park' },
];
</script>

<template>
  <a-table :columns="columns" :data-source="data" />
</template>
```

## 自定义列渲染

```vue
<script setup>
import { ref } from 'vue';
import { Tag } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Age', dataIndex: 'age', key: 'age' },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    slots: { customRender: 'status' },
  },
  {
    title: 'Action',
    key: 'action',
    slots: { customRender: 'action' },
  },
];

const data = ref([
  { key: '1', name: 'John', age: 32, status: 'active' },
  { key: '2', name: 'Jim', age: 42, status: 'inactive' },
]);

const handleEdit = (record) => {
  console.log('Edit:', record);
};

const handleDelete = (record) => {
  console.log('Delete:', record);
};
</script>

<template>
  <a-table :columns="columns" :data-source="data">
    <template #bodyCell="{ column, record }">
      <template v-if="column.key === 'status'">
        <Tag :color="record.status === 'active' ? 'green' : 'red'">
          {{ record.status === 'active' ? 'Active' : 'Inactive' }}
        </Tag>
      </template>
      <template v-else-if="column.key === 'action'">
        <a @click="handleEdit(record)">
          <EditOutlined /> 编辑
        </a>
        <a-divider type="vertical" />
        <a @click="handleDelete(record)">
          <DeleteOutlined /> 删除
        </a>
      </template>
    </template>
  </a-table>
</template>
```

## 排序

```vue
<script setup>
import { ref } from 'vue';

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name', sorter: true },
  { title: 'Age', dataIndex: 'age', key: 'age', sorter: (a, b) => a.age - b.age },
  { title: 'Address', dataIndex: 'address', key: 'address' },
];

const data = [
  { key: '1', name: 'John', age: 32, address: 'New York' },
  { key: '2', name: 'Jim', age: 42, address: 'London' },
  { key: '3', name: 'Joe', age: 11, address: 'Sydney' },
];
</script>

<template>
  <a-table :columns="columns" :data-source="data" />
</template>
```

## 筛选

```vue
<script setup>
import { ref } from 'vue';

const columns = [
  {
    title: 'Name',
    dataIndex: 'name',
    key: 'name',
    filters: [
      { text: 'John', value: 'John' },
      { text: 'Jim', value: 'Jim' },
    ],
    onFilter: (value, record) => record.name.includes(value),
  },
  { title: 'Age', dataIndex: 'age', key: 'age' },
  { title: 'Address', dataIndex: 'address', key: 'address' },
];

const data = [
  { key: '1', name: 'John Brown', age: 32, address: 'New York' },
  { key: '2', name: 'Jim Green', age: 42, address: 'London' },
];
</script>

<template>
  <a-table :columns="columns" :data-source="data" />
</template>
```

## 分页

```vue
<script setup>
import { ref } from 'vue';

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 100,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total) => `共 ${total} 条`,
});

const handleTableChange = (pag) => {
  pagination.value.current = pag.current;
  pagination.value.pageSize = pag.pageSize;
  // 重新请求数据
  fetchData();
};
</script>

<template>
  <a-table
    :columns="columns"
    :data-source="data"
    :pagination="pagination"
    @change="handleTableChange"
  />
</template>
```

## 行选择

```vue
<script setup>
import { ref } from 'vue';

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Age', dataIndex: 'age', key: 'age' },
];

const data = [
  { key: '1', name: 'John', age: 32 },
  { key: '2', name: 'Jim', age: 42 },
];

const selectedRowKeys = ref([]);
const loading = ref(false);

const rowSelection = {
  selectedRowKeys,
  onChange: (keys, rows) => {
    console.log('Selected keys:', keys);
    console.log('Selected rows:', rows);
  },
};

const handleBatchDelete = () => {
  console.log('Delete selected:', selectedRowKeys.value);
};
</script>

<template>
  <a-table
    :columns="columns"
    :data-source="data"
    :row-selection="rowSelection"
  >
    <template #headerCell="{ column }">
      <template v-if="column.key === 'action'">
        <a-button type="primary" danger size="small" @click="handleBatchDelete">
          批量删除 ({{ selectedRowKeys.length }})
        </a-button>
      </template>
    </template>
  </a-table>
</template>
```

## 可编辑行

```vue
<script setup>
import { ref, reactive } from 'vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name', edit: true },
  { title: 'Age', dataIndex: 'age', key: 'age', edit: true },
  { title: 'Action', key: 'action' },
];

const data = reactive([
  { key: '1', name: 'John', age: 32 },
  { key: '2', name: 'Jim', age: 42 },
]);

const editingKey = ref('');

const edit = (key) => {
  editingKey.value = key;
};

const save = (record) => {
  editingKey.value = '';
  console.log('Save:', record);
};
</script>

<template>
  <a-table :columns="columns" :data-source="data">
    <template #bodyCell="{ column, record }">
      <template v-if="column.edit && editingKey === record.key">
        <a-input v-model:value="record[column.dataIndex]" style="width: 100px" />
        <a @click="save(record)">Save</a>
      </template>
      <template v-else-if="column.key === 'action'">
        <a @click="edit(record.key)">Edit</a>
      </template>
      <template v-else>
        {{ record[column.dataIndex] }}
      </template>
    </template>
  </a-table>
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：忘记指定 key 属性 -->
<!-- data-source 中的每项必须有唯一的 key -->

<!-- ❌ 错误：slots 使用错误 -->
<!-- 应该用 bodyCell，不是 default -->

<!-- ❌ 错误：分页属性写错 -->
<!-- ❌ :pagination="true" -->
<!-- ✅ :pagination="pagination" -->
```

## Key Points

- 数据项必须有 `key` 属性
- 使用 `bodyCell` slot 自定义列
- 使用 `sorter` 启用排序
- 使用 `filters` 启用筛选
- 分页配置是对象，不是布尔值
- 使用 `row-selection` 启用行选择
