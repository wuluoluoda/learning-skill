# 显式调用流程

显式调用是用户直接点名 `learning`，例如 `/learning`、`$learning` 或 skill chip。它只负责创建或切换当前项目的学习模式。

## 流程

1. 运行：

   ```bash
   python3 <skill-dir>/scripts/learning_state.py toggle --project <project>
   ```

2. 读取脚本 JSON 输出：
   - `enabled: 1` 表示已开启。
   - `enabled: 0` 表示已关闭。
   - `ok: false` 时，根据 `error` 处理；如果是 `managed_block_corrupt`，读取输出里的 `agents_file`，人工检查 learning 托管块，避免误删项目规则。

3. 验证脚本结果：
   - 读回 `<project>/.codex/learning/state.json`，确认 `enabled` 与脚本输出一致。
   - 读回项目 `AGENTS.md`：开启时应存在完整 `learning-managed` 托管块；关闭时应不存在该托管块。若关闭后 `AGENTS.md` 只剩该块，脚本应已删除文件。

4. 回复用户：
   - 开启：`已开启这个项目的 learning，后续会在自然阶段边界补充解释。`
   - 关闭：`已关闭这个项目的 learning，后续不再主动补充教学。`
   - 如果显式调用中包含清楚、可复用的教学偏好，先运行 `ensure`，再整理写入 `NOTES.md`，并在确认句后补一句“也已记录：...”
   - 每次切换后都追加一个红球重点问题：`🔴 请观察：learning 是否影响了正式任务质量或让输出漂移？如果有影响，请及时关闭，谨慎再用。`

显式调用完成短确认后结束本流程。学习模式影响后续对话。
