# Paper-Specific Interactive Elements

论文转课程专用交互元素，基于 paper-to-course 的设计系统实现。

---

## 1. Formula Breakdown（公式拆解）

**用途**：将论文中的数学公式逐行翻译成通俗解释，类似代码 ↔ 英文翻译块。

```html
<div class="formula-block animate-in">
  <div class="formula-original">
    <span class="formula-label">ORIGINAL FORMULA</span>
    <div class="formula-math">
      <!-- LaTeX 渲染或纯文本公式 -->
      L(θ) = E_{s,a~π_θ}[r(s,a)]
    </div>
  </div>
  <div class="formula-explanation">
    <span class="formula-label">WHAT IT MEANS</span>
    <div class="formula-line">
      <span class="formula-symbol">L(θ)</span>
      <span class="formula-english">This is the loss function — a score that tells us "how wrong" our current model is.</span>
    </div>
    <div class="formula-line">
      <span class="formula-symbol">E_{s,a~π_θ}</span>
      <span class="formula-english">"E" means "expected value" (average). We're averaging over all situations (s) and actions (a) the agent might take, following its current policy π_θ.</span>
    </div>
    <div class="formula-line">
      <span class="formula-symbol">r(s,a)</span>
      <span class="formula-english">The reward the agent gets for taking action a in situation s. This is the "feedback signal" from the environment.</span>
    </div>
  </div>
</div>
```

**CSS classes used**：`formula-block`, `formula-original`, `formula-math`, `formula-explanation`, `formula-line`, `formula-symbol`, `formula-english`, `formula-label`

---

## 2. Literature Timeline（文献时间线）

**用途**：展示一个领域的发展历程，关键节点用动画标注方法演进。

```html
<div class="timeline-container animate-in">
  <div class="timeline-line"></div>

  <div class="timeline-item" data-year="2016">
    <div class="timeline-dot"></div>
    <div class="timeline-card">
      <span class="timeline-year">2016</span>
      <h4>DeepMind DQN</h4>
      <p class="timeline-desc">Deep Q-Network 证明了深度强化学习在 Atari 游戏上的可行性。</p>
      <div class="timeline-method-tag">DQN</div>
    </div>
  </div>

  <div class="timeline-item" data-year="2017">
    <div class="timeline-dot"></div>
    <div class="timeline-card">
      <span class="timeline-year">2017</span>
      <h4>Transformer Architecture</h4>
      <p class="timeline-desc">Attention Is All You Need — 完全基于注意力机制的序列建模。</p>
      <div class="timeline-method-tag">Attention</div>
    </div>
  </div>

  <div class="timeline-item" data-year="2020">
    <div class="timeline-dot"></div>
    <div class="timeline-card">
      <span class="timeline-year">2020</span>
      <h4>AlphaFold 2</h4>
      <p class="timeline-desc">基于 Transformer 和注意力机制解决蛋白质折叠问题。</p>
      <div class="timeline-method-tag">Attention + Structure</div>
    </div>
  </div>

</div>
```

**CSS classes used**：`timeline-container`, `timeline-line`, `timeline-item`, `timeline-dot`, `timeline-card`, `timeline-year`, `timeline-method-tag`

---

## 3. Comparison Table（对比表格）

**用途**：可交互的多方法对比表，悬停显示详细分析。

