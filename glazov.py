import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Новые настройки
API_TOKEN = '8539613400:AAHMTojTM1haqncFTcoBvgSPD6rIO-vHX6w'
CHANNEL_ID = '@pcmagaz'  # Твой новый канал
ADMIN_IDS = [8002061677, 6768271408]  # Список ID новых администраторов

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    photo = State()
    description = State()
    price = State()
    link = State()
    confirm = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Привет! Чтобы подать объявление, пришлите <b>одно фото</b> товара.", parse_mode="HTML")
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Введите <b>Описание:</b>", parse_mode="HTML")
    await state.set_state(Form.description)

@dp.message(Form.description, F.text)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите <b>Цену:</b>", parse_mode="HTML")
    await state.set_state(Form.price)

@dp.message(Form.price, F.text)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Пришлите <b>Ссылку</b> на Авито или Юлу:", parse_mode="HTML")
    await state.set_state(Form.link)

@dp.message(Form.link, F.text)
async def process_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if "avito.ru" in link.lower() or "youla.ru" in link.lower():
        await state.update_data(link=link)
        data = await state.get_data()
        user_name = f"@{message.from_user.username}" if message.from_user.username else "скрыт"
        
        preview_text = (
            f"📝 <b>Описание:</b> {data['description']}\n"
            f"💰 <b>Цена:</b> {data['price']}\n\n"
            f"🔗 <b>Ссылка:</b> <a href='{data['link']}'>открыть на сайте</a>\n\n"
            f"⚠️ <b>ДИСКЛЕЙМЕР:</b>\n"
            f"<i>Друзья, если хотите что-то купить по объявлению — смотрите профиль продавца и будьте внимательны! "
            f"Покупайте только через «Авито Доставку» или «Юлу»! Никогда не переводите деньги напрямую на карту.</i>\n\n"
            f"P.S. Если Telegram не пропустил ссылку на ваше объявление, отправьте её в комментарии.\n\n"
            f"Чтобы выложить объявление: @pc_magaz_bot\n"
            f"👤 <b>Продавец:</b> {user_name} (ID: {message.from_user.id})"
        )
        
        await message.answer_photo(data['photo'], caption=f"<b>Предпросмотр:</b>\n\n{preview_text}", parse_mode="HTML")
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить на модерацию", callback_data="send_to_admin")],
            [InlineKeyboardButton(text="❌ Удалить и начать заново", callback_data="cancel_post")]
        ])
        await message.answer("Все верно?", reply_markup=kb)
        await state.set_state(Form.confirm)
    else:
        await message.answer("❌ Ошибка! Нужна ссылка на avito.ru или youla.ru")

@dp.callback_query(Form.confirm)
async def send_to_moderation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "send_to_admin":
        data = await state.get_data()
        user_name = f"@{callback.from_user.username}" if callback.from_user.username else "скрыт"
        
        final_caption = (
            f"📝 <b>Описание:</b> {data['description']}\n"
            f"💰 <b>Цена:</b> {data['price']}\n\n"
            f"🔗 <b>Ссылка:</b> <a href='{data['link']}'>открыть на сайте</a>\n\n"
            f"⚠️ <b>ДИСКЛЕЙМЕР:</b>\n"
            f"<i>Друзья, если хотите что-то купить по объявлению — смотрите профиль продавца и будьте внимательны! "
            f"Покупайте только через «Авито Доставку» или «Юлу»! Никогда не переводите деньги напрямую на карту.</i>\n\n"
            f"P.S. Если Telegram не пропустил ссылку на ваше объявление, отправьте её в комментарии.\n\n"
            f"Чтобы выложить объявление: @pc_magaz_bot\n"
            f"👤 <b>Продавец:</b> {user_name} (ID: {callback.from_user.id})"
        )

        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data="admin_publish")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data="admin_decline")]
        ])

        # Рассылка всем админам из списка
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(admin_id, photo=data['photo'], caption=final_caption, parse_mode="HTML", reply_markup=admin_kb)
            except Exception as e:
                print(f"Не удалось отправить админу {admin_id}: {e}")

        await callback.message.answer("🚀 Ваше объявление отправлено на проверку администраторам!")
    else:
        await callback.message.answer("❌ Объявление удалено.")
    
    await callback.message.delete()
    await state.clear()

@dp.callback_query(F.data.startswith("admin_"))
async def admin_action(callback: CallbackQuery):
    # Проверка, что нажал один из админов
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("У вас нет прав.")

    if callback.data == "admin_publish":
        try:
            await bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id
            )
            # Убираем кнопки у того админа, кто нажал
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply("✅ Опубликовано в канал!")
        except Exception as e:
            await callback.answer(f"Ошибка: {e}", show_alert=True)
            
    elif callback.data == "admin_decline":
        await callback.message.delete()
        await callback.answer("Объявление отклонено")

async def main():
    print("Бот запущен с новыми админами и каналом!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())