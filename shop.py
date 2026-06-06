from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data

router = Router()

EMOJI_NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

ASSET_EMOJIS = {
    "cars": "🚗",
    "flats": "🏢",
    "houses": "🏠",
    "planes": "✈️",
    "helicopters": "🚁",
    "smartphones": "📱",
    "watches": "⌚",
}

SELL_SYNONYMS = {
    "cars": ["машина", "машину", "автомобиль", "авто", "тачка", "тачку", "машины"],
    "flats": ["квартира", "квартиру", "квартиры", "хата", "хату"],
    "houses": ["дом", "дома", "домик", "хата", "хату"],
    "planes": ["самолёт", "самолет", "самолеты", "самолёты", "самолётик", "самолетик"],
    "helicopters": ["вертолёт", "вертолет", "вертолеты", "вертолёты", "вертолётик", "вертолетик"],
    "smartphones": ["телефон", "смартфон", "смартфоны", "телефоны", "мобильник"],
    "watches": ["часы", "часики", "watch", "watches"],
}

SHOP_ITEMS = {
    "smartphones": [
        {"name": "Nokia 105 (2024)", "price": 900},
        {"name": "Realme C53", "price": 3500},
        {"name": "Samsung Galaxy A15", "price": 6500},
        {"name": "Xiaomi Redmi Note 13", "price": 9000},
        {"name": "Nothing Phone (2a)", "price": 12000},
        {"name": "Google Pixel 8a", "price": 18000},
        {"name": "OnePlus 12R", "price": 22000},
        {"name": "Samsung Galaxy S24 Ultra", "price": 35000},
        {"name": "iPhone 15 Pro Max", "price": 40000},
        {"name": "Xiaomi 14 Ultra", "price": 42000},
    ],
    "cars": [
        {"name": "Lada Granta", "price": 5000},
        {"name": "Kia Rio", "price": 12000},
        {"name": "Volkswagen Polo", "price": 18000},
        {"name": "Hyundai Solaris", "price": 25000},
        {"name": "Toyota Camry", "price": 35000},
        {"name": "BMW 3 Series", "price": 60000},
        {"name": "Mercedes-Benz E-Class", "price": 90000},
        {"name": "Audi A8", "price": 120000},
        {"name": "Porsche 911", "price": 250000},
        {"name": "Lamborghini Revuelto", "price": 400000},
    ],
    "flats": [
        {"name": "Комната в общаге", "price": 3000},
        {"name": "Однушка в хрущёвке", "price": 8000},
        {"name": "Двушка в панельке", "price": 15000},
        {"name": "Трешка в новостройке", "price": 30000},
        {"name": "Студия в центре", "price": 50000},
        {"name": "Евродвушка", "price": 70000},
        {"name": "Элитная квартира", "price": 120000},
        {"name": "Пентхаус", "price": 250000},
        {"name": "Лофт", "price": 400000},
        {"name": "Апартаменты", "price": 600000},
    ],
    "houses": [
        {"name": "Дачный домик", "price": 20000},
        {"name": "Коттедж в пригороде", "price": 70000},
        {"name": "Загородный дом", "price": 150000},
        {"name": "Вилла на море", "price": 300000},
        {"name": "Особняк", "price": 600000},
        {"name": "Резиденция", "price": 1200000},
        {"name": "Замок", "price": 2500000},
        {"name": "Дворец", "price": 4000000},
        {"name": "Остров", "price": 12000000},
        {"name": "Супер-особняк", "price": 30000000},
    ],
    "planes": [
        {"name": "Cessna 172", "price": 20000},
        {"name": "Piper PA-28", "price": 35000},
        {"name": "Beechcraft Baron", "price": 60000},
        {"name": "Pilatus PC-12", "price": 120000},
        {"name": "Embraer Phenom 300", "price": 250000},
        {"name": "Bombardier Challenger 350", "price": 400000},
        {"name": "Gulfstream G650", "price": 700000},
        {"name": "Dassault Falcon 8X", "price": 1200000},
        {"name": "Boeing 737", "price": 2500000},
        {"name": "Airbus A320", "price": 3000000},
    ],
    "helicopters": [
        {"name": "Robinson R44", "price": 9000},
        {"name": "Bell 206", "price": 20000},
        {"name": "Eurocopter EC120", "price": 35000},
        {"name": "AgustaWestland AW109", "price": 60000},
        {"name": "Bell 429", "price": 90000},
        {"name": "Airbus H145", "price": 150000},
        {"name": "Sikorsky S-76", "price": 250000},
        {"name": "AgustaWestland AW139", "price": 400000},
        {"name": "Bell 525 Relentless", "price": 700000},
        {"name": "Airbus H225", "price": 1200000},
    ],
    "watches": [
        {"name": "Casio F-91W", "price": 200},
        {"name": "Swatch Originals", "price": 800},
        {"name": "Seiko 5", "price": 2000},
        {"name": "Citizen Eco-Drive", "price": 3500},
        {"name": "Tissot PRX", "price": 7000},
        {"name": "TAG Heuer Carrera", "price": 20000},
        {"name": "Omega Seamaster", "price": 40000},
        {"name": "Rolex Submariner", "price": 120000},
        {"name": "Audemars Piguet Royal Oak", "price": 300000},
        {"name": "Patek Philippe Nautilus", "price": 600000},
    ],
}

