import json
import random
import http.client
import re
import datetime
from aiogram import Router
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form, LogState
import aiohttp
from config import Config
from aiogram.utils.keyboard import KeyboardBuilder
from googletrans import Translator

translator = Translator()

router = Router()

users = {}

activity_levels = {
    "минимальная физическая нагрузка": 1.2,
    "умеренная активность": 1.38,
    "тренировки средней интенсивности 5 раз в неделю": 1.46,
    "интенсивные тренировки 5 раз в неделю": 1.55,
    "каждодневные тренировки": 1.64,
    "интенсивные тренировки каждый день": 1.73,
    "тяжелые физические нагрузки каждый день или дважды в день": 1.9,
}

activities = {
    "Бег (8 км/ч)": 7,
    "Плавание (2,5 км/ч)": 7,
    "Езда на велосипеде (15 км/ч)": 5,
    "Танцы": 5,
    "Футбол": 6,
    "Ходьба на лыжах": 7,
    "Баскетбол\Волейбол": 5,
    "Гребля на каноэ (4 км/ч)": 3,
    "Зарядка средней интенсивности": 4,
    "Занятия аэробикой": 5,
    "Статическая йога": 3,
    "Пешая прогулка (5,8 км/ч)": 5,
    "Катание на коньках\роликах": 4,
    "Прогулка с собакой": 3,
    "Теннис": 6,
    "Хоккей": 4,
    "Медленная ходьба": 3,
}


# Расчёт дневных норм воды и калорий
def calculate_daily_norms(weight, height, age, activity_coefficient, sex, temperature):
    water_norms = 0
    if temperature > 25:
        water_norms += 500
    if sex == "Мужчина":
        calorie_norms = (
            10 * weight + 6.25 * height - 5 * age + 5
        ) * activity_coefficient
        water_norms += (weight * 35) * activity_coefficient
    else:
        calorie_norms = (
            10 * weight + 6.25 * height - 5 * age - 161
        ) * activity_coefficient
        water_norms += (weight * 31) * activity_coefficient
    return int(water_norms), int(calorie_norms)


# Получение данных о температуре
async def get_current_temperature_async(city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    temperature = float(data["main"]["temp"])
                    return temperature
                elif response.status == 401:
                    return None, "Неверный API-ключ. Пожалуйста, проверьте ключ."
                else:
                    return None, "Ошибка при запросе данных для города."
    except Exception as e:
        return None, f"Произошла ошибка: {str(e)}"


async def get_random_exercise(api_key):
    url = "https://exercisedb.p.rapidapi.com/exercises?limit=10&offset=0"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "exercisedb.p.rapidapi.com",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return random.choice(data)
            else:
                return None


def translate_text(text, target_language="ru"):
    translated = translator.translate(text, dest=target_language)
    return translated.text


# получение данных о калориях продукта
async def get_product_calorie(product_name):
    """Получение данных о калорийности продукта"""

    # Формируем URL для запроса (поиск по имени)
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": product_name,
        "json": 1,
        "fields": "product_name,code,nutriments",
        "page_size": 1,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("products"):
                        product = data["products"][0]
                        # Получаем калории на 100 грамм
                        calories_100g = product.get("nutriments", {}).get(
                            "energy-kcal_100g", 0
                        )
                        return calories_100g
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def create_activity_levels_keyboard():
    kb_list = []
    for activity in activity_levels.keys():
        kb_list.append([KeyboardButton(text=activity)])
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите уровень активности:",
    )
    return keyboard


def gender_keyboard():
    kb_list = [[KeyboardButton(text="Мужчина")], [KeyboardButton(text="Женщина")]]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите пол:",
    )
    return keyboard


def create_activities_keyboard():
    kb_list = []
    for activity in activities.keys():
        kb_list.append([KeyboardButton(text=activity)])
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите активность:",
    )
    return keyboard


# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "Добро пожаловать! Я ваш бот.\nВведите /help для списка команд."
    )


# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля пользователя\n"
        "/get_daily_norms - Значения дневных норм калорий и воды\n"
        "/log_food - Сохранение данных о калорийности, расчет остатка до выполнения нормы\n"
        "/log_water - Сохранение данных о выпитой воде, расчет остатка до выполнения нормы\n"
        "/log_workout <тип тренировки> <время (мин)> - Сохранение данных о сожженых калориях, учет расхода воды\n"
        "/get_recommendation_exercise - Получение примера упражнения\n"
        "/check_progress - Вывод информации о потреблении\расходе воды\калорий и остатка до нормы\n"
    )


# FSM: диалог с пользователем
@router.message(Command("set_profile"))
async def start_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id] = {}
    await message.reply("Введите ваш возраст")
    await state.set_state(Form.age)


@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        if int(message.text) < 110:
            users[user_id]["age"] = int(message.text)
            await state.update_data(age=message.text)
            await message.reply("Введите ваш вес (в кг)")
            await state.set_state(Form.weight)
        else:
            await process_age_incorrect(message, state)
    except Exception as e:
        await process_age_incorrect(message, state)


@router.message(Form.age)
async def process_age_incorrect(message: Message, state: FSMContext):
    await message.reply("Введите корректный возраст: введите только цифры")
    await state.set_state(Form.age)


@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        users[user_id]["weight"] = int(message.text)
        await state.update_data(weight=message.text)
        await message.reply("Введите ваш рост (в см)")
        await state.set_state(Form.height)
    except Exception as e:
        await process_weight_incorrect(message, state)


@router.message(Form.weight)
async def process_weight_incorrect(message: Message, state: FSMContext):
    await message.reply("Введите корректный вес: введите только цифры")
    await state.set_state(Form.weight)


@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        users[user_id]["height"] = int(message.text)
        await state.update_data(height=message.text)
        await message.reply("В каком городе вы находитесь?")
        await state.set_state(Form.city)
    except Exception as e:
        await process_height_incorrect(message, state)


@router.message(Form.height)
async def process_height_incorrect(message: Message, state: FSMContext):
    await message.reply("Введите корректный рост: введите только цифры")
    await state.set_state(Form.height)


@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    city_name = message.text.strip()
    try:
        temperature = await get_current_temperature_async(
            city_name, api_key=Config().API_KEY
        )
        if temperature is None:
            await process_city_incorrect(message, state)
            return
        user_id = message.from_user.id
        users[user_id]["city"] = city_name
        await state.update_data(city=city_name)
        await message.reply(
            "Если вы хотите задать вручную цель по каллориям введите цифру, иначе введите 0"
        )
        await state.set_state(Form.calories_goal)
    except Exception as e:
        await process_city_incorrect(message, state)


@router.message(Form.city)
async def process_city_incorrect(message: Message, state: FSMContext):
    await message.reply(
        "Данный город не найден! Пожалуйста, введите корректное название города."
    )
    await state.set_state(Form.city)


