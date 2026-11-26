# ipk farm

Сборка пакетов фида `halo`/`donyx` и публикация opkg-репозитория. Живёт в этом
репозитории рядом с фидами; когда заматереет — переедет в свой git.

## Модель

- **flavor** — бренд: `irz` (irzOS, фид `/opkg/halo`) и `donyx` (dnxOS, `/opkg/donyx`).
  Это параметр сборки `DONYX=1` и набор пакетов, **не ветка**.
- **platform** — arch/SDK: `r2` (mipsel), `r50` (arm), `irm` (aarch64), `wrs`/`x86` —
  `planned`, в сборке не участвуют.
- Пакеты фида — `all`, поэтому сборка идёт **один раз на flavor**, на SDK его
  основной платформы (`sdk_platform`). Платформа нужна для arch-гейта,
  arch-extras и opkg-конфига.
- Источник упаковки один — этот репозиторий (`wrtnavsegda/master`). Репозитории
  пакетов (`donyx/split`, `horizon-uc`, `aurora`) тянет SDK при сборке;
  `farm pull` их не трогает.
- Buildbot — только `DEVELOP`. Номер сборки (и пути к `ipk/`) меняются каждую
  ночь, поэтому opkg-конфиг всегда привязан к номеру.

## Команды

```sh
python3 farm/main.py status                 # платформы, последние сборки/публикации
python3 farm/main.py pull                   # git fetch + ff-only для упаковки
python3 farm/main.py config --flavor irz --platform r50 --variant dist
python3 farm/main.py config --flavor irz --platform r50 --variant custom --out /tmp/customfeeds.conf
python3 farm/main.py build --flavor irz --dry-run          # показать команды
python3 farm/main.py build --flavor irz                    # собрать и записать манифест
python3 farm/main.py build --flavor irz --only halo-mod-software
python3 farm/main.py build --flavor donyx --publish        # собрать и опубликовать
python3 farm/main.py publish --build 12
python3 farm/main.py logs --build 12
```

`--platform` по умолчанию — `sdk_platform` flavor'а. `--release` задаёт номер
выпуска (`HALO_RELEASE`), иначе UTC `ГГММДДччмм`. `--allow-dirty` разрешает
собирать из грязной рабочей копии (в манифест всё равно попадёт HEAD).

## Что делает build

1. `preflight`: SDK на месте, `scripts/feeds` есть, рабочая копия чистая.
2. Пишет `feeds.conf` в SDK из `farm/feeds/<platform>.conf`
   (`@REPO@`, `@IRZ_LOCAL@` + `src-link halo`). Руками не правится.
3. Фиксирует `HEAD`, `HALO_PINNED`/`HALO_BRANCH`, номер сборки buildbot.
4. `feeds update/install`, затем `make package/feeds/halo/<dir>/{clean,compile} V=s`
   по списку `scripts/feed-packages*` (или `--only`).
5. Собирает ipk, читает control, проверяет гейты: arch (`all` / платформа),
   дубликаты имён.
6. Пишет артефакты в `~/.local/state/ipk-farm/builds/<id>/`:
   `manifest.json`, `ipk/`, `logs/`, `build.log`; состояние — `state.db`.

## Публикация

- merge с текущим фидом: новый пакет заменяет свою прошлую версию, остальные
  не трогаются;
- версии обязаны расти (сравнение в духе opkg), иначе публикация отклоняется;
- индекс пересобирается `ipkg-make-index.sh` по содержимому каталога, затем
  `usign -S` и проверка `usign -V`;
- `Packages`, `Packages.gz`, `Packages.sig` подменяются атомарно;
- запись в `publishes`, сборка помечается опубликованной.

Ключ и подпись — только на ферме (`sign_key` в `farm.toml`), в UI/логи не попадают.

## Веб-интерфейс

```sh
python3 farm/main.py serve --host 127.0.0.1 --port 8099
# на ферме, чтобы открыть с рабочей машины:
python3 farm/main.py serve --host 0.0.0.0 --port 8099
```

Один экран: платформы, флейворы, пакеты опубликованного фида со статусом
относительно последней сборки, апстрим (коммиты после опубликованной сборки),
конфиг opkg с табами dist/custom, история сборок и лог в диалоге.

Действия: `git pull` (только упаковка), `Собрать`, `Собрать и опубликовать`,
`Опубликовать сборку`. Долгие операции запускаются фоновым процессом, лог
обновляется каждые 2 с. Сборка и публикация защищены `flock` на flavor/фид.

Сервер без авторизации — рассчитан на локальную сеть; наружу выставлять
через nginx с basic-auth.

## Где что лежит

```
farm/
  farm.toml        конфиг: flavors, platforms, пути
  feeds/*.conf     шаблоны feeds.conf по платформам
  config.py        загрузка/валидация конфига
  buildbot.py      манифест buildbot, последняя сборка
  opkgcfg.py       distfeeds.conf / customfeeds.conf
  build.py         сборка, манифест, гейты
  publish.py       публикация, индекс, подпись
  ipk.py           разбор ipk, сравнение версий
  state.py         SQLite: сборки, пакеты, публикации, pull
  cli.py           команды
  web.py           HTTP API + статика
  static/          index.html, app.js, style.css
  tests/           unit-тесты (stdlib unittest)
```

## Проверки

```sh
python3 -m unittest farm.tests.test_farm -v
```

## Пока не сделано

- добавление/редактирование платформы из UI (макет — `docs/farm-ui-concept.html`);
- проверка зависимостей через `opkg simulate` в чистом rootfs;
- точечная сборка из UI (в CLI уже есть `--only`);
- авто-опрос buildbot по таймеру, systemd-юнит для `serve`.
