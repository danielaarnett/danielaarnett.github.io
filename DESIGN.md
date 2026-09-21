# Главная: «Авторский архив»

Первый макет общего направления сайта Daniel A. Arnett. Светлая книжная бумага, чернильно-зелёные поверхности, медные акценты, оригинальная гравюра с вороном и монограмма A. Шрифты Viaoda Libre, Source Serif 4 и Source Sans 3 продолжают существующий стиль чтения.

## Что можно посмотреть

- `index.html` — новая главная: знакомство с книгами, мастерская, будущая библиотека готовой прозы, блок автора и навигационный подвал.
- `index-previous.html` — сохранённая предыдущая главная для сравнения.
- Фильтры жанров, окна аннотаций, раскрытие частей рукописи и мобильное меню работают без сборки и сторонних JS-библиотек.
- `reading.css`, `reading.html`, `plans.html` и общие стили прежних страниц не менялись.

Открыть `index.html` в браузере либо запустить локальный сервер из корня проекта: `python -m http.server 4173 --bind 127.0.0.1`, затем перейти на http://127.0.0.1:4173/.

## Содержимое и границы макета

Названия, обложки, аннотации и значения прогресса перенесены из существующего проекта. Короткие тексты главной и слоган предложены для этого макета. Фрагментов прозы в проекте нет: окна показывают аннотации и явно сообщают о подготовке отрывков. Готовые произведения не подменены черновиками.

Подписка Boosty не подключена. Нет имитации входа, оплаты или проверки подписки. Раздел готовой прозы показывает будущую структуру и текущее состояние «Раздел готовится». Для следующего этапа нужны страница автора на Boosty, согласованные условия доступа, тексты для публикации и выбранный способ проверки подписки. Закрытые тексты нельзя помещать в общедоступный статический репозиторий; доступ к ним должен проверяться на сервере.

## Референсы

- https://sethring.com/ — иллюстрация как вход в мир автора.
- https://wanderinginn.com/ — разные пути для нового читателя и подписчика.
- https://rickriordan.com/ — выразительные шапка и подвал с повторной навигацией.

Иллюстрация и оформление созданы для этого проекта, материалы референсов не копировались.

## Иллюстрация

`images/archive-raven.png` создана встроенным Imagegen, без CLI/API. Оригинал сохранён отдельно инструментом генерации; рабочая копия находится в репозитории.

Промпт:

Use case: illustration-story. Asset type: original wide hero background for the literary website of dark fantasy and psychological prose author Daniel A. Arnett. Create a sophisticated atmospheric antique copperplate etching / charcoal illustration of a large black raven perched on a bare twisted branch in the RIGHT foreground, beyond it a haunting old northern European town with steep roofs, a distant narrow clock tower, industrial chimneys disappearing into mist. Wide landscape 3:2 composition. The LEFT 40 percent is quiet near-black charcoal fog with only faint silhouettes so cream website typography can overlay it. Most visible detailed art is on the RIGHT two thirds. Restrained palette, soot black, warm smoke gray, faded parchment highlights, very subtle weathered copper. Fine hatching and natural paper grain, strong raven silhouette with beautiful feather detail, subtle layered depth, editorial book frontispiece quality, not a video game illustration, not glossy 3D, no bright colors. Low key twilight but midtones on the right must remain legible. No text, no lettering, no logo, no borders, no UI. Original imaginary town, contemplative mysterious mood.
