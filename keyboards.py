from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="🎮 Игры"),
            KeyboardButton(text="🎁 Бонус"),
        ],
        [
            KeyboardButton(text="❓ Помощь"),
            KeyboardButton(text="💼 Работа"),
            KeyboardButton(text="🌱 Развитие"),
        ],
        [
            KeyboardButton(text="🎰 Розыгрыши"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [
            KeyboardButton(text="🛒 Рынок"),
            KeyboardButton(text="📦 Кейсы"),
        ],
        [
            KeyboardButton(text="🔗 Реферальная система"),
            KeyboardButton(text="💎 Донат"),
        ],
    ],
    resize_keyboard=True,
)

razvitie_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

games_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎰 Рулетка"),
            KeyboardButton(text="🃏 Блэкджек"),
        ],
        [
            KeyboardButton(text="💣 Мины"),
            KeyboardButton(text="💥 Краш"),
        ],
        [
            KeyboardButton(text="🪙 Монетка"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

settings_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="✏️ Изменить имя"),
            KeyboardButton(text="🔗 Кликабельность ника"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

ref_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👥 Рефералы"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="🗑️ Обнулить")],
        [KeyboardButton(text="🛠️ Установить"), KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="🚫 Бан"), KeyboardButton(text="🔓 Разбан")],
        [KeyboardButton(text="🔇 Мут"), KeyboardButton(text="🔈 Снять мут")],
        [KeyboardButton(text="⚠️ Варн"), KeyboardButton(text="✅ Снять варн")],
        [KeyboardButton(text="🌐 Эко Панель")],
        [KeyboardButton(text="❓ Руководство")],
        [KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

founder_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="💸 Забрать")],
        [KeyboardButton(text="🗑️ Обнулить"), KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="🛠️ Установить"), KeyboardButton(text="👑 Управление ролями")],
        [KeyboardButton(text="👥 Админы"), KeyboardButton(text="🚫 Бан")],
        [KeyboardButton(text="🔓 Разбан"), KeyboardButton(text="🔇 Мут")],
        [KeyboardButton(text="🔈 Снять мут"), KeyboardButton(text="⚠️ Варн")],
        [KeyboardButton(text="✅ Снять варн"), KeyboardButton(text="🌐 Эко Панель")],
        [KeyboardButton(text="📊 Логи"), KeyboardButton(text="⚙️ Система")],
        [KeyboardButton(text="🔑 API & Конфиги"), KeyboardButton(text="🔒 Защита")],
        [KeyboardButton(text="❓ Руководство"), KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

zam_ld_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="🗑️ Обнулить")],
        [KeyboardButton(text="🛠️ Установить"), KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="👑 Управление ролями"), KeyboardButton(text="🌐 Эко Панель")],
        [KeyboardButton(text="🚫 Бан"), KeyboardButton(text="🔓 Разбан")],
        [KeyboardButton(text="🔇 Мут"), KeyboardButton(text="🔈 Снять мут")],
        [KeyboardButton(text="⚠️ Варн"), KeyboardButton(text="✅ Снять варн")],
        [KeyboardButton(text="📊 Логи"), KeyboardButton(text="🔒 Защита")],
        [KeyboardButton(text="❓ Руководство"), KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

tech_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="📊 Логи"), KeyboardButton(text="🛡 Антиспам")],
        [KeyboardButton(text="💾 База данных"), KeyboardButton(text="🔒 Защита")],
        [KeyboardButton(text="⚙️ Система"), KeyboardButton(text="❓ Руководство")],
        [KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

admin_role_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="🚫 Бан"), KeyboardButton(text="🔓 Разбан")],
        [KeyboardButton(text="🔇 Мут"), KeyboardButton(text="🔈 Снять мут")],
        [KeyboardButton(text="⚠️ Варн"), KeyboardButton(text="✅ Снять варн")],
        [KeyboardButton(text="🌐 Эко Панель")],
        [KeyboardButton(text="❓ Руководство"), KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)


designer_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎨 Редактор текстов"), KeyboardButton(text="😊 Редактор эмодзи")],
        [KeyboardButton(text="📝 Сообщения бота"),   KeyboardButton(text="📋 Репорты")],
        [KeyboardButton(text="ℹ️ Информация"),        KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

moder_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔇 Мут"),      KeyboardButton(text="🔈 Снять мут")],
        [KeyboardButton(text="⚠️ Варн"),      KeyboardButton(text="✅ Снять варн")],
        [KeyboardButton(text="📨 Жалобы"),    KeyboardButton(text="📋 Репорты")],
        [KeyboardButton(text="ℹ️ Информация"), KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

follower_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Репорты"),    KeyboardButton(text="ℹ️ Информация")],
        [KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

def get_razvitie_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏦 Банк",   callback_data="rzv_bank"),
            InlineKeyboardButton(text="🛡 Кланы",  callback_data="rzv_klan"),
        ],
        [
            InlineKeyboardButton(text="🖥 Ферма", callback_data="rzv_ferma"),
        ],
        [
            InlineKeyboardButton(text="🏡 Дом", callback_data="rzv_dom"),
            InlineKeyboardButton(text="🏎 Авто", callback_data="rzv_avto"),
        ],
        [
            InlineKeyboardButton(text="🏢 Бизнес", callback_data="rzv_biz"),
        ],
        [
            InlineKeyboardButton(text="🏪 Магазин", callback_data="rzv_magazin"),
        ],
    ])


def get_razvitie_shop_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Купить дом", callback_data="rzv_mag_dom"),
            InlineKeyboardButton(text="🕍 Гоночные авто", callback_data="rzv_mag_avto"),
        ],
        [
            InlineKeyboardButton(text="🏢 Купить бизнес", callback_data="rzv_mag_biz"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="rzv_back"),
        ],
    ])


def eco_panel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать промо", callback_data="eco_create_promo"),
                InlineKeyboardButton(text="📋 Промокоды", callback_data="eco_list_promos"),
            ],
            [
                InlineKeyboardButton(text="🎰 Создать розыгрыш", callback_data="eco_create_raffle"),
                InlineKeyboardButton(text="📋 Все розыгрыши", callback_data="eco_list_raffles"),
            ],
        ]
    )


admin_set_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Ник", callback_data="set_name"),
        ],
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="set_balance"),
            InlineKeyboardButton(text="🏦 Банк", callback_data="set_bank"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_set"),
        ],
    ]
)


def get_admin_set_kb(user_id: int) -> InlineKeyboardMarkup:
    from admin_roles import get_role, ROLE_FOUNDER
    role = get_role(user_id)
    rows = [
        [InlineKeyboardButton(text="✏️ Ник", callback_data="set_name")],
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="set_balance"),
            InlineKeyboardButton(text="🏦 Банк", callback_data="set_bank"),
        ],
    ]
    if role == ROLE_FOUNDER:
        rows.append([InlineKeyboardButton(text="🆔 Game ID", callback_data="set_game_id")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_set")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_bank_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Пополнить", callback_data="bank_save_add"),
                InlineKeyboardButton(text="➖ Снять", callback_data="bank_save_withdraw"),
            ],
            [
                InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits"),
            ],
        ]
    )

def get_deposit_terms_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день — 3%/день", callback_data="deposit_1d")],
            [InlineKeyboardButton(text="3 дня — 5%/день", callback_data="deposit_3d")],
            [InlineKeyboardButton(text="7 дней — 7%/день", callback_data="deposit_7d")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
        ]
    )

def get_bank_action_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Положить", callback_data="bank_save_add")],
            [InlineKeyboardButton(text="➖ Снять", callback_data="bank_save_withdraw")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
        ]
    )
