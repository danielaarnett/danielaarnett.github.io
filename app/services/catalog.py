"""Author-approved public titles; placeholders never contain unpublished prose."""
from .access import SHELVES

TITLES = {
    'novellas': ['Купол смерти', 'Мелки', 'Мать', 'Рядом', '731', 'Бетонная коробка', 'Могильщики', 'Заяц', 'Искупление', 'Кипящая вода', 'Кто мы?', 'Оно', 'Он и Она', 'Отец', 'Как умирают мотыльки?', 'По нотам', 'Ночь ремней', 'Поговорить не хочешь?', 'Шепчущий', 'Тук-тук', 'Там, внутри', 'Шесть футов вниз', 'Стою у двери и стучу', 'Горячее солнце', 'Неправильно', 'Стекло', 'Восемь писем', 'Золотой билет', 'Маскарад'],
    'short_novels': ['Раскармливание', 'Орден на сдачу', 'Потухшее солнце', 'Дождливый вторник', 'Смятые холсты', 'Тлеющий'],
    'novels': ['Дети Крампуса - тени Йоля', 'Моя слабость, моя боль', 'Люциан', 'Нил и Харден: доставка до востребования', 'Вчера здесь был завтрак'],
    'scripts': ['Опенинг Sanitarium', 'Опенинг Knights and Merchants', 'Опенинг The Final Station', 'Новеллизация Gremlins Inc.: Проект Автоматон', 'Новеллизация Ardmage Cradle of the Ard'],
    'unfinished': ['История одного города', 'Метро 2033: Римские свечи', 'Степень свободы', 'В архиве', 'Outlands', 'Сиблинги', 'Фан-проза по мультсериалу Аватар - Легенда об Аанге', 'Санктум'],
    'poetry': ['Петля', 'Где ты, там я', 'Стой!', 'Чувствуешь', 'Девственница', 'Рейкьявик', 'Считаешь до трёх', 'Ты никогда не видела слёз', 'Когда-нибудь', 'Моя краска', 'Давай мы не будем друзьями'],
    'songs': ['Дождь, дождь', 'Стань моим солнцем', 'Изувечь меня', 'Я скучаю по тебе', 'У меня есть мечта', 'Это моя зима', 'Под кронами деревьев', 'Тяжело', 'Лгунья', 'Война', 'Белое платье', 'Ты можешь спасти меня'],
}


def build_shelves(available):
    published = {book['title']: book for books in available.values() for book in books}
    listed = {title for titles in TITLES.values() for title in titles}
    listed.add('Дети Крампуса: Тени Йоля')
    shelves = []
    for key, label in SHELVES.items():
        books = []
        for title in TITLES[key]:
            if title == 'Моя слабость, моя боль' and title in published:
                books.append(published[title])
            else:
                books.append(dict(title=title, cover='', href='#forthcoming-dialog', subtitle='', placeholder=True))
        books.extend(book for book in available.get(key, []) if book['title'] not in listed)
        shelves.append(dict(key=key, title=label, books=books))
    return shelves
