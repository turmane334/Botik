
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, text TEXT, timestamp DATETIME)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()
def save_message(user_name, text):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_name, text, timestamp) VALUES (?, ?, ?)',
                   (user_name, text, datetime.now()))
    conn.commit()
    conn.close()
def set_group_id(group_id):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("main_group_id", ?)', (str(group_id),))
    conn.commit()
    conn.close()
def get_group_id():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "main_group_id"')
    row = cursor.fetchone()
    conn.close()
    return int(row[0]) if row else None
def get_history(limit=500):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_name, text FROM messages ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
def clear_history():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()
# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start_here"), F.chat.type.in_({"group", "supergroup"}))
async def register_group(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        set_group_id(message.chat.id)
        await message.answer("📍 Группа привязана. Начинаю протоколировать события.")
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def collector(message: types.Message):
    reg_id = get_group_id()
    if reg_id and message.chat.id == reg_id and message.text:
        save_message(message.from_user.full_name or "User", message.text)
@dp.message(Command("report"), F.chat.type == "private")
async def send_report(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    history = get_history()
    if not history:
        return await message.answer("В архивах пусто.")
    
    raw_data = "\n".join([f"[{u}]: {t}" for u, t in reversed(history)])
    if len(raw_data) > 3500:
        with open("logs.txt", "w", encoding="utf-8") as f: f.write(raw_data)
        await message.answer_document(types.FSInputFile("logs.txt"), caption="Сырые логи")
    else:
        await message.answer(f"```\n{raw_data}\n```", parse_mode="MarkdownV2")
@dp.message(Command("publish"), F.chat.type == "private")
async def publish_story(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    group_id = get_group_id()
    if not group_id:
        return await message.answer("Сначала напиши /start_here в группе.")
    text = message.text.replace("/publish", "").strip()
    if not text:
        return await message.answer("Добавь текст новости после команды.")
    # Формируем красивый пост
    today = datetime.now().strftime("%d.%m.%Y")
    final_post = (
        f"📢 *ВАЖНЫЕ НОВОСТИ ЗА СЕГОДНЯ* ({today})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡️ *Будьте в курсе событий!*"
    )
    try:
        await bot.send_message(group_id, final_post, parse_mode="Markdown")
        await message.answer("🚀 Опубликовано!")
        # Опционально: очистить историю, чтобы завтра начать с чистого листа
        # clear_history() 
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
async def main():
    init_db()
    await dp.start_polling(bot)
if __name__ == '__main__':
    asyncio.run(main())
