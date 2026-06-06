# 🎤 Sans Voice Assistant

一个基于本地LLM的智能语音助手，支持语音交互、多步推理、工具调用和多模态理解。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Whisper-STT-green?logo=openai" />
  <img src="https://img.shields.io/badge/Edge--TTS-Speech-purple?logo=microsoft" />
  <img src="https://img.shields.io/badge/Ollama-Local-red?logo=ollama" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" />
</p>

## ✨ 特性

- 🎤 **语音交互** - Whisper语音识别 + Piper/Edge TTS语音合成
- 🤖 **混合模型** - 本地Ollama(qwen3:4b) + 云端MIMO，自动切换
- 🧠 **Agent能力** - 6个专门Agent + 多步推理 + 自主循环
- 🔧 **工具系统** - 15个内置工具，支持文件操作、系统控制、网络搜索等
- 💾 **记忆系统** - ChromaDB向量数据库，语义检索用户记忆
- 🎯 **唤醒词** - "Hi Sans" 文本匹配 + 音频模型双重检测
- 🎨 **科幻UI** - tkinter粒子悬浮球可视化

## 📦 安装

```bash
# 1. 克隆项目
git clone https://github.com/cerqwq/sans-voice-assistant.git
cd sans-voice-assistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的API密钥

# 4. 安装Ollama（可选，本地模型）
ollama pull qwen3:4b
```

## 🚀 使用

```bash
# 语音模式
python main.py

# 文本模式
python main.py --text

# 使用Piper TTS（本地离线）
set USE_PIPER_TTS=true
python main.py
```

说 **"Hi Sans"** 唤醒，然后说出你的指令。

## 📁 项目结构

```
voice-assistant/
├── main.py                 # 主入口
├── config.py               # 配置管理
├── requirements.txt        # 依赖清单
├── core/                   # 核心模块
│   ├── assistant.py        # 混合模型架构
│   ├── agent.py            # Agent多步推理
│   ├── orchestrator.py     # 多Agent编排器
│   ├── memory_manager.py   # 记忆管理器
│   ├── tts.py              # TTS引擎
│   ├── wakeword.py         # 唤醒词检测
│   ├── overlay.py          # 科幻UI
│   └── tool_registry.py    # 工具注册中心
├── core/agents/            # 专门Agent
│   ├── coding_agent.py     # 编程Agent
│   ├── research_agent.py   # 研究Agent
│   ├── monitor_agent.py    # 监控Agent
│   ├── automation_agent.py # 自动化Agent
│   ├── file_agent.py       # 文件Agent
│   └── learning_agent.py   # 学习Agent
└── tools/                  # 工具集（15个）
```

## 🛠️ 工具列表

| 工具 | 功能 |
|------|------|
| `get_datetime_location` | 获取时间、日期、位置 |
| `launch_app` | 启动应用或打开URL |
| `get_weather` | 查询天气 |
| `system_volume` | 音量控制 |
| `screen_brightness` | 亮度控制 |
| `system_control` | 锁屏/关机/重启 |
| `web_search` | 网页搜索 |
| `search_files` | 文件搜索 |
| `clipboard` | 剪贴板操作 |
| `take_screenshot` | 截图 |
| `media_control` | 媒体控制 |
| `read_file` | 读取文件 |
| `write_file` | 写入文件 |
| `execute_command` | 执行命令 |
| `execute_python` | 执行Python代码 |

## 🧠 Agent系统

| Agent | 功能 |
|-------|------|
| CodingAgent | 代码生成、调试、重构 |
| ResearchAgent | 信息搜索、知识检索 |
| MonitorAgent | 系统监控、性能分析 |
| AutomationAgent | 定时任务、自动执行 |
| FileAgent | 文件管理、批量操作 |
| LearningAgent | 学习建议、知识整理 |

## 🔧 配置说明

```bash
# .env 文件
MIMO_API_KEY=your_api_key        # 云端API密钥
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
OLLAMA_MODEL=qwen3:4b            # 本地模型
WHISPER_MODEL=small              # 语音识别模型
TTS_VOICE=zh-CN-XiaoxiaoNeural   # TTS语音
```

## 📝 开发

### 添加新工具

1. 在 `tools/` 目录创建新文件
2. 定义工具函数和工具定义
3. 在 `core/tool_registry.py` 中注册

### 添加新Agent

1. 在 `core/agents/` 目录创建新文件
2. 继承 `BaseAgent` 类
3. 实现 `can_handle()` 和 `run()` 方法

## 📄 许可证

MIT License

## 🙏 致谢

- [Ollama](https://ollama.ai) - 本地LLM运行
- [Whisper](https://github.com/openai/whisper) - 语音识别
- [Piper](https://github.com/rhasspy/piper) - 语音合成
- [ChromaDB](https://www.trychroma.com) - 向量数据库
- [Edge TTS](https://github.com/rany2/edge-tts) - 微软TTS
