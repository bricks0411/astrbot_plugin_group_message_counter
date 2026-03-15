# astrbot_plugin_group_message_counter

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL_3.0-blue.svg" alt="License: AGPL-3.0">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/AstrBot-v4.5.7+-orange.svg" alt="AstrBot v4.5.7+">
</p>

<p align="center">
  <img src="https://count.getloli.com/@MessageCounter?name=MessageCounter&theme=asoul&padding=10&offset=0&align=top&scale=1&pixelated=1&darkmode=auto" alt="Moe Counter">
</p>

到底谁才是群里的 **大水笔** 呢？

## 项目简介

> 哎我操，怎么 $10$ 分钟不看群，群里又 $99+$ 了，你们的嘴巴比加特林还快啊真的是

<img src="C:\Users\联想\AppData\Roaming\Typora\typora-user-images\image-20260303001032682.png" alt="image-20260303001032682" style="zoom: 80%;" />

如果你想知道，这个群里面到底谁才是那个大水笔，那这个插件就很适合你的需求。

这个插件可以偷偷：

- 监听并记录群成员每日发言并计算次数
- 计算今天的群里面又被群友灌了多少水
- 视奸那个说 “不行真的得睡了” 的群友，又偷偷说了几句话
- 把前 $10$ 个最能水群的水笔挂到群里

数据通过 **SQLite** 实现可持久化数据存储，**支持异步写入**，**保证并发安全**，让每一句话都能被准确记录！

目前仅在 **QQ 个人号** 上进行过测试，不保证其余平台的兼容性与稳定性。

## 功能说明

### 1. 异步监听

异步监听群消息事件，自动记录并更新相关数据。

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
├── utils/
│  	└── render.py
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

已建立索引以优化查询，正如我之前所说的，监听群友的消息，不仅要准，还要快！

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

## TODO

- 自动删除过于久远的持久化数据
- 查看指定群友消息数

- $7$ 日群聊活跃度展示
- 排行榜自动化推送
- Astrbot WebUI 配置项

## 贡献

- 提交 Issue 报告问题
- Pull Request 改进代码
- 提出任何合理的建议