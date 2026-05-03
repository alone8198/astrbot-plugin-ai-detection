# astrbot-plugin-ai-detection

<div align="center">
  <p>
    <a href="https://github.com/Soulter/AstrBot">
      <img src="https://img.shields.io/badge/AstrBot-插件-blue?style=flat-square" alt="AstrBot 插件">
    </a>
    <a href="https://github.com/alone8198/astrbot-plugin-ai-detection/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License">
    </a>
    <a href="https://github.com/alone8198/astrbot-plugin-ai-detection/releases">
      <img src="https://img.shields.io/github/v/release/alone8198/astrbot-plugin-ai-detection?style=flat-square" alt="Release">
    </a>
  </p>
</div>

---

## 📌 简介

一款面向 [AstrBot](https://github.com/Soulter/AstrBot) 的 AI 内容安全检测插件。

在用户消息进入 LLM 之前、以及 AI 回复发送给用户之前，对内容进行**双层检测**（关键词 + AI 智能检测），违规内容自动拦截，并支持黑名单与消息撤回。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 双层检测 | 关键词预过滤（快速） + AI 模型检测（精确），两级把关 |
| 🚫 用户输入拦截 | 检测到违规内容后直接拦截，不再交给 LLM 处理 |
| 🔄 AI 输出替换 | 检测到 AI 回复违规，自动替换为简洁提示语 |
| 📋 黑名单机制 | 多次违规自动拉黑，禁止该用户继续使用 AI 功能 |
| ↩️ 消息撤回 | 支持 QQ OneBot 协议（Napcat / Lagrange），可撤回违规消息 |
| ⚙️ 可视化配置 | 所有选项均可在 AstrBot WebUI 中直接配置，无需改代码 |
| 🛠️ 管理指令 | 内置黑名单管理、违规统计等管理指令 |

---

## 📦 安装方法

### 方式一：插件市场（推荐）

1. 打开 AstrBot WebUI
2. 进入 **插件市场**
3. 搜索 `ai-detection` 或 `AI检测`
4. 点击 **安装**

### 方式二：Git 克隆

```bash
# 进入 AstrBot 插件目录
cd /path/to/astrbot/data/plugins

# 克隆本插件
git clone https://github.com/alone8198/astrbot-plugin-ai-detection.git

# 在 WebUI 中重载插件即可生效
```

### 方式三：手动下载

1. 前往 [Releases](https://github.com/alone8198/astrbot-plugin-ai-detection/releases) 下载最新版压缩包
2. 解压到 `data/plugins/astrbot-plugin-ai-detection/`
3. 在 WebUI 中重载插件

---

## ⚙️ 配置说明

安装后在 **AstrBot WebUI → 插件管理 → AI检测插件** 中配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `detection_provider` | 模型选择器 | 未设置 | 选择用于检测的 AI 模型（从 AstrBot 已启用模型中选取） |
| `detect_user_input` | 开关 | `true` | 是否检测用户输入 |
| `detect_ai_output` | 开关 | `true` | 是否检测 AI 输出 |
| `max_violations` | 整数 | `3` | 违规次数达到此值后自动加入黑名单 |
| `enable_recall` | 开关 | `false` | 是否启用消息撤回（需机器人有管理权限） |
| `keyword_filter` | 文本 | 空 | 违规关键词列表，逗号分隔，命中直接拦截（无需 AI 调用） |
| `block_message` | 文本 | `⚠️ 您的消息包含违规内容...` | 用户输入被拦截时的提示，支持 `{count}` 和 `{max}` 变量 |
| `replace_message` | 文本 | `⚠️ 该回复因包含不良内容已被拦截替换` | AI 输出被替换时的提示文字 |
| `blacklist_message` | 文本 | `⛔ 您已被加入黑名单...` | 黑名单用户尝试使用 AI 时收到的提示 |
| `detection_prompt` | 文本 | 默认检测提示词 | 自定义 AI 检测提示词，必须包含 `{content}` 变量 |

---

## 💬 指令列表

| 指令 | 说明 | 示例 |
|------|------|------|
| `/检测黑名单` | 查看所有黑名单用户 | `/检测黑名单` |
| `/移出黑名单 <用户ID>` | 将用户移出黑名单并重置违规计数 | `/移出黑名单 123456789` |
| `/清空违规` | 清空所有违规记录和黑名单 | `/清空违规` |
| `/检测统计` | 查看违规统计概况 | `/检测统计` |

---

## 🔧 工作原理

```
用户发送消息
    │
    ▼
┌────────────────────────────────────┐
│  on_llm_request 钩子              │
│                                    │
│  ① 黑名单检查                      │
│     └─ 在黑名单中 → 直接拦截      │
│  ② 关键词预过滤                    │
│     └─ 命中 → 违规处理            │
│  ③ AI 模型检测                     │
│     └─ 违规 → 违规处理            │
│                                    │
│  违规处理流程:                      │
│  ├─ 发送拦截提示语                │
│  ├─ 记录违规次数                  │
│  ├─ 达阈值 → 加入黑名单           │
│  └─ 撤回消息（若开启）             │
└────────────────────────────────────┘
  正常 ↓
    ▼
┌────────────────────────────────────┐
│  LLM 处理请求                     │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│  on_llm_response 钩子             │
│                                    │
│  ① 关键词预过滤                    │
│  ② AI 模型检测                     │
│     └─ 违规 → 替换输出内容         │
└────────────────────────────────────┘
    ↓
  发送给用户
```

---

## 📂 数据存储

违规记录和黑名单以 JSON 文件形式存储在 AstrBot 数据目录：

```
data/plugin_data/ai_detection_plugin/ai_detection/
├── blacklist.json    # 黑名单用户列表
└── violations.json   # 各用户违规计数
```

可通过 `/清空违规` 指令一键清空所有数据。

---

## 🐛 问题排查

**Q：检测模型怎么选择？**
> 先在 AstrBot WebUI 的「提供商配置」中添加并启用至少一个 LLM 提供商，然后在插件配置中通过下拉列表选择即可。

**Q：消息撤回不生效？**
> 请确保：① `enable_recall` 已开启；② 机器人是群管理员（QQ 群场景）；③ 使用的是 `aiocqhttp` 平台适配器。

**Q：如何快速拦截特定关键词？**
> 在 `keyword_filter` 配置项中填写关键词，用逗号分隔，例如：`赌博,色情,暴力`。命中后直接拦截，无需调用 AI，响应极快。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'feat: add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

<div align="center">
  <p>⭐ 如果这个插件对你有帮助，欢迎给个 Star！</p>
  <p>
    <a href="https://github.com/Soulter/AstrBot">AstrBot 项目主页</a> ·
    <a href="https://github.com/alone8198/astrbot-plugin-ai-detection/issues">提交 Issue</a>
  </p>
</div>
