# -*- coding: utf-8 -*-
"""Текст из PDF чистым Python. Решение D-009: ноль зависимостей.

ЗАЧЕМ. Технические характеристики элементов питания Energizer публикует только
в даташитах-PDF. Без чтения PDF у сайта остались бы размеры и напряжение и не
было бы ни ёмкости, ни объёма, ни импеданса — то есть нечего было бы считать
сверх переписанного.

ТРИ УСТРОЙСТВА ТЕКСТА, И ВСЕ ТРИ ВСТРЕТИЛИСЬ В ОДНОЙ ВЫГРУЗКЕ:

  1. Обычные строковые литералы в скобках: «(Chemical System:) Tj».
  2. Шестнадцатеричные строки с идентификаторами глифов: «<0026><004B> TJ»,
     где 0x26 — не буква, а номер глифа в подмножестве шрифта. Такие файлы
     первая версия отдавала как пустые, и это были ровно серебряно-оксидные
     миниатюрные элементы — сердце ниши.
  3. Сканы без текстового слоя. Тут ничего не сделать, и притворяться нельзя.

ГЛИФЫ ДЕКОДИРУЮТСЯ ПО ТАБЛИЦЕ ИЗ САМОГО ФАЙЛА. В PDF лежит /ToUnicode с парами
«код → символ». Соблазнительная догадка «номер глифа = ASCII минус 29» на
проверенных файлах верна, но это догадка о ЧУЖОМ шрифте: другое подмножество —
и текст молча превратится в правдоподобный мусор. Берём объявленную таблицу.

И ПОСЛЕ ЭТОГО ТЕКСТ ПРОВЕРЯЕТСЯ. Декодирование, давшее что-то, ещё не значит,
что оно дало верное. `looks_english` требует найти в результате настоящие слова
даташита; не нашлось — считаем файл нечитаемым, а не выдаём догадку за данные.

ПОЧЕМУ ТЕКСТ СКЛЕИВАЕТСЯ БЕЗ ПРОБЕЛОВ. Даташиты свёрстаны с ручным кернингом:
«Classification» разложено на «C l as s i f i c ati o n» отдельными литералами
с позиционированием между ними. Восстанавливать пробелы бессмысленно — вместо
этого СНИМАЕМ ПРОБЕЛЫ ВОВСЕ и ищем по сплошной строке.
"""
import re
import zlib

# Строковый литерал PDF: скобки, внутри экранированные пары или обычные байты.
_STR = re.compile(rb"\((?:\\.|[^\\()])*\)", re.S)
_HEX = re.compile(rb"<([0-9A-Fa-f\s]{2,})>")
_ESC = re.compile(rb"\\([nrtbf()\\]|[0-7]{1,3})")
_SIMPLE = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"", b"f": b""}

_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_PAIR = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_TRIPLE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")

# Слова, которые обязаны найтись в настоящем даташите. Проверка декодирования
# известными ответами: без неё «получилось» и «получилось верно» неразличимы.
_MARKERS = ("Voltage", "Capacity", "Designation", "Chemical", "Weight",
            "Volume", "Energizer", "Battery", "Dimensions", "Nominal",
            "Typical", "System", "Impedance", "Temperature")
_MIN_MARKERS = 2


def _unescape(b):
    def one(m):
        g = m.group(1)
        if g in _SIMPLE:
            return _SIMPLE[g]
        if g in (b"(", b")", b"\\"):
            return g
        return bytes([int(g, 8) & 0xFF])
    return _ESC.sub(one, b)


def _all_streams(raw):
    """Каждый поток файла: и сжатый, и лежащий как есть.

    Таблицы /ToUnicode у Energizer не сжаты, и первая версия их не видела,
    потому что перебирала только то, что разжимается.
    """
    out = []
    for m in re.finditer(rb"stream\r?\n", raw):
        start = m.end()
        end = raw.find(b"endstream", start)
        if end < 0:
            continue
        blob = raw[start:end]
        try:
            out.append(zlib.decompress(blob))
        except Exception:
            out.append(blob)
    return out


def cmap(raw):
    """Соответствие «код глифа → символ», объявленное в самом файле.

    Карт может быть несколько — по одной на шрифт. Если две карты сопоставляют
    одному коду РАЗНЫЕ символы, код выбрасывается: молча выбрать одну из двух
    значит выдумать текст.
    """
    table, conflict = {}, set()

    def put(code, ch):
        if code in conflict:
            return
        if code in table and table[code] != ch:
            conflict.add(code)
            table.pop(code, None)
            return
        table[code] = ch

    for s in _all_streams(raw):
        if b"beginbfchar" not in s and b"beginbfrange" not in s:
            continue
        for body in _BFCHAR.findall(s):
            for src, dst in _PAIR.findall(body):
                try:
                    put(int(src, 16), chr(int(dst[:4], 16)))
                except ValueError:
                    continue
        for body in _BFRANGE.findall(s):
            for lo, hi, dst in _TRIPLE.findall(body):
                try:
                    a, b, d = int(lo, 16), int(hi, 16), int(dst[:4], 16)
                except ValueError:
                    continue
                if b - a > 4096:
                    continue
                for k in range(a, b + 1):
                    put(k, chr(d + k - a))
    return table


def content_streams(raw):
    """Только ПОТОКИ СОДЕРЖИМОГО страницы.

    Разжимается многое: встроенные шрифты, цветовые профили, электронная
    подпись. В шрифте TrueType тоже есть строковые литералы — имена таблиц
    вроде post и prep, — и первая версия честно вытащила их как «текст
    даташита», выдав на a76.pdf семьдесят килобайт двоичного мусора.

    Признаков три, и двух не хватило. Поток обязан содержать блок текста BT,
    оператор показа Tj или TJ, выбор шрифта Tf — И БЫТЬ ПЕЧАТНЫМ. Последнее
    решает: программа шрифта — это произвольные байты, среди которых «BT» и
    «Tj» встречаются случайно, и на 319z.pdf такой поток дал тридцать две
    тысячи знаков правдоподобного мусора, прошедшего проверку на английский.
    Настоящий поток содержимого — это операторы, то есть почти сплошной ASCII.
    """
    out = []
    for s in _all_streams(raw):
        if b"BT" not in s or b"Tf" not in s:
            continue
        if b"Tj" not in s and b"TJ" not in s:
            continue
        head = s[:4000]
        printable = sum(1 for b in head if 32 <= b < 127 or b in (9, 10, 13))
        if head and printable / len(head) >= 0.85:
            out.append(s)
    return out


def _decode_hex(body, table):
    """Шестнадцатеричная строка -> текст по таблице. Коды по два байта: так их
    записывает Identity-H, и так объявлен codespacerange у этих файлов."""
    h = re.sub(rb"\s+", b"", body)
    if len(h) % 4:
        return ""
    out = []
    for i in range(0, len(h), 4):
        try:
            code = int(h[i:i + 4], 16)
        except ValueError:
            return ""
        ch = table.get(code)
        if ch is None:
            return ""
        out.append(ch)
    return "".join(out)


def looks_english(s):
    """Похоже ли извлечённое на настоящий даташит. Известные ответы вместо
    доверия к тому, что «что-то получилось»."""
    flat = re.sub(r"\s+", "", s)
    return sum(1 for w in _MARKERS if w in flat) >= _MIN_MARKERS


def text(raw):
    """Весь текст даташита одной строкой. Пустая строка означает «прочитать не
    удалось» — и это ЧЕСТНЫЙ ответ, а не отсутствие данных у производителя."""
    table = cmap(raw)
    parts = []
    for s in content_streams(raw):
        for m in _STR.finditer(s):
            parts.append(_unescape(m.group(0)[1:-1]).decode("latin-1"))
        if table:
            for m in _HEX.finditer(s):
                parts.append(_decode_hex(m.group(1), table))
    out = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return out if looks_english(out) else ""


def compact(raw):
    """Тот же текст БЕЗ пробелов — рабочая форма для поиска полей.

    Пробелы в даташите расставлены кернингом, а не смыслом: искать по ним
    значит искать по случайности вёрстки.

    Заодно вычищается «x-none» — маркер «язык не проверять», который Word
    оставляет в текстовом слое. Он стоит РОВНО МЕЖДУ подписью и значением
    («TypicalCapacity:x-none540mAh») и в первой версии съел ёмкость у двухсот
    даташитов из четырёхсот: подпись находилась, число — нет.
    """
    return re.sub(r"\s+", "", text(raw)).replace("x-none", "")


def number(s):
    """Число из куска даташита. Возвращает None, а не ноль: «нет данных» и
    «ноль» — разные ответы, и путать их нельзя."""
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    return float(m.group(0)) if m else None