CATEGORY_NAMES = {
    "smartphones": "Смартфоны",
    "cars": "Машины",
    "flats": "Квартиры",
    "houses": "Дома",
    "planes": "Самолёты",
    "helicopters": "Вертолёты",
    "watches": "Часы",
}

def get_shop_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Машины", callback_data="shop_cars")],
            [InlineKeyboardButton(text="🏢 Квартиры", callback_data="shop_flats")],
            [InlineKeyboardButton(text="🏠 Дома", callback_data="shop_houses")],
            [InlineKeyboardButton(text="✈️ Самолёты", callback_data="shop_planes")],
            [InlineKeyboardButton(text="🚁 Вертолёты", callback_data="shop_helicopters")],
            [InlineKeyboardButton(text="📱 Смартфоны", callback_data="shop_smartphones")],
            [InlineKeyboardButton(text="⌚ Часы", callback_data="shop_watches")],
        ]
    )

def get_shop_items_kb(category):
    # 10 кнопок в 2 ряда по 5, с эмодзи-цифрами
    buttons = [
        InlineKeyboardButton(text=EMOJI_NUMBERS[i], callback_data=f"buy_{category}_{i}")
        for i in range(10)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[:5],
            buttons[5:],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")]
        ]
    )

@router.message(F.text.lower().in_(["магазин", "shop", "🛒 магазин", 'магаз']))
async def show_shop_menu(message: Message):
    await message.answer("🛒 Магазин. Выберите категорию:", reply_markup=get_shop_main_kb())

@router.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: CallbackQuery):
    category = callback.data.replace("shop_", "")
    if category == "main":
        await callback.message.edit_text("🛒 Магазин. Выберите категорию:", reply_markup=get_shop_main_kb())
        await callback.answer()
        return
    items = SHOP_ITEMS.get(category)
    if not items:
        await callback.answer("Категория не найдена.")
        return
    text = f"📦 {CATEGORY_NAMES.get(category, category).capitalize()}:\n\n"
    for i, item in enumerate(items):
        text += f"{EMOJI_NUMBERS[i]} {item['name']} — {item['price']}$\n"
    text += "\nВыберите номер для покупки:"
    await callback.message.edit_text(text, reply_markup=get_shop_items_kb(category))
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def buy_shop_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    category = parts[1]
    idx = int(parts[2])
    item = SHOP_ITEMS[category][idx]
    user = get_user(user_id)

    # Проверка на наличие уже купленного предмета (лимит 1)
    _owned = user.get(category)
    _has_item = bool(_owned) if not isinstance(_owned, list) else len(_owned) > 0
    if _has_item:
        _name = _owned if isinstance(_owned, str) else (_owned[0] if _owned else "")
        await callback.answer(
            f"❌ У вас уже есть: {_name}\nСначала продайте его.\nКоманда: продать {category}",
            show_alert=True
        )
        return

    balance = get_balance(user_id)
    if balance < item["price"]:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return

    # Покупка
    update_balance(user_id, balance - item["price"])
    user[category] = item["name"]
    save_user_data()
    await callback.message.edit_text(f"✅ Вы купили {item['name']} за {item['price']}$!", reply_markup=get_shop_main_kb())
    await callback.answer()

@router.message(F.text.lower().startswith("продать "))
async def sell_item(message: Message):
    user_id = message.from_user.id
    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.answer("Укажите, что вы хотите продать (например, `продать смартфон`).")
        return
    word = parts[1]
    category = find_category_by_synonym(word)
    if not category:
        # fallback: старый способ
        if word.endswith("ы") or word.endswith("и"):
            category = word[:-1] + "s"
        else:
            category = word
    user = get_user(user_id)
    _raw = user.get(category)
    item_name = _raw if isinstance(_raw, str) else (_raw[0] if isinstance(_raw, list) and _raw else None)
    if not item_name:
        await message.answer("У вас нет такого предмета.")
        return
    price = next((item["price"] for item in SHOP_ITEMS[category] if item["name"] == item_name), None)
    if not price:
        await message.answer("Ошибка при продаже.")
        return
    sell_price = int(price * 0.6)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user[category] = None
    save_user_data()
    await message.answer(f"Вы продали {item_name} за {sell_price}$!")

def get_assets_text(user):
    assets = []
    for cat in SHOP_ITEMS.keys():
        if user.get(cat):
            emoji = ASSET_EMOJIS.get(cat, "")
            assets.append(f"{emoji}: {user[cat]}")
    return "\n".join(assets) if assets else "Нет имущества"

def find_category_by_synonym(word):
    for cat, synonyms in SELL_SYNONYMS.items():
        if word in synonyms:
            return cat
    return None

