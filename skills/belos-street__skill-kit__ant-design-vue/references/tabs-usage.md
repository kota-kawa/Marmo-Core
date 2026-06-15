---
name: tabs-usage
description: Ant Design Vue Tabs component usage patterns and best practices
---

# Tabs Usage

> Tabs make it easy to switch between different views or content sections within the same context.

**Official Docs**: https://www.antdv.com/components/tabs

## Basic Usage

### Default Tabs

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <a-tab-pane key="1" tab="Tab 1">Content of Tab Pane 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2">Content of Tab Pane 2</a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">Content of Tab Pane 3</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
const activeKey = ref('1');
</script>
```

### Disabled Tab

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <a-tab-pane key="1" tab="Tab 1">Tab 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2" disabled>Tab 2</a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">Tab 3</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
const activeKey = ref('1');
</script>
```

### Centered Tabs

```vue
<template>
  <a-tabs v-model:activeKey="activeKey" centered>
    <a-tab-pane key="1" tab="Tab 1">Content of Tab Pane 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2" force-render>Content of Tab Pane 2</a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">Content of Tab Pane 3</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
const activeKey = ref('1');
</script>
```

## Tabs with Icons

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <a-tab-pane key="1">
      <template #tab>
        <span>
          <apple-outlined />
          Tab 1
        </span>
      </template>
      Tab 1
    </a-tab-pane>
    <a-tab-pane key="2">
      <template #tab>
        <span>
          <android-outlined />
          Tab 2
        </span>
      </template>
      Tab 2
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { AppleOutlined, AndroidOutlined } from '@ant-design/icons-vue';
import { ref } from 'vue';
const activeKey = ref('1');
</script>
```

## Tab Position

### Horizontal and Vertical

```vue
<template>
  <div>
    <a-radio-group v-model:value="mode" :style="{ marginBottom: '8px' }">
      <a-radio-button value="top">Horizontal</a-radio-button>
      <a-radio-button value="left">Vertical</a-radio-button>
    </a-radio-group>
    <a-tabs
      v-model:activeKey="activeKey"
      :tab-position="mode"
      :style="{ height: '200px' }"
      @tabScroll="callback"
    >
      <a-tab-pane v-for="i in 30" :key="i" :tab="`Tab-${i}`">Content of tab {{ i }}</a-tab-pane>
    </a-tabs>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import type { TabsProps } from 'ant-design-vue';
const mode = ref<TabsProps['tabPosition']>('top');
const activeKey = ref(1);
const callback: TabsProps['onTabScroll'] = val => {
  console.log(val);
};
</script>
```

### All Positions

```vue
<template>
  <a-radio-group v-model:value="tabPosition" style="margin: 8px">
    <a-radio-button value="top">top</a-radio-button>
    <a-radio-button value="bottom">bottom</a-radio-button>
    <a-radio-button value="left">left</a-radio-button>
    <a-radio-button value="right">right</a-radio-button>
  </a-radio-group>
  <a-tabs v-model:activeKey="activeKey" :tab-position="tabPosition" animated>
    <a-tab-pane key="1" tab="Tab 1">Content of Tab 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2">Content of Tab 2</a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">Content of Tab 3</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import { TabsProps } from 'ant-design-vue/es/tabs';
const tabPosition = ref<TabsProps['tabPosition']>('top');
const activeKey = ref('1');
</script>
```

## Tab Size

```vue
<template>
  <div>
    <a-radio-group v-model:value="size" style="margin-bottom: 16px">
      <a-radio-button value="small">Small</a-radio-button>
      <a-radio-button value="default">Default</a-radio-button>
      <a-radio-button value="large">Large</a-radio-button>
    </a-radio-group>
    <a-tabs v-model:activeKey="activeKey" :size="size">
      <a-tab-pane key="1" tab="Tab 1">Content of tab 1</a-tab-pane>
      <a-tab-pane key="2" tab="Tab 2">Content of tab 2</a-tab-pane>
      <a-tab-pane key="3" tab="Tab 3">Content of tab 3</a-tab-pane>
    </a-tabs>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import type { TabsProps } from 'ant-design-vue';
const size = ref<TabsProps['size']>('small');
const activeKey = ref('1');
</script>
```

## Card Style Tabs

```vue
<template>
  <a-tabs v-model:activeKey="activeKey" type="card">
    <a-tab-pane key="1" tab="Tab 1">Content of Tab Pane 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2">Content of Tab Pane 2</a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">Content of Tab Pane 3</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
const activeKey = ref('1');
</script>
```

## Editable Tabs

```vue
<template>
  <a-tabs
    v-model:activeKey="activeKey"
    type="editable-card"
    @edit="onEdit"
  >
    <a-tab-pane
      v-for="pane in panes"
      :key="pane.key"
      :tab="pane.title"
      :closable="pane.closable"
    >
      {{ pane.content }}
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import type { TabsProps } from 'ant-design-vue';

interface PaneType {
  key: string;
  title: string;
  content: string;
  closable?: boolean;
}

const activeKey = ref('1');
const panes = ref<PaneType[]>([
  { key: '1', title: 'Tab 1', content: 'Content of Tab Pane 1', closable: false },
  { key: '2', title: 'Tab 2', content: 'Content of Tab Pane 2', closable: true },
]);

let newTabIndex = 3;

