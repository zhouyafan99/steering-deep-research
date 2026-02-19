
README
```md
# Steering Deep Research（可转舵的深度研究）

> 深度研究不是黑盒长跑：允许你在运行中随时“转舵”——注入新指令、改计划、继续跑，不用重启。

## 背景/问题
传统 deep research 常见问题：
- 一跑几十分钟，最后才发现方向偏了
- 早期对模糊需求的误解会被放大，后续无法纠正
- 想改需求只能停止任务重跑，浪费 token 和时间

## 我的解决方案
把 deep research 变成可交互过程：
- 先澄清（Clarifier）
- 输出轻量 CoT：只展示 **Plan + 阅读的网站 Sources**（不给用户看全部 agent logs）
- 研究过程中随时输入干预指令（steer）
- Supervisor 接收指令 → 转成约束 → 交给 Planner 更新 plan → 继续研究

## 你能获得什么
- ✅ 运行中干预研究方向（核心差异点）
- ✅ 轻量可视化：Plan + Sources（可点击链接）
- ✅ 最终报告（带引用）

## Quickstart
```bash
cd web/backend
pip install -r requirements.txt
python main.py

cd web/frontend
npm install
npm run dev  # 或 npm start
打开 http://localhost:3000

