# Telegram-бот записи для мастера маникюра (aiogram + SQLite)

## Возможности
- Запись через inline-календарь на текущий и следующий месяц.
- Выбор только свободного слота.
- Ограничение: у пользователя только одна активная запись.
- Сбор имени и телефона перед подтверждением.
- Уведомления администратору и в канал расписания.
- Отмена записи пользователем (слот снова становится доступным).
- Админ-панель:
  - добавление рабочего дня;
  - добавление/удаление временных слотов;
  - закрытие дня полностью;
  - просмотр расписания на дату;
  - отмена записи клиента.
- Кнопки "Прайсы" и "Портфолио" в главном меню.
- Напоминание за 24 часа через APScheduler + восстановление задач после перезапуска.

## Переменные окружения
Создайте `.env`:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=123456789
SCHEDULE_CHANNEL_ID=-1001234567890
DATABASE_PATH=manicure_bot.db
```

## Запуск
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Структура проекта
```text
manik/
├── bot.py
├── config.py
├── requirements.txt
├── README.md
├── database/
│   └── db.py
├── handlers/
│   ├── __init__.py
│   ├── admin.py
│   └── user.py
├── keyboards/
│   └── inline.py
└── utils/
    ├── middlewares.py
    ├── reminders.py
    └── states.py
```
