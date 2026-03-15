# utils/render.py

from PIL import Image, ImageDraw, ImageFont


class ImageRenderer:

    def __init__(self, plugin_data_path, font_path):
        self.plugin_data_path = plugin_data_path
        self.font_path = font_path
        self.font_cache = {}

    # 字体加载
    def load_font(self, size):
        if size in self.font_cache:
            return self.font_cache[size]

        try:
            font = ImageFont.truetype(self.font_path, size)
        except OSError as e:
            raise FileNotFoundError(f"字体加载失败: {self.font_path}") from e

        self.font_cache[size] = font
        return font

    # UI组件
    def _draw_header(
        self, draw, width, header_height, title, font):
        draw.rectangle([0, 0, width, header_height], fill="#1677FF"
    )

        box = draw.textbbox((0, 0), title, font=font)
        w = box[2] - box[0]
        h = box[3] - box[1]

        draw.text(
            ((width - w) / 2, (header_height - h) / 2),
            title,
            fill="white",
            font=font
        )

    # 卡片绘制
    def _draw_card(
        self, draw, width, top_y, padding, card_height,
        number_text, label_text,
        font_number, font_label
    ):

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
        box = draw.textbbox((0, 0), number_text, font=font_number)
        num_w = box[2] - box[0]
        num_h = box[3] - box[1]

        draw.text(
            ((width - num_w) / 2, top_y + 20),
            number_text,
            fill="#222222",
            font=font_number
        )

        # label
        box = draw.textbbox((0, 0), label_text, font=font_label)
        label_w = box[2] - box[0]

        draw.text(
            ((width - label_w) / 2, top_y + 25 + num_h + 23),
            label_text,
            fill="#666666",
            font=font_label
        )

    def _get_rank_style(self, rank):
        if rank == 1:
            return "#D4AF37", "#FFF9E6"
        if rank == 2:
            return "#C0C0C0", "#F5F5F5"
        if rank == 3:
            return "#CD7F32", "#FFF4EC"
        return "#1677FF", "#F9FAFB"

    def _truncate_text(self, draw, text, max_width, font):
        if not text:
            return ""

        while text:
            box = draw.textbbox((0, 0), text, font=font)
            width = box[2] - box[0]

            if width <= max_width:
                return text

            text = text[:-1]

        return ""

    # 排名图片渲染
    def _draw_rank_card(
        self, draw, width, padding, top_y, card_height,
        rank, name, user_id, count,
        fonts, max_count
    ):

        font_rank, font_name, font_count, font_qq = fonts

        left_x = padding
        right_x = width - padding
        bottom_y = top_y + card_height

        rank_color, bg_color = self._get_rank_style(rank)

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
        draw.text(
            (left_x + 30, top_y + 30),
            f"#{rank}",
            fill=rank_color,
            font=font_rank
        )

        # 用户名
        name = self._truncate_text(draw, name, 400, font_name)

        draw.text(
            (left_x + 150, top_y + 20),
            name,
            fill="#222222",
            font=font_name
        )

        # QQ
        draw.text(
            (left_x + 150, top_y + 55),
            f"QQ：{user_id}",
            fill="#888888",
            font=font_qq
        )

        # 消息数量
        count_text = f"{count} 条"

        box = draw.textbbox((0, 0), count_text, font=font_count)
        count_w = box[2] - box[0]

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

        ratio = count / max_count if max_count else 0
        bar_width = int((bar_right - bar_left) * ratio)

        draw.rounded_rectangle(
            [bar_left, bar_top, bar_right, bar_top + bar_height],
            radius=5,
            fill="#EEEEEE"
        )

        draw.rounded_rectangle(
            [bar_left, bar_top, bar_left + bar_width, bar_top + bar_height],
            radius=5,
            fill=rank_color
        )

    # 渲染：群统计
    def render_group_message_image(
        self, group_id, group_name,
        total_count, user_count, date
    ):

        width = 900
        height = 650
        padding = 40
        card_height = 130
        spacing = 40
        header_height = 90

        image = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(image)

        font_title = self.load_font(40)
        font_label = self.load_font(26)
        font_big = self.load_font(42)
        font_mid = self.load_font(32)

        self._draw_header(
            draw,
            width,
            header_height,
            f"{date} 群消息统计",
            font_title
        )

        y = header_height + 50

        self._draw_card(
            draw, width, y, padding, card_height,
            group_name, "群名称",
            font_big, font_label
        )

        y += card_height + spacing

        self._draw_card(
            draw, width, y, padding, card_height,
            str(user_count), "今日发言人数",
            font_mid, font_label
        )

        y += card_height + spacing

        self._draw_card(
            draw, width, y, padding, card_height,
            str(total_count), "今日消息条数",
            font_mid, font_label
        )

        group_id = "".join(c for c in group_id if c.isdigit())

        image_path = self.plugin_data_path / f"group_message_count_{date}_{group_id}.png"
        image.save(image_path)

        return str(image_path)

    # 渲染：排行榜
    def render_group_rank_image(self, group_name, group_id, rank_list, date):

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
        font_rank = self.load_font(42)
        font_name = self.load_font(28)
        font_count = self.load_font(30)
        font_qq = self.load_font(18)

        self._draw_header(
            draw,
            width,
            header_height,
            f"{date} 群水笔排行",
            font_title
        )

        start_y = header_height + 50

        max_count = rank_list[0]["message_count"] if rank_list else 1

        fonts = (font_rank, font_name, font_count, font_qq)

        for i in range(max_items):

            item = rank_list[i]

            self._draw_rank_card(
                draw,
                width,
                padding,
                start_y + i * (card_height + spacing),
                card_height,
                i + 1,
                item["user_name"],
                item["user_id"],
                item["message_count"],
                fonts,
                max_count
            )

        group_id = "".join(c for c in group_id if c.isdigit())

        image_path = self.plugin_data_path / f"group_rank_{date}_{group_id}.png"
        image.save(image_path)

        return str(image_path)