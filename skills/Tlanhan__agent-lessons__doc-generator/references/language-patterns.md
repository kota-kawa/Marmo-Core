# 编程语言识别规则

## 识别目标文件的语言

根据扩展名判断：
- `.py` → Python
- `.ts` / `.js` → TypeScript / JavaScript
- `.go` → Go
- `.java` → Java
- 其他 → 通用处理

---

## 各语言的文档提取规则

### Python
- 优先读取已有 docstring（`"""..."""`）
- 提取 `def` 和 `class` 定义
- 注意 `@` 装饰器（说明这是路由/属性/抽象方法等）
- 类型注解（`param: str`）直接用于参数类型文档

### TypeScript / JavaScript
- 优先读取已有 JSDoc（`/** ... */`）
- 提取 `function`、`const xx = () =>`、`class` 定义
- `interface` 和 `type` 定义需要单独记录
- `export` 的内容是公共 API，优先文档化

### Go
- 提取 `func` 定义
- 注意 receiver（`func (r Receiver) Method()`）说明所属类型
- 大写开头的函数/类型是导出的，优先文档化

---

## 优先级规则

1. 已有注释/docstring → 整理优化后使用
2. 函数签名 → 根据参数名和类型推断
3. 函数体逻辑 → 阅读实现来补充说明
4. 实在看不懂 → 标注 ⚠️ 待确认
