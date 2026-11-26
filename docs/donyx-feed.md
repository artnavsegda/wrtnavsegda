# Donyx-фид Halo (dnxOS)

Donyx — это **flavor**, а не ветка: тот же репозиторий `wrtnavsegda`, тот же код,
бренд включается `DONYX=1`, набор пакетов — `scripts/feed-packages-donyx`,
публикация — в `/var/www/html/opkg/donyx`.

Сборка и публикация — через ферму:

```sh
python3 farm/main.py build --flavor donyx
```

Ферма сама пишет `feeds.conf` в SDK (без отдельных клонов), собирает
`halo`/`halo-preview` (оба варианта), модули и `halo-metrics`, публикует подписанный
индекс и мержит его с текущим фидом. Публикация обязательна после сборки.

Платформа для сборки — та, что выбрана в интерфейсе (для Donyx iRM — `irm`,
SDK `~/sdk24`); arch-extras для Donyx не добавляются: `lighttpd-mod-proxy`
на iRM должен быть из прошивки (aarch64).

## Что важно

- Аврору в donyx-фид не кладём: на iRM должна остаться штатная. Иначе
  `opkg upgrade` предложил бы заменить её локальной Vue 3-сборкой.
- `halo` и `halo-preview` собираются из общего рантайма (Svelte/@halo/ui) того
  коммита donyx, что указан в `halo.mk`.

## Старое

`scripts/build-feed-donyx` и отдельный клон `~/Coding/wrtnavsegda-donyx`
больше не нужны: ветка `donyx` слита в `master`, а сборка и публикация делаются
фермой. Скрипт оставлен как запасной путь на случай, если ферма недоступна.
