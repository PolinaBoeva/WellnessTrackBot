from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    age = State()
    weight = State()
    height = State()
    activity_coefficient = State()
    city = State()
    calories_goal = State()
    sex = State()

class LogState(StatesGroup):
    water_amount = State()
    food_name = State()
    food_weight = State()
    workout_type = State()
    workout_time = State()