---
name: tree-usage
description: Ant Design Vue Tree 树形组件的用法，包括基本数据、勾选、异步加载和自定义节点。
official_doc: https://www.antdv.com/components/tree
---

# Tree 树形组件

> Ant Design Vue Tree 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';

const treeData = ref([
  {
    title: 'parent 1',
    key: '0-0',
    children: [
      { title: 'child 1', key: '0-0-0' },
      { title: 'child 2', key: '0-0-1' },
    ],
  },
  {
    title: 'parent 2',
    key: '0-1',
    children: [
      { title: 'child 2-1', key: '0-1-0' },
      { title: 'child 2-2', key: '0-1-1' },
    ],
  },
]);
</script>

<template>
  <a-tree :tree-data="treeData" />
</template>
```

## 可勾选

```vue
<script setup>
import { ref } from 'vue';

const checkedKeys = ref(['0-0-0']);

const treeData = ref([
  {
    title: 'parent 1',
    key: '0-0',
    children: [
      { title: 'child 1', key: '0-0-0' },
      { title: 'child 2', key: '0-0-1' },
    ],
  },
]);

const onCheck = (checkedKeys, info) => {
  console.log('Checked keys:', checkedKeys);
  console.log('Info:', info);
};
</script>

<template>
  <a-tree
    v-model:checked-keys="checkedKeys"
    :tree-data="treeData"
    checkable
    @check="onCheck"
  />
</template>
```

## 可选中

```vue
<script setup>
import { ref } from 'vue';

const selectedKeys = ref([]);

const treeData = ref([
  {
    title: 'parent 1',
    key: '0-0',
    children: [
      { title: 'child 1', key: '0-0-0' },
      { title: 'child 2', key: '0-0-1' },
    ],
  },
]);

const onSelect = (selectedKeys, info) => {
  console.log('Selected:', selectedKeys);
};
</script>

<template>
  <a-tree
    v-model:selected-keys="selectedKeys"
    :tree-data="treeData"
    @select="onSelect"
  />
</template>
```

## 异步加载

```vue
<script setup>
import { ref } from 'vue';

const treeData = ref([
  {
    title: 'parent 1',
    key: '0-0',
    children: [],
  },
]);

const loadData = (treeNode) => {
  return new Promise((resolve) => {
    if (treeNode.children && treeNode.children.length > 0) {
      resolve();
      return;
    }

    // 模拟异步加载
    setTimeout(() => {
      treeNode.children = [
        { title: 'child 1', key: `${treeNode.key}-0` },
        { title: 'child 2', key: `${treeNode.key}-1` },
      ];
      resolve();
    }, 1000);
  });
};
</script>

<template>
  <a-tree :tree-data="treeData" :load-data="loadData" />
</template>
```

## 自定义节点

```vue
<script setup>
import { ref } from 'vue';
import { FileTextOutlined, FolderOutlined, FilePdfOutlined } from '@ant-design/icons-vue';

const treeData = ref([
  {
    title: 'Documents',
    key: '0-0',
    icon: () => <FolderOutlined />,
    children: [
      {
        title: 'report.pdf',
        key: '0-0-0',
        icon: () => <FilePdfOutlined />,
        isLeaf: true,
      },
      {
        title: 'notes.txt',
        key: '0-0-1',
        icon: () => <FileTextOutlined />,
        isLeaf: true,
      },
    ],
  },
]);
</script>

<template>
  <a-tree :tree-data="treeData" show-icon />
</template>
```

## 受控模式

```vue
<script setup>
import { ref } from 'vue';

const expandedKeys = ref(['0-0']);
const checkedKeys = ref([]);

const treeData = ref([
  {
    title: 'parent 1',
    key: '0-0',
    children: [
      { title: 'child 1', key: '0-0-0' },
      { title: 'child 2', key: '0-0-1' },
    ],
  },
]);

const onExpand = (keys) => {
  expandedKeys.value = keys;
};

const onCheck = (keys) => {
  checkedKeys.value = keys;
};
</script>

<template>
  <a-tree
    v-model:expanded-keys="expandedKeys"
    v-model:checked-keys="checkedKeys"
    :tree-data="treeData"
    checkable
    @expand="onExpand"
    @check="onCheck"
  />
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：忘记唯一的 key -->
<!-- 每个节点必须有唯一的 key -->

<!-- ❌ 错误：使用 title 而不是 title -->
<!-- 节点属性应该是 title 和 key -->

<!-- ✅ 正确数据结构 -->
{
  title: '节点名称',  // 显示文本
  key: 'unique-key',  // 唯一标识
  children: []         // 子节点
}
```

## Key Points

- 每个节点必须有唯一的 `key`
- 使用 `title` 显示文本
- 使用 `children` 定义子节点
- 使用 `loadData` 实现异步加载
- 使用 `icon` slot 自定义图标
- 使用 `checkable` 启用勾选
- 使用 `show-icon` 显示图标
