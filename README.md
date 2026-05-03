# AstrBot AI 检测插件

[![AstrBot](https://img.shields.io/badge/AstrBot-%E6%8F%92%E4%BB%B6-blue)](https://github.com/Soulter/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> 检测用户输入和 AI 输出中的违规内容，支持关键词过滤、AI 智能检测、黑名单机制和消息撤回。

---

## 功能特性

- ✅ **双层检测** — 关键词预过滤（快速） + AI 模型检测（精确）
- ✅ **用户输入拦截** — 检测到违规内容后拦截，不再交给 AI 处理
- ✅ **AI 输出替换** — 检测到违规回复，自动替换为简洁原因
- ✅ **黑名单机制** — 多次违规自动拉黑，禁止使用 AI 功能
- ✅ **消息撤回** — 支持 QQ OneBot 协议（Napcat / Lagrange），可撤回违规消息
- ✅ **管理指令** — 查看黑名单、移出黑名单、查看统计等
- ✅ **可视化配置** — 在 AstrBot WebUI 中直接配置所有选项

## 安装方法

### 方式一：通过插件市场（推荐）

在 AstrBot WebUI → 插件市场 中搜索 `ai-detection` 并安装。

### 方式二：手动安装

```bash
# 进入 AstrBot 的 data/plugins 目录
cd data/plugins

# 克隆仓库
git clone https://github.com/alone8198/astrbot-plugin-ai-detection.git

# 在 WebUI 中重载插件
```

### 方式三：下载压缩包

1. 下载 [最新 Release](https://github.com/alone8198/astrbot-plugin-ai-detection/releases) 的源码包
2. 解压到 `data/plugins/astrbot-plugin-ai-detection/`
3. 在 WebUI 中重载插件

## 配置说明

插件安装后，在 AstrBot WebUI → 插件管理 → AI检测插件 中进行配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `detection_provider` | 模型选择 | 未设置 | 选择用于检测的 AI 模型（下拉选择 AstrBot 已启用的模型） |
| `detect_user_input` | 开关 | `true` | 是否检测用户输入 |
| `detect_ai_output` | 开关 | `true` | 是否检测 AI 输出 |
| `max_violations` | 整数 | `3` | 几次违规后加入黑名单 |
| `enable_recall` | 开关 | `false` | 是否启用消息撤回（需机器人有管理员权限） |
| `keyword_filter` | 文本 | 空 | 关键词列表，逗号分隔，命中直接拦截 |
| `block_message` | 文本 | `⚠️ 您的消息包含违规内容...` | 用户输入被拦截时的提示文字 |
| `replace_message` | 文本 | `⚠️ 该回复因包含不良内容已被拦截替换` | AI 输出被替换时的提示文字 |
| `blacklist_message` | 文本 | `⛔ 您已被加入黑名单...` | 黑名单用户收到提示文字 |
| `detection_prompt` | 文本 | 默认检测提示词 | 自定义 AI 检测使用的提示词 |

## 指令列表

| 指令 | 说明 | 示例 |
|------|------|------|
| `/检测黑名单` | 查看所有黑名单用户 | `/检测黑名单` |
| `/移出黑名单 <用户ID>` | 将用户移出黑名单 | `/移出黑名单 123456789` |
| `/清空违规` | 清空所有违规记录和黑名单 | `/清空违规` |
| `/检测统计` | 查看违规统计概况 | `/检测统计` |

## 工作原理

```
用户发送消息
    │
    ▼
┌──────────────────────────────┐
│  on_llm_request 钩子         │
│                              │
│  1. 黑名单检查               │
│      └─ 在黑名单中 → 直接拦截 │
│  2. 关键词预过滤              │
│      └─ 命中 → 违规处理       │
│  3. AI 模型检测               │
│      └─ 违规 → 违规处理       │
│                              │
│  违规处理:                    │
│  ├─ 发送拦截提示             │
│  ├─ 记录违规次数              │
│  ├─ 达阈值 → 加入黑名单       │
│  └─ 撤回消息（可选）          │
└──────────────────────────────┘
  正常 ↓
    ▼
┌──────────────────────────────┐
│  LLM 处理请求                │
└──────────────────────────────┘
    ↓
┌──────────────────────────────┐
│  on_llm_response 钩子        │
│                              │
│  1. 关键词预过滤              │
│  2. AI 模型检测               │
│      └─ 违规 → 替换输出内容    │
└──────────────────────────────┘
    ↓
  发送给用户
```

## 数据存储

违规记录和黑名单数据存储在 AstrBot 数据目录：

```
data/plugin_data/ai_detection_plugin/ai_detection/
├── blacklist.json    # 黑名单列表
└── violations.json   # 违规计数
```

可通过 `/清空违规` 指令一键清空。

## 开发说明

```bash
# 克隆项目
git clone https://github.com/alone8198/astrbot-plugin-ai-detection.git
cd astrbot-plugin-ai-detection

# 将项目复制到 AstrBot 插件目录
cp -r . /path/to/astrbot/data/plugins/astrbot-plugin-ai-detection
```

### 文件结构

```
astrbot-plugin-ai-detection/
├── main.py               # 插件主代码
├── metadata.yaml         # 插件元数据
├── _conf_schema.json     # 配置 Schema
└── README.md             # 本文件
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT](LICENSE)