@router.message(Form.calories_goal)
async def process_calories(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        calories_goal = int(message.text)
        users[user_id]["calories_goal"] = calories_goal
        await state.update_data(calories_goal=calories_goal)
        await state.set_state(Form.activity_coefficient)
        await message.answer(
            "Выберите уровень физической активности:",
            reply_markup=create_activity_levels_keyboard(),
        )
    except ValueError:
        await process_calories_incorrect(message, state)


@router.message(Form.calories_goal)
async def process_calories_incorrect(message: Message, state: FSMContext):
    await message.reply("Введите корректную цель по калориям: введите только цифры")
    await state.set_state(Form.calories_goal)


@router.message(Form.activity_coefficient)
async def process_activity_level(message: Message, state: FSMContext):
    user_id = message.from_user.id
    activity_level = message.text

    if activity_level in activity_levels:
        users[user_id]["activity_coefficient"] = activity_levels[activity_level]
        await state.update_data(activity_coefficient=activity_levels[activity_level])

        await state.set_state(Form.sex)
        await message.answer(
            "Выберите ваш пол:",
            reply_markup=gender_keyboard(),
        )
    else:
        await message.answer(
            "Пожалуйста, выберите правильный уровень активности из предложенных."
        )


@router.message(Form.sex)
async def process_sex(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["sex"] = message.text
    await state.update_data(sex=message.text)
    await message.answer("Профиль заполнен!")
    await state.clear()


# может быть вынести в класс
@router.message(Command("get_daily_norms"))
async def get_daily_norms(message: Message):
    user_id = message.from_user.id

    if user_id not in users:
        await message.answer("Заполните профиль.")
        return

    user_data = users[user_id]

    # Если еще нет значений для норм воды и калорий, рассчитываем их
    if user_data.get("water_norms") is None or user_data.get("calorie_norms") is None:
        temperature = await get_current_temperature_async(
            user_data.get("city"), api_key=Config().API_KEY
        )

        if temperature is None:
            await message.answer("Ошибка при получении данных о температуре.")
            return

        # Вычисляем нормы воды и калорий
        water_norms, calorie_norms = calculate_daily_norms(
            user_data["weight"],
            user_data["height"],
            user_data["age"],
            user_data["activity_coefficient"],
            user_data["sex"],
            temperature,
        )

        if int(user_data.get("calories_goal", 0)) != 0:
            calorie_norms = int(user_data["calories_goal"])

        user_data["water_norms"] = water_norms
        user_data["calorie_norms"] = calorie_norms

    water_norms = user_data.get("water_norms")
    calorie_norms = user_data.get("calorie_norms")

    await message.answer(
        f"Цель по воде: {water_norms} мл\n" f"Цель по калориям: {calorie_norms} ккал"
    )


@router.message(Command("log_water"))
async def log_water(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Заполните profile.")
        return
    await message.answer("Введите количество выпитой воды в миллилитрах")
    await state.set_state(LogState.water_amount)


@router.message(LogState.water_amount)
async def process_water_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Заполните профиль.")
        return
    water_amount = int(message.text)
    users[user_id].setdefault("water", 0)
    users[user_id]["water"] += water_amount

    if users[user_id].get("water_norms") is None:
        await get_daily_norms(message)

    remaining_water = int(users[user_id]["water_norms"] - users[user_id]["water"])

    await message.answer(
        f"Данные сохранены! Осталось выпить {remaining_water} мл воды."
    )
    await state.clear()


@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Заполните профиль.")
        return
    await message.answer("Введите название продукта")
    await state.set_state(LogState.food_name)


@router.message(LogState.food_name)
async def process_food_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    product_name = message.text
    calories_100g = await get_product_calorie(product_name)
    if calories_100g is None:
        await message.answer("Ошибка при получении данных о продукте.")
        return
    # Сохраняем данные о продукте
    users[user_id].setdefault("calories", {})
    users[user_id]["calories"][product_name] = calories_100g

    # Сохраняем текущий продукт в состояние FSM
    await state.update_data(current_product=product_name)

    await message.answer(
        f"Калорийность продукта: {calories_100g} ккал на 100 грамм\nВведите количество продукта (в граммах)"
    )
    await state.set_state(LogState.food_weight)


@router.message(LogState.food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    weight = int(message.text)

    # Получаем текущий продукт из состояния
    user_data = await state.get_data()
    current_product = user_data.get("current_product")

    if current_product is None:
        await message.answer("Ошибка: не выбран продукт.")
        return

    # Получаем калорийность для текущего продукта
    calories_100g = users[user_id]["calories"].get(current_product)
    if calories_100g is None:
        await message.answer("Ошибка: продукт не найден в базе.")
        return

    # Рассчитываем калории для указанного веса
    calories = calories_100g * weight / 100

    # Обновляем общее количество съеденных калорий пользователя
    users[user_id].setdefault("food", 0)
    users[user_id]["food"] += calories

    await message.answer(
        f"Съедено {current_product} на {calories} ккал\nДанные сохранены!"
    )

    await state.clear()


@router.message(Command("log_workout"))
async def log_workout(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in users:
        await message.answer("Заполните профиль.")
        return

    await message.answer(
        "Выберите активность:", reply_markup=create_activities_keyboard()
    )
    await state.set_state(LogState.workout_type)


@router.message(LogState.workout_type)
async def select_activity(message: Message, state: FSMContext):
    activity = message.text

    if activity not in activities:
        await message.answer("Пожалуйста, выберите одну из предложенных активностей.")
        return

    await state.update_data(selected_activity=activity)

    await message.answer("Введите время тренировки в минутах:")
    await state.set_state(LogState.workout_time)


@router.message(LogState.workout_time)
async def input_time(message: Message, state: FSMContext):
    try:
        time = int(message.text)
        if time <= 0:
            raise ValueError("Время должно быть положительным числом.")
    except ValueError as e:
        await message.answer("Введите правильное число минут.")
        return

    user_data = await state.get_data()
    activity = user_data.get("selected_activity")
    calories_per_minute = activities.get(activity)
    user_id = message.from_user.id

    total_calories = (calories_per_minute * users[user_id]["weight"] * time) / 60

    # Обновляем сожженные калории
    users[user_id].setdefault("burned_calories", 0)
    users[user_id]["burned_calories"] += total_calories

    await message.answer(
        f"Вы выбрали активность: {activity}\n"
        f"Время тренировки: {time} минут\n"
        f"Вы сожгли {total_calories} калорий!"
    )

    await state.clear()


@router.message(Command("get_recommendation_exercise"))
async def get_recommendation_exercise(message: Message):
    random_exercise = await get_random_exercise(Config().Exercise_API_KEY)

    name = random_exercise.get("name", "Неизвестное упражнение")
    body_part = random_exercise.get("bodyPart", "Не указано")
    equipment = random_exercise.get("equipment", "Не указано")
    target = random_exercise.get("target", "Не указано")
    secondary_muscles = (
        ", ".join(random_exercise.get("secondaryMuscles", [])) or "Не указаны"
    )
    instructions = "\n".join(random_exercise.get("instructions", ["Нет инструкций"]))

    # Переводим данные на русский
    name_translated = translate_text(name, "ru")
    body_part_translated = translate_text(body_part, "ru")
    equipment_translated = translate_text(equipment, "ru")
    target_translated = translate_text(target, "ru")
    secondary_muscles_translated = translate_text(secondary_muscles, "ru")
    instructions_translated = "\n".join(
        [
            translate_text(instruction, "ru")
            for instruction in random_exercise.get("instructions", ["Нет инструкций"])
        ]
    )

    await message.answer(
        f"Рандомное упражнение: {name_translated}\n"
        f"Часть тела: {body_part_translated}\n"
        f"Целевая мышца: {target_translated}\n"
        f"Оборудование: {equipment_translated}\n"
        f"Второстепенные мышцы: {secondary_muscles_translated}\n"
        f"Инструкции:\n{instructions_translated}\n"
        f"GIF: {random_exercise.get('gifUrl', 'Нет изображения')}"
    )


@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Заполните профиль.")
        return

    if (
        users[user_id].get("water_norms") is None
        or users[user_id].get("calorie_norms") is None
    ):
        await get_daily_norms(message)

    calorie_norms = users[user_id].get("calorie_norms", 0)
    if int(users[user_id].get("calories_goal", 0)) != 0:
        calorie_norms = int(users[user_id].get("calories_goal"))

    consumed_water = users[user_id].get("water", 0)
    consumed_food = users[user_id].get("food", 0)

    remaining_water = int(users[user_id]["water_norms"] - consumed_water)
    remaining_calories = int(calorie_norms - consumed_food)
    burned_calories = users[user_id].get("burned_calories", 0)

    await message.answer(
        f"Выпито воды: {consumed_water} мл из {users[user_id]['water_norms']} мл\n"
        f"Осталось выпить воды: {remaining_water} мл\n"
        f"Потреблено калорий: {consumed_food} ккал из {calorie_norms} ккал\n"
        f"Сожжено калорий: {burned_calories} ккал\n"
        f"Осталось набрать калорий: {remaining_calories} ккал"
    )


def setup_handlers(dp):
    dp.include_router(router)
