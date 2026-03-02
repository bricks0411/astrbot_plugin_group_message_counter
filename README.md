# astrbot_plugin_group_message_counter

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL_3.0-blue.svg" alt="License: AGPL-3.0">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/AstrBot-v4.5.7+-orange.svg" alt="AstrBot v4.5.7+">
</p>

<p align="center">
  <img src="https://count.getloli.com/@MessageCounter?name=MessageCounter&theme=asoul&padding=10&offset=0&align=top&scale=1&pixelated=1&darkmode=auto" alt="Moe Counter">
</p>

到底谁才是群里的 **大水王** 呢？

## 项目简介

本插件用于：

- 实时记录群成员每日发言次数
- 统计群每日总消息数
- 统计当日发言人数
- 生成当日发言排行榜图片（前 $10$ 名）

数据通过 SQLite 持久化存储，支持异步写入。

## 功能说明

### 1. 异步监听

异步监听群消息事件，自动记录：

- 群号
- 用户 ID
- 用户昵称
- 日期
- 发言次数

### 2. 查询群消息统计

指令：

```
/查询群消息
```

返回：

- 群名称
- 今日发言人数
- 今日消息总条数
- 统计图片

### 3. 查询群排行榜

指令：

```
/查询排行榜
```

返回：

- 今日发言前 $10$ 名
- 发言条数
- 可视化排行榜图片

## 图片说明

生成图片包含：

- 标题栏
- 数据卡片
- 排行名次
- 发言数量
- 进度条显示

前三名采用不同颜色样式区分。

## 项目结构

```
astrbot_plugin_group_message_counter/
│
├── data
|	├──t2i_templates
|	|	├── astrbot_powershell.html
|	|	└── base.html
|	└── cmd_config.json
├── font/
│   └── LXGWWenKai-Regular.ttf
├── main.py
├── metadata.yaml
└── README.md
```

## 安装方式

- 将插件目录放入：

```
AstrBot/data/plugins/
```

- 安装依赖：

```bash
pip install aiosqlite pillow aiohttp
```

- 确保字体文件存在：

```
font/LXGWWenKai-Regular.ttf
```

若字体缺失，图片中的中文可能会无法正常显示。

## 数据存储

数据库路径：

```
AstrBot/data/plugin_data/GroupMessageCounter/message_counter.db
```

包含两张表：

- `group_message_stats`：用户每日发言记录
- `group_message_count`：群每日消息总数

已建立索引以优化查询。

## 技术实现

- Python 3
- SQLite
- aiosqlite（异步数据库操作）
- Pillow（图片生成）
- SQLite WAL 模式
- asyncio.Lock 保证并发安全

## License

本项目基于 **GNU General Public License (GPL)** 进行许可。

你可以在遵守 GPL 协议的前提下：

- 使用
- 修改
- 分发本项目

建议在仓库根目录添加官方 GPL 文本作为 `LICENSE` 文件。

## 作者

Bricks0411

## 贡献

欢迎提交 Issue 或 Pull Request。