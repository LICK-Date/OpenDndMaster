# DungeonMaster

`DungeonMaster` 是一个基于 LangGraph 思路搭建的本地单人跑团 DM Agent 原型。当前仓库已经不再适合使用上游 `LangGraph` 的主页式 README 来描述，实际可运行的核心应用位于 `apps/dm_agent`，支持命令行单回合、交互式会话，以及本地 Web UI。

项目当前重点是：

- 用结构化世界数据驱动文本跑团
- 用轻量规则决定是否判定、判定阈值和后果
- 在可用时接入 OpenAI-compatible LLM 生成叙事
- 在 LLM 不可用时稳定退回本地模板叙事
- 持续把世界、玩家、NPC 和会话记录写回本地文件

## 当前状态

目前仓库已经具备以下能力：

- 可从仓库根目录直接运行 `apps/dm_agent/main.py`
- 可启动本地 Web UI：`apps/dm_agent/web_server.py`
- 支持加载已有世界，或在 Web UI 中创建新世界
- 自动维护 `world.json`、`player_profile.json`、`player.md`、`NPC_List.json`、`npcs/*.json`
- 记录 `session_log.txt` 和 `session_transcript.json`
- 支持通过环境变量或 Web UI 保存并切换 LLM 配置
- 图执行优先使用 LangGraph；若当前环境未安装对应模块，会自动回退到仓库内置的轻量 `runtime_graph`

这个仓库现在是“LangGraph 源码 + DungeonMaster 应用原型”并存的开发仓库，而不是单纯的上游框架镜像。

## 目录说明

```text
.
├── apps/
│   └── dm_agent/              # 当前主要应用入口
│       ├── main.py            # CLI 入口
│       ├── web_server.py      # 本地 Web UI 入口
│       ├── graph.py           # 图构建
│       ├── nodes.py           # 规则节点与叙事节点
│       ├── memory_store.py    # 世界数据读写
│       ├── settings_store.py  # LLM 配置持久化
│       └── web/               # 前端页面
├── workspace_data/
│   ├── settings/              # LLM 配置存储
│   └── worlds/                # 世界、角色、NPC、会话记录
├── libs/                      # LangGraph 相关源码库
└── README.md
```

## 快速开始

### 运行要求

- Python 3.10 及以上
- 在仓库根目录执行命令

当前 `dm_agent` 这条运行链尽量只依赖 Python 标准库；即使没有安装完整 LangGraph 运行环境，也可以通过仓库内置的轻量图执行器跑起来。

### 单回合 CLI

```bash
python apps/dm_agent/main.py --world demo --input "我尝试说服Mara给我一个安静的房间"
```

查看完整状态：

```bash
python apps/dm_agent/main.py --world demo --input "我偷偷调查楼上的脚印" --dump-state
```

### 交互式 CLI

```bash
python apps/dm_agent/main.py --world campaign_01 --interactive
```

可用命令：

- `/help` 查看帮助
- `/state` 查看当前世界和角色摘要
- `/dump` 输出最近一次完整状态
- `/exit` 结束会话

### Web UI

```bash
python apps/dm_agent/web_server.py --host 127.0.0.1 --port 8787
```

启动后打开 [http://127.0.0.1:8787](http://127.0.0.1:8787)。

Web UI 当前已接通的内容包括：

- 世界列表加载与切换
- 新建世界
- 对话输入与回合推进
- 当前世界、角色属性、NPC、近期事件展示
- 历史 transcript 回显
- LLM 配置的新增、编辑、激活、删除

## LLM 配置

项目使用 OpenAI-compatible Chat Completions 接口。

可通过两种方式配置：

### 方式 1：环境变量

必填项：

- `DM_LLM_BASE_URL` 或 `OPENAI_BASE_URL`
- `DM_LLM_MODEL` 或 `OPENAI_MODEL`

可选项：

- `DM_LLM_API_KEY` 或 `OPENAI_API_KEY`
- `DM_LLM_TIMEOUT`，默认 `30`
- `DM_LLM_TEMPERATURE`，默认 `0.7`
- `DM_LLM_JSON_MODE`，默认 `on`

PowerShell 示例：

```powershell
$env:DM_LLM_BASE_URL = "https://api.openai.com/v1"
$env:DM_LLM_MODEL = "gpt-4.1-mini"
$env:DM_LLM_API_KEY = "<your-key>"
$env:DM_LLM_JSON_MODE = "on"
python apps/dm_agent/web_server.py --host 127.0.0.1 --port 8787
```

### 方式 2：Web UI 内配置

打开右上角设置面板后，可以直接保存多个模型配置。配置会持久化到：

```text
workspace_data/settings/llm_profiles.json
```

当前激活的配置会在后续回合中直接生效。

### 未配置 LLM 时的行为

如果没有可用 LLM，或者 LLM 返回超时、网络错误、非预期 JSON，系统会自动退回本地模板叙事，保证回合仍然可继续。

## 世界数据结构

每个世界默认位于：

```text
workspace_data/worlds/<world_id>/
```

典型结构如下：

```text
workspace_data/worlds/<world_id>/
├── session_log.txt
├── session_transcript.json
└── world_Info/
    ├── world.json
    ├── player_profile.json
    ├── player.md
    ├── NPC_List.json
    └── npcs/
        └── *.json
```

如果目标世界不存在，系统会自动引导生成一个最小可运行世界。

## 当前规则流

`dm_agent` 当前的回合流程大致如下：

1. 读取世界、玩家、NPC 和记忆快照
2. 识别玩家动作类型
3. 判断本回合是否需要掷骰
4. 计算阈值并执行 `d20`
5. 应用 NPC 态度变化和隐藏声望变化
6. 写回世界数据与会话日志
7. 生成叙事输出

当前已经覆盖的几类动作包括：

- 社交类互动
- 威胁类互动
- 力量、敏捷、智力、天赋倾向动作
- 无需判定的纯叙事推进

## 已知限制

为了让 README 和现状保持一致，这里明确列出目前还没完成的部分：

- Web UI 里的“导入世界”“导出世界”按钮目前还没有接后端能力
- 世界删除按钮目前只是界面占位，还没有真实删除逻辑
- 当前是本地单用户原型，没有鉴权、多房间或多人同步
- NPC 反应和世界后果仍然是轻量规则模型，不是深度模拟
- LLM 输出依赖严格 JSON 结构，不符合时会直接 fallback
- `apps/dm_agent` 目前还没有独立整理成完整发布包

## 关于 `libs/`

仓库保留了 `libs/` 下的 LangGraph 相关源码，方便直接参考、联调或后续回接真实 LangGraph 能力。根目录 `Makefile` 主要服务于这些库的开发流程，不是 `dm_agent` 的一键启动脚本。

如果你修改的是 `libs/` 下的库，请遵循对应库目录的开发命令：

- `make format`
- `make lint`
- `make test`

## 推荐阅读

- 应用说明：[apps/dm_agent/README.md](apps/dm_agent/README.md)
- Web 入口：[apps/dm_agent/web_server.py](apps/dm_agent/web_server.py)
- CLI 入口：[apps/dm_agent/main.py](apps/dm_agent/main.py)
- 世界数据示例：`workspace_data/worlds/demo`

如果你接下来要继续推进这个项目，比较自然的下一步通常是三件事之一：补齐世界导入导出、给 `dm_agent` 增加自动化测试，或者把 NPC / faction 的状态演化做得更深一些。