```html
<div class="comparison-table-container animate-in">
  <table class="comparison-table">
    <thead>
      <tr>
        <th>Method</th>
        <th>Communication</th>
        <th>Scalability</th>
        <th>Sample Efficiency</th>
        <th>Centralized Training</th>
      </tr>
    </thead>
    <tbody>
      <tr class="method-row" data-method="QMIX">
        <td><span class="method-name">QMIX</span></td>
        <td><span class="cell-check">✓</span> Full</td>
        <td><span class="cell-bar" style="--pct: 70%">70%</span></td>
        <td><span class="cell-bar" style="--pct: 85%">85%</span></td>
        <td><span class="cell-check">✓</span></td>
      </tr>
      <tr class="method-row" data-method="COMA">
        <td><span class="method-name">COMA</span></td>
        <td><span class="cell-check">✓</span> Full</td>
        <td><span class="cell-bar" style="--pct: 60%">60%</span></td>
        <td><span class="cell-bar" style="--pct: 65%">65%</span></td>
        <td><span class="cell-check">✓</span></td>
      </tr>
      <tr class="method-row highlight-row" data-method="Ours">
        <td><span class="method-name highlight">MGAT-AC (Ours)</span></td>
        <td><span class="cell-partial">⊘ Partial</span></td>
        <td><span class="cell-bar" style="--pct: 95%">95%</span></td>
        <td><span class="cell-bar" style="--pct: 92%">92%</span></td>
        <td><span class="cell-check">✓</span></td>
      </tr>
    </tbody>
  </table>

  <!-- 悬停详情弹窗（由 main.js 自动绑定） -->
  <div class="comparison-tooltip" id="tip-QMIX" hidden>
    <strong>QMAX vs QMIX:</strong> QMIX 使用单调性约束保证可分解性，
    但牺牲了表达多样性。适用于通信受限的完全合作场景。
  </div>
</div>
```

**CSS classes used**：`comparison-table-container`, `comparison-table`, `method-row`, `method-name`, `cell-bar`, `cell-check`, `cell-partial`, `highlight-row`, `comparison-tooltip`

---

## 4. Ablation Diagram（消融实验图）

**用途**：可视化消融实验结果，展示每个组件的贡献。

```html
<div class="ablation-container animate-in">
  <h3>Ablation Study — 哪些组件真正重要？</h3>
  <p class="ablation-intro">每次去掉一个组件，看性能下降多少。下降越多，该组件越关键。</p>

  <div class="ablation-chart">
    <!-- 基准线：完整模型 -->
    <div class="ablation-bar-group">
      <span class="ablation-label">Full Model</span>
      <div class="ablation-bar-track">
        <div class="ablation-bar fill-full" style="width: 100%">
          <span class="ablation-value">95.2%</span>
        </div>
      </div>
    </div>

    <!-- 去掉 GAT -->
    <div class="ablation-bar-group">
      <span class="ablation-label">w/o GAT</span>
      <div class="ablation-bar-track">
        <div class="ablation-bar fill-remove" style="width: 72%">
          <span class="ablation-value">68.5%</span>
        </div>
        <div class="ablation-drop-marker" style="left: 72%">
          <span class="ablation-drop-label">-26.7%</span>
        </div>
      </div>
    </div>

    <!-- 去掉 PPO -->
    <div class="ablation-bar-group">
      <span class="ablation-label">w/o PPO</span>
      <div class="ablation-bar-track">
        <div class="ablation-bar fill-remove" style="width: 81%">
          <span class="ablation-value">77.1%</span>
        </div>
        <div class="ablation-drop-marker" style="left: 81%">
          <span class="ablation-drop-label">-18.1%</span>
        </div>
      </div>
    </div>

    <!-- 去掉 PER -->
    <div class="ablation-bar-group">
      <span class="ablation-label">w/o PER</span>
      <div class="ablation-bar-track">
        <div class="ablation-bar fill-remove" style="width: 89%">
          <span class="ablation-value">84.7%</span>
        </div>
        <div class="ablation-drop-marker" style="left: 89%">
          <span class="ablation-drop-label">-10.5%</span>
        </div>
      </div>
    </div>
  </div>

  <div class="ablation-insight">
    <span class="insight-icon">💡</span>
    <strong>关键发现：</strong>GAT（注意力机制）对性能贡献最大（-26.7%），其次是 PPO（-18.1%）。PER 的影响相对较小（-10.5%）。
  </div>
</div>
```

**CSS classes used**：`ablation-container`, `ablation-bar-group`, `ablation-label`, `ablation-bar-track`, `ablation-bar`, `fill-full`, `fill-remove`, `ablation-drop-marker`, `ablation-drop-label`, `ablation-insight`

---

## 5. Method Chat（方法对话动画）

**用途**：用群聊动画模拟不同方法/组件之间的"对话"，解释它们如何协作。

