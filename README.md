# QQ AI 机器人

基于 Python + FastAPI 的 QQ 群聊机器人，集成原神资料查询、米游社账号绑定与签到、LLM 智能闲聊等功能。

## 已实现能力

### CP1-CP4：运行时骨架与 QQ 接入
- 统一应用启动入口，JSON 配置文件 + 环境变量配置加载
- 结构化日志、健康检查（`/healthz`）
- OneBot v11 Webhook 接入（NapCat 兼容）
- CLI 交互模式（`--cli` 参数）
- 统一事件模型、Router 分发、插件系统

### CP5-CP7：原神与米游社
- 角色武器材料等静态数据查询
- Enka.Network 公开面板查询（含 TTL 缓存）
- 米游社 Cookie 绑定/解绑、实时便笺、每日签到、战绩摘要

### CP8：LLM 闲聊
- 多模型路由（默认模型 / 升级模型）
- 对话上下文管理、Token 用量跟踪（日/总限额）
- 可配置 system prompt，支持角色人设

### CP9：角色养成资料
- 角色突破材料、天赋材料、BOSS 属性查询
- 命座信息、技能介绍、天赋、被动
- 本地静态 JSON 嵌入，零外部依赖

### CP10：响应门控（信号架构）
- **四种响应模式**：`all`（全回）、`auto`（评分门控）、`mention`（仅 @/回复）、`none`（静默）
- **硬信号**：@提及检测、回复检测 — 命中则绕过评分直接回复
- **软信号**：疑问句检测、兴趣关键词匹配、噪音过滤（短消息负分）
- **后处理器**：随机刷存在感（可配置概率）
- 私聊（PRIVATE）场景始终放行，不受门控影响
- 降级链：配置缺失时自动降级并告警

## 启动方式

```bash
source .venv/bin/activate

# 开发模式（HTTP + OneBot）
python -m app --config configs/dev.json

# CLI 交互模式（调试用）
python -m app --config configs/dev.json --cli
```

## 运行测试

```bash
source .venv/bin/activate
pytest
```

## 项目结构

```
app/                  # 应用包
├── bootstrap.py      # Application、build_application
├── config.py         # 配置加载（默认值 → JSON → 环境变量）
├── event_model.py    # NormalizedEvent、Scene、ReplyTarget
├── plugin.py         # BotPlugin ABC、PluginContext、PluginResult
├── router.py         # Router — 按序 match → handle 分发
├── plugins/          # 插件
│   ├── chat.py       #   ChatPlugin — LLM 闲聊（含信号门控）
│   ├── genshin/      #   原神查询插件
│   └── ...
├── adapters/         # 消息适配器
│   ├── __init__.py   #   CLIAdapter
│   └── onebot.py     #   OneBotAdapter（NapCat）
├── signals/          # 响应门控信号系统
│   ├── __init__.py   #   SignalVerdict、Signal ABC、SignalEvaluator
│   ├── hard.py       #   AtMention、ReplyToBot
│   ├── soft.py       #   QuestionDetect、KeywordMatch、NoiseFilter
│   └── post.py       #   RandomPass
├── llm/              # LLM Provider
├── providers/        # 外部数据 Provider
└── storage/          # 存储抽象
configs/              # 配置文件
tests/                # 测试（~270 个）
docs/                 # 架构文档
```
