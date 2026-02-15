import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==========================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ==========================================
API_TOKEN = '8539613400:AAHMTojTM1haqncFTcoBvgSPD6rIO-vHX6w'
CHANNEL_ID = '@pcmagaz' 
ADMIN_IDS = [8002061677, 6768271408] 
NEWS_LINK = 'https://t.me/NGB_B' # Ссылка на новостной канал

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хранилище для защиты от дублей (чтобы админы не публиковали одно и то же дважды)
published_messages = set()

class Form(StatesGroup):
    photo = State()
    description = State()
    price = State()
    link = State()
    confirm = State()

def format_price(raw_price):
    """Оставляет только цифры и делает формат: 25 000 руб"""
    clean_digits = "".join([c for c in raw_price if c.isdigit()])
    if not clean_digits:
        return None
    # Форматирование числа с пробелами
    formatted = f"{int(clean_digits):,}".replace(",", " ")
    return f"{formatted} руб"

def create_final_caption(data, user, user_id):
    """Финальный дизайн объявления"""
    
    if user:
        seller_line = f"@{user} (ID: {user_id})"
    else:
        seller_line = f"ID: {user_id}"

    return (
        f"<b>НОВОЕ ОБЪЯВЛЕНИЕ</b>\n\n"
        f"📝 <b>Описание:</b> {data['description']}\n\n"
        f"💰 <b>Цена:</b> {data['price']}\n\n"
        f"🔗 <b>Ссылка:</b> <a href='{data['link']}'>открыть на сайте</a>\n\n"
        f"📢 <b>Новости:</b> <a href='{NEWS_LINK}'>Новостной канал</a>\n\n"
        f"⚠️ <b>ДИСКЛЕЙМЕР:</b>\n"
        f"<i>Друзья, если хотите что-то купить по объявлению — смотрите профиль продавца и будьте внимательны! "
        f"Покупайте только через «Авито Доставку» или «Юлу»! Никогда не переводите деньги напрямую на карту.</i>\n\n"
        f"P.S. Если Telegram не пропустил ссылку на ваше объявление, отправьте её в комментарии.\n\n"
        f"Чтобы выложить объявление: @pc_magaz_bot\n"
        f"👤 <b>Продавец:</b> {seller_line}"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Новости проекта", url=NEWS_LINK)]
    ])
    await message.answer(
        "👋 Привет! Чтобы подать объявление, пришлите <b>одно фото</b> товара.", 
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Введите <b>описание</b> (лимит до ~360 символов,увы исправить нельзя):", parse_mode="HTML")
    await state.set_state(Form.description)

@dp.message(Form.description, F.text)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Укажите <b>цену</b> (только цифры):", parse_mode="HTML")
    await state.set_state(Form.price)

@dp.message(Form.price, F.text)
async def process_price(message: types.Message, state: FSMContext):
    formatted_price = format_price(message.text)
    if formatted_price is None:
        await message.answer("❌ <b>Ошибка!</b> Введите цену только цифрами (например: 15000).", parse_mode="HTML")
        return
    await state.update_data(price=formatted_price)
    await message.answer("Пришлите <b>ссылку</b> (Авито/Юла):", parse_mode="HTML")
    await state.set_state(Form.link)

@dp.message(Form.link, F.text)
async def process_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if "avito.ru" in link.lower() or "youla.ru" in link.lower():
        await state.update_data(link=link)
        data = await state.get_data()
        
        caption = create_final_caption(data, message.from_user.username, message.from_user.id)
        
        await message.answer_photo(
            data['photo'], 
            caption=f"<b>Предпросмотр:</b>\n\n{caption}", 
            parse_mode="HTML"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить на модерацию", callback_data="send_to_admin")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data="cancel_post")]
        ])
        await message.answer("Все верно?", reply_markup=kb)
        await state.set_state(Form.confirm)
    else:
        await message.answer("❌ Нужна ссылка на <b>avito.ru</b> или <b>youla.ru</b>", parse_mode="HTML")

@dp.callback_query(Form.confirm)
async def send_to_moderation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "send_to_admin":
        data = await state.get_data()
        final_caption = create_final_caption(data, callback.from_user.username, callback.from_user.id)

        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data="admin_publish")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data="admin_decline")]
        ])

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(admin_id, photo=data['photo'], caption=final_caption, parse_mode="HTML", reply_markup=admin_kb)
            except:
                pass
        await callback.message.answer("🚀 Объявление отправлено на модерацию!")
    else:
        await callback.message.answer("❌ Удалено.")
    
    await callback.message.delete()
    await state.clear()

@dp.callback_query(F.data.startswith("admin_"))
async def admin_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Нет прав.")

    # Создаем ключ, чтобы не было дублей при нажатии обоими админами
    msg_key = f"{callback.message.chat.id}_{callback.message.message_id}"

    if callback.data == "admin_publish":
        if msg_key in published_messages:
            await callback.answer("⚠️ Уже опубликовано другим админом!", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return

        try:
            await bot.copy_message(CHANNEL_ID, callback.message.chat.id, callback.message.message_id)
            published_messages.add(msg_key) # Помечаем как опубликованное
            await callback.message.edit_reply_markup(reply_markup=None)
            await bot.send_message(callback.from_user.id, "✅ Успешно опубликовано!")
        except Exception as e:
            await callback.answer(f"Ошибка: {e}", show_alert=True)
            
    elif callback.data == "admin_decline":
        await callback.message.delete()
        published_messages.add(msg_key)

async def main():
    print("Бот запущен! Дизайн обновлен, защита от дублей включена.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
