from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 إنشاء فيديو", callback_data="video"),
            InlineKeyboardButton("🎵 إنشاء أغنية", callback_data="song"),
        ],
        [
            InlineKeyboardButton("📚 السجل", callback_data="history"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel"),
        ],
    ])


def aspect_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 9:16 عمودي", callback_data="aspect:9:16"),
        ],
        [
            InlineKeyboardButton("⬜ 1:1 مربع", callback_data="aspect:1:1"),
            InlineKeyboardButton("🖥️ 16:9 أفقي", callback_data="aspect:16:9"),
        ],
    ])


def duration_menu(kind="video"):
    if kind == "video":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("5 ثواني", callback_data="duration:5"),
                InlineKeyboardButton("8 ثواني", callback_data="duration:8"),
            ]
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("30 ثانية", callback_data="duration:30"),
            InlineKeyboardButton("60 ثانية", callback_data="duration:60"),
        ],
        [
            InlineKeyboardButton("120 ثانية", callback_data="duration:120"),
        ],
    ])