```html
<div class="group-chat animate-in" data-chat-id="method-flow">
  <div class="chat-header">
    <span class="chat-title">💬 How MGAT-AC Components Interact</span>
  </div>

  <div class="chat-messages">
    <div class="chat-msg" data-sender="Sensor" data-delay="0">
      <div class="chat-avatar sensor">📡</div>
      <div class="chat-bubble">
        <span class="chat-sender">Sensor Module</span>
        <p class="chat-text">I see 3 nearby drones. Their positions and velocities are: [p1, v1], [p2, v2], [p3, v3].</p>
      </div>
    </div>

    <div class="chat-msg" data-sender="GAT" data-delay="800">
      <div class="chat-avatar gat">🧠</div>
      <div class="chat-bubble">
        <span class="chat-sender">Graph Attention Network</span>
        <p class="chat-text">Got it. I'm computing attention weights. Drone #2 is most critical — highest collision risk with me.</p>
      </div>
    </div>

    <div class="chat-msg" data-sender="Actor" data-delay="1600">
      <div class="chat-avatar actor">🎭</div>
      <div class="chat-bubble">
        <span class="chat-sender">Actor Network</span>
        <p class="chat-text">Based on the GAT output and my current state, I'll choose action: adjust heading by +15°.</p>
      </div>
    </div>

    <div class="chat-msg" data-sender="Critic" data-delay="2400">
      <div class="chat-avatar critic">📊</div>
      <div class="chat-bubble">
        <span class="chat-sender">Critic Network</span>
        <p class="chat-text">Good choice! Estimated Q-value is 0.87. The expected future reward looks promising.</p>
      </div>
    </div>
  </div>

  <div class="typing-indicator" hidden>
    <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
  </div>
</div>
```

**CSS classes used**：`group-chat`, `chat-messages`, `chat-msg`, `chat-avatar`, `chat-bubble`, `chat-sender`, `chat-text`

---

## 6. Quiz: Paper Comprehension（论文理解测验）

**用途**：选择题测试读者对论文核心内容的理解程度。

```html
<div class="quiz-container animate-in" data-quiz-id="q1">
  <div class="quiz-header">
    <span class="quiz-icon">📝</span>
    <h4>Comprehension Check</h4>
  </div>

  <div class="quiz-question">
    <p><strong>Q:</strong> What is the primary advantage of using GAT over a simple MLP in MGAT-AC?</p>
  </div>

  <div class="quiz-options">
    <div class="quiz-option" data-correct="true">
      <span class="option-letter">A</span>
      <span class="option-text">GAT dynamically weights the importance of each neighbor, enabling the agent to focus on the most dangerous drones.</span>
      <span class="quiz-feedback correct">✓ Correct! This is exactly why GAT is used — it learns which neighbors matter most.</span>
    </div>

    <div class="quiz-option" data-correct="false">
      <span class="option-letter">B</span>
      <span class="option-text">GAT runs faster than MLP on the same hardware.</span>
      <span class="quiz-feedback incorrect">✗ Not quite. GAT is actually more computationally expensive than a simple MLP.</span>
    </div>

    <div class="quiz-option" data-correct="false">
      <span class="option-letter">C</span>
      <span class="option-text">GAT eliminates the need for a critic network.</span>
      <span class="quiz-feedback incorrect">✗ Incorrect. The actor-critic architecture is preserved; GAT only modifies the state representation.</span>
    </div>
  </div>
</div>
```

**CSS classes used**：`quiz-container`, `quiz-header`, `quiz-icon`, `quiz-question`, `quiz-options`, `quiz-option`, `option-letter`, `option-text`, `quiz-feedback`, `correct`, `incorrect`

---

## 设计原则

1. **通俗优先**：公式解释用"购物小票"类比，不用"数学定义"
2. **聚焦"为什么"**：不仅解释公式是什么，更要解释为什么这个设计有效
3. **一致性**：所有颜色、间距、动画时间与 `styles.css` 保持一致
4. **无内联样式**：所有样式通过 class 引用，禁止内联 style 属性
5. **可访问性**：Glossary Tooltips 覆盖所有专业术语（首次出现标记）
