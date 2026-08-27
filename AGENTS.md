# AGENTS.md

## 项目概述

ARIA 是一个 Windows 桌面应用，捕获系统音频或麦克风输入，在可移动的 PyQt6 悬浮窗中实时渲染转录文本。目前有两条识别路径：Sherpa-ONNX 流式识别和 Windows 11 内建字幕。翻译是独立层，支持在线和本地。项目要求 Python 3.10+，仅支持 Windows。

## 开发环境

要求：

- Windows 10/11。
- Python >= 3.10。
- 使用 uv 管理虚拟环境和依赖。

运行应用：

```powershell
uv run aria
```

## 验证命令

始终使用 uv。提交前先跑最相关的检查，再跑完整套件：

```powershell
uv run ruff format
uv run ruff check --fix
uv run pytest
```

打包/导入测试：

```powershell
uv run python -c "import aria; print('import ok')"
```

如果测试需要 Windows 音频设备、GUI 交互、CUDA 或已安装的模型，请注明限制，不要伪造测试结果。


## 注释/文档纪律

- 注释/文档只写**做了什么、为什么**。不写"怎么摸索到的、历史上踩过什么坑、为什么没用另一方案"。对比可行 vs 不可行、踩坑史、淘汰方案是 git log / issue tracker 的事，不进注释
- 注释中绝不提及或引用任何外部文档，不能用诸如`详情见xxx.mdc`、`具体看xxx领域的文档`
- 一句话能写的规矩**不用扩成一段论证**。论证口头给用户讲，不写进文件；AI 读到对应代码/类型自会懂为什么，不用注释先讲一遍
- 不给已有代码补解释性注释

- 文档 只写"项目是什么"，不写用户的要求、展望，不写讨论过程，不写其他方案，不写其他文档的内容
- `description`骨架提示只写**是什么、何时读**。不写写法理论、不写"不是什么"。

## 架构规则

- 保持音频捕获、ASR、翻译、UI 的分离。

## UI 和 UX 规则

- 转录/渲染工作保持在 Qt UI 线程之外。
- 保持可移动/可调整大小的字幕和翻译悬浮窗，除非任务明确改变交互模式。
- 避免在 UI 线程中阻塞网络调用或模型下载。
- 保持源字幕和翻译字幕逻辑分离，以便可以独立禁用。
- 遵循 `i18n/` 下的本地化模式；存在翻译 key 时不要硬编码用户可见字符串。

## Windows 特定规则

- 将 WASAPI loopback 和 Windows 内建字幕集成视为平台特定代码；将平台假设与核心管道逻辑隔离。
- 修改 `audio/` 时同时测试系统音频和麦克风路径。
- 注意设备枚举、默认设备变更、采样率和停止/重启时的资源清理。
- 不要假设需要或已获得管理员权限。

## Working Rules(IMPORTANT!)
- Use Chinese to talk with user
- Never work with project when user did not ask for it