const onEdit: TabsProps['onEdit'] = (targetKey, action) => {
  if (action === 'add') {
    const newKey = `${newTabIndex++}`;
    panes.value.push({
      key: newKey,
      title: `Tab ${newKey}`,
      content: `Content of Tab Pane ${newKey}`,
      closable: true,
    });
    activeKey.value = newKey;
  } else if (action === 'remove') {
    const index = panes.value.findIndex(pane => pane.key === targetKey);
    if (index !== -1) {
      panes.value.splice(index, 1);
      if (activeKey.value === targetKey && panes.value.length > 0) {
        activeKey.value = panes.value[Math.max(0, index - 1)].key;
      }
    }
  }
};
</script>
```

## Custom Tab Bar

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <template #tabBar="{ panes, activeKey, onTabClick }">
      <div class="custom-tab-bar">
        <div
          v-for="pane in panes"
          :key="pane.key"
          class="custom-tab"
          :class="{ 'custom-tab-active': activeKey === pane.key }"
          @click="onTabClick(pane.key)"
        >
          {{ pane.tab }}
        </div>
      </div>
    </template>
    <a-tab-pane key="1" tab="Tab 1">Content 1</a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2">Content 2</a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
const activeKey = ref('1');
</script>

<style scoped>
.custom-tab-bar {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.custom-tab {
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
}

.custom-tab:hover {
  background: #fff;
}

.custom-tab-active {
  background: #fff;
  color: #1890ff;
  font-weight: 500;
}
</style>
```

## Lazy Loading Content

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <a-tab-pane key="1" tab="Tab 1">
      <component :is="Tab1Component" v-if="activeKey === '1'" />
    </a-tab-pane>
    <a-tab-pane key="2" tab="Tab 2" force-render>
      <component :is="Tab2Component" v-if="activeKey === '2'" />
    </a-tab-pane>
    <a-tab-pane key="3" tab="Tab 3">
      <component :is="Tab3Component" v-if="activeKey === '3'" />
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import Tab1Component from './Tab1.vue';
import Tab2Component from './Tab2.vue';
import Tab3Component from './Tab3.vue';

const activeKey = ref('1');
</script>
```

## Common Patterns

### Form in Tabs

```vue
<template>
  <a-tabs v-model:activeKey="activeKey">
    <a-tab-pane key="1" tab="Basic Info">
      <a-form :model="form.basic">
        <a-form-item label="Name">
          <a-input v-model:value="form.basic.name" />
        </a-form-item>
      </a-form>
    </a-tab-pane>
    <a-tab-pane key="2" tab="Advanced Settings">
      <a-form :model="form.advanced">
        <a-form-item label="Description">
          <a-textarea v-model:value="form.advanced.description" />
        </a-form-item>
      </a-form>
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue';

const activeKey = ref('1');
const form = reactive({
  basic: { name: '' },
  advanced: { description: '' },
});
</script>
```

### Table in Tabs

```vue
<template>
  <a-tabs v-model:activeKey="activeKey" type="card">
    <a-tab-pane key="1" tab="All Tasks">
      <a-table :columns="columns" :data-source="allTasks" />
    </a-tab-pane>
    <a-tab-pane key="2" tab="Pending">
      <a-table :columns="columns" :data-source="pendingTasks" />
    </a-tab-pane>
    <a-tab-pane key="3" tab="Completed">
      <a-table :columns="columns" :data-source="completedTasks" />
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';

const activeKey = ref('1');
const tasks = ref([...]);

const allTasks = computed(() => tasks.value);
const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending'));
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed'));

const columns = [...];
</script>
```

## Best Practices

1. **Use meaningful keys**: Use descriptive keys instead of indexes for better maintainability
2. **Limit tab count**: Keep tabs under 7-8 for better usability
3. **Use force-render**: For complex content, use `force-render` to render all tabs upfront
4. **Lazy load content**: For heavy content, conditionally render based on active tab
5. **Consistent styling**: Match tab style with overall design (card vs line)
6. **Mobile consideration**: Tabs switch to top position automatically on mobile
7. **Accessibility**: Ensure tab content is accessible via keyboard navigation

## Common Issues

### Tab Content Not Rendering

**Problem**: Content doesn't render when switching tabs.

**Solution**: Use `force-render` prop:
```vue
<a-tab-pane key="2" tab="Tab 2" force-render>
  Content that needs to render immediately
</a-tab-pane>
```

### Losing State on Tab Switch

**Problem**: Form data or component state is lost when switching tabs.

**Solution**: Keep components mounted or use Vuex/Pinia for state:
```vue
<!-- Keep mounted -->
<a-tab-pane key="1" tab="Tab 1" force-render>
  <FormComponent />
</a-tab-pane>

<!-- Or use store -->
<script setup>
const formData = useStore().formData;
</script>
```

### Too Many Tabs

**Problem**: More than 8-10 tabs makes UI cluttered.

**Solution**: Use scrollable tabs or reorganize content:
```vue
<a-tabs v-model:activeKey="activeKey" :tab-position="'top'">
  <!-- Many tabs will auto-scroll -->
</a-tabs>
```

## Key Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `v-model:activeKey` | string | - | Current active tab key |
| `type` | string | 'line' | Tab style: 'line' or 'card' |
| `tab-position` | string | 'top' | Position: 'top', 'bottom', 'left', 'right' |
| `size` | string | 'default' | Size: 'small', 'default', 'large' |
| `centered` | boolean | false | Center tabs |
| `animated` | boolean | true | Enable animation |
| `destroy-inactive-tab-pane` | boolean | false | Destroy inactive tabs |

## Key Events

| Event | Parameters | Description |
|-------|------------|-------------|
| `@change` | (activeKey: string) | Triggered when tab changes |
| `@tabClick` | (clickedKey: string) | Triggered when tab is clicked |
| `@edit` | (targetKey: string, action: string) | For editable tabs |
| `@tabScroll` | (event) | Triggered when tabs are scrolled |
