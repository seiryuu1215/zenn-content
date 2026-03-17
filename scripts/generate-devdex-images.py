#!/usr/bin/env python3
"""DevDex書籍用の画像を生成するスクリプト"""

from PIL import Image, ImageDraw, ImageFont
import os

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
os.makedirs(IMAGES_DIR, exist_ok=True)

# フォント設定
FONT_BOLD = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'
FONT_REGULAR = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'

# カラーパレット（ダークテーマ）
BG = '#0f172a'
CARD_BG = '#1e293b'
CARD_BORDER = '#334155'
ACCENT = '#38bdf8'     # sky-400
ACCENT2 = '#a78bfa'    # violet-400
ACCENT3 = '#34d399'    # emerald-400
ACCENT4 = '#fb923c'    # orange-400
ACCENT5 = '#f472b6'    # pink-400
ACCENT6 = '#facc15'    # yellow-400
TEXT_PRIMARY = '#f1f5f9'
TEXT_SECONDARY = '#94a3b8'
TEXT_MUTED = '#64748b'


def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = radius
    # 角丸四角形
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def generate_subagent_flow():
    """サブエージェント6体制の構成図を生成"""
    W, H = 1200, 720
    img = Image.new('RGB', (W, H), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONT_BOLD, 28)
    font_agent = ImageFont.truetype(FONT_BOLD, 20)
    font_role = ImageFont.truetype(FONT_REGULAR, 14)
    font_label = ImageFont.truetype(FONT_BOLD, 13)
    font_human = ImageFont.truetype(FONT_BOLD, 16)

    # タイトル
    draw.text((W // 2, 35), 'サブエージェント 6体制', font=font_title,
              fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')
    draw.text((W // 2, 65), 'Claude Code × 役割分離による AI駆動開発',
              font=font_role, fill=hex_to_rgb(TEXT_SECONDARY), anchor='mm')

    # エージェント定義
    agents = [
        ('PM', 'PM Agent', '要件整理\n意思決定記録', ACCENT),
        ('IMP', 'Implement', 'コード実装\nAPI統一パターン', ACCENT2),
        ('TST', 'Test Agent', 'テスト自動生成\n2,100+件', ACCENT3),
        ('REV', 'Review', '品質・セキュリティ\nCriticalバグ発見', ACCENT4),
        ('DRY', 'Diary Agent', 'ログ→日記\n→Zenn記事', ACCENT5),
        ('BIZ', 'Business', '収益設計\nFeature Gate', ACCENT6),
    ]

    # 上段: PM → Implement → Test → Review（メインフロー）
    # 下段: Diary, Business（サポート）
    card_w, card_h = 155, 130
    top_y = 140
    bottom_y = 430

    # 上段4つの位置計算
    top_agents = agents[:4]
    top_gap = 50
    top_total = len(top_agents) * card_w + (len(top_agents) - 1) * top_gap
    top_start_x = (W - top_total) // 2

    top_positions = []
    for i, (abbr, name, role, color) in enumerate(top_agents):
        x = top_start_x + i * (card_w + top_gap)
        top_positions.append((x, top_y))

        # カード描画
        draw_rounded_rect(draw, (x, top_y, x + card_w, top_y + card_h),
                          radius=12, fill=hex_to_rgb(CARD_BG),
                          outline=hex_to_rgb(color), width=2)

        # アイコン的な丸
        cx = x + card_w // 2
        circle_y = top_y + 28
        draw.ellipse((cx - 16, circle_y - 16, cx + 16, circle_y + 16),
                     fill=hex_to_rgb(color))
        draw.text((cx, circle_y), abbr[:2], font=font_label,
                  fill=hex_to_rgb(BG), anchor='mm')

        # 名前
        draw.text((cx, top_y + 58), name, font=font_agent,
                  fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')

        # 役割
        for j, line in enumerate(role.split('\n')):
            draw.text((cx, top_y + 82 + j * 18), line, font=font_role,
                      fill=hex_to_rgb(TEXT_SECONDARY), anchor='mm')

    # 上段の矢印（→）
    arrow_color = hex_to_rgb(TEXT_MUTED)
    for i in range(len(top_positions) - 1):
        x1 = top_positions[i][0] + card_w + 5
        x2 = top_positions[i + 1][0] - 5
        y = top_y + card_h // 2
        draw.line((x1, y, x2 - 8, y), fill=arrow_color, width=2)
        # 矢じり
        draw.polygon([(x2 - 8, y - 6), (x2, y), (x2 - 8, y + 6)],
                     fill=arrow_color)

    # フローラベル
    flow_label_y = top_y + card_h + 18
    draw.text((W // 2, flow_label_y), '── メイン開発フロー ──',
              font=font_label, fill=hex_to_rgb(TEXT_MUTED), anchor='mm')

    # 下段2つ
    bottom_agents = agents[4:]
    bottom_gap = 120
    bottom_total = len(bottom_agents) * card_w + (len(bottom_agents) - 1) * bottom_gap
    bottom_start_x = (W - bottom_total) // 2

    bottom_positions = []
    for i, (abbr, name, role, color) in enumerate(bottom_agents):
        x = bottom_start_x + i * (card_w + bottom_gap)
        bottom_positions.append((x, bottom_y))

        draw_rounded_rect(draw, (x, bottom_y, x + card_w, bottom_y + card_h),
                          radius=12, fill=hex_to_rgb(CARD_BG),
                          outline=hex_to_rgb(color), width=2)

        cx = x + card_w // 2
        circle_y = bottom_y + 28
        draw.ellipse((cx - 16, circle_y - 16, cx + 16, circle_y + 16),
                     fill=hex_to_rgb(color))
        draw.text((cx, circle_y), abbr[:2], font=font_label,
                  fill=hex_to_rgb(BG), anchor='mm')

        draw.text((cx, bottom_y + 58), name, font=font_agent,
                  fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')

        for j, line in enumerate(role.split('\n')):
            draw.text((cx, bottom_y + 82 + j * 18), line, font=font_role,
                      fill=hex_to_rgb(TEXT_SECONDARY), anchor='mm')

    # サポートフローラベル
    support_label_y = bottom_y - 18
    draw.text((W // 2, support_label_y), '── サポートエージェント ──',
              font=font_label, fill=hex_to_rgb(TEXT_MUTED), anchor='mm')

    # 下段から上段への点線（Diary → 全体、Business → PM）
    dash_color = hex_to_rgb(TEXT_MUTED)

    # Diary → メインフローへの点線
    diary_cx = bottom_positions[0][0] + card_w // 2
    for yy in range(top_y + card_h + 35, bottom_y - 25, 8):
        draw.line((diary_cx, yy, diary_cx, yy + 4), fill=dash_color, width=1)

    # Business → メインフローへの点線
    biz_cx = bottom_positions[1][0] + card_w // 2
    for yy in range(top_y + card_h + 35, bottom_y - 25, 8):
        draw.line((biz_cx, yy, biz_cx, yy + 4), fill=dash_color, width=1)

    # 人間の役割（下部）
    human_y = bottom_y + card_h + 50
    draw.line((100, human_y - 15, W - 100, human_y - 15),
              fill=hex_to_rgb(CARD_BORDER), width=1)

    human_roles = ['方向性を決める', '判断を承認する', '最終確認する']
    draw.text((W // 2, human_y + 8), '👤 人間の役割:',
              font=font_human, fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')
    roles_text = '　　'.join(human_roles)
    draw.text((W // 2, human_y + 35), roles_text,
              font=font_role, fill=hex_to_rgb(TEXT_SECONDARY), anchor='mm')

    output_path = os.path.join(IMAGES_DIR, 'devdex-subagent-flow.png')
    img.save(output_path, 'PNG')
    print(f'Generated: {output_path}')


def generate_scale_infographic():
    """DevDex規模感インフォグラフィックを生成"""
    W, H = 1200, 500
    img = Image.new('RGB', (W, H), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONT_BOLD, 26)
    font_number = ImageFont.truetype(FONT_BOLD, 44)
    font_label = ImageFont.truetype(FONT_REGULAR, 15)
    font_sub = ImageFont.truetype(FONT_REGULAR, 12)

    # タイトル
    draw.text((W // 2, 40), '5日間・76時間で作った DevDex の全貌',
              font=font_title, fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')

    # メトリクスカード
    metrics = [
        ('86,000', '行のコード', ACCENT, ''),
        ('63', 'APIエンドポイント', ACCENT2, '相場: 10〜20本'),
        ('33', 'ページ', ACCENT3, '相場: 5〜15画面'),
        ('2,100+', 'ユニットテスト', ACCENT4, '相場: 0〜300件'),
        ('543+', 'マージ済みPR', ACCENT5, ''),
        ('256', '診断パターン', ACCENT6, '16タイプ×16 MBTI'),
    ]

    card_w, card_h = 165, 160
    cols = 6
    gap = 12
    total_w = cols * card_w + (cols - 1) * gap
    start_x = (W - total_w) // 2
    y = 90

    for i, (number, label, color, sub) in enumerate(metrics):
        x = start_x + i * (card_w + gap)

        draw_rounded_rect(draw, (x, y, x + card_w, y + card_h),
                          radius=12, fill=hex_to_rgb(CARD_BG),
                          outline=hex_to_rgb(CARD_BORDER), width=1)

        # 上部のカラーライン
        draw.line((x + 12, y + 8, x + card_w - 12, y + 8),
                  fill=hex_to_rgb(color), width=3)

        cx = x + card_w // 2

        # 数字
        draw.text((cx, y + 60), number, font=font_number,
                  fill=hex_to_rgb(color), anchor='mm')

        # ラベル
        draw.text((cx, y + 100), label, font=font_label,
                  fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')

        # サブテキスト
        if sub:
            draw.text((cx, y + 125), sub, font=font_sub,
                      fill=hex_to_rgb(TEXT_MUTED), anchor='mm')

    # 下部のタイムライン
    timeline_y = y + card_h + 50
    draw.text((W // 2, timeline_y), '── 開発タイムライン ──',
              font=ImageFont.truetype(FONT_BOLD, 14),
              fill=hex_to_rgb(TEXT_MUTED), anchor='mm')

    days = [
        ('Day 1', '15h', 'v0 MVP\n認証・用語管理', ACCENT),
        ('Day 2', '17h', 'v1 AI機能\n用語抽出・概要補完', ACCENT2),
        ('Day 3', '16h', 'v2 診断・スキル\n案件マッチング', ACCENT3),
        ('Day 4', '10h', 'v2.5 Pro機能\n🎯ダーツ大会中', ACCENT4),
        ('Day 5', '6h', 'v3 企業向け\n組織・権限', ACCENT5),
    ]

    day_w = 180
    day_gap = 20
    day_total = len(days) * day_w + (len(days) - 1) * day_gap
    day_start_x = (W - day_total) // 2
    day_y = timeline_y + 25

    font_day = ImageFont.truetype(FONT_BOLD, 15)
    font_hour = ImageFont.truetype(FONT_REGULAR, 13)
    font_desc = ImageFont.truetype(FONT_REGULAR, 12)

    # タイムラインの横線
    line_y = day_y + 15
    draw.line((day_start_x, line_y, day_start_x + day_total, line_y),
              fill=hex_to_rgb(CARD_BORDER), width=2)

    for i, (day, hours, desc, color) in enumerate(days):
        x = day_start_x + i * (day_w + day_gap)
        cx = x + day_w // 2

        # ドット
        draw.ellipse((cx - 6, line_y - 6, cx + 6, line_y + 6),
                     fill=hex_to_rgb(color))

        # Day + 時間
        draw.text((cx, day_y + 35), f'{day} ({hours})', font=font_day,
                  fill=hex_to_rgb(TEXT_PRIMARY), anchor='mm')

        # 説明
        for j, line in enumerate(desc.split('\n')):
            draw.text((cx, day_y + 55 + j * 16), line, font=font_desc,
                      fill=hex_to_rgb(TEXT_SECONDARY), anchor='mm')

    output_path = os.path.join(IMAGES_DIR, 'devdex-scale-overview.png')
    img.save(output_path, 'PNG')
    print(f'Generated: {output_path}')


if __name__ == '__main__':
    generate_subagent_flow()
    generate_scale_infographic()
    print('Done!')
