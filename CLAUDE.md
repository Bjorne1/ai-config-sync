# CLAUDE.md

This repository is now a Python + PySide6 Windows desktop application.

## 项目概述

AI Config Sync 用于把统一源目录中的 `Skills` / `Commands` 分发到 Claude、Codex、Gemini、Antigravity 等工具目录，并可选同步到 WSL2。

## 常用命令

```bash
# 安装依赖
python -m pip install -r requirements.txt

# 启动桌面 GUI
python -m python_app

# Windows 启动脚本
start.bat

# 验证
python -m compileall python_app
python -m unittest discover -s tests -p "test_*.py"
```

## 架构说明

### 核心模块

- `python_app\bootstrap.py` - Qt 应用装配与启动入口
- `python_app\controller.py` - GUI 与服务层之间的动作编排
- `python_app\core\config_service.py` - `config.json` 读写、归一化与迁移
- `python_app\core\environment_service.py` - Windows / WSL 环境解析
- `python_app\core\resource_service.py` - 资源扫描与展开
- `python_app\core\resource_operations.py` - 状态汇总、同步、清理
- `python_app\core\sync_engine.py` - `copy` / `symlink` 执行逻辑
- `python_app\gui\main_window.py` - 主窗口与页面容器

### 数据流

1. GUI 发出动作信号
2. `controller.py` 调用 `AppService`
3. `python_app\core\**` 处理配置、扫描、同步、清理、更新
4. Controller 回填 snapshot / logs / 结果到主窗口

## Windows 特殊要求

- 只支持 Windows
- 创建软链接需要管理员权限或启用开发者模式
