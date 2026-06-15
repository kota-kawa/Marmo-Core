/**
 * demo3.js — 模型选择 / 切换 + 思考深度测试
 *
 * 运行：
 *   node src/demo3.js
 *
 * 测试内容：
 *   1. 检查当前模型（Pro / Flash / Flash-Lite）
 *   2. 检查当前思考深度（standard / extended）
 *   3. 切换到 Pro 模型
 *   4. 切换到扩展思考等级
 *   5. 验证最终状态
 */
import { createGeminiSession, disconnect } from './index.js';

async function main() {
  console.log('=== Gemini Skill Demo 3 — 模型 + 思考深度切换测试 ===\n');

  const { ops } = await createGeminiSession();

  process.on('SIGINT', () => {
    console.log('\n[demo3] Ctrl+C，断开连接...');
    disconnect();
    process.exit(0);
  });

  try {
    // ── 1. 当前模型 ──
    console.log('[1] 获取当前模型...');
    const model0 = await ops.getCurrentModel();
    if (model0.ok) {
      console.log(`    ✅ 当前模型: 「${model0.raw}」（标准化: ${model0.model}）`);
    } else {
      console.warn(`    ⚠ 无法获取: ${model0.error}`);
    }

    // ── 2. 当前思考深度 ──
    console.log('\n[2] 获取当前思考深度...');
    const depth0 = await ops.getThinkingDepth();
    console.log(`    ✅ 当前思考深度: ${depth0.level}${depth0.raw ? `（副标签: "${depth0.raw}"）` : ''}`);

    // ── 3. 切换到 Pro 模型 ──
    console.log('\n[3] 切换到 Pro 模型...');
    const switchModel = await ops.switchToModel('pro');
    if (switchModel.ok) {
      if (switchModel.alreadyTarget) {
        console.log('    ✅ 已经是 Pro，无需切换');
      } else {
        console.log(`    ✅ 切换成功（之前: ${switchModel.previousModel || '未知'}）`);
      }
    } else {
      console.error(`    ❌ 切换失败: ${switchModel.error}`);
    }

    // ── 4. 切换到扩展思考 ──
    console.log('\n[4] 切换到扩展思考等级...');
    const switchDepth = await ops.setThinkingDepth('extended');
    if (switchDepth.ok) {
      if (switchDepth.alreadyTarget) {
        console.log('    ✅ 已经是 extended，无需切换');
      } else {
        console.log(`    ✅ 切换成功（之前: ${switchDepth.previousLevel || '未知'}）`);
      }
    } else {
      console.error(`    ❌ 切换失败: ${switchDepth.error}`);
    }

    // ── 5. 最终状态 ──
    console.log('\n[5] 最终状态确认...');
    const [finalModel, finalDepth] = await Promise.all([
      ops.getCurrentModel(),
      ops.getThinkingDepth(),
    ]);
    console.log(`    📌 模型: ${finalModel.raw}（${finalModel.model}）`);
    console.log(`    📌 思考深度: ${finalDepth.level}`);

    const success = finalModel.model === 'pro' && finalDepth.level === 'extended';
    console.log(`\n${success ? '✅ 测试通过！' : '⚠ 最终状态未达目标'}`);

  } catch (err) {
    console.error('Error:', err);
  }

  console.log('\n[done] 模型切换测试完毕。按 Ctrl+C 退出。');
}

main().catch(console.error);
