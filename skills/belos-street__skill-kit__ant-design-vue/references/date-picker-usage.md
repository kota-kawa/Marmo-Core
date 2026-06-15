---
name: date-picker-usage
description: Ant Design Vue DatePicker 日期选择器的用法，包括日期范围、格式化、禁用日期等。
official_doc: https://www.antdv.com/components/date-picker
---

# DatePicker 日期选择器

> Ant Design Vue DatePicker 组件的正确用法。

## 基础用法

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const date = ref(null);
</script>

<template>
  <a-date-picker v-model:value="date" />
</template>
```

## 格式化

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const date = ref(null);

const format = 'YYYY-MM-DD';
const formatChinese = 'YYYY年MM月DD日';
</script>

<template>
  <a-date-picker v-model:value="date" :format="format" />
  <a-date-picker v-model:value="date" :format="formatChinese" />
</template>
```

## 日期范围选择

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const rangeValue = ref([]);
</script>

<template>
  <a-range-picker v-model:value="rangeValue" />
</template>
```

## 预设范围

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const value = ref([]);

const presets = [
  { label: '今天', value: [dayjs(), dayjs()] },
  { label: '本周', value: [dayjs().startOf('week'), dayjs().endOf('week')] },
  { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
  { label: '本年', value: [dayjs().startOf('year'), dayjs().endOf('year')] },
];
</script>

<template>
  <a-range-picker
    v-model:value="value"
    :presets="presets"
    format="YYYY-MM-DD"
  />
</template>
```

## 禁用日期

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const date = ref(null);

const disabledDate = (current) => {
  // 禁用今天之前的日期
  return current && current < dayjs().endOf('day');
};

const disabledRangeDate = (current) => {
  // 禁用 2024-03-01 之前的日期
  return current && current < dayjs('2024-03-01');
};
</script>

<template>
  <a-date-picker
    v-model:value="date"
    :disabled-date="disabledDate"
    placeholder="选择日期"
  />
</template>
```

## 日期时间选择

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const dateTime = ref(null);
</script>

<template>
  <a-date-picker
    v-model:value="dateTime"
    show-time
    format="YYYY-MM-DD HH:mm:ss"
    placeholder="选择日期时间"
  />
</template>
```

## 选择周

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const week = ref(null);
</script>

<template>
  <a-date-picker
    v-model:value="week"
    picker="week"
    format="YYYY 第 WW 周"
    placeholder="选择周"
  />
</template>
```

## 选择月份

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const month = ref(null);
</script>

<template>
  <a-date-picker
    v-model:value="month"
    picker="month"
    format="YYYY-MM"
    placeholder="选择月份"
  />
</template>
```

## 选择季度

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const quarter = ref(null);
</script>

<template>
  <a-date-picker
    v-model:value="quarter"
    picker="quarter"
    format="YYYY [Q]Q"
    placeholder="选择季度"
  />
</template>
```

## 选择年份

```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const year = ref(null);
</script>

<template>
  <a-date-picker
    v-model:value="year"
    picker="year"
    format="YYYY"
    placeholder="选择年份"
  />
</template>
```

## 常见错误

```vue
<!-- ❌ 错误：忘记安装 dayjs -->
<!-- DatePicker 需要 dayjs 作为依赖 -->

<!-- ❌ 错误：值类型不是 dayjs -->
<!-- value 应该是 dayjs 对象，不是 Date 或 string -->

<!-- ✅ 正确：使用 dayjs -->
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';

const date = ref(dayjs('2024-03-15'));
</script>

<!-- ❌ 错误：范围选择器的值格式不对 -->
<!-- 范围选择器的值应该是 [dayjs, dayjs] -->
```

## Key Points

- 需要安装 `dayjs`
- 值类型是 `dayjs` 对象，不是 `Date`
- 使用 `format` 属性设置显示格式
- 使用 `disabledDate` 属性禁用特定日期
- 范围选择器值类型是 `[dayjs, dayjs]`
- 使用 `picker` 属性选择周/月/季度/年份
