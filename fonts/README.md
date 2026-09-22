# Шрифты главной страницы

На главной используются две семьи из Google Fonts, размещённые локально:

- **Literata** — заголовки и литературные абзацы; normal/italic, вес 400–650, переменная оптическая ось 7–72.
- **Golos Text** — навигация, кнопки, подписи и небольшие тексты; normal, вес 400–700.

Файлы WOFF2 получены из официального CSS Google Fonts 22 сентября 2026 года. Двоичные файлы не изменены; имена сделаны понятными. Для каждой семьи сохранены отдельные подмножества cyrillic, cyrillic-ext, latin и latin-ext. Браузер загружает нужное подмножество по unicode-range из `css/fonts.css`.

CSS-источник: https://fonts.googleapis.com/css2?family=Golos+Text:wght@400..700&family=Literata:ital,opsz,wght@0,7..72,400..650;1,7..72,400..650&display=swap

Официальные исходники и сведения:

- https://github.com/googlefonts/literata
- https://github.com/google/fonts/tree/main/ofl/literata
- https://github.com/google/fonts/tree/main/ofl/golostext

Обе семьи распространяются по SIL Open Font License 1.1. Полные лицензии и сведения об авторах находятся рядом: `Literata-OFL.txt` и `Golos-Text-OFL.txt`.

Главная не обращается к серверам Google при открытии. Кириллические прямые начертания предварительно загружаются в `index.html`. На прочих страницах сохранено прежнее оформление.
