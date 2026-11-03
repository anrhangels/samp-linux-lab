[← Документация](README.md) · [Быстрый старт](quickstart.md) · [Словарь](glossary.md)

# Где скачивать игру и компоненты

Ссылки ведут на страницы разработчиков и официальные каталоги. Оттуда выбирайте актуальную загрузку: прямые адреса установщиков могут меняться. Страница Arizona требует JavaScript; скачивание откройте в обычном браузере.

## Игровые проекты

| Проект | Где скачивать | Статус в лаборатории |
| :--- | :--- | :--- |
| Arizona RP | [Официальный сайт и Windows-лаунчер](https://arizona-rp.com/) | Запущен; [инструкция](arizona.md) |
| Advance RP | [Официальный сайт, раздел начала игры](https://adv-rp.com/) | Инструкции изучены; запуск не проверен |
| Radmir RP / CRMP | [Официальный сайт](https://radmir.online/) | Запуск не проверен |

Для Arizona использован официальный Windows-лаунчер. Запись проекта в этой таблице сама по себе не означает, что мы скачивали и запускали его клиент. История браузерных скачиваний не восстановлена; здесь указаны официальные источники компонентов, упомянутых в работе.

## Компоненты Linux

| Компонент | Зачем нужен | Официальный источник |
| :--- | :--- | :--- |
| Flatpak / Flathub | Установка Faugus | [Настройка Flatpak](https://flatpak.org/setup/) · [Faugus на Flathub](https://flathub.org/apps/io.github.Faugus.faugus-launcher) |
| Faugus | Управление игрой, префиксом и Proton | [Исходный код и инструкция](https://github.com/Faugus/faugus-launcher) |
| GE-Proton | Запуск Windows-клиента | [Проект](https://github.com/GloriousEggroll/proton-ge-custom) · [Релизы](https://github.com/GloriousEggroll/proton-ge-custom/releases) |
| umu | Окружение Proton вне Steam | [Основной проект](https://github.com/Open-Wine-Components/umu-launcher) · [Сборки Faugus](https://github.com/Faugus/umu-launcher/releases) |
| MangoHud | FPS, время кадра, нагрузка | [Проект и параметры](https://github.com/flightlessmango/MangoHud) |
| DXVK | Перевод Direct3D в Vulkan | [Проект и документация](https://github.com/doitsujin/dxvk) |
| Hyprland / Xwayland | Масштабирование старых приложений | [Документация Xwayland](https://wiki.hypr.land/configuring/extra/xwayland/) |

DXVK входит в Proton: отдельная ручная подмена DLL для описанного запуска не требуется. MangoHud необязателен для игры. Библиотеки и шрифты не скачиваются нашим скриптом и не включены в репозиторий.
