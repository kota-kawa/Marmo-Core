---
name: "lessons-to-slides"
description: "当用户说'生成幻灯片'、'做成PPT'、'生成slides'、'课程转演示文稿'时触发。将 lessons/ 目录下的课程文件转换为 Marp HTML 幻灯片。"
---

# 课程 → 幻灯片转换器

## 目标

将 `lessons/` 下的 Markdown 课程文件，转换为可直接演示的 Marp HTML 幻灯片。

---

## 第零步：确认环境

用 Bash 工具运行：
```bash
marp --version
```

如果输出 NOT_INSTALLED 或报错，告知用户：
```
请先安装 Marp CLI：npm install -g @marp-team/marp-cli
```
然后停止，不继续执行。

---

## 第一步：收集课程文件

用 Glob 工具找出 `lessons/` 下所有 `.md` 文件，按文件名排序（module1 → module7）。
用 Read 工具依次读取每个文件内容。

---

## 第二步：写出自定义主题

用 Write 工具创建 `slides/theme.css`，内容如下：

```css
/* @theme agent-course */
@import 'gaia';

:root {
  --color-background: #1a1a2e;
  --color-background-code: #16213e;
  --color-foreground: #e8e8e8;
  --color-highlight: #0f3460;
  --color-dimmed: #888;
}

section {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 28px;
  padding: 50px 60px;
}

section h1 {
  color: #e94560;
  font-size: 48px;
  border-bottom: 3px solid #e94560;
  padding-bottom: 16px;
}

section h2 {
  color: #0f9b8e;
  font-size: 36px;
}

section h3 {
  color: #e8c87a;
  font-size: 30px;
}

section code {
  background: #0f3460;
  color: #e94560;
  padding: 2px 8px;
  border-radius: 4px;
}

section pre {
  background: #16213e;
  border-left: 4px solid #e94560;
  border-radius: 8px;
}

section pre code {
  background: transparent;
  color: #e8e8e8;
  padding: 0;
}

section table {
  font-size: 24px;
}

section th {
  background: #0f3460;
  color: #e8c87a;
}

section blockquote {
  border-left: 4px solid #e94560;
  color: #aaa;
  font-style: italic;
}

section.title-slide {
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}

section.title-slide h1 {
  font-size: 56px;
  border: none;
}
```

---

## 第三步：逐个处理课程文件

对每个读取到的课程文件，执行以下处理后，用 Write 工具写出到 `slides/src/` 目录：

### 处理规则

**① 在文件最开头插入 Marp frontmatter**（替换掉原文件没有的 frontmatter）：
```
---
marp: true
theme: agent-course
paginate: true
---
```

**② 在 frontmatter 之后、正文之前，插入一张封面页**：
```markdown

<!-- _class: title-slide -->

# [原文件的一级标题内容]

---
```

**③ 删除文件末尾的导航链接**：
删除包含 `*上一课：` 或 `*下一课：` 的行（这些链接在幻灯片里没用）。

**④ 其余内容保持不变**，`---` 已经是 Marp 的换页符，无需额外处理。

### 输出文件命名

按原文件名，写入 `slides/src/` 目录：
- 原文件：`lessons/module1-what-is-agent.md`
- 写出为：`slides/src/module1-what-is-agent.md`

---

## 第四步：生成 HTML 幻灯片

用 Bash 工具运行：

```bash
for f in slides/src/module*.md; do
  marp "$f" --html --theme slides/theme.css \
    --output "slides/html/$(basename ${f%.md}).html" \
    --allow-local-files
done
```

> 注意：Marp 批量转换时不能同时指定 --output 目录，需要逐个处理。

等待命令完成。

---

## 第五步：生成合并版（完整课程一个文件）

用 Write 工具创建 `slides/src/full-course.md`：

内容为所有课程文件处理后的内容，按顺序拼接。文件最开头加总封面：

```markdown
---
marp: true
theme: agent-course
paginate: true
---

<!-- _class: title-slide -->

# AI Agent & Skill
## 从零到实战完整课程

---
```

然后依次追加每个模块处理后的正文内容（去掉每个文件自己的 frontmatter，保留正文）。

用 Bash 工具运行生成 HTML：

```bash
marp slides/src/full-course.md \
  --html \
  --theme slides/theme.css \
  --output slides/html/full-course.html \
  --allow-local-files
```

---

## 第六步：生成导航首页 index.html

用 Write 工具创建 `slides/html/index.html`，内容为一个 HTML 导航页，包含：

- 页面标题：「AI Agent & Skill 课程导航」
- 一个醒目的「▶ 播放完整课程」按钮，链接到 `full-course.html`
- 7 张卡片，每张对应一个模块，点击跳转到对应的 `moduleX-xxx.html`
- 每张卡片包含：模块编号、模块标题、一句话简介
- 页面配色与幻灯片主题一致（背景 #1a1a2e，强调色 #e94560，副标题色 #0f9b8e）
- 底部说明文字：「用浏览器打开 · 空格键 / 方向键翻页」

> index.html 是整个幻灯片系统的入口，用户只需打开这一个文件，就能跳转到任意模块或完整播放。

---

## 第七步：告知用户

```
✓ 幻灯片生成完成

入口页面：slides/html/index.html  ← 从这里开始
完整课程：slides/html/full-course.html
单模块（共 7 个）：slides/html/module*.html

打开 index.html，点卡片跳转模块，或直接播放完整课程。
演示时按方向键或空格键翻页。
```

---

## 异常处理

- **marp 命令失败**：输出完整错误信息，不要静默失败
- **某个课程文件格式特殊导致处理失败**：跳过该文件，继续处理其他文件，最后报告哪个文件跳过了
- **slides/ 目录不存在**：用 Bash 运行 `mkdir -p slides/src slides/html` 创建
