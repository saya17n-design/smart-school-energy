import asyncio
import datetime
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# ---------------- Bell schedule ----------------
bell_schedule = [
    ("08:00", "08:45"),
    ("08:50", "09:35"),
    ("09:50", "10:35"),
    ("10:50", "11:35"),
    ("11:50", "12:35"),
    ("12:50", "13:35"),
    ("13:45", "14:30"),
    ("14:40", "15:25"),
    ("15:30", "16:15")
]

# ---------------- Data storage ----------------
user_schedules = {}
user_points = {}
user_devices = {}
watchdog_mode = {}

# ---------------- AI schedule analysis ----------------
def analyze_schedule(user_id):
    today = user_schedules.get(user_id, [])
    now = datetime.datetime.now().time()
    actions = []

    for i, (start, end) in enumerate(bell_schedule, start=1):
        start_time = datetime.datetime.strptime(start, "%H:%M").time()
        end_time = datetime.datetime.strptime(end, "%H:%M").time()

        if i > len(today):
            continue

        subject = today[i - 1]

        if subject == "-":
            if start_time <= now <= end_time:
                actions.append(f"Classroom is empty now (lesson {i}) | close the window, turn off the computer, turn off the lights 💡")
                add_points(user_id, 5)
        else:
            delta = (
                datetime.datetime.combine(datetime.date.today(), start_time)
                - datetime.datetime.now()
            ).total_seconds()
            if 0 < delta <= 900:  # 15 minutes before
                actions.append(f"In 15 minutes lesson {i} ({subject}) | prepare the equipment 📚")

    if not actions:
        actions.append("No recommendations at the moment ✅")

    return "\n".join(actions)

# ---------------- Green points system ----------------
def add_points(user_id, pts):
    user_points[user_id] = user_points.get(user_id, 0) + pts

def get_points(user_id):
    return user_points.get(user_id, 0)

# ---------------- Virtual devices ----------------
def add_device(user_id, device):
    user_devices.setdefault(user_id, []).append({"name": device, "status": "off"})

def toggle_device(user_id, device):
    for d in user_devices.get(user_id, []):
        if d["name"] == device:
            d["status"] = "on" if d["status"] == "off" else "off"
            return d["status"]
    return None

def list_devices(user_id):
    return user_devices.get(user_id, [])

# ---------------- Money saved simulation ----------------
def money_saved(user_id):
    points = get_points(user_id)
    money = points * 2
    if money >= 6000:
        return f"You saved {money}₸! 🎉 Equivalent to a train trip from Pavlodar to Almaty 🚆"
    elif money >= 1000:
        return f"You saved {money}₸! 🎉 Equivalent to a cinema trip with friends 🍿"
    elif money >= 10:
        return f"You saved {money}₸! 🎉 Equivalent to the cost of stationery 💰 Keep saving!"
    else:
        return f"You saved {money}₸ 💰 Keep saving!"

# ---------------- AI load forecast ----------------
def forecast_load(user_id):
    devices = user_devices.get(user_id, [])
    active = sum(1 for d in devices if d["status"] == "on")
    forecast = active * random.randint(50, 150)
    return f"Energy consumption forecast for the next hour: {forecast} W ⚡️"

# ---------------- Smart watchdog ----------------
def toggle_watchdog(user_id):
    watchdog_mode[user_id] = not watchdog_mode.get(user_id, False)
    return "enabled 🛡" if watchdog_mode[user_id] else "disabled ❌"

# ---------------- Commands ----------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Schedule", callback_data="schedule")],
        [InlineKeyboardButton(text="💡 Devices", callback_data="devices")],
        [InlineKeyboardButton(text="🌱 Points", callback_data="points"),
         InlineKeyboardButton(text="💰 Money", callback_data="money")],
        [InlineKeyboardButton(text="⚡️ Forecast", callback_data="forecast")],
        [InlineKeyboardButton(text="🛡 Smart watchdog", callback_data="watchdog")]
    ])
    await message.answer("Hi! I am a smart assistant for schools 🏫", reply_markup=kb)

@dp.callback_query()
async def callbacks(call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data

    if data == "schedule":
        await call.message.answer(
            "Send your schedule for the day (9 lines, one subject each).\n"
            "Example:\nMath\nPhysics\n-\nHistory\n-\n-\n-\n-\n-"
        )

    elif data == "devices":
        devices = list_devices(user_id)
        if not devices:
            await call.message.answer("You don’t have any devices yet. Add one with: add [name]")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{d['name']} ({d['status']})", callback_data=f"toggle:{d['name']}")]
                for d in devices
            ])
            await call.message.answer("Your devices:", reply_markup=kb)

    elif data.startswith("toggle:"):
        device = data.split(":")[1]
        status = toggle_device(user_id, device)
        await call.answer(f"{device} → {status}")

    elif data == "points":
        await call.message.answer(f"Your green points: {get_points(user_id)} 🌱")

    elif data == "money":
        await call.message.answer(money_saved(user_id))

    elif data == "forecast":
        await call.message.answer(forecast_load(user_id))

    elif data == "watchdog":
        status = toggle_watchdog(user_id)
        await call.message.answer(f"Smart watchdog mode {status}")

@dp.message()
async def get_schedule_or_devices(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Add device
    if text.startswith("add "):
        device = text[4:]
        add_device(user_id, device)
        await message.answer(f"Device {device} added ✅")
        return

    # If it's a schedule
    lessons = text.split("\n")
    if len(lessons) == 9:
        user_schedules[user_id] = lessons
        result = analyze_schedule(user_id)
        await message.answer("Schedule accepted ✅\n\n" + result)
    else:
        # Always reply with analysis too
        result = analyze_schedule(user_id)
        await message.answer("Unknown command or wrong format.\n\n" + result)

# ---------------- Automatic reminders ----------------
async def auto_actions():
    while True:
        for user_id in user_schedules.keys():
            result = analyze_schedule(user_id)
            await bot.send_message(user_id, result)
        await asyncio.sleep(2400)  # every 40 minutes

# ---------------- Run ----------------
async def main():
    asyncio.create_task(auto_actions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())