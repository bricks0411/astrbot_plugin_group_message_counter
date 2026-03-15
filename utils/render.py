# utils/render.py

from tkinter import font
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

class ImageRenderer:
    # 初始化类
    def __init__(self, plugin_data_path, font_path):
        self.plugin_data_path = plugin_data_path
        self.font_path = font_path
        # 设定字体缓存机制
        self.font_cache = {}

    # 字体加载
    def load_font(self, size):
        # 若缓存存在，则使用缓存中的字体，降低磁盘 IO
        if size in self.font_cache:
            return self.font_cache[size]

        try:
            font = ImageFont.truetype(self.font_path, size)
        except:
            font = ImageFont.load_default()

        self.font_cache[size] = font
        return font

    # 图片渲染：查询当天群消息总数
    def render_group_message_image(self, group_id: str, group_name: str, total_count: int, user_count: int, date: str):
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

        return str(image_path)

    # 图片渲染：查询当天群消息排名
    def render_group_rank_image(self, group_name: str, group_id: str, rank_list: list, date: str):
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

        return str(image_path)