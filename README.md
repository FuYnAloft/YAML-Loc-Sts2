# YAML-Loc-Sts2

`YAML-Loc-Sts2` 是一个专为 StS2 模组开发者设计的本地化文件转换工具。它将开发者从繁琐的 JSON 格式的本地化书写中解放出来，允许使用更具可读性的 YAML 编写文本，并自动处理游戏框架所需的复杂命名前缀与格式要求（例如`BASELIBPREFIX-I_HATE_THOSE_SNAKE_UPPER_CASE`）。

## 核心特性
- **告别“雷霆类名”**：不再需要写类似`MYEXAMPLEMOD-THOSE_SNAKE_UPPER_CASE`的ID，脚本会自动转换。
- **零成本迁移**: 自带从 JSON 到 YAML 的转换功能，可以轻松将原有的本地化迁移至 YAML。
- **嵌套结构**: 不再需要重复书写ID，直接使用嵌套结构组织内容。
- **YAML是对的**: YAML 支持注释和多行文本，本地化文件会更清晰易读。

使用此工具后，你的本地化文件将变得简洁清晰：

```yaml
# 可以随便写注释！
ExampleStrike:             # 不用写 WEIRD_UPPER_SANKE_CASE 了，脚本可以自动转换！
  title: 打击               # 不用写多遍ID了，直接采用嵌套结构！
  description: 造成42点伤害
ExampleDefense:            # 不用写 BaseLib 添的前缀了，脚本可以自动添加！
  title: 防御
  description: 获得37点格挡
ExampleMultiLine:
  title: 一个描述很长的牌
  description: |-          # 多行文本可以轻松书写！
    随机发动1种效果:
    - 直接获得本场战斗胜利
    - 直接获得本场战斗失败
    - 一键为群友安装杀戮尖塔2
    - 一键卸载杀戮尖塔2
```

## 安装与使用

### 1. 放置脚本
首先，从 [Releases](https://github.com/FuYnAloft/YAML-Loc-Sts2/releases) 下载最新的`convert.py`脚本。
（注意：若使用的 python 版本低于 `3.12`，请下载`convert_compat.py`）

本脚本使用相对脚本的路径，为了确保路径正确，请务必按照以下结构放置文件：

```txt
<ModName>/
├── <ModName>/
│   ├── localization/           # 本地化 JSON 文件（游戏读取）
│   │   └── zhs/
│   │       ├── cards.json
│   │       └── (...)
│   └── .gitignore              # （可选）忽略 JSON 本地化
├── Tools/
│   ├── localization/           # 本地化 YAML 源文件（易于编辑）
│   │   ├── zhs/
│   │   │   ├── cards.yaml
│   │   │   └── (...)
│   │   └── convert.py          # 转换脚本
│   └── .gdignore               # 使 Godot 忽略此目录
├── <ModName>.csproj            # C# 项目文件
└── MainFile.cs
```
（也可以参考仓库中的`ExampleMod`示例项目）

### 2. 修改配置
打开`convert.py`，编辑其中的`配置区`（大约在第200行），具体说明详见代码注释。

### 3. 运行
#### 方法 A：使用`uv`（推荐）
如果你在使用 [uv](https://github.com/astral-sh/uv)，无需手动安装依赖，直接在项目根目录执行：
```bash
uv run Tools/localization/convert.py
```
#### 方法 B：使用标准 `python`
1. **安装依赖**：
   ```bash
   pip install pyyaml
   ```
2. **执行脚本**：
   ```bash
   python Tools/localization/convert.py
   ```