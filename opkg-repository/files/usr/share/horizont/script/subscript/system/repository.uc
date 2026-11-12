#!/usr/bin/ucode
// Репозитории пакетов (opkg feeds) — схема /system/repository (пакет opkg-repository).
// Записи — строки «src/gz <имя> <адрес>» и «src <имя> <адрес>» файлов /etc/opkg/*.conf
// (distfeeds.conf — фиды прошивки, customfeeds.conf — свои); закомментированная строка —
// выключенный репозиторий. Ключ записи — имя (оно же имя списка пакетов в lists_dir opkg).
// Добавление — в customfeeds.conf (с update — затем opkg update в фоне); изменение и удаление —
// правкой строки в её файле (атомарно: временный файл и rename). Действие update — opkg update,
// вывод потоком (wait). Контракт — как у прод-скриптов horizont (parse_values: _section,
// _option, _value, data).

import * as fs from 'fs';
import { parse_values, typify } from 'horizont.utils';

const DIR = '/etc/opkg';
const SCHEMA_PATH = '/system/repository';
const HORIZONT_PIPE = '/var/run/horizont.pipe';
const CUSTOM = DIR + '/customfeeds.conf';
const NAME = /^[A-Za-z0-9_.-]{1,64}$/;
const URL = /^(https?|ftp|file):\/\/[^\s'"]+$/;
// строка фида: «[# ]src[/gz] <имя> <адрес>»
const LINE = /^(\s*#\s*)?(src\/gz|src)\s+(\S+)\s+(\S+)\s*$/;

// каталог списков пакетов: lists_dir из /etc/opkg.conf
function lists_dir() {
	for (let l in split(fs.readfile('/etc/opkg.conf') ?? '', '\n')) {
		let m = match(l, /^\s*lists_dir\s+\S+\s+(\S+)/);
		if (m) return m[1];
	}
	return '/var/opkg-lists';
}

function conf_files() {
	return filter(sort(fs.glob(DIR + '/*.conf') ?? []), (f) => fs.stat(f)?.type == 'file');
}

// все фиды: {имя: {file, idx, disabled, compressed, url}} и строки файлов
function scan() {
	let feeds = {}, files = {};
	for (let f in conf_files()) {
		let lines = split(fs.readfile(f) ?? '', '\n');
		files[f] = lines;
		for (let i = 0; i < length(lines); i++) {
			let m = match(lines[i], LINE);
			// пример из штатного customfeeds.conf — не репозиторий
			if (!m || !match(m[3], NAME) || index(m[4], 'example.com') >= 0 || feeds[m[3]])
				continue;
			feeds[m[3]] = {file: f, idx: i, disabled: !!m[1], compressed: m[2] == 'src/gz', url: m[4]};
		}
	}
	return {feeds, files};
}

function line(f, name) {
	return sprintf('%s%s %s %s', f.disabled ? '# ' : '', f.compressed ? 'src/gz' : 'src', name, f.url);
}

function save(file, lines) {
	let tmp = file + '.new';
	if (!fs.writefile(tmp, join('\n', lines)))
		return false;
	return fs.rename(tmp, file);
}

function record(name, f, dir) {
	let r = {name, disabled: f.disabled, url: f.url, compressed: f.compressed, file: replace(f.file, DIR + '/', '')};
	let list = `${dir}/${name}`;
	let st = fs.stat(list);
	if (st) {
		let n = 0;
		for (let l in split(fs.readfile(list) ?? '', '\n'))
			if (substr(l, 0, 9) == 'Package: ') n++;
		r.packages = n;
		let t = localtime(st.mtime);
		r.updated = sprintf('%04d-%02d-%02d %02d:%02d:%02d', t.year, t.mon, t.mday, t.hour, t.min, t.sec);
	}
	return r;
}

const bool = (v) => v === true || v == 1 || v == 'true';

const action = {
	_get: function() {
		let s = scan(), dir = lists_dir(), out = {};
		for (let name, f in s.feeds)
			out[name] = record(name, f, dir);
		return out;
	},

	_add: function() {
		let data = parse_values().data;
		let name = '' + (data.name ?? ''), url = '' + (data.url ?? '');
		if (!match(name, NAME))
			return {'error': 'invalid repository name'};
		if (!match(url, URL))
			return {'error': 'invalid repository url'};
		let s = scan();
		if (s.feeds[name])
			return {'error': name + ' already exists'};

		let f = {disabled: false, compressed: data.compressed == null ? true : bool(data.compressed), url};
		let lines = s.files[CUSTOM] ?? [];
		// последний перевод строки файла — пустой элемент: новая строка — перед ним
		if (length(lines) && lines[-1] == '')
			splice(lines, length(lines) - 1, 0, line(f, name));
		else
			push(lines, line(f, name), '');
		if (!save(CUSTOM, lines))
			return {'error': 'cannot write ' + CUSTOM};

		// списки пакетов — в фоне: ответ добавления не ждёт загрузку (вывод — в журнал); после —
		// reload схемы в канал horizont (он держит данные в кэше: иначе «пакеты» и «обновлён»
		// так и остались бы пустыми до перезапуска)
		if (bool(data.update))
			system(`(opkg update 2>&1 | logger -t opkg-repository; ` +
				`[ -p ${HORIZONT_PIPE} ] && echo "reload:${SCHEMA_PATH}" > ${HORIZONT_PIPE}) >/dev/null 2>&1 &`);

		let out = {};
		f.file = CUSTOM;
		out[name] = record(name, f, lists_dir());
		return out;
	},

	_set: function() {
		let data = parse_values();
		let s = scan();
		let f = s.feeds[data._section];
		if (!f)
			return {'error': 'repository not found'};
		let v = typify(data._value);
		if (data._option == 'url') {
			if (!match('' + v, URL))
				return {'error': 'invalid repository url'};
			f.url = '' + v;
		} else if (data._option == 'disabled')
			f.disabled = bool(v);
		else if (data._option == 'compressed')
			f.compressed = bool(v);
		else
			return {'error': 'read-only option'};

		let lines = s.files[f.file];
		lines[f.idx] = line(f, data._section);
		if (!save(f.file, lines))
			return {'error': 'cannot write ' + f.file};
	},

	_delete: function() {
		let data = parse_values();
		let s = scan();
		let f = s.feeds[data._section];
		if (!f)
			return {'error': 'repository not found'};
		let lines = s.files[f.file];
		splice(lines, f.idx, 1);
		if (!save(f.file, lines))
			return {'error': 'cannot write ' + f.file};
		// скачанный список удалённого репозитория больше не нужен
		fs.unlink(`${lists_dir()}/${data._section}`);
		fs.unlink(`${lists_dir()}/${data._section}.sig`);
	},

	// изменения уже в файлах; opkg прочтёт их при следующем update
	_apply: function() {
	},

	// opkg update — вывод потоком (действие с wait)
	_update: function() {
		system('opkg update 2>&1');
	},
};

if (!length(ARGV))
	printf("%J\n", {'error': 'action not given'});
else {
	let cmd = '_' + shift(ARGV);
	if (!exists(action, cmd))
		printf("%J\n", {'error': 'unknown action'});
	else {
		let x = action[cmd]();
		if (x)
			printf("%J\n", x);
	}
}
