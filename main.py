import json
import os
import sqlite3
import aiosqlite
import aiohttp
import asyncio
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

@register("GroupMessageCounter", 
          "Bricks0411", 
          "一个简单的逼话计数器，用来统计群友今天在群里说了多少话", 
          "0.0.1"
)
class GroupMessageCounter(Star):

    # self.plugin_data_path = base_path / "plugin_data" / self.__class__.__name__

    # 初始化插件类
    def __init__(self, context: Context):
        # 确保目录存在
        super().__init__(context)
        # 获取并初始化插件持久化数据的存储路径
        base_path = Path(get_astrbot_data_path())
        self.plugin_data_path = base_path / "plugin_data" / self.__class__.__name__
        self.database_path = self.plugin_data_path / "message_counter.db"
        # 创建目录
        self.plugin_data_path.mkdir(parents = True, exist_ok = True)
        BASE_DIR = Path(__file__).resolve().parent
        self.font_path = str(BASE_DIR / "font" / "LXGWWenKai-Regular.ttf")
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
            CREATE INDEX IF NOT EXISTS idx_group_date_count_stats
            ON group_message_stats (group_id, date)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_group_date_count_count
            ON group_message_count (group_id, date)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_group_date_count_count_rank
            ON group_message_stats (group_id, date, message_count DESC, user_id ASC);
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
                UPDATE group_message_stats
                SET user_name = ?
                WHERE group_id = ? AND user_id = ? AND date = ?;
                """,
                (user_name, group_id, user_id, date)
            )
            await db.execute(
                """
                INSERT INTO group_message_stats (group_id, user_id, date, user_name, message_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(group_id, user_id, date)
                DO UPDATE SET 
                    message_count = message_count + 1;
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
            # 查询用户当天在某群的消息数量
            async with db.execute(
                """
                SELECT message_count
                FROM group_message_stats
                WHERE group_id = ? AND user_id = ? AND date = ?
                """, 
                (group_id, user_id, date)
            ) as cursor:
                    row = await cursor.fetchone()

            await db.commit()

        return row["message_count"]

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

    # 图片渲染：查询当天群消息总数
    async def render_group_message_image(self, group_id: str, group_name: str, total_count: int, user_count: int, date: str):
        width = 900
        padding = 40
        height = 650
        card_height = 130
        spacing = 40

        image = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(image)

        # 字体
        font_title = self.load_font(40)
        font_label = self.load_font(26)
        font_number_big = self.load_font(42)
        font_number_mid = self.load_font(32)

        # 顶部蓝色标题栏
        header_height = 90
        draw.rectangle([0, 0, width, header_height], fill="#1677FF")

        title = f"{date} 群消息统计"
        title_box = draw.textbbox((0, 0), title, font=font_title)
        title_w = title_box[2] - title_box[0]
        title_h = title_box[3] - title_box[1]

        draw.text(
            ((width - title_w) / 2, (header_height - title_h) / 2),
            title,
            fill="white",
            font=font_title
        )

        # 卡片绘制
        def draw_card(top_y, number_text, label_text, big_number=True):
            left_x = padding
            right_x = width - padding
            bottom_y = top_y + card_height

            # 阴影
            draw.rounded_rectangle(
                [left_x + 6, top_y + 6, right_x + 6, bottom_y + 6],
                radius=25,
                fill="#EAEAEA"
            )

            # 主卡片
            draw.rounded_rectangle(
                [left_x, top_y, right_x, bottom_y],
                radius=25,
                fill="#F9FAFB"
            )

            # 数字
            number_font = font_number_big if big_number else font_number_mid
            num_box = draw.textbbox((0, 0), number_text, font=number_font)
            num_w = num_box[2] - num_box[0]
            num_h = num_box[3] - num_box[1]

            number_top_offset = 20

            draw.text(
                ((width - num_w) / 2, top_y + number_top_offset),
                number_text,
                fill="#222222",
                font=number_font
            )

            # 标签
            label_box = draw.textbbox((0, 0), label_text, font=font_label)
            label_w = label_box[2] - label_box[0]
            label_h = label_box[3] - label_box[1]

            label_spacing = 23

            draw.text(
                ((width - label_w) / 2, top_y + 25 + num_h + label_spacing),
                label_text,
                fill="#666666",
                font=font_label
            )

        # ========================
        # 三个卡片
        # ========================
        first_card_y = header_height + 50

        draw_card(first_card_y, group_name, "群名称", big_number=True)

        draw_card(
            first_card_y + card_height + spacing,
            str(user_count),
            "今日发言人数"
        )

        draw_card(
            first_card_y + (card_height + spacing) * 2,
            str(total_count),
            "今日消息条数"
        )

        group_id = "".join(c for c in group_id if c.isalnum())
        image_path = self.plugin_data_path / f"group_message_count_{date}_{group_id}.png"
        image.save(image_path)

        logger.info(f"图片生成成功！路径是: {image_path}")

        return str(image_path)

    # 图片渲染：查询当天群消息排名
    async def render_group_rank_image(self, group_name: str, group_id: str, rank_list: list, date: str):
        max_items = min(10, len(rank_list))

        width = 900
        padding = 40
        header_height = 90
        card_height = 110
        spacing = 25

        height = (
            header_height
            + 60
            + max_items * (card_height + spacing)
            + 40
        )

        image = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(image)

        font_title = self.load_font(38)
        font_rank_big = self.load_font(42)
        font_name = self.load_font(28)
        font_count = self.load_font(30)
        font_qq = self.load_font(18)

        # 顶栏
        draw.rectangle([0, 0, width, header_height], fill="#1677FF")

        title = f"{date} 群水笔排行"
        title_box = draw.textbbox((0, 0), title, font=font_title)
        title_w = title_box[2] - title_box[0]
        title_h = title_box[3] - title_box[1]

        draw.text(
            ((width - title_w) / 2, (header_height - title_h) / 2),
            title,
            fill="white",
            font=font_title
        )
        # 颜色判断函数
        def get_rank_style(rank):
            if rank == 1:
                return "#D4AF37", "#FFF9E6"   # 金色 + 浅金背景
            elif rank == 2:
                return "#C0C0C0", "#F5F5F5"   # 银色 + 浅灰背景
            elif rank == 3:
                return "#CD7F32", "#FFF4EC"   # 铜色 + 浅铜背景
            else:
                return "#1677FF", "#F9FAFB"   # 默认蓝

        # 卡片绘制函数
        def draw_rank_card(top_y, rank, name, user_id, count):
            
            def truncate_text(text, max_width, font):
                if not text:
                    return ""
                while text:
                    box = draw.textbbox((0, 0), text, font=font)
                    width = box[2] - box[0]
                    if width <= max_width:
                        return text
                    text = text[:-1]
                return ""
            
            left_x = padding
            right_x = width - padding
            bottom_y = top_y + card_height

            rank_color, bg_color = get_rank_style(rank)

            # 阴影
            draw.rounded_rectangle(
                [left_x + 5, top_y + 5, right_x + 5, bottom_y + 5],
                radius=20,
                fill="#EAEAEA"
            )

            # 主卡片
            draw.rounded_rectangle(
                [left_x, top_y, right_x, bottom_y],
                radius=20,
                fill=bg_color
            )

            # 排名
            rank_text = f"#{rank}"
            draw.text(
                (left_x + 30, top_y + 30),
                rank_text,
                fill=rank_color,
                font=font_rank_big
            )

            # 用户名
            max_name_width = 400
            name = truncate_text(name, max_name_width, font_name)
            draw.text(
                (left_x + 150, top_y + 20),
                name,
                fill="#222222",
                font=font_name
            )

            # QQ号（小号灰色）
            qq_text = f"QQ：{user_id}"
            draw.text(
                (left_x + 150, top_y + 55),
                qq_text,
                fill="#888888",
                font=font_qq
            )

            # 条数（右对齐）
            count_text = f"{count} 条"
            count_box = draw.textbbox((0, 0), count_text, font=font_count)
            count_w = count_box[2] - count_box[0]

            draw.text(
                (right_x - count_w - 30, top_y + 37),
                count_text,
                fill="#444444",
                font=font_count
            )

            # 进度条
            bar_left = left_x + 150
            bar_right = right_x - 30
            bar_top = top_y + 80
            bar_height = 10

            max_count = rank_list[0]["message_count"] if rank_list else 1
            ratio = count / max_count if max_count else 0

            bar_width = int((bar_right - bar_left) * ratio)

            # 背景条
            draw.rounded_rectangle(
                [bar_left, bar_top, bar_right, bar_top + bar_height],
                radius=5,
                fill="#EEEEEE"
            )

            # 实际条
            draw.rounded_rectangle(
                [bar_left, bar_top, bar_left + bar_width, bar_top + bar_height],
                radius=5,
                fill=rank_color
            )

        # 渲染排行榜
        start_y = header_height + 50

        for i in range(max_items):
            item = rank_list[i]
            draw_rank_card(
                start_y + i * (card_height + spacing),
                i + 1,
                item["user_name"],
                item["user_id"],
                item["message_count"]
            )

        group_id = "".join(c for c in group_id if c.isalnum())
        image_path = self.plugin_data_path / f"group_rank_{date}_{group_id}.png"
        image.save(image_path)

        logger.info(f"图片生成成功！路径是 {image_path}")

        return str(image_path)

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
        group_id = event.get_group_id()
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

        image_path = await self.render_group_message_image(group_id, group_name, result_message_count, result_person_count, date)

        yield event.image_result(image_path)
        # yield event.plain_result(f"本群今天有 {result_person_count} 个群友说过话，他们一共发送了 {result_message_count} 条消息！")

    # 查询排行榜，根据用户所在的群聊自动生成当天消息总数排行
    @filter.command("查询排行榜")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def get_group_message_rank(self, event: AstrMessageEvent):
        """查询本群消息排行"""
        date = self.today()
        group_id = event.get_group_id()
        rank_list = await self.get_group_user_message_rank(group_id)

        group_info = await event.bot.get_group_info(
            group_id = int(group_id),
            no_cache = False
        )
        group_name = group_info["group_name"]

        image_path = await self.render_group_rank_image(group_name, group_id, rank_list, date)

        yield event.image_result(image_path)

    # 监听群消息，将对应用户的消息归档到数据库中
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message_counter(self, event: AstrMessageEvent):
        """实时监听对应群聊消息，更新对应群消息的数据"""
        # 获取消息的基本信息
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        group_id = event.get_group_id()
        date = self.today()

        message_count = await self.update_user_counter(group_id, user_id, user_name)
        logger.info(f"消息数更新完毕！用户 {user_id} 在 {date} 这一天往群 {group_id} 发了 {message_count} 条消息。")
     
    # 统一加载字体
    def load_font(self, size):
        try:
            if hasattr(self, "font_path") and self.font_path:
                if Path(self.font_path).exists():
                    return ImageFont.truetype(str(self.font_path), size)
        except Exception as e:
            logger.info(f"字体加载失败: {e}")

        return ImageFont.load_default()

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""  
        self.db = await aiosqlite.connect(self.database_path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL;")
        self.db_lock = asyncio.Lock()
    
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.db.close()