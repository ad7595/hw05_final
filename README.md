# Yatube

Это социальная сеть, предназначенная для блогеров и любителей контента. Здесь пользователи могут публиковать свои посты, подписываться на интересные группы, комментировать записи других пользователей, а также подписываться на блогеров, чьи посты им особенно интересны. Кроме того, платформа предоставляет возможность добавлять и удалять записи в своем профиле и в группах.

# Технологии:
- Pyhton 
- Django 

# Как развернуть проект локально:
Клонируйте проект из репозитория:

```
git clone https://github.com/ad7595/hw05_final.git
```

Создайте и активируйте виртуальное окружение:
```
python -m venv venv
source venv/scripts/activate
```

Установите зависимости:
```
pip install -r requirements.txt
```

Создайте и примините миграции:
```
python manage.py makemigrations
python manage.py migrate
```
В папке с файлом manage.py выполните команду:
```
python manage.py runserver
```
Создайте superuser'a:
```
python manage.py createsuperuser
```
Проект доступен локально!
