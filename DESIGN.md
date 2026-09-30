# Главная: «Авторский архив»

Главная Daniel A. Arnett сочетает светлую книжную бумагу, тёплые тёмные поверхности и медные акценты. Две основные гарнитуры — Literata и Golos Text, локальные WOFF2 с кириллицей. Статическая версия: `index.html`; серверная: `app/templates/home.html`. Поведение синхронизировано в `js/home.js` и `app/static/home.js`.

## Композиция от 30 сентября 2026

- Шапка: логотип `images/logo.png` с сохранением пропорций, навигация «Читать», «Книги», «В работе», «Аудиокниги», «Читательский круг». Для аудиокниг пока информационная заглушка.
- После первого экрана — «Читать»: три обновления с авторскими текстами, наклонённые тонкие рамки с `art1.png`, `art2.png` и пустая третья рамка. Две кривые SVG соединяют иллюстрации. Тёмный тёплый фон постепенно переходит от цвета шапки. На телефоне каждая иллюстрация идёт над текстом.
- Карусель и прежнее приветствие автора удалены из главной, их стили и обработчики убраны. Остальные арты сохранены в репозитории.
- «Книги»: три рамки с `book_1.png`, `book_2.png`, `book_3.png`; категории «Бесплатно», «Свидетель», «Ценитель». Кнопки ведут к доступному чтению и описанию соответствующего уровня подписки.
- «Прежде чем стать книгой»: книги закрыты по умолчанию. Раскрывается только одна, плюс превращается в минус, высота раскрывается плавно. `progress.png` подстраивается под высоту раздела и слегка увеличивается, оставаясь позади текста. Без JavaScript работает нативная группа details. Настройка уменьшенного движения отключает анимации.
- Числа рукописей сохранены. Менять `data-written-words` и `data-target-words` у частей в обеих версиях главной; JS пересчитывает проценты и дуги. Общий плановый объём хранится в данных и не выводится читателю.
- «Читательский круг»: три уровня, без иллюстрации кабинета. Красные маркеры — «Бесплатно», синие — «Свидетель» (150 руб./мес.), жёлтые — «Ценитель» (350 руб./мес.). Платные кнопки пока открывают информационные заглушки; Boosty не подключён.
- «Бумажные издания»: авторское описание и заглушка предзаказа.
- Подвал: по центру «КОНЕЦ СТРАНИЦЫ — НЕ КОНЕЦ ИСТОРИИ», нижняя разделительная линия во всю ширину. Нижние подписи сохранены.
- Старые изображения стрелок удалены из кнопок и ссылок, в том числе на страницах чтения. Отдельная квадратная кнопка с векторным шевроном появляется справа внизу после прокрутки. Полоса прокрутки прямоугольная, без боковых зазоров.

## Содержимое и границы

Пролог «Моя слабость, моя боль» опубликован по адресу `/read/moya-slabost-moya-bol/prolog/`; его текст и форматирование не менялись. В блоке обновлений работает только эта кнопка чтения; остальные две открывают заглушки. Авторские описания будущего доступа сохранены, ограничения подписки на статической странице пока не вводятся.

Серверное ядро хранит главы и проверяет доступ до загрузки прозы; реальные платежи и Boosty не подключены. Приватная БД, ключи и закрытые рукописи не входят в Git. Запуск Flask описан в `README.md`; не раздавать корень проекта общим файловым сервером.

## Референсы

- https://sethring.com/ — иллюстрация как вход в мир автора.
- https://wanderinginn.com/ — разные пути для нового читателя и подписчика.
- https://rickriordan.com/ — выразительные шапка и подвал с повторной навигацией.

Иллюстрация и оформление созданы для этого проекта, материалы референсов не копировались.

## Иллюстрация

`images/archive-raven.png` создана встроенным Imagegen, без CLI/API. Оригинал сохранён отдельно инструментом генерации; рабочая копия находится в репозитории.

Промпт:

Use case: illustration-story. Asset type: original wide hero background for the literary website of dark fantasy and psychological prose author Daniel A. Arnett. Create a sophisticated atmospheric antique copperplate etching / charcoal illustration of a large black raven perched on a bare twisted branch in the RIGHT foreground, beyond it a haunting old northern European town with steep roofs, a distant narrow clock tower, industrial chimneys disappearing into mist. Wide landscape 3:2 composition. The LEFT 40 percent is quiet near-black charcoal fog with only faint silhouettes so cream website typography can overlay it. Most visible detailed art is on the RIGHT two thirds. Restrained palette, soot black, warm smoke gray, faded parchment highlights, very subtle weathered copper. Fine hatching and natural paper grain, strong raven silhouette with beautiful feather detail, subtle layered depth, editorial book frontispiece quality, not a video game illustration, not glossy 3D, no bright colors. Low key twilight but midtones on the right must remain legible. No text, no lettering, no logo, no borders, no UI. Original imaginary town, contemplative mysterious mood.

## Полигональная шапка

Главная использует `images/archive-raven-poly.png`: композиция с вороном и городом сохранена, графика переработана в полигональном стиле по образцу `images/progress.png`. Создано встроенным imagegen; точный промпт — `images/archive-raven-poly.prompt.md`. Предыдущая иллюстрация сохранена для истории.

Шапка дополнительно затемнена отдельным чёрным слоем с непрозрачностью 28%; арт не менялся. Линия над жанрами проходит на всю ширину окна. Авторские изменения навигации, кнопок и текста из `index.html` включены в публикацию и перенесены в серверную главную.
