# main.py

import os
import sqlite3
import aiosqlite
import asyncio
from pathlib import Path
from datetime import datetime

from .utils.render import ImageRenderer

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger


@register("GroupMessageCounter", 
          "Bricks0411", 
          "一个简单的逼话计数器，用来统计群友今天在群里说了多少话", 
          "0.2.0"
)
class GroupMessageCounter(Star):

    # self.plugin_data_path = base_path / "plugin_data" / self.__class__.__name__

    # 初始化插件类
    def __init__(self, context: Context):
        # 确保目录存在
        super().__init__(context)
        # 获取并初始化插件持久化数据的存储路径
        base_path = StarTools.get_data_dir()
        self.plugin_data_path = base_path
        self.database_path = self.plugin_data_path / "message_counter.db"
        # 创建目录
        self.plugin_data_path.mkdir(parents = True, exist_ok = True)
        BASE_DIR = Path(__file__).resolve().parent
        self.font_path = str(BASE_DIR / "font" / "LXGWWenKai-Regular.ttf")
        # 判断字体文件是否存在
        if not Path(self.font_path).exists():
            raise FileNotFoundError(
                f"字体文件不存在：{self.font_path}"
            )
        # 实例化绘图类
        self.image_renderer = ImageRenderer(self.plugin_data_path, self.font_path)
        # 初始化数据库
        self.init_db()


    # 获取当前日期
    def today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # 初始化数据库
    def init_db(self):
        conn = sqlite3.connect(self.database_path)
        # SQL 语句对象
        cursor = conn.cursor()

        # 创建总表，用于存储群消息数　
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS group_message_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                user_name TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(group_id, user_id, date)
            );
            """
        )
        # 创建群聊 - 消息数表，用于存储不同群当天的消息总数
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS group_message_count (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                group_id TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date, group_id)
            );
            """
        )
        # 创建索引，提升查询效率，遵循最左匹配原则
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_group_date_count_count_rank
            ON group_message_stats (group_id, date, message_count DESC, user_id ASC);
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_group_date_count_count
            ON group_message_count (group_id, date)
            """
        )
        
        # 提交修改
        conn.commit()
        # 关闭连接，防止连接持续存在导致并发问题
        conn.close()
        
    # 更新用户群消息数
    async def update_user_counter(self, group_id: str, user_id: str, user_name: str):
        date = self.today()
        db = self.db

        async with self.db_lock:  # 加锁
            # 更新总表信息
            await db.execute(
                """
                INSERT INTO group_message_stats (group_id, user_id, date, user_name, message_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(group_id, user_id, date)
                DO UPDATE SET 
                    message_count = message_count + 1,
                    user_name = excluded.user_name;
                """, 
                (group_id, user_id, date, user_name)
            )
            # 更新群聊 - 消息数表信息
            await db.execute(
                """
                INSERT INTO group_message_count (date, group_id, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(date, group_id)
                DO UPDATE SET message_count = message_count + 1;
                """, 
                (date, group_id)
            )

            await db.commit()

    # 获取指定群消息，并返回对应位置的结果
    async def get_group_message_total_count(self, group_id: str):
        date = self.today()
        db = self.db
        # 查询指定群消息数量
        async with db.execute(
            """
            SELECT message_count AS total
            FROM group_message_count
            WHERE group_id = ? AND date = ?
            """, 
            (group_id, date)) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return 0

        return row["total"] or 0

    # 获取指定群中今天发言的用户数量
    async def get_group_user_total_count(self, group_id: str):
        date = self.today()
        db = self.db

        async with db.execute(
            """
            SELECT COUNT(*) AS total
            FROM group_message_stats
            WHERE group_id = ? AND date = ?
            """, 
            (group_id, date)
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return 0

        return row["total"] or 0

    # 获取指定群中消息数量排行榜（若发言用户多于 10 位，则返回前 10 位）
    async def get_group_user_message_rank(self, group_id: str):
        date = self.today()
        db = self.db
        # 查询当天用户 - 群消息数信息，并降序排序
        async with db.execute(
            """
            SELECT user_name, message_count, user_id
            FROM group_message_stats
            WHERE group_id = ? AND date = ?
            ORDER BY message_count DESC, user_id ASC
            LIMIT 10;
            """,
            (group_id, date)
        ) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def hello_world(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    # 查询群消息总数，自动统计当天的群消息总数
    @filter.command("查询群消息")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def get_group_message_count(self, event: AstrMessageEvent):
        """查询本群消息总数"""
        group_id = str(event.get_group_id())
        # 从数据库中查询对应群聊消息总数
        result_message_count = await self.get_group_message_total_count(group_id)
        result_person_count = await self.get_group_user_total_count(group_id)
        date = self.today()

        # CQHTTP API，实现群名称查询，后期计划同步到数据库中，减少重复查询开销
        group_info = await event.bot.get_group_info(
            group_id = int(group_id),
            no_cache = False
        )
        group_name = group_info["group_name"]

        # 将绘图任务置于单独线程中，防止阻塞其他任务导致 bot 响应变慢
        image_path = await asyncio.to_thread(
            self.image_renderer.render_group_message_image, 
            group_id, 
            group_name, 
            result_message_count, 
            result_person_count, 
            date
        )

        logger.debug(f"图片生成成功！路径是: {image_path}")

        yield event.image_result(image_path)
        # yield event.plain_result(f"本群今天有 {result_person_count} 个群友说过话，他们一共发送了 {result_message_count} 条消息！")

    # 查询排行榜，根据用户所在的群聊自动生成当天消息总数排行
    @filter.command("查询排行榜")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def get_group_message_rank(self, event: AstrMessageEvent):
        """查询本群消息排行"""
        date = self.today()
        group_id = str(event.get_group_id())
        rank_list = await self.get_group_user_message_rank(group_id)

        group_info = await event.bot.get_group_info(
            group_id = int(group_id),
            no_cache = False
        )
        group_name = group_info["group_name"]

        # 将绘图任务置于单独线程中，防止阻塞其他任务导致 bot 响应变慢
        image_path = await asyncio.to_thread(
            self.image_renderer.render_group_rank_image,
            group_name,
            group_id,
            rank_list,
            date
        )

        logger.debug(f"图片生成成功！路径是: {image_path}")

        yield event.image_result(image_path)

    # 监听群消息，将对应用户的消息归档到数据库中
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message_counter(self, event: AstrMessageEvent):
        """实时监听对应群聊消息，更新对应群消息的数据"""
        # 获取消息的基本信息
        user_id = str(event.get_sender_id())
        user_name = event.get_sender_name()
        group_id = str(event.get_group_id())

        await self.update_user_counter(group_id, user_id, user_name)
        logger.debug(f"接收到来自用户 {user_name}（编号：{user_id}）的消息！")

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""  
        self.db = await aiosqlite.connect(
            self.database_path,
            check_same_thread = False
        )
        self.db.row_factory = aiosqlite.Row
        # 定义写日志策略：预写日志，避免数据库写操作阻塞读操作
        await self.db.execute("PRAGMA journal_mode = WAL;")
        # 定义 fsync 同步策略：减少同步次数以提升性能，但数据稳定性将会降低，在本插件的业务场景下，这点损失倒是无伤大雅
        await self.db.execute("PRAGMA synchronous = NORMAL;")
        # 定义临时表存放策略：放入内存，查询速度更快
        await self.db.execute("PRAGMA temp_store = MEMORY;")
        self.db_lock = asyncio.Lock()
    
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.db.close()