# -*- coding: utf-8 -*-
"""Гейты BatteryCross. Читают СОБРАННЫЕ файлы, а не намерения генератора.

ПОЧЕМУ ИМЕННО ТАК. Гейты у нас уже дважды были зелёными на сломанном сайте:
один искал внешние адреса по «http» и пропустил src вообще без схемы; другой
сверял вывод с той самой функцией, которая его и считала. Поэтому каждый гейт
здесь получает СЛОВАРЬ ОТДАННЫХ ФАЙЛОВ и больше ничего, а `--selftest` ломает
сборку нарочно и требует, чтобы гейт покраснел.

ДВА ГЕЙТА ЕСТЬ ТОЛЬКО У ЭТОГО САЙТА, И ОБА ПРО ЦЕНУ ОШИБКИ:

  · ЧЕСТНОСТЬ МАСШТАБА. Силуэты рисуются в реальном масштабе, и весь смысл
    рисунка в том, что совпадение габаритов видно глазом. Рисунок, где два
    силуэта нарисованы в разных масштабах, лжёт, оставаясь при верных
    подписях, — ровно как неравные корзины гистограммы, нарисованные равной
    шириной, выдумали у нас заголовочное утверждение на 318 страницах;
  · ПОСАДКА И ЭЛЕКТРИКА НЕ СЛИВАЮТСЯ. Ни одна страница не имеет права сказать
    «подходит» одним словом. Элемент, который влезает в отсек, не всегда
    безопасная замена, и это единственное, ради чего сайт существует.
"""
import ast
import hashlib
import io
import json
import os
import re
import sys
from datetime import date as _date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cells as C  # noqa: E402
import draw  # noqa: E402
import prose as P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
STAMP_DIR = os.path.join(HERE, ".stamps")   # ВНЕ каталога выкладки

TITLE_MAX = 60
DESC_MIN, DESC_MAX = 50, 160
DOMAIN = "batterycross.com"

QUOTE = P.QUOTE

ALLOWED_PREFIX = ("data:image/svg+xml,", "mailto:", "#", "/")

# ЕДИНСТВЕННЫЕ хосты, на которые сайту разрешено СОСЛАТЬСЯ. Не загрузить —
# сослаться: по гипертекстовой ссылке браузер не идёт, пока по ней не нажали,
# и на нулевые сетевые запросы готовой страницы она не влияет. Список
# закрытый и содержит ровно то, откуда взяты числа: перечень изделий и
# даташиты того же производителя.
# Три адреса отказа добавлены не для удобства, а потому что обязательное
# раскрытие рекламной сети обязано вести к отказу ссылкой, а не строкой,
# которую читатель перепечатывает руками.
OUTBOUND_HOSTS = ("data.energizer.com", "adssettings.google.com",
                  "policies.google.com", "optout.aboutads.info")

# Слова, которыми нельзя обещать замену без оговорки. «Compatible» и
# «equivalent» сливают посадку с электрикой в одно слово, а весь сайт про то,
# что это разные вопросы.
FORBIDDEN = ("compatible", "equivalent to", "interchangeable with",
             "safe substitute for", "direct replacement")


def _html(files):
    return {p: t for p, t in files.items() if p.endswith(".html")}


def _embeds(files):
    """Встраиваемые виджеты. Это НЕ страницы сайта: у них нет шапки, подвала,
    навигации, поля поиска и рекламы, они живут в чужой странице, у них своя
    таблица стилей и canonical у них указывает на ту страницу, фрагментом
    которой они являются. Правила, написанные для страниц сайта, к ним не
    применимы, и потому область каждого такого правила объявлена ЯВНО — а не
    получилась случайно."""
    return {p: t for p, t in _html(files).items()
            if 'name="page-type" content="embed"' in t}


def _site_pages(files):
    """Страницы САЙТА — всё, кроме виджетов."""
    emb = _embeds(files)
    return {p: t for p, t in _html(files).items() if p not in emb}


def _cells(files):
    return {p: t for p, t in _html(files).items()
            if 'name="page-type" content="cell"' in t}


def _text(html):
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def _sample(bad, n, what):
    """Объявить ВЫБОРКУ гейта и уронить его, если она пуста.

    Гейт, осмотревший ноль страниц, печатает «пройден» и выглядит
    доказательством: у этого сайта так отчитывались два рекламных гейта
    над сборкой, где рекламы не было вовсе, — а всего таких гейтов
    оказалось двадцать пять из семидесяти. Пустая выборка кричит,
    слепая молчит.
    """
    if not n:
        bad.append("гейту нечего читать: %s — выборка пуста" % what)
    return n


# ------------------------------------------------------------------- гейты

def g_language(files):
    """Ни одной кириллической буквы ни в одном отданном файле. Русский текст
    однажды уехал у нас на 321 страницу мимо всех структурных проверок."""
    bad = []
    _sample(bad, len(files), "отданных файлов")
    for p, t in files.items():
        hits = re.findall(r"[Ѐ-ӿ]+", t)
        if hits:
            bad.append("%s: %s" % (p, ", ".join(hits[:3])))
    return bad


def g_no_double_escape(files):
    """Ни одной дважды экранированной сущности в отданном.

    «&amp;mdash;» печаталось словом в ячейке таблицы на четырёх страницах:
    заглушку прогнали через экранирование, которое и превращает «&» в
    «&amp;». Такая строка ВСЕГДА дефект: её никто не хочет видеть.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    for p, t in pages.items():
        for m in re.finditer(r"&amp;[a-zA-Z]+;|&amp;#\d+;", t):
            bad.append("%s: «%s»" % (p, m.group(0)))
    return bad[:8]


_SRC = {}
# Сам файл гейтов в этом списке тоже: управляющий байт уже въехал
# внутрь регулярки гейта и выключил её, оставив проверку зелёной.
SOURCE_FILES = ("design.py", "render.py", "prose.py", "cells.py",
                "depth.py", "draw.py", "gates.py")


def _sources():
    """Исходники генератора, прочитанные С ДИСКА.

    Управляющий байт въехал на сайт ЧЕРЕЗ исходник: в design.py вместо
    эскейпа CSS лежал байт 0x82, и гейт, читающий только выкладку, увидел бы
    его лишь там, куда он дотёк. Читаем и то, из чего собрано.
    """
    if not _SRC:
        for n in SOURCE_FILES:
            p = os.path.join(HERE, n)
            if os.path.isfile(p):
                _SRC[n] = io.open(p, encoding="utf-8").read()
    return _SRC


def g_control_chars(files):
    """Ни одного управляющего байта ни в отданном, ни в исходнике генератора.

    Проверялся ТОЛЬКО диапазон C0 (меньше 0x20). Диапазон C1 (0x80-0x9F) и
    DEL не проверялись вовсе, и U+0082 проехал в CSS всех 164 страниц:
    задуманный эскейп на U+2022 BULLET был прочитан как ВОСЬМЕРИЧНЫЙ, цифра
    осталась литералом, и подпись «ours» у вычисленных нами строк читалась
    на 115 страницах как «2 ours». Область действия гейта — часть гейта.
    """
    bad = []
    src = _sources()
    # ДВЕ половины выборки, и считаются они порознь: управляющий байт
    # въехал на сайт ЧЕРЕЗ исходник, а исходники лежат на диске всегда —
    # пока их считали вместе с выкладкой, пустая выкладка гейт не роняла.
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(src), "исходников генератора")
    # ВЫБОРКА ОБЪЯВЛЕНА ПОИМЁННО. _sources берёт файл, только если он
    # лежит на диске, и переименованный модуль просто переставал
    # осматриваться — не «выборка стала меньше», а осмотр перестал
    # существовать, и никто об этом не узнавал.
    for _n in SOURCE_FILES:
        if _n not in src:
            bad.append("исходник %s не прочитан: он выпал из осмотра "
                       "молча" % _n)
    scan = list(files.items())
    scan += [("исходник %s" % k, v) for k, v in src.items()]
    for p, t in scan:
        for i, ch in enumerate(t):
            o = ord(ch)
            if (o < 0x20 and ch not in "\n\t") or o == 0x7F \
                    or 0x80 <= o <= 0x9F:
                bad.append("%s: байт 0x%02X в позиции %d" % (p, o, i))
                break
    return bad


def g_no_external(files):
    """Ни одного постороннего ПОДРЕСУРСА и ни одной ссылки за пределы
    объявленного списка.

    Прежнее правило было «всё, за чем пойдёт браузер, — своё», и одним словом
    оно запрещало две РАЗНЫЕ вещи. Подресурс — картинка, стиль, шрифт, скрипт
    — браузер тянет САМ при открытии страницы: это сетевой запрос, гость в
    политике приватности и лишняя точка отказа. Гипертекстовая ссылка не
    тянет ничего, пока по ней не нажали.

    Сайт воспроизводит чужие числа на 174 страницах, объявляет источник
    фразой в подвале и не даёт проверить НИ ОДНУ цифру — ноль внешних адресов
    на весь корпус. Это нарушение PLAYBOOK §1 п.4 и §8, и держалось оно
    побочным следствием формулировки этого гейта.

    Поэтому правило разделено, и обе половины стали СТРОЖЕ, а не слабее:
      * подресурс — только свой, как и было, без исключений вовсе;
      * ссылка наружу — только на хост из ЯВНОГО списка ниже, только из тега
        <a>, только с rel="nofollow noopener" и только по https.
    Любой другой внешний адрес — по-прежнему провал.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    for p, t in pages.items():
        # Сперва подресурсы: src где угодно, href у <link>, и любой url() в
        # стилях. Ссылку из <a> сюда пускать нельзя, поэтому <a href> из
        # разбора вычитается ЯВНО, а не пропускается умолчанием.
        subres = re.findall(r'\bsrc="([^"]*)"', t)
        subres += re.findall(r'<link\b[^>]*\bhref="([^"]*)"', t)
        subres += re.findall(r"url\(([^)]*)\)", t)
        for r in subres:
            r = r.strip().strip("'" + QUOTE)
            if not r:
                bad.append("%s: пустой подресурс" % p)
            elif r.startswith(ALLOWED_PREFIX) or r.startswith(
                    "https://%s" % DOMAIN):
                continue
            else:
                bad.append("%s: подресурс наружу %s" % (p, r[:60]))
        for m in re.finditer(r"<a\b([^>]*)>", t):
            attrs = m.group(1)
            h = re.search(r'href="([^"]*)"', attrs)
            r = (h.group(1).strip() if h else "")
            if not r:
                bad.append("%s: пустая ссылка" % p)
                continue
            if r.startswith(ALLOWED_PREFIX) or r.startswith(
                    "https://%s" % DOMAIN):
                continue
            host = re.match(r"https://([^/]+)/", r)
            if not host or host.group(1) not in OUTBOUND_HOSTS:
                bad.append("%s: ссылка на неразрешённый хост %s" % (p, r[:60]))
                continue
            if 'rel="nofollow noopener"' not in attrs:
                bad.append("%s: внешняя ссылка без rel nofollow noopener: %s"
                           % (p, r[:60]))
    # ПОЧТА — В ОБЁРТКЕ, ВСЯ. Cloudflare по умолчанию переписывает адреса на
    # «[email protected]» и дописывает свой скрипт на каждую страницу; на
    # соседнем сайте это уже случилось. Обёртка стояла только в подвале:
    # лид страницы Contact и абзац Corrections на About оставались голыми,
    # хотя README утверждал обратное, а слова «email_off» не было ни в одном
    # из 93 гейтов.
    seen = 0
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r'<a href="mailto:[^"]*"[^>]*>.*?</a>', t):
            seen += 1
            if ("<!--email_off-->" not in t[max(0, m.start() - 20):m.start()]
                    or "<!--/email_off-->" not in t[m.end():m.end() + 20]):
                bad.append("%s: почтовая ссылка вне обёртки email_off — "
                           "площадка перепишет её на «[email protected]»: %s"
                           % (p, m.group(0)[:60]))
    if not seen:
        bad.append("почтовых ссылок ноль — пустая выборка это провал")
    _sample(bad, seen, "почтовых ссылок, осмотренных на обёртку")
    return bad


# ПРЕДЕЛ ВСТРОЕННОГО СКРИПТА. Он стережёт не байты, а РОЛЬ: скрипт этого
# сайта только переключает состояние, а сообщения и ссылки живут в разметке.
# Как только в него начинают складывать текст, он перестаёт помещаться — и
# упирается в этот предел раньше, чем в обзор.
#   Было 2048 при скрипте 2036 — то есть запаса не осталось вовсе, и первая
# же настоящая работа в поиске упёрлась бы в предел, который про другое.
# Поиск получил подбор габарита по допуску (это и есть обещание «линейки
# достаточно»), скрипт стал 2768 байт. Предел поднят до 3072 — запас есть,
# и он по-прежнему кусается: любая попытка сложить в скрипт разметку или
# подписи добавит на порядок больше.
SCRIPT_MAX = 3072


def _is_data(attrs):
    """Инертный блок данных, а не код. Два вида: поиск страницы и структурные
    данные. Проверять «application/json in attrs» было НЕДОСТАТОЧНО —
    «application/ld+json» такой подстроки не содержит, и структурные данные
    поехали бы по правилам исполняемого кода."""
    return "application/json" in attrs or "application/ld+json" in attrs


def g_no_scripts(files):
    """Не больше одного скрипта на страницу, встроенного и короткого.

    Правило было «ноль скриптов», и оно стоило сайту поиска: справочник, куда
    приходят с кодом на корпусе, не имел ни одного поля ввода. Правило было
    моим выбором, а не требованием. Теперь: скрипт может быть один, только
    встроенный, без src, короче двух килобайт — то есть браузеру по-прежнему
    некуда идти наружу.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    for p, t in pages.items():
        tags = re.findall(r"<script([^>]*)>(.*?)</script>", t, re.S)
        # Блоки ДАННЫХ браузер не исполняет: это инертный текст, и считать его
        # скриптом незачем. Их ДВА РАЗНЫХ ВИДА, и считаются они порознь —
        # поиск страницы (`application/json`) и структурные данные
        # (`application/ld+json`). Ограничение на исполняемый код от этого не
        # слабеет: исполняемый по-прежнему один, встроенный и короткий.
        data = [x for x in tags if _is_data(x[0])]
        code = [x for x in tags if not _is_data(x[0])]
        plain = [x for x in data if "ld+json" not in x[0]]
        ld = [x for x in data if "ld+json" in x[0]]
        if len(code) > 1:
            bad.append("%s: исполняемых скриптов %d" % (p, len(code)))
        if len(plain) > 1:
            bad.append("%s: блоков данных %d" % (p, len(plain)))
        if len(ld) > 1:
            bad.append("%s: блоков структурных данных %d" % (p, len(ld)))
        for attrs, body in data:
            if "src" in attrs:
                bad.append("%s: блок данных со ссылкой" % p)
        tags = code
        for attrs, body in tags:
            if "src" in attrs:
                bad.append("%s: скрипт со ссылкой" % p)
            if len(body) > SCRIPT_MAX:
                bad.append("%s: скрипт %d байт" % (p, len(body)))
            if re.search(r"https?:|//[a-z]", body):
                bad.append("%s: в скрипте внешний адрес" % p)
    return bad


def g_script_builds_no_markup(files):
    """Скрипт не строит разметку и не содержит обратных слэшей.

    Мой повторяющийся класс ошибок: экранирование съедается при переносе. На
    этом сайте оно съелось в скрипте фильтра — вложенные кавычки в строке с
    разметкой превратились в `shells is not defined`, то есть поиск на
    странице поиска не работал вовсе, а все двадцать гейтов были зелёные.

    Правило, закрывающее класс: сообщения и ссылки живут в РАЗМЕТКЕ, скрипт
    только переключает состояние. Тогда вложенных кавычек не возникает, и
    обратный слэш в теле скрипта становится признаком беды.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    seen = 0
    for p, t in pages.items():
        for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>",
                                      t, re.S):
            seen += 1
            if _is_data(attrs):
                # Блок данных. Слэш здесь законен: json.dumps пишет \u00b7
                # для разделителя. Зато он обязан РАЗБИРАТЬСЯ — иначе страница
                # молча останется без поиска, — и не содержать «<», которым
                # можно выйти из блока раньше времени.
                try:
                    json.loads(body)
                except ValueError:
                    bad.append("%s: блок данных не разбирается как JSON" % p)
                if "<" in body:
                    bad.append("%s: в блоке данных знак «<»" % p)
                continue
            if chr(92) in body:
                bad.append("%s: в скрипте обратный слэш" % p)
            if re.search(r"innerHTML|outerHTML|document\.write", body):
                bad.append("%s: скрипт строит разметку" % p)
            if re.search(r"<[a-z]+[ >]", body):
                bad.append("%s: в скрипте теги" % p)
    _sample(bad, seen, "блоков скрипта")
    return bad


def g_head(files):
    """ОБЛАСТЬ: страницы сайта. Виджеты проверяет g_embeds_are_fragments —
    у них нет описания и canonical ведёт на источник, и это не дефект."""
    bad = []
    pages = _site_pages(files)
    if not pages:
        return ["гейту нечего читать: страниц сайта нет"]
    for p, t in pages.items():
        m = re.search(r"<title>(.*?)</title>", t, re.S)
        if not m:
            bad.append("%s: нет title" % p)
        elif len(m.group(1)) > TITLE_MAX:
            bad.append("%s: title %d знаков" % (p, len(m.group(1))))
        d = re.search(r'<meta name="description" content="([^"]*)"', t)
        if not d or not DESC_MIN <= len(d.group(1)) <= DESC_MAX:
            bad.append("%s: описание %s"
                       % (p, len(d.group(1)) if d else "отсутствует"))
        c = re.search(r'<link rel="canonical" href="([^"]*)"', t)
        want = ("/" + p[:-len("index.html")]) if p.endswith("index.html") \
            else "/" + p
        if not c:
            bad.append("%s: нет canonical" % p)
        elif not c.group(1).endswith(want):
            bad.append("%s: canonical %s, ожидалось %s" % (p, c.group(1), want))
        if t.count("<h1>") != 1:
            bad.append("%s: h1 встречается %d раз" % (p, t.count("<h1>")))
    return bad


def g_internal_links(files):
    have = set()
    for p in files:
        have.add("/" + p)
        if p.endswith("index.html"):
            have.add("/" + p[:-len("index.html")])
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    _sample(bad, len(have), "известных адресов")
    seen = 0
    for p, t in pages.items():
        for r in re.findall(r'href="(/[^"#]*)"', t):
            seen += 1
            if r not in have:
                bad.append("%s -> %s" % (p, r))
    _sample(bad, seen, "внутренних ссылок")
    return sorted(set(bad))[:20]


def g_orphans(files):
    linked = set()
    for t in _html(files).values():
        for r in re.findall(r'href="(/[^"#]*)"', t):
            linked.add(r)
    bad = []
    if not _html(files):
        return ["гейту нечего читать: страниц нет"]
    for p in _html(files):
        if p in ("index.html", "404.html"):
            continue
        url = "/" + (p[:-len("index.html")] if p.endswith("index.html") else p)
        if url not in linked:
            bad.append(url)
    return sorted(bad)[:20]


def g_sitemap(files):
    sm = files.get("sitemap.xml")
    if not sm:
        return ["нет sitemap.xml"]
    listed = re.findall(r"<loc>https://[^/]+([^<]*)</loc>", sm)
    bad = []
    for url in listed:
        rel = url.lstrip("/") + ("index.html" if url.endswith("/") else "")
        if rel not in files:
            bad.append("в карте нет такого файла: %s" % url)
        elif "noindex" in files[rel]:
            bad.append("в карте закрытая от индексации: %s" % url)
    indexable = {"/" + (p[:-len("index.html")] if p.endswith("index.html")
                        else p)
                 for p, t in _html(files).items() if "noindex" not in t}
    missing = indexable - set(listed)
    if missing:
        bad.append("не попали в карту: %d, например %s"
                   % (len(missing), sorted(missing)[0]))
    return bad


def g_robots(files):
    r = files.get("robots.txt", "")
    return [] if "Sitemap:" in r else ["robots.txt не указывает карту сайта"]


def _foreign_hosts(files):
    """Каждый ЧУЖОЙ хост, за которым браузер идёт САМ при открытии страницы.

    Проверяется всё, за чем он идёт без участия человека, — src, href у
    <link> и url() в стилях, — и не только начинающееся с http: гейт,
    искавший «http», однажды пропустил src вообще без схемы.

    <a href> сюда НЕ ВХОДИТ, и это не послабление. Политика приватности
    описывает то, что грузится при открытии страницы: гипертекстовая ссылка
    не грузит ничего, пока по ней не нажали, и попав в этот список она
    заставила бы политику объявлять «сторонней службой» сайт производителя,
    на даташит которого мы просто ссылаемся. Ссылки наружу проверяет
    g_no_external по закрытому списку хостов, а «сколько сетевых запросов
    делает готовая страница» — g_no_scripts и правило нулевой сети.
    """
    hosts = set()
    for p, t in _html(files).items():
        refs = re.findall(r'\bsrc="([^"]*)"', t)
        refs += re.findall(r'<link\b[^>]*\bhref="([^"]*)"', t)
        refs += re.findall(r"url\(([^)]*)\)", t)
        for r in refs:
            r = r.strip().strip("'" + chr(34))
            m = re.match(r"(?:https?:)?//([^/]+)", r)
            if m and m.group(1).lower() != DOMAIN:
                hosts.add(m.group(1).lower())
    return hosts


def g_ad_disclosure_survives_the_network(files):
    """Обязательное раскрытие стоит на /privacy/ при ЛЮБОМ состоянии сети.

    Оно было написано «заранее, чтобы не писать второпях» — и стиралось
    ровно тем событием, ради которого писалось: ветка «сеть есть» печатала
    четыре предложения без единой ссылки на отказ, а переключала ветки одна
    строка в THIRD_PARTIES. Гейт политики сверял ХОСТЫ и состояние и ни
    одного требуемого предложения не искал.

    Проверяются ОБЕ сборки, а не только сегодняшняя: текст собирается и при
    выключенной сети, и при включённой, и каждая из трёх обязанностей —
    предыдущие посещения, отказ через настройки сети, отказ через
    aboutads.info — обязана найтись в обеих.
    """
    import render as rd
    bad = []
    page = files.get("privacy/index.html")
    if page is None:
        return ["страницы политики нет в сборке — проверять нечего"]
    want = ("previous visits to this and other sites",
            "adssettings.google.com", "optout.aboutads.info")
    vis = _text(page)
    for w in want:
        if w not in page:
            bad.append("сегодняшняя политика не несёт обязательного «%s»" % w)
    if "rel=\"nofollow noopener\"" not in page:
        bad.append("адреса отказа напечатаны, но не ссылками: читателю "
                   "предложено перепечатать их руками")
    _sample(bad, len(vis.split()), "слов в отданной политике")
    # ВТОРАЯ СБОРКА — с включённой сетью. Без неё правило проверяло бы
    # ровно ту ветку, которая и так цела, и молчало бы о той, что стирает.
    keep = rd.THIRD_PARTIES
    try:
        rd.THIRD_PARTIES = (("Google AdSense", "pagead2.googlesyndication.com",
                             "advertising", True),)
        on = rd.ad_privacy_block()
    finally:
        rd.THIRD_PARTIES = keep
    for w in want:
        if w not in on:
            bad.append("сборка С СЕТЬЮ теряет обязательное «%s»: раскрытие "
                       "стирается тем самым событием, ради которого "
                       "написано" % w)
    if "Google AdSense" not in on:
        bad.append("сборка с сетью не называет саму сеть")
    return bad


def g_privacy_matches_markup(files):
    """Текст политики сверяется с тем, что РЕАЛЬНО грузят страницы, и в ОБЕ
    СТОРОНЫ.

    Утверждение о приватности — это утверждение о БАЙТАХ, за которыми идёт
    браузер, а не о том, что мы написали: на студийном сайте политика
    отрицала аналитику, пока хост вставлял счётчик на каждую страницу.
    Проверка соответствия без обратной стороны у нас уже прятала беду на 105
    живых страницах, поэтому здесь считаются оба направления:

      · каждый ХОСТ, названный политикой, обязан встречаться в разметке;
      · каждый чужой хост в разметке обязан быть назван политикой;
      · отрицание аналитики и кук обязано подтверждаться разметкой;
      · раз на страницах есть рекламные места — политика обязана про них
        сказать, и если она называет рекламную сеть, эта сеть обязана быть в
        разметке.

    Прежняя редакция отрицала стороннее одним предложением на все времена
    («no third-party script loads on any page»): такое верно ровно до первого
    дня заработка и ложно на следующий.
    """
    pv = files.get("privacy/index.html", "")
    if not pv:
        return ["нет страницы приватности"]
    pages = _html(files)
    if not pages:
        return ["страниц ноль — пустая выборка это провал"]
    bad = []
    declared = {h.lower() for h in re.findall(r'data-host="([^"]*)"', pv)}
    if not declared and 'data-hosts="none"' not in pv:
        bad.append("политика не называет ни одной службы и не говорит, что их "
                   "нет вовсе")
    if declared and 'data-hosts="none"' in pv:
        bad.append("политика одновременно называет службы и утверждает, что "
                   "их нет")
    actual = _foreign_hosts(files)
    for h in sorted(declared - actual):
        bad.append("политика называет %s, а разметка за ним не ходит" % h)
    for h in sorted(actual - declared):
        bad.append("разметка ходит за %s, а политика о нём молчит" % h)

    claims_none = "runs no analytics" in pv
    no_cookies = "sets no cookies" in pv
    for p, t in sorted(pages.items()):
        bodies = " ".join(b for _a, b in
                          re.findall(r"<script([^>]*)>(.*?)</script>", t, re.S))
        loads = bodies + " " + " ".join(re.findall(r'src="([^"]*)"', t))
        if claims_none and re.search(r"gtag|analytics|plausible|umami|matomo",
                                     loads, re.I):
            bad.append("%s: политика отрицает аналитику, а разметка её несёт" % p)
        if no_cookies and re.search(r"document\.cookie|localStorage", bodies):
            bad.append("%s: политика отрицает куки и хранилище" % p)

    # Реклама: разметка и политика описывают ОДНО состояние.
    ads_in_markup = sum(1 for t in pages.values() if 'class="bx-ad ' in t)
    m = re.search(r'data-ads="([^"]*)"', pv)
    if ads_in_markup and not m:
        bad.append("рекламные места есть на %d страницах, а политика о них не "
                   "говорит ни слова" % ads_in_markup)
    if m and m.group(1) != "none":
        net = m.group(1).lower()
        if net not in declared:
            bad.append("политика называет рекламную сеть %s, но не считает её "
                       "сторонней службой" % net)
        if net not in actual:
            bad.append("политика называет рекламную сеть %s, а разметка за ней "
                       "не ходит" % net)
    elif m and not ads_in_markup:
        bad.append("политика описывает рекламные места, которых в разметке "
                   "нет ни одного")
    return bad[:20]


# Абзацы, которые НЕ являются разбором раздела: подпись к столбцам, подпись
# к рисунку и строка чужих маркировок. Список объявлен здесь, а не выведен из
# того, что попалось: гейт, берущий определение у проверяемого, проверяет
# функцию ею же.
NOT_THE_ANSWER = ("bx-legend", "bx-cap", "bx-also", "bx-src", "bx-nolink")


def _section_answer(sect):
    """Абзац РАЗБОРА внутри раздела: первый <p>, который не подпись.

    Раньше правило звучало «первый <p> сразу за <h2>», и это работало ровно
    до того дня, когда таблицу подняли выше разбора: между заголовком и
    разбором встали подпись к столбцам и сама таблица, регулярка
    `</h2>\\s*<p` перестала совпадать — и гейт МОЛЧА позеленел бы на всех
    страницах элементов. Область гейта — часть гейта, и переверстка её
    сдвинула: правило теперь ищет абзац по РОЛИ, а не по соседству.
    """
    for m in re.finditer(r"<p([^>]*)>(.*?)</p>", sect, re.S):
        attrs, body = m.group(1), m.group(2)
        if any(c in attrs for c in NOT_THE_ANSWER):
            continue
        return re.sub(r"<[^>]+>", " ", body)
    return None


def g_answer_first(files):
    """Под каждым H2 самодостаточный абзац своего окна и с числом.

    Абзац ищется ВНУТРИ РАЗДЕЛА и по роли, а не по соседству с заголовком:
    в разделе замен между заголовком и разбором стоят подпись к столбцам и
    таблица, потому что ответ должен быть виден раньше разговора о нём.
    """
    import depth as _D
    import render as rd
    bad = []
    cells = _cells(files)
    if not cells:
        return ["страниц элементов нет — пустая выборка это провал"]
    seen = 0
    for p, t in cells.items():
        col = _main_col(t)
        if col is None:
            bad.append("%s: основная колонка не нашлась" % p)
            continue
        chunks = re.split(r"<h2>", col)
        for chunk in chunks[1:]:
            h2 = chunk.split("</h2>")[0]
            if h2 in P.CONSTANT_HEADS:
                continue
            sect = chunk.split("</h2>", 1)[1] if "</h2>" in chunk else ""
            # Раздел чертежа — ОБЪЯВЛЕННОЕ исключение, и у него есть цена:
            # чертёж обязан там быть. Прежде исключение действовало молча,
            # потому что регулярка «</h2>\\s*<p» на нём просто не совпадала.
            if h2 in rd.FIGURE_HEADS:
                seen += 1
                if 'class="bx-fig"' not in sect:
                    bad.append("%s: «%s» объявлен разделом чертежа, а чертежа "
                               "в нём нет" % (p, h2[:26]))
                continue
            para = _section_answer(sect)
            if para is None:
                bad.append("%s: «%s» без абзаца разбора вовсе" % (p, h2[:26]))
                continue
            seen += 1
            # СЧИТАЕТ ГЕЙТ, И ОКНО ЗНАЕТ НАИЗУСТЬ. Раньше здесь стояли P.wc
            # и rd.window_for — те же счётчик и те же границы, по которым
            # абзац и складывался: с окном (0, 1000000) гейт печатал
            # «пройден» на любой прозе, а с постоянным счётчиком — на любой
            # длине. Проверяющий сделал ровно это.
            n = _words(para)
            if n != P.wc(para):
                bad.append("%s: «%s» — генератор насчитал %d слов, гейт %d"
                           % (p, h2[:26], P.wc(para), n))
            kind = ("intro" if (h2 in rd.INTRO_HEADS
                                or _D.HEAD_KIND.get(h2) == "intro")
                    else "answer")
            lo, hi = WINDOW_KNOWN[kind]
            if tuple(rd.window_for(h2)) != (lo, hi):
                bad.append("%s: «%s» — окно генератора %s, известный ответ "
                           "%s" % (p, h2[:26], tuple(rd.window_for(h2)),
                                   (lo, hi)))
            if not lo <= n <= hi:
                bad.append("%s: «%s» — %d слов, окно %d–%d"
                           % (p, h2[:26], n, lo, hi))
            elif not re.search(r"[0-9]", para):
                bad.append("%s: «%s» без числа" % (p, h2[:26]))
    if not seen:
        bad.append("не проверено ни одного абзаца — пустая выборка это провал")
    return bad[:20]


def g_twins(files):
    """Ни одной пары страниц выше порога. Порогов ДВА, и они спрашивают разное:
    по видимому тексту — то, что видят читатель и поиск; по скелету фразы —
    «тот же абзац с подставленной величиной».

    СХОДСТВО СЧИТАЕТ ГЕЙТ, а не отбор. Проверяющий заставил render.jaccard
    возвращать ноль: отбор перестал отсеивать близнецов, страниц стало 164
    вместо 146, независимый счёт нашёл три пары выше порога — худшая 0,792 у
    /mr52/ против /nr52/, — а оба гейта близнецов напечатали «пройден» с
    цифрой 0,000 в руках. Здесь считается своей черепицей и своим Жаккаром, а
    ответ генератора сверяется с ответом гейта: расхождение значит, что
    корпус отбирался числом, которого никто не проверял.
    """
    import render as rd
    bad = []
    pairs = 0
    kinds = {}
    for p, t in _html(files).items():
        m = re.search(r'name="page-type" content="([a-z]+)"', t)
        if not m:
            continue
        kinds.setdefault(m.group(1), []).append(p)
    for kind, paths in sorted(kinds.items()):
        if len(paths) < 2:
            continue
        keys, texts, skels, theirs_t, theirs_s = [], [], [], [], []
        for p in paths:
            own = rd.own_prose(files[p])
            keys.append(p)
            texts.append(_shingle(own, rd.TEXT_PAT))
            skels.append(_shingle(own, rd.SKEL_PAT))
            theirs_t.append(rd._shingles(own, rd.TEXT_PAT))
            theirs_s.append(rd._shingles(own, rd.SKEL_PAT))
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                pairs += 1
                jt = _overlap(texts[i], texts[j])
                js = _overlap(skels[i], skels[j])
                # Сверка с генератором: он отбирал корпус этим числом.
                for who, mine, got in (
                        ("тексту", jt, rd.jaccard(theirs_t[i], theirs_t[j])),
                        ("скелету", js, rd.jaccard(theirs_s[i], theirs_s[j]))):
                    if abs(mine - got) > 1e-9:
                        bad.append("%s ~ %s: по %s отбор насчитал %.3f, гейт "
                                   "%.3f" % (keys[i], keys[j], who, got, mine))
                if jt > rd.TWIN_TEXT:
                    bad.append("%s ~ %s: текст %.2f" % (keys[i], keys[j], jt))
                elif js >= rd.TWIN_SKELETON:
                    bad.append("%s ~ %s: скелет %.2f" % (keys[i], keys[j], js))
                if len(bad) > 10:
                    return bad
    _sample(bad, pairs, "сравненных пар страниц")
    return bad


def g_scale_honest(files):
    """Все силуэты одного рисунка нарисованы в ОДНОМ масштабе.

    Проверяется по САМОЙ РАЗМЕТКЕ: ширина прямоугольника делится на объявленный
    масштаб и сверяется с подписанным размером. Рисунок с разными масштабами
    лжёт при верных подписях, и это худший вид ошибки — незаметный.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    seen = 0
    for p, t in pages.items():
        for svg in re.findall(r"<svg[^>]*class=\"bx-draw.*?</svg>", t, re.S):
            seen += 1
            m = re.search(r'class="bx-scale">([\d.]+) px per mm', svg)
            if not m:
                bad.append("%s: в рисунке не назван масштаб" % p)
                continue
            k = float(m.group(1))
            for w, lab in zip(
                    re.findall(r'<rect[^>]*width="([\d.]+)"[^>]*class="bx-body',
                               svg),
                    re.findall(r'class="bx-num"[^>]*>([\d.]+) mm', svg)):
                got = float(w) / float(lab)
                if abs(got - k) > 0.05 * k:
                    bad.append("%s: силуэт %s px при подписи %s мм даёт "
                               "%.2f px/мм, объявлено %.2f"
                               % (p, w, lab, got, k))
    _sample(bad, seen, "чертежей")
    return bad[:20]


def g_fit_and_volts_separate(files):
    """Посадка и электрика не сливаются в одно слово.

    «Compatible» и «equivalent to» обещают то, чего мы не проверяли: элемент,
    влезающий в отсек, не всегда безопасная замена. На этом сайте цена ошибки —
    испорченный прибор, и обещание одним словом здесь запрещено.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    # Запрет одним словом — на ВСЕХ страницах, а не только на страницах
    # элементов: витрина снятых была страницей-списком и правило её не
    # касалось, а нарушалось оно именно там.
    for p, t in pages.items():
        low = _text(t).lower()
        for w in FORBIDDEN:
            if w in low:
                bad.append("%s: обещание одним словом «%s»" % (p, w))

        # Успокоение вместо предупреждения: класс «wrong» — это не сползшее
        # показание, и слова про «не отказ» рядом с ним стояли на 13 живых
        # страницах при разнице до 700%.
        #
        # ОБЛАСТЬ ПРАВИЛА — ОДИН АБЗАЦ, а не страница целиком. Пока сверялось
        # по всей странице, гейт покраснел на четырёх ртутных страницах, где
        # «не как отказ» относится к ближайшей замене класса calibration, а
        # слова «different voltage class» стоят в ЛЕГЕНДЕ ШКАЛЫ и говорят о
        # самой оси. Правило про соседство утверждения и его опровержения; на
        # разных абзацах соседства нет. Нарочная поломка ставит обе половины в
        # ОДИН абзац и по-прежнему краснеет.
        for para in re.findall(r"<p[^>]*>(.*?)</p>", t, re.S):
            plow = _text(para).lower()
            if "not as a failure" in plow and "different voltage class" in plow:
                bad.append("%s: «не как отказ» при другом классе напряжения"
                           % p)
                break
        # Прокладка под элемент, который и так глубже, — совет наоборот.
        if "spacer" in low and "is deeper" in low:
            bad.append("%s: прокладка там, где элемент глубже" % p)

    for p, t in _html(files).items():
        if '<table class="bx-fits"' in t:
            head = re.search(r'<table class="bx-fits">.*?</thead>', t, re.S)
            if head and ("Fit" not in head.group(0)
                         or "Voltage" not in head.group(0)):
                bad.append("%s: в таблице замен нет двух отдельных столбцов" % p)

    # ЛЮБАЯ таблица, называющая замену вердиктом посадки, обязана в той же
    # строке назвать напряжение. Иначе «drop-in» читается как ответ, а он
    # ответ только на половину вопроса.
    fits = set(P.FIT_WORD.values())
    verdicts = 0
    for p, t in pages.items():
        for row in re.findall(r"<tr[^>]*><th>.*?</tr>", t, re.S):
            cellsv = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            words = {re.sub(r"<[^>]+>", "", c).strip() for c in cellsv}
            if not (words & fits):
                continue
            verdicts += 1
            if "bx-v-" not in row:
                bad.append("%s: вердикт посадки без класса напряжения" % p)
                break
    _sample(bad, verdicts, "строк таблиц с вердиктом посадки")
    return bad[:20]


def _verdict_pages(files):
    """ВЫБОРКА ПО СОДЕРЖИМОМУ, а не по типу страницы.

    Правило «рекомендация не выходит без границ применимости» проверялось
    только там, где page-type равен «cell», и нарушалось ровно там, куда
    главная отправляет большинство пришедших: витрина снятых делала 64
    рекомендации без единой оговорки этого сайта. Область гейта — часть
    гейта, и спрашивать надо не только «что он проверяет», но и «на каком
    множестве».

    Страница попадает в выборку, если на ней есть метка класса напряжения
    рядом с названием другого элемента (`bx-vtag`) или столбец «Closest
    current». Разметка ищется В РАЗМЕТКЕ, а не в видимом тексте: имена
    классов живут и в CSS, встроенном в каждую страницу.

    ВИДЖЕТЫ СЮДА НЕ ВХОДЯТ, и это сказано ЗДЕСЬ, а не получается само.
    Виджет — фрагмент чужой страницы: у него нет ни шапки, ни подвала, ни
    места для трёх блоков этого сайта, и оговорка «not affiliated with» в нём
    относилась бы к чужому сайту, а не к нашему. Правило для них написано
    отдельным гейтом g_embed_verdict_carries_limits, и написано оно ровно
    потому, что до него виджеты публиковали вердикт вообще без оговорок,
    молча пользуясь тем, что эта выборка их не видела.
    """
    out = {}
    for p, t in _site_pages(files).items():
        body = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        if 'class="bx-vtag"' in body or "Closest current" in body:
            out[p] = t
    return out


def g_safety_notice(files):
    """На каждой странице, КОТОРАЯ НАЗЫВАЕТ ЗАМЕНУ, стоит блок границ
    применимости, предупреждение об аккумуляторах и оговорка о
    неаффилированности. Оговорка, существующая и никуда не подшитая, —
    задокументированная причина отказа рекламной сети."""
    bad = []
    pages = _verdict_pages(files)
    # Пустая выборка обязана краснеть: два рекламных гейта этого сайта до сих
    # пор печатают «пройден» над пустотой.
    if not pages:
        return ["выборка страниц с вердиктом пуста — гейту не на чем работать"]
    for p, t in pages.items():
        if "Before you swap anything" not in t:
            bad.append("%s: нет блока границ применимости" % p)
        if "not affiliated with" not in t:
            bad.append("%s: нет оговорки о неаффилированности" % p)
        if "Rechargeable cells are never a drop-in" not in t:
            bad.append("%s: нет предупреждения об аккумуляторах" % p)
    return bad[:20]


def g_no_empty_ad_slot(files):
    """Пустого рекламного места в разметке нет.

    display:none не выводит узел из :last-child, и пятьсот сорок невидимых мест
    однажды сломали у нас пять правил отступов на 157 страницах. Место
    появляется вместе с объявлением или не появляется вовсе.
    """
    bad, seen = [], 0
    for p, t in _html(files).items():
        for m in re.finditer(r'<div class="bx-ad[^"]*">(.*?)</div>', t, re.S):
            seen += 1
            if not m.group(1).strip():
                bad.append("%s: пустое рекламное место в разметке" % p)
    # Гейт, осмотревший НОЛЬ мест, ничего не доказал: он печатал «пройден» на
    # сборке, в которой рекламы не было вовсе.
    if not seen:
        bad.append("мест не осмотрено ни одного — пустая выборка это провал, "
                   "а не «пройден»")
    return bad[:20]


def g_css_classes_used(files):
    """Каждый класс, объявленный в CSS, встречается в разметке.

    Класс без применения — это либо забытая правка, либо рычаг, которого нет.
    Описанный и несуществующий рычаг хуже отсутствующего: на него рассчитывают.
    """
    bad = []
    # ОТДАННЫЕ байты, а не текст модуля: рычаг, объявленный в одном месте и
    # уехавший из другого, — тот же дефект, вид сбоку.
    sheets = _sheets_ship(files, bad)
    declared = set(re.findall(r"\.(bx-[a-z0-9-]+)", sheets.get("CSS", "")))
    used = set()
    for t in _html(files).values():
        for attr in re.findall(r'class="([^"]*)"', t):
            used.update(attr.split())
        # Классы, которые СОЗДАЁТ скрипт, тоже применяются — просто позже.
        # Гейт обязан смотреть на то, что окажется в браузере, а не только на
        # то, что лежит в файле; иначе он объявит прогрессивное улучшение
        # мёртвым кодом и заставит выбросить работающую вещь.
        for body in re.findall(r"<script[^>]*>(.*?)</script>", t, re.S):
            used.update(re.findall(r"bx-[a-z0-9-]+", body))
    # Жалобы разбора отданных таблиц возвращаются ВМЕСТЕ с находкой: они
    # тут терялись, и гейт печатал «пройден» на пустом списке классов.
    _sample(bad, len(declared), "объявленных в отданном CSS классов")
    missing = sorted(declared - used)
    if missing:
        bad.append("класс объявлен в CSS и не встречается в разметке: %s"
                   % ", ".join(missing[:8]))
    return bad[:20]


def _snapshot():
    """Снимок производителя, прочитанный С ДИСКА.

    Гейт, сверяющий страницу с тем, что породил её же генератор, соглашается
    сам с собой. Источник читается отдельно и целиком.
    """
    p = os.path.join(HERE, "data", "energizer_cells.json")
    return json.load(io.open(p, encoding="utf-8"))


_SNAP_RAW = {}


def _snapshot_text():
    if "t" not in _SNAP_RAW:
        p = os.path.join(HERE, "data", "energizer_cells.json")
        _SNAP_RAW["t"] = io.open(p, encoding="utf-8").read().upper()
    return _SNAP_RAW["t"]


def _in_snapshot(name):
    """Стоит ли ИМЕННО ЭТО имя в снимке — целиком, а не куском чужого."""
    if not name:
        return False
    return bool(re.search(r"(?<![A-Z0-9])%s(?![A-Z0-9])"
                          % re.escape(name.upper()), _snapshot_text()))


def g_chemistry_matches_code(files):
    """Химия страницы не спорит ни с буквой обозначения, ни с полем записи.

    Прежняя версия спрашивала лишь одно: встречается ли нужное слово ГДЕ-ТО
    на странице. Оно встречалось — в таблице соседей, — и MR43 уехал в
    выкладку как «silver oxide» при 1,4 В, чего не бывает: буква M называет
    ртуть. Теперь буква обозначения сверяется с полем ТОЙ ЖЕ записи снимка, и
    расхождение обязано быть НАПЕЧАТАНО, а не разрешено молча.

    Сперва само правило проверяется известными ответами: иначе гейт сверял бы
    вывод с той же функцией, которая его и породила.
    """
    import cells as C
    bad = []
    known = (("MR43", "mercuric oxide"), ("LR44", "alkaline"),
             ("SR44", "silver oxide"), ("CR2032", "lithium"),
             ("PR44", "zinc air"), ("HR03", "nickel-metal hydride"),
             ("R6", "carbon zinc"), ("FR6", "lithium"))
    for code, want in known:
        got = C.chem_canon(C.chem_from_code(code) or "")
        if got != want:
            bad.append("буква обозначения читается неверно: %s -> %s, надо %s"
                       % (code, got or "ничего", want))
    if bad:
        return bad

    by_code = {}
    for r in _snapshot():
        for c in C.iec_all(r):
            by_code.setdefault(re.sub(r"[^A-Z0-9]", "", c.upper()),
                               []).append(C._s(r, "battery-chemistry"))
    pages = _cells(files)
    if not pages:
        bad.append("гейт не нашёл ни одной страницы элемента")
    _sample(bad, len(by_code), "обозначений, разобранных из снимка")
    matched = 0
    for p, t in sorted(pages.items()):
        m = re.search(r"<h1>([^<]+)</h1>", t)
        if not m:
            continue
        code = m.group(1).strip()
        want = C.chem_from_code(code)
        if not want:
            continue
        low = _text(t).lower()
        short = C.chem_canon(want)
        if short not in low:
            bad.append("%s: код обещает %s, на странице этого нет"
                       % (p, short))
        fields = by_code.get(re.sub(r"[^A-Z0-9]", "", code.upper()), [])
        matched += 1 if fields else 0
        clash = sorted({C.chem_canon(f) for f in fields
                        if f and C.chem_canon(f) != short})
        # Раскрытий два, и они про РАЗНОЕ. Спор буквы с полем самого элемента
        # (MR43: одна запись, поле «серебро», буква M) печатается словами
        # «The two disagree». Запись ЧУЖОЙ химии под тем же кодом (EV115 —
        # угольно-цинковый под LR6) печатается словами «chemistry rather
        # than». Молчания не допускается ни в одном из двух случаев.
        if clash:
            vis = _text(t)
            told = ("The two disagree" in vis
                    or "chemistry rather than" in vis)
            unnamed = [ch for ch in clash if ch not in vis.lower()]
            if unnamed or not told:
                bad.append("%s: запись говорит %s, буква %s, а страница "
                           "молчит об этом" % (p, ", ".join(clash), short))
    # ВТОРАЯ СТОРОНА: поле записи обязано НАХОДИТЬСЯ. Пока оно не находилось
    # ни разу, сверка буквы с полем не выполнялась вовсе, а гейт печатал
    # «пройден» — проверяющий сломал разбор снимка и не услышал ни звука.
    _sample(bad, matched, "страниц, которым нашлась запись снимка")
    return bad[:20]


def g_ad_slots_exact(files):
    """Рекламное место отрисовывается РОВНО в заявленный размер.

    Судья нашёл у одного из макетов объявленный 300x600, отрисованный как
    256x600, и назвал это верно: не косметика, а недобор инвентаря, то есть
    денег. Замер в браузере показал у нас то же на узком экране: 728x90
    сплющивался до 366x90. Поэтому на узком МЕНЯЕТСЯ ФОРМАТ, а размеры заданы
    точно и сверяются с объявлением render.AD_SLOTS.
    """
    import render as rd
    bad = []
    css = _sheets_ship(files, bad).get("AD_CSS", "")
    if not rd.AD_SLOTS:
        return ["мест не объявлено вовсе — пустая выборка это провал, "
                "а не «пройден»"]
    for cls, modes in sorted(rd.AD_SLOTS.items()):
        found = re.findall(r"\." + re.escape(cls) + r"\{width:(\d+)px;"
                           r"height:(\d+)px\}", css)
        got = {(int(a), int(b)) for a, b in found}
        # Объявление двухрежимное: широкая колонка и узкая. Нарисованы должны
        # быть РОВНО те же размеры, и проверяется это в обе стороны — гейт
        # соответствия без обратной стороны однажды спрятал у нас слипшийся
        # текст в 520 ячейках на 105 живых страницах.
        want = {tuple(s) for mode in modes.values() for s in mode}
        if got != want:
            miss = sorted(want - got)
            extra = sorted(got - want)
            bad.append("%s: объявлено, но не нарисовано %s; нарисовано, но не "
                       "объявлено %s" % (cls, miss, extra))
    # Искать надо СВОЙСТВО в теле правила, а не строку где угодно: условие
    # медиазапроса «@media (max-width:63rem)» тоже содержит эти буквы, и первая
    # версия гейта покраснела на собственном переключении формата.
    bodies = " ".join(re.findall(r"\{([^}]*)\}", css))
    if "max-width" in bodies:
        bad.append("в теле правила места есть max-width — место будет "
                   "сплющено, а не заменено другим форматом")
    # Гейт БОЛЬШЕ НЕ СТОИТ внутри условия, которое охраняет: раньше он
    # начинался с `if not rd.ADS: return`, то есть выключался тем же флагом,
    # что и проверяемое, и был структурно неспособен покраснеть на уезжающей
    # сборке.
    known = set(rd.AD_SLOTS)
    pages = _html(files)
    if not pages:
        return ["страниц ноль — пустая выборка это провал"]
    seen = 0
    for p, t in pages.items():
        for m in re.finditer(r'<div class="bx-ad ([a-z-]+)">', t):
            seen += 1
            if m.group(1) not in known:
                bad.append("%s: место с неизвестным классом %s"
                           % (p, m.group(1)))
    if not seen:
        bad.append("ни одного рекламного места на %d страницах — сайт живёт "
                   "с рекламы, и отсутствие инвентаря это провал" % len(pages))
    return bad[:20]


def g_drawing_never_shrinks(files):
    """Чертёж с подписанным масштабом не ужимается по ширине.

    Честность масштаба должна держаться ПРАВИЛОМ, а не удачей: пока картинку
    можно сжать средствами CSS, подпись «14 px per mm» становится ложью на
    экране, оставаясь правдой в разметке. Проверяется по стилю, а не по
    намерению.
    """
    bad = []
    css = _sheets_ship(files, bad).get("CSS", "")
    # Гейт читает СТИЛЬ, поэтому обязан убедиться, что стиль уезжает на
    # страницы и что чертежи на них есть: иначе он проверяет таблицу,
    # которой никто не видит, и молчит над пустой выкладкой.
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    _sample(bad, sum(1 for t in pages.values() if "bx-draw" in t),
            "страниц с чертежом")
    m = re.search(r"\.bx-draw\{([^}]*)\}", css)
    if not m:
        return bad + ["в CSS нет правила для .bx-draw"]
    rule = m.group(1)
    if "max-width:none" not in rule:
        bad.append(".bx-draw допускает сжатие: %s" % rule[:60])
    # Контейнер обязан уметь прокручиваться, иначе рисунок разорвёт страницу.
    f = re.search(r"\.bx-fig\{([^}]*)\}", css)
    if not f or "overflow-x:auto" not in f.group(1):
        bad.append(".bx-fig не прокручивается — широкий чертёж порвёт страницу")
    return bad


def g_links_point_at_pages(files):
    """Ссылка на элемент ведёт на его страницу, если страница есть.

    Гейт «ссылки ведут на существующее» этого не ловит: /codes/ существует.
    Валидная ссылка не туда — отдельный дефект, и он убил главный клик сайта:
    663 ссылки в таблицах замен вели в список из 720 строк вместо страницы
    замены. Причина была в двойном импорте модуля, но гейт обязан ловить
    следствие, а не догадываться о причине.
    """
    have = {p[:-len("/index.html")] for p in files if p.endswith("/index.html")}
    bad = []
    _sample(bad, len(have), "страниц с собственным адресом")
    seen = 0
    for p, t in _html(files).items():
        for tbl in re.findall(r'<table class="bx-fits">.*?</table>', t, re.S):
            seen += 1
            for href, code in re.findall(r'<a href="([^"]+)">([^<]+)</a>', tbl):
                if href != "/codes/":
                    continue
                want = re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")
                if want in have:
                    bad.append("%s: ссылка на %s ведёт в указатель, хотя "
                               "страница /%s/ существует" % (p, code, want))
    _sample(bad, seen, "таблиц замен")
    return bad[:20]


def g_numbers_agree(files):
    """Число, названное в прозе, совпадает с тем, что на сайте есть.

    Каждая страница считала своё население сама, и три страницы разошлись:
    218 против 210, 134 против 126, обещанные 160 оболочек против 11 страниц.
    Гейт сверяет заявленное с ФАКТИЧЕСКИМ содержимым выкладки.
    """
    import render as rd
    bad = []
    home = files.get("index.html", "")
    hubs = len({p.split("/")[1] for p in files
                if p.startswith("shell/") and p.endswith("index.html")})
    # Порог стоял здесь СЛОВОМ — «that carry three», — и якорем этого гейта
    # было само слово. Подмена MIN_HUB с 3 на 4 в байтовой копии проходила
    # 88 гейтов из 88: сайт публиковал шесть оболочек при пороге 4 и писал
    # «three». Теперь порог читается цифрой И сверяется с константой.
    m = re.search(r"the (\d+) envelopes that carry (\d+)", home)
    if not m:
        bad.append("главная не называет число страниц оболочек")
    else:
        if int(m.group(1)) != hubs:
            bad.append("главная обещает %s страниц оболочек, на сайте %d"
                       % (m.group(1), hubs))
        if int(m.group(2)) != rd.MIN_HUB:
            bad.append("главная называет порог оболочки %s, а MIN_HUB это %d"
                       % (m.group(2), rd.MIN_HUB))

    codes = files.get("codes/index.html", "")
    rows = len(re.findall(r"<li[ >]", codes))
    m5 = re.search(r"the list of <a[^>]*>(\d+) codes", home)
    if not m5:
        bad.append("главная не называет число кодов в указателе")
    elif int(m5.group(1)) != rows:
        bad.append("главная обещает %s кодов, в указателе строк %d"
                   % (m5.group(1), rows))

    sh = files.get("shells/index.html", "")
    m2 = re.search(r"(\d+) envelopes here carry (\d+) designations or more", sh)
    if not m2:
        bad.append("страница оболочек не называет ни числа, ни порога")
    else:
        if int(m2.group(1)) != hubs:
            bad.append("страница оболочек говорит %s, каталогов %d"
                       % (m2.group(1), hubs))
        if int(m2.group(2)) != rd.MIN_HUB:
            bad.append("страница оболочек называет порог %s, MIN_HUB это %d"
                       % (m2.group(2), rd.MIN_HUB))

    dis = files.get("discontinued/index.html", "")
    rows = len(re.findall(r"<tr[^>]*><th>", dis)) - 1  # минус строка заголовка
    m3 = re.search(r"The (\d+) listed here", dis)
    if not m3:
        bad.append("страница снятых не называет число строк")
    elif int(m3.group(1)) != rows:
        bad.append("страница снятых обещает %s строк, в таблице %d"
                   % (m3.group(1), rows))

    cells = len({p.split("/")[0] for p in files
                 if p.endswith("/index.html") and p.count("/") == 1
                 and 'content="cell"' in files[p]})
    meth = files.get("method/index.html", "")
    m4 = re.search(r"and (\d+) have a page", meth)
    if not m4:
        bad.append("метод не называет число страниц")
    elif int(m4.group(1)) != cells:
        bad.append("метод обещает %s страниц элементов, собрано %d"
                   % (m4.group(1), cells))
    # Оба порога метода — цифрой и против своих констант.
    m6 = re.search(r"at least (\d+) of those computed values", meth)
    if not m6:
        bad.append("метод не называет порог вычисленных величин")
    elif int(m6.group(1)) != rd.MIN_FACTS:
        bad.append("метод называет порог величин %s, MIN_FACTS это %d"
                   % (m6.group(1), rd.MIN_FACTS))
    m7 = re.search(r"whose envelope carries (\d+) designations or more", meth)
    if not m7:
        bad.append("метод не называет порог оболочки")
    elif int(m7.group(1)) != rd.MIN_HUB:
        bad.append("метод называет порог оболочки %s, MIN_HUB это %d"
                   % (m7.group(1), rd.MIN_HUB))
    # Гейт называет ПЯТЬ страниц поимённо, и если хоть одной нет, он
    # проверяет меньше, чем думает. Расхождение он ловит в обе стороны:
    # сравнение строгое, и «больше посчитанного» и «меньше» одинаково
    # краснеют. Остальные счётные утверждения читает соседний гейт.
    for need in ("index.html", "codes/index.html", "shells/index.html",
                 "discontinued/index.html", "method/index.html"):
        if not files.get(need):
            bad.append("гейту нечего читать: нет страницы %s" % need)
    _sample(bad, len(_html(files)), "страниц")
    return bad


def g_dist_matches_build(files):
    """Файлы на диске совпадают с тем, что выдаёт сборка.

    Гейты читают то, что построено в памяти. Однажды это разошлось с диском:
    функция уехала ниже блока __main__, `python render.py` упал с NameError, а
    gates.py импортировал модуль и остался зелёным поверх прошлой выкладки.
    Тот же гейт закрывает правку руками поверх сгенерированного — доску фермы
    у нас так правили, и следующий запуск генератора стёр бы сутки работы.
    """
    if not os.path.isdir(DIST):
        return ["выкладки нет: сначала python render.py"]
    bad, seen = [], set()
    for root, _dirs, names in os.walk(DIST):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, DIST).replace(os.sep, "/")
            seen.add(rel)
            if rel not in files:
                bad.append("на диске лишний файл: %s" % rel)
                continue
            disk = io.open(full, encoding="utf-8", newline="").read()
            if disk != files[rel]:
                bad.append("на диске не то, что собрано: %s" % rel)
    for rel in files:
        if rel not in seen:
            bad.append("на диске нет собранного: %s" % rel)
    return sorted(bad)[:8]


def g_css_classes_declared(files):
    """Каждый класс из разметки объявлен в CSS.

    ВТОРАЯ сторона предыдущего гейта, и вопрос она задаёт другой. Правило без
    носителя — забытая правка. Носитель без правила — брак, который ВИДНО: у
    нас .bx-vtag не был объявлен нигде, и в 520 ячейках на 105 страницах
    напряжение слиплось с подписью в «1.2 V +0.0%same volts» при всех зелёных
    гейтах.
    """
    import design
    import render as rd
    # Три таблицы стилей, а не одна: общая, рекламная и та, что уезжает
    # внутри виджета. Пока читались только две, классы виджета выглядели
    # необъявленными, а необъявленный класс — это брак, который ВИДНО.
    bad = []
    sheets = _sheets_ship(files, bad)
    declared = set(re.findall(r"\.(bx-[a-z0-9-]+)",
                              "".join(sheets.get(k, "") for k in
                                      ("CSS", "AD_CSS", "EMBED_CSS"))))
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    _sample(bad, len(declared), "объявленных в CSS классов")
    used = set()
    for t in pages.values():
        for attr in re.findall(r'class="([^"]*)"', t):
            used.update(x for x in attr.split() if x.startswith("bx-"))
    _sample(bad, len(used), "применённых в разметке классов")
    extra = sorted(used - declared)
    if extra:
        bad.append("класс есть в разметке и не объявлен в CSS: %s"
                   % ", ".join(extra[:8]))
    return bad


def g_chemistry_names_whole(files):
    """Названия химий в витринах — целые слова из данных, а не обрубки.

    Список резался по шестидесятому знаку: «alkaline, carbon zinc, lithium,
    mercuric oxide and nickel-me». Видимый текст не режется по счётчику
    символов. Словарь берётся ИЗ ДАННЫХ — иначе гейт сверял бы строку с
    самой собой.
    """
    import render as rd
    known = {rd.chem(c) for c in rd.CELLS} if getattr(rd, "CELLS", None) else set()
    if not known:
        return ["не из чего составить словарь химий"]
    bad = []
    _sample(bad, len(known), "названий химий в данных")
    # Выборка гейта — СТРОКИ ДВУХ ВИТРИН, а не словарь: словарь взялся из
    # данных и непуст всегда, поэтому пустая выкладка гейт не роняла и он
    # печатал «пройден», не прочитав ни одной строки.
    seen = 0
    for p in ("shells/index.html", "sizes/index.html"):
        t = files.get(p, "")
        if not t:
            bad.append("гейту нечего читать: нет страницы %s" % p)
        for row in re.findall(r"<tr[^>]*><th>.*?</tr>", t, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if len(cells) < 3:
                continue
            txt = re.sub(r"<[^>]+>", "", cells[-1]).strip()
            if not txt:
                continue
            seen += 1
            names = [x.strip() for x in
                     re.split(r",\s*|\s+and\s+", txt) if x.strip()]
            for n in names:
                if n not in known:
                    bad.append("%s: «%s» — не химия из данных (в строке «%s»)"
                               % (p, n, txt[:70]))
    _sample(bad, seen, "строк с названием химии")
    return bad[:8]


def g_gone_not_present_tense(files):
    """Снятый элемент не говорит о себе в настоящем времени.

    На странице 3-0316 строка таблицы говорила «No longer listed», а абзац
    ниже — «It reaches shelves as 3-0316». Обе фразы порождены нами, обе
    прошли все гейты, и они противоречат друг другу. Это тот же класс, на
    котором FedPay называл падение с первого места на двадцать первое
    победой: две порождённые фразы об одном факте надо сверять МЕЖДУ СОБОЙ.
    """
    bad = []
    cellp = _cells(files)
    _sample(bad, len(cellp), "страниц элементов")
    seen = 0
    for p, t in cellp.items():
        vis = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " | ", t, flags=re.S)
        vis = re.sub(r"<[^>]+>", " | ", vis)
        gone = "No longer listed" in vis or "Not listed by Energizer" in vis
        if not gone:
            continue
        seen += 1
        for phrase in ("It reaches shelves", "is sold as", "is listed as",
                       "you can buy it", "reaches shelves as"):
            if phrase in vis:
                bad.append("%s: снят с производства, а пишет «%s»"
                           % (p, phrase))
    _sample(bad, seen, "страниц снятых элементов")
    return bad[:8]


def g_article_agrees(files):
    """«a»/«an» в видимом тексте согласовано со ЗВУКОМ следующего слова.

    На страницах стояло «A AA is a shape», «A F», «A N» и «a alkaline cell»:
    артикль был вписан в шаблон буквой. Английский выбирает его по звуку —
    «an AA» (эй-эй), «an F» (эф), но «a C» (си) и «a 9V» (найн-волт).

    Гейт сперва проверяет саму функцию известными ответами: иначе он сверял
    бы вывод с той же функцией, которая его и породила, и соглашался бы сам
    с собой при любой ошибке в правиле.
    """
    import prose as pr
    wrong = pr.article_selftest()
    if wrong:
        return ["правило артикля не сходится с известными ответами: %s"
                % ", ".join("%s -> %s, а надо %s" % x for x in wrong[:4])]
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    seen = 0
    for p, t in pages.items():
        vis = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " | ", t, flags=re.S)
        # Граница элемента — стена: в указателе кодов заголовок группы «A»
        # стоит прямо перед строкой «A23», и без стены это читается как
        # артикль.
        vis = re.sub(r"<[^>]+>", " | ", vis)
        vis = re.sub(r"&[a-z]+;", " ", vis)
        for m in re.finditer(r"\b(an?|An?) ([A-Za-z0-9][\w.-]*)", vis):
            seen += 1
            want = pr.article(m.group(2))
            if m.group(1).lower() != want:
                bad.append("%s: «%s», а надо «%s»" % (p, m.group(0), want))
    _sample(bad, seen, "артиклей в видимом тексте")
    return bad[:8]


def g_number_agrees_with_verb(files):
    """Число согласовано с глаголом в ВИДИМОМ тексте.

    «1 designation of the 6 here are discontinued» стояло на шести живых
    страницах: глагол был вписан в шаблон одной формой, а подлежащее
    считается. Ни один гейт не читал этого — поймал глаз.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    words = 0
    for p, t in pages.items():
        vis = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S)
        # Описание страницы человек читает в выдаче: это тоже видимый текст,
        # и «the 1 cell that drop into the same slot» стояло именно там.
        d = re.search(r'name="description" content="([^"]*)"', t)
        vis = re.sub(r"<[^>]+>", " ", vis)
        vis = re.sub(r"\s+", " ", vis) + (" | " + d.group(1) if d else "")
        words += len(vis.split())
        # Список глаголов расширен по живой находке: «The 1 option below
        # share the diameter» проходило мимо трёх первых.
        #
        # Запятая, двоеточие и «and» — граница придаточного: у фразы «1 cell
        # sits at exactly this size, and 20 more share» ДВА подлежащих, и
        # второе не единица. Без границы гейт краснел на верном тексте.
        for m in re.finditer(
                r"\b1 [a-z]+ (?![^.]{0,45}?\band\b)[^.,;:]{0,45}?"
                r"\b(are|have|were|share|run|carry|differ|sit|come|do|make"
                r"|hold|cost|need|fit|enter|stand|reach|weigh)\b", vis):
            bad.append("%s: «%s»" % (p, m.group(0)))
    _sample(bad, words, "видимых слов")
    return bad[:8]


def g_no_candidate_count(files):
    """Число «для скольких строк замены нет» равно числу таких строк.

    Подводка обещала, что таблица называет замену ДЛЯ КАЖДОЙ строки, а для 61
    из 126 она не называет ничего. Обещание в прозе и содержимое таблицы —
    две величины, и считать их надо одну по другой.
    """
    dis = files.get("discontinued/index.html", "")
    if not dis:
        return ["нет страницы снятых"]
    rows = re.findall(r"<tr[^>]*><th>.*?</tr>", dis, re.S)
    none = sum(1 for r in rows if "none in this catalog" in r)
    m = re.search(r"for (\d+) of them this catalog lists nothing", dis,
                  re.I)
    if not m:
        bad = ["страница снятых не называет, для скольких замены нет"]
        return bad
    if int(m.group(1)) != none:
        return ["страница снятых обещает %s строк без замены, их %d"
                % (m.group(1), none)]
    return []


def g_shell_slug_form(files):
    """Приставка в адресе оболочки совпадает с габаритом, НАПЕЧАТАННЫМ на
    самой странице.

    Всё круглое звалось монетой, и /shell/coin-14-5-50-5-mm/ описывал
    пальчиковый цилиндр 14,5 x 50,5 мм. Ссылки при этом были валидные, гейты
    зелёные: адрес существовал, просто врал.

    Оговорка обещала, что этот дефект закрыт, а гейт брал ожидаемую форму у
    C.shell_form — той самой функции, которая адрес и написала. Проверяющий
    заставил её отвечать «coin» на всё: каждый цилиндр уехал монетой, ИМЕННО
    ТОТ АДРЕС ИЗ ОГОВОРКИ вернулся на сайт, и гейт напечатал «пройден».

    Теперь эталонов два, и оба вне функции:
      · габарит читается из ВИДИМОГО ЗАГОЛОВКА страницы («14.5 x 50.5 mm»),
        сверяется с числами адреса и решает форму по правилу, написанному
        здесь (_form_of): три величины — коробка, круглая ниже своего
        диаметра — монета, не ниже — цилиндр;
      · ответ C.shell_form сверяется с этим выводом, и расхождение
        печатается: адрес пишет она, и молчать о её ответе нельзя.
    """
    import cells as C
    bad = []
    seen = 0
    for p, t in sorted(_html(files).items()):
        if not p.startswith("shell/") or not p.endswith("index.html"):
            continue
        seen += 1
        slug = p.split("/")[1]
        head = slug.split("-")[0]
        if head not in ("coin", "cylinder", "box"):
            bad.append("%s: приставка «%s» не из трёх известных" % (p, head))
            continue
        nums = [x for x in slug[len(head) + 1:-len("-mm")].split("-")]
        # 14-5-50-5 -> 14.5, 50.5;  26-5-17-5-48-5 -> 26.5, 17.5, 48.5
        vals, i = [], 0
        while i < len(nums):
            if i + 1 < len(nums) and len(nums[i + 1]) == 1:
                vals.append(float(nums[i] + "." + nums[i + 1]))
                i += 2
            else:
                vals.append(float(nums[i]))
                i += 1
        # ГАБАРИТ СО СТРАНИЦЫ, а не из адреса: адрес и есть проверяемое.
        m = re.search(r"<h1[^>]*>([^<]*)</h1>", t)
        shown = re.findall(r"[0-9]+(?:\.[0-9]+)?",
                           m.group(1)) if m else []
        printed = [float(x) for x in shown]
        if not printed:
            bad.append("%s: на странице не напечатан габарит вовсе" % p)
            continue
        if printed != vals:
            bad.append("%s: в адресе %s, а на странице напечатано %s"
                       % (p, vals, printed))
            continue
        want = _form_of(tuple(printed))
        if want is None:
            bad.append("%s: величин габарита %d — ни круглая, ни коробка"
                       % (p, len(printed)))
            continue
        if want != head:
            bad.append("%s: адрес говорит «%s», а напечатанный габарит %s — "
                       "это «%s»" % (p, head, printed, want))
        shell = (("round",) + tuple(vals)) if len(vals) == 2 \
            else (("prismatic",) + tuple(vals))
        theirs = C.shell_form(shell)
        if theirs != want:
            bad.append("%s: адрес пишет cells.shell_form, и она говорит "
                       "«%s», а габарит %s — это «%s»"
                       % (p, theirs, printed, want))
    _sample(bad, seen, "страниц оболочек")
    # Обе формы обязаны встретиться: гейт, увидевший одни монеты, ничего не
    # сказал бы про цилиндры — а сломанная функция отвечала именно «coin».
    heads = {p.split("/")[1].split("-")[0] for p in files
             if p.startswith("shell/") and p.endswith("index.html")}
    for want in ("coin", "cylinder"):
        if want not in heads:
            bad.append("ни одной оболочки формы «%s» — половина правила не "
                       "проверена ни разу" % want)
    return bad


def _payload(files, page="index.html"):
    """Указатель поиска ОДНОЙ страницы, разобранный в поля.

    Указатель лежит инертным блоком данных, то есть ТЕКСТОМ: гейт внутренних
    ссылок читает разметку и проходит мимо него целиком. Разбор один на все
    гейты — величина, разобранная в трёх местах по-своему, разойдётся.
    """
    t = files.get(page, "")
    m = re.search(r'<script type="application/json" id="bx-index">(.*?)'
                  r"</script>", t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
    except ValueError:
        return None
    if not isinstance(d, dict) or set(d) != {"w", "h", "r"} or not d.get("r"):
        return None
    rows = []
    for s in d["r"].split(";"):
        f = s.split("|")
        if len(f) != 6:
            return None
        try:
            rows.append({"name": f[0], "href": d["h"][int(f[1])],
                         "canon": f[2], "what": d["w"][int(f[3])],
                         "dims": f[4], "kind": f[5]})
        except (ValueError, IndexError):
            return None
    return rows


def _key(name):
    import render as rd
    return rd._index_key(name)


def _rows_by_key(rows):
    out = {}
    for r in rows:
        out.setdefault(_key(r["name"]), []).append(r)
    return out


def g_search_index_resolves(files):
    """Адреса внутри поискового указателя ведут на существующие страницы.

    Гейт внутренних ссылок читает РАЗМЕТКУ: href в теге. Адреса поиска лежат
    в блоке данных, то есть в тексте, и мимо того гейта проходят целиком —
    ровно тот класс, на котором мы уже горели с литеральным переносом строки
    в заголовках.
    """
    bad = []
    home = files.get("index.html", "")
    if 'id="bx-q"' not in home:
        bad.append("на главной нет поля поиска")
    rows = _payload(files)
    if rows is None:
        return bad + ["блок данных поиска отсутствует или не разбирается"]
    if len(rows) < 100:
        bad.append("в указателе поиска строк %d" % len(rows))
    by_key = _rows_by_key(rows)
    dup = sorted(k for k, v in by_key.items() if len(v) > 1)
    if dup:
        bad.append("ключи поиска повторяются: %s" % ", ".join(dup[:6]))
    for r in rows:
        href, name = r["href"], r["name"]
        if not href:
            bad.append("строка поиска без адреса: %s" % name)
            continue
        page = href.split("#")[0]
        if page.strip("/") + "/index.html" not in files:
            bad.append("поиск ведёт на несуществующее: %s -> %s"
                       % (name, href))
            continue
        if not r["what"]:
            bad.append("строка поиска без описания: %s" % name)
        if not _key(name):
            bad.append("имя без ключа: %s" % name)
        if r["kind"] not in ("0", "1", "2", "3"):
            bad.append("строка неизвестного рода: %s" % name)
        # Обозначение обязано НАЗЫВАТЬСЯ на той странице, куда ведёт: иначе
        # переход выглядит промахом. Торговая маркировка и обиходное имя
        # ведут на страницу элемента, где их и не должно быть.
        target = files.get(page.strip("/") + "/index.html", "")
        if r["kind"] in ("1", "2") and "#" not in href and target and \
                not re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                              % re.escape(name), target):
            bad.append("поиск ведёт на %s по имени «%s», а имени там нет"
                       % (href, name))
    return bad[:8]


def g_lookup_on_every_page(files):
    """Поле поиска — на КАЖДОЙ странице, и одно и то же.

    Главное действие справочника стояло на двух страницах из 164, и обе не
    те, на которые приводит выдача: человек приземлялся на /cr2016/ с CR2025
    в руке, и следующим его шагом была ссылка на список из 717 строк.

    Здесь же проверяется вторая половина обещания: страница работает БЕЗ
    скрипта. Поле стоит в разметке, а не показывается скриптом; форма
    отправляется на существующую страницу; подсказка про выключенные скрипты
    есть и она соседка поля, а не его замена.
    """
    bad = []
    # ОБЛАСТЬ: страницы сайта. Поле поиска внутри виджета увело бы человека
    # с чужой страницы, на которой виджет стоит, и потому его там нет.
    pages = _site_pages(files)
    if not pages:
        return ["гейту нечего читать: страниц сайта нет"]
    blocks = set()
    for p, t in sorted(pages.items()):
        if 'id="bx-q"' not in t:
            bad.append("%s: нет поля поиска" % p)
            continue
        m = re.search(r'<form class="bx-find[^"]*" id="bx-find"([^>]*)>', t)
        if not m:
            bad.append("%s: поле не в форме поиска" % p)
            continue
        attrs = m.group(1)
        if "hidden" in attrs:
            bad.append("%s: форма поиска скрыта в разметке" % p)
        act = re.search(r'action="([^"]*)"', attrs)
        if not act or act.group(1).strip("/") + "/index.html" not in files:
            bad.append("%s: форме поиска некуда отправляться без скрипта" % p)
        inp = re.search(r'<input type="search" id="bx-q"([^>]*)>', t)
        if not inp:
            bad.append("%s: поля ввода нет в разметке" % p)
        elif "hidden" in inp.group(1) or "name=" not in inp.group(1):
            bad.append("%s: поле скрыто или без имени — без скрипта мертво" % p)
        # Скрипт держится за ЭТИ узлы без проверок: ужимая его под два
        # килобайта, я снял с них `if`. Значит их наличие — обязанность
        # гейта, иначе пропавший узел молча убьёт весь поиск.
        for need, what in (('id="bx-nojs"', "подсказки про выключенные "
                                            "скрипты"),
                           ('id="bx-none"', "сообщения о промахе"),
                           ('id="bx-n"', "счётчика найденного"),
                           ('id="bx-res"', "списка подсказок")):
            if need not in t:
                bad.append("%s: нет %s" % (p, what))
        d = re.search(r'<script type="application/json" id="bx-index">'
                      r"(.*?)</script>", t, re.S)
        if not d:
            bad.append("%s: нет данных поиска" % p)
        else:
            blocks.add(d.group(1))
    if len(blocks) > 1:
        bad.append("указателей поиска на сайте %d, а должен быть один"
                   % len(blocks))
    return bad[:20]


# Что человек набирает и куда это ОБЯЗАНО его привести. Ответы известные,
# набраны руками из аудита: поиск отдавал ноль строк на «AA», «AAA» и «9V»
# при живых страницах в сорока пикселях ниже поля, и мусор на «D», «C» и «N».
LOOKUP_KNOWN = (
    ("aa", "/size/aa/"), ("aaa", "/size/aaa/"), ("9v", "/size/9v/"),
    ("c", "/size/c/"), ("d", "/size/d/"), ("n", "/size/n/"),
    ("f", "/size/f/"), ("j", "/size/j/"), ("lantern", "/size/lantern/"),
    ("ag13", "/lr44/"), ("sg13", "/sr44/"), ("ag12", "/lr43/"),
    ("v13ga", "/lr44/"), ("l1154", "/lr44/"), ("za675", "/pr44/"),
    ("dl2032", "/cr2032/"), ("cr123a", "/cr17345/"), ("23a", "/1811a/"),
    ("lr1130", "/lr54/"), ("sr1154", "/sr44/"), ("sr626", "/sr66/"),
    ("cr2032", "/cr2032/"), ("357", "/sr44/"),
)

# Хвост часового стандарта снимается С ЗАПРОСА, а не с данных: на элементе
# вытиснено SR626SW, в стандарте он SR626. Проверяется то, на что правило
# опирается: основа существует отдельной строкой.
LOOKUP_SUFFIX = (("sr626sw", "sr626"), ("sr721sw", "sr721"),
                 ("sr1154w", "sr1154"))

# Сколько строк показывает список подсказок. Число живёт В СКРИПТЕ, и гейт
# сверяется с ним же: обещание, не помещающееся в список, — рычаг, которого
# нет.
LOOKUP_SHOWN = 12


def g_lookup_answers_known_strings(files):
    """Набранное человеком находит ответ. Ответы ИЗВЕСТНЫЕ, не выведенные.

    Гейт не переписывает сопоставление на питоне — гейт, сверяющий вывод с
    той же функцией, которая его породила, у нас уже был зелёным на сломанном
    сайте. Он проверяет ДАННЫЕ, на которые опирается объявленный порядок
    ярусов: точное совпадение ключа, потом габарит. Само сопоставление
    проверяется руками в браузере, и иначе никак.
    """
    bad = []
    rows = _payload(files)
    if rows is None:
        return ["блок данных поиска отсутствует или не разбирается"]
    by_key = _rows_by_key(rows)
    if not by_key:
        return ["указатель поиска пуст — пустая выборка это провал"]
    for typed, want in LOOKUP_KNOWN:
        hit = by_key.get(typed)
        if not hit:
            bad.append("набрано «%s» — ни одной строки" % typed)
        elif hit[0]["href"].split("#")[0] != want:
            bad.append("набрано «%s» — ведёт на %s, известный ответ %s"
                       % (typed, hit[0]["href"], want))
    for typed, stem in LOOKUP_SUFFIX:
        if typed in by_key:
            continue
        if stem not in by_key:
            bad.append("«%s» снимает хвост до «%s», а такой строки нет"
                       % (typed, stem))
    # Голое число — это МИЛЛИМЕТРЫ. «20» обязано найти всё диаметром 20 мм.
    mm20 = [r for r in rows if r["dims"] == "20" or r["dims"].startswith("20x")]
    if len(mm20) < 3:
        bad.append("голое «20» находит %d строк по габариту" % len(mm20))
    if not any(r["name"] == "CR2032" for r in mm20):
        bad.append("CR2032 не находится по габариту 20 мм")
    return bad[:20]


def g_index_has_no_dead_ends(files):
    """Ни одна строка указателя не ведёт в никуда.

    193 строки из 715 — 27% — рисовались жирным текстом без единой ссылки:
    человек находил свой код и упирался. Якорь тоже обязан СУЩЕСТВОВАТЬ: адрес
    с решёткой, под которой нет метки, — это тот же тупик, только длиннее.
    """
    bad = []
    rows = _payload(files)
    if rows is None:
        return ["блок данных поиска отсутствует или не разбирается"]
    gone = files.get("discontinued/index.html", "")
    if not gone:
        bad.append("витрины снятых нет — гейту не с чем сверяться")
    anchors = 0
    for r in rows:
        href = r["href"]
        if not href:
            bad.append("строка без адреса: %s" % r["name"])
            continue
        if "#" not in href:
            continue
        page, frag = href.split("#", 1)
        anchors += 1
        target = files.get(page.strip("/") + "/index.html", "")
        if 'id="%s"' % frag not in target:
            bad.append("якорь %s не существует на %s" % (frag, page))
        # Лучший ответ не пропущен: у снятого элемента строка витрины снятых
        # называет ближайший текущий, и она лучше собственной строки указателя.
        if page == "/codes/" and gone:
            k = frag[2:]
            if 'id="d-%s"' % k in gone:
                bad.append("%s уводит в указатель, хотя строка витрины снятых "
                           "для него есть" % r["name"])
    if not anchors:
        bad.append("якорных адресов ноль — пустая выборка это провал")
    return bad[:20]


def g_lookup_promises_hold(files):
    """Обещанное про поиск ВЫПОЛНЯЕТСЯ.

    Описанный и несуществующий рычаг хуже отсутствующего: на него
    рассчитывают. Главная дважды обещала, что голое «20» найдёт всё диаметром
    20 мм, — а `measured()` требовал второго числа или букв «mm», и голое
    число в размерную ветку не попадало вовсе. Она же отвечала набравшему
    «AA», что его код принадлежит другой компании.

    Число из обещания читается ИЗ САМОЙ СТРАНИЦЫ, а не набирается здесь.
    """
    bad = []
    rows = _payload(files)
    if rows is None:
        return ["блок данных поиска отсутствует или не разбирается"]
    by_key = _rows_by_key(rows)
    pages = _html(files)
    if not pages:
        return ["гейту нечего читать: страниц нет"]

    # 1. Сайт больше не отсылает человека с его собственным кодом.
    for p, t in sorted(pages.items()):
        vis = _text(t)
        if "are not in this data" in vis:
            bad.append("%s: страница объявляет чужими коды, которые в "
                       "указателе есть" % p)
    for mark in ("AG13", "V13GA", "ZA675"):
        if _key(mark) not in by_key:
            bad.append("маркировка %s не заведена в указателе" % mark)

    # 2. Обещание про голое число подкреплено габаритами — И ДЛИНОЙ СПИСКА.
    # Список показывает первые LOOKUP_SHOWN строк; обещание, которое в него
    # не помещается, — это описанный рычаг, которого нет.
    home = files.get("index.html", "")
    # ВСЕ вхождения потолка, а не «есть хотя бы одно». Потолок стоит в
    # скрипте дважды — в общем наборщике и в подборе ближайшего габарита, — и
    # пока правило искало подстроку, поломка меняла первое вхождение, второе
    # оставалось на месте, и проверка обещания молча зеленела.
    caps = [int(x) for x in re.findall(r"h\.length<([0-9]+)", home)]
    if not caps:
        bad.append("в отданном скрипте нет потолка списка — обещание "
                   "проверять не с чем")
    for cap in sorted(set(caps)):
        if cap != LOOKUP_SHOWN:
            bad.append("скрипт показывает %d строк, а обещано %d"
                       % (cap, LOOKUP_SHOWN))
    m = re.search(r"a bare <b>([0-9]+)</b> lists the designations "
                  r"([0-9]+) mm across", home)
    if not m:
        bad.append("главная не обещает поиска по голому числу — "
                   "проверять нечего")
    else:
        if m.group(1) != m.group(2):
            bad.append("обещание называет два разных числа: %s и %s"
                       % (m.group(1), m.group(2)))
        d = m.group(1)
        named = [r for r in rows
                 if (r["dims"] == d or r["dims"].startswith(d + "x"))
                 and r["kind"] in ("0", "1")]
        if len(named) < 3:
            bad.append("обещано «%s перечисляет обозначения %s мм», строк по "
                       "габариту %d" % (d, d, len(named)))
        if len(named) > LOOKUP_SHOWN:
            bad.append("обещано перечислить обозначения %s мм, их %d, а "
                       "список показывает %d" % (d, len(named), LOOKUP_SHOWN))

    # 3. Примеры в самом поле находятся. Подсказка — тоже обещание.
    ph = re.search(r'placeholder="([^"]*)"', home)
    if not ph:
        bad.append("у поля поиска нет подсказки")
    else:
        for ex in [x.strip() for x in ph.group(1).split(",")]:
            k = _key(ex)
            if k in by_key:
                continue
            dk = "x".join(re.findall(r"[0-9]+(?:[.][0-9]+)?", ex))
            if dk and any(r["dims"] == dk or r["dims"].startswith(dk + "x")
                          for r in rows):
                continue
            bad.append("пример «%s» из подсказки ничего не находит" % ex)

    # 4. Каждое обиходное имя, названное ссылкой на главной, ищется по нему же.
    for href in set(re.findall(r'href="(/size/[a-z0-9-]+/)"', home)):
        slug = href.strip("/").split("/")[1]
        hit = by_key.get(_key(slug))
        if not hit:
            bad.append("на главной есть %s, а в указателе имени «%s» нет"
                       % (href, slug))
        elif hit[0]["href"] != href:
            bad.append("«%s» ведёт на %s, а на главной это %s"
                       % (slug, hit[0]["href"], href))
    return bad[:20]

def g_no_self_links(files):
    """Ни одна ссылка не ведёт на страницу, где стоит.

    В указателе 205 кодов из 720 ссылались на сам указатель: человек нажимал и
    оставался на месте без единого слова. Петля хуже отсутствия ссылки —
    отсутствие хотя бы честно.
    """
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "страниц")
    links = 0
    for p, t in pages.items():
        here = "/" + (p[:-len("index.html")] if p.endswith("index.html") else p)
        hrefs = re.findall(r'href="(/[^"#]*)"', t)
        links += len(hrefs)
        n = sum(1 for h in hrefs if h == here)
        if n:
            bad.append("%s: ссылок на самоё себя %d" % (p, n))
    _sample(bad, links, "внутренних ссылок")
    return bad[:20]


PLACEHOLDER_CELL = ("none", "nan", "null", "undefined", "unknown",
                    "choose a replacement", "()", "[]", "{}", "n/a")
PLACEHOLDER_TEXT = ("NaN", "undefined", "unknown", "Choose a Replacement")


def g_no_placeholder_values(files):
    """Ни одна ячейка не печатает питоновскую или скриптовую заглушку.

    «None» стоял значением колонки Envelope на четырёх витринах типоразмеров,
    а рядом «unknown» вместо напряжения. Запасной вариант «esc(x) or mdash» не
    срабатывал НИКОГДА: str(None) даёт непустую строку. Пропуск обязан быть
    НАЗВАН — тире или «not published», — а не показан внутренним значением.
    """
    bad = []
    pages = _html(files)
    if not pages:
        bad.append("гейту нечего читать: страниц нет")
    cells_seen = 0
    for p, t in sorted(pages.items()):
        for m in re.finditer(r"<(t[dh]|li)[^>]*>(.*?)</\1>", t, re.S):
            v = re.sub(r"\s+", " ",
                       re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            cells_seen += 1
            if v.lower() in PLACEHOLDER_CELL:
                bad.append("%s: ячейка со значением «%s»" % (p, v))
            elif not v and m.group(1) != "li":
                # ПУСТАЯ ячейка — то же самое «ничто», напечатанное
                # значением, только молча. Пропуск обязан быть НАЗВАН:
                # тире или «not published», и тогда читатель знает, что
                # это не ноль. Пункт списка сюда не входит: пустой <li>
                # ловит другой гейт, а разделители в меню законны.
                bad.append("%s: пустая ячейка таблицы" % p)
        if ">None<" in t:
            bad.append("%s: голое None в разметке" % p)
        vis = _text(t)
        for w in PLACEHOLDER_TEXT:
            if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(w), vis):
                bad.append("%s: в видимом тексте слово «%s»" % (p, w))
    if not cells_seen:
        bad.append("гейт не прочитал ни одной ячейки")
    return bad[:20]


def g_stamped_codes_in_source(files):
    """Каждое обозначение под словами «Also stamped» стоит В СНИМКЕ.

    Эта строка утверждает, что имя ВЫТИСНЕНО на корпусе. Сайт печатал под ней
    обозначения, которых не существует: LR1131 вместо настоящего LR1130,
    SR1131, LR1121 и пятизначные LR15111 и MR16112, которых стандарт не знает
    вовсе. Доказать мы можем ровно одно — что имя стоит в записи
    производителя, и печатать под этой строкой можно только его.
    """
    bad = []
    pats = (r'<p class="bx-also">Also stamped ([^<]*)</p>',
            r"<th>Also stamped</th><td>([^<]*)</td>",
            r'<p class="bx-legend">Also stamped on cells in this table: '
            r"([^<]*)\.</p>")
    n = 0
    for p, t in sorted(_html(files).items()):
        for pat in pats:
            for m in re.finditer(pat, t):
                for name in m.group(1).split(", "):
                    name = name.strip().rstrip(".")
                    if not name:
                        continue
                    n += 1
                    if not _in_snapshot(name):
                        bad.append("%s: «%s» напечатано как вытисненное, а в "
                                   "снимке его нет" % (p, name))
    # ОБЛАСТЬ ШИРЕ ОДНОЙ СТРОКИ: под «Also stamped» имя утверждается
    # вытисненным, а в заголовке страницы — просто опубликованным, и
    # прослеживаться до снимка обязано и то, и другое. Сайт печатал
    # LR1131 вместо LR1130 под одной строкой; заголовок отличается от
    # неё только тем, что его читают первым.
    heads = 0
    for p, t in sorted(_cells(files).items()):
        m = re.search(r"<h1>([^<]+)</h1>", t)
        if not m:
            bad.append("%s: у страницы элемента нет заголовка" % p)
            continue
        heads += 1
        name = m.group(1).strip()
        if not _in_snapshot(name):
            bad.append("%s: заголовок «%s» не стоит в снимке" % (p, name))
    _sample(bad, n, "строк вытисненных обозначений")
    _sample(bad, heads, "заголовков страниц элементов")
    return bad[:20]


# Известные ответы: полная форма МЭК для коротких обозначений, которые мы
# несём. Лежат ЗДЕСЬ, а не в генераторе, — иначе гейт сверял бы таблицу с ней
# же самой. None означает: ответа нет, печатать нельзя ничего.
IEC_KNOWN = (
    ("LR44", "LR1154"), ("SR44", "SR1154"), ("LR54", "LR1130"),
    ("SR54", "SR1130"), ("LR55", "LR1120"), ("SR55", "SR1120"),
    ("LR43", "LR1142"), ("SR43", "SR1142"), ("SR42", "SR1136"),
    ("LR41", "LR736"), ("SR41", "SR736"), ("SR48", "SR754"),
    ("SR57", "SR927"), ("SR58", "SR721"), ("SR59", "SR726"),
    ("SR60", "SR621"), ("SR66", "SR626"), ("SR68", "SR916"),
    ("SR69", "SR921"),
    ("LR52", None), ("MR52", None), ("MR43", None), ("MR44", None),
    ("PR44", None), ("LR03", None), ("CR2032", None),
)


def g_iec_long_form_known(files):
    """Полная форма МЭК берётся из таблицы, и каждое имя прослеживается.

    Форма ВЫЧИСЛЯЛАСЬ из опубликованного габарита, и правило было
    неустойчиво: на одной оболочке 11,6 x 2,05 давало SR1120, а 11,6 x 2,1 —
    LR1121. README уверял, что правило «сверено с восемью известными
    ответами»; такой сверки в гейтах не было НИ ОДНОЙ.

    Вторая половина: любое имя, опубликованное в указателе, обязано быть либо
    в снимке, либо в этой таблице стандарта, либо тем же именем снимка без
    фирменной буквы впереди (EPX625 -> PX625). Больше взяться ему неоткуда.
    """
    import cells as C
    bad = []
    for code, want in IEC_KNOWN:
        got = C.full_iec_code({"code": code})
        if got != want:
            bad.append("полная форма %s: получено %s, известный ответ %s"
                       % (code, got or "ничего", want or "ничего"))
    if bad:
        return bad

    import prose as P
    rows = _payload(files)
    if rows is None:
        return bad + ["блок данных поиска отсутствует или не разбирается"]
    if len(rows) < 100:
        bad.append("в указателе имён %d — гейту нечего проверять" % len(rows))
    standard = {v for _k, v in IEC_KNOWN if v}
    marks = {m.upper() for m, _t, _w in C.TRADE_MARKINGS}
    household = {s.upper() for s in P.POPULAR_SIZES}
    for r in rows:
        name, kind = r["name"], r["kind"]
        if kind == "0":
            # Обиходное имя или подпись оболочки. Подпись обязана СЛОЖИТЬСЯ
            # из собственного габарита строки, а не быть набрана отдельно.
            if name.upper() in household:
                continue
            if r["dims"] and name == r["dims"].replace("x", " x ") + " mm":
                continue
            bad.append("«%s» выдаёт себя за размер, но ни обиходное имя, "
                       "ни подпись собственного габарита" % name)
            continue
        if kind == "3":
            # Торговая маркировка. Она обязана быть В ТАБЛИЦЕ и обязана НЕ
            # быть в снимке: наш источник её не печатает, и объявлять её
            # обозначением значит выдумать факт.
            if name.upper() not in marks:
                bad.append("«%s» выдаёт себя за торговую маркировку, а в "
                           "таблице её нет" % name)
            elif _in_snapshot(name):
                bad.append("«%s» названо торговой маркировкой, а оно стоит "
                           "в снимке производителя" % name)
            continue
        if name.upper() in standard or _in_snapshot(name) \
                or _in_snapshot("E" + name):
            continue
        bad.append("«%s» опубликовано, но не прослеживается ни до снимка, "
                   "ни до стандарта" % name)
    return bad[:20]


def g_index_keys_unique(files):
    """Указатель свёрнут по одному ключу, и его длина ПОСЧИТАНА, а не набрана.

    На /codes/ стояло 717 строк при 715 обозначениях: «15-LF» и «15LF»
    оставались двумя строками, и одна вела на страницу элемента, а вторая в
    витрину оболочки — выбор из одного, притворяющийся выбором из двух.
    Свёртка, число в подводке, число на главной и длина поискового указателя
    обязаны быть одной величиной.
    """
    bad = []
    codes = files.get("codes/index.html", "")
    keys = re.findall(r'data-k="([^"]*)"', codes)
    lis = re.findall(r"<li[ >]", codes)
    if not keys:
        bad.append("в указателе кодов нет ни одной строки")
        return bad
    counts = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1
    dup = sorted(k for k, v in counts.items() if v > 1)
    if dup:
        bad.append("ключи повторяются: %s" % ", ".join(dup[:6]))
    if len(lis) != len(keys):
        bad.append("строк %d, ключей %d" % (len(lis), len(keys)))
    m = re.search(r'<p class="bx-lead">(\d+) entr', codes)
    if not m:
        bad.append("указатель не называет своей длины")
    elif int(m.group(1)) != len(keys):
        bad.append("указатель обещает %s, строк %d" % (m.group(1), len(keys)))

    home = files.get("index.html", "")
    m2 = re.search(r"the list of <a[^>]*>(\d+) codes", home)
    if not m2:
        bad.append("главная не называет числа кодов")
    elif int(m2.group(1)) != len(keys):
        bad.append("главная обещает %s кодов, в указателе %d"
                   % (m2.group(1), len(keys)))

    rows = _payload(files)
    if rows is None:
        bad.append("блок данных поиска отсутствует или не разбирается")
        return bad[:20]
    # Поиск ЗНАЕТ БОЛЬШЕ указателя кодов, и ровно на то, что объявлено:
    # обиходные имена, витрины оболочек и торговые маркировки. Всё, что
    # шире этого, — имя, взявшееся ниоткуда.
    codes = {_key(r["name"]) for r in rows if r["kind"] in ("1", "2")}
    extra = {_key(r["name"]) for r in rows if r["kind"] in ("0", "3")}
    if codes != set(keys):
        only_i = sorted(set(keys) - codes)[:4]
        only_s = sorted(codes - set(keys))[:4]
        bad.append("указатель и поиск разошлись именами: только в указателе "
                   "%s, только в поиске %s" % (only_i, only_s))
    if len(codes) != len(keys):
        bad.append("в поиске обозначений %d, в указателе %d"
                   % (len(codes), len(keys)))
    if not extra:
        bad.append("поиск не знает ни одного обиходного имени — пустая "
                   "выборка это провал")
    if extra & codes:
        bad.append("имя заведено дважды: %s" % sorted(extra & codes)[:4])
    return bad[:20]


def _volts_column(table):
    """Значения колонки напряжения таблицы, или None, если её нет."""
    head = re.search(r"<thead>\s*<tr[^>]*>(.*?)</tr>", table, re.S)
    body = re.search(r"<tbody>(.*?)</tbody>", table, re.S)
    if not head or not body:
        return None
    names = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip().lower()
             for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>",
                                 head.group(1), re.S)]
    idx = None
    for want in ("volts", "voltage"):
        if want in names:
            idx = names.index(want)
            break
    if idx is None:
        return None
    vals = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S):
        cs = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
        if len(cs) == len(names):
            vals.append(re.sub(r"\s+", " ",
                               re.sub(r"<[^>]+>", " ", cs[idx])).strip())
    return vals


def g_completeness_claim_counted(files):
    """«Every one of them delivers X» печатается только из ПОСЧИТАННОГО.

    Множество напряжений строилось по тем участникам, У КОГО напряжение есть,
    а фраза утверждала обо ВСЕХ: /size/f/ обещала «every one of them delivers
    1.5 V» прямо над строкой, в которой напряжения не было вовсе.
    Утверждение о полноте — величина, а не оборот речи.
    """
    bad, seen = [], 0
    for p, t in sorted(_html(files).items()):
        vis = _text(t)
        claim = "every one of them delivers" in vis
        for table in re.findall(r"<table[^>]*>.*?</table>", t, re.S):
            vals = _volts_column(table)
            if vals is None:
                continue
            seen += 1
            silent = [v for v in vals if not re.search(r"\d", v)]
            if claim and silent:
                bad.append("%s: обещано «every one of them delivers», а без "
                           "цифры %d строк" % (p, len(silent)))
    if not seen:
        bad.append("гейт не нашёл ни одной таблицы с колонкой напряжения")
    return bad[:20]


def g_chem_note_volts_from_page(files):
    """Число в заметке о химии стоит в ЯЧЕЙКЕ той же страницы.

    В шаблоне было набрано «1.35 V» для ртути, и оно спорило с собственными
    данными сайта на двенадцати страницах: та же страница печатала 1,4 В в
    таблице, а 17 ртутных записей снимка из 24 несут 1,4 В и ровно одна 1,35.
    Число в прозе печатается ТОЛЬКО из записи, и запись видна тут же.
    """
    bad, notes = [], 0
    for p, t in sorted(_cells(files).items()):
        vals = set()
        for m in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", t, re.S):
            vals |= set(re.findall(r"(\d+(?:\.\d+)?) V",
                                   re.sub(r"<[^>]+>", " ", m.group(1))))
        blk = re.search(r"<h2>What the chemistry changes</h2>(.*?)</ul>",
                        t, re.S)
        if not blk:
            continue
        for note in re.findall(r"<li><b>[^<]*</b>(.*?)</li>", blk.group(1),
                               re.S):
            notes += 1
            for v in re.findall(r"(\d+(?:\.\d+)?) V", note):
                if v not in vals:
                    bad.append("%s: заметка о химии говорит %s V, а в "
                               "таблицах страницы такого значения нет"
                               % (p, v))
    if notes < 20:
        bad.append("гейт прочитал заметок о химии: %d — выборка пуста или "
                   "разметка сменилась" % notes)
    return bad[:20]


# Обороты, которыми сайт говорил за весь мир, читая каталог ОДНОГО
# производителя. Каждый воспроизведён из выкладки: «no longer made anywhere»
# на 4 страницах, «nothing reproduces that voltage» на 12, голое «Nothing
# shares this exact size» на 24 — при том что соседние формулировки того же
# факта были ограничены данными («nothing in its catalog shares this size»).
WORLD_CLAIMS = (
    r"no longer made anywhere",
    r"not made anywhere",
    r"nothing reproduces that voltage",
    r"Nothing shares this exact size",
    r"Nothing is this exact size",
    r"nothing on the market",
    # «not that nobody makes the cell» — это ОТРИЦАНИЕ мирового утверждения и
    # лучший абзац на сайте. Ловится только неотрицанная форма.
    r"(?<!not that )nobody makes",
    r"(?<!not that )no one makes",
    r"the only cell that",
    # Оговорка «current» относилась к КАТАЛОГУ, но читалась как «сейчас в
    # мире не делают такой глубины»: фраза стояла на 54 живых страницах, и
    # различить два прочтения по ней было нельзя. Теперь называется источник.
    r"Nothing current is the same",
    r"Nothing in this shell holds more",
)


def g_claims_scoped_to_data(files):
    """Ни одного утверждения о МИРЕ: сайт читает каталог одного производителя.

    «The chemistry is banned and nothing reproduces that voltage» стояло на 12
    страницах, тогда как воздушно-цинковые на 1,4 В лежат в СОБСТВЕННЫХ данных
    сайта. Одна и та же мысль имела три формулировки, и одна из трёх была
    безоговорочной. Область утверждения — часть утверждения.
    """
    bad = []
    pages = _html(files)
    if not pages:
        bad.append("гейту нечего читать: страниц нет")
    for p, t in sorted(pages.items()):
        vis = _text(t)
        for phrase in WORLD_CLAIMS:
            m = re.search(phrase, vis, re.I)
            if m:
                bad.append("%s: «%s» — утверждение обо всём мире"
                           % (p, m.group(0)))
    return bad[:20]


# --------------------------------------------------- напряжение и его шкала

# Известные ответы для чистых функций. Считаны РУКАМИ по определению классов,
# опубликованному на /method/, а не выведены из тех же функций: гейт, сверяющий
# вывод с породившей его функцией, соглашается сам с собой и остаётся зелёным,
# когда функцию ломают.
V_KNOWN = [
    # (напряжение в руках, напряжение кандидата, процент, класс, место штриха)
    (1.5, 1.5, 0.0, "same", 50.0),
    (1.5, 1.53, 2.0, "same", 52.4),
    (1.5, 1.55, 3.3, "minor", 54.0),
    (1.5, 1.45, -3.3, "minor", 45.0),
    (1.5, 1.59, 6.0, "minor", 57.2),
    (1.5, 1.35, -10.0, "calibration", 35.0),
    (1.5, 1.2, -20.0, "calibration", 20.0),
    (9.0, 7.2, -20.0, "calibration", 20.0),
    (1.5, 1.19, -20.7, "wrong", 19.6),
    (1.5, 3.0, 100.0, "wrong", 87.5),
    (1.5, 12.0, 700.0, "wrong", 98.1),
    (9.0, 3.0, -66.7, "wrong", 5.0),
    # ОБРАТНАЯ СТОРОНА КАЖДОЙ ПАРЫ, посчитанная руками по тому же правилу:
    # класс решается разрывом, отнесённым к БОЛЬШЕМУ номиналу, и потому у
    # пары он один. 1,2 против 1,5 — это 0,3 В, то есть 20% от 1,5 с любой
    # стороны, хотя от 1,2 тот же разрыв печатается как +25,0%.
    (1.2, 1.5, 25.0, "calibration", 80.0),
    (7.2, 9.0, 25.0, "calibration", 80.0),
    (1.19, 1.5, 26.1, "wrong", 80.2),
    (3.0, 1.5, -50.0, "wrong", 8.6),
    (1.53, 1.5, -2.0, "same", 47.0),
    (1.55, 1.5, -3.2, "minor", 45.2),
]


def g_volt_functions_known_answers(files):
    """Две функции, из которых берётся ВСЁ про напряжение, проверены
    известными ответами, монотонностью и разрешающей способностью.

    Отношение считается ОДНОЙ функцией, класс — ОДНОЙ. До этого граница
    сравнивалась с долей, и одно и то же напечатанное «-20,0%» уезжало в
    «wrong class» на 14 строках и в «reads off» на 3: 1,2 против 1,5 даёт
    -0.20000000000000004, а 7,2 против 9 даёт -0.19999999999999998.
    """
    import cells as Cx
    bad = []
    # Известные ответы — выборка этого гейта, и проверять их стоит ровно
    # потому, что из этих функций печатаются страницы: пустая выкладка
    # значит, что проверенная арифметика никуда не поехала.
    _sample(bad, len(V_KNOWN), "известных ответов")
    _sample(bad, len(_cells(files)), "страниц элементов")
    if not V_KNOWN:
        return bad + ["таблица известных ответов пуста"]
    for base, other, pct, klass, pos in V_KNOWN:
        r = Cx.signed_ratio(base, other)
        if r is None:
            bad.append("%s -> %s: отношение не посчитано" % (base, other))
            continue
        if Cx.signed_pct(r) != pct:
            bad.append("%s -> %s: процент %s, ожидался %s"
                       % (base, other, Cx.signed_pct(r), pct))
        if Cx.consequence_class(r) != klass:
            bad.append("%s -> %s: класс %s, ожидался %s"
                       % (base, other, Cx.consequence_class(r), klass))
        if abs(Cx.scale_position(r) - pos) > 0.05:
            bad.append("%s -> %s: штрих на %s, ожидался %s"
                       % (base, other, Cx.scale_position(r), pos))
    # Направление: знак обязан следовать за данными, а не за словом в шаблоне.
    if not (Cx.signed_ratio(1.5, 1.2) < 0 < Cx.signed_ratio(1.2, 1.5)):
        bad.append("знак отношения не следует за направлением")
    # ГРАНИЦА РЕШАЕТСЯ ПО НАПЕЧАТАННОЙ ЦИФРЕ, А НЕ ПО ДВОИЧНОМУ ХВОСТУ.
    # 1,2 против 1,5 без округления даёт меру пары 20.000000000000004 —
    # больше границы на одну шестнадцатую триллионной, и по «сырому» числу
    # 37 пар снимка уехали бы из «показания уплывут» в «другой класс, не
    # замена». Сначала проверяется, что хвост ЕСТЬ (иначе проба перестала
    # что-либо доказывать), потом — что класс за ним не пошёл.
    raw = (1.5 - 1.2) / 1.2 * 100.0
    if not raw / (1.0 + raw / 100.0) > Cx.V_SERIOUS_PCT:
        bad.append("проба границы устарела: неокруглённая мера пары 1,2/1,5 "
                   "больше не выходит за %s%%" % Cx.V_SERIOUS_PCT)
    # Печатаемая цифра решает по обе стороны границы и в обе стороны знака:
    # -20.049% печатается как «-20.0%», -20.051% — как «-20.1%».
    for r, klass, why in ((Cx.signed_ratio(1.2, 1.5), "calibration",
                           "мера пары печатается как 20.0%"),
                          (Cx.signed_ratio(1.5, 1.2), "calibration",
                           "та же пара с другой стороны"),
                          (-0.20049, "calibration", "печатается как -20.0%"),
                          (-0.20051, "wrong", "печатается как -20.1%"),
                          (0.2504, "calibration", "печатается как +25.0%"),
                          (0.2506, "wrong", "печатается как +25.1%")):
        got = Cx.consequence_class(r)
        if got != klass:
            bad.append("отношение %s: класс «%s», ожидался «%s» — %s"
                       % (r, got, klass, why))
    # Край класса — величина, а не набранная константа: на нём стоит и зона
    # дорожки, и текст под ней, и обе половины обязаны брать его отсюда.
    if abs(Cx.class_edge(-1) * 100.0 + Cx.V_SERIOUS_PCT) > 1e-9:
        bad.append("нижний край класса %s, ожидался %s"
                   % (Cx.class_edge(-1), -Cx.V_SERIOUS_PCT / 100.0))
    if abs(Cx.class_edge(1) - 0.25) > 1e-9:
        bad.append("верхний край класса %s, ожидался 0.25" % Cx.class_edge(1))
    # СИММЕТРИЯ КЛАССА ПО ПАРЕ на всех напряжениях снимка. Пара 1,2 и 1,5
    # получала «reads off» с одной страницы и «wrong class» с другой — одно
    # физическое отношение и две противоположные рекомендации.
    vs = sorted({v for row in V_KNOWN for v in row[:2]})
    _sample(bad, len(vs), "напряжений известных ответов")
    seen_pairs = 0
    for a in vs:
        for b in vs:
            if a == b:
                continue
            seen_pairs += 1
            ka = Cx.consequence_class(Cx.signed_ratio(a, b))
            kb = Cx.consequence_class(Cx.signed_ratio(b, a))
            if ka != kb:
                bad.append("%s против %s даёт «%s», а обратно «%s»"
                           % (a, b, ka, kb))
    _sample(bad, seen_pairs, "взаимных пар напряжений")
    # Монотонность места штриха по всей оси и в обе стороны.
    prev = None
    for i in range(-99, 1000):
        p = Cx.scale_position(i / 100.0)
        if prev is not None and p < prev - 1e-9:
            bad.append("место штриха не монотонно на %d%%" % i)
            break
        prev = p
    # Разрешающая способность: 3% и 700% обязаны разъезжаться по дорожке.
    d = abs(Cx.scale_position(7.0) - Cx.scale_position(0.03))
    if d < 20.0:
        bad.append("3%% и 700%% расходятся на %.1f пункта дорожки" % d)
    # Полоса и центр — из тех же величин.
    if Cx.scale_position(0.0) != 50.0:
        bad.append("центр оси не в середине дорожки")
    return bad[:20]


_VCELL = re.compile(r'class="bx-v bx-v-([a-z]+)"[^>]*>(.*?)'
                    r'<span class="bx-vtag">([^<]*)</span>', re.S)


def g_volt_tag_matches_pct(files):
    """Метка последствия ПЕРЕСЧИТАНА из процента, напечатанного рядом с ней.

    Один и тот же «-20.0%» стоял с меткой «wrong class» на 14 строках и
    «reads off» на 3. Гейт читает разметку и требует, чтобы класс в имени
    стиля, слово метки и напечатанное число были одним и тем же ответом.
    Дополнительно на страницах элементов процент пересчитывается из ДВУХ
    напряжений, напечатанных на той же странице.
    """
    import cells as Cx
    bad, seen = [], 0
    for p, t in _html(files).items():
        body = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        mine = re.search(r'<span class="bx-val">([\d.]+)</span>'
                         r'<span class="bx-unit">V</span>', body)
        base = float(mine.group(1)) if mine else None
        # НАПРАВЛЕНИЕ — СВОЙСТВО САЙТА, а не таблицы. Здесь стоял разбор
        # таблиц по шапке: «Voltage» меряет от этого элемента, «Voltage
        # shift» — от снятого, и строки второй из сверки ИСКЛЮЧАЛИСЬ. Ровно
        # в них и жил дефект: процент от снятого рядом с напряжением
        # снятого. Рамка теперь одна, и сверяется КАЖДАЯ ячейка страницы.
        for m in _VCELL.finditer(body):
            klass, printed, tag = m.group(1), _text(m.group(2)), m.group(3)
            seen += 1
            if klass == "unknown":
                if "%" in printed:
                    bad.append("%s: класс unknown при напечатанном проценте" % p)
                continue
            pm = re.search(r"([-+−]?\d+(?:\.\d+)?)\s*%", printed)
            if not pm:
                bad.append("%s: метка «%s» без напечатанного процента"
                           % (p, tag))
                continue
            pct = float(pm.group(1).replace("−", "-"))
            want = Cx.consequence_class(pct / 100.0)
            if want != klass:
                bad.append("%s: %s%% помечено «%s», а это «%s»"
                           % (p, pct, klass, want))
            if P.V_TAG.get(klass) != tag:
                bad.append("%s: класс %s подписан «%s»" % (p, klass, tag))
            vm = re.search(r"([\d.]+)\s*V", printed)
            if base and vm:
                got = Cx.signed_pct(Cx.signed_ratio(base, float(vm.group(1))))
                # Печатается без десятой доли начиная с сотни процентов.
                if abs(got) >= 100:
                    ok = abs(round(got) - pct) < 0.51
                else:
                    ok = abs(got - pct) < 0.051
                if not ok:
                    bad.append("%s: %s V против %s V даёт %s%%, напечатано %s%%"
                               % (p, vm.group(1), base, got, pct))
    if seen < 100:
        bad.append("ячеек с классом напряжения найдено %d — выборка пуста или "
                   "разметка изменилась" % seen)
    return bad[:20]


def g_scale_encodes_ratio(files):
    """Шкала КОДИРУЕТ отклонение, а не рисует одну и ту же картинку.

    Полоса стояла как left:0;right:0 на всех 57 страницах со шкалой, а 133
    штриха из 160 — ровно на 0% или 100%, потому что ось нормировалась на
    min и max набора самой страницы: 3% и 700% выходили одинаковыми.

    Гейт пересчитывает КАЖДЫЙ штрих из двух напряжений, напечатанных на той
    же странице, требует, чтобы ось была НАЗВАНА, и чтобы полоса стояла на
    границе класса.
    """
    import cells as Cx
    bad, seen = [], 0
    # Края зоны спрашиваются у функции класса: мера класса симметрична по
    # ПАРЕ, а не по этому элементу, и потому вниз граница -20%, вверх +25%.
    lo = Cx.scale_position(Cx.class_edge(-1))
    hi = Cx.scale_position(Cx.class_edge(1))
    for p, t in _html(files).items():
        body = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        for m in re.finditer(r'<div class="bx-scale-v"[^>]*aria-label="'
                             r'([^"]*)">(.*?)</p></div>', body, re.S):
            seen += 1
            label, guts = m.group(1), m.group(2)
            base = re.search(r"sits from this one at ([\d.]+) V", label)
            if not base:
                bad.append("%s: шкала не называет напряжение этого элемента" % p)
                continue
            v = float(base.group(1))
            pairs = re.findall(r"([\d.]+) V at ([-+−]?[\d.]+)%", label)
            if not pairs:
                bad.append("%s: шкала не называет ни одного соседа" % p)
                continue
            want = []
            for pv, pct in pairs:
                r = Cx.signed_ratio(v, float(pv))
                got = Cx.signed_pct(r)
                shown = float(pct.replace("−", "-"))
                if abs(got) >= 100:
                    ok = abs(round(got) - shown) < 0.51
                else:
                    ok = abs(got - shown) < 0.051
                if not ok:
                    bad.append("%s: %s V против %s V даёт %s%%, названо %s%%"
                               % (p, pv, v, got, shown))
                want.append(round(Cx.scale_position(r), 1))
            got_pins = [float(x) for x in
                        re.findall(r'class="bx-scale-pin bx-scale-pin-off" '
                                   r'style="left:([\d.]+)%"', guts)]
            if sorted(got_pins) != sorted(want):
                bad.append("%s: штрихи на %s, а из напряжений выходит %s"
                           % (p, sorted(got_pins), sorted(want)))
            here = re.findall(r'class="bx-scale-pin" style="left:([\d.]+)%"',
                              guts)
            if here != ["%.1f" % Cx.scale_position(0.0)]:
                bad.append("%s: штрих этого элемента не в центре оси: %s"
                           % (p, here))
            band = re.search(r'class="bx-scale-band" '
                             r'style="left:([\d.]+)%;right:([\d.]+)%"', guts)
            if not band:
                bad.append("%s: у дорожки нет размеченной зоны класса" % p)
            elif (abs(float(band.group(1)) - lo) > 0.05
                  or abs(float(band.group(2)) - (100.0 - hi)) > 0.05):
                bad.append("%s: зона класса не на границе класса: %s"
                           % (p, band.group(0)))
            note = re.search(r'<p class="bx-scale-note">(.*)$', guts, re.S)
            said = _text(note.group(1)) if note else ""
            for phrase in ("The axis is the difference from this cell",
                           "%s%%" % P.pct_num(Cx.V_SERIOUS_PCT),
                           # Оговорка о ВЗАИМНОСТИ стоит там же, где числа:
                           # без неё читатель видит «+25.0%» с меткой класса,
                           # чья граница на той же странице названа 20%.
                           "of the higher of the two nominals",
                           "%s%% above" % P.pct_num(
                               abs(Cx.class_edge(1)) * 100.0),
                           "compressed"):
                if phrase not in said:
                    bad.append("%s: ось не названа на странице (%s)"
                               % (p, phrase))
    if seen < 30:
        bad.append("шкал найдено %d — выборка пуста или разметка изменилась"
                   % seen)
    return bad[:20]


# Слова, которыми сайт выносит вердикт ПОСАДКИ. Список набран здесь, а не
# импортирован из шаблонов: гейт, читающий свой словарь у проверяемого, — это
# проверка вывода функции ею же самой. Ниже стоит сверка: каждое слово из
# prose.FIT_WORD обязано быть в этом списке, иначе новое слово проедет мимо.
FIT_CLAIM_WORDS = ("drops straight in", "drop into the same", "drop in",
                   "drops in", "goes in and stands shorter", "sits lower",
                   "is too tall to close", "too tall", "is too wide to enter",
                   "too wide", "is too narrow to hold contact", "too narrow",
                   "drop-in", "fits", "fit this slot", "fit the same slot",
                   "takes the same slot", "take the same slot")
# «Are the same size» намеренно НЕ здесь: это фраза о размерах, а не вердикт
# посадки, и на /method/ она объясняет буквы обозначения, ничего не предлагая.
# Область правила — вердикт, а вердикт этот сайт выносит словами выше.

# Чем сентенция имеет право доказать, что назвала последствие: числом вольт,
# процентом, меткой класса или прямым «не публикуется».
_VOLT_EVIDENCE = re.compile(
    r"\d[\d.]*\s*V\b|[-+−]?\d[\d.]*\s*%|not published|"
    + "|".join(re.escape(x) for x in sorted(P.V_TAG.values())))


def _designations():
    """Обозначения, прочитанные С ДИСКА из снимка производителя.

    Список кодов, взятый у генератора, сделал бы гейт проверкой генератора
    самим собой. Берём независимый источник и оставляем только то, что нельзя
    спутать с обычным словом: не короче трёх знаков и с цифрой внутри.
    """
    out = set()

    def add(x):
        x = (x or "").strip().upper()
        if len(x) >= 3 and re.search(r"\d", x)                 and re.match(r"^[A-Z0-9][A-Z0-9./-]*$", x):
            out.add(x)

    for rec in _snapshot():
        for k in ("battery-iec", "post_title", "battery-ansi", "aliases"):
            v = rec.get(k)
            if isinstance(v, list):
                for y in v:
                    add(y)
            elif isinstance(v, str):
                for y in re.split(r"[,;]| or ", v):
                    add(y)
    return out


def g_fit_claim_carries_voltage(files):
    """В ПРОЗЕ слово о посадке не выходит без последствия по напряжению.

    ОБЛАСТЬ: видимый текст ВНЕ таблиц, на всех типах страниц. Прежний гейт
    смотрел только на строки таблиц, и двадцать восемь страниц вели абзацем
    «The closest listed cell, A27, fits but sits lower» при переходе 1,5 -> 12
    вольт. Правило было верным, множество — не тем.
    """
    missing = [w for w in P.FIT_WORD.values()
               if w.lower() not in FIT_CLAIM_WORDS]
    if missing:
        return ["слово вердикта посадки не заведено в гейте: %s"
                % ", ".join(missing)]
    codes = _designations()
    if len(codes) < 100:
        return ["обозначений из снимка прочитано %d — источник не тот"
                % len(codes)]
    crx = re.compile("|".join(
        r"(?<![A-Za-z0-9.\-])%s(?![A-Za-z0-9.\-])" % re.escape(c)
        for c in sorted(codes, key=len, reverse=True)))
    bad, seen = [], 0
    for p, t in _html(files).items():
        # Голова страницы убирается вместе со скриптами и стилями: напряжение
        # из <title> закрывало собой голый вердикт в абзаце ниже, и нарочная
        # поломка не краснела. Таблицы тоже: их строки проверяет
        # g_fit_and_volts_separate, и области двух гейтов объявлены раздельно.
        body = re.sub(r"<head.*?</head>|<script.*?</script>"
                      r"|<style.*?</style>|<table.*?</table>",
                      " ", t, flags=re.S)
        for blk in re.finditer(r"<(p|li|h1|h2|h3|figcaption)\b[^>]*>(.*?)</\1>",
                               body, re.S):
            vis = (_text(blk.group(2)).replace("&mdash;", "—")
                   .replace("&rsquo;", "'").replace("&minus;", "−"))
            for sent in re.split(r"(?<=[.!?])\s+", vis):
                low = sent.lower()
                if not any(w in low for w in FIT_CLAIM_WORDS):
                    continue
                if not crx.search(sent):
                    continue
                seen += 1
                if not _VOLT_EVIDENCE.search(sent):
                    bad.append("%s: вердикт посадки без напряжения: %s"
                               % (p, sent.strip()[:110]))
    if seen < 50:
        bad.append("предложений с вердиктом посадки найдено %d — выборка "
                   "пуста или словарь разошёлся с шаблонами" % seen)
    return bad[:20]



# Сколько видимых слов обязано стоять НАД первым объявлением и ПОД ним.
# Верхняя половина — это ответ, ради которого человек пришёл; нижняя —
# доказательство, что коробка не пришита к подвалу.
AD_WORDS_ABOVE, AD_WORDS_BELOW = 60, 60

# Один и тот же скелет описания больше чем на стольких страницах — это уже не
# расчёт, а подстановка кода в общую фразу.
DESC_SKELETON_MAX = 12

# Поля, которых у этого сайта НЕТ и которые поэтому не имеют права появиться
# в машиночитаемом виде: рейтингов никто не ставил, автора у страницы нет,
# цены сайт не знает, изготовитель у обозначения не один.
LD_FORBIDDEN = ("aggregateRating", "review", "offers", "price", "author",
                "datePublished", "brand", "manufacturer", "sku", "gtin")


def _main_col(html):
    """Основная колонка без шапки, подвала и боковой.

    Считается ГЛУБИНОЙ вложенности, а не первым закрывающим тегом: внутри
    колонки десятки div, и «до первого </div>» дало бы пустую выборку, а
    пустая выборка у нас однажды уже печатала «пройден».
    """
    key = '<div class="bx-main">'
    i = html.find(key)
    if i < 0:
        return None
    j, depth = i + len(key), 1
    for m in re.finditer(r"<div\b|</div>", html[j:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return html[j:j + m.start()]
    return None


def _path_of(p):
    return "/" + (p[:-len("index.html")] if p.endswith("index.html") else p)


def _no_chrome(html):
    """Колонка без обстановки: без рекламных коробок и без поля поиска.

    Собственный текст объявления не имеет права оправдывать его присутствие —
    это правило уже было. Поле поиска встало на все 166 страниц и принесло с
    собой сорок слов подписи; они ровно такая же обстановка, и считать их
    содержимым значит завести инвентарь на странице, где читать нечего.
    """
    html = re.sub(r'<div class="bx-ad .*?</div>', " ", html, flags=re.S)
    return re.sub(r'<form class="bx-find.*?</form>', " ", html, flags=re.S)


def _visible(html):
    """Видимые слова. Стиль и скрипт вычищаются ВМЕСТЕ: иначе
    «text-align:right» считается словом «right», а их под тысячу."""
    return P.wc(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                       flags=re.S))


def g_ad_inventory_by_content(files):
    """Инвентарь заводится по СОДЕРЖИМОМУ страницы, а не по её типу.

    Сайт живёт с рекламы и уезжал без единого места: флаг снимал разметку, а
    гейт стоял внутри того же условия и был структурно неспособен покраснеть.
    Теперь решение принимает одна функция, и здесь оно сверяется с ОТДАННОЙ
    разметкой в обе стороны: страница, которой хватает содержимого, обязана
    нести место, а страница из запретного списка — не нести никогда.

    Функция проверяется ИЗВЕСТНЫМИ ОТВЕТАМИ, а не только собственным выводом:
    гейт, сверяющий вывод с той же функцией, которая его и посчитала, у нас
    уже был зелёным на сломанном сайте.
    """
    import render as rd
    bad = []
    long_body = "<p>%s</p>" % " ".join(["word"] * (rd.AD_MIN_WORDS + 40))
    edge_body = "<p>%s</p>" % " ".join(["word"] * rd.AD_MIN_WORDS)
    thin_body = "<p>%s</p>" % " ".join(["word"] * (rd.AD_MIN_WORDS - 1))
    for path, body, want in (("/lr44/", long_body, True),
                             ("/lr44/", edge_body, True),
                             ("/lr44/", thin_body, False),
                             ("/privacy/", long_body, False),
                             ("/404.html", long_body, False),
                             ("/terms/", long_body, False)):
        if bool(rd.carries_ads(path, body)) is not want:
            bad.append("известный ответ разошёлся: carries_ads(%s, %d слов) "
                       "не %s" % (path, rd.visible_words(body), want))
    # ОБЛАСТЬ: страницы сайта. У виджета нет основной колонки и нет рекламы
    # по построению; что он её не несёт, проверяет g_embeds_are_fragments.
    pages = _site_pages(files)
    if not pages:
        return bad + ["страниц ноль — пустая выборка это провал"]
    with_ad = 0
    for p, t in sorted(pages.items()):
        main = _main_col(t)
        if main is None:
            bad.append("%s: основная колонка не нашлась" % p)
            continue
        # Слова считаются БЕЗ обстановки: ни собственный текст коробки, ни
        # подпись поля поиска не имеют права оправдывать её присутствие.
        body = _no_chrome(main)
        has = 'class="bx-ad ' in t
        want = rd.carries_ads(_path_of(p), body)
        if want and not has:
            bad.append("%s: %d слов и ни одного места"
                       % (p, rd.visible_words(body)))
        elif has and not want:
            bad.append("%s: место есть, а содержимого под него нет (%d слов)"
                       % (p, rd.visible_words(body)))
        with_ad += 1 if has else 0
    if not with_ad:
        bad.append("ни одного места на %d страницах — сайт живёт с рекламы, и "
                   "отсутствие инвентаря это провал" % len(pages))
    if with_ad == len(pages):
        bad.append("места на всех %d страницах без исключения — значит "
                   "запретный список не работает" % len(pages))
    return bad[:20]


def g_ad_below_the_answer(files):
    """Ответ ВЫШЕ первого объявления на каждом типе страниц.

    Место в потоке уже уезжало в самый хвост: метки в разметке не стояло, а
    запасной путь дописывал коробку в конец — под блоком методики, где она не
    стоит ничего и где над ней уже нет вопроса, ради которого страницу
    открыли. Проверяется не «есть место», а ГДЕ оно: подводка выше него,
    слова выше и слова ниже.
    """
    bad, seen = [], 0
    for p, t in sorted(_html(files).items()):
        main = _main_col(t)
        if main is None:
            continue
        i = main.find("bx-ad bx-ad-flow")
        if i < 0:
            if "bx-ad bx-ad-tower" in t:
                bad.append("%s: башня есть, а места в потоке нет" % p)
            continue
        seen += 1
        lead = main.find('<p class="bx-lead">')
        if lead < 0 or lead > i:
            bad.append("%s: объявление стоит выше подводки" % p)
        above = _visible(_no_chrome(main[:i]))
        below = _visible(_no_chrome(main[i:]))
        if above < AD_WORDS_ABOVE:
            bad.append("%s: над объявлением %d слов, нужно %d"
                       % (p, above, AD_WORDS_ABOVE))
        if below < AD_WORDS_BELOW:
            bad.append("%s: под объявлением %d слов — коробка пришита к "
                       "подвалу" % (p, below))
        if "bx-ad bx-ad-tower" in main:
            bad.append("%s: башня стоит в основной колонке, а не в боковой" % p)
    if not seen:
        bad.append("ни одной страницы с местом в потоке — пустая выборка это "
                   "провал, а не «пройден»")
    return bad[:20]


def g_public_contact_own_domain(files):
    """Публичный адрес — на СВОЁМ домене, и ящик поддержки платящих клиентов
    не появляется на страницах рекламного сайта ни разу.

    Он стоял в подвале 331 раз: письмо про даташит падало бы туда, где лежат
    просьбы о лицензионном ключе, а домен студии оказывался публично связан с
    рекламной собственностью. Имя юридического лица — другое дело: §8 требует
    названного издателя, и «BiLingoPlus LLC» остаётся.
    """
    bad, seen = [], 0
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r'href="mailto:([^"]*)"', t):
            seen += 1
            addr = m.group(1)
            if not addr.endswith("@" + DOMAIN):
                bad.append("%s: публичный адрес %s не на своём домене"
                           % (p, addr))
        low = t.lower()
        if "bilingoplus.com" in low or "@bilingoplus" in low:
            bad.append("%s: на странице назван домен или ящик студии" % p)
    if not seen:
        bad.append("ни одного публичного адреса на сайте — пустая выборка это "
                   "провал")
    return bad[:20]


def g_share_cards(files):
    """Карточка ссылки есть везде и НЕ РАСХОДИТСЯ с головой страницы.

    Заголовок и описание печатаются теперь в двух местах. Два места, где
    написано одно и то же, расходятся — поэтому гейт сверяет их знак в знак,
    а не проверяет наличие. Отдельно: `og:image` объявлять НЕЧЕМ — растровых
    изображений на сайте нет ни одного, — и карточка обязана быть `summary`.
    Объявленная картинка, которой нет, разворачивается пустой рамкой.
    """
    bad, seen = [], 0
    # ОБЛАСТЬ: страницы сайта. Виджет ссылкой не делятся — им делятся
    # встраиванием, и карточка ему не нужна.
    for p, t in sorted(_site_pages(files).items()):
        seen += 1
        head = t[:t.find("</head>")]

        def one(pat):
            m = re.search(pat, head)
            return m.group(1) if m else None

        title = one(r"<title>(.*?)</title>")
        desc = one(r'<meta name="description" content="([^"]*)"')
        canon = one(r'<link rel="canonical" href="([^"]*)"')
        pairs = ((r'<meta property="og:title" content="([^"]*)"', title),
                 (r'<meta property="og:description" content="([^"]*)"', desc),
                 (r'<meta property="og:url" content="([^"]*)"', canon),
                 (r'<meta name="twitter:title" content="([^"]*)"', title),
                 (r'<meta name="twitter:description" content="([^"]*)"', desc))
        for pat, want in pairs:
            got = one(pat)
            if got is None:
                bad.append("%s: нет метки %s" % (p, pat[13:30]))
            elif got != want:
                bad.append("%s: карточка разошлась с головой: «%s» против "
                           "«%s»" % (p, got[:40], (want or "")[:40]))
        card = one(r'<meta name="twitter:card" content="([^"]*)"')
        if card != "summary":
            bad.append("%s: карточка объявлена как %s, а картинки у сайта нет"
                       % (p, card))
        if not one(r'<meta property="og:site_name" content="([^"]*)"'):
            bad.append("%s: карточка без имени сайта" % p)
        if not one(r'<meta property="og:type" content="([^"]*)"'):
            bad.append("%s: карточка без типа" % p)
        img = one(r'<meta property="og:image" content="([^"]*)"')
        if img is not None:
            ref = img.split("https://%s" % DOMAIN)[-1].lstrip("/")
            if ref not in files and ref + "index.html" not in files:
                bad.append("%s: объявлена картинка %s, которой нет" % (p, img))
    if not seen:
        bad.append("страниц ноль — пустая выборка это провал")
    return bad[:20]


def g_structured_data_real(files):
    """Структурные данные разбираются, и КАЖДОЕ поле есть на странице глазами.

    Разметка, утверждающая машине больше, чем видит человек, — это ровно тот
    класс, за который снимают расширенные результаты, и ровно тот, из-за
    которого страница на этой ферме уже объявляла полноту, которой не
    считала. Поэтому: JSON обязан разбираться, тип — быть из объявленного
    списка, значение свойства — встречаться в ВИДИМОМ тексте страницы, имя
    крошки — в её видимой цепочке, адрес — вести на существующий файл. Полей,
    которых у сайта нет (рейтинг, автор, цена, изготовитель), не бывает.
    """
    import render as rd
    bad, seen = [], 0
    for p, t in sorted(_html(files).items()):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
        noindex = 'content="noindex' in t
        if not blocks:
            if not noindex:
                bad.append("%s: индексируемая страница без структурных данных"
                           % p)
            continue
        seen += 1
        vis = _text(t)
        crumb = re.search(r'<p class="bx-crumb">(.*?)</p>', t, re.S)
        crumb_text = _text(crumb.group(0)) if crumb else ""
        for raw in blocks:
            for word in LD_FORBIDDEN:
                if word in raw:
                    bad.append("%s: в структурных данных поле «%s», которого "
                               "у сайта нет" % (p, word))
            if "<" in raw:
                bad.append("%s: в блоке структурных данных знак «<»" % p)
            try:
                nodes = json.loads(raw)
            except ValueError as e:
                bad.append("%s: структурные данные не разбираются: %s"
                           % (p, e))
                continue
            if not isinstance(nodes, list) or not nodes:
                bad.append("%s: структурные данные не список узлов" % p)
                continue
            for node in nodes:
                ty = node.get("@type")
                if ty not in rd.LD_TYPES:
                    bad.append("%s: тип %s не объявлен" % (p, ty))
                for key in ("url", "item", "publishingPrinciples"):
                    u = node.get(key)
                    if isinstance(u, str) and u.startswith("https://" + DOMAIN):
                        ref = u[len("https://" + DOMAIN):].lstrip("/")
                        if ref and ref not in files \
                                and ref + "index.html" not in files:
                            bad.append("%s: %s ведёт в никуда: %s"
                                       % (p, key, u))
                if ty == "BreadcrumbList":
                    for it in node["itemListElement"]:
                        if it["name"] not in crumb_text:
                            bad.append("%s: крошка «%s» машине есть, а глазами "
                                       "нет" % (p, it["name"]))
                if ty == "Product":
                    if node["name"] not in vis:
                        bad.append("%s: имя %s машине есть, а глазами нет"
                                   % (p, node["name"]))
                    for a in node.get("alternateName") or []:
                        if a not in vis:
                            bad.append("%s: чужое имя %s машине есть, а "
                                       "глазами нет" % (p, a))
                    props = node.get("additionalProperty") or []
                    if not props:
                        bad.append("%s: карточка изделия без единой величины"
                                   % p)
                    for pr in props:
                        if str(pr["value"]) not in vis:
                            bad.append("%s: величина %s=%s машине есть, а "
                                       "глазами нет"
                                       % (p, pr["name"], pr["value"]))
                    d = re.search(
                        r'<meta name="description" content="([^"]*)"', t)
                    if d and node.get("description") != d.group(1):
                        bad.append("%s: описание машине и описание в голове "
                                   "разошлись" % p)
                if ty in ("WebSite", "Organization"):
                    nm = node.get("name") or ""
                    if nm.lower() not in vis.lower():
                        bad.append("%s: имя «%s» машине есть, а глазами нет"
                                   % (p, nm))
                    em = node.get("email")
                    if em and em not in t:
                        bad.append("%s: почта %s машине есть, а на странице "
                                   "нет" % (p, em))
    if not seen:
        bad.append("ни одной страницы со структурными данными — пустая "
                   "выборка это провал, а не «пройден»")
    return bad[:20]


def g_descriptions_differ(files):
    """Описания различаются СВОИМИ величинами, а не подставленным кодом.

    Сто двадцать пять описаний были одним предложением, в котором менялось
    одно слово: поиск такое переписывает, то есть сниппет на большей части
    корпуса перестаёт быть нашим. Проверяется СКЕЛЕТ — описание с вычеркнутыми
    числами и обозначениями. Если после вычёркивания величин остаётся один и
    тот же текст на десятках страниц, значит различала их подстановка, а не
    расчёт.
    """
    bad, skel, exact = [], {}, {}
    for p, t in sorted(_html(files).items()):
        m = re.search(r'<meta name="description" content="([^"]*)"', t)
        if not m:
            continue
        d = m.group(1)
        exact.setdefault(d, []).append(p)
        k = re.sub(r"\s+", " ",
                   re.sub(r"[0-9]+", "",
                          re.sub(r"\b[A-Z][A-Z0-9./+-]{1,14}\b", "", d)))
        skel.setdefault(k, []).append(p)
    if not skel:
        return ["ни одного описания — пустая выборка это провал"]
    for d, ps in sorted(exact.items()):
        if len(ps) > 1:
            bad.append("одно описание на %d страницах: %s"
                       % (len(ps), ", ".join(ps[:3])))
    for k, ps in sorted(skel.items(), key=lambda kv: -len(kv[1])):
        if len(ps) > DESC_SKELETON_MAX:
            bad.append("один скелет описания на %d страницах (предел %d): «%s»"
                       % (len(ps), DESC_SKELETON_MAX, k.strip()[:60]))
    return bad[:20]



# ------------------- ТЕКСТ: СЧЁТ СЛОВ, ЧЕРЕПИЦА, СХОДСТВО И ФОРМА ОБОЛОЧКИ
#
# Проверяющий сломал три функции нарочно и получил семьдесят семь зелёных
# гейтов:
#   · rd.page_words врал втрое — двадцать страниц ниже пола уехали в карту
#     сайта, одна из них на 518 слов при поле 1500;
#   · rd.jaccard возвращал ноль — отбор перестал отсеивать близнецов, страниц
#     стало 164 вместо 146, а независимый счёт нашёл три пары выше порога,
#     худшая 0,792 у /mr52/ против /nr52/;
#   · C.shell_form возвращала «coin» для всего — каждый цилиндр уехал монетой,
#     включая тот самый адрес, который назван в оговорке гейта.
# Все три гейта считали ЭТАЛОН ТОЙ ЖЕ ФУНКЦИЕЙ, которая печатала проверяемое.
#
# Ниже — вторая реализация каждой, написанная здесь и своим способом, и
# таблицы известных ответов, посчитанных РУКАМИ по правилу, а не выведенных
# из тех же функций.


def _words(text):
    """Видимые слова. ВТОРАЯ реализация, без регулярных выражений вовсе:
    перебор знаков, чтобы совпадение с prose.wc ничего не наследовало от неё.

    Слово — буква и то, что тянется за ней буквами, апострофом и дефисом.
    Разметка словами не бывает, и ССЫЛКА НА ЗНАК тоже: «&mdash;» совпадало со
    словом «mdash», их 125 на одной странице, и счётчик печатал 1543 слова
    там, где видимых 1419.
    """
    n, i, out, word, tag = len(text), 0, 0, False, False
    while i < n:
        ch = text[i]
        if tag:
            tag = ch != ">"
            i += 1
            continue
        if ch == "<":
            tag, word = True, False
            i += 1
            continue
        if ch == "&":
            j = _char_ref_end(text, i)
            if j:
                word, i = False, j
                continue
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            if not word:
                out += 1
                word = True
        elif not (word and (ch == "'" or ch == "-")):
            word = False
        i += 1
    return out


def _char_ref_end(text, i):
    """Конец ссылки на знак, начинающейся в i, или 0. Формы ровно три:
    &имя; &#число; &#xчисло; — и имя короче двух букв ссылкой не считается,
    иначе «AT&T; talks» потеряло бы букву."""
    j = i + 1
    if j < len(text) and text[j] == "#":
        j += 1
        digits = "0123456789"
        if j < len(text) and (text[j] == "x" or text[j] == "X"):
            j += 1
            digits = "0123456789abcdefABCDEF"
        k = j
        while k < len(text) and text[k] in digits:
            k += 1
        return k + 1 if k > j and k < len(text) and text[k] == ";" else 0
    k = j
    while k < len(text) and (text[k].isalnum() and text[k].isascii()):
        k += 1
    if k - j < 2 or k >= len(text) or text[k] != ";":
        return 0
    return k + 1 if text[j].isalpha() else 0


def _page_words(html):
    """Видимые слова ОСНОВНОЙ КОЛОНКИ без обстановки — вторая реализация той
    выборки, по которой сеть считает страницу содержательной, и по которой
    render решает, предлагать её роботу или нет.

    Колонка берётся глубиной вложенности, а не «до первого </div>»: наивный
    вариант дал бы пустую выборку, а пустая выборка печатает «пройден».
    """
    key = '<div class="bx-main">'
    i = html.find(key)
    if i < 0:
        return 0
    j, depth = i + len(key), 1
    end = len(html)
    for m in re.finditer(r"<div\b|</div>", html[j:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            end = j + m.start()
            break
    col = html[j:end]
    for pat in (r'<div class="bx-ad .*?</div>',
                r'<form class="bx-find.*?</form>',
                r"<script.*?</script>", r"<style.*?</style>"):
        col = re.sub(pat, " ", col, flags=re.S)
    return _words(col)


def _shingle(text, pattern, k=5):
    """Черепица из k слов подряд. ВТОРАЯ реализация, и представление другое:
    строки, а не кортежи, — чтобы два набора нельзя было спутать молча."""
    w = re.findall(pattern, text.lower())
    out = set()
    for i in range(len(w) - k + 1):
        out.add(" ".join(w[i:i + k]))
    return out


def _overlap(a, b):
    """Жаккар. ВТОРАЯ реализация: пересечение считается перебором, а не
    операцией над множествами."""
    inter = 0
    for x in a:
        if x in b:
            inter += 1
    union = len(a) + len(b) - inter
    return inter / float(union) if union else 0.0


def _form_of(dims):
    """Форма оболочки ПО ЧИСЛАМ. Вторая реализация правила, которое видно на
    рисунке: три величины — коробка; круглая ниже своего диаметра — монета;
    круглая не ниже — цилиндр."""
    if len(dims) == 3:
        return "box"
    if len(dims) != 2:
        return None
    return "coin" if dims[1] < dims[0] else "cylinder"


# Известные ответы для счётчика слов. Посчитаны РУКАМИ по правилу выше.
WC_KNOWN = [
    ("", 0),
    ("one two three", 3),
    ("<p>one two</p>", 2),
    ("<p class='x y z'>one</p>", 1),
    ("a &mdash; b", 2),
    ("&amp; &quot; &nbsp; &#8212; &#x2014;", 0),
    ("mdash", 1),                     # то же слово текстом — слово
    ("&mdash;", 0),                   # ссылкой на знак — не слово
    ("AT&T talks", 3),                # «&T » не ссылка: точки с запятой нет
    ("don't count twice", 3),
    ("well-known cell", 2),
    ("1.5 V lithium", 2),             # «1.5» словом не бывает, «V» бывает
    # Стиль вычищает ВЫЗЫВАЮЩИЙ, не счётчик: остаётся «p{text-align:right}»,
    # и это три слова, а не четыре — дефис держит слово целым.
    ("<style>p{text-align:right}</style>", 3),
]

# Известные ответы для выборки пола объёма: что входит в счёт и что нет.
PW_KNOWN = [
    ('<div class="bx-main"><p>one two three</p></div>', 3),
    ('<header>chrome words here</header><div class="bx-main"><p>one two</p>'
     '</div><footer>and here</footer>', 2),
    ('<div class="bx-main"><p>one</p><div class="bx-ad bx-ad-flow">'
     '<span>Advertisement</span></div><p>two</p></div>', 2),
    ('<div class="bx-main"><p>one</p><form class="bx-find"><label>type the '
     'code</label></form><p>two</p></div>', 2),
    ('<div class="bx-main"><p>one</p><script>var t="two three"</script>'
     '<p>four</p></div>', 2),
    ('<div class="bx-main"><p>a &mdash; b</p></div>', 2),
    ("<p>no main column at all</p>", 0),
]

# Известные ответы для черепицы. Окно в ПЯТЬ слов: текст короче пяти слов не
# даёт ни одной черепицы, и сравнивать в нём нечего.
SHINGLE_KNOWN = [
    ("one two three four", "text", 0),
    ("one two three four five", "text", 1),
    ("one two three four five six", "text", 2),
    ("one one one one one one", "text", 1),      # оба окна одинаковы
    ("reads 1.5 v here now then", "text", 2),
    ("reads 1.5 v here now then", "skel", 1),    # «1.5» из скелета выпадает
]

# Известные ответы для сходства. Посчитаны руками: пересечение на объединение.
JACCARD_KNOWN = [
    ((), (), 0.0),
    (("a",), ("a",), 1.0),
    (("a", "b"), (), 0.0),
    (("a",), ("b",), 0.0),
    (("a", "b", "c"), ("b", "c", "d"), 0.5),
    (("a", "b", "c", "d"), ("c", "d", "e"), 0.4),
    (("a", "b", "c", "d"), ("a", "b", "c", "d"), 1.0),
]

# Известные ответы для формы оболочки. Тот самый адрес из оговорки гейта —
# первым: 14,5 x 50,5 — пальчиковый цилиндр, никакая не монета.
SHELL_KNOWN = [
    (("round", 14.5, 50.5), "cylinder"),
    (("round", 26.2, 50.0), "cylinder"),
    (("round", 10.0, 10.0), "cylinder"),         # равные — уже не монета
    (("round", 20.0, 3.2), "coin"),
    (("round", 11.6, 5.4), "coin"),
    (("round", 7.9, 3.6), "coin"),
    (("prismatic", 26.5, 17.5, 48.5), "box"),
    (("prismatic", 68.2, 68.2, 115.0), "box"),
]

# Окна абзацев — ЧИСЛАМИ, а не ссылкой на те же константы, из которых проза
# и складывалась, и порог инвентаря тоже.
WINDOW_KNOWN = {"intro": (18, 56), "answer": (35, 72)}
AD_MIN_WORDS_KNOWN = 300

# ЧТО ИМЕННО РЕШАЕТ ОТБОР КОРПУСА — список ЯВНЫЙ, и он сверяется с тем, что
# проверено известными ответами. Проба, чей охват нигде не записан, выглядит
# полной при любом числе проверенных функций: пока таблицы просто лежали
# рядом с гейтом, добавить шестую функцию отбора и не заметить, что для неё
# известных ответов нет, было нечем.
SELECTION_FUNCS = (("prose", "wc"), ("render", "page_words"),
                   ("render", "_shingles"), ("render", "jaccard"),
                   ("cells", "shell_form"), ("render", "window_for"))
KNOWN_ANSWER_FOR = {
    ("prose", "wc"): WC_KNOWN,
    ("render", "page_words"): PW_KNOWN,
    ("render", "_shingles"): SHINGLE_KNOWN,
    ("render", "jaccard"): JACCARD_KNOWN,
    ("cells", "shell_form"): SHELL_KNOWN,
    ("render", "window_for"): WINDOW_KNOWN,
}


def g_text_functions_known_answers(files):
    """Пять функций, из которых берётся ВЕСЬ отбор корпуса, проверены
    известными ответами и второй реализацией.

    Отбор страницы решают ровно они: счёт слов ставит пол объёма, черепица и
    сходство отсеивают близнецов, форма оболочки пишет адрес. Проверяющий
    сломал три из пяти, и ни один гейт не покраснел, потому что каждый считал
    ожидаемое той же функцией.

    Сверок здесь три, и они разные:
      · известные ответы, набранные руками, — против обеих реализаций;
      · две реализации между собой НА ВСЕЙ ВЫКЛАДКЕ, а не на примерах;
      · пороги и окна — числами, потому что константа, из которой сложена
        проза, не может быть эталоном для проверки этой же прозы.
    """
    import cells as Cx
    import prose as Px
    import render as rd
    bad = []
    _sample(bad, len(WC_KNOWN), "известных ответов счётчика слов")
    _sample(bad, len(PW_KNOWN), "известных ответов выборки пола")
    _sample(bad, len(SHINGLE_KNOWN), "известных ответов черепицы")
    _sample(bad, len(JACCARD_KNOWN), "известных ответов сходства")
    _sample(bad, len(SHELL_KNOWN), "известных ответов формы оболочки")
    _sample(bad, len(_html(files)), "отданных страниц")

    for text, want in WC_KNOWN:
        for who, got in (("prose.wc", Px.wc(text)), ("вторая", _words(text))):
            if got != want:
                bad.append("%s: на «%s» получено %d, известный ответ %d"
                           % (who, text[:34], got, want))
    for html, want in PW_KNOWN:
        for who, got in (("render.page_words", rd.page_words(html)),
                         ("вторая", _page_words(html))):
            if got != want:
                bad.append("%s: на образце получено %d, известный ответ %d"
                           % (who, got, want))
    pats = {"text": rd.TEXT_PAT, "skel": rd.SKEL_PAT}
    for text, which, want in SHINGLE_KNOWN:
        for who, got in (("render._shingles",
                          len(rd._shingles(text, pats[which]))),
                         ("вторая", len(_shingle(text, pats[which])))):
            if got != want:
                bad.append("%s: на «%s» черепиц %d, известный ответ %d"
                           % (who, text[:34], got, want))
    for a, b, want in JACCARD_KNOWN:
        for who, got in (("render.jaccard", rd.jaccard(set(a), set(b))),
                         ("вторая", _overlap(set(a), set(b)))):
            if abs(got - want) > 1e-9:
                bad.append("%s: на %s и %s сходство %.3f, известный ответ %.3f"
                           % (who, a or "()", b or "()", got, want))
    for shell, want in SHELL_KNOWN:
        for who, got in (("cells.shell_form", Cx.shell_form(shell)),
                         ("вторая", _form_of(tuple(shell[1:])))):
            if got != want:
                bad.append("%s: %s названо «%s», известный ответ «%s»"
                           % (who, shell, got, want))

    # ДВЕ РЕАЛИЗАЦИИ НА ВСЕЙ ВЫКЛАДКЕ. Примеры ловят правило, корпус ловит
    # случай: ссылка на знак, которой в примерах не было, найдётся здесь.
    seen = 0
    for p, t in sorted(_html(files).items()):
        seen += 1
        if rd.page_words(t) != _page_words(t):
            bad.append("%s: счёт слов %d у генератора и %d у второй "
                       "реализации" % (p, rd.page_words(t), _page_words(t)))
        if len(bad) > 20:
            return bad[:20]
    _sample(bad, seen, "страниц, сверенных двумя счётчиками")

    # Окна и порог — числами.
    for kind, want in sorted(WINDOW_KNOWN.items()):
        got = (rd.window_for("Why the swap matters") if kind == "answer"
               else rd.window_for(rd.INTRO_HEADS[0]))
        if tuple(got) != want:
            bad.append("окно «%s» вышло %s, а объявлено %s"
                       % (kind, tuple(got), want))
    if rd.AD_MIN_WORDS != AD_MIN_WORDS_KNOWN:
        bad.append("порог инвентаря %d, а известный ответ %d"
                   % (rd.AD_MIN_WORDS, AD_MIN_WORDS_KNOWN))
    if rd.WORD_FLOOR != 1500:
        bad.append("пол объёма %d, а PLAYBOOK §1 требует 1500" % rd.WORD_FLOOR)
    if (rd.TWIN_TEXT, rd.TWIN_SKELETON) != (0.70, 0.95):
        bad.append("пороги близнецов %s, а объявлены 0.70 и 0.95"
                   % ((rd.TWIN_TEXT, rd.TWIN_SKELETON),))
    # ОХВАТ СВЕРЯЕТСЯ С ОБЪЯВЛЕННЫМ. Функция отбора, для которой таблицы
    # здесь нет, проверена не была — а гейт при этом печатал бы «пройден».
    for key in SELECTION_FUNCS:
        if not KNOWN_ANSWER_FOR.get(key):
            bad.append("%s.%s решает отбор корпуса, а известных ответов для "
                       "неё нет" % key)
    return bad[:20]


# ----------------------------------------------------- ПОЛ ОБЪЁМА И БЛИЗНЕЦЫ

def g_word_floor(files):
    """Всё, что предложено роботу, дотягивает до пола объёма PLAYBOOK §1.

    Ни одна из 164 страниц не дотягивала до 1500 слов, медиана была 1037, и
    на этом требовании держится вся лестница дохода: сеть проверяет объём
    ПОСТРАНИЧНО по всему инвентарю.

    Гейт считает ОБЕ стороны, потому что проверка соответствия без обратной
    стороны у нас уже прятала беду на 105 живых страницах:
      · индексируемая страница не бывает ниже пола;
      · страница ниже пола не бывает индексируемой и не бывает в карте сайта;
      · список исключений — РОВНО тот, что объявлен в render.FLOOR_EXEMPT, и
        каждый его адрес существует;
      · обе выборки — и та, что выше пола, и та, что ниже, — непустые: гейт,
        которому нечего читать, печатал у нас «пройден»;
      · СЛОВА СЧИТАЕТ ГЕЙТ, а не та функция, которая по этому же счёту
        решает, предлагать страницу роботу или нет. Проверяющий завысил
        render.page_words втрое: двадцать страниц ниже пола уехали в карту
        сайта, одна на 518 слов при поле 1500, и семьдесят семь гейтов
        остались зелёными. Оба счёта печатаются, и расхождение — провал.
    """
    import render as rd
    bad = []
    pages = _site_pages(files)
    if not pages:
        return ["гейту нечего читать: страниц сайта нет"]
    # Известные ответы ПЕРЕД счётом: гейт, у которого верна только страница,
    # молчит одинаково при любом счётчике. Полный набор — в
    # g_text_functions_known_answers, здесь ровно те два случая, из-за
    # которых страница ниже пола уезжала в индекс.
    for text, want in (("a &mdash; b", 2), ("one two three", 3)):
        if _words(text) != want:
            bad.append("счётчик гейта врёт на известном ответе: «%s» это %d, "
                       "а не %d" % (text, want, _words(text)))
    if bad:
        return bad
    sm = files.get("sitemap.xml", "")
    listed = set(re.findall(r"<loc>https://[^/]+([^<]*)</loc>", sm))
    above = below = 0
    for p, t in sorted(pages.items()):
        url = _path_of(p)
        # СЧИТАЕТ ГЕЙТ, А НЕ ГЕНЕРАТОР. Раньше здесь стояло rd.page_words —
        # ровно та функция, которая решает, индексировать страницу или нет:
        # втрое завышенный счёт увёл двадцать страниц ниже пола в карту
        # сайта, одну из них на 518 слов, и все семьдесят семь гейтов
        # остались зелёными. Расхождение двух счётов печатается отдельно:
        # оно значит, что отбор шёл по числу, которого никто не проверял.
        words = _page_words(t)
        theirs = rd.page_words(t)
        if theirs != words:
            bad.append("%s: генератор насчитал %d слов, гейт %d — отбор шёл "
                       "по непроверенному числу" % (p, theirs, words))
        indexed = rd.INDEX_META in t
        if url in rd.FLOOR_EXEMPT:
            continue
        if words >= rd.WORD_FLOOR:
            above += 1
            continue
        below += 1
        if indexed:
            bad.append("%s: %d слов при поле %d, а страница индексируется"
                       % (p, words, rd.WORD_FLOOR))
        if url in listed:
            bad.append("%s: ниже пола и при этом в карте сайта" % p)
    if not above:
        bad.append("ни одной страницы выше пола — выборка пуста")
    if not below:
        # Пустая нижняя выборка означала бы, что вторая половина правила ни
        # разу не проверялась. Это не провал сайта, но это провал ГЕЙТА как
        # доказательства, и молчать о нём нельзя.
        bad.append("ни одной страницы ниже пола — вторая половина правила "
                   "не проверена ни разу")
    ex = 0
    for url in rd.FLOOR_EXEMPT:
        key = url.lstrip("/") + ("index.html" if url.endswith("/") else "")
        if key not in files:
            bad.append("в списке исключений адрес, которого нет: %s" % url)
            continue
        ex += 1
        kind = re.search(r'name="page-type" content="([a-z]+)"', files[key])
        kind = kind.group(1) if kind else "неизвестный"
        # ОСВОБОЖДЕНИЕ — ДЛЯ СЛУЖЕБНЫХ СТРАНИЦ. Оно выключает пол объёма
        # постранично, и дописанная в него страница СОДЕРЖИМОГО уезжает в
        # карту сайта тонкой: 123 слова при объявленном поле 1500 и все
        # гейты зелёные. Сам список прибит руками в REFERENCE_CONSTS, а
        # здесь проверяется, кому освобождение выдано.
        if kind != "page":
            bad.append("освобождение от пола объёма выдано странице типа "
                       "«%s»: %s — это содержимое, а не служебная страница"
                       % (kind, url))
    _sample(bad, ex, "адресов, освобождённых от пола объёма")
    return bad[:20]


def g_twin_scope_is_whole_text(files):
    """Гейт близнецов читает ВЕСЬ видимый текст, а не его четверть.

    Он читал заголовочный абзац и по одному абзацу за каждым не-константным
    h2 — 23,7% видимого текста основной колонки. Три четверти того, что видят
    читатель и Googlebot, не сравнивалось ничем, и пара /lr14/ - /lr20/
    проходила порог скелета с зазором в одну тысячную.

    Здесь проверяется и ОБЛАСТЬ, и РЕЗУЛЬТАТ, и делается это на СОБРАННЫХ
    страницах, а не на выводе той же функции, которая их отбирала:
      · выборка own_prose покрывает не меньше DOLE долю видимых слов колонки;
      · из неё вычтены ТОЛЬКО объявленные общими блоки — если исчез хоть один
        заголовок из CONSTANT_HEADS, покрытие поедет вверх, и это тоже видно;
      · попарное сходство по тексту и по скелету ниже своих порогов;
      · печатается медиана, а не только максимум: по максимуму о корпусе
        судить нельзя, KeepsUntil собрался с медианой 0,82.
    """
    import render as rd
    DOLE = 0.60
    cells = _cells(files)
    if len(cells) < 30:
        return ["страниц элементов %d — выборка не та" % len(cells)]
    bad = []
    covered = []
    for p, t in sorted(cells.items()):
        col = _main_col(t)
        if col is None:
            bad.append("%s: основная колонка не нашлась" % p)
            continue
        # СЧИТАЕТ ГЕЙТ. С постоянным счётчиком доля выходила ровно 1,0 —
        # «гейт близнецов видит 100% текста» — при любой выборке; проверяющий
        # заменил бы P.wc на что угодно и не услышал ни звука.
        vis = _no_chrome(re.sub(r"<script.*?</script>|<style.*?</style>",
                                " ", col, flags=re.S))
        whole, mine = _words(vis), _words(rd.own_prose(t))
        if whole != P.wc(vis) or mine != P.wc(rd.own_prose(t)):
            bad.append("%s: генератор насчитал %d и %d слов, гейт %d и %d"
                       % (p, P.wc(vis), P.wc(rd.own_prose(t)), whole, mine))
        if not whole:
            bad.append("%s: видимых слов ноль" % p)
            continue
        covered.append(mine / float(whole))
    if not covered:
        return bad + ["покрытие не посчитано ни на одной странице"]
    covered.sort()
    med = covered[len(covered) // 2]
    if med < DOLE:
        bad.append("гейт близнецов видит %.1f%% видимого текста, а обязан "
                   "видеть не меньше %.0f%%" % (100 * med, 100 * DOLE))
    # Общие блоки обязаны БЫТЬ и обязаны быть вычтены: если их вычитание
    # перестало работать, покрытие уйдёт к единице и правило потеряет смысл.
    for head in P.CONSTANT_HEADS:
        n = sum(1 for t in cells.values() if "<h2>%s</h2>" % head in t)
        if n < len(cells):
            bad.append("общий блок «%s» стоит на %d страницах из %d"
                       % (head, n, len(cells)))
    if bad:
        # ВЫБОРКА НЕВЕРНА — мерить по ней сходство бессмысленно: число
        # выйдет, а значить оно будет не то, что написано в оговорке.
        return bad[:20]
    texts = {p: rd.own_prose(t) for p, t in cells.items()}
    for name, pat, thr in (("тексту", rd.TEXT_PAT, rd.TWIN_TEXT),
                           ("скелету", rd.SKEL_PAT, rd.TWIN_SKELETON)):
        # Черепица и сходство — СВОИ. Гейт, считающий сходство той же
        # функцией, которая отбирала корпус, печатает её ответ, а не свой:
        # с jaccard, возвращающим ноль, оба гейта отчитались о 0,000.
        sh = [(p, _shingle(v, pat), rd._shingles(v, pat))
              for p, v in sorted(texts.items())]
        worst, vals, drift = (0.0, "", ""), [], 0
        for i in range(len(sh)):
            for j in range(i + 1, len(sh)):
                v = _overlap(sh[i][1], sh[j][1])
                if abs(v - rd.jaccard(sh[i][2], sh[j][2])) > 1e-9:
                    drift += 1
                vals.append(v)
                if v > worst[0]:
                    worst = (v, sh[i][0], sh[j][0])
            if drift > 20:
                # Отбор и гейт разошлись на десятках пар — дальше считать
                # нечего: корпус уже отобран непроверенным числом.
                break
        vals.sort()
        if drift:
            bad.append("по %s отбор и гейт разошлись на %d парах из %d"
                       % (name, drift, len(vals)))
        if not vals:
            bad.append("по %s не сравнено ни одной пары" % name)
        elif worst[0] > thr:
            bad.append("близнецы по %s: %.3f у пары %s / %s при пороге %.2f"
                       % (name, worst[0], worst[1], worst[2], thr))
        else:
            med = vals[len(vals) // 2]
            if med > thr:
                bad.append("медиана сходства по %s %.3f при пороге %.2f"
                           % (name, med, thr))
    return bad[:20]


def g_hazard_named_where_it_bites(files):
    """Два случая, где неверная замена ДЕЙСТВИТЕЛЬНО вредит, названы поимённо.

    По всему собранному тексту 164 страниц не встречалось ни слова «smoke
    alarm», ни «hearing aid», ни разговора о проглатывании — при том что
    смысл существования сайта в том, что замена может навредить.

    Правило со ЗНАЧЕНИЯМИ, а не с типом страницы: девятивольтовая — та, у
    которой напряжение не ниже 8,4 В; литиевый диск от 16 мм — тот, у
    которого химия литий, высота меньше диаметра и диаметр не меньше 16.
    Выборки обязаны быть непустыми обе.
    """
    import render as rd
    import depth as D
    bad = []
    nine = coin = seen = away = 0
    stack = []
    by_record, by_print = set(), set()
    lo, hi = D.ALARM_VOLTS
    for cell in rd.CELLS:
        path = "/%s/" % rd.slug(cell)
        key = path.strip("/") + "/index.html"
        t = files.get(key)
        if t is None:
            # СЧИТАЕТСЯ, А НЕ ПРОПУСКАЕТСЯ. Здесь стояло голое continue, и
            # 69 записей из 215 не находили своей страницы: самая дорогая
            # проверка сайта осматривала две трети корпуса и отчитывалась
            # так, будто осмотрела всё.
            away += 1
            continue
        seen += 1
        vis = _text(t).lower()
        own = _own_volts(t)
        if own is not None and lo <= own <= hi:
            by_print.add(key)
        if lo <= (cell.get("volts") or 0) <= hi:
            by_record.add(key)
            nine += 1
            if "smoke alarm" not in vis:
                bad.append("%s: девятивольтовая страница молчит о дымовом "
                           "извещателе" % key)
        # ВЫБОРКА ПО ГЕОМЕТРИИ НОРМЫ, а не по химии. Пока здесь стояло
        # `chem == "lithium" and diameter >= 16`, гейт стерёг 10 страниц из
        # 73 и был зелёным над дырой в 59: он спрашивал у рендера ровно то,
        # что рендер сам и решил. Теперь признак читается из ЗАПИСИ —
        # «single cell battery with a diameter greater than the height»,
        # 16 CFR 1263.2, — и разойтись с рендером ему есть чем.
        hz = D.hazard_kind(cell)
        if hz:
            coin += 1
            want = ["poison help", "1-800-222-1222", "16 cfr 1263",
                    "household trash"]
            # Цинк-воздух выведен из части 1263 решением Комиссии
            # (16 CFR 1263.1(d)) — на этих пяти страницах требовать слово
            # «Reese» значит требовать вранья о норме.
            want.append("reese" if hz == "covered" else "1263.1(d)")
            for w in want:
                if w not in vis:
                    bad.append("%s: страница кнопочного элемента (%s) не "
                               "называет «%s»" % (key, hz, w))
            # ВТОРАЯ СТОРОНА той же сверки: слева ЗАПИСЬ, справа
            # НАПЕЧАТАННОЕ. Порог тяжести берётся из depth.INGEST_MM, а не
            # набирается здесь второй раз; правило прозы «плашка опасности
            # говорит по набору» проверяет то же самое по таблице отданной
            # страницы, и разойтись этим двум есть чем.
            # Оговорка об изъятии обязана стоять РОВНО на изъятых. Без
            # обратной стороны правило ловило бы только «не сказали» и
            # молчало бы о «сказали не там»: 68 страниц из 72 объявили бы
            # себя выведенными из-под нормы, и ни один гейт не покраснел бы.
            if ("zinc air is the one exception" in vis) != (hz == "exempt"):
                bad.append("%s: оговорка об изъятии из части 1263 стоит не "
                           "по своей выборке (%s)" % (key, hz))
            heavy = ((cell.get("diameter") or 0) >= D.INGEST_MM
                     and (cell.get("volts") or 0) >= 3.0)
            if heavy != ("most severe reported injuries" in vis):
                bad.append("%s: запись даёт %s мм при %s В, а плашка говорит "
                           "%s" % (key, cell.get("diameter"),
                                   cell.get("volts"),
                                   "об обычном классе" if heavy
                                   else "о тяжелейшем"))
        elif C.is_coin(cell) is True:
            # ЕДИНСТВЕННАЯ МОЛЧАЩАЯ ВЕТКА НАЗВАНА ВСЛУХ. Диаметр больше
            # высоты, но это сборка, а норма говорит «single cell battery»:
            # 2MR9 — столбик кнопок 16,89 x 15,4 мм. Ветка обязана остаться
            # одноместной; вырастет — значит признак сборки поехал.
            stack.append(key)
    if not nine:
        bad.append("девятивольтовых страниц ноль — пустая выборка это провал")
    if not coin:
        bad.append("страниц кнопочных элементов ноль — пустая выборка это "
                   "провал")
    if len(stack) != 1:
        bad.append("сборок-исключений %d, а должна быть ровно одна (2MR9): "
                   "либо признак сборки поехал, либо страница без плашки "
                   "появилась молча — %s"
                   % (len(stack), ", ".join(sorted(stack)[:4]) or "ни одной"))
    _sample(bad, seen, "страниц элементов, осмотренных на опасные применения")
    if seen != len(_cells(files)):
        bad.append("осмотрено %d страниц элементов, а в сборке их %d: %d "
                   "записей не нашли своей страницы и выпали из осмотра"
                   % (seen, len(_cells(files)), away))
    # ДВЕ СТОРОНЫ ОТБОРА. Слева поле записи, справа НАПЕЧАТАННОЕ на странице
    # напряжение. Пока сторона была одна, переименованное или пропавшее поле
    # просто выводило страницу из-под правила, и правило молчало о ней —
    # ровно так флаг, сверенный с «Y» там, где в файле стояло «Yes», спрятал
    # у нас все предупреждения разом.
    if by_record != by_print:
        bad.append("отбор девятивольтовых по полю записи и по напечатанному "
                   "напряжению разошёлся: только в записи %s, только на "
                   "странице %s"
                   % (sorted(by_record - by_print)[:3] or "нет",
                      sorted(by_print - by_record)[:3] or "нет"))
    return bad[:20]


def g_sources_numbered_and_real(files):
    """У каждой страницы элемента есть НУМЕРОВАННЫЕ источники, и они настоящие.

    Сайт воспроизводил чужие числа на всех страницах, объявлял источник фразой
    в подвале и не давал проверить ни одну цифру: ноль внешних адресов на весь
    корпус при требовании PLAYBOOK §1 п.4 «нумерованные ссылки на источники —
    конкретные ID записей, номера документов, даты».

    Проверяется не наличие разметки, а СОВПАДЕНИЕ С ИСТОЧНИКОМ: каждый
    напечатанный номер записи есть в снимке, каждое имя даташита есть в
    снимке, и адрес собран той же функцией, что и всюду.
    """
    import render as rd
    ids, sheets = set(), set()
    for c in rd.CELLS:
        for r in (c.get("records") or []):
            ids.add(r["id"])
            if r["tds"]:
                sheets.add(r["tds"])
    if len(ids) < 100:
        return ["записей из снимка прочитано %d — источник не тот" % len(ids)]
    bad, seen = [], 0
    for p, t in sorted(_cells(files).items()):
        m = re.search(r'<ol class="bx-refs">(.*?)</ol>', t, re.S)
        if not m:
            bad.append("%s: нет нумерованного списка источников" % p)
            continue
        seen += 1
        block = m.group(1)
        nums = re.findall(r'<span class="bx-refno">\[(\d+)\]</span>', block)
        if not nums:
            bad.append("%s: список источников без номеров" % p)
        elif [int(x) for x in nums] != list(range(1, len(nums) + 1)):
            bad.append("%s: номера источников не по порядку: %s"
                       % (p, ",".join(nums)))
        recs = re.findall(r"catalog record (\d+)", block)
        if not recs:
            bad.append("%s: ни одной записи каталога не названо" % p)
        for r in recs:
            if int(r) not in ids:
                bad.append("%s: запись %s в снимке отсутствует" % (p, r))
        for href in re.findall(r'href="(https://[^"]+)"', block):
            host = re.match(r"https://([^/]+)/", href)
            if not host or host.group(1) not in OUTBOUND_HOSTS:
                bad.append("%s: источник ведёт на чужой хост %s" % (p, href))
                continue
            name = href.rsplit("/", 1)[-1]
            if name not in sheets:
                bad.append("%s: даташита %s в снимке нет" % (p, name))
            if href != C.tds_url(name):
                bad.append("%s: адрес даташита собран не общей функцией" % p)
    if seen < 30:
        bad.append("страниц с источниками %d — выборка пуста или не та" % seen)
    return bad[:20]


def g_print_stylesheet(files):
    """Печать не режет ни таблицу, ни чертёж.

    Это справочник, который несут к прилавку. Обе прокручиваемые коробки —
    таблица и чертёж — в печати обрезаются в каждом крупном браузере, и
    правила @media print на сайте не было вовсе.
    """
    bad = []
    css = _sheets_ship(files, bad).get("CSS", "")
    m = re.search(r"@media print\{(.*?)\n\}", css, re.S)
    if not m:
        return ["в CSS нет ни одного правила @media print"]
    blk = m.group(1)
    for need, why in ((".bx-tw", "прокручиваемая таблица"),
                      (".bx-fig", "прокручиваемый чертёж")):
        if need not in blk:
            bad.append("в печати не отпущен %s (%s)" % (need, why))
    if "overflow:visible" not in blk.replace(" ", ""):
        bad.append("в печати не снят overflow — правые столбцы обрежутся")
    for need in (".bx-mast", ".bx-ad"):
        if need not in blk:
            bad.append("в печати не убран %s" % need)
    # Правило обязано доехать ДО СТРАНИЦЫ, а не остаться в исходнике.
    pages = _site_pages(files)
    if not pages:
        return bad + ["страниц сайта нет — пустая выборка это провал"]
    missing = [p for p, t in pages.items() if "@media print" not in t]
    if missing:
        bad.append("правил печати нет на %d страницах, например %s"
                   % (len(missing), sorted(missing)[0]))
    return bad[:20]


def g_institutional_shell(files):
    """Институциональная оболочка PLAYBOOK §8 — вся, и со всех страниц.

    About не было вовсе: «кто это ведёт» лежало абзацем внутри /contact/, а
    рецензент рекламной сети ищет About по имени.
    """
    import render as rd
    bad = []
    need = ("/about/", "/contact/", "/privacy/", "/terms/", "/method/")
    for url in need:
        key = url.strip("/") + "/index.html"
        if key not in files:
            bad.append("нет обязательной страницы %s" % url)
    about = files.get("about/index.html", "")
    if about:
        col = _main_col(about)
        if col is None:
            bad.append("у About не нашлась основная колонка")
            col = ""
        vis = _text(col)
        for want in (rd.PUBLISHER, "Wyoming", rd.CONTACT):
            if want not in vis:
                bad.append("About не называет «%s»" % want)
        if "/method/" not in about:
            bad.append("About не ведёт на страницу методики")
    pages = _site_pages(files)
    if not pages:
        return bad + ["страниц сайта нет — пустая выборка это провал"]
    for url in need:
        absent = [p for p, t in pages.items()
                  if ('href="%s"' % url) not in t
                  and ('>%s<' % url) not in t
                  and _path_of(p) != url]
        if absent:
            bad.append("%s не связана с %d страницами, например %s"
                       % (url, len(absent), sorted(absent)[0]))
    return bad[:20]


def g_dataset_published(files):
    """Набор данных опубликован, датирован и СОВПАДАЕТ со снимком.

    PLAYBOOK §7 требует публичный версионный CSV с первого дня. Проверяется
    не наличие файла, а то, что в нём: строка на обозначение, разметка «наше»
    в заголовке, и величины, сходящиеся с записями снимка.
    """
    import render as rd
    dated = rd.DATASET_PATH.lstrip("/") % rd.DATA_SNAPSHOT.isoformat()
    latest = rd.DATASET_LATEST.lstrip("/")
    bad = []
    for key in (dated, latest):
        if key not in files:
            bad.append("нет файла набора данных %s" % key)
    if bad:
        return bad
    if files[dated] != files[latest]:
        bad.append("датированный CSV и latest.csv различаются побайтово")
    lines = files[dated].rstrip("\n").split("\n")
    head = lines[0].split(",")
    if not any(h.startswith("ours:") for h in head):
        bad.append("в заголовке CSV не помечено ни одно вычисленное поле")
    if len(lines) - 1 != len(rd.CELLS):
        bad.append("строк в CSV %d, обозначений в снимке %d"
                   % (len(lines) - 1, len(rd.CELLS)))
    by = {c["code"]: c for c in rd.CELLS}
    icode, ivolt = head.index("designation"), head.index("volts")
    ilisted = head.index("listed_by_energizer")
    checked = 0
    for row in lines[1:]:
        cols = next(csv_rows(row))
        c = by.get(cols[icode])
        if c is None:
            bad.append("в CSV обозначение, которого нет в снимке: %s"
                       % cols[icode][:20])
            continue
        checked += 1
        want = ("yes" if c["active"] else "no")
        if cols[ilisted] != want:
            bad.append("%s: в CSV статус %s, в снимке %s"
                       % (c["code"], cols[ilisted], want))
        if c.get("volts") is not None and cols[ivolt]:
            if abs(float(cols[ivolt]) - c["volts"]) > 1e-6:
                bad.append("%s: в CSV %s В, в снимке %s В"
                           % (c["code"], cols[ivolt], c["volts"]))
    if checked < 100:
        bad.append("сверено строк %d — выборка пуста или не та" % checked)
    # Ссылка на набор данных обязана быть на сайте, иначе его никто не найдёт.
    if not any(rd.DATASET_LATEST in t for t in _site_pages(files).values()):
        bad.append("на набор данных не ссылается ни одна страница")
    return bad[:20]


def csv_rows(line):
    """Разбор строки CSV по RFC 4180. Своими руками и на месте: стандартная
    библиотека умеет это, но здесь важно читать РОВНО то, что записано, а не
    то, что модуль готов простить."""
    out, cur, q, i = [], "", False, 0
    while i < len(line):
        ch = line[i]
        if q:
            if ch == QUOTE and i + 1 < len(line) and line[i + 1] == QUOTE:
                cur += QUOTE
                i += 1
            elif ch == QUOTE:
                q = False
            else:
                cur += ch
        elif ch == QUOTE:
            q = True
        elif ch == ",":
            out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    out.append(cur)
    yield out


def g_embeds_are_fragments(files):
    """Виджет — фрагмент чужой страницы, и ведёт себя как фрагмент.

    Это ТРЕТИЙ обязательный артефакт PLAYBOOK §7, и он же единственная часть
    сайта, которая уезжает на чужой домен. Поэтому он проверяется отдельным
    правилом, а не остатками правил для страниц: ни скрипта, ни рекламы, ни
    навигации, ни поля поиска, noindex, canonical на свою страницу, обратная
    ссылка и связь с той страницей в обе стороны.
    """
    import render as rd
    emb = _embeds(files)
    if not emb:
        return ["виджетов ноль — пустая выборка это провал"]
    bad = []
    for p, t in sorted(emb.items()):
        if "<script" in t:
            bad.append("%s: в виджете скрипт" % p)
        for forbidden in ('class="bx-ad ', 'class="bx-nav"', 'id="bx-find"',
                          "bx-mast"):
            if forbidden in t:
                bad.append("%s: в виджете обстановка сайта (%s)"
                           % (p, forbidden))
        if 'content="noindex, follow"' not in t:
            bad.append("%s: виджет не закрыт от индексации" % p)
        c = re.search(r'<link rel="canonical" href="([^"]*)"', t)
        own = _path_of(p)
        want = "https://%s%s" % (DOMAIN, own.replace("/embed/", "/", 1))
        if not c:
            bad.append("%s: у виджета нет canonical" % p)
        elif c.group(1) != want:
            bad.append("%s: canonical %s, ожидалось %s"
                       % (p, c.group(1), want))
        if ('<a href="%s"' % want) not in t:
            bad.append("%s: виджет не ссылается назад на свою страницу" % p)
        src = want.replace("https://%s" % DOMAIN, "").lstrip("/")
        page = files.get(src + "index.html")
        if page is None:
            bad.append("%s: страницы, которой это фрагмент, нет" % p)
        elif ('href="%s"' % own) not in page:
            bad.append("%s: со своей страницы виджет не предложен" % p)
        for ref in re.findall(r'(?:src|href)="([^"]*)"', t):
            if ref.startswith(("http://", "https://")) and DOMAIN not in ref:
                bad.append("%s: виджет тянет чужой адрес %s" % (p, ref[:50]))
    return bad[:20]

# ------------------------------------------------- ОБЛИК: цвет, кегль, ритм
#
# Семь гейтов ниже написаны в художественную волну, и каждый куплен находкой
# аудита, а не вкусом. Общее у них одно: они читают ТОТ ЖЕ ТЕКСТ CSS, который
# уезжает на страницы, и считают, а не смотрят.


def _sheets():
    """Все три таблицы стилей сайта поимённо, КАК ИХ ОБЪЯВИЛ ГЕНЕРАТОР.

    Отдельно от отданных байтов эти тексты годятся ровно на одно: сказать,
    где в отданной таблице проходит граница между общим листом и рекламным.
    Читать облик по ним нельзя — см. _sheets_ship.
    """
    import design
    import render as rd
    return {"CSS": design.CSS, "AD_CSS": design.AD_CSS,
            "EMBED_CSS": rd.EMBED_CSS}


# Свойства, которые ВЫЧИСЛЯЮТСЯ на страницу и потому стоят атрибутом style=:
# место штриха на шкале и края полосы класса. Всё остальное в атрибуте — это
# правило облика, спрятанное мимо таблицы стилей и мимо всех гейтов облика.
INLINE_STYLE_OK = ("left", "right")


_SHEETS_MEMO = [None, [], {}]


def _sheets_ship(files, bad):
    """Разбор отданных таблиц стилей, посчитанный один раз на прогон.

    Гейтов облика одиннадцать, а перебор всех отданных страниц с разбором
    их style стоит секунды. Ключ — ТОТ ЖЕ САМЫЙ словарь файлов, а не его
    содержимое: самопроверка каждый раз подаёт новую копию, и на ней разбор
    честно повторяется. Подмена в модуле сбрасывает память отдельно, через
    _sheets_forget: иначе гейт отвечал бы разбором ДО поломки.
    """
    if _SHEETS_MEMO[0] is files:
        bad.extend(_SHEETS_MEMO[1])
        return _SHEETS_MEMO[2]
    mine = []
    out = _sheets_read(files, mine)
    _SHEETS_MEMO[:] = [files, mine, out]
    bad.extend(mine)
    return out


def _sheets_forget():
    """Забыть разбор: таблицу стилей подменили в модуле."""
    _SHEETS_MEMO[:] = [None, [], {}]


def _sheets_read(files, bad):
    """Таблицы стилей ТАК, КАК ИХ ПОЛУЧАЕТ БРАУЗЕР.

    Шесть гейтов облика читали текст CSS из модуля, а эта функция доказывала
    ровно одно: что объявленный текст ПРИСУТСТВУЕТ на 177 страницах. Что на
    них нет ничего сверх него, не проверялось ничем — то есть правило,
    дописанное вторым элементом style, внешним листом или атрибутом style=,
    лежало вне области всех шести гейтов сразу.

    Здесь каждый байт отданной таблицы обязан быть учтён:
      · у каждой страницы РОВНО один элемент style и ни одного внешнего листа;
      · все страницы сайта несут один и тот же текст, все виджеты — свой;
      · отданный текст сайта делится надвое по единственному вхождению
        рекламного листа, и склейка частей побайтово равна целому — значит
        правило не может спрятаться в шве;
      · атрибут style= разрешён только вычисленному месту (INLINE_STYLE_OK).

    Возвращаются ОТДАННЫЕ тексты под прежними именами: гейты спрашивают
    «CSS», «AD_CSS» и «EMBED_CSS» о разном, и роли у листов разные.
    """
    import design
    _sample(bad, len(_html(files)), "страниц")
    emb = _embeds(files)
    site_txt, emb_txt, seen = {}, {}, 0
    for p, t in sorted(_html(files).items()):
        blocks = re.findall(r"<style[^>]*>(.*?)</style>", t, re.S)
        if len(blocks) != 1:
            bad.append("%s: элементов style %d, а обязан быть ровно один"
                       % (p, len(blocks)))
            continue
        seen += 1
        (emb_txt if p in emb else site_txt).setdefault(blocks[0], []).append(p)
        for m in re.finditer(r"<link[^>]*>", t):
            if 'rel="stylesheet"' in m.group(0):
                bad.append("%s: внешний лист стилей — правило вне области "
                           "гейтов облика" % p)
        for m in re.finditer(r'\sstyle="([^"]*)"', t):
            for decl in m.group(1).split(";"):
                prop = decl.split(":")[0].strip()
                if prop and prop not in INLINE_STYLE_OK:
                    bad.append("%s: «%s» стоит атрибутом style=, мимо таблицы "
                               "стилей" % (p, decl.strip()[:40]))
    _sample(bad, seen, "страниц с отданной таблицей стилей")
    for what, got in (("сайта", site_txt), ("виджетов", emb_txt)):
        _sample(bad, len(got), "отданных таблиц стилей %s" % what)
        if len(got) > 1:
            bad.append("страницы %s несут %d РАЗНЫХ таблицы стилей: %s"
                       % (what, len(got),
                          ", ".join(sorted(v[0] for v in got.values()))))
    if len(site_txt) != 1 or len(emb_txt) != 1:
        return {}
    site = next(iter(site_txt))
    embed = next(iter(emb_txt))
    # Шов: рекламный лист дописан к общему одним куском. Граница берётся из
    # модуля, но ОБЕ части — из отданных байтов, и их склейка обязана быть
    # равна целому, иначе анализ разбирал бы не всё, что уехало.
    ad_mod = design.strip_comments(design.AD_CSS)
    if site.count(ad_mod) != 1:
        bad.append("рекламный лист входит в отданную таблицу %d раз, а обязан "
                   "один: разобрать её на части нечем" % site.count(ad_mod))
        return {}
    cut = site.index(ad_mod)
    css, ad = site[:cut], site[cut:]
    if css + ad != site:
        bad.append("части отданной таблицы не складываются в неё целиком")
        return {}
    if css != design.strip_comments(design.CSS):
        bad.append("отданный общий лист не совпадает с design.CSS")
    # И ОСТАЛЬНЫЕ ДВЕ. Сверялась только первая половина, и обещание
    # «каждый байт отданной таблицы обязан быть учтён» было ложью для
    # двух листов из трёх: правило, дописанное ПОСЛЕ рекламного листа
    # или в лист виджета, уезжало на 177 страниц при всех зелёных
    # гейтах — его не с чем было сравнивать.
    import render as _rd
    if ad != design.strip_comments(design.AD_CSS):
        bad.append("отданный рекламный лист не совпадает с design.AD_CSS")
    if embed != design.strip_comments(_rd.EMBED_CSS):
        bad.append("отданный лист виджета не совпадает с render.EMBED_CSS")
    return {"CSS": css, "AD_CSS": ad, "EMBED_CSS": embed}


_COLOUR = re.compile(r"^\s*(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()")


def _root_blocks(css):
    """(голый :root, :root в тёмной теме, :root в печати) — тексты блоков."""
    bare, dark, prnt = [], [], []
    i = 0
    while True:
        j = css.find(":root", i)
        if j < 0:
            break
        k = css.find("{", j)
        e = css.find("}", k)
        if k < 0 or e < 0:
            break
        head = css[:j]
        # Внутри какого media-блока стоит этот :root — считаем по последней
        # незакрытой строке «@media ...{» левее него.
        depth = head.count("{") - head.count("}")
        where = bare
        if depth > 0:
            last = head.rfind("@media")
            cond = css[last:css.find("{", last)] if last >= 0 else ""
            if "print" in cond:
                where = prnt
            elif "dark" in cond:
                where = dark
        where.append(css[k + 1:e])
        i = e + 1
    return "\n".join(bare), "\n".join(dark), "\n".join(prnt)


def _tokens_of(block):
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;}]+)", block))


def g_colour_tokens_paired(files):
    """Каждый цвет — переменная на ГОЛОМ :root, и тёмная тема переопределяет
    ТО ЖЕ ИМЯ.

    Цвет, объявленный единственный раз внутри media-блока, — дефект: у нас
    так карточка осталась светлой внутри тёмной полосы при 1,07:1. И ни один
    цвет не объявляется через var() другого цвета: алиас вычисляется на :root
    и наследуется ЧИСЛОМ, поэтому переопределение темы на контейнере его не
    трогает — это та же авария, вид сбоку.

    Виджет нарушал оба правила разом: шесть литеральных цветов вердиктов
    прямо в правилах, три из них — только в тёмном media-блоке.
    """
    bad = []
    sheets = _sheets_ship(files, bad)
    for name, css in sorted(sheets.items()):
        bare, dark, prnt = _root_blocks(css)
        light = {k: v for k, v in _tokens_of(bare).items()
                 if _COLOUR.match(v)}
        if name == "CSS" and not light:
            bad.append("%s: на голом :root не объявлено ни одного цвета" % name)
        for k, v in sorted(_tokens_of(bare).items()):
            if _COLOUR.match(v) and "var(" in v:
                bad.append("%s: %s объявлен через var() другого цвета" %
                           (name, k))
        # Цвет, названный ТОЛЬКО в тёмной теме или только в печати, — тот
        # самый дефект, ради которого гейт написан.
        for where, blk in (("тёмной теме", dark), ("печати", prnt)):
            for k, v in sorted(_tokens_of(blk).items()):
                if _COLOUR.match(v) and k not in light:
                    bad.append("%s: %s объявлен только в %s" % (name, k, where))
        # И обратная сторона: у каждого цвета голого :root обязана быть
        # тёмная пара. Иначе половина палитры тянется в тёмную тему как есть.
        if name != "AD_CSS":
            dk = _tokens_of(dark)
            for k in sorted(light):
                if k not in dk:
                    bad.append("%s: %s не переопределён в тёмной теме" %
                               (name, k))
        # Литеральный цвет в ПРАВИЛЕ, а не в токене.
        body = css
        for blk in (bare, dark, prnt):
            # ПУСТОЙ блок не вырезается: str.replace("") вставляет пробел
            # между КАЖДЫМИ двумя знаками, и «#eeeeee» превращается в
            # «# e e e e e e» — литеральный цвет переставал находиться вовсе.
            # У рекламного листа своего :root нет, и эта половина проверки
            # молча не работала на нём ни разу.
            if blk:
                body = body.replace(blk, " ")
        for m in re.finditer(r"[^-\w](#[0-9a-fA-F]{3,8})", body):
            bad.append("%s: литеральный цвет %s стоит в правиле, а не в токене"
                       % (name, m.group(1)))
    return bad[:20]


# ------------------------------------------------------------------ КОНТРАСТ
#
# ПАРЫ ПЕРЕЧИСЛЕНЫ ПОИМЁННО, потому что дефект был именно в паре, а не в
# токене: у силуэта заливка держалась темы, обводка ехала за темой, каждая по
# отдельности выглядела разумно, и в тёмной теме линия чертежа встала к панели
# на 1,04:1. Проверять надо то, что ЛЕЖИТ ДРУГ НА ДРУГЕ.
#   вид «text»    — 4,5:1, обычный текст;
#   вид «graphic» — 3:1, всё, что несёт смысл и не буква.
CONTRAST_PAIRS = (
    ("--ink", "--bg", "text", "основной текст на странице"),
    ("--ink", "--panel", "text", "основной текст на панели"),
    ("--ink", "--sunk", "text", "текст на утопленном"),
    ("--ink-2", "--bg", "text", "вторые чернила на странице"),
    ("--ink-2", "--panel", "text", "вторые чернила на панели"),
    ("--ink-2", "--panel-2", "text", "вторые чернила на второй панели"),
    ("--ink-2", "--sunk", "text", "вторые чернила на утопленном"),
    ("--panel", "--ink", "text", "логотип: панель по чернилам"),
    ("--signal", "--panel", "text", "сигнал в ячейке таблицы"),
    ("--signal", "--bg", "text", "сигнал на странице"),
    ("--signal", "--sunk", "graphic", "штрих чужого напряжения на дорожке"),
    ("--line-1", "--panel", "graphic", "волосяная между строками списка"),
    ("--line-1", "--bg", "graphic", "волосяная на странице"),
    ("--line-2", "--panel", "graphic", "средняя линейка на панели"),
    ("--line-2", "--sunk", "graphic", "рамка дорожки и рамка места"),
    ("--line-2", "--bg", "graphic", "средняя линейка на странице"),
    ("--line-3", "--panel", "graphic", "тяжёлая линейка и обводка чертежа"),
    ("--line-3", "--bg", "graphic", "тяжёлая линейка на странице"),
    ("--line-3", "--metal", "graphic", "обводка силуэта по своей же заливке"),
    ("--metal", "--panel", "graphic", "заливка силуэта на панели"),
    ("--ink", "--sunk", "graphic", "штрих этого элемента на дорожке"),
    ("--ink-2", "--sunk", "graphic", "край класса на дорожке"),
)

EMBED_CONTRAST_PAIRS = (
    ("--e-ink", "--e-paper", "text", "текст виджета"),
    ("--e-ink2", "--e-paper", "text", "вторые чернила виджета"),
    ("--e-signal", "--e-paper", "text", "вердикт «другой класс»"),
    ("--e-line", "--e-paper", "graphic", "линейка строки виджета"),
)

# Поверхности проверяются НЕ друг против друга: панель на фоне страницы даёт
# 1,5:1 и обязана — это две соседние ступени одной стали, а не кодировка.
# Границу между ними рисует ЛИНЕЙКА, и вот она в таблице пар есть. Список
# объявлен явно, и гейт требует, чтобы вместе с таблицей пар он покрывал ВСЕ
# цветовые токены: удобный белый список ослепил у нас однажды целый гейт.
SURFACE_TOKENS = ("--bg", "--panel", "--panel-2", "--sunk", "--e-paper")


def _srgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    out = []
    for v in c:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    """Отношение контраста по WCAG 2.x. Чистая функция; самопроверка ломает
    ЕЁ, а не страницу."""
    la, lb = _lum(_srgb(a)), _lum(_srgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def g_contrast_pairs_hold(files):
    """Контраст СЧИТАЕТСЯ, а не оценивается глазом, и в ОБЕИХ темах.

    Аудит нашёл в светлой теме заливку силуэта на 1,69:1, дорожку шкалы на
    1,48:1 и полосу класса на 1,14:1 при требовании 3:1, а в тёмной — обводку
    чертежа на 1,04:1. Одно и то же кодирование читалось в одной теме и не
    читалось в другой, то есть картинка значила разное в зависимости от
    настройки операционной системы.

    Известные ответы: гейт проверяет саму формулу на чёрном по белому (21:1)
    и на одинаковой паре (1:1), потому что считалка, согласная сама с собой,
    молчит одинаково при любом ответе.
    """
    bad = []
    _sheets_ship(files, bad)
    if abs(contrast("#000000", "#ffffff") - 21.0) > 0.01:
        bad.append("формула контраста врёт на чёрном по белому")
    if abs(contrast("#123456", "#123456") - 1.0) > 0.001:
        bad.append("формула контраста врёт на одинаковой паре")
    sheets = _sheets_ship(files, bad)
    for css, pairs, who in ((sheets.get("CSS", ""), CONTRAST_PAIRS, "сайт"),
                            (sheets.get("EMBED_CSS", ""),
                             EMBED_CONTRAST_PAIRS, "виджет")):
        bare, dark, _p = _root_blocks(css)
        light = {k: v.strip() for k, v in _tokens_of(bare).items()
                 if _COLOUR.match(v)}
        theme = {"светлая": dict(light)}
        theme["тёмная"] = dict(light)
        theme["тёмная"].update({k: v.strip()
                                for k, v in _tokens_of(dark).items()
                                if _COLOUR.match(v)})
        if not pairs:
            bad.append("%s: пар не объявлено — пустая выборка это провал" % who)
        # Ни один цвет не имеет права остаться непроверенным: либо он в
        # таблице пар, либо он объявлен поверхностью.
        named = {t for p in pairs for t in p[:2]} | set(SURFACE_TOKENS)
        for k in sorted(light):
            if k not in named:
                bad.append("%s: цвет %s не проверен ни одной парой и не "
                           "объявлен поверхностью" % (who, k))
        for name, tk in sorted(theme.items()):
            for fg, bgc, kind, what in pairs:
                if fg not in tk or bgc not in tk:
                    bad.append("%s/%s: пара %s на %s не разрешается в цвета"
                               % (who, name, fg, bgc))
                    continue
                need = 4.5 if kind == "text" else 3.0
                r = contrast(tk[fg], tk[bgc])
                if r + 1e-9 < need:
                    bad.append("%s/%s: %s — %s на %s = %.2f:1 при пороге %.1f"
                               % (who, name, what, tk[fg], tk[bgc], r, need))
    return bad[:20]


# Носители сигнального цвета: перечислены ПОИМЁННО, потому что правило —
# «один цвет, одна работа», а работа проверяется только чтением списка.
# Обе строки говорят одно и то же про одну и ту же величину: напряжение этой
# замены вне нормы. Было пять работ у одного цвета плюс полный светофор из
# трёх других — одиннадцать окрашенных мест, несущих ДВА независимых вердикта.
SIGNAL_CARRIERS = {"CSS": {".bx-scale-pin-off", ".bx-v-wrong"},
                   "AD_CSS": set(),
                   "EMBED_CSS": {".bx-emb .bx-v-wrong"}}
# Цвета, которых на сайте больше нет и которые нельзя вернуть молча: светофор
# нёс второй вердикт рядом с первым и тем отменял сигнальность сигнала.
FORBIDDEN_TOKENS = ("--ok", "--warn", "--stop", "--on-metal", "--metal-2")


def g_one_signal_one_job(files):
    """Один сигнальный цвет и ОДНА его работа.

    `--signal` красил пять разных вещей: «вы здесь» в меню, «не ваше
    напряжение» на шкале, «высота, до которой надо дотянуться» в чертеже,
    «посчитано нами» у строки таблицы и «ничего не нашлось» у поиска. Рядом с
    ним жил полный светофор `--ok/--warn/--stop`, и он нёс ДВА независимых
    вердикта одновременно: зелёный значил «встаёт» в одном столбце и «то же
    напряжение» в соседнем. Цвет, который значит пять вещей, не значит ничего.
    """
    bad = []
    for name, css in sorted(_sheets_ship(files, bad).items()):
        want = SIGNAL_CARRIERS.get(name)
        if want is None:
            bad.append("%s: для этой таблицы не объявлено, кто носит сигнал"
                       % name)
            continue
        got = set()
        for m in re.finditer(r"([^{}/]+)\{([^}]*)\}", css):
            sel, body = m.group(1).strip(), m.group(2)
            if sel.startswith("@") or sel.startswith(":root"):
                continue
            if re.search(r"var\(--(?:e-)?signal\)", body):
                got.add(re.sub(r"\s+", " ", sel))
        if got != want:
            bad.append("%s: сигнал носят %s, а объявлено %s"
                       % (name, sorted(got) or "никто", sorted(want)))
        for t in FORBIDDEN_TOKENS:
            if re.search(r"%s\s*:" % re.escape(t), css):
                bad.append("%s: вернулся отменённый цвет %s" % (name, t))
    return bad[:20]


# ОДНА шкала кегля. Значения читаются ИЗ ТОКЕНОВ, а не набираются здесь
# второй раз: гейт, знающий ответ наизусть, проверяет себя.
TYPE_TOKEN_PREFIX = ("--t-", "--e-t-")


def g_type_scale_is_one(files):
    """Кегль берётся из шкалы, и заголовок раздела не мельче своего текста.

    Было четырнадцать разных кеглей, шесть из них мельче основного текста, и
    заголовок раздела стоял 13 px при тексте 15 px: `h2` читался заголовком
    только за счёт линейки над ним. Плюс три «уровня» 15/16/17 в пиксель
    друг от друга — это шум, а не иерархия.
    """
    bad = []
    sheets = _sheets_ship(files, bad)
    # У рекламного листа нет своего :root: он ДОПИСЫВАЕТСЯ к общему и
    # пользуется его шкалой. Источник токенов назван явно, чтобы
    # «токенов нет» не превращалось в «проверять нечего».
    SCALE_FROM = {"CSS": "CSS", "AD_CSS": "CSS", "EMBED_CSS": "EMBED_CSS"}
    for name, css in sorted(sheets.items()):
        bare, _d, _p = _root_blocks(sheets[SCALE_FROM[name]])
        scale = {k: v.strip() for k, v in _tokens_of(bare).items()
                 if k.startswith(TYPE_TOKEN_PREFIX)}
        if not scale:
            bad.append("%s: шкала кегля не объявлена ни одним токеном" % name)
            continue
        body = css.replace(bare, " ")
        # font-size: и кегль внутри сокращённого font:
        sizes = re.findall(r"font-size\s*:\s*([^;}]+)", body)
        sizes += [m.group(1) for m in
                  re.finditer(r"font\s*:\s*[^;}]*?"
                              r"((?:var\(--[a-z0-9-]+\))|[0-9.]+(?:rem|px|em))"
                              r"\s*/", body)]
        for s in sizes:
            s = s.strip()
            if s.startswith("var(") and s[4:-1] in scale:
                continue
            bad.append("%s: кегль %s взят мимо шкалы" % (name, s))
        if not sizes:
            bad.append("%s: не найдено ни одного кегля — выборка пуста" % name)
    # Заголовок раздела не мельче текста, который он открывает. Сравниваются
    # ЧИСЛА из токенов, а не имена: имя ничего не обещает.
    look = sheets.get("CSS", "")
    bare, _d, _p = _root_blocks(look)
    tk = _tokens_of(bare)

    def rem(tok):
        m = re.search(r"([0-9.]+)rem", tk.get(tok, ""))
        return float(m.group(1)) if m else None

    h2 = re.search(r"\bh2\{[^}]*?font\s*:\s*\d+\s+var\((--t-[a-z]+)\)",
                   look)
    bodyf = re.search(r"\bbody\{[^}]*?font\s*:\s*\d+\s+var\((--t-[a-z]+)\)",
                      look, re.S)
    if not h2 or not bodyf:
        bad.append("не прочитан кегль h2 или body — сравнивать нечего")
    else:
        a, b = rem(h2.group(1)), rem(bodyf.group(1))
        if a is None or b is None:
            bad.append("кегль h2 или body не выражен в rem")
        elif a < b:
            bad.append("заголовок раздела %.4frem мельче текста %.4frem"
                       % (a, b))
    return bad[:20]


# Отступы, которые НЕ выводятся из шага, и почему каждый из них таков.
# Список объявлен, потому что удобный белый список ослепил у нас гейт: пустой
# он кричит, слепой молчит. Каждая строка — величина ЧУЖОЙ природы.
SPACING_EXEMPT = {
    "300px": "ширина рекламной башни: размер инвентаря, а не ритма",
    "336px": "формат объявления", "728px": "формат объявления",
    "970px": "формат объявления", "250px": "формат объявления",
    "280px": "формат объявления", "90px": "формат объявления",
    "600px": "формат объявления", "250px": "формат объявления",
    "1008px": "перелом колонок: считается из ширины башни и зазора",
    "544px": "перелом узких полей",
    "332px": "перелом формата объявления",
    "368px": "перелом формата объявления",
    "1109px": "перелом формата объявления",
    "1351px": "перелом формата объявления",
    "1px": "толщина скрытой skip-ссылки, а не отступ",
}


def g_spacing_from_one_unit(files):
    """Каждый отступ выведен из ОДНОГО шага, и результат — целое число.

    Шаг был объявлен (--u:7px) и почти соблюдался, но рядом с ним лежали
    набранные руками 2px четырежды, 3px трижды и 4px дважды, а множители .8
    и 1.4 давали 5,6 и 9,8 px. То есть ритмов было не один, а четыре, и один
    из них дробный. Шаг переведён на 8px, при котором целыми выходят .25,
    .5, .75, 1, 1.25, 1.5 и все целые множители.
    """
    bad = []
    sheets = _sheets_ship(files, bad)
    css = sheets.get("CSS", "") + sheets.get("AD_CSS", "")
    bare, _d, _p = _root_blocks(sheets.get("CSS", ""))
    m_u = re.search(r"--u:(\d+)px", bare)
    if not m_u:
        return bad + ["в отданной таблице стилей нет шага --u"]
    u = int(m_u.group(1))
    body = css.replace(bare, " ")
    seen = 0
    for m in re.finditer(r"([0-9]*\.?[0-9]+)px", body):
        seen += 1
        lit = m.group(0)
        if lit in SPACING_EXEMPT:
            continue
        bad.append("отступ %s набран числом, а не выведен из шага" % lit)
    if not seen:
        bad.append("в CSS не нашлось ни одной величины в пикселях — "
                   "выборка пуста, а это провал")
    mults = re.findall(r"var\(--u\)\s*\*\s*([0-9]*\.?[0-9]+)", body)
    mults += re.findall(r"var\(--u\)\s*\*\s*([0-9]*\.?[0-9]+)", bare)
    if not mults:
        bad.append("ни один отступ не выведен из шага — выборка пуста")
    # Разрешение, которым никто не пользуется, — не милость, а дыра:
    # удобный белый список однажды ослепил у нас гейт целиком, и
    # пустая выборка кричит, а слепая молчит. Каждое исключение
    # обязано быть ВОСТРЕБОВАНО тем самым CSS, который его просил.
    stale = sorted(set(SPACING_EXEMPT) -
                   set(re.findall(r"[0-9]*\.?[0-9]+px", body)))
    if stale:
        bad.append("исключение из ритма больше никем не занято: %s"
                   % ", ".join(stale[:6]))
    for k in sorted(set(mults)):
        px = float(k) * u
        if abs(px - round(px)) > 1e-9:
            bad.append("множитель %s даёт %.2f px — дробный ритм" % (k, px))
    # Множителей должно быть НЕСКОЛЬКО: ритм, выродившийся в одно число, —
    # это отсутствие ритма, и такое у нас на ферме уже было.
    if len(set(mults)) < 4:
        bad.append("все отступы свелись к %d множителям — это не ритм"
                   % len(set(mults)))
    return bad[:20]


def _painted_slot(cls, view, css):
    """Что РИСУЕТ CSS для этого места при этой ширине экрана.

    Читается сам текст правил: базовое объявление плюс медиазапросы по
    порядку. Гейт, спрашивающий у той же функции, которая рисует, согласится
    сам с собой при любом ответе.
    """
    got = None
    for m in re.finditer(r"(?:@media \((min|max)-width:(\d+)px\)\{)?"
                         r"\.%s\{width:(\d+)px;height:(\d+)px\}"
                         % re.escape(cls), css):
        kind, edge, w, h = m.group(1), m.group(2), int(m.group(3)), \
            int(m.group(4))
        if kind is None:
            got = (w, h)
        elif kind == "max" and view <= int(edge):
            got = (w, h)
        elif kind == "min" and view >= int(edge):
            got = (w, h)
    return got


def g_ad_format_fits_column(files):
    """Формат объявления ВЛЕЗАЕТ в колонку, и проверено это на каждой ширине.

    Реклама перекрывала башню на 47 пикселей в полосе 1009-1083 px. В CSS
    стояло 728 px, в объявлении AD_SLOTS стояло 728 px, гейт сверял 728 с 728
    и был прав — а КОНТЕЙНЕР не мерил никто, полосы прокрутки при этом не
    появлялось, и на экране ничего не выглядело сломанным. Здесь сверяются
    ДВЕ РАЗНЫЕ вещи: то, что рисует текст CSS, и то, что позволяет геометрия
    колонки, посчитанная из шага, полей, зазора и ширины башни.
    """
    import design
    bad = []
    css = _sheets_ship(files, bad).get("AD_CSS", "")
    L = design.layout()
    checked = 0
    for cls in sorted(design.AD_SLOTS):
        for view in range(design.MIN_VIEW, design.MAX_VIEW + 1):
            checked += 1
            want = design.slot_for(cls, view, L)
            got = _painted_slot(cls, view, css)
            room = design.holder_px(cls, view, L)
            if got is None:
                bad.append("%s: при %d px CSS не рисует места вовсе"
                           % (cls, view))
            elif got[0] > room:
                bad.append("%s: при %d px нарисовано %dx%d в контейнер %d px "
                           "— наедет на соседа без всякой прокрутки"
                           % (cls, view, got[0], got[1], room))
            elif want != got:
                bad.append("%s: при %d px влезает %s, а нарисовано %s"
                           % (cls, view, want, got))
            if len(bad) > 6:
                return bad
    if not checked:
        bad.append("не проверено ни одной ширины — пустая выборка это провал")
    return bad


def g_answer_above_reference(files):
    """Ответ стоит ВЫШЕ справочных величин в самой разметке.

    Замер в браузере: таблица замен начиналась на 912-м пикселе при экране
    1024x800 и на 1061-м при 375x667 — полторы высоты экрана прокрутки до
    того, ради чего сайт существует. Выше неё стояли чужие маркировки этого
    же элемента, полоса его характеристик, шкала и целый раздел прозы, то
    есть всё про элемент, который у человека УЖЕ В РУКЕ.

    Порядок проверяется по РАЗМЕТКЕ, а не по пикселям: пиксели зависят от
    ширины экрана, а порядок — нет, и именно порядок мы задаём.
    """
    bad = []
    cells = _cells(files)
    if not cells:
        return ["страниц элементов нет — пустая выборка это провал"]
    seen = 0
    for p, t in sorted(cells.items()):
        col = _main_col(t)
        if col is None:
            bad.append("%s: основная колонка не нашлась" % p)
            continue
        # Класс bx-fits носят ДВЕ таблицы: «что подойдёт в этот отсек»
        # и «куда подойдёт этот элемент». Первая по разметке — не то
        # же самое, что ответ, и на страницах без первой таблицы гейт
        # мерил бы расстояние до второй. Ответ помечен ЯВНО.
        ans = col.find('id="fits"')
        if ans < 0:
            continue          # страница без таблицы замен: проверять нечего
        seen += 1
        for cls, what in (("bx-strip", "полоса характеристик"),
                          ("bx-also", "чужие маркировки"),
                          ("bx-scale-v", "шкала напряжения")):
            i = col.find('class="%s"' % cls)
            if 0 <= i < ans:
                bad.append("%s: %s стоит выше таблицы замен" % (p, what))
        h1 = col.find("<h1")
        if h1 < 0 or h1 > ans:
            bad.append("%s: заголовок не выше ответа" % p)
    if not seen:
        bad.append("ни одной таблицы замен не нашлось — выборка пуста")
    return bad[:20]


# ------------------------------------------- НАЙДЕННОЕ АУДИТОМ СЕНТЯБРЯ 2026
#
# Шесть гейтов ниже куплены находками, каждая из которых проехала мимо
# тридцати четырёх зелёных гейтов. Общий у них вопрос один и тот же, и он не
# «есть ли правило», а «НА КАКОМ МНОЖЕСТВЕ оно проверено» и «ОТКУДА взялся
# эталон». Правило, верное на страницах элементов и не проверенное на
# витрине; проверка вывода той функцией, которая его и породила; картинка,
# рисующая одно и то же для 3% и для 700%, — это три вида одной ошибки.

_IN_EMPTY_PROBE = [False]

# Гейты, которых проба ПУСТОЙ ВЫБОРКОЙ не касается, и почему. Список
# ЯВНЫЙ: пропуск был написан условием внутри цикла и потому был не
# виден ниоткуда, а невидимый пропуск — ровно та дыра, которую этот
# гейт ловит у других. Пропуск, не названный здесь, роняет пробу.
EMPTY_PROBE_SKIP = {
    "пустая выборка роняет каждый гейт":
        "звал бы сам себя и ушёл бы в рекурсию; на пустой выборке "
        "краснеет по своей же первой строке",
}


def g_empty_sample_is_a_failure(files):
    """КАЖДЫЙ гейт набора краснеет, когда читать нечего.

    Двадцать пять гейтов из семидесяти печатали «пройден», не прочитав ни
    одной страницы. Два рекламных отчитывались об инвентаре, которого в
    сборке не было вовсе; шесть гейтов облика читали таблицу стилей из
    модуля и ни разу не спросили, уехала ли она на страницы; остальные
    молчали над пустым перебором.

    Разовой чисткой это не держится: следующий написанный гейт о правиле не
    знает. Поэтому правило само стало гейтом. Себя он не проверяет — иначе
    ушёл бы в рекурсию, — а на пустой выборке краснеет по своей же первой
    строке.
    """
    if _IN_EMPTY_PROBE[0]:
        return []
    bad = []
    _sample(bad, len(GATES), "гейтов в наборе")
    _sample(bad, len(files), "отданных файлов")
    if len(GATES) != GATE_COUNT:
        bad.append("гейтов %d, а объявлено %d" % (len(GATES), GATE_COUNT))
    known = dict(GATES)
    for name in sorted(EMPTY_PROBE_SKIP):
        if name not in known:
            bad.append("проба освобождает гейт, которого в наборе нет: %s"
                       % name)
    _IN_EMPTY_PROBE[0] = True
    probed = set()
    try:
        for name, fn in GATES:
            if name in EMPTY_PROBE_SKIP:
                continue
            probed.add(name)
            try:
                out = fn({})
            except Exception as exc:
                bad.append("гейт «%s» на пустой выборке падает с %s вместо "
                           "жалобы" % (name, type(exc).__name__))
                continue
            if not out:
                bad.append("гейт «%s» на пустой выборке печатает «пройден»"
                           % name)
    finally:
        _IN_EMPTY_PROBE[0] = False
    # ПОКРЫТИЕ СВЕРЯЕТСЯ С НАБОРОМ. Проба, обошедшая гейт стороной и
    # не объявившая об этом, — это тот же молчаливый пропуск этажом
    # выше: она сама выглядела бы полной, ничего не проверив.
    missed = {n for n, _ in GATES} - probed - set(EMPTY_PROBE_SKIP)
    if missed:
        bad.append("проба обошла стороной и не объявила: %s"
                   % ", ".join(sorted(missed)))
    _sample(bad, len(probed), "гейтов, опробованных пустой выборкой")
    return bad


# Типы страниц, которые поиск ОБЯЗАН находить, и типы, которые не обязан.
# Оба списка названы: тип, не попавший ни в один, роняет гейт, иначе новый
# вид страницы тихо оказался бы вне правила.
LOOKUP_MUST_FIND = ("cell", "hub")
LOOKUP_NEED_NOT_FIND = ("page", "index", "embed")


def g_lookup_finds_every_page(files):
    """Поиск находит КАЖДУЮ страницу, которую сайт публикует.

    Проверялось только одно направление — что каждая строка указателя ведёт
    на существующую страницу. Прямое не проверял никто, и сайт публиковал
    /size/aa/, /size/9v/, /size/d/, а набравший «AA», «9v» или «D» не
    получал ни строки — при том, что ссылка на ту же страницу стояла в сорока
    пикселях под полем ввода, а сообщение об отсутствии отвечало ему, что
    его код принадлежит другой компании.

    У проверки соответствия ВСЕГДА две стороны. Это вторая.
    """
    bad = []
    rows = _payload(files)
    if rows is None:
        return ["блок данных поиска отсутствует или не разбирается"]
    dest = {r["href"].split("#")[0] for r in rows if r["href"]}
    _sample(bad, len(dest), "адресов, на которые ведёт поиск")
    lost, seen = [], 0
    for p, t in sorted(_site_pages(files).items()):
        m = re.search(r'name="page-type" content="([a-z]+)"', t)
        kind = m.group(1) if m else ""
        if kind not in LOOKUP_MUST_FIND:
            if kind not in LOOKUP_NEED_NOT_FIND:
                bad.append("%s: тип страницы «%s» не объявлен ни в одном из "
                           "двух списков — область гейта неизвестна"
                           % (p, kind))
            continue
        seen += 1
        if not p.endswith("index.html"):
            bad.append("%s: страница без собственного каталога" % p)
            continue
        url = "/" + p[:-len("index.html")]
        if url not in dest:
            lost.append(url)
    _sample(bad, seen, "страниц, которые поиск обязан находить")
    if lost:
        bad.append("сайт публикует, а поиск не находит (%d): %s"
                   % (len(lost), ", ".join(sorted(lost)[:6])))
    return bad


# Геометрия, которая ОБЯЗАНА меняться вместе с величиной, и геометрия,
# которая обязана быть ПОСТОЯННОЙ, потому что кодирует постоянное. Названы
# обе стороны: полоса класса стояла «left:0;right:0» на всех 57 страницах,
# то есть не кодировала ничего, и потому её нельзя ни сделать переменной
# молча, ни оставить постоянной там, где величина у каждой страницы своя.
GEOMETRY_VARIES = "bx-scale-pin-off"
GEOMETRY_CONSTANT = "bx-scale-band"


def g_graphic_geometry_varies(files):
    """Рисунок, взявшийся кодировать величину, МЕНЯЕТ ради неё форму.

    Все 57 шкал рисовали одну и ту же картинку: полоса от края до края, 133
    штриха из 160 ровно на 0% или на 100%, потому что ось нормировалась на
    крайние значения самой страницы. Разница в 3% и разница в 700% выходили
    двумя одинаковыми чёрточками под одной и той же подписью. Каждое число
    на странице было верным — неверным было КОДИРОВАНИЕ, и это ровно тот
    класс, на котором неравные корзины гистограммы, нарисованные равной
    шириной, выдумали у нас заголовочное утверждение на 318 страницах.

    Гейт считает ПО ВСЕМУ КОРПУСУ, а не по странице: соседний гейт
    пересчитывает каждый штрих из напряжений и на одинаковой картинке тоже
    покраснел бы, но лишь потому, что арифметика разошлась. Здесь вопрос
    другой и проверяется он прямо: РАЗНЫЕ величины обязаны получать РАЗНУЮ
    геометрию, порядок мест обязан следовать порядку величин, а то, что
    объявлено постоянным, обязано быть постоянным.
    """
    bad = []
    _sample(bad, len(_html(files)), "страниц")
    by_q, by_geo, const, widgets = {}, {}, set(), 0
    for p, t in sorted(_html(files).items()):
        body = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        for m in re.finditer(r'<div class="bx-scale-v"[^>]*aria-label="'
                             r'([^"]*)">(.*?)</p></div>', body, re.S):
            widgets += 1
            label, guts = m.group(1), m.group(2)
            qs = re.findall(r"[\d.]+ V at ([-+−]?[\d.]+)%", label)
            pins = re.findall(r'class="bx-scale-pin %s" style="left:'
                              r'([\d.]+)%%"' % GEOMETRY_VARIES, guts)
            if len(qs) != len(pins):
                bad.append("%s: величин %d, штрихов %d — сопоставить нечем"
                           % (p, len(qs), len(pins)))
                continue
            for q, pos in zip(qs, pins):
                v = float(q.replace("−", "-"))
                by_q.setdefault(v, set()).add(pos)
                by_geo.setdefault(pos, set()).add(v)
            for b in re.findall(r'class="%s" style="([^"]*)"'
                                % GEOMETRY_CONSTANT, guts):
                const.add(b)
    _sample(bad, widgets, "шкал в корпусе")
    _sample(bad, len(by_geo), "различных мест штриха")
    if widgets and len(by_geo) < 2:
        bad.append("на %d шкалах место штриха принимает %d значение — "
                   "картинка одинаковая при разных величинах"
                   % (widgets, len(by_geo)))
    for pos, vals in sorted(by_geo.items()):
        spread = max(vals) - min(vals) if len(vals) > 1 else 0.0
        if spread > 0.5:
            bad.append("место left:%s%% несёт величины от %s%% до %s%% — "
                       "геометрия не различает их" % (pos, min(vals),
                                                      max(vals)))
    for v, geos in sorted(by_q.items()):
        if len(geos) > 1:
            bad.append("величина %s%% нарисована в %d разных местах: %s"
                       % (v, len(geos), sorted(geos)[:4]))
    order = sorted((v, float(sorted(g)[0])) for v, g in by_q.items())
    for i in range(1, len(order)):
        if order[i][1] < order[i - 1][1] - 1e-9:
            bad.append("порядок мест не следует за порядком величин: %s%% "
                       "стоит левее %s%%" % (order[i][0], order[i - 1][0]))
            break
    if widgets and len(const) != 1:
        bad.append("объявленная ПОСТОЯННОЙ полоса класса принимает %d "
                   "значений: %s" % (len(const), sorted(const)[:3]))
    return bad[:20]


# Известные ответы для арифметики раскладки, ПОСЧИТАННЫЕ РУКАМИ по числам,
# которые лежат в CSS: шаг 8 px, поля два шага (один шаг ниже 544), мера
# 1360, боковая колонка 300, зазор четыре шага, перелом на одну колонку 1008,
# полоса прокрутки 17.
#
#   main = min(view - 17, 1360) - 2 * поля,   и минус 300 + 32, если view > 1008
#
# Зачем: гейт «формат места влезает в колонку» сверяет нарисованное с
# holder_px() — с функцией ТОГО ЖЕ модуля. Пока её никто не проверил
# известными ответами, это была проверка одной половины design.py другой его
# половиной, а именно этим способом реклама и наехала на башню на 47 px при
# двух согласных между собой числах 728 и 728.
LAYOUT_KNOWN_CONST = {"u": 8, "pad": 16, "pad_narrow": 8, "wide": 1360,
                      "side": 300, "gap": 32, "cols_at": 1008,
                      "narrow_at": 544}
LAYOUT_KNOWN_SCROLLBAR = 17
LAYOUT_KNOWN_MAIN = ((320, 287), (375, 342), (544, 511), (545, 496),
                     (768, 719), (1008, 959), (1009, 628), (1084, 703),
                     (1109, 728), (1351, 970), (1600, 996))
LAYOUT_KNOWN_HOLDER = (("bx-ad-tower", 1008, 959), ("bx-ad-tower", 1009, 300),
                       ("bx-ad-tower", 1600, 300), ("bx-ad-flow", 375, 342),
                       ("bx-ad-flow", 1009, 628), ("bx-ad-flow", 1109, 728))
LAYOUT_KNOWN_SLOT = (("bx-ad-flow", 320, (250, 250)),
                     ("bx-ad-flow", 375, (336, 280)),
                     ("bx-ad-flow", 1084, (336, 280)),
                     ("bx-ad-flow", 1109, (728, 90)),
                     ("bx-ad-flow", 1351, (970, 250)),
                     ("bx-ad-tower", 375, (300, 250)),
                     ("bx-ad-tower", 1009, (300, 600)))


def g_layout_arithmetic_known_answers(files):
    """Ширина колонки и выбор формата сверены с ОТВЕТАМИ, набранными руками.

    Соседний гейт спрашивает у design.holder_px(), сколько места есть, и
    сравнивает с тем, что рисует CSS. Обе стороны живут в одном модуле, и
    гейт, сверяющий вывод с функцией, которая его породила, остаётся зелёным
    ровно тогда, когда функция сломана. Ответы ниже посчитаны по числам CSS
    арифметикой на бумаге; если раскладку меняют осознанно, таблицу надо
    пересчитать — и то, что гейт при этом краснеет, и есть его работа.
    """
    import design
    bad = []
    _sample(bad, len(LAYOUT_KNOWN_MAIN), "известных ответов о ширине колонки")
    _sample(bad, len(_html(files)), "страниц")
    if design.SCROLLBAR != LAYOUT_KNOWN_SCROLLBAR:
        bad.append("резерв под полосу прокрутки %s, известный ответ %s"
                   % (design.SCROLLBAR, LAYOUT_KNOWN_SCROLLBAR))
    L = design.layout()
    for k, want in sorted(LAYOUT_KNOWN_CONST.items()):
        if L.get(k) != want:
            bad.append("раскладка: %s = %s, известный ответ %s"
                       % (k, L.get(k), want))
    if bad:
        # Дальше считать нечего: расхождение в константах объяснит любую
        # разницу ниже и утопит настоящую находку в шуме.
        return bad
    for view, want in LAYOUT_KNOWN_MAIN:
        got = design.main_px(view, L)
        if got != want:
            bad.append("основная колонка при %d px = %s, известный ответ %s"
                       % (view, got, want))
    for cls, view, want in LAYOUT_KNOWN_HOLDER:
        got = design.holder_px(cls, view, L)
        if got != want:
            bad.append("контейнер %s при %d px = %s, известный ответ %s"
                       % (cls, view, got, want))
    for cls, view, want in LAYOUT_KNOWN_SLOT:
        got = design.slot_for(cls, view, L)
        if tuple(got) != tuple(want):
            bad.append("формат %s при %d px = %s, известный ответ %s"
                       % (cls, view, got, want))
    # И правило, которое эти числа существуют чтобы держать: НИ НА ОДНОЙ
    # ширине выбранный формат не шире своего контейнера.
    for cls in sorted(design.AD_SLOTS):
        for view in range(design.MIN_VIEW, design.MAX_VIEW + 1):
            w = design.slot_for(cls, view, L)[0]
            if w > design.holder_px(cls, view, L):
                bad.append("%s при %d px: формат %d px в контейнер %d px"
                           % (cls, view, w, design.holder_px(cls, view, L)))
                break
    return bad[:20]


# Слова, которыми ПОДВОДКА называет последствие по напряжению, и класс,
# который каждое из них обещает. Набраны ЗДЕСЬ РУКАМИ, а не взяты у prose:
# гейт, берущий словарь у проверяемого, сверяет функцию ею же самой. Ниже
# стоит и обратная сверка — каждый класс из prose.V_TAG обязан быть здесь
# назван, иначе новый класс проедет мимо правила молча.
LEAD_CLASS_WORDS = (("a higher voltage class", "wrong"),
                    ("a lower voltage class", "wrong"),
                    ("which reads high", "calibration"),
                    ("which reads low", "calibration"),
                    ("a shade high", "minor"),
                    ("a shade low", "minor"))


def g_lead_class_follows_ratio(files):
    """Класс последствия, названный В ПОДВОДКЕ, следует из ОТНОШЕНИЯ вольт.

    Соседний гейт требует, чтобы вердикт посадки в прозе нёс рядом с собой
    напряжение. Этого мало: напряжение стояло рядом и БЫЛО НАЗВАНО НЕ ТЕМ
    КЛАССОМ. «The closest listed cell, A27, fits but sits lower» стояло на 23
    страницах при переходе 1,5 -> 12 В, то есть при +700%; один и тот же
    напечатанный «-20,0%» был «wrong class» на 14 строках и «reads off» на
    трёх. Абзацем ниже те же страницы писали верное — противоречили себе, и
    неверной была та половина, которая выше сгиба и которую цитирует поиск.

    Гейт берёт ДВА НАПРЯЖЕНИЯ, напечатанных в одном предложении, считает
    класс двумя проверенными функциями и требует, чтобы слово подводки было
    словом этого класса. Сверяются обе стороны: и оговорка при разнице, и
    обещание «то же напряжение» — «7.2H5 carries the same 7.2 V» уже стояло
    у нас на девятивольтовой странице, где «то же» указывало на соседа.
    """
    import cells as Cx
    bad = []
    known = {k for _w, k in LEAD_CLASS_WORDS} | {"same"}
    missing = sorted(set(P.V_TAG) - known)
    if missing:
        return ["класс последствия не заведён в гейте: %s"
                % ", ".join(missing)]
    pages = _cells(files)
    _sample(bad, len(pages), "страниц элементов")
    words = "|".join(re.escape(w) for w, _k in LEAD_CLASS_WORDS)
    dash = r"(?:-|&mdash;|—)"
    rx_gap = re.compile(r"runs ([\d.]+) V %s ([-+−]?[\d.]+)%%, (%s)"
                        % (dash, words))
    rx_same = re.compile(r"(?:runs|at) the same ([\d.]+) V")
    gaps = sames = 0
    for p, t in sorted(pages.items()):
        m = re.search(r'<p class="bx-lead">(.*?)</p>', t, re.S)
        if not m:
            bad.append("%s: нет подводки" % p)
            continue
        lead = _text(m.group(1))
        mv = re.search(r"([\d.]+) V", lead)
        if not mv:
            continue
        mine = float(mv.group(1))
        for g in rx_gap.finditer(lead):
            gaps += 1
            other, shown, said = float(g.group(1)), g.group(2), g.group(3)
            klass = Cx.consequence_class(Cx.signed_ratio(mine, other))
            want = dict(LEAD_CLASS_WORDS)[said]
            if klass != want:
                bad.append("%s: «%s» обещает класс %s, а %s В против %s В "
                           "даёт %s" % (p, said, want, other, mine, klass))
            pct = float(shown.replace("−", "-"))
            got = Cx.signed_pct(Cx.signed_ratio(mine, other))
            near = 0.51 if abs(got) >= 100 else 0.051
            if abs(got - pct) > near and abs(round(got) - pct) > near:
                bad.append("%s: напечатано %s%%, а %s В против %s В даёт %s%%"
                           % (p, shown, other, mine, got))
        for s in rx_same.finditer(lead):
            sames += 1
            v = float(s.group(1))
            if Cx.consequence_class(Cx.signed_ratio(mine, v)) != "same":
                bad.append("%s: подводка обещает «то же напряжение» на %s В, "
                           "а у этого элемента %s В" % (p, v, mine))
    _sample(bad, gaps, "оговорок класса в подводках")
    _sample(bad, sames, "обещаний «то же напряжение» в подводках")
    return bad[:20]


def _members_of(page_html):
    """Сколько строк в ПЕРВОЙ таблице страницы, не считая шапки."""
    m = re.search(r"<table[^>]*>(.*?)</table>", page_html, re.S)
    if not m:
        return None
    return len(re.findall(r"<tr[^>]*><th>", m.group(1))) - 1


def g_cross_page_counts_agree(files):
    """Число, названное в прозе, ПОСЧИТАНО по тому, о чём оно говорит, —
    и когда говорит о другой странице тоже.

    «717 entries» стояло над 715 обозначениями; «every one of them delivers
    1.5 V» стояло над таблицей, где напряжение первой строки — «unknown»;
    главная называла 133 снятых, а витрина в четырёх абзацах ниже — 125.
    Гейт чисел проверял шесть названных поимённо фраз на пяти страницах;
    остальные счётные утверждения не читал никто.

    Здесь считаются три семейства, и все три — по СОДЕРЖИМОМУ, а не по
    шаблону:
      · витрина оболочки или типоразмера обещает N обозначений — в её
        собственной таблице обязано быть N строк;
      · страница элемента говорит «оболочка держит N» — на ТОЙ странице
        обязано быть N строк; а если страницы у оболочки нет, N обязано быть
        меньше наименьшей оболочки, у которой страница есть (иначе она бы
        существовала);
      · одно и то же число о снятых на главной и на витрине снятых.
    Правило ловит расхождение В ОБЕ СТОРОНЫ: и когда проза обещает больше
    посчитанного, и когда меньше.
    """
    bad = []
    hubs = {p: t for p, t in _html(files).items()
            if 'name="page-type" content="hub"' in t}
    _sample(bad, len(hubs), "витрин")
    for p, t in sorted(hubs.items()):
        lead = re.search(r'<p class="bx-lead">(.*?)</p>', t, re.S)
        if not lead:
            bad.append("%s: нет подводки" % p)
            continue
        m = re.search(r"(\d+) designations? (?:carry|share)", _text(lead.group(1)))
        rows = _members_of(t)
        if not m:
            bad.append("%s: витрина не называет, сколько обозначений несёт" % p)
        elif rows is None:
            bad.append("%s: витрина обещает %s обозначений и не показывает "
                       "таблицы" % (p, m.group(1)))
        elif int(m.group(1)) != rows:
            bad.append("%s: обещано %s обозначений, в таблице строк %d"
                       % (p, m.group(1), rows))

    sizes = [_members_of(t) for t in hubs.values()
             if _members_of(t) is not None]
    shells = [_members_of(files[p]) for p in files
              if p.startswith("shell/") and p.endswith("index.html")]
    shells = [x for x in shells if x is not None]
    _sample(bad, len(shells), "страниц оболочек")
    floor = min(shells) if shells else 0

    said = 0
    for p, t in sorted(_cells(files).items()):
        m = re.search(r"against a shell that holds (\d+) designations?",
                      _text(t))
        if not m:
            continue
        said += 1
        n = int(m.group(1))
        links = sorted(set(re.findall(r'href="(/shell/[^"]+)"', t)))
        if links:
            rows = _members_of(files.get(links[0].strip("/") + "/index.html",
                                         ""))
            if rows is None:
                bad.append("%s: ссылается на %s, а таблицы там нет"
                           % (p, links[0]))
            elif rows != n:
                bad.append("%s: обещает оболочку на %d, а на %s строк %d"
                           % (p, n, links[0], rows))
        elif n >= floor:
            bad.append("%s: обещает оболочку на %d обозначений и не ведёт на "
                       "неё, хотя страницу заводят уже с %d"
                       % (p, n, floor))
    _sample(bad, said, "фраз об оболочке на страницах элементов")

    home = _text(files.get("index.html", ""))
    gone = _text(files.get("discontinued/index.html", ""))
    a = re.search(r"against (\d+) it does not", home)
    b = re.search(r"(\d+) designations no longer have a part", gone)
    if not a:
        bad.append("главная не называет, скольких Energizer больше не несёт")
    if not b:
        bad.append("витрина снятых не называет своего числа")
    if a and b and a.group(1) != b.group(1):
        bad.append("главная говорит о %s снятых, витрина снятых — о %s"
                   % (a.group(1), b.group(1)))
    _sample(bad, len(sizes), "таблиц витрин")
    return bad[:20]


# ------------------- взаимность вердикта, проза против таблицы, виджет, ширина

# Две таблицы замен на странице элемента, названные СВОИМ первым столбцом.
# Столбец напряжения у них теперь ОДИН И ТОТ ЖЕ и по имени, и по рамке —
# отличать таблицы по нему больше нельзя, да и нечестно было: рамка перестала
# быть свойством таблицы и стала свойством САЙТА.
T_LIVE = "<th>Cell</th>"            # что ещё выпускается и встаёт сюда
T_GONE = "<th>Discontinued cell</th>"   # во что этот элемент можно поставить


def _fits_rows(html, want_head):
    """Строки таблицы замен, у которой ПЕРВЫЙ столбец назван want_head.

    Рамка у обеих одна: процент отсчитан от элемента ЭТОЙ страницы и
    относится к элементу СТРОКИ, чьё напряжение напечатано рядом. Возвращает
    {код: {class, tag, pct, volts}}.
    """
    body = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    rows = {}
    for tb in re.finditer(r'<table class="bx-fits">(.*?)</table>', body, re.S):
        # Шапка ОТРЕЗАЕТСЯ, и строки читаются ПОРОЗНЬ. Пока разбор шёл одним
        # выражением по всей таблице, «.*?» перескакивал из строки шапки в
        # первую строку тела: у каждой таблицы появлялась запись с кодом
        # «Cell», а первая настоящая строка пропадала из выборки — то есть
        # именно та, о которой чаще всего и говорит проза.
        parts = tb.group(1).split("</thead>")
        if want_head not in parts[0]:
            continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", parts[-1], re.S):
            cm = re.match(r"<th[^>]*>(?:<a[^>]*>)?([^<]+?)(?:</a>)?</th>", row)
            vm = re.search(r'<td class="bx-v bx-v-([a-z]+)">(.*?)'
                           r'<span class="bx-vtag">([^<]*)</span>', row, re.S)
            if not cm or not vm:
                continue
            printed = _text(vm.group(2))
            pm = re.search(r"([-+−]?\d+(?:\.\d+)?)\s*%", printed)
            wm = re.search(r"([\d.]+)\s*V", printed)
            rows[cm.group(1).strip()] = {
                "class": vm.group(1), "tag": vm.group(3),
                "pct": (float(pm.group(1).replace("−", "-"))
                        if pm else None),
                "volts": float(wm.group(1)) if wm else None}
    return rows


# Шапки таблиц замен — ОБЕ и только они. Строка, чью шапку никто не назвал,
# не читается ни одним гейтом, и это уже случалось: правило проверялось на
# страницах элементов и нарушалось на витрине.
FITS_HEADS = (("Cell", "Fit", "Voltage", "Chemistry", "Capacity"),
              ("Discontinued cell", "Fit", "Voltage", "Chemistry"))


def _fits_census(html, p, bad):
    """Сколько строк таблиц замен на странице ЕСТЬ — против того, сколько
    прочитано.

    _fits_rows молча пропускала таблицу с незнакомой шапкой и строку, у
    которой не разобрались код или ячейка напряжения, а ещё складывала
    строки в словарь по коду — две строки с одним кодом схлопывались в
    одну. Все три пропуска были невидимы: гейт отчитывался о прочитанном и
    молчал о том, чего прочитать не смог.
    """
    body = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    seen = 0
    for tb in re.finditer(r'<table class="bx-fits">(.*?)</table>', body,
                          re.S):
        parts = tb.group(1).split("</thead>")
        head = tuple(_text(x).strip() for x in
                     re.findall(r"<th[^>]*>(.*?)</th>", parts[0], re.S))
        if head not in FITS_HEADS:
            bad.append("%s: таблица замен с шапкой %s — такой не объявлено, "
                       "её строки не читает ни один гейт" % (p, head))
            continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", parts[-1], re.S):
            seen += 1
            cm = re.match(r"<th[^>]*>(?:<a[^>]*>)?([^<]+?)(?:</a>)?</th>",
                          row)
            vm = re.search(r'<td class="bx-v bx-v-([a-z]+)">(.*?)'
                           r'<span class="bx-vtag">([^<]*)</span>', row,
                           re.S)
            if not cm or not vm:
                bad.append("%s: строка таблицы замен не разобралась и потому "
                           "не проверена: %s" % (p, _text(row)[:60]))
    return seen


def _code_of(html):
    m = re.search(r"<h1>([^<]+)</h1>", html)
    return m.group(1).strip() if m else None


def _own_volts(html):
    """Напряжение САМОГО элемента страницы — то, что напечатано в его шапке."""
    m = re.search(r'<span class="bx-val">([\d.]+)</span>'
                  r'<span class="bx-unit">V</span>', html)
    return float(m.group(1)) if m else None


_GONE_LEAD = re.compile(
    r"<h2>What this cell can stand in for</h2><p>(.*?)</p>", re.S)

# Оговорка, которой страница ОБЪЯСНЯЕТ обе таблицы. Гейт проверяет не только
# то, что она стоит, но и то, что сказанное в ней — правда: обещание «на
# другой странице знак другой» три волны стояло рядом с таблицей, где та же
# цифра с тем же знаком печаталась с обеих сторон.
GLOSS_MUST = (
    "in every table on the page, including the one listing cells no longer "
    "made",
    "A figure always belongs to the cell whose voltage is printed beside it",
    "the sign is the other one, with the figure taken against that cell "
    "instead of this one",
    "where the two run at the same voltage, both pages print zero",
)

# Подпись таблицы снятых. Она обязана называть ТУ ЖЕ рамку, что и таблица.
GONE_LEGEND = ("Voltage is measured against this cell, the same way "
               "everywhere on the page")


def g_reciprocal_verdicts_agree(files):
    """ОДНА ПАРА ЭЛЕМЕНТОВ — ОДИН ВЕРДИКТ, с какой бы из двух страниц на неё
    ни смотрели, и В КАЖДОЙ ИЗ ДВУХ ТАБЛИЦ.

    Первая беда была в мере класса: /lr14/ печатала для 1.2H3 «1.2 V -20.0%
    reads off», /1-2h3/ для LR14 — «1.5 V +25.0% wrong class». Одно
    физическое отношение, две противоположные рекомендации. Класс с тех пор
    решается по разрыву, отнесённому к БОЛЬШЕМУ номиналу.

    Вторая беда пряталась ровно там, куда гейт не смотрел. Он читал только
    таблицу «Cell» и только одиннадцать пар той формы, на которой был
    написан. У 113 пар из 278 одна сторона стоит в таблице СНЯТЫХ, и там
    процент считался от снятого, а напечатан был рядом с напряжением
    снятого: «303 — 1.55 V — -3.2%» на /lr44/ и «1.5 V -3.2%» на /303/ —
    одна и та же цифра с одним и тем же знаком на обеих страницах пары, при
    том что 303 идёт ВЫШЕ LR44. Число и напряжение в одной ячейке были про
    разные предметы.

    ОБЛАСТЬ. Все строки ОБЕИХ таблиц замен на всех страницах элементов, и
    каждая взаимная пара, найденная перебором обеих. Проверяется:
    1) ПРЕДМЕТ ЧИСЛА — напряжение в ячейке равно собственному напряжению
       элемента строки на его же странице, а процент рядом пересчитывается
       из напряжения страницы и этого напряжения;
    2) ВЗАИМНОСТЬ — класс и метка одни, знаки противоположны, а ноль стоит
       с обеих сторон ровно тогда, когда напряжения равны;
    3) ПОДВОДКА таблицы снятых — «the gap reaches N%» считается по строкам
       этой же таблицы, мерой пары;
    4) ОГОВОРКА страницы — стоит целиком и обещает ровно то, что проверено
       выше.
    Выборок шесть, и каждая обязана быть непустой: пары со стороной в
    таблице снятых и пары с РАЗНЫМИ модулями процентов названы отдельно —
    ради них гейт и написан.
    """
    import cells as Cx
    bad = []
    pages = _cells(files)
    _sample(bad, len(pages), "страниц элементов")
    by_code, tables = {}, {}
    census = 0
    for p, x in sorted(pages.items()):
        census += _fits_census(x, p, bad)
        code = _code_of(x)
        if not code:
            bad.append("%s: у страницы элемента нет кода в <h1> — её строки "
                       "выпадали из осмотра молча" % p)
            continue
        by_code[code] = p
        tables[p] = {"code": code, "volts": _own_volts(x), "html": x,
                     "live": _fits_rows(x, T_LIVE),
                     "gone": _fits_rows(x, T_GONE)}
    _sample(bad, sum(1 for t in tables.values() if t["live"]),
            "таблиц «Cell»")
    _sample(bad, sum(1 for t in tables.values() if t["gone"]),
            "таблиц «Discontinued cell»")
    _sample(bad, census, "строк таблиц замен, найденных переписью")

    # 1. Предмет числа. Проверяется КАЖДАЯ строка обеих таблиц, а не только
    # та, у которой нашлась взаимная. Перепись выше посчитала, сколько строк
    # на страницах ЕСТЬ; расхождение с прочитанным — провал, а не примечание.
    seen_rows = seen_gone_rows = 0
    for p, t in sorted(tables.items()):
        base = t["volts"]
        for kind in ("live", "gone"):
            for code, r in sorted(t[kind].items()):
                seen_rows += 1
                if kind == "gone":
                    seen_gone_rows += 1
                q = by_code.get(code)
                own = tables[q]["volts"] if q in tables else None
                if own is not None and r["volts"] is not None \
                        and abs(own - r["volts"]) > 1e-9:
                    bad.append("%s: в строке %s напечатано %s В, а сам %s "
                               "идёт при %s В — напряжение в ячейке не его"
                               % (p, code, r["volts"], code, own))
                if base and r["volts"] and r["pct"] is not None:
                    want = Cx.signed_pct(Cx.signed_ratio(base, r["volts"]))
                    near = 0.51 if abs(want) >= 100 else 0.051
                    if abs(want - r["pct"]) > near:
                        bad.append("%s: строка %s несёт %s В и %s%%, но %s В "
                                   "против %s В даёт %s%% — число и "
                                   "напряжение в одной ячейке про разные "
                                   "элементы"
                                   % (p, code, r["volts"], r["pct"],
                                      r["volts"], base, want))
                if len(bad) > 20:
                    return bad[:20]
    _sample(bad, seen_rows, "строк таблиц замен")
    _sample(bad, seen_gone_rows, "строк таблицы снятых")
    if census != seen_rows:
        bad.append("перепись насчитала %d строк таблиц замен, а прочитано "
                   "%d: разница выпала из осмотра молча" % (census, seen_rows))

    # 2. Взаимность. Пара берётся из ОБЪЕДИНЕНИЯ обеих таблиц с каждой
    # стороны: сторона пары может стоять в любой из них.
    pairs = gone_pairs = skew = zero_pairs = 0
    for p, t in sorted(tables.items()):
        me = t["code"]
        mine = dict(t["live"])
        mine.update(t["gone"])
        for code, r in sorted(mine.items()):
            q = by_code.get(code)
            if q is None or q not in tables:
                continue
            theirs = dict(tables[q]["live"])
            theirs.update(tables[q]["gone"])
            back = theirs.get(me)
            if back is None:
                continue
            pairs += 1
            if code in t["gone"] or me in tables[q]["gone"]:
                gone_pairs += 1
            if r["class"] != back["class"]:
                bad.append("%s зовёт %s «%s», а %s зовёт %s «%s» — одна пара, "
                           "два вердикта"
                           % (me, code, r["class"], code, me, back["class"]))
            if r["tag"] != back["tag"]:
                bad.append("%s: метка «%s» против «%s» на %s"
                           % (me, r["tag"], back["tag"], code))
            if r["pct"] is None or back["pct"] is None:
                bad.append("%s: у пары %s/%s процент напечатан не с обеих "
                           "сторон" % (me, me, code))
                continue
            if r["pct"] == 0.0 and back["pct"] == 0.0:
                zero_pairs += 1
                if r["volts"] and back["volts"] \
                        and abs(r["volts"] - back["volts"]) > 1e-9:
                    bad.append("%s: пара %s/%s печатает ноль с обеих сторон "
                               "при %s В против %s В"
                               % (me, me, code, r["volts"], back["volts"]))
            elif r["pct"] * back["pct"] >= 0:
                bad.append("%s: %s%% и %s%% у одной пары %s/%s — знаки не "
                           "противоположны, и с обеих страниц пара читается "
                           "одинаково"
                           % (me, r["pct"], back["pct"], me, code))
            if abs(abs(r["pct"]) - abs(back["pct"])) > 0.051:
                skew += 1
            # Оба напечатанных процента пересчитываются из ДВУХ напряжений,
            # напечатанных на этих же двух страницах. База — своя у каждой.
            if r["volts"] and back["volts"]:
                for shown, base, other in ((r["pct"], back["volts"],
                                            r["volts"]),
                                           (back["pct"], r["volts"],
                                            back["volts"])):
                    got = Cx.signed_pct(Cx.signed_ratio(base, other))
                    near = 0.51 if abs(got) >= 100 else 0.051
                    if abs(got - shown) > near:
                        bad.append("%s: %s В против %s В даёт %s%%, "
                                   "напечатано %s%%"
                                   % (me, other, base, got, shown))
            if len(bad) > 20:
                return bad[:20]
    _sample(bad, pairs, "взаимных пар страниц")
    _sample(bad, gone_pairs, "взаимных пар со стороной в таблице снятых")
    _sample(bad, zero_pairs, "взаимных пар одного напряжения")
    if pairs and not skew:
        bad.append("ни одной пары с разными модулями процентов — правило "
                   "проверено только там, где оно и так не могло сломаться")

    # 3. Подводка таблицы снятых считает разрыв по СТРОКАМ ЭТОЙ ЖЕ таблицы.
    leads = 0
    for p, t in sorted(tables.items()):
        if not t["gone"]:
            continue
        m = _GONE_LEAD.search(t["html"])
        if not m:
            bad.append("%s: у таблицы снятых нет подводки" % p)
            continue
        lead = _text(m.group(1))
        gm = re.search(r"the gap reaches ([\d.]+)%", lead)
        gaps = [Cx.gap_pct(t["volts"], r["volts"])
                for r in t["gone"].values() if r["volts"] and t["volts"]]
        gaps = [g for g in gaps if g is not None]
        if gm is None:
            if gaps and max(gaps) > Cx.V_MINOR_PCT:
                bad.append("%s: разрыв доходит до %s%%, а подводка о нём "
                           "молчит" % (p, P.pct_num(max(gaps))))
            continue
        leads += 1
        if not gaps:
            bad.append("%s: подводка называет разрыв, а в таблице нет ни "
                       "одного напряжения" % p)
            continue
        want = P.pct_num(max(gaps))
        if gm.group(1) != want:
            bad.append("%s: подводка обещает разрыв до %s%%, а строки той же "
                       "таблицы дают %s%%" % (p, gm.group(1), want))
        if len(bad) > 20:
            return bad[:20]
    _sample(bad, leads, "подводок с названным разрывом")

    # 4. Оговорка страницы. Она объясняет читателю обе таблицы сразу, и
    # проверенное выше — ровно то, что она обещает.
    for p, t in sorted(tables.items()):
        text = _text(t["html"])
        for must in GLOSS_MUST:
            if must not in text:
                bad.append("%s: оговорка не несёт «%s»" % (p, must[:48]))
                break
        if t["gone"] and GONE_LEGEND not in text:
            bad.append("%s: подпись таблицы снятых не называет рамку" % p)
        if len(bad) > 20:
            return bad[:20]
    return bad[:20]


_SIGNED_PCT = re.compile(r"[-+−]\d+(?:\.\d+)?\s*%")


def _last_code(win, *tables):
    """Обозначение, названное В ЭТОМ ЖЕ предложении ближе всего к проценту.

    Границы слева и справа обязательны: без них «R14» находится внутри
    «LR14», а «303» внутри «1303».
    """
    best, at = None, -1
    for tb in tables:
        for code in tb:
            for m in re.finditer(r"(?<![0-9A-Za-z.-])%s(?![0-9A-Za-z-])"
                                 % re.escape(code), win):
                if m.start() > at:
                    best, at = code, m.start()
    return best


def _other_volts(win, base):
    """Чужое напряжение, названное рядом с процентом."""
    vs = [float(x) for x in re.findall(r"([\d.]+) V\b", win)]
    for v in reversed(vs):
        if base is None or abs(v - base) > 1e-9:
            return v
    return None


def g_prose_ratio_matches_table(files):
    """Знаковый процент В ПРОЗЕ равен проценту В ТАБЛИЦЕ той же страницы.

    «SR54 is the same 11.6 x 3.1 mm in silver oxide: 1.55 V against this
    cell's 1.5 V, -3.2%» стояло на четырнадцати страницах, а таблица четырьмя
    сотнями слов ниже печатала для SR54 «1.55 V +3.3%». Отношение то же, а в
    абзаце перевёрнуты И база, И знак: своя арифметика в шаблоне делила на
    чужое напряжение, потому что направление подразумевалось предлогом
    «against», а не спрашивалось у данных.

    ОБЛАСТЬ. Проза — основная колонка БЕЗ таблиц и БЕЗ блока дорожки: числа
    дорожки пересчитывает гейт «шкала кодирует отклонение» из тех же двух
    функций, и дважды одно и то же не проверяется. Беззнаковые проценты
    (плотность, доля ёмкости, доля объёма) отношением напряжений не бывают
    и сюда не входят.

    Ветвление по ФОРМЕ: если рядом названо обозначение из таблицы страницы —
    сверяется со строкой этой таблицы; если названо только чужое напряжение —
    пересчитывается из двух напряжений. Обе выборки обязаны быть непустыми,
    а процент, не привязанный ни к тому ни к другому, роняет гейт: величина
    без опоры на странице — это ровно то, чем была та фраза.
    """
    import cells as Cx
    import render as rd
    bad = []
    pages = _cells(files)
    _sample(bad, len(pages), "страниц элементов")
    by_table = by_volts = 0
    for p, x in sorted(pages.items()):
        here = _fits_rows(x, T_LIVE)
        shift = _fits_rows(x, T_GONE)
        col = rd.main_column(x) or ""
        col = re.sub(r"<script.*?</script>|<style.*?</style>", " ", col,
                     flags=re.S)
        col = re.sub(r"<table.*?</table>", " ", col, flags=re.S)
        col = re.sub(r'<div class="bx-scale-v".*?</p></div>', " ", col,
                     flags=re.S)
        text = _text(col)
        mv = re.search(r'<span class="bx-val">([\d.]+)</span>'
                       r'<span class="bx-unit">V</span>', x)
        base = float(mv.group(1)) if mv else None
        for m in _SIGNED_PCT.finditer(text):
            shown = float(m.group(0).replace("−", "-").replace("%", "").strip())
            win = text[max(0, m.start() - 200):m.start()]
            code = _last_code(win, here, shift)
            if code is not None and code in here:
                by_table += 1
                got = here[code]["pct"]
                if got is None or abs(got - shown) > 0.051:
                    bad.append("%s: в прозе %s%% про %s, а в таблице той же "
                               "страницы %s%%" % (p, shown, code, got))
                continue
            if code is not None and code in shift:
                # РАМКА У ОБЕИХ ТАБЛИЦ ОДНА, и потому сверка одна: число в
                # прозе равно числу в строке И пересчитывается из двух
                # напряжений. Пока рамки было две, здесь стояла отдельная
                # ветка, требовавшая ПРОТИВОПОЛОЖНЫХ знаков у прозы и
                # строки, — она и узаконивала ячейку, где процент и
                # напряжение были про разные предметы.
                by_table += 1
                got = shift[code]["pct"]
                if got is None or abs(got - shown) > 0.051:
                    bad.append("%s: в прозе %s%% про %s, а в таблице снятых "
                               "той же страницы %s%%" % (p, shown, code, got))
                other = shift[code]["volts"]
                if base and other:
                    want = Cx.signed_pct(Cx.signed_ratio(base, other))
                    near = 0.51 if abs(want) >= 100 else 0.051
                    if abs(want - shown) > near:
                        bad.append("%s: в прозе %s%% про %s, а %s В против "
                                   "%s В даёт %s%%"
                                   % (p, shown, code, other, base, want))
                continue
            other = _other_volts(win, base)
            if other is not None and base:
                by_volts += 1
                got = Cx.signed_pct(Cx.signed_ratio(base, other))
                near = 0.51 if abs(got) >= 100 else 0.051
                if abs(got - shown) > near:
                    bad.append("%s: в прозе %s%%, а %s В против %s В даёт %s%%"
                               % (p, shown, other, base, got))
                continue
            bad.append("%s: %s%% в прозе не опирается ни на строку таблицы, "
                       "ни на пару напряжений" % (p, shown))
            if len(bad) > 20:
                return bad[:20]
    _sample(bad, by_table, "процентов, сверенных со строкой таблицы")
    _sample(bad, by_volts, "процентов, пересчитанных из двух напряжений")
    # ОБРАТНАЯ СТОРОНА ОБЛАСТИ. Правило написано для страниц элементов: там
    # есть таблица «Voltage», с которой процент и сверяется. Знаковый процент
    # в прозе любой ДРУГОЙ страницы сайта — величина, для которой правила нет
    # вовсе, и она обязана уронить гейт, а не проехать мимо него молча.
    outside = 0
    for p, x in sorted(_site_pages(files).items()):
        if p in pages:
            continue
        col = rd.main_column(x) or ""
        col = re.sub(r"<script.*?</script>|<style.*?</style>", " ", col,
                     flags=re.S)
        col = re.sub(r"<table.*?</table>", " ", col, flags=re.S)
        col = re.sub(r'<div class="bx-scale-v".*?</p></div>', " ", col,
                     flags=re.S)
        outside += 1
        for m in _SIGNED_PCT.finditer(_text(col)):
            bad.append("%s: знаковый процент %s в прозе страницы, для которой "
                       "правило сверки не написано" % (p, m.group(0)))
            break
    _sample(bad, outside, "страниц сайта вне области правила")
    return bad[:20]


# Оговорки, без которых виджет не имеет права печатать вердикт. Набраны
# ЗДЕСЬ, а не взяты у render: гейт, берущий текст у проверяемого, сверяет
# страницу ею же самой.
EMBED_MUST_SAY = (
    "Fit and voltage are separate answers",
    "never merged into one",
    "Neither of them answers chemistry",
    "Rechargeable cells are never a drop-in for primary cells regardless of "
    "size",
    "can still be the wrong cell",
)


def g_embed_verdict_carries_limits(files):
    """Виджет, публикующий вердикт, несёт оговорки ЭТОГО САЙТА ЦЕЛИКОМ.

    Сто сорок шесть виджетов печатали «drop-in, -20.0%, reads off» для
    никель-металлогидридного элемента — без столбца химии, без слова о том,
    что аккумулятор не бывает прямой заменой, без границ применимости и без
    единого способа узнать всё это со страницы, на которую их вставили. А
    вставляют их на форум и в ремонтную заметку, где контекста нет вовсе и
    вернуться некуда: обратная ссылка — не оговорка.

    ОБЛАСТЬ ГЕЙТА ОБЪЯВЛЕНА ЗДЕСЬ: только виджеты. Гейт «оговорки
    безопасности на месте» выбирает страницы по метке `bx-vtag`, и виджеты в
    его выборку не входят намеренно — у них нет ни подвала, ни трёх блоков
    сайта. Пока правила для них не было вовсе, они пользовались этим молча.
    """
    bad = []
    emb = _embeds(files)
    if not emb:
        return ["виджетов ноль — пустая выборка это провал"]
    fits = set(P.FIT_WORD.values())
    verdicts = 0
    for p, x in sorted(emb.items()):
        vis = _text(x)
        head = re.search(r"<thead>(.*?)</thead>", x, re.S)
        if not head or "<th>Chemistry</th>" not in head.group(1):
            bad.append("%s: в таблице виджета нет столбца химии" % p)
        body = re.search(r"<tbody>(.*?)</tbody>", x, re.S)
        for row in re.findall(r"<tr>(.*?)</tr>", body.group(1) if body else "",
                              re.S):
            tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            if not ({_text(c).strip() for c in tds} & fits):
                continue
            verdicts += 1
            if "bx-v-" not in row:
                bad.append("%s: вердикт посадки без класса напряжения" % p)
            if 'class="bx-vtag"' not in row:
                bad.append("%s: вердикт без последствия словом" % p)
            if len(tds) < 4 or not _text(tds[3]).strip():
                bad.append("%s: в строке вердикта нет химии" % p)
        for phrase in EMBED_MUST_SAY:
            if phrase not in vis:
                bad.append("%s: виджет печатает вердикт без оговорки «%s»"
                           % (p, phrase[:44]))
        if len(bad) > 20:
            return bad[:20]
    _sample(bad, verdicts, "строк вердикта в виджетах")
    # ВТОРАЯ СТОРОНА: страница обещает ровно то, что виджет несёт. «The same
    # table without the site around it» было обещанием без столбца химии и
    # без единой оговорки.
    offers = 0
    for p, x in sorted(_cells(files).items()):
        m = re.search(r'<p class="bx-src">[^<]*<a href="/embed/[^"]*">.*?</p>',
                      x, re.S)
        if not m:
            continue
        offers += 1
        said = _text(m.group(0)).lower()
        for word in ("chemistry", "limits"):
            if word not in said:
                bad.append("%s: страница предлагает виджет, не назвав «%s»"
                           % (p, word))
    _sample(bad, offers, "предложений виджета на страницах")
    return bad[:20]


# Самый узкий экран, на котором сайт обязан не ехать вбок, и арифметика
# ширины слова. Числа НАБРАНЫ ЗДЕСЬ РУКАМИ и проверяются замером: строка
# цитирования на главной держит литерал https://batterycross.com/data/
# latest.csv — 39 знаков моноширинного набора кеглем .875rem, то есть
# 39 * 0.6 * 14 = 327.6 px, и браузер намерил 328 px в коробке 304 px.
# Отсюда 0.6 em на знак; кегль берём самый крупный, каким на сайте набран
# текст (--t-body, 1rem = 16 px), потому что гейт обязан ошибаться в
# сторону строгости.
NARROW_VIEW = 320
CHAR_EM = 0.6
ROOT_PX = 16
BREAKERS = ("overflow-wrap:break-word", "overflow-wrap:anywhere",
            "word-break:break-all")


def _keys_of(css, prop):
    """Ключи селекторов, объявляющих это свойство: («class», имя) и
    («tag», имя). Берётся ПОСЛЕДНИЙ ключ селектора — тот, к чему правило и
    применяется."""
    keys = set()
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if prop not in body.replace(" ", "").replace("\n", ""):
            continue
        for part in sel.split(","):
            part = part.strip().split()[-1] if part.strip() else ""
            part = part.split(":")[0]
            if part.startswith("."):
                keys.add(("class", part[1:]))
            elif re.match(r"^[a-z][a-z0-9]*$", part):
                keys.add(("tag", part))
    return keys


def _runs(html):
    """Куски видимого текста ВМЕСТЕ С предками: (текст, стек (тег, классы)).

    Гейт читает видимый текст, а не разметку, но про КАЖДЫЙ кусок обязан
    знать, в чём он лежит: слово в ячейке с white-space:nowrap не переносится
    никаким правилом переноса, а слово внутри прокручиваемой коробки не
    двигает страницу вовсе.
    """
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                  flags=re.S)
    out, stack, pos = [], [], 0
    void = ("br", "meta", "link", "img", "hr", "input", "source", "col")
    for m in re.finditer(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", html):
        chunk = html[pos:m.start()]
        pos = m.end()
        if chunk.strip():
            out.append((chunk, list(stack)))
        tag = m.group(2).lower()
        if m.group(1):
            while stack and stack[-1][0] != tag:
                stack.pop()
            if stack:
                stack.pop()
        elif tag not in void and not m.group(3).endswith("/"):
            cm = re.search(r'class="([^"]*)"', m.group(3))
            stack.append((tag, set((cm.group(1) if cm else "").split())))
    return out


def _matches(stack, keys):
    for tag, classes in stack:
        if ("tag", tag) in keys:
            return True
        for c in classes:
            if ("class", c) in keys:
                return True
    return False


def g_narrow_column_holds_text(files):
    """На самом узком экране ни одно слово не уносит страницу вбок.

    Замер в браузере: documentElement.scrollWidth 336 против clientWidth 320
    НА ГЛАВНОЙ. Виновата строка цитирования — неразрывный литерал
    https://batterycross.com/data/latest.csv, 328 px в коробке 304 px при
    word-break:normal и overflow-wrap:normal. Ехала вправо вся страница
    целиком, а не одна строка.

    Стороны две, и обе обязательны.
      · Правило переноса объявлено НА ВСЁМ ТЕКСТЕ, а не на классе, который
        кто-то не забудет поставить: ловить такие литералы поимённо значит
        ждать следующего. Проверяется и у сайта, и у виджета — виджет живёт
        в чужой странице любой ширины.
      · Слово длиннее колонки не лежит там, где перенос запрещён
        (white-space:nowrap) и коробка не прокручивается. Оба множества
        селекторов ЧИТАЮТСЯ ИЗ ОТДАННОГО CSS, а не набраны здесь: правило,
        переписанное в двух местах, однажды разойдётся.
    """
    import design
    import render as rd
    bad = []
    sheets = _sheets_ship(files, bad)
    pages = _site_pages(files)
    _sample(bad, len(pages), "страниц сайта")
    if "index.html" not in pages:
        bad.append("главной нет в выборке, а мерили именно её")
    site = sheets.get("CSS", "") + sheets.get("AD_CSS", "")
    room = design.main_px(NARROW_VIEW)
    limit = int(room / (CHAR_EM * ROOT_PX))
    # ПРАВИЛО ЧИТАЕТСЯ ИЗ ОТДАННЫХ БАЙТОВ КАЖДОЙ СТРАНИЦЫ, а не из модуля:
    # браузер идёт за тем, что отдано, и «строгий CSP убил счётчик молча» на
    # этой ферме ровно потому, что сверяли намерение, а не ответ.
    checked = 0
    for x_pages in (pages, _embeds(files)):
        for p, x in sorted(x_pages.items()):
            st = re.search(r"<style>(.*?)</style>", x, re.S)
            if not st:
                bad.append("%s: на странице нет своей таблицы стилей" % p)
                continue
            m = re.search(r"(?:^|[\s};])body\s*\{([^{}]*)\}", st.group(1),
                          re.S)
            if not m:
                bad.append("%s: в отданной таблице стилей нет правила body"
                           % p)
                continue
            checked += 1
            if not any(b in re.sub(r"\s+", "", m.group(1))
                       for b in BREAKERS):
                bad.append("%s: отданный body не разрешает переносить длинное "
                           "слово, а колонка тут %d px" % (p, room))
            if len(bad) > 20:
                return bad[:20]
    _sample(bad, checked, "правил body в отданных байтах")
    _sample(bad, len(sheets), "таблиц стилей")
    if limit < 10:
        bad.append("предел длины слова вышел %d знаков — арифметика сломана"
                   % limit)
    nowrap = _keys_of(site, "white-space:nowrap")
    scroll = _keys_of(site, "overflow-x:auto")
    _sample(bad, len(nowrap), "селекторов без переноса")
    _sample(bad, len(scroll), "прокручиваемых селекторов")
    seen = long_ = 0
    for p, x in sorted(pages.items()):
        for chunk, stack in _runs(x):
            seen += 1
            for word in _text(chunk).split():
                if len(word) <= limit:
                    continue
                long_ += 1
                if _matches(stack, nowrap) and not _matches(stack, scroll):
                    bad.append("%s: «%s» — %d знаков в %d px колонки там, где "
                               "перенос запрещён и прокрутки нет"
                               % (p, word[:40], len(word), room))
        if len(bad) > 20:
            return bad[:20]
    _sample(bad, seen, "кусков видимого текста")
    if not long_:
        bad.append("слов длиннее %d знаков не нашлось вовсе — вторая половина "
                   "правила проверена не была" % limit)
    return bad[:20]


# ------------------------------------------- МЕТА-ГЕЙТ: ОТКУДА ВЗЯТ ЭТАЛОН
#
# Проверяющий не стал ломать сайт. Он сломал ГЕНЕРАТОР — по одной функции за
# раз — и получил семьдесят семь зелёных гейтов: page_words врал втрое и увёл
# двадцать страниц ниже пола в карту сайта; jaccard возвращал ноль и отбор
# перестал отсеивать близнецов; shell_form звала монетой каждый цилиндр. Гейт,
# который считает ожидаемое ТОЙ ЖЕ функцией, что напечатала проверяемое,
# соглашается сам с собой при любом ответе.
#
# Разовой чисткой это не держится: следующий написанный гейт о правиле не
# знает. Поэтому правило само стало гейтом — как «пустая выборка роняет каждый
# гейт». Механика: гейты разбираются как ТЕКСТ (ast по собственному
# исходнику), для каждой функции генератора, до которой гейт дотягивается —
# прямо или через помощника в этом файле, — ставится ЗАВЕДОМО ЛЖИВАЯ подмена,
# и каждый дотягивающийся гейт обязан покраснеть. Не обязан только тот, про
# кого ЗДЕСЬ НАПИСАНО, зачем он функцию зовёт, если не ради эталона.

# Модули генератора, чьи функции и величины могут стать эталоном.
REF_MODULES = ("cells", "prose", "render", "design", "draw", "depth")

# Функции, которым РАЗРЕШЕНО обращаться к генератору не по имени: мета-гейт
# для того и написан, чтобы подменять функции по строке, а _stub — его рука.
# Список закрытый: обращение не по имени в любом другом месте — жалоба.
DYNAMIC_REF_OK = ("_gate_reach", "g_reference_is_not_the_code_under_test",
                  "_stub", "_ref_module")

_REACH_MEMO = [None, None]


def _gate_reach():
    """(функции, величины, жалобы) — по ИСХОДНИКУ гейтов, а не по догадке.

    Разбор был устроен так, что видел РОВНО ОДНО написание: вызов вида
    rd.page_words(...). Проверяющий обошёл его дважды и оба раза остался
    зелёным — getattr(rd, "page_" + "words") и псевдоним уровня модуля
    _PLANTED = rd.page_words. Значит разбор ловил не обращение к генератору,
    а его орфографию. Теперь засчитывается ЛЮБОЕ обращение, которое видно в
    тексте:
      · rd.page_words — и вызовом, и просто именем (псевдоним берут именно
        так, а потом зовут уже своё имя);
      · псевдоним уровня модуля: QUOTE = P.QUOTE;
      · getattr(rd, "имя") с ПОСТОЯННОЙ строкой — разрешается в имя;
    а всё, что в тексте не разрешается, — getattr с вычисленным именем,
    from render import ..., __import__, importlib вне списка DYNAMIC_REF_OK —
    ОТВЕРГАЕТСЯ ЖАЛОБОЙ. Поддержать такое обращение честно нельзя: имя
    появляется во время работы, и охват стал бы догадкой.

    Обращения делятся надвое ПО ТОМУ, ЧТО ВЗЯЛИ: вызываемое (эталон
    вычисления, ему полагается лживая подмена) и величина (эталон значения,
    ей полагается пин или причина) — см. REFERENCE_CONSTS.
    """
    import importlib
    text = _sources().get("gates.py")
    if not text:
        return None, None, ["исходник гейтов не прочитан — разбирать нечего"]
    # Ключ памяти — И ТЕКСТ, И СПИСОК МОДУЛЕЙ: память, не знающая про одну
    # из своих причин, отдаёт разбор ДО изменения и молчит об этом.
    if _REACH_MEMO[0] == (text, tuple(REF_MODULES)):
        return _REACH_MEMO[1]
    say = []
    tree = ast.parse(text)
    mods = {}
    for name in REF_MODULES:
        try:
            mods[name] = importlib.import_module(name)
        except Exception as exc:
            # МОЛЧА ОСЛЕПНУТЬ НЕЛЬЗЯ. Здесь стояло mods[name] = None, и
            # модуль, переставший импортироваться, вычёркивал из охвата все
            # свои функции разом: мета-гейт печатал бы «пройден», проверив
            # на шестую часть меньше и не сказав об этом ни слова.
            mods[name] = None
            say.append("модуль генератора %s не импортируется (%s): всё, что "
                       "гейты у него берут, выпало бы из охвата молча"
                       % (name, type(exc).__name__))

    def alias_map(body, start):
        out = dict(start)
        for stmt in body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name in REF_MODULES:
                            out[a.asname or a.name] = a.name
        return out

    top = {}
    for n in tree.body:
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in REF_MODULES:
                    top[a.asname or a.name] = a.name
        if isinstance(n, ast.ImportFrom) and n.module in REF_MODULES:
            say.append("gates.py берёт имена у генератора через «from %s "
                       "import ...»: обращение без имени модуля разбор не "
                       "видит, и охват стал бы неполным молча" % n.module)

    # Псевдоним УРОВНЯ МОДУЛЯ: QUOTE = P.QUOTE. Через него функция генератора
    # попадала в гейт мимо всякого разбора вызовов.
    handle = {}
    for n in tree.body:
        if not isinstance(n, ast.Assign) or not isinstance(n.value,
                                                           ast.Attribute):
            continue
        v = n.value
        if isinstance(v.value, ast.Name) and v.value.id in top:
            mod = top[v.value.id]
            if hasattr(mods.get(mod), v.attr):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        handle[t.id] = (mod, v.attr)

    funcs = {}
    for n in tree.body:
        if not isinstance(n, ast.FunctionDef):
            continue
        al = alias_map(n.body, top)
        calls, consts, local = set(), set(), set()

        def note(mod, attr, _c=calls, _k=consts):
            if not hasattr(mods.get(mod), attr):
                return
            (_c if callable(getattr(mods[mod], attr)) else _k).add((mod, attr))

        for x in ast.walk(n):
            if isinstance(x, ast.ImportFrom) and x.module in REF_MODULES:
                say.append("%s берёт имя у генератора через «from %s "
                           "import ...»" % (n.name, x.module))
            if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name):
                mod = al.get(x.value.id)
                if mod:
                    note(mod, x.attr)
            elif isinstance(x, ast.Name) and x.id in handle:
                note(*handle[x.id])
            if not isinstance(x, ast.Call):
                continue
            f = x.func
            if isinstance(f, ast.Name):
                local.add(f.id)
            if n.name in DYNAMIC_REF_OK:
                continue
            if isinstance(f, ast.Name) and f.id in ("getattr", "setattr"):
                a0 = x.args[0] if x.args else None
                a1 = x.args[1] if len(x.args) > 1 else None
                if isinstance(a0, ast.Name) and a0.id in al:
                    if isinstance(a1, ast.Constant) and isinstance(a1.value,
                                                                   str):
                        note(al[a0.id], a1.value)
                    else:
                        say.append("%s обращается к %s через %s с вычисленным "
                                   "именем: разбор такое обращение прочитать "
                                   "не может и охват стал бы догадкой"
                                   % (n.name, al[a0.id], f.id))
            if isinstance(f, ast.Name) and f.id == "__import__":
                say.append("%s зовёт __import__: модуль, взятый во время "
                           "работы, разбор не видит" % n.name)
            if isinstance(f, ast.Attribute) and f.attr == "import_module":
                say.append("%s зовёт importlib.import_module: модуль, взятый "
                           "во время работы, разбор не видит" % n.name)
        funcs[n.name] = (calls, consts, local)

    def reach(name, seen):
        if name in seen or name not in funcs:
            return set(), set()
        seen.add(name)
        c, k, local = funcs[name]
        got_c, got_k = set(c), set(k)
        for l in local:
            a, b = reach(l, seen)
            got_c |= a
            got_k |= b
        return got_c, got_k

    invf, invk = {}, {}
    for g in sorted(name for name in funcs if name.startswith("g_")):
        c, k = reach(g, set())
        for key in c:
            invf.setdefault(key, []).append(g)
        for key in k:
            invk.setdefault(key, []).append(g)
    out = (invf, invk, say)
    _REACH_MEMO[:] = [(text, tuple(REF_MODULES)), out]
    return out


# ЗАВЕДОМО ЛЖИВАЯ подмена для каждой функции генератора, до которой
# дотягивается хоть один гейт. Ложь выбрана так, чтобы её было ВИДНО в
# проверяемом: подмена, которая случайно совпадает с правдой, ничего не
# доказывает. Стоящая рядом строка — что именно она ломает.
REFERENCE_STUBS = {
    ("cells", "_s"): lambda: (lambda row, key: "mercuric oxide"),
    # Строка, объявляющая предметом РАМКУ: ровно та подмена сторон,
    # ради которой гейт строки и написан.
    ("cells", "pair_row"): lambda: (
        lambda frame, subject: {"subject": frame["code"],
                                "frame": subject["code"],
                                "cell": frame, "fit": "drop-in",
                                "volt": None, "mah": None}),
    ("cells", "chem_canon"): lambda: (lambda name: "unspecified"),
    ("cells", "chem_from_code"): lambda: (lambda code: "alkaline"),
    ("cells", "class_edge"): lambda: (lambda sign: 0.5),
    ("cells", "consequence_class"): lambda: (
        lambda ratio: None if ratio is None
        else ("wrong" if abs(ratio) > 0.199 else "same")),
    ("cells", "full_iec_code"): lambda: (lambda cell: "LR1131"),
    ("cells", "gap_pct"): lambda: (lambda a, b: 0.0),
    ("cells", "iec_all"): lambda: (lambda row: ["LR44"]),
    ("cells", "is_coin"): lambda: (lambda cell: True),
    ("cells", "scale_position"): lambda: (
        lambda ratio: None if ratio is None
        else (50.0 if not ratio else (100.0 if ratio > 0 else 0.0))),
    ("cells", "shell_form"): lambda: (lambda s: "coin"),
    ("cells", "signed_pct"): lambda: (lambda r: 0.0),
    ("cells", "signed_ratio"): lambda: (lambda a, b: 0.0),
    ("cells", "tds_url"): lambda: (lambda name: "https://example.com/x.pdf"),
    # Ложь выбрана по СМЫСЛУ гейта: он требует плашку там, где норма
    # действует. Подмена объявляет кнопочным элементом всё подряд — тогда
    # предупреждения не хватит на 70 с лишним страницах, и гейт обязан
    # покраснеть. Ложь «ничего не кнопочное» доказала бы меньше: она
    # оставила бы выборку пустой, а пустая выборка и так провал.
    ("depth", "hazard_kind"): lambda: (lambda cell: "covered"),
    ("design", "holder_px"): lambda: (lambda cls, view, L=None: 970),
    ("design", "layout"): lambda: _lie_layout(),
    ("design", "main_px"): lambda: (lambda view, L=None: 970),
    ("design", "slot_for"): lambda: (lambda cls, view, L=None: (970, 250)),
    ("design", "strip_comments"): lambda: (lambda css: css[:40]),
    ("prose", "article"): lambda: (
        lambda w, cap=False: ("An" if cap else "an")),
    ("prose", "article_selftest"): lambda: (lambda: [("x", "a", "an")]),
    ("prose", "chem"): lambda: (lambda cell: "lithium"),
    ("prose", "pct_num"): lambda: (lambda x: "0.0"),
    ("prose", "wc"): lambda: (lambda text: 9999),
    ("render", "_index_key"): lambda: (lambda s: "x"),
    ("render", "_shingles"): lambda: (lambda text, pattern: set()),
    # Ложь: раскрытие, из которого убраны все три обязанности. Гейт
    # «раскрытие переживает подключение сети» обязан покраснеть — иначе он
    # сверяет собранное с тем, что собрал тот же код.
    ("render", "ad_privacy_block"): lambda: (
        lambda: '<p class="bx-legend" data-ads="none">No ads here.</p>'),
    ("render", "carries_ads"): lambda: (lambda path, body: True),
    ("render", "chem"): lambda: (lambda cell: "unspecified chemistry"),
    ("render", "jaccard"): lambda: (lambda a, b: 0.0),
    ("render", "main_column"): lambda: (lambda html: ""),
    ("render", "own_prose"): lambda: (
        lambda html: "one two three four five six seven eight"),
    ("render", "page_words"): lambda: (lambda html: 9999),
    ("render", "slug"): lambda: (lambda cell: "no-such-page"),
    ("render", "visible_words"): lambda: (lambda html: 9999),
    ("render", "window_for"): lambda: (lambda h2: (0, 10 ** 6)),
}

def _lie_layout():
    """Раскладка, в которой всё влезает всюду. Берётся НАСТОЯЩАЯ и портятся
    ровно две величины: подмена, роняющая гейт по KeyError, проверяет
    устойчивость к мусору, а не то, читает ли гейт эти числа."""
    import design
    L = dict(design.layout())
    L["side"] = L["main"] = 970
    return lambda css=None: dict(L)

# Гейт зовёт функцию НЕ РАДИ ЭТАЛОНА, и вот зачем. Список ЯВНЫЙ: пара, не
# попавшая ни сюда, ни в проверку, роняет мета-гейт.
NOT_A_REFERENCE = {
    ("g_ad_below_the_answer", "prose", "wc"):
        "длина куска для ПОРЯДКА на экране, а не эталон объёма: "
        "гейт смотрит, что выше чего стоит, а не сколько там слов",
}

_IN_REFERENCE_PROBE = [False]


def g_reference_is_not_the_code_under_test(files):
    """Ни один гейт не берёт ЭТАЛОН у функции, которую проверяет.

    Проверяется не намерение, а поведение: каждая функция генератора, до
    которой дотягивается гейт, подменяется заведомо лживой, и гейт обязан
    покраснеть. Гейт, оставшийся зелёным на лжи, СТРУКТУРНО не способен
    провалиться — и это видно здесь, а не через полгода и не глазами
    проверяющего.

    Три половины, и все обязательны:
      · каждая дотянутая функция объявлена — либо подменой, либо причиной,
        по которой она эталоном не является;
      · каждая объявленная подмена ДОТЯГИВАЕТСЯ хоть до одного гейта: запись
        про функцию, которую никто не зовёт, — обещание проверки, которой нет;
      · каждый неосвобождённый гейт краснеет на подмене;
      · каждый ОСВОБОЖДЁННЫЙ на ней остаётся зелёным — иначе освобождение
        не объяснение, а отговорка, скрывающая работающую проверку.

    Себя гейт не проверяет — ушёл бы в рекурсию, — а на пустой выборке
    краснеет по своей же первой строке.
    """
    if _IN_REFERENCE_PROBE[0]:
        return []
    bad = []
    _sample(bad, len(GATES), "гейтов в наборе")
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(REFERENCE_STUBS), "объявленных подмен")
    if not files:
        return bad
    inv, _consts, say = _gate_reach()
    if inv is None:
        return bad + say
    # ЖАЛОБЫ РАЗБОРА — ЭТО ПРОВАЛ, А НЕ ПРИМЕЧАНИЕ. Обращение к генератору,
    # которое разбор прочитать не может, означает не «его нет», а «мы не
    # знаем, есть ли он»: ровно так проверяющий дважды провёл мимо охвата
    # работающую подмену и оба раза получил зелёный набор.
    bad.extend(say)
    _sample(bad, len(inv), "функций генератора, дотянутых гейтами")
    by_name = dict(GATES)
    fn_name = {fn.__name__: name for name, fn in GATES}
    if len(fn_name) != len(GATES):
        bad.append("в наборе %d записей, а разных определений %d: по имени "
                   "проба найдёт не всех" % (len(GATES), len(fn_name)))

    # 0. Каждый дотянувшийся ОПРЕДЕЛЁН В НАБОРЕ. Проверяется здесь, до
    #    дорогого перебора: определение, выпавшее из набора, раньше молча
    #    пропускалось в самом переборе и проба выглядела полной.
    for key, gs in sorted(inv.items()):
        for g in gs:
            if g not in fn_name:
                bad.append("определение «%s» дотягивается до %s.%s, а гейта с "
                           "таким именем в наборе нет: проба его не касается"
                           % ((g,) + key))
    # 1. Всё дотянутое объявлено.
    for key, gs in sorted(inv.items()):
        if key in REFERENCE_STUBS:
            continue
        loose = [g for g in gs if (g,) + key not in NOT_A_REFERENCE]
        if loose:
            bad.append("%s.%s зовётся гейтами (%s), а подмены для неё не "
                       "объявлено: гейт мог бы соглашаться сам с собой"
                       % (key[0], key[1], ", ".join(loose)))
    # 2. Ничего лишнего не объявлено.
    for key in sorted(REFERENCE_STUBS):
        if key not in inv:
            bad.append("подмена для %s.%s объявлена, а ни один гейт эту "
                       "функцию не зовёт" % key)
    for trio in sorted(NOT_A_REFERENCE):
        g, mod, fn = trio
        if g not in fn_name:
            bad.append("освобождён гейт, которого нет: %s" % g)
        elif g not in inv.get((mod, fn), []):
            bad.append("гейт «%s» освобождён от %s.%s, а он её не зовёт"
                       % (g, mod, fn))
    if bad:
        return bad[:20]

    # 3. Подмена обязана покраснить каждый дотянувшийся неосвобождённый гейт.
    import importlib
    _IN_REFERENCE_PROBE[0] = True
    try:
        for key in sorted(REFERENCE_STUBS):
            mod, attr = key
            reached = inv.get(key, [])
            targets = [g for g in reached
                       if (g,) + key not in NOT_A_REFERENCE]
            excused = [g for g in reached if g not in targets]
            if not reached:
                continue
            m = importlib.import_module(mod)
            saved = getattr(m, attr)
            setattr(m, attr, REFERENCE_STUBS[key]())
            _sheets_forget()
            try:
                for g in targets + excused:
                    name = fn_name.get(g)
                    if name is None:
                        # ЗДЕСЬ СТОЯЛО «continue». Определение, которое
                        # переименовали или убрали из набора, оставив в
                        # исходнике, выпадало из пробы без единой жалобы:
                        # покрытие держалось на совпадении имени, и КАЖДОЕ
                        # несовпадение означало «проверено» вместо «не
                        # проверено». Это та самая дыра, которую мета-гейт
                        # ловит у других, — этажом выше.
                        bad.append("определение «%s» дотягивается до %s.%s, а "
                                   "гейта с таким именем в наборе нет: проба "
                                   "его не касается" % (g, mod, attr))
                        continue
                    try:
                        out = by_name[name](files)
                    except Exception as exc:
                        bad.append("гейт «%s» на подменённой %s.%s падает с "
                                   "%s вместо жалобы"
                                   % (name, mod, attr, type(exc).__name__))
                        continue
                    if g in excused:
                        # ОСВОБОЖДЕНИЕ ОБЯЗАНО БЫТЬ ПРАВДОЙ. Одно из них
                        # уже оказалось ложным: carries_ads считает слова
                        # через visible_words, и гейт краснел по-настоящему,
                        # пока запись уверяла, что функция ему не эталон.
                        if out:
                            bad.append("освобождение устарело: гейт «%s» на "
                                       "подменённой %s.%s КРАСНЕЕТ, а запись "
                                       "уверяет, что она ему не эталон"
                                       % (name, mod, attr))
                    elif not out:
                        bad.append("гейт «%s» СТРУКТУРНО не способен "
                                   "провалиться: %s.%s подменена на заведомо "
                                   "лживую, а он печатает «пройден»"
                                   % (name, mod, attr))
            finally:
                setattr(m, attr, saved)
                _sheets_forget()
    finally:
        _IN_REFERENCE_PROBE[0] = False
    return bad[:20]


# ------------------------------- МЕТА-ГЕЙТ: ОТКУДА ВЗЯТА ВЕЛИЧИНА ЭТАЛОНА
#
# Мета-гейт эталона следил за ФУНКЦИЯМИ и ничего не знал про ВЕЛИЧИНЫ, а
# гейт, взявший порог у той же строки кода, которая его напечатала,
# соглашается сам с собой ровно так же. Стоило это уже дорого: render.
# FLOOR_EXEMPT постранично выключает пол объёма, гейт читал ТОТ ЖЕ список,
# и семь настоящих тонких страниц, дописанных в него, уехали бы в карту
# сайта при всех зелёных гейтах — 123 слова при объявленном поле в 1500.
#
# Вид объявления — часть объявления:
#   ("pin", значение)     величина набрана ЗДЕСЬ РУКАМИ и обязана совпасть;
#   ("size", n, образцы)  для таблиц, которые руками не набрать: длина и
#                         несколько записей, набранные руками;
#   ("why", причина)      почему ни то ни другое невозможно и ЧТО отвечает
#                         за величину вместо пина.
REFERENCE_CONSTS = {
    # Допуск посадки. Гейт строки считает вердикт САМ, и порог, взятый
    # у проверяемого без пина, дал бы ему согласиться с изменённым
    # порогом молча.
    ("cells", "FIT_MM"): ("pin", 0.3),
    ("cells", "V_MINOR_PCT"): ("pin", 6.0),
    ("cells", "V_SERIOUS_PCT"): ("pin", 20.0),
    ("cells", "TRADE_MARKINGS"): ("size", 53, (
        ("AG13", "LR1154", "importers"), ("ZA10", "PR70", "hearing"))),
    # Пороги публикации. Оба стояли в прозе СЛОВОМ «three» и потому не
    # сверялись ни с чем: подмена MIN_HUB на 4 прошла 88 гейтов из 88, сайт
    # публиковал шесть оболочек при пороге 4 и писал «три». Пин здесь —
    # вторая половина той же починки: гейт читает константу, и константа
    # прибита руками.
    # Наборы, чья ДЛИНА печатается на странице. Объявлены здесь, потому что
    # гейт сверяет напечатанное число с длиной набора, и набор, изменившийся
    # молча, изменил бы и число, и проверку разом.
    ("cells", "FACT_KINDS"): ("size", 7, (
        ("repl", "whether one cell fits where another sat and in what sense"),
        ("code", "a check of the designation against the measured size"))),
    ("cells", "DATA_FILES"): ("size", 1, ()),
    ("render", "ANSWER_COLUMNS"): ("pin", ("Fit", "Voltage", "Chemistry")),
    ("prose", "CANNOT_SEE"): ("size", 3, (
        "Whether the contacts reach a shorter cell.",)),
    ("render", "MIN_HUB"): ("pin", 3),
    ("render", "MIN_FACTS"): ("pin", 3),
    ("depth", "ALARM_VOLTS"): ("pin", (8.4, 9.6)),
    ("depth", "INGEST_MM"): ("pin", 16.0),
    ("depth", "HEAD_KIND"): ("size", 40, (
        "What a lithium coin is asked to hold",
        "What the datasheet does not say")),
    ("render", "FIND_TOL_MM"): ("pin", 1),
    ("render", "THIRD_PARTIES"): ("pin", ()),
    ("render", "FINDER"): ("why",
                           "гейт «поиск отвечает по габариту» ИСПОЛНЯЕТ этот "
                           "код поверх отданного указателя и сверяет ответ с "
                           "указателем; перенабрать его здесь значило бы "
                           "сверять код с его же копией"),
    ("design", "MIN_VIEW"): ("pin", 320),
    ("design", "MAX_VIEW"): ("pin", 1600),
    ("design", "SCROLLBAR"): ("pin", 17),
    ("design", "AD_SLOTS"): ("pin", {
        "bx-ad-flow": {"cols": [(970, 250), (728, 90), (336, 280),
                                (300, 250), (250, 250)],
                       "one": [(336, 280), (300, 250), (250, 250)]},
        "bx-ad-tower": {"cols": [(300, 600)],
                        "one": [(300, 250), (250, 250)]}}),
    ("render", "AD_SLOTS"): ("pin", {
        "bx-ad-flow": {"cols": [(970, 250), (728, 90), (336, 280),
                                (300, 250), (250, 250)],
                       "one": [(336, 280), (300, 250), (250, 250)]},
        "bx-ad-tower": {"cols": [(300, 600)],
                        "one": [(300, 250), (250, 250)]}}),
    ("design", "CSS"): ("why",
                        "лист сверяется ПОБАЙТОВО с отданными байтами в "
                        "_sheets_read; набрать его здесь второй раз значило "
                        "бы переписать весь облик, и вопрос «уехало ли на "
                        "страницы ровно это» так и остался бы незакрытым"),
    ("design", "AD_CSS"): ("why",
                           "то же: рекламная половина отданной таблицы "
                           "сверяется побайтово в _sheets_read"),
    ("render", "EMBED_CSS"): ("why",
                              "то же: лист виджета сверяется побайтово с "
                              "отданными байтами в _sheets_read"),
    ("render", "CELLS"): ("why",
                          "это САМИ ДАННЫЕ, а не эталон вычисления: их "
                          "сверяет со снимком поставщика «вытисненное "
                          "прослеживается до снимка», а с опубликованным "
                          "набором — «набор данных опубликован и сходится»"),
    ("prose", "QUOTE"): ("pin", chr(34)),
    ("prose", "CONSTANT_HEADS"): ("pin", ("Before you swap anything",
                                          "Where these numbers come from")),
    ("prose", "FIT_WORD"): ("pin", {"drop-in": "drop-in",
                                    "shorter": "sits lower",
                                    "taller": "too tall",
                                    "wider": "too wide",
                                    "narrower": "too narrow"}),
    ("prose", "POPULAR_SIZES"): ("pin", ("AA", "AAA", "AAAA", "C", "D", "N",
                                         "9V", "J", "F", "Lantern")),
    ("prose", "V_TAG"): ("pin", {"same": "same volts",
                                 "minor": "close enough",
                                 "calibration": "reads off",
                                 "wrong": "wrong class"}),
    ("render", "AD_MIN_WORDS"): ("pin", 300),
    ("render", "CONTACT"): ("pin", "hello@batterycross.com"),
    ("render", "DATASET_LATEST"): ("pin", "/data/latest.csv"),
    ("render", "DATASET_PATH"): ("pin", "/data/batterycross-cells-%s.csv"),
    ("render", "DATA_SNAPSHOT"): ("pin", _date(2026, 9, 1)),
    ("render", "FIGURE_HEADS"): ("pin", ("Drawn to scale",)),
    # ВОТ РАДИ ЧЕГО ВСЁ ЭТО. Список выключает пол объёма постранично, и он
    # был единственной величиной этого правила, не прибитой руками: порог
    # 1500 прибит, пороги близнецов прибиты, порог инвентаря прибит, а
    # список исключений — нет. Семь настоящих тонких страниц, дописанных в
    # него, оставляли все гейты зелёными.
    ("render", "FLOOR_EXEMPT"): ("pin", ("/privacy/", "/terms/", "/contact/",
                                         "/about/", "/404.html")),
    ("render", "INDEX_META"): ("pin", '<meta name="robots" content="index, '
                                      'follow, max-image-preview:large">'),
    ("render", "INTRO_HEADS"): ("pin", (
        "What fits the compartment, and what does not",
        "What the chemistry changes",
        "What this cell can stand in for",
        "Every published figure",
        "Cells measured next to this one")),
    ("render", "LD_TYPES"): ("pin", ("Organization", "WebSite",
                                     "BreadcrumbList", "ListItem", "Product",
                                     "PropertyValue")),
    ("render", "PUBLISHER"): ("pin", "BiLingoPlus LLC"),
    ("render", "SKEL_PAT"): ("pin", "[a-z][a-z" + chr(39) + "-]*"),
    ("render", "TEXT_PAT"): ("pin", "[a-z0-9][a-z0-9" + chr(39) + ".-]*"),
    ("render", "TWIN_TEXT"): ("pin", 0.70),
    ("render", "TWIN_SKELETON"): ("pin", 0.95),
    ("render", "WORD_FLOOR"): ("pin", 1500),
}


def _ref_module(name):
    """Модуль генератора ПО СТРОКЕ. Обращение по строке живёт здесь и в
    DYNAMIC_REF_OK: разбор такое обращение прочитать не может, поэтому мест,
    где оно разрешено, ровно столько, сколько записано."""
    import importlib
    return importlib.import_module(name)


def g_reference_constants_declared(files):
    """Каждая ВЕЛИЧИНА генератора, которую читает гейт, объявлена здесь.

    Это вторая половина правила «эталон не берётся у проверяемого». Первая
    следит за функциями: подменить функцию лживой и потребовать, чтобы гейт
    покраснел. С величиной так нельзя — подменённый порог часто и должен
    менять вердикт, — поэтому величина прибивается РУКАМИ здесь, и
    расхождение с генератором есть провал.

    Три вида объявления и обе стороны соответствия:
      · читаемая гейтом и не объявленная — провал (гейт мог бы соглашаться
        сам с собой);
      · объявленная и никем не читаемая — тоже провал: описанный и
        несуществующий рычаг хуже отсутствующего, на него рассчитывают.
    """
    bad = []
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(REFERENCE_CONSTS), "объявленных величин генератора")
    _invf, invk, say = _gate_reach()
    if invk is None:
        return bad + say
    bad.extend(say)
    _sample(bad, len(invk), "величин генератора, читаемых гейтами")
    for key in sorted(invk):
        if key not in REFERENCE_CONSTS:
            bad.append("%s.%s читается гейтами (%s), а эталоном не объявлена: "
                       "гейт мог бы соглашаться сам с собой"
                       % (key[0], key[1], ", ".join(sorted(invk[key]))))
    for key in sorted(REFERENCE_CONSTS):
        rule = REFERENCE_CONSTS[key]
        if key not in invk:
            bad.append("величина %s.%s объявлена эталоном, а ни один гейт её "
                       "не читает" % key)
            continue
        got = getattr(_ref_module(key[0]), key[1], None)
        if rule[0] == "pin":
            if got != rule[1]:
                bad.append("%s.%s это %s, а руками здесь набрано %s"
                           % (key[0], key[1], repr(got)[:90],
                              repr(rule[1])[:90]))
        elif rule[0] == "size":
            if got is None or len(got) != rule[1]:
                bad.append("%s.%s держит %s записей, а руками объявлено %d"
                           % (key[0], key[1],
                              "нисколько" if got is None else len(got),
                              rule[1]))
            for one in rule[2]:
                if got is None or one not in got:
                    bad.append("%s.%s потеряла объявленную запись %s"
                               % (key[0], key[1], repr(one)[:60]))
        elif rule[0] == "why":
            if len(rule[1]) < 40:
                bad.append("причина для %s.%s не написана" % key)
        else:
            bad.append("для %s.%s объявлен неизвестный вид «%s»"
                       % (key[0], key[1], rule[0]))
    return bad[:20]


# --------------------------------------- МЕТА-ГЕЙТ: УЧЁТ ГЕЙТОВ И ПРОБ
#
# Мета-гейт эталона нашёл тринадцать гейтов, не способных провалиться, и сам
# оказался устроен так же: его охват держался на совпадении fn.__name__ с
# определением верхнего уровня, а КАЖДОЕ несовпадение молча пропускалось —
# «continue» вместо жалобы. Гейт, переименованный или убранный из набора при
# живом определении в исходнике, выпадал из пробы, и проба при этом
# печаталась пройденной. Здесь пересчитывается ВСЁ: определения против
# набора, набор против каждой из трёх проб, и то, что печатается как
# проверка, против того, что проверкой объявлено.

# Определения g_*, НЕ зарегистрированные в наборе, и почему. Пусто: гейт,
# лежащий в исходнике и никуда не подключённый, — это выключенная проверка,
# и выключить её можно только назвав.
GATES_NOT_REGISTERED = {}

# Гейты, которые не берут у генератора НИЧЕГО: читают только отданные байты.
# Список нужен не ради них, а ради обратной стороны: гейт, ПЕРЕСТАВШИЙ
# дотягиваться до генератора (обращение переписали через getattr или через
# псевдоним), тихо переезжает сюда — и, не будучи здесь названным, роняет
# учёт. Ровно так проверяющий дважды провёл мимо охвата работающую подмену.
NO_REFERENCE_GATES = {
    # Четыре правила облика читаются только по отданным байтам: у генератора
    # тут спрашивать нечего, правило целиком выражено в стилях и разметке.
    "g_reader_rules",
    "g_answer_above_reference",
    # Волна отношений. Оба гейта считают эталон ЗАНОВО по снимку с диска и
    # по отданным страницам и ни одной функции генератора не зовут: подменять
    # у них нечего, а величины-наборы, которые они читают, объявлены
    # эталонами в REFERENCE_CONSTS.
    "g_relations_computed",
    "g_declared_sets_match_pages",
    # Величины в прозе: ни одной ФУНКЦИИ генератора он не зовёт, и пробе
    # лживой подменой у него ловить нечего. Его эталоны — снимок с диска,
    # прибитая руками C.TRADE_MARKINGS и таблица известных ответов на
    # собственный разбор.
    # Поиск: гейт ИСПОЛНЯЕТ отданный render.FINDER с допуском
    # render.FIND_TOL_MM и сверяет ответ с указателем, вынутым из отданной
    # страницы. Обе величины объявлены эталонами; ни одной ФУНКЦИИ
    # генератора он не зовёт, и подменять у него нечего.
    "g_search_answers_by_size",
    "g_prose_quantities_declared",
    "g_readme_counts_the_gates",
    "g_chem_note_volts_from_page",
    "g_claims_scoped_to_data",
    "g_completeness_claim_counted",
    "g_control_chars",
    "g_cross_page_counts_agree",
    "g_dataset_published",
    "g_descriptions_differ",
    "g_dist_matches_build",
    "g_embed_verdict_carries_limits",
    "g_embeds_are_fragments",
    "g_empty_sample_is_a_failure",
    "g_fit_and_volts_separate",
    "g_fit_claim_carries_voltage",
    "g_gate_registry_is_complete",
    "g_gone_not_present_tense",
    "g_graphic_geometry_varies",
    "g_head",
    "g_index_has_no_dead_ends",
    "g_institutional_shell",
    "g_internal_links",
    "g_language",
    "g_links_point_at_pages",
    "g_lookup_finds_every_page",
    "g_lookup_on_every_page",
    "g_no_candidate_count",
    "g_no_double_escape",
    "g_no_empty_ad_slot",
    "g_no_external",
    "g_no_placeholder_values",
    "g_no_scripts",
    "g_no_self_links",
    "g_number_agrees_with_verb",
    "g_numbers_agree",
    "g_orphans",
    "g_privacy_matches_markup",
    "g_public_contact_own_domain",
    "g_reference_constants_declared",
    "g_reference_is_not_the_code_under_test",
    "g_robots",
    "g_safety_notice",
    "g_scale_honest",
    "g_script_builds_no_markup",
    "g_share_cards",
    "g_silent_skips_are_named",
    "g_sitemap",
    "g_stamped_codes_in_source",
    "g_structured_data_real",
}

# Проверки, которые ПЕЧАТАЮТСЯ рядом с гейтами, но гейтами не являются, и
# почему. Проверка даты содержимого печаталась как гейт, а лежала вне набора,
# вне GATE_COUNT, вне списка поломок и вне обеих проб — то есть выглядела
# восемьдесят третьим гейтом, не будучи проверенной ничем.
EXTRA_CHECKS = {
    "дата содержимого совпадает с содержимым":
        "читает не отданные файлы, а отпечаток на диске и календарь, и "
        "потому не может быть частью набора; известными ответами её чистую "
        "половину проверяет stamp_selftest, а сохранность жалобы на повторе "
        "— круговой прогон там же",
}


def g_gate_registry_is_complete(files):
    """Каждый гейт учтён по имени, и каждая проба знает, кого не осмотрела.

    Проб у набора три, и все три ищут гейт ПО ИМЕНИ ОПРЕДЕЛЕНИЯ: пустая
    выборка перебирает набор, эталон разбирает исходник, известные ответы
    держат таблицы для названных функций. Пока имя не с чем было сверить,
    любое несовпадение означало «проверено» вместо «не проверено».

    Здесь сверяется ВСЁ и в обе стороны:
      · имя и определение в наборе — по одному разу;
      · гейт — простое определение верхнего уровня: лямбда, замыкание,
        partial, обёртка декоратором и запись, положенная в набор во время
        работы, ОТВЕРГАЮТСЯ, потому что искать их пробам не по чему;
      · определение g_*, не попавшее в набор, объявлено выключенным;
      · охват каждой из трёх проб равен набору минус объявленное;
      · то, что печатается как пройденная проверка, объявлено либо гейтом,
        либо проверкой вне набора.
    """
    import types
    bad = []
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(GATES), "гейтов в наборе")
    text = _sources().get("gates.py")
    if not text:
        return bad + ["исходник гейтов не прочитан — учитывать нечего"]
    tree = ast.parse(text)
    gdefs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name.startswith("g_")}
    _sample(bad, len(gdefs), "определений гейтов в исходнике")

    names = [n for n, _ in GATES]
    for n in sorted({x for x in names if names.count(x) > 1}):
        bad.append("имя гейта «%s» стоит в наборе %d раза"
                   % (n, names.count(n)))
    twice = {}
    for n, fn in GATES:
        twice.setdefault(id(fn), []).append(n)
    for who in sorted(twice.values()):
        if len(who) > 1:
            bad.append("одно определение зарегистрировано под именами: %s"
                       % ", ".join(who))
    if len(GATES) != GATE_COUNT:
        bad.append("гейтов %d, а объявлено %d" % (len(GATES), GATE_COUNT))

    for n, fn in GATES:
        why = None
        if not isinstance(fn, types.FunctionType):
            why = "это не функция, а %s" % type(fn).__name__
        elif fn.__name__ == "<lambda>":
            why = "это лямбда: у неё нет имени определения"
        elif fn.__qualname__ != fn.__name__:
            why = "это замыкание внутри %s" % fn.__qualname__
        elif hasattr(fn, "__wrapped__"):
            why = "это обёртка декоратором"
        elif fn.__name__ not in gdefs:
            why = ("в исходнике нет определения верхнего уровня с именем %s"
                   % fn.__name__)
        elif globals().get(fn.__name__) is not fn:
            why = "имя %s в модуле указывает на другое" % fn.__name__
        if why:
            bad.append("гейт «%s» пробам по имени недоступен: %s — такой гейт "
                       "не поддерживается, а не пропускается" % (n, why))

    reg = {fn.__name__ for _, fn in GATES
           if isinstance(fn, types.FunctionType)}
    for n in sorted(gdefs - reg):
        if n not in GATES_NOT_REGISTERED:
            bad.append("определение %s выглядит гейтом, но в наборе его нет и "
                       "выключение не объявлено" % n)
    for n in sorted(GATES_NOT_REGISTERED):
        if n not in gdefs:
            bad.append("выключенным объявлено определение, которого нет: %s"
                       % n)
        elif n in reg:
            bad.append("определение %s объявлено выключенным, а оно в наборе"
                       % n)

    for n in sorted(EMPTY_PROBE_SKIP):
        if n not in names:
            bad.append("проба пустой выборкой освобождает гейт, которого в "
                       "наборе нет: %s" % n)
    _sample(bad, len(set(names) - set(EMPTY_PROBE_SKIP)),
            "гейтов под пробой пустой выборкой")

    invf, _invk, say = _gate_reach()
    if invf is None:
        return bad + say
    bad.extend(say)
    reaching = set()
    for gs in invf.values():
        reaching |= set(gs)
    for g in sorted(reaching - reg):
        bad.append("определение %s дотягивается до генератора, а гейта с "
                   "таким именем в наборе нет" % g)
    for g in sorted(reg - reaching):
        if g not in NO_REFERENCE_GATES:
            bad.append("гейт %s не берёт у генератора ничего и в список таких "
                       "не внесён: если он раньше брал, обращение пропало "
                       "молча" % g)
    for g in sorted(NO_REFERENCE_GATES):
        if g not in reg:
            bad.append("в списке не берущих у генератора имя, которого в "
                       "наборе нет: %s" % g)
        elif g in reaching:
            bad.append("гейт %s числится не берущим у генератора, а он берёт: "
                       "запись устарела" % g)
    _sample(bad, len(reaching), "гейтов под пробой эталоном")

    for key in sorted(SELECTION_FUNCS):
        if not KNOWN_ANSWER_FOR.get(key):
            bad.append("%s.%s решает отбор корпуса, а таблицы известных "
                       "ответов для неё нет" % key)
        if key not in invf:
            bad.append("%s.%s объявлена решающей отбор, а ни один гейт её не "
                       "зовёт" % key)
    for key in sorted(KNOWN_ANSWER_FOR):
        if key not in SELECTION_FUNCS:
            bad.append("известные ответы объявлены для %s.%s, а решающей "
                       "отбор она не числится" % key)
    _sample(bad, len(SELECTION_FUNCS), "функций отбора с известными ответами")

    head = "  " + "пройден "
    printed = {x.value[len(head):] for x in ast.walk(tree)
               if isinstance(x, ast.Constant) and isinstance(x.value, str)
               and x.value.startswith(head)}
    printed.discard("%s")
    for n in sorted(printed):
        if n not in EXTRA_CHECKS:
            bad.append("«%s» печатается пройденной проверкой, а ни гейтом, ни "
                       "объявленной проверкой вне набора не является" % n)
    for n in sorted(EXTRA_CHECKS):
        if n not in printed:
            bad.append("объявлена проверка вне набора, которую никто не "
                       "печатает: %s" % n)
        if n in names:
            bad.append("«%s» объявлена и гейтом, и проверкой вне набора" % n)
    _sample(bad, len(EXTRA_CHECKS), "объявленных проверок вне набора")
    return bad[:20]


# ------------- ГЕЙТ: ВСЯ СТРОКА ТАБЛИЦЫ ПАРЫ — ПРО ОДИН И ТОТ ЖЕ ПРЕДМЕТ
#
# Формы таблиц, где строка говорит о ПАРЕ элементов. Для каждой объявлено:
# откуда берётся РАМКА отсчёта, каким столбцом НАЗВАН предмет и что в каждом
# столбце напечатано и ПРО КОГО. Столбец, которого здесь нет, роняет гейт
# вместе с таблицей, чьей шапки нет в списке: область гейта — часть гейта, и
# таблица, которую не читает ни один гейт, у нас уже была.
PAIR_TABLES = (
    {"what": "страница элемента: чем заменить",
     "head": ("Cell", "Fit", "Voltage", "Chemistry", "Capacity"),
     "frame": "h1", "subject": 0,
     "cols": ((0, "code", "subject"), (1, "fit", "subject"),
              (2, "volt", "subject"), (3, "chem", "subject"),
              (4, "mah", "subject"))},
    {"what": "страница элемента: во что это можно поставить",
     "head": ("Discontinued cell", "Fit", "Voltage", "Chemistry"),
     "frame": "h1", "subject": 0,
     "cols": ((0, "code", "subject"), (1, "fit", "subject"),
              (2, "volt", "subject"), (3, "chem", "subject"))},
    {"what": "виджет",
     "head": ("Cell", "Fit", "Voltage", "Chemistry"),
     "frame": "h1", "subject": 0,
     "cols": ((0, "code", "subject"), (1, "fit", "subject"),
              (2, "volt", "subject"), (3, "chem", "subject"))},
    # ДВА ПРЕДМЕТА В ОДНОЙ СТРОКЕ — и это законно ровно потому, что второй
    # НАЗВАН четвёртым столбцом: до него строка про снятый элемент, после
    # него — про тот, что ему на смену. Гейт следует за объявлением.
    {"what": "витрина снятых",
     "head": ("Cell", "Envelope", "Volts", "Closest current", "Fit",
              "What the swap costs"),
     "frame": 0, "subject": 3,
     "cols": ((0, "code", "frame"), (1, "shell", "frame"),
              (2, "volts", "frame"), (3, "code", "subject"),
              (4, "fit", "subject"), (5, "volt", "subject"))},
    # Шапка сама называет рамку: «Voltage against MR43». Строка целиком про
    # выпускаемый элемент, а MR43 — отсек, из которого на него смотрят.
    {"what": "витрина оболочки: что из неё ушло",
     "head": ("Still listed", "Voltage against",
              "What the percentage does not say"),
     "frame": "head", "subject": 0,
     "cols": ((0, "code", "subject"), (1, "volt", "subject"),
              (2, "chem_first", "subject"))},
)

_PAIR_V = re.compile(r"([\d.]+)\s*V(?![A-Za-z])")
_PAIR_PCT = re.compile(r"([-+−]?\d+(?:\.\d+)?)\s*%")
_PAIR_MM = re.compile(r"([\d.]+)")


def _pair_text(raw):
    """Видимый текст ячейки: сущности разворачиваются, теги выбрасываются."""
    return " ".join(_text(raw).replace("&mdash;", "—")
                    .replace("&minus;", "−")
                    .replace("&rsquo;", "'").replace("&amp;", "&").split())


def _envelope(cell):
    """Оболочка ИЗ СНИМКА, посчитанная ЗДЕСЬ.

    Второй, независимый счёт того же, что считает cells.shell. Так и надо:
    гейт, взявший оболочку у проверяемого и вердикт посадки у него же,
    согласится с ним и на перевёрнутом вердикте — а перевёрнутый вердикт тут
    и стоял, на 102 строках.
    """
    h = cell.get("height")
    if h is None:
        return None
    d = cell.get("diameter")
    if d is not None:
        return ("round", round(d, 1), round(h, 1))
    lg, wd = cell.get("length"), cell.get("width")
    if lg is not None and wd is not None:
        return ("box", round(lg, 1), round(wd, 1), round(h, 1))
    return None


def _printed_gap(x, y):
    """Расстояние между двумя мерами В ТОМ ВИДЕ, В КАКОМ ОНО НАПЕЧАТАНО.

    Своя, вторая реализация того же правила: сайт печатает меры десятой
    долей, читатель вычитает напечатанное, и вердикт обязан следовать за
    его вычитанием. Двоичный хвост разности этого не знает — 1.6 - 1.3 это
    0.30000000000000004, то есть «больше допуска 0,3» у пары, обе цифры
    которой напечатаны на странице. Правило доказывается известными
    ответами ниже, а не сверкой с cells.fit_gap.
    """
    return round(round(y, 1) - round(x, 1), 1)


def _fit_by_size(frame, subject, tol):
    """Вердикт посадки ПРЕДМЕТА в отсек рамки, посчитанный ЗДЕСЬ из размеров.

    Направление у этой функции ровно одно и оно доказывается известными
    ответами ниже, а не чтением: «встанет ли SUBJECT туда, где стоял FRAME».
    Допуск приходит извне и прибит руками в REFERENCE_CONSTS.

    Разности берутся у _printed_gap: граница вердикта решается по цифрам,
    которые стоят на странице.
    """
    a, b = _envelope(frame), _envelope(subject)
    if not a or not b or a[0] != b[0]:
        return None
    if a[0] == "round":
        dd, dh = _printed_gap(a[1], b[1]), _printed_gap(a[2], b[2])
    else:
        d1 = _printed_gap(a[1], b[1])
        d2 = _printed_gap(a[2], b[2])
        dh = _printed_gap(a[3], b[3])
        if abs(d1) > tol or abs(d2) > tol:
            return "wider" if (d1 > 0 or d2 > 0) else "narrower"
        dd = 0.0
    if abs(dd) > tol:
        return "wider" if dd > 0 else "narrower"
    if abs(dh) <= tol:
        return "drop-in"
    return "taller" if dh > 0 else "shorter"


def _fit_known_answers(tol):
    """Направление эталона — ИЗВЕСТНЫМИ ОТВЕТАМИ, набранными руками.

    Чистую функцию проверяют известными ответами: перевёрнутая _fit_by_size
    молча согласилась бы с перевёрнутой страницей, и гейт печатал бы
    «пройден» над тем самым дефектом, ради которого написан.
    """
    base = {"diameter": 11.6, "height": 5.4}
    cases = (({"diameter": 11.6, "height": 5.4}, "drop-in"),
             ({"diameter": 11.6, "height": 5.6}, "drop-in"),
             ({"diameter": 11.6, "height": 6.4}, "taller"),
             ({"diameter": 11.6, "height": 4.2}, "shorter"),
             ({"diameter": 12.6, "height": 5.4}, "wider"),
             ({"diameter": 10.6, "height": 5.4}, "narrower"))
    bad = []
    # ГРАНИЦА — ОТДЕЛЬНЫМИ ИЗВЕСТНЫМИ ОТВЕТАМИ, и сперва доказывается, что
    # двоичный хвост вообще есть: без первой строки следующие три ничего
    # не проверяют. Пара 1,3 / 1,6 напечатана на /346/ и /sr716w/, и по
    # напечатанным цифрам она ровно на допуске.
    if 1.6 - 1.3 <= 0.3:
        bad.append("двоичного хвоста у 1.6 - 1.3 не оказалось — проба "
                   "границы посадки перестала что-либо проверять")
    edge = (({"diameter": 7.9, "height": 1.3},
             {"diameter": 7.9, "height": 1.6}, "drop-in"),
            ({"diameter": 7.9, "height": 1.6},
             {"diameter": 7.9, "height": 1.3}, "drop-in"),
            ({"diameter": 7.9, "height": 1.3},
             {"diameter": 7.9, "height": 1.7}, "taller"),
            ({"diameter": 10.2, "height": 5.4},
             {"diameter": 10.5, "height": 5.4}, "drop-in"))
    for f, s, want in edge:
        got = _fit_by_size(f, s, tol)
        if got != want:
            bad.append("на границе допуска %s мм в отсеке %s мм это «%s», а "
                       "посчитано «%s»: класс пошёл за двоичным остатком, а "
                       "не за напечатанной цифрой"
                       % (s["height"], f["height"], want, got))
    for other, want in cases:
        got = _fit_by_size(base, other, tol)
        if got != want:
            bad.append("эталон посадки перевёрнут: %s мм в отсеке %s мм это "
                       "«%s», а посчитано «%s»"
                       % (other["height"], base["height"], want, got))
    return bad


def _pair_tables(html):
    """Таблицы страницы: (шапка, строки, разметка таблицы целиком)."""
    out = []
    for m in re.finditer(r"<table\b[^>]*>(.*?)</table>", html, re.S):
        parts = m.group(1).split("</thead>")
        head = tuple(_pair_text(x) for x in
                     re.findall(r"<th[^>]*>(.*?)</th>", parts[0], re.S))
        rows = [(r, re.findall(r"(<t[hd]\b[^>]*>.*?</t[hd]>)", r, re.S))
                for r in re.findall(r"<tr[^>]*>(.*?)</tr>", parts[-1], re.S)]
        out.append((head, rows, m.group(0)))
    return out


def _pair_shape(head):
    """Форма таблицы по её шапке. «Voltage against MR43» — это объявленное
    «Voltage against» с дописанным кодом рамки, и только оно."""
    for shape in PAIR_TABLES:
        want = shape["head"]
        if len(want) != len(head):
            continue
        if all(a == b or a.startswith(b + " ") for a, b in zip(head, want)):
            return shape
    return None


def _pair_page_cell(html, by_code):
    """Элемент, ЧЕЙ ОТСЕК на этой странице: код из h1. У виджета в h1 стоит
    ещё габарит и напряжение, поэтому берётся то, что до тире."""
    code = _code_of(html)
    if not code:
        return None
    return by_code.get(code.replace("&mdash;", "—").split("—")[0]
                       .strip())


def _pair_pct_word(pct):
    """Печатаемый процент — ПО ТОМУ ЖЕ ПРАВИЛУ, что и на странице, но
    набранному здесь: «+0.0%» это не число, а артефакт округления со знаком,
    а десятая доля у трёхзначного — шум."""
    if abs(pct) < 0.05:
        return "0%"
    return ("%+.0f%%" % pct) if abs(pct) >= 100 else ("%+.1f%%" % pct)


def _pair_column(kind, cell, frame, subject, raw, tol, where):
    """Одна ячейка строки, пересчитанная для ОБЪЯВЛЕННОГО предмета."""
    import cells as Cx
    txt = _pair_text(raw)
    bad = []
    if kind == "code":
        return bad
    if kind == "shell":
        env = _envelope(cell)
        got = [float(x) for x in _PAIR_MM.findall(txt)]
        want = list(env[1:]) if env else []
        if [round(x, 1) for x in got] != want:
            bad.append("%s: габарит в ячейке %s, а у %s он %s"
                       % (where, txt, cell["code"], want))
        return bad
    if kind in ("volt", "volts"):
        v = _PAIR_V.search(txt)
        own = cell.get("volts")
        if own is None:
            if "not published" not in txt:
                bad.append("%s: у %s напряжения в снимке нет, а в ячейке «%s»"
                           % (where, cell["code"], txt))
            return bad
        if not v or abs(float(v.group(1)) - own) > 1e-9:
            bad.append("%s: в ячейке %s, а %s идёт при %s В — напряжение в "
                       "ячейке не его" % (where, txt, cell["code"], own))
        if kind == "volts":
            return bad
        base = frame.get("volts")
        pm = _PAIR_PCT.search(txt)
        if base is None:
            if pm:
                bad.append("%s: процент напечатан, а у рамки %s напряжения "
                           "нет" % (where, frame["code"]))
            return bad
        ratio = (own - base) / base
        want_pct = _pair_pct_word(round(ratio * 100.0, 1))
        got_pct = pm.group(0).replace(" ", "").replace("−", "-") if pm \
            else ""
        if got_pct != want_pct:
            bad.append("%s: %s В против %s В у %s даёт %s, напечатано «%s»"
                       % (where, own, base, frame["code"], want_pct, got_pct))
        klass = Cx.consequence_class(ratio)
        cm = re.search(r"bx-v-([a-z]+)", raw)
        if not cm or cm.group(1) != klass:
            bad.append("%s: класс в разметке «%s», а пара %s к %s это «%s»"
                       % (where, cm.group(1) if cm else "нет",
                          cell["code"], frame["code"], klass))
        tag = P.V_TAG.get(klass)
        if tag and tag not in txt:
            bad.append("%s: метка «%s» не стоит в ячейке «%s»"
                       % (where, tag, txt))
        return bad
    if kind == "fit":
        want = _fit_by_size(frame, subject, tol)
        if want is None:
            bad.append("%s: у пары %s и %s размеров на вердикт не хватает, а "
                       "вердикт напечатан: «%s»"
                       % (where, frame["code"], subject["code"], txt))
            return bad
        word = P.FIT_WORD.get(want, want)
        if txt != word:
            bad.append("%s: посадка %s в отсеке %s это «%s», напечатано «%s»"
                       % (where, subject["code"], frame["code"], word, txt))
        row = Cx.pair_row(frame, subject)
        if row.get("subject") != subject["code"]:
            bad.append("%s: строка объявляет предметом %s, а напечатан %s"
                       % (where, row.get("subject"), subject["code"]))
        if row.get("fit") != want:
            bad.append("%s: pair_row даёт посадку «%s», а размеры снимка — "
                       "«%s»" % (where, row.get("fit"), want))
        return bad
    if kind == "chem":
        want = P.chem(cell)
        if txt != want:
            bad.append("%s: химия в ячейке «%s», а у %s она «%s»"
                       % (where, txt, cell["code"], want))
        return bad
    if kind == "chem_first":
        mine, theirs = P.chem(subject), P.chem(frame)
        low = txt.lower()
        if mine == theirs:
            if "same chemistry" not in low:
                bad.append("%s: у %s и %s химия одна, а ячейка говорит «%s»"
                           % (where, subject["code"], frame["code"], txt))
            return bad
        i, j = low.find(mine), low.find(theirs)
        if i < 0:
            bad.append("%s: строка про %s, а его химия «%s» в ячейке «%s» не "
                       "названа" % (where, subject["code"], mine, txt))
        elif 0 <= j < i:
            bad.append("%s: ячейка называет химию рамки %s раньше химии "
                       "предмета %s: «%s»"
                       % (where, frame["code"], subject["code"], txt))
        return bad
    if kind == "mah":
        own = cell.get("mah")
        got = _PAIR_MM.findall(txt.replace(",", ""))
        if own is None:
            if got:
                bad.append("%s: ёмкости у %s в снимке нет, а в ячейке «%s»"
                           % (where, cell["code"], txt))
        elif not got or abs(float(got[0]) - own) > 0.05:
            bad.append("%s: ёмкость в ячейке «%s», а у %s она %s"
                       % (where, txt, cell["code"], own))
        return bad
    return ["%s: столбец «%s» объявлен, а проверять его гейт не умеет"
            % (where, kind)]


def _pair_empty_row(shape, cells, raw, where):
    """Строка «сравнивать не с чем». Она объявлена ровно у виджета и ровно
    одной формы; всякая другая склейка ячеек — молчаливый пропуск."""
    if shape["what"] != "виджет":
        return ["%s: ячейки склеены colspan в таблице, где этого не бывает"
                % where]
    if len(cells) != 2 or _pair_text(cells[0]) != "—" \
            or "Nothing" not in _pair_text(cells[1]):
        return ["%s: пустая строка виджета не той формы: %s"
                % (where, [_pair_text(x)[:40] for x in cells])]
    return []


def g_pair_row_one_subject(files):
    """ВСЯ СТРОКА ТАБЛИЦЫ ПАРЫ — ПРО ОДИН ПРЕДМЕТ, И ПРЕДМЕТ ЭТОТ НАЗВАН.

    ПОЧЕМУ ГЕЙТ НЕ ПОСТОЛБЦОВЫЙ. Одну и ту же таблицу снятых чинили три
    проверки подряд: сперва процент считался от снятого, а стоял рядом с
    напряжением снятого; потом подпись называла рамку отсчёта неверно; потом
    слово посадки описывало элемент ЭТОЙ страницы, пока напряжение, химия и
    код в той же строке описывали элемент СТРОКИ — «sits lower» на 102
    строках, где предмет строки не садится ниже, а НЕ ДАЁТ ЗАКРЫТЬ КРЫШКУ.
    Каждый раз проверка писалась НА СТОЛБЕЦ, и каждая была зелёной: столбец
    сам по себе был верен всякий раз. Дефект живёт не в столбце, а МЕЖДУ
    столбцами — в том, что один из них говорит о другом предмете, чем
    соседние, — и увидеть его можно только пересчитав ВСЮ СТРОКУ для ОДНОГО
    предмета. Поэтому здесь проверяется строка целиком, а столбцы объявлены
    поимённо: новый столбец, не внесённый в PAIR_TABLES, роняет гейт, как и
    таблица, чьей шапки в списке нет.

    ОБЛАСТЬ — все пять поверхностей, на которых сайт печатает строку о паре:
    обе таблицы страницы элемента, таблица виджета, витрина снятых (там
    предметов в строке два, и второй НАЗВАН четвёртым столбцом) и таблица
    оболочки, где рамку называет сама шапка. Выборка каждой формы объявлена
    отдельно: исчезнувшая таблица роняет гейт, а не молча сужает его.

    ЭТАЛОН НЕ У ПРОВЕРЯЕМОГО. Посадка считается здесь из размеров снимка и
    допуска, прибитого руками в REFERENCE_CONSTS, а направление счёта
    доказано известными ответами; процент — здесь же из двух напряжений.
    cells.pair_row спрашивается отдельно и только о том, СОВПАДАЕТ ли
    объявленный ею предмет с напечатанным.
    """
    import cells as Cx
    import render as rd
    bad = list(_fit_known_answers(Cx.FIT_MM))
    tol = Cx.FIT_MM
    by_code = {c["code"]: c for c in (getattr(rd, "CELLS", None) or [])}
    _sample(bad, len(_html(files)), "отданных страниц")
    _sample(bad, len(by_code), "записей снимка")
    seen = dict((s["what"], 0) for s in PAIR_TABLES)
    for p, html in sorted(_html(files).items()):
        page = _pair_page_cell(html, by_code)
        for head, rows, raw_table in _pair_tables(html):
            shape = _pair_shape(head)
            if shape is None:
                if 'class="bx-fits"' in raw_table:
                    bad.append("%s: таблица пар с шапкой %s — такой формы не "
                               "объявлено, её строки не читает никто"
                               % (p, list(head)))
                continue
            frame = page
            if shape["frame"] == "head":
                frame = by_code.get(head[1].split("against")[-1].strip())
            elif shape["frame"] != "h1":
                frame = None
            if shape["frame"] == "h1" and page is None:
                bad.append("%s: таблица пар стоит, а элемента страницы в h1 "
                           "нет — её строки выпадали бы из осмотра молча" % p)
                continue
            if shape["frame"] == "head" and frame is None:
                bad.append("%s: шапка называет рамкой «%s», а такой записи в "
                           "снимке нет" % (p, head[1]))
                continue
            for raw_row, cells in rows:
                where = "%s [%s]" % (p, shape["what"])
                if "colspan" in raw_row:
                    bad.extend(_pair_empty_row(shape, cells, raw_row, where))
                    continue
                if len(cells) != len(head):
                    bad.append("%s: в строке %d ячеек, а в шапке %d"
                               % (where, len(cells), len(head)))
                    continue
                if isinstance(shape["frame"], int):
                    frame = by_code.get(_pair_text(cells[shape["frame"]]))
                subject = by_code.get(_pair_text(cells[shape["subject"]]))
                where = "%s %s" % (where, _pair_text(cells[0]))
                if subject is None or frame is None:
                    bad.extend(_pair_no_pair(shape, cells, head, where))
                    continue
                seen[shape["what"]] += 1
                for i, kind, whose in shape["cols"]:
                    who = subject if whose == "subject" else frame
                    bad.extend(_pair_column(kind, who, frame, subject,
                                            cells[i], tol, where))
                if len(bad) > 20:
                    return bad[:20]
    for what, n in sorted(seen.items()):
        _sample(bad, n, "строк формы «%s»" % what)
    return bad[:20]


def _pair_no_pair(shape, cells, head, where):
    """Строка, в которой предмет не назван обозначением. Законна она ровно
    одна: снятый элемент, которому в каталоге нет замены, — и тогда столбцы
    про предмет обязаны стоять пустыми, а не нести вердикт ни о ком."""
    if shape["what"] != "витрина снятых":
        return ["%s: обозначения из строки нет в снимке: %s"
                % (where, [_pair_text(x)[:30] for x in cells])]
    said = _pair_text(cells[shape["subject"]])
    if "none in this catalog" not in said:
        return ["%s: замена названа «%s», а такой записи в снимке нет"
                % (where, said)]
    empty = [i for i, kind, whose in shape["cols"]
             if whose == "subject" and kind != "code"
             and _pair_text(cells[i]) != "—"]
    if empty:
        return ["%s: замены нет, а столбцы %s всё равно что-то о ней говорят"
                % (where, empty)]
    return []


# ------------------------------------ МЕТА-ГЕЙТ: У ТИХОЙ ВЕТКИ ЕСТЬ ИМЯ
#
# Общее правило всей волны, записанное проверкой: У ПРОВЕРКИ НЕТ ИСХОДА
# «НИЧЕГО НЕ НАШЛОСЬ». Тихая ветка — `continue`, `pass` или пустой `return`
# без единой жалобы рядом — выводит страницу, строку или запись из-под
# правила, и снаружи это неотличимо от «правило выполнено». Так у нас 69
# записей из 215 не находили своей страницы в самой дорогой проверке сайта,
# так неразобравшаяся строка таблицы замен переставала считаться, так
# переименованный гейт выпадал из пробы мета-гейта.
#
# Отличить законный ОТБОР (страница не того типа, строка не того столбца) от
# молчаливого ПРОПУСКА может только человек. Поэтому каждая ветка объявлена
# здесь строкой своего условия: новая, никем не названная, роняет гейт, а
# названная и исчезнувшая — тоже, чтобы список не превращался в кладбище.
SILENT_SKIPS = {
    ("_pair_shape", "len(want) != len(head)"),
    # Ветки волны отношений. Каждая выводит запись снимка или страницу
    # из-под правила, и каждая названа.
    ("_rel_alkaline_silver", "v is None"),
    ("_rel_code_holds_height", "h is None"),
    ("g_relations_computed", "not me"),
    ("_declared_fact_prefixes",
     "not (isinstance(s, ast.Constant) and isinstance(s.value, str))"),
    ("_declared_fact_prefixes",
     'not (isinstance(n, ast.FunctionDef) and n.name == "facts")'),
    # Ветки гейта величин в прозе. Каждая выводит строку из-под правила, и
    # каждая названа: разбор, тихо переставший что-либо находить, зеленит
    # гейт ровно так же, как его отсутствие.
    ("_prose_snapshot_value", "code.upper() not in names"),
    ("g_prose_quantities_declared",
     "id(node) in skip or _PROSE_CYR.search(node.value)"),
    ("g_prose_quantities_declared",
     'kind == "цифрами" and _prose_is_code(tok, codes)'),
    ("g_prose_quantities_declared", "len(_PROSE_WORD.findall(vis)) < 3"),
    ("g_prose_quantities_declared",
     "not (isinstance(node, ast.Constant) and isinstance(node.value, str))"),
    ("_fits_rows", 'not cm or not vm'),
    ("_fits_rows", 'want_head not in parts[0]'),
    ("_gate_reach", 'n.name in DYNAMIC_REF_OK'),
    ("_gate_reach", 'not hasattr(mods.get(mod), attr)'),
    ("_gate_reach",
     'not isinstance(n, ast.Assign) or not isinstance(n.value, ast.Attribute)'),
    ("_gate_reach", 'not isinstance(n, ast.FunctionDef)'),
    ("_gate_reach", 'not isinstance(x, ast.Call)'),
    ("_keys_of", r'prop not in body.replace(" ", "").replace("\n", "")'),
    ("_section_answer", 'any(c in attrs for c in NOT_THE_ANSWER)'),
    ("g_ad_below_the_answer", 'main is None'),
    ("g_answer_above_reference", 'ans < 0'),
    ("g_answer_first", 'h2 in P.CONSTANT_HEADS'),
    ("g_chem_note_volts_from_page", 'not blk'),
    ("g_chemistry_matches_code", 'not m'),
    ("g_chemistry_matches_code", 'not want'),
    ("g_chemistry_names_whole", 'len(cells) < 3'),
    ("g_chemistry_names_whole", 'not txt'),
    ("g_completeness_claim_counted", 'vals is None'),
    ("g_cross_page_counts_agree", 'not m'),
    ("g_descriptions_differ", 'not m'),
    ("g_embed_verdict_carries_limits",
     'not ({_text(c).strip() for c in tds} & fits)'),
    ("g_embed_verdict_carries_limits", 'not m'),
    ("g_empty_sample_is_a_failure", '_IN_EMPTY_PROBE[0]'),
    ("g_empty_sample_is_a_failure", 'name in EMPTY_PROBE_SKIP'),
    ("g_fit_and_volts_separate", 'not (words & fits)'),
    ("g_fit_claim_carries_voltage",
     'not any(w in low for w in FIT_CLAIM_WORDS)'),
    ("g_fit_claim_carries_voltage", 'not crx.search(sent)'),
    ("g_gone_not_present_tense", 'not gone'),
    ("g_iec_long_form_known", 'name.upper() in household'),
    ("g_iec_long_form_known",
     'name.upper() in standard or _in_snapshot(name) or _in_snapshot("E" + name)'),
    ("g_iec_long_form_known",
     'r["dims"] and name == r["dims"].replace("x", " x ") + " mm"'),
    ("g_index_has_no_dead_ends", '"#" not in href'),
    ("g_lead_class_follows_ratio", 'not mv'),
    ("g_links_point_at_pages", 'href != "/codes/"'),
    ("g_lookup_answers_known_strings", 'typed in by_key'),
    ("g_lookup_promises_hold",
     'dk and any(r["dims"] == dk or r["dims"].startswith(dk + "x") for r in rows)'),
    ("g_lookup_promises_hold", 'k in by_key'),
    ("g_narrow_column_holds_text", 'len(word) <= limit'),
    ("g_no_external",
     'r.startswith(ALLOWED_PREFIX) or r.startswith( "https://%s" % DOMAIN)'),
    ("g_one_signal_one_job", 'sel.startswith("@") or sel.startswith(":root")'),
    ("g_orphans", 'p in ("index.html", "404.html")'),
    ("g_prose_ratio_matches_table", 'p in pages'),
    ("g_reciprocal_verdicts_agree", 'back is None'),
    ("g_reciprocal_verdicts_agree", 'not t["gone"]'),
    ("g_reciprocal_verdicts_agree", 'q is None or q not in tables'),
    ("g_reference_is_not_the_code_under_test", '_IN_REFERENCE_PROBE[0]'),
    ("g_reference_is_not_the_code_under_test", 'key in REFERENCE_STUBS'),
    ("g_reference_is_not_the_code_under_test", 'not reached'),
    ("g_shell_slug_form",
     'not p.startswith("shell/") or not p.endswith("index.html")'),
    ("g_spacing_from_one_unit", 'lit in SPACING_EXEMPT'),
    ("g_stamped_codes_in_source", 'not name'),
    ("g_twins", 'len(paths) < 2'),
    ("g_twins", 'not m'),
    ("g_type_scale_is_one", 's.startswith("var(") and s[4:-1] in scale'),
    ("g_volt_functions_known_answers", 'a == b'),
    ("g_word_floor", 'url in rd.FLOOR_EXEMPT'),
    # Ветки самого этого гейта: он не исключение из собственного правила.
    ("g_silent_skips_are_named", "n in reach or n not in funcs"),
    ("g_silent_skips_are_named",
     "not isinstance(x, ast.If) or len(x.body) != 1"),
    ("g_silent_skips_are_named", "not quiet"),
}


def g_silent_skips_are_named(files):
    """Каждая ТИХАЯ ветка внутри гейта названа в исходнике.

    Считается ЗАМЫКАНИЕ гейтов: сами гейты и все помощники, до которых они
    дотягиваются по вызовам в этом же файле. Помощники молчали ровно так же
    — _fits_rows пропускала неразобравшуюся строку и незнакомую таблицу, и
    гейт отчитывался о прочитанном, ничего не сказав о непрочитанном.

    Обе стороны провальны: ветка без имени — пропуск, о котором никто не
    решал; имя без ветки — запись, которая ничего не значит, но выглядит
    объяснением.
    """
    bad = []
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(SILENT_SKIPS), "объявленных тихих веток")
    text = _sources().get("gates.py")
    if not text:
        return bad + ["исходник гейтов не прочитан — считать нечего"]
    tree = ast.parse(text)
    funcs, calls = {}, {}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            funcs[n.name] = n
            calls[n.name] = {x.func.id for x in ast.walk(n)
                             if isinstance(x, ast.Call)
                             and isinstance(x.func, ast.Name)}
    reach, stack = set(), [n for n in funcs if n.startswith("g_")]
    while stack:
        n = stack.pop()
        if n in reach or n not in funcs:
            continue
        reach.add(n)
        stack.extend(calls.get(n, ()))
    _sample(bad, len(reach), "функций в замыкании гейтов")
    found = set()
    for name in sorted(reach):
        for x in ast.walk(funcs[name]):
            if not isinstance(x, ast.If) or len(x.body) != 1:
                continue
            s = x.body[0]
            quiet = (isinstance(s, (ast.Continue, ast.Pass))
                     or (isinstance(s, ast.Return)
                         and (s.value is None
                              or (isinstance(s.value, ast.List)
                                  and not s.value.elts))))
            if not quiet:
                continue
            cond = ast.get_source_segment(text, x.test) or ""
            found.add((name, " ".join(w for w in cond.split()
                                      if w != chr(92))))
    _sample(bad, len(found), "тихих веток, найденных в исходнике")
    for one in sorted(found - SILENT_SKIPS):
        bad.append("тихая ветка не названа: %s, «%s» — она выводит "
                   "проверяемое из-под правила, и снаружи это неотличимо от "
                   "«правило выполнено»" % one)
    for one in sorted(SILENT_SKIPS - found):
        bad.append("объявлена тихая ветка, которой в исходнике нет: %s, «%s»"
                   % one)
    return bad[:20]


# ------------------- ГЕЙТ: README СЧИТАЕТ ГЕЙТЫ ПО ФАКТУ
#
# README трижды подряд аттестовал сайт числом «82 гейта», пока гейтов было 86,
# а заголовок раздела называл ещё третье число. Ни одну из этих цифр не читал
# ни один гейт: набор проверок сторожит весь сайт, а СЧЁТ САМОГО НАБОРА не
# сторожил никто. Вместе с ним разъехались и остальные величины учёта —
# определения, прибитые руками величины, тихие ветки и нарочные поломки.
#
# У каждого счётного утверждения README есть ЯКОРЬ — слова вокруг числа, — и
# величина, которая считается ЗАНОВО из кода. Фраза обязана стоять ровно один
# раз: устаревшее число якорь не соберёт, а утверждение, переписанное прозой,
# потеряет якорь и уронит гейт тоже — менять текст мимо его проверки нельзя.

_DOC = {}


def _readme():
    """README, прочитанный С ДИСКА и закэшированный. Свой кэш нужен затем же,
    зачем он у исходников: `--selftest` подсовывает в него испорченный текст,
    а иначе поломку этому гейту негде поставить."""
    if not _DOC:
        _DOC["README.md"] = io.open(os.path.join(HERE, "README.md"),
                                    encoding="utf-8").read()
    return _DOC["README.md"]


_RU_TENS = {2: "двадцать", 3: "тридцать", 4: "сорок", 5: "пятьдесят",
            6: "шестьдесят", 7: "семьдесят", 8: "восемьдесят",
            9: "девяносто"}
_RU_UNITS = {1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
             6: "шесть", 7: "семь", 8: "восемь", 9: "девять"}


def _ru_numeral(n):
    """Числительное словами для 20..99 — ровно тот диапазон, в котором README
    пишет счёт гейтов заголовком.

    Вне диапазона возвращается None, и это ЖАЛОБА зовущего, а не тихий
    пропуск: число, которое нечем написать словами, обязано остановить
    сборку, а не проехать мимо проверки.
    """
    if not 20 <= n <= 99:
        return None
    tens, units = divmod(n, 10)
    if not units:
        return _RU_TENS[tens]
    return "%s %s" % (_RU_TENS[tens], _RU_UNITS[units])


def _gate_defs_in_source():
    """Сколько определений g_* верхнего уровня лежит в исходнике гейтов."""
    text = _sources().get("gates.py")
    if not text:
        return None
    return len([n for n in ast.parse(text).body
                if isinstance(n, ast.FunctionDef) and n.name.startswith("g_")])


def _declared_breaks():
    """Сколько нарочных поломок объявлено в `selftest`.

    Считается ПО ИСХОДНИКУ, а не запуском: полный прогон проб стоит минут, а
    число это README печатает отдельным утверждением, и разъезжается оно
    ровно тогда, когда поломку добавили.
    """
    text = _sources().get("gates.py")
    if not text:
        return None
    n = 0
    for node in ast.walk(ast.parse(text)):
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        if isinstance(node, ast.AugAssign):
            target = node.target
        named = isinstance(target, ast.Name) and target.id == "breaks"
        if named and isinstance(node.value, (ast.List, ast.Tuple)):
            n += len(node.value.elts)
    return n


def _doc_claims():
    """Счётные утверждения README о самом наборе проверок — ПОИМЁННО, и рядом
    величина, посчитанная заново. Новое утверждение заводится записью здесь;
    утверждения, которого здесь нет, гейт не сторожит, и это видно."""
    n = len(GATES)
    word = _ru_numeral(n)
    return (
        ("счёт гейтов в команде запуска",
         "# %d гейтов по собранному И по диску" % n),
        ("счёт гейтов в таблице файлов",
         "| %d гейтов по собранному + отпечаток содержимого |" % n),
        ("счёт гейтов заголовком раздела",
         None if word is None
         else "## %s гейтов, и каждый краснеет по команде" % word.capitalize()),
        ("счёт определений гейтов",
         "%s определений против набора" % _gate_defs_in_source()),
        ("счёт прибитых руками величин",
         "%d читаемых гейтами величин" % len(REFERENCE_CONSTS)),
        ("счёт тихих веток",
         "%d тихих веток" % len(SILENT_SKIPS)),
        ("счёт нарочных поломок",
         "Нарочных поломок стало **%s**" % _declared_breaks()),
    )


def g_search_answers_by_size(files):
    """ГЛАВНОЕ ОБЕЩАНИЕ САЙТА, ПРОВЕРЕННОЕ ИСПОЛНЕНИЕМ.

    Поле поиска подписано «type the code stamped on it, or its size in
    millimeters», и на главной стоит пример «20 x 3.2 finds CR2032». Это и
    есть работа сайта; всё остальное — справочная часть вокруг неё.

    Гейт не разглядывает код поиска, а ЗАПУСКАЕТ отданный: тот самый
    `render.FINDER` поверх того самого указателя, вынутого из отданной
    страницы. Разглядывание здесь уже подводило — 23 гейта были зелёными,
    пока главный клик сайта вёл в никуда, а 91 гейт был зелёным, пока
    «14.5 x 50.5» (это AA) уводило на 22,5-вольтовую батарею.

    Спрашивается три вещи, и все три — по КОРПУСУ, а не по примерам:
      · каждый двухчисловой габарит указателя обязан первым результатом
        дать элемент ЭТОГО габарита (Enter уходит именно на первый);
      · среди показанных строк не должно быть строк чужого габарита —
        подсказка, набранная обломками запроса, это не подсказка;
      · каждое имя указателя обязано находить само себя, иначе починка
        размерного запроса оплачена поломкой запроса по коду.
    И отдельно — чтения ЛИНЕЙКОЙ: сайт обещает, что линейки достаточно, а
    линейка даёт целые миллиметры.
    """
    import json as _json
    import subprocess
    import tempfile
    import render as rd
    bad = []
    src = None
    for name in sorted(files):
        if name.endswith("index.html") and 'id="bx-index"' in files[name]:
            m = re.search(r'<script type="application/json" id="bx-index">'
                          r'(.*?)</script>', files[name], re.S)
            if m:
                src = m.group(1)
                break
    if not src:
        return ["указателя поиска нет ни на одной отданной странице — "
                "проверять нечего, и это провал, а не пропуск"]
    rows = [r.split("|") for r in _json.loads(src)["r"].split(";")]
    _sample(bad, len(rows), "строк указателя поиска")
    if len(rows) < 100:
        return bad + ["строк указателя %d — источник не тот" % len(rows)]
    with tempfile.TemporaryDirectory() as tmp:
        io.open(os.path.join(tmp, "i.json"), "w",
                encoding="utf-8").write(src)
        io.open(os.path.join(tmp, "f.js"), "w",
                encoding="utf-8").write(rd.FINDER)
        io.open(os.path.join(tmp, "t.js"), "w",
                encoding="utf-8").write(_SEARCH_HARNESS)
        try:
            out = subprocess.run(["node", os.path.join(tmp, "t.js"), tmp,
                                  str(rd.FIND_TOL_MM)],
                                 capture_output=True, text=True, timeout=180,
                                 encoding="utf-8")
        except FileNotFoundError:
            return bad + ["node не найден: единственная проверка главного "
                          "обещания сайта не выполнялась, и зелёной она "
                          "быть не может"]
        if out.returncode != 0:
            return bad + ["прогон поиска упал: %s"
                          % (out.stderr or "")[-300:]]
        got = _json.loads(out.stdout)
    _sample(bad, got["sizes"], "различных габаритов, опрошенных поиском")
    _sample(bad, got["names"], "имён указателя, опрошенных поиском")
    _sample(bad, got["ruler"], "чтений линейкой, опрошенных поиском")
    if not got["sizes"] or not got["names"] or not got["ruler"]:
        bad.append("одна из выборок пуста — пустая выборка это провал")
    for line in got["miss"][:3]:
        bad.append("габарит %s: первым результатом элемент другого "
                   "размера — %s" % (line[0], line[1]))
    if got["junk"]:
        bad.append("в подсказках %d строк чужого габарита из %d показанных: "
                   "обломки запроса гуляют по ярусам имён"
                   % (got["junk"], got["shown"]))
    for line in got["self"][:3]:
        bad.append("имя %s не находит само себя — %s" % (line[0], line[1]))
    for line in got["far"][:3]:
        bad.append("чтение линейкой %s: %s" % (line[0], line[1]))
    return bad[:12]


# Оболочка DOM ровно под то, чем пользуется поиск. Разметку она не
# изображает: важно, ЧТО он положил в список и в каком порядке.
_SEARCH_HARNESS = r"""
const fs=require('fs'),path=require('path'),dir=process.argv[2],
      TOL=+process.argv[3];
const raw=fs.readFileSync(path.join(dir,'i.json'),'utf8');
const J=JSON.parse(raw), R=J.r.split(';').map(x=>x.split('|'));
function mkEl(id){return {id:id,hidden:0,value:'',textContent:'',className:'',
  children:[],appendChild(c){this.children.push(c)},addEventListener(){}};}
const els={}; els['bx-index']=mkEl('bx-index'); els['bx-index'].textContent=raw;
for(const k of ['bx-find','bx-q','bx-res','bx-none','bx-n','bx-nojs'])els[k]=mkEl(k);
let handler=null;
els['bx-q'].addEventListener=function(ev,fn){if(ev==='input')handler=fn};
global.document={getElementById:x=>els[x]||null,
  createElement:t=>({tagName:t,href:'',textContent:'',className:'',
    children:[],appendChild(c){this.children.push(c)}})};
global.location={href:''};
eval(fs.readFileSync(path.join(dir,'f.js'),'utf8'));
function find(q){els['bx-res'].children.length=0;els['bx-q'].value=q;handler();
  return els['bx-res'].children.map(li=>li.children[0].textContent);}
const dims=new Map();
for(const r of R){if(!dims.has(r[0]))dims.set(r[0],[]);dims.get(r[0]).push(r[4]);}
const sizes=[...new Set(R.filter(r=>r[4]&&r[4].split('x').length===2).map(r=>r[4]))];
const miss=[],junkRows=[],self=[],far=[];let shown=0,junk=0;
for(const s of sizes){const res=find(s.split('x').join(' x '));shown+=res.length;
  for(const nm of res)if(!(dims.get(nm)||[]).includes(s))junk++;
  if(!res.length||!(dims.get(res[0])||[]).includes(s))
    miss.push([s.split('x').join(' x '),res[0]?res[0]+' ('+(dims.get(res[0])||[])[0]+')':'ПУСТО']);}
for(const nm of new Set(R.map(r=>r[0]))){const res=find(nm);
  if(!res.length||res[0]!==nm)self.push([nm,res[0]||'ПУСТО']);}
let ruler=0;
for(const s of sizes){const n=s.split('x').map(Number);
  for(const v of [[Math.round(n[0]),Math.round(n[1])],
                  [+(n[0]+0.1).toFixed(1),+(n[1]-0.1).toFixed(1)]]){ruler++;
    const res=find(v[0]+' x '+v[1]);
    if(!res.length){far.push([v.join(' x '),'ничего не найдено, а настоящий '+s]);continue}
    const g=(dims.get(res[0])||[]).map(d=>d.split('x').map(Number))
      .filter(a=>a.length===2)
      .map(a=>Math.max(Math.abs(a[0]-v[0]),Math.abs(a[1]-v[1])));
    if(!g.length||Math.min(...g)>TOL)
      far.push([v.join(' x '),'первым '+res[0]+', а это другой размер']);}}
process.stdout.write(JSON.stringify({sizes:sizes.length,
  names:new Set(R.map(r=>r[0])).size,ruler:ruler,shown:shown,junk:junk,
  miss:miss,self:self,far:far}));
"""


def g_readme_counts_the_gates(files):
    """README НАЗЫВАЕТ ЧИСЛОМ то, чем сам себя аттестует, и число это
    пересчитывается из кода.

    Счёт гейтов — документированная величина ТОГО, ЧТО СТОРОЖИТ ВСЁ
    ОСТАЛЬНОЕ, и он трижды подряд был неверен: две команды запуска обещали 82
    гейта, заголовок раздела — восемьдесят пять, а в наборе лежало 86. Вместе
    с ним разъехались определения, прибитые величины, тихие ветки и поломки:
    ни одну из этих цифр не пересчитывал никто, потому что все гейты читают
    ВЫКЛАДКУ, а README выкладкой не является.

    ОБЕ СТОРОНЫ ПРОВАЛЬНЫ. Число, отставшее от кода, якоря не соберёт;
    утверждение, переписанное прозой, потеряет якорь и уронит гейт тоже —
    правка текста, обходящая свою проверку, и есть тот способ, каким «82»
    пережило три круга. Фраза, встреченная дважды, тоже провал: два места с
    одним числом разъезжаются поодиночке.

    ЧИСТАЯ ФУНКЦИЯ — ИЗВЕСТНЫМИ ОТВЕТАМИ. Числительное словами проверяется
    шестью парами, включая обе границы диапазона: считалка, согласная сама с
    собой, молчит одинаково при любом ответе.
    """
    bad = []
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(GATES), "гейтов в наборе")
    for num, want in ((20, "двадцать"), (85, "восемьдесят пять"),
                      (86, "восемьдесят шесть"), (99, "девяносто девять"),
                      (19, None), (100, None)):
        if _ru_numeral(num) != want:
            bad.append("числительное для %d вышло «%s», а известный ответ "
                       "«%s»" % (num, _ru_numeral(num), want))
    if not _sources().get("gates.py"):
        return bad + ["исходник гейтов не прочитан — пересчитывать нечего"]
    doc = _readme()
    _sample(bad, len(doc), "знаков README")
    claims = _doc_claims()
    _sample(bad, len(claims), "счётных утверждений README")
    for what, phrase in claims:
        if phrase is None:
            bad.append("%s: величину нечем написать словами — проверить "
                       "README нечем, и это провал, а не пропуск" % what)
        else:
            seen = doc.count(phrase)
            if seen != 1:
                bad.append("%s: фразы «%s» в README %d, а обязана быть ровно "
                           "одна: число отстало от кода либо утверждение "
                           "переписали мимо его проверки"
                           % (what, phrase, seen))
    return bad[:20]


# ------------------- ГЕЙТ: ВЕЛИЧИНА В ШАБЛОНЕ ПРОЗЫ ПОСЧИТАНА ИЛИ ОБЪЯВЛЕНА
#
# ПОЧЕМУ ЭТОГО НЕ ВИДНО В ОТДАННОМ ТЕКСТЕ. Все остальные гейты читают
# собранные байты, и по ним этот дефект НЕ ОТЛИЧИМ от исправного: фраза
# грамматична, число правдоподобно, единица на месте, соседние абзацы того же
# рода. «They are the same hazard and the same 3 V» — верное предложение на
# шести страницах и ложное на четырёх, и отличаются они не текстом, а тем,
# ОТКУДА взялась тройка. «Carries its whole identity in six characters» на
# странице /346/ читается как факт; «шесть» там просто набрано руками, а кода
# три знака. Величину, которую никто не считал, видно ТОЛЬКО в исходнике:
# литерал внутри шаблона — это утверждение о данных, сделанное мимо данных.
#
# ЧТО СЧИТАЕТСЯ ВЕЛИЧИНОЙ. Цифры в ВИДИМОМ тексте шаблона и величины,
# написанные СЛОВАМИ: «треть миллиметра», «десятая доля миллиметра», «шесть
# знаков», «три вольта». Все четыре найденные дыры были из второй половины
# наполовину — искать только цифры значило бы пройти мимо трёх из пяти.
#
# ОБЕ СТОРОНЫ ПРОВАЛЬНЫ. Величина в шаблоне, не объявленная здесь, — провал;
# объявление, которому в шаблонах ничего не отвечает, — тоже: описанный и
# несуществующий рычаг хуже отсутствующего, на него рассчитывают.

# Модули, из которых собираются страницы. gates.py сюда не входит: его строки
# на страницу не попадают, и правило это про то, что читает человек.
PROSE_MODULES = ("render.py", "prose.py", "depth.py", "cells.py",
                 "design.py", "draw.py")

# Строковые константы, которые НЕ проза: их числа — это машина, а не
# утверждение о данных. Объявляются поимённо с причиной, потому что
# «похоже на CSS» — это признак, а не граница.
PROSE_MACHINE_TEXT = {
    ("design", "CSS"): "таблица стилей: её числа — кегли, отступы и переломы "
                       "раскладки, и сторожат их g_type_scale_is_one, "
                       "g_spacing_from_one_unit и арифметика раскладки",
    ("design", "AD_CSS"): "рекламная половина той же таблицы стилей; её "
                          "размеры мест сверяет g_ad_slots_exact",
    ("render", "EMBED_CSS"): "таблица стилей виджета, сверяется побайтово "
                             "с отданными байтами в _sheets_read",
    ("render", "FINDER"): "скрипт поиска: его числа — ярусы разбора запроса, "
                          "и отвечают за них g_lookup_* по ОТВЕТАМ поиска",
}

# Функции, чей строковый аргумент — РЕГУЛЯРКА, а не текст. re.* распознаётся
# по имени модуля, остальные называются здесь: шаблон разбора на страницу не
# попадает, а цифр в нём полно.
PROSE_PATTERN_ARGS = {("design", "_one")}

# ВЕЛИЧИНЫ, КОТОРЫЕ ОСТАЛИСЬ НАБРАННЫМИ, И ПОЧЕМУ ЭТО ЗАКОННО.
#   ключ:   (модуль, как напечатано, ЯКОРЬ — кусок видимого текста, который
#           саму величину и содержит; переписанное предложение теряет якорь и
#           роняет гейт, то есть правка обязана пройти здесь);
#   вид:    ("мир", причина)        — факт ВНЕ снимка: год закона, номер
#                                     стандарта, телефон, номер источника.
#                                     Проверить нечем, поэтому написана
#                                     причина;
#           ("снимок", (код, поле)) — величина ПЕРЕСЧИТЫВАЕТСЯ из снимка;
#           ("правило", имя)        — величину проверяет названная функция
#                                     из PROSE_QUANTITY_RULES.
PROSE_QUANTITIES = {
    # --- примеры размера: пересчитываются из снимка ---
    ("render", "20", "CR2032, AG13, AA, 20 x 3.2"):
        ("снимок", ("CR2032", "battery-diameter")),
    ("render", "3.2", "CR2032, AG13, AA, 20 x 3.2"):
        ("снимок", ("CR2032", "battery-height")),
    ("render", "20", "20 x 3.2, or just 20"):
        ("снимок", ("CR2032", "battery-diameter")),
    ("render", "3.2", "20 x 3.2, or just 20"):
        ("снимок", ("CR2032", "battery-height")),
    ("render", "20", "a bare 20 lists the designations"):
        ("снимок", ("CR2032", "battery-diameter")),
    ("render", "3.2", "20 x 3.2 finds CR2032"):
        ("снимок", ("CR2032", "battery-height")),
    ("render", "11.6", "finds CR2032, 11.6"):
        ("снимок", ("LR44", "battery-diameter")),
    ("render", "5.4", "5.4 opens the envelope page"):
        ("снимок", ("LR44", "battery-height")),
    ("render", "20", "CR2032 means 20 mm across"):
        ("снимок", ("CR2032", "battery-diameter")),
    ("render", "3.2", "across and 3.2 mm tall"):
        ("снимок", ("CR2032", "battery-height")),
    # --- факты вне снимка ---
    ("render", "1", "1] Energizer product data index"):
        ("мир", "номер источника в нумерованном списке страницы метода: "
                "величина не физическая, а порядковая, и считать её не из "
                "чего — источников ровно четыре и они перечислены рядом"),
    ("render", "2", "2] Energizer technical data sheets"):
        ("мир", "тот же нумерованный список источников страницы метода, "
                "вторая запись: номер порядковый, а не измеренный"),
    ("render", "3", "3] IEC 60086"):
        ("мир", "тот же нумерованный список источников страницы метода, "
                "третья запись: номер порядковый, а не измеренный"),
    ("render", "60086", "IEC 60086, the international standard"):
        ("мир", "номер международного стандарта на первичные батареи: это "
                "его имя, а не измеренная величина, и в снимке его нет"),
    ("render", "4", "4] Reese"):
        ("мир", "тот же нумерованный список источников страницы метода, "
                "четвёртая запись: номер порядковый, а не измеренный"),
    ("render", "2022", "United States, 2022"):
        ("мир", "год принятия закона Риза в США: факт вне каталога "
                "производителя, проверяемый только по самому закону"),
    ("depth", "1", "Poison Help line at 1-800-222-1222 straight away"):
        ("мир", "телефон национальной токсикологической службы США: набор "
                "цифр, у которого нет источника в данных о батареях"),
    ("depth", "800", "Poison Help line at 1-800-222-1222 straight away"):
        ("мир", "тот же телефон национальной токсикологической службы США, "
                "вторая группа цифр: считать её тоже не из чего"),
    ("depth", "222", "Poison Help line at 1-800-222-1222 straight away"):
        ("мир", "тот же телефон национальной токсикологической службы США, "
                "третья группа цифр: считать её тоже не из чего"),
    ("depth", "1222", "Poison Help line at 1-800-222-1222 straight away"):
        ("мир", "тот же телефон национальной токсикологической службы США, "
                "четвёртая группа цифр: считать её тоже не из чего"),
    # --- проверяемые правила ---
    ("render", "150", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("render", "3", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("render", "1.5", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("prose", "150", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("prose", "3", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("prose", "1.5", "150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V"):
        ("правило", "энергия вдвое"),
    ("render", "12.5", "a cell measuring 12.5 mm is coded 12"):
        ("правило", "код округляет до целого"),
    ("render", "12", "a cell measuring 12.5 mm is coded 12"):
        ("правило", "код округляет до целого"),
    ("render", "a tenth", "outside size to a tenth of a millimeter"):
        ("правило", "печать в десятую долю"),
    ("render", "a tenth", "published dimensions to a tenth of a millimeter"):
        ("правило", "печать в десятую долю"),
    # --- АРНОСТЬ СРАВНЕНИЯ. «Два» здесь не счёт по корпусу, а число сторон
    # у отношения, которое сайт печатает: эта страница и один другой
    # элемент. Правило доказывает это и по коду, и по отданным таблицам.
    ("render", "two nominals", "the higher of the two nominals"):
        ("правило", "сравнение двустороннее"),
    ("render", "two readings", "One gap, two readings"):
        ("правило", "сравнение двустороннее"),
    ("render", "two rules", "Outside those two rules the class changes"):
        ("правило", "сравнение двустороннее"),
    ("render", "two cannot", "everything the first two cannot see"):
        ("правило", "сравнение двустороннее"),
    ("render", "two cells", "Two cells are a drop-in when every "
                            "cross-section matches"):
        ("правило", "сравнение двустороннее"),
    ("render", "two nominal", "the gap between two nominal voltages"):
        ("правило", "сравнение двустороннее"),
    ("render", "two pages", "whichever of the two pages you meet it on"):
        ("правило", "сравнение двустороннее"),
    ("render", "two voltages", "how far apart two voltages are"):
        ("правило", "сравнение двустороннее"),
    ("render", "two never", "the two never answer each other"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two part", "where the two part company the measurement wins"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two cells", "one relation between two cells"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two run", "where the two run at the same voltage"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two nominal", "the higher of the two nominal voltages"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two nominal", "the gap between two nominal voltages taken "
                             "against the higher of the two"):
        ("правило", "сравнение двустороннее"),
    ("render", "two nominal", "decided on the gap against the higher of the "
                              "two nominal voltages"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two directions", "differs between the two directions"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two disagree", "The two disagree"):
        ("правило", "сравнение двустороннее"),
    ("prose", "two cells", "because two cells filed next to each other by "
                           "name"):
        ("правило", "сравнение двустороннее"),
    ("depth", "two cells", "the one check that separates two cells of one "
                           "envelope"):
        ("правило", "сравнение двустороннее"),
    ("depth", "two cells", "a kitchen scale separates two cells of one "
                           "envelope"):
        ("правило", "сравнение двустороннее"),
    ("depth", "two apart", "tells the two apart on a table"):
        ("правило", "сравнение двустороннее"),
    # --- ЧЕМ МЕРЯЮТ ОБОЛОЧКУ. Две величины у круглой, три у призматической —
    # это свойство самой shell(), и правило читает его по снимку.
    ("render", "three measurements", "boxes with three measurements rather "
                                     "than two"):
        ("правило", "коробку меряют тремя"),
    ("render", "three measurements", "three measurements for a box"):
        ("правило", "коробку меряют тремя"),
    ("render", "three figures", "a box cell takes three figures"):
        ("правило", "коробку меряют тремя"),
    ("prose", "two cross-sections", "two cross-sections to match instead of "
                                    "one diameter"):
        ("правило", "коробку меряют тремя"),
    ("depth", "three measurements", "a box cell has three measurements to "
                                    "agree on rather than two"):
        ("правило", "коробку меряют тремя"),
    # --- СЛОВО ОТНОШЕНИЯ ВЫБИРАЕТСЯ ЧИСЛОМ. Таблица кратностей: каждое
    # слово стоит против своего множителя, и это проверяется.
    ("prose", "three times", "roughly three times the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "four times", "roughly four times the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "five times", "roughly five times the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "six times", "roughly six times the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "eight times", "roughly eight times the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "a third", "roughly a third of the nominal of"):
        ("правило", "отношение выбирается по числу"),
    ("prose", "a quarter", "roughly a quarter of the nominal of"):
        ("правило", "отношение выбирается по числу"),
    # --- ИЗВЕСТНЫЕ ОТВЕТЫ ДЛЯ ДИАПАЗОНА: это не проза, а эталон, и он же
    # доказывает, что вырожденный диапазон теряет слово «from».
    ("prose", "2", "from 2 to 3.2 mm"):
        ("правило", "диапазон не вырождается"),
    ("prose", "3.2", "from 2 to 3.2 mm"):
        ("правило", "диапазон не вырождается"),
    # --- ФАКТЫ ВНЕ СНИМКА ---
    ("render", "two dates", "the difference between two dates is itself "
                            "checkable"):
        ("мир", "экспорт данных датирован, и сравнивают всегда ДВА датированных "
                "среза: это свойство самого способа сравнения, а не величина "
                "из каталога, и посчитать его по снимку не из чего"),
    # --- ЦИТАТЫ НОРМЫ. Номер титула, части и параграфа — ИМЯ документа, а
    # не измеренная величина: в каталоге производителя его нет и посчитать
    # его не из чего. Текст сверен с самой нормой (eCFR, 16 CFR часть 1263,
    # источник 88 FR 65295 от 21.09.2023), а не с пересказом.
    ("depth", "16", "greater than its height, 16 CFR 1263.2"):
        ("мир", "титул 16 Свода федеральных правил США: имя документа"),
    ("depth", "1263.2", "greater than its height, 16 CFR 1263.2"):
        ("мир", "параграф 1263.2 — тот, где дано определение кнопочного "
                "элемента, и оно процитировано рядом почти дословно"),
    ("depth", "15", "Reese's Law (15 U.S.C. 2056e)"):
        ("мир", "титул 15 Кодекса США: имя документа, не величина"),
    ("depth", "2056", "Reese's Law (15 U.S.C. 2056e)"):
        ("мир", "номер раздела 2056e Кодекса США, куда внесён закон Риза"),
    ("depth", "16", "and 16 CFR part 1263 put child-resistant"):
        ("мир", "титул 16 Свода федеральных правил, вторая ссылка той же "
                "строки: часть 1263 издана во исполнение этого закона"),
    ("depth", "1263", "and 16 CFR part 1263 put child-resistant"):
        ("мир", "номер части Свода федеральных правил США, которая и есть "
                "правило о кнопочных элементах: имя документа, а не "
                "измеренная величина"),
    ("depth", "21", "imported after 21 September 2024 carry it"):
        ("мир", "день из переходного положения нормы: 16 CFR 1263.1(b), "
                "«after September 21, 2024, must meet the labeling "
                "requirements for battery packaging»"),
    ("depth", "2024", "imported after 21 September 2024 carry it"):
        ("мир", "год из того же переходного положения нормы"),
    ("depth", "16", "rule: 16 CFR 1263.1(d) records"):
        ("мир", "титул 16 Свода, третья ссылка: та же норма, ветка изъятия"),
    ("depth", "1263.1", "rule: 16 CFR 1263.1(d) records"):
        ("мир", "параграф 1263.1(d) — тот, где записано решение Комиссии, "
                "что цинк-воздушные кнопочные элементы не несут опасности "
                "проглатывания и под часть не подпадают"),
    ("depth", "1263", "rule: 16 CFR 1263.1(d) records"):
        ("мир", "номер той же части Свода в ссылке на ветку изъятия: часть "
                "одна, параграфов в ней несколько"),
    ("depth", "16", "household trash (16 CFR 1263.4(b)(3))"):
        ("мир", "титул 16 Свода, четвёртая ссылка: требование к надписи"),
    ("depth", "1263.4", "household trash (16 CFR 1263.4(b)(3))"):
        ("мир", "параграф 1263.4(b)(3) — перечень обязательных надписей, "
                "откуда взята формулировка про бытовой мусор"),
    ("depth", "3", "household trash (16 CFR 1263.4(b)(3))"):
        ("мир", "номер подпункта (b)(3) параграфа 1263.4 — там перечислены "
                "обязательные надписи, и формулировка про бытовой мусор "
                "взята оттуда"),
    ("render", "100", 'width="100 " height='):
        ("мир", "доля ширины в готовом сниппете встраивания: это не "
                "измеренная величина, а указание «во всю ширину того места, "
                "куда вставили», и другого значения у него быть не может"),
    ("cells", "41", "e41e.pdf"):
        ("мир", "имя файла даташита у производителя: имя документа, а не "
                "измеренная величина, и в снимке его не из чего вывести"),
    ("depth", "two ways", "The standard writes this designation two ways"):
        ("мир", "IEC 60086 задаёт короткую и полную запись обозначения — это "
                "правило самого стандарта, которого в каталоге производителя "
                "нет и пересчитать его по снимку невозможно"),
}


def _prose_number(v):
    """Число из поля снимка. Поле умеет держать «N/A» и пустую строку, и
    поднятое исключение обвалило бы весь набор проверок, а не покраснело."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _prose_rule_energy(files):
    """«150 мА·ч при 3 В — вдвое больше энергии, чем 150 мА·ч при 1,5 В»:
    арифметика примера обязана сходиться по той же формуле, что и сайт."""
    if 150 * 3.0 != 2.0 * (150 * 1.5):
        return ["пример энергии на /method/ не сходится: 150 x 3 это не вдвое "
                "больше, чем 150 x 1,5"]
    return []


def _prose_rule_code_rounding(files):
    """«Элемент 12,5 мм кодируется как 12»: в снимке обязан НАЙТИСЬ такой
    элемент, иначе пример объясняет правило, которого в данных нет."""
    for rec in _snapshot():
        d, iec = _prose_number(rec.get("battery-diameter")), rec.get("battery-iec")
        if d is None or not isinstance(iec, str):
            continue
        if abs(d - 12.5) < 0.05 and re.search(r"[A-Z]{1,2}12\d\d", iec):
            return []
    return ["пример «12,5 мм кодируется как 12» не подтверждается снимком: "
            "ни одной записи 12,5 мм с кодом на 12 в нём нет"]


def _prose_rule_tenth(files):
    """«Опубликованный габарит с точностью до десятой доли миллиметра»:
    ни одна отданная страница не печатает размер С ДВУМЯ знаками после
    запятой. Утверждение о точности проверяется по НАПЕЧАТАННОМУ."""
    bad, seen = [], 0
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r"(\d+\.\d+)\s*mm\b", _text(t)):
            seen += 1
            if len(m.group(1).split(".")[1]) > 1:
                bad.append("%s: размер «%s mm» напечатан точнее десятой доли, "
                           "а сайт обещает десятую" % (p, m.group(1)))
    if not seen:
        bad.append("на отданных страницах не нашлось ни одного размера в мм — "
                   "проверять обещание о десятой доле не на чем")
    return bad[:4]


def _prose_rule_pair_is_two(files):
    """«ДВА» — арность всех отношений сайта, и она проверяется, а не
    подразумевается: «two cells», «two nominals», «two readings», «two
    pages», «two directions» — всё это про ОДНО сравнение, у которого ровно
    две стороны. Доказывается и по коду, и по отданным страницам."""
    import inspect
    bad = []
    # Функции названы ПОИМЁННО, а не через getattr с вычисленным именем:
    # разбор охвата такое обращение прочитать не может, и охват стал бы
    # догадкой — об этом краснеет соседний мета-гейт.
    for name, fn in (("fits", C.fits), ("voltage_gap", C.voltage_gap),
                     ("fit_gap", C.fit_gap),
                     ("code_depth_verdict", C.code_depth_verdict)):
        pos = [p for p in inspect.signature(fn).parameters.values()
               if p.default is inspect.Parameter.empty]
        if len(pos) != 2:
            bad.append("C.%s берёт %d обязательных довода, а проза обещает "
                       "отношение между двумя" % (name, len(pos)))
    # И по отданному: в таблице сравнения СТРОКА называет ровно один другой
    # элемент, то есть отношение и правда двустороннее — эта страница и он.
    seen, rows = 0, 0
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r'<table class="bx-fits">.*?</table>', t, re.S):
            seen += 1
            body = re.search(r"<tbody>(.*?)</tbody>", m.group(0), re.S)
            for tr in re.findall(r"<tr>(.*?)</tr>",
                                 body.group(1) if body else "", re.S):
                rows += 1
                if tr.count("<th>") != 1:
                    bad.append("%s: строка сравнения называет %d элементов, "
                               "а отношение обещано между двумя"
                               % (p, tr.count("<th>")))
    if not seen or not rows:
        bad.append("таблиц сравнения не нашлось — арность отношения "
                   "проверять не на чем")
    return bad[:4]


def _prose_rule_box_measures(files):
    """«Три меры у коробки, две у монеты» — по СНИМКУ, а не по памяти:
    shell() круглой формы возвращает две величины, призматической — три, и
    в корпусе обязаны найтись обе."""
    got = {}
    for rec in _snapshot():
        h = _prose_number(rec.get("battery-height"))
        d = _prose_number(rec.get("battery-diameter"))
        lg = _prose_number(rec.get("battery-length"))
        wd = _prose_number(rec.get("battery-width"))
        if h is None:
            # Запись без высоты не меряется вовсе — НАЗВАННАЯ тихая ветка.
            continue
        if d is not None:
            got.setdefault("round", set()).add(2)
        elif lg is not None and wd is not None:
            got.setdefault("box", set()).add(3)
    bad = []
    if got.get("round") != {2}:
        bad.append("круглая оболочка меряется %s величинами, а проза обещает "
                   "две" % sorted(got.get("round") or []))
    if got.get("box") != {3}:
        bad.append("призматическая оболочка меряется %s величинами, а проза "
                   "обещает три" % sorted(got.get("box") or []))
    return bad


def _prose_rule_answer_columns(files):
    """«Три вопроса в трёх колонках» — против ЗАГОЛОВКОВ отданных таблиц.
    Число колонок печатается из ANSWER_COLUMNS, и здесь доказывается, что
    именно эти заголовки на страницах и стоят."""
    import render as rd
    bad, seen = [], 0
    want = list(rd.ANSWER_COLUMNS)
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r"<thead><tr>((?:<th>[^<]*</th>)+)</tr></thead>",
                             t):
            heads = re.findall(r"<th>([^<]*)</th>", m.group(1))
            # Три колонки ответа идут ПОДРЯД и сразу за именем элемента:
            # справа от них таблица вольна нести что угодно ещё.
            if heads[1:1 + len(want)] == want:
                seen += 1
    if not seen:
        bad.append("ни одной таблицы с колонками %s на отданных страницах — "
                   "число колонок обещано и не подтверждено" % want)
    return bad


def _prose_rule_ratio_words(files):
    """СЛОВО ОТНОШЕНИЯ ВЫБИРАЕТСЯ ЧИСЛОМ. «Roughly double» было набрано в
    шаблоне про литий и печаталось на 33 страницах, из которых 17 несли
    1,5 В: это не вдвое, это столько же. Таблица кратностей проверяется с
    двух сторон — известными ответами и тем, что каждое слово стоит против
    СВОЕГО множителя."""
    import prose as pr
    bad = [("отношение %s к %s: ждали %s, вышло %s" % x)
           for x in pr.ratio_selftest()]
    word = {2: "double", 3: "three", 4: "four", 5: "five", 6: "six",
            8: "eight", 10: "ten"}
    for n, phrase in sorted(pr.RATIO_UP.items()):
        if word.get(n) not in phrase:
            bad.append("кратность %d названа «%s» — слово не про это число"
                       % (n, phrase))
        if pr.ratio_phrase(1.5 * n, [1.5], "X") != phrase % "X":
            bad.append("кратность %d не выбирается по числу: вышло «%s»"
                       % (n, pr.ratio_phrase(1.5 * n, [1.5], "X")))
    down = {2: "half", 3: "a third", 4: "a quarter"}
    for n, phrase in sorted(pr.RATIO_DOWN.items()):
        if down.get(n) not in phrase:
            bad.append("доля 1/%d названа «%s» — слово не про это число"
                       % (n, phrase))
        if pr.ratio_phrase(1.5 / n, [1.5], "X") != phrase % "X":
            bad.append("доля 1/%d не выбирается по числу: вышло «%s»"
                       % (n, pr.ratio_phrase(1.5 / n, [1.5], "X")))
    if not pr.RATIO_UP or not pr.RATIO_DOWN:
        bad.append("таблица кратностей пуста — проверять нечего")
    return bad[:6]


def _prose_rule_span(files):
    """ДИАПАЗОН С РАВНЫМИ КОНЦАМИ — НЕ ДИАПАЗОН. Известные ответы для span(),
    плюс запрет на «from X to X» в отданном тексте: восемнадцать страниц
    печатали «at depths from 50.5 to 50.5 mm»."""
    import prose as pr
    bad = ["диапазон разошёлся с известным ответом: %s -> %s, а надо %s"
           % (a, g, w) for a, w, g in pr.span_selftest()]
    seen = 0
    for p, t in sorted(_html(files).items()):
        for m in re.finditer(r"from (\d+(?:\.\d+)?) to (\d+(?:\.\d+)?)",
                             _text(t)):
            seen += 1
            if m.group(1) == m.group(2):
                bad.append("%s: «%s» — концы диапазона равны, это не "
                           "диапазон" % (p, m.group(0)))
    if not seen:
        bad.append("на отданных страницах нет ни одного диапазона — "
                   "проверять вырождение не на чем")
    return bad[:6]


PROSE_QUANTITY_RULES = {
    "энергия вдвое": _prose_rule_energy,
    "код округляет до целого": _prose_rule_code_rounding,
    "печать в десятую долю": _prose_rule_tenth,
    "сравнение двустороннее": _prose_rule_pair_is_two,
    "коробку меряют тремя": _prose_rule_box_measures,
    "отношение выбирается по числу": _prose_rule_ratio_words,
    "диапазон не вырождается": _prose_rule_span,
}

_PROSE_CYR = re.compile(u"[Ѐ-ӿ]")
_PROSE_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
_PROSE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]*")
_PROSE_NUMWORD = ("zero one two three four five six seven eight nine ten "
                  "eleven twelve thirteen fourteen fifteen sixteen seventeen "
                  "eighteen nineteen twenty thirty forty fifty sixty seventy "
                  "eighty ninety hundred thousand").split()
_PROSE_FRACWORD = "half third quarter fifth tenth hundredth".split()
# Числительные, которые СЧИТАЮТ набор. «One» и «zero» сюда не входят: перед
# существительным это артикль и слово, а не счёт по корпусу.
_PROSE_COUNTWORD = [w for w in _PROSE_NUMWORD if w not in ("zero", "one")]
# Единицы, которые сайт СЧИТАЕТ САМ. Число рядом с любой из них — утверждение
# о данных, и набирать его руками нельзя.
_PROSE_MEASURE = ("mm millimeter millimeters V volt volts mAh cc mWh ohm "
                  "ohms g gram grams percent character characters digit "
                  "digits").split()


def _prose_visible(s):
    """ВИДИМЫЙ текст шаблона: без тегов, без сущностей, без спецификаторов.

    Разметку выкидываем ровно потому же, почему её выкидывает гейт слов:
    «text-align:right» — это не слово «right», а «width=20» — не величина в
    предложении. Спецификатор формата — наоборот, ЗНАК того, что величину
    подставят, то есть посчитают: место подстановки нас не интересует.
    """
    t = re.sub(r"<[^<>]*>", " ", s)
    t = re.sub(r"&[a-zA-Z]+;|&#\d+;", " ", t)
    t = re.sub(r"%\([a-zA-Z_]+\)[sdfr]|%[-+ 0-9.]*[sdfr%]", " ", t)
    # Пробелы схлопываются: шаблон разложен по строкам исходника, и якорь
    # объявления — это ПРЕДЛОЖЕНИЕ, а не его вёрстка в файле.
    return " ".join(t.split())


def _prose_hits(text):
    """Величины в видимом тексте: (вид, как напечатано, токен вокруг цифр)."""
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        tok = None
        for t in _PROSE_TOKEN.finditer(text):
            if t.start() <= m.start() and t.end() >= m.end():
                tok = t.group(0)
                break
        out.append(("цифрами", m.group(0), tok))
    low = text.lower()
    # «A third-party network» — не треть: дефис продолжает слово, а не
    # величину. Дробь без своего существительного величиной не считается.
    frac = (r"\b(?:a|an|the|" + "|".join(_PROSE_NUMWORD) + r")\s+(?:"
            + "|".join(_PROSE_FRACWORD) + r")\b(?!-)")
    for m in re.finditer(frac, low):
        out.append(("словами", m.group(0), None))
    # Числительное перед ЛЮБЫМ словом, а не только перед единицей измерения.
    # Величина, набранная словом, невидима для всякой сверки по собранному:
    # MIN_HUB стоял словом «three» в шести местах, подмена константы с 3 на 4
    # прошла 88 гейтов из 88 — сайт публиковал шесть оболочек при пороге 4 и
    # печатал «three», — а сам этот гейт держался за то же слово якорем.
    # «Five things that are calculated» стояло рядом со списком из семи видов,
    # «these five carry» — рядом со срезом без счёта.
    broad = (r"\b(?:" + "|".join(_PROSE_COUNTWORD) + r")\s+[a-z][a-z'-]*")
    for m in re.finditer(broad, low):
        out.append(("словами", m.group(0), None))
    # «One» и «zero» перед НЕ-единицей — это английский артикль и
    # существительное («one of them», «absent and zero are different
    # answers»), а не счёт по корпусу. Перед единицей, которую сайт считает
    # сам, они остаются величиной и ловятся здесь.
    meas = (r"\b(?:zero|one)\s+(?:" + "|".join(_PROSE_MEASURE) + r")\b")
    for m in re.finditer(meas, low):
        out.append(("словами", m.group(0), None))
    return out


def _prose_parse_known_answers():
    """Разбор — ИЗВЕСТНЫМИ ОТВЕТАМИ. Разбор, переставший что-либо находить,
    зеленит гейт молча: пустая выборка кричит, слепая молчит."""
    bad = []
    cases = (
        ("the same 3 V", [("цифрами", "3")]),
        ("carries its whole identity in six characters",
         [("словами", "six characters")]),
        ("within a third of a millimeter", [("словами", "a third")]),
        ("A tenth of a millimeter under a thumb", [("словами", "a tenth")]),
        ("A third-party advertising network", []),
        ("%s mm apart", []),
        ('<a href="/346/">346</a> is listed here', [("цифрами", "346")]),
        ('<td style="width:20px">a wide cell</td>', []),
        # Числительное перед НЕ-единицей: ровно та дыра, через которую
        # «three designations» и «five things» прошли мимо всех проверок.
        ("carry three designations or more", [("словами", "three designations")]),
        ("These five carry the most", [("словами", "five carry")]),
        ("adds five things that are calculated", [("словами", "five things")]),
        # «One» перед существительным — артикль, перед единицей — величина.
        ("one of them enters the same opening", []),
        ("Absent and zero are different answers", []),
        ("the same one volt everywhere", [("словами", "one volt")]),
        ("seventeen designations share it", [("словами", "seventeen designations")]),
    )
    for src, want in cases:
        got = [(k, v) for k, v, _t in _prose_hits(_prose_visible(src))]
        if got != want:
            bad.append("разбор величин прозы разошёлся с известным ответом: "
                       "на «%s» ждали %s, вышло %s" % (src, want, got))
    # ИМЯ ПРОТИВ ВЕЛИЧИНЫ — известными ответами, обе стороны. Докстрока
    # _prose_is_code обещала защиту по длине, которой в теле не было: 104
    # обозначения снимка состоят из одних цифр, и подставленный вместо
    # расчёта литерал 341 прошёл 88 гейтов из 88.
    codes = _prose_names()
    for tok, want in (("CR2032", True), ("AG13", True), ("LR44W", True),
                      ("346", False), ("341", False), ("3", False),
                      ("2032", False), ("NOSUCH9", False)):
        if _prose_is_code(tok, codes) is not want:
            bad.append("имя против величины разошлось с известным ответом: "
                       "«%s» считается %s" % (tok, "именем" if not want
                                              else "величиной"))
    return bad


def _prose_skipped_nodes(tree, mod):
    """Строки, которые прозой не являются: докстроки, машинный текст и
    шаблоны разбора. Каждое исключение — либо структурное (докстрока,
    аргумент re.*), либо названное поимённо с причиной."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            body = getattr(n, "body", None)
            if body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
        if isinstance(n, ast.Assign):
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if any((mod, x) in PROSE_MACHINE_TEXT for x in names):
                for s in ast.walk(n.value):
                    if isinstance(s, ast.Constant) and isinstance(s.value, str):
                        out.add(id(s))
        if isinstance(n, ast.Call):
            f = n.func
            nm = (f.attr if isinstance(f, ast.Attribute)
                  else (f.id if isinstance(f, ast.Name) else ""))
            is_re = (isinstance(f, ast.Attribute)
                     and isinstance(f.value, ast.Name) and f.value.id == "re")
            if is_re or (mod, nm) in PROSE_PATTERN_ARGS:
                for a in n.args:
                    for s in ast.walk(a):
                        if isinstance(s, ast.Constant) \
                                and isinstance(s.value, str):
                            out.add(id(s))
    return out


def _prose_names():
    """ИМЕНА, внутри которых цифра — часть имени, а не величина.

    Две половины, и обе объявлены. Обозначения читаются С ДИСКА из снимка
    (_designations), чужие маркировки берутся из C.TRADE_MARKINGS — таблицы,
    прибитой руками в REFERENCE_CONSTS длиной и образцами: «AG13» это имя
    ровно потому, что оно в этой таблице стоит, а «AG14» стоять в ней не
    будет и величиной пройти не сможет.
    """
    out = set(_designations())
    for mark, iec, _whose in C.TRADE_MARKINGS:
        out.add(mark.upper())
        out.add(iec.upper())
    return out


def _prose_is_code(tok, codes):
    """Цифра ВНУТРИ обозначения — это имя, а не величина: «CR2032» и «AG13»
    называют элемент. Доказывается снимком, а не списком исключений.

    Хвост часового исполнения (W, SW) — часть самого стандарта, и поиск
    сайта снимает его перед сверкой; здесь то же правило и по той же
    причине.

    ГОЛАЯ ЦИФРА. Докстрока обещала, что цифра короче трёх знаков
    обозначением не считается, а проверки длины в теле не было вовсе:
    защита была СЛУЧАЙНОЙ. В снимке 104 обозначения из одних цифр (164,
    193, 201, 303, 333, 341, 346), и подстановка литерала 341 вместо
    посчитанного зазора прошла 88 гейтов из 88, напечатав «341 mm apart»
    на 163 строках. Теперь голая цифра НЕ прячется за именем никогда:
    имя, состоящее из одних цифр, в прозе пишется только подстановкой, и
    если такое имя и правда надо набрать, оно объявляется в
    PROSE_QUANTITIES, как всякая другая набранная величина.
    """
    if not tok:
        return False
    t = tok.upper().strip(".,;:")
    if t.isdigit():
        return False
    if t in codes:
        return True
    for suf in ("SW", "W"):
        if t.endswith(suf) and t[:-len(suf)] in codes:
            return True
    return False


def _prose_snapshot_value(code, field):
    """Величина поля из СНИМКА для одного обозначения, напечатанная так же,
    как её печатает сайт. Записи обязаны сойтись между собой."""
    vals = set()
    for rec in _snapshot():
        iec = rec.get("battery-iec")
        names = []
        if isinstance(iec, str):
            names = [x.strip().upper() for x in re.split(r"[,;]| or ", iec)]
        elif isinstance(iec, list):
            names = [str(x).strip().upper() for x in iec]
        if code.upper() not in names:
            continue
        v = _prose_number(rec.get(field))
        if v is not None:
            vals.add(round(v, 1))
    if len(vals) != 1:
        return None
    return ("%.1f" % vals.pop()).rstrip("0").rstrip(".")


def _prose_check_one(key, rule, files):
    """Одно объявление против того, чем оно себя оправдывает."""
    mod, printed, anchor = key
    # Величина ищется в якоре БЕЗ ОГЛЯДКИ НА РЕГИСТР: находится она в
    # приведённом к нижнему регистру тексте, а якорь — кусок исходного
    # предложения, и «Two cells» в начале фразы иначе объявить нечем.
    if printed not in anchor.lower():
        return ["величина %s.«%s» объявлена якорем «%s», который её самой не "
                "содержит: якорь обязан быть тем предложением, о котором речь"
                % (mod, printed, anchor)]
    kind = rule[0]
    if kind == "мир":
        if len(rule[1]) < 40:
            return ["для %s.«%s» причина не написана" % (mod, printed)]
        return []
    if kind == "снимок":
        code, field = rule[1]
        got = _prose_snapshot_value(code, field)
        if got is None:
            return ["величина %s.«%s» объявлена как %s элемента %s, а в "
                    "снимке такого значения нет или записи о нём спорят"
                    % (mod, printed, field, code)]
        if got != printed:
            return ["в шаблоне напечатано «%s», а %s элемента %s в снимке это "
                    "%s" % (printed, field, code, got)]
        return []
    if kind == "правило":
        fn = PROSE_QUANTITY_RULES.get(rule[1])
        if fn is None:
            return ["для %s.«%s» названо правило «%s», которого нет"
                    % (mod, printed, rule[1])]
        return fn(files)
    return ["у %s.«%s» объявлен неизвестный вид «%s»" % (mod, printed, kind)]


def g_prose_quantities_declared(files):
    """ФИЗИЧЕСКАЯ ВЕЛИЧИНА В ШАБЛОНЕ ПРОЗЫ ЛИБО ПОСЧИТАНА, ЛИБО ОБЪЯВЛЕНА.

    ЧЕГО НЕ ВИДНО В ОТДАННОМ ТЕКСТЕ, и почему этот гейт единственный читает
    ИСХОДНИК. Предложение с набранной руками величиной грамматично, число в
    нём правдоподобно, единица на месте: «They are the same hazard and the
    same 3 V» неотличимо от исправного текста, пока не спросишь, ОТКУДА эта
    тройка. Она была набрана — и на четырёх страницах из десяти стояла рядом
    с именами элементов на 1,4 и 1,5 В, то есть печатала обратное главному
    утверждению сайта. Так же «в шесть знаков» о коде из трёх, «десятая доля
    миллиметра» там, где ветка впускает от 0,4 до 1,2 мм, и «треть
    миллиметра» рядом с посчитанными «0.3 mm» на той же странице метода.
    Ни один гейт по собранному этого увидеть не может: он сверяет
    напечатанное с напечатанным, а здесь неверен ИСТОЧНИК числа.

    ЧТО ЧИТАЕТСЯ. Каждая строковая константа шести модулей, из которых
    собираются страницы, кроме докстрок, машинного текста (объявлен поимённо
    с причиной) и шаблонов разбора. У строки берётся ВИДИМЫЙ текст — без
    тегов, сущностей и спецификаторов, — и в нём ищутся цифры И величины
    словами: три из пяти найденных дыр были написаны словами, и гейт,
    искавший бы только цифры, прошёл бы мимо них.

    ЧТО РАЗРЕШЕНО. Цифра внутри ОБОЗНАЧЕНИЯ («CR2032», «AG13») — это имя, и
    доказывается оно снимком, а не списком исключений. Всё остальное
    объявляется в PROSE_QUANTITIES: с причиной, если величина лежит вне
    снимка (год закона, номер стандарта, телефон), или с проверкой, если её
    можно пересчитать. Спецификатор формата — знак того, что величину
    посчитают, и он-то и есть исправное состояние.

    ОБЕ СТОРОНЫ. Необъявленная величина — провал; объявление без своей
    величины в шаблонах — тоже провал, и якорь объявления обязан содержать
    саму величину, чтобы переписанное предложение проходило через эту
    таблицу, а не мимо неё.
    """
    bad = []
    _sample(bad, len(files), "отданных файлов")
    _sample(bad, len(PROSE_MODULES), "модулей, из которых собраны страницы")
    _sample(bad, len(PROSE_QUANTITIES), "объявленных величин прозы")
    _sample(bad, len(PROSE_QUANTITY_RULES), "правил, проверяющих величины")
    bad.extend(_prose_parse_known_answers())
    codes = _prose_names()
    if len(codes) < 100:
        return bad + ["обозначений из снимка прочитано %d — источник не тот"
                      % len(codes)]
    _sample(bad, len(C.TRADE_MARKINGS), "объявленных чужих маркировок")
    src = _sources()
    used, strings, hits = set(), 0, 0
    for mod in PROSE_MODULES:
        text = src.get(mod)
        if text is None:
            bad.append("исходник %s не прочитан — его шаблоны не осмотрены "
                       "вовсе, и это провал, а не пропуск" % mod)
            continue
        name = mod[:-3]
        tree = ast.parse(text)
        skip = _prose_skipped_nodes(tree, name)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)):
                continue
            if id(node) in skip or _PROSE_CYR.search(node.value):
                continue
            vis = _prose_visible(node.value)
            if len(_PROSE_WORD.findall(vis)) < 3:
                continue
            strings += 1
            for kind, printed, tok in _prose_hits(vis):
                if kind == "цифрами" and _prose_is_code(tok, codes):
                    continue
                hits += 1
                key = None
                for k in PROSE_QUANTITIES:
                    if k[0] == name and k[1] == printed and k[2] in vis:
                        key = k
                        break
                if key is None:
                    bad.append("%s: величина «%s» набрана руками в шаблоне "
                               "прозы и ниоткуда не выведена: «%s»"
                               % (mod, printed,
                                  " ".join(vis.split())[:90]))
                    continue
                used.add(key)
    _sample(bad, strings, "шаблонов прозы, прочитанных разбором")
    _sample(bad, hits, "величин, найденных в шаблонах")
    # Правило, которое ни одна величина не называет, — описанный и никем не
    # дёрнутый рычаг: он выглядит проверкой и ею не является.
    named = {r[1] for r in PROSE_QUANTITIES.values() if r[0] == "правило"}
    for nm in sorted(PROSE_QUANTITY_RULES):
        if nm not in named:
            bad.append("правило «%s» объявлено, а ни одна величина его не "
                       "называет: проверка, которую никто не зовёт, "
                       "выглядит проверкой и ею не является" % nm)
    for key in sorted(PROSE_QUANTITIES):
        if key not in used:
            bad.append("объявлена величина %s.«%s» при «%s», а в шаблонах её "
                       "нет: объявление, которому нечего оправдывать, "
                       "выглядит объяснением и им не является" % key)
            continue
        bad.extend(_prose_check_one(key, PROSE_QUANTITIES[key], files))
    return bad[:20]


# --------------------------------------------------------------------------
# ПЯТОЕ СЕМЕЙСТВО: ОТНОШЕНИЕ — ТОЖЕ ВЕЛИЧИНА.
#
# Прошлая волна посчитала числа и оставила СЛОВА, которые их сравнивают.
# Сравнение, превосходная степень, диапазон, принадлежность к набору и
# дизъюнкция — все они утверждают что-то о величинах, и каждое обязано
# считаться из тех же чисел, что напечатаны рядом.

RATIO_WORD_FOR = {2: "double", 3: "three times", 4: "four times",
                  5: "five times", 6: "six times", 8: "eight times"}


def _rel_alkaline_silver():
    """Номиналы щелочного и серебряного классов ИЗ СНИМКА, посчитанные тут
    же и независимо от prose: гейт, берущий эталон у проверяемого,
    соглашается сам с собой."""
    out = {}
    for rec in _snapshot():
        ch = (rec.get("battery-chemistry") or "")
        ch = ch.lower() if isinstance(ch, str) else ""
        v = _prose_number(rec.get("battery-voltage"))
        if v is None:
            continue
        for kind in ("alkaline", "silver"):
            if kind in ch:
                out.setdefault(kind, {})
                out[kind][v] = out[kind].get(v, 0) + 1
    return {k: sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for k, d in out.items()}


_REL_IEC4 = re.compile(r"^([A-Z]{1,2})(\d{2})(\d{2})$")


def _rel_snapshot_names(rec):
    """Обозначения одной записи снимка — тем же разбором, что и у соседних
    проверок: поле держит и список, и строку через запятую или «or».

    Имя берётся И из post_title: у CR1632 поле battery-iec это «N/A», а имя,
    под которым эта запись выходит на сайт, стоит в заголовке. Проверка,
    читавшая только battery-iec, назвала бы такой код неизвестным и
    покраснела бы на исправной странице.
    """
    out = []
    iec = rec.get("battery-iec")
    if isinstance(iec, list):
        out = [str(x).strip().upper() for x in iec]
    elif isinstance(iec, str):
        out = [x.strip().upper() for x in re.split(r"[,;]| or ", iec)]
    title = rec.get("post_title")
    if isinstance(title, str) and title.strip():
        out.append(title.strip().upper())
    return [x for x in out if x and x != "N/A"]


def _rel_code_holds_height():
    """Кодирует ли обозначение СВОЮ опубликованную высоту — по снимку и
    своим разбором четырёхзначного кода.

    Эталон здесь считается заново: cells.code_check ответил бы то же самое,
    и гейт согласился бы сам с собой при любой ошибке в нём.
    """
    out = {}
    for rec in _snapshot():
        h = _prose_number(rec.get("battery-height"))
        if h is None:
            # Записи без опубликованной высоты нечем проверять, и они не
            # объявляются ни кодирующими, ни спорящими: НАЗВАННАЯ тихая
            # ветка, а не молчаливый пропуск.
            continue
        for name in _rel_snapshot_names(rec):
            m = _REL_IEC4.match(name)
            ok = bool(m) and abs(int(m.group(3)) / 10.0 - h) < 0.05
            out[name] = out.get(name, False) or ok
    return out


def _rel_size_disputes():
    """Обозначения, чьи записи публикуют РАЗНЫЕ напечатанные габариты.

    Считается по снимку, а не по cells.size_spread: у той функции гейта не
    было ни одного, и сверять её с ней же значило бы соглашаться с ней.
    """
    fields = ("battery-diameter", "battery-height", "battery-length",
              "battery-width")
    by = {}
    for rec in _snapshot():
        for name in _rel_snapshot_names(rec):
            by.setdefault(name, []).append(rec)
    out = set()
    for name, recs in by.items():
        for f in fields:
            vals = {round(v, 1) for v in
                    (_prose_number(r.get(f)) for r in recs) if v is not None}
            if len(vals) > 1:
                out.add(name)
    return out


def g_relations_computed(files):
    """ОТНОШЕНИЕ, НАПЕЧАТАННОЕ СЛОВОМ, СХОДИТСЯ С ЧИСЛАМИ РЯДОМ С НИМ.

    ЧТО ЭТО ЗА СЕМЕЙСТВО. Прошлая волна подставила величины и оставила слова,
    которые их СРАВНИВАЮТ. «Runs at %s, roughly double the nominal of the
    alkaline and silver classes» печаталось на 33 страницах: напряжение
    подставлялось, отношение было набрано, и 17 страниц печатали 1,5 В, то
    есть СТОЛЬКО ЖЕ, а не вдвое; на одной из них Alkaline назывался тем же
    абзацем строкой выше. «The cells that get confused with %s are the ones
    a digit away» стояло на 122 страницах при 314 названных соседях, из
    которых на один знак отличаются 20 — и та же фраза была признана неверной
    и убрана ИЗ ЗАГОЛОВКА, а в лиде строкой ниже пережила правку дословно.
    «Which the standard writes into the code» печаталось на тех же 314
    позициях и было верно на 30. «Every one of them either rattles or refuses
    to let the cover close» — дизъюнкция над набором, которого никто не мерил:
    на странице, где оба названных элемента ВЫШЕ, ни один не болтается.

    ЧТО ЧИТАЕТСЯ. Отданные страницы, а не исходник: величины, стоящие рядом
    со словом, читаются из той же разметки, которую видит читатель, и
    пересчитываются здесь заново. Проверок четыре, и каждая обязана найти
    хоть один образец: пустая выборка кричит, слепая молчит.

      1. КРАТНОСТЬ ПРОТИВ НАПРЯЖЕНИЙ. Слово отношения в заметке о литии
         сверяется с напечатанным номиналом и с номиналами щелочного и
         серебряного классов, посчитанными ЗДЕСЬ по снимку.
      2. ЧТО КОД ПИШЕТ О ГЛУБИНЕ. Строка, обещающая, что стандарт пишет
         разницу в оба обозначения, обязана называть два кода, у которых
         размер и правда закодирован; строка, отрицающая это, — обязана не
         называть таких.
      3. ДИЗЪЮНКЦИЯ. «Either A or B» и «every one of them» о наборе: обе
         половины обязаны в наборе быть, иначе набор описан неверно.
      4. ПОЛНОТА ПЕРЕЧНЯ. Срез без счёта — утверждение «здесь все»: витрина
         главной теряла R6, обычную угольно-цинковую AA, и та же страница
         двумя разделами ниже печатала все шесть.
    """
    import prose as pr
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "отданных страниц")
    base = _rel_alkaline_silver()
    if len(base) != 2:
        return bad + ["номиналы щелочного и серебряного классов по снимку не "
                      "посчитались (%s) — сверять отношение не с чем" % base]

    # 1. Кратность против напечатанного напряжения.
    seen1 = 0
    pat = re.compile(r"runs at ([0-9.]+) V, ([a-z ]+?) the nominal of "
                     r"the alkaline and silver classes")
    same = re.compile(r"runs at ([0-9.]+) V, the same nominal the alkaline "
                      r"and silver classes carry")
    for p, t in sorted(pages.items()):
        vis = _text(t)
        for m in same.finditer(vis):
            seen1 += 1
            v = float(m.group(1))
            for kind, b in sorted(base.items()):
                if not 0.95 <= v / b <= 1.05:
                    bad.append("%s: «the same nominal» при %s V против %s V "
                               "у класса %s" % (p, m.group(1), b, kind))
        for m in pat.finditer(vis):
            seen1 += 1
            v, word = float(m.group(1)), m.group(2).strip()
            for kind, b in sorted(base.items()):
                r = v / b
                n = int(round(r))
                want = RATIO_WORD_FOR.get(n)
                if not (n >= 2 and abs(r - n) <= 0.08 * n and want
                        and want in word):
                    bad.append("%s: «%s» при %s V против %s V у класса %s — "
                               "отношение %.2f" % (p, word, m.group(1), b,
                                                   kind, r))
    if not seen1:
        bad.append("ни одной заметки об отношении напряжений на отданных "
                   "страницах — проверять кратность не на чем")

    # 2. Что обозначения говорят о разнице глубин. Считается ПО СНИМКУ и
    # своим разбором кода: эталон, взятый у проверяемого, соглашается сам с
    # собой, и cells.code_check здесь звать нельзя.
    seen2 = 0
    codes = _rel_code_holds_height()
    item = re.compile(r"<li><b>([A-Z0-9./-]+)[^<]*</b> &mdash; same diameter,"
                      r".*?, (which the standard writes into both codes|"
                      r"which neither designation carries|"
                      r"which the codes disagree with the published sheet "
                      r"about)\.</li>", re.S)
    for p, t in sorted(pages.items()):
        me = re.search(r'<meta name="page-type" content="cell">', t)
        if not me:
            continue
        own = p.split("/")[0].upper()
        for m in item.finditer(t):
            seen2 += 1
            other, verdict = m.group(1).upper(), m.group(2)
            both = codes.get(own, False) and codes.get(other, False)
            if verdict.startswith("which the standard") and not both:
                bad.append("%s: про %s сказано, что разницу пишет стандарт, "
                           "а размер закодирован не у обоих" % (p, other))
            if verdict.startswith("which neither") and both:
                bad.append("%s: про %s сказано, что обозначения разницы не "
                           "несут, а закодирована она у обоих" % (p, other))
    if not seen2:
        bad.append("ни одной строки о соседе по глубине — проверять, что "
                   "говорит код, не на чем")

    # 3. Дизъюнкция над набором: обе половины обязаны в нём быть.
    seen3 = 0
    dis = re.compile(r"(\d+) cells (?:stand ([0-9.]+) mm tall|run from "
                     r"([0-9.]+) to ([0-9.]+) mm tall) against this one's "
                     r"([0-9.]+) mm, so ([^.]+)\.")
    for p, t in sorted(pages.items()):
        for m in dis.finditer(_text(t)):
            seen3 += 1
            lo = float(m.group(2) or m.group(3))
            hi = float(m.group(2) or m.group(4))
            here, tail = float(m.group(5)), m.group(6)
            has_short, has_tall = lo < here, hi > here
            if "and none of them is loose" in tail and has_short:
                bad.append("%s: сказано, что ни один не болтается, а %s мм "
                           "мельче %s" % (p, m.group(3) or m.group(2), here))
            if "and none of them is too tall" in tail and has_tall:
                bad.append("%s: сказано, что ни один не высок, а %s мм "
                           "выше %s" % (p, m.group(4) or m.group(2), here))
            if "stand off the contact and" in tail \
                    and not (has_short and has_tall):
                bad.append("%s: обе половины дизъюнкции обещаны, а набор "
                           "лежит по одну сторону от %s мм" % (p, here))
    if not seen3:
        bad.append("ни одной дизъюнкции о наборе соседей — проверять её "
                   "половины не на чем")

    # 4. ПОЛНОТА ПЕРЕЧНЯ. Срез без счёта — это утверждение «здесь все»:
    # витрина главной брала первые пять имён и молчала об остальных, и R6,
    # обычная угольно-цинковая AA, пропадала из «оболочек, с которыми
    # приходят», тогда как таблица оболочек двумя разделами ниже считала её
    # шестой. Сверяются ДВЕ СТРАНИЦЫ друг с другом.
    seen4 = 0
    home = pages.get("index.html", "")
    block = re.search(r"<h2>The envelopes people arrive with</h2>.*?</ul>",
                      home, re.S)
    shells = dict((lb, int(n)) for lb, n in re.findall(
        r"<tr><th><a[^>]*>([^<]+)</a></th><td>(\d+)</td>",
        pages.get("shells/index.html", "")))
    if not shells:
        bad.append("таблицы оболочек нет — сверять полноту витрины не с чем")
    for li in re.findall(r"<li>(.*?)</li>", block.group(0) if block else "",
                         re.S):
        seen4 += 1
        lab = re.search(r'^(?:<a[^>]*>)?([^<]+)', li)
        span = re.search(r'<span class="bx-res-what">(.*?)&mdash;', li, re.S)
        txt = span.group(1) if span else ""
        more = re.search(r"and (\d+) more", txt)
        if more:
            txt = txt[:more.start()]
        listed = len([x for x in re.split(r",\s*|\s+and\s+", txt.strip()) if x])
        listed += int(more.group(1)) if more else 0
        want = shells.get(lab.group(1).strip()) if lab else None
        if want is None:
            bad.append("витрина главной называет оболочку, которой нет в "
                       "таблице оболочек: %s" % _text(li)[:40])
        elif listed != want:
            bad.append("витрина главной перечисляет %d обозначений оболочки "
                       "%s, а в таблице их %d: срез без счёта — это "
                       "утверждение «здесь все»"
                       % (listed, lab.group(1).strip(), want))
    if seen4 < 1:
        bad.append("витрины оболочек на главной нет — проверять полноту "
                   "перечня не на чем")
    _sample(bad, seen1 + seen2 + seen3 + seen4, "проверенных отношений")
    return bad[:12]


def g_declared_sets_match_pages(files):
    """ОБЪЯВЛЕННЫЙ НАБОР СОВПАДАЕТ С ТЕМ, ЧТО НАПЕЧАТАНО.

    Утверждение о полноте печатается только из ПОСЧИТАННОЙ величины, а
    посчитать её можно лишь из объявленного набора. Здесь сходятся четыре
    набора, каждый из которых до этой волны существовал в двух копиях —
    объявленной и набранной словом:

      · C.FACT_KINDS против того, что facts() выдаёт на корпусе: «every page
        adds five things that are calculated» стояло рядом со списком из
        СЕМИ видов, и число словом не сверял никто;
      · C.DATA_FILES против того, что сборка и правда открывает: «there is
        no third source» стояло ПОД списком, пронумерованным до четырёх;
      · render.ANSWER_COLUMNS против заголовков отданных таблиц: «three
        questions in three separate columns» не сверялось ни с одной;
      · P.CANNOT_SEE против напечатанного числа слепых пятен.

    И пятое, у которого гейта не было вовсе: cells.size_spread. Спор записей
    о размере обязан быть НАПЕЧАТАН на странице элемента — у /sr60/ записи
    публиковали и 2,1, и 2,2 мм, страница печатала 2,2 как решённое, и ни
    один из 88 гейтов этого не читал.
    """
    import prose as pr
    import render as rd
    import cells as c2
    bad = []
    pages = _html(files)
    _sample(bad, len(pages), "отданных страниц")

    # Виды вычисленного читаются ИЗ ИСХОДНИКА facts(), а не из её вывода на
    # корпусе: гейт, спросивший ту же функцию, согласился бы с ней при любом
    # новом виде, дописанном мимо объявления.
    kinds = _declared_fact_prefixes()
    _sample(bad, len(kinds), "видов вычисленного в исходнике facts()")
    declared = {k for k, _d in c2.FACT_KINDS}
    for k in sorted(kinds - declared):
        bad.append("facts() выдаёт вид «%s», а в FACT_KINDS его нет: число "
                   "видов на странице метода было бы меньше правды" % k)
    for k in sorted(declared - kinds):
        bad.append("в FACT_KINDS объявлен вид «%s», которого facts() не "
                   "выдаёт ни разу" % k)
    meth = pages.get("method/index.html", "")
    front = _text(pages.get("index.html", ""))
    m = re.search(r"adds (\d+) kinds of value that are calculated", front)
    if not m:
        bad.append("главная не называет числа вычисляемых видов")
    elif int(m.group(1)) != len(c2.FACT_KINDS):
        bad.append("главная обещает %s видов вычисленного, объявлено %d"
                   % (m.group(1), len(c2.FACT_KINDS)))
    for _k, d in c2.FACT_KINDS:
        if d not in front:
            bad.append("вид «%s» объявлен, а на главной его нет" % d)

    for path in c2.DATA_FILES:
        if not os.path.isfile(path):
            bad.append("объявленного файла данных нет на диске: %s" % path)
    m = re.search(r"The build opens (\d+) data files?", meth)
    if not m:
        bad.append("страница метода не называет числа открываемых файлов")
    elif int(m.group(1)) != len(c2.DATA_FILES):
        bad.append("метод обещает %s файлов данных, объявлено %d"
                   % (m.group(1), len(c2.DATA_FILES)))

    home = pages.get("index.html", "")
    m = re.search(r"answers (\d+) questions in (\d+) separate columns", home)
    if not m:
        bad.append("главная не называет числа колонок ответа")
    else:
        for g in (1, 2):
            if int(m.group(g)) != len(rd.ANSWER_COLUMNS):
                bad.append("главная называет %s колонок, объявлено %d"
                           % (m.group(g), len(rd.ANSWER_COLUMNS)))
    heads = 0
    want = list(rd.ANSWER_COLUMNS)
    for p, t in sorted(pages.items()):
        for m2 in re.finditer(r"<thead><tr>((?:<th>[^<]*</th>)+)</tr></thead>",
                              t):
            hs = re.findall(r"<th>([^<]*)</th>", m2.group(1))
            if hs[1:1 + len(want)] == want:
                heads += 1
    if not heads:
        bad.append("ни одной таблицы с колонками %s — объявленные колонки "
                   "нигде не напечатаны" % want)

    seen = 0
    for p, t in sorted(pages.items()):
        for m3 in re.finditer(r"(\d+) things this site cannot see\. (.*?)"
                              r"Rechargeable cells", _text(t), re.S):
            seen += 1
            if int(m3.group(1)) != len(pr.CANNOT_SEE):
                bad.append("%s: обещано %s слепых пятен, объявлено %d"
                           % (p, m3.group(1), len(pr.CANNOT_SEE)))
            for one in pr.CANNOT_SEE:
                if _text(one) not in m3.group(2):
                    bad.append("%s: слепое пятно «%s» объявлено, а на "
                               "странице его нет" % (p, one[:40]))
    if not seen:
        bad.append("оговорки о слепых пятнах нет ни на одной странице")

    # cells.size_spread: спор записей о размере обязан быть НАПЕЧАТАН, и
    # спор этот считается по СНИМКУ. У самой size_spread не было ни одного
    # гейта — ноль упоминаний в этом файле, — а /sr60/ печатала 2,2 мм как
    # решённое там, где записи публикуют и 2,1, и 2,2.
    disputes = _rel_size_disputes()
    said = {p.split("/")[0].upper() for p, t2 in pages.items()
            if "do not all publish the same outside size" in t2}
    have = {p.split("/")[0].upper() for p in pages
            if p.endswith("/index.html") and p.count("/") == 1}
    for name in sorted(disputes & have):
        if name not in said:
            bad.append("%s: записи снимка публикуют разные габариты, а "
                       "страница молчит об этом" % name)
    if not disputes:
        bad.append("в снимке не нашлось ни одного спора о размере — "
                   "проверять его печать не на чем")
    _sample(bad, len(disputes), "обозначений со спором записей о размере")
    return bad[:12]


def _declared_fact_prefixes():
    """Виды вычисленного, ВЫПИСАННЫЕ ИЗ ИСХОДНИКА cells.facts(): каждая
    строка out.append("вид:...") даёт свой префикс."""
    src = _sources().get("cells.py")
    if src is None:
        return set()
    tree = ast.parse(src)
    out = set()
    for n in ast.walk(tree):
        if not (isinstance(n, ast.FunctionDef) and n.name == "facts"):
            continue
        for s in ast.walk(n):
            if not (isinstance(s, ast.Constant)
                    and isinstance(s.value, str)):
                # Не строка — не шаблон вида: НАЗВАННАЯ тихая ветка.
                continue
            m = re.match(r"^([a-z]+):%", s.value)
            if m:
                out.add(m.group(1))
    return out


def g_reader_rules(files):
    """Четыре правила облика, которые владелец назвал сам, — и которые
    молча отменить нельзя.

    Все четыре он нашёл за минуту, глядя на сайт, а весь сентябрьский аудит
    их не увидел: проверки читали разметку, а не страницу. Поэтому они
    здесь — чтобы следующая переверстка не вернула их тихо.

    Про ширину прозы отдельно. Это ЧЕТВЁРТЫЙ раз, когда он просит текст во
    всю ширину; трижды до того правка делалась «по признаку» — чинилось
    место, на которое показали. Гейт проверяет не место, а отсутствие самой
    возможности: переменной --measure в стилях быть не должно.
    """
    if not files:
        return ["страниц ноль — пустая выборка это провал"]
    bad = []
    for path, html in files.items():
        if "--measure" in html:
            bad.append("%s: вернулось сужение прозы (--measure)" % path)
        # Смотрим В САМО ПРАВИЛО, а не по всей странице: position:sticky есть
        # и у рекламной колонки, и проверка «есть ли слово на странице»
        # проходила чужим совпадением, когда шапку раскрепляли.
        m = re.search(r"\.bx-mast\{([^}]*)\}", html)
        if m and "position:sticky" not in m.group(1):
            bad.append("%s: шапка перестала закрепляться" % path)
        if "background-attachment:local,local,scroll,scroll" in html:
            bad.append("%s: вернулись полосы у краёв таблиц" % path)
        if "&copy; %d BiLingoPlus" % 2026 in html or "© 2026 BiLingoPlus" in html:
            bad.append("%s: юрлицо вернулось в подвал" % path)
        if bad:
            break
    return bad


GATES = [
    ("язык страницы английский", g_language),
    ("нет управляющих байтов", g_control_chars),
    ("нет двойного экранирования", g_no_double_escape),
    ("браузер не ходит наружу", g_no_external),
    ("скрипт один, встроенный, короткий", g_no_scripts),
    ("скрипт не строит разметку", g_script_builds_no_markup),
    ("голова страницы заполнена верно", g_head),
    ("внутренние ссылки ведут на существующее", g_internal_links),
    ("нет страниц-сирот", g_orphans),
    ("карта сайта совпадает с сайтом", g_sitemap),
    ("robots указывает карту", g_robots),
    ("политика совпадает с разметкой", g_privacy_matches_markup),
    ("ответ первым в каждом разделе", g_answer_first),
    ("нет близнецов по прозе", g_twins),
    ("чертёж не врёт масштабом", g_scale_honest),
    ("посадка и электрика раздельно", g_fit_and_volts_separate),
    ("оговорки безопасности на месте", g_safety_notice),
    ("нет пустых рекламных мест", g_no_empty_ad_slot),
    ("объявленные классы применяются", g_css_classes_used),
    ("применённые классы объявлены", g_css_classes_declared),
    ("выкладка совпадает с генератором", g_dist_matches_build),
    ("химия не спорит с обозначением", g_chemistry_matches_code),
    ("рекламные места точного размера", g_ad_slots_exact),
    ("чертёж не ужимается по ширине", g_drawing_never_shrinks),
    ("ссылки ведут на страницу, а не в указатель", g_links_point_at_pages),
    ("числа в прозе совпадают с сайтом", g_numbers_agree),
    ("нет ссылок на самих себя", g_no_self_links),
    ("поиск ведёт на существующее", g_search_index_resolves),
    ("поиск на каждой странице", g_lookup_on_every_page),
    ("поиск отвечает на набранное", g_lookup_answers_known_strings),
    ("в указателе нет тупиков", g_index_has_no_dead_ends),
    ("обещанное про поиск выполняется", g_lookup_promises_hold),
    ("адрес оболочки называет её форму", g_shell_slug_form),
    ("сказано, для скольких замены нет", g_no_candidate_count),
    ("число согласовано с глаголом", g_number_agrees_with_verb),
    ("артикль согласован со звуком", g_article_agrees),
    ("снятый не говорит о себе в настоящем", g_gone_not_present_tense),
    ("названия химий целые", g_chemistry_names_whole),
    ("в ячейках нет заглушек", g_no_placeholder_values),
    ("вытисненное прослеживается до снимка", g_stamped_codes_in_source),
    ("полная форма МЭК из известных ответов", g_iec_long_form_known),
    ("ключи указателя уникальны и посчитаны", g_index_keys_unique),
    ("утверждение о полноте посчитано", g_completeness_claim_counted),
    ("числа в заметках о химии из записей", g_chem_note_volts_from_page),
    ("утверждения ограничены данными", g_claims_scoped_to_data),
    ("напряжение считается двумя функциями",
     g_volt_functions_known_answers),
    ("метка совпадает с напечатанным процентом", g_volt_tag_matches_pct),
    ("шкала кодирует отклонение", g_scale_encodes_ratio),
    ("вердикт посадки в прозе несёт напряжение",
     g_fit_claim_carries_voltage),
    ("инвентарь заводится по содержимому", g_ad_inventory_by_content),
    ("объявление ниже ответа", g_ad_below_the_answer),
    ("публичный адрес на своём домене", g_public_contact_own_domain),
    ("карточка ссылки совпадает с головой", g_share_cards),
    ("структурные данные совпадают с видимым", g_structured_data_real),
    ("описания различаются своими величинами", g_descriptions_differ),
    ("пол объёма держится", g_word_floor),
    ("гейт близнецов читает весь текст", g_twin_scope_is_whole_text),
    ("опасные применения названы", g_hazard_named_where_it_bites),
    ("источники пронумерованы и настоящие", g_sources_numbered_and_real),
    ("печать не режет таблицу и чертёж", g_print_stylesheet),
    ("институциональная оболочка на месте", g_institutional_shell),
    ("набор данных опубликован и сходится", g_dataset_published),
    ("виджеты остаются фрагментами", g_embeds_are_fragments),
    # Художественная волна: цвет, кегль, ритм и порядок на экране.
    ("цвета парны и объявлены на голом :root", g_colour_tokens_paired),
    ("контраст пар держится", g_contrast_pairs_hold),
    ("один сигнал — одна работа", g_one_signal_one_job),
    ("кегль из одной шкалы", g_type_scale_is_one),
    ("отступы из одного шага", g_spacing_from_one_unit),
    ("формат места влезает в колонку", g_ad_format_fits_column),
    ("ответ выше справочных величин", g_answer_above_reference),
    # Волна аудита: область гейта, эталон гейта и кодирование картинкой.
    ("пустая выборка роняет каждый гейт", g_empty_sample_is_a_failure),
    ("поиск находит каждую опубликованную страницу",
     g_lookup_finds_every_page),
    ("геометрия меняется вместе с величиной", g_graphic_geometry_varies),
    ("арифметика раскладки из известных ответов",
     g_layout_arithmetic_known_answers),
    ("класс в подводке следует из отношения", g_lead_class_follows_ratio),
    ("счётные утверждения посчитаны", g_cross_page_counts_agree),
    # Волна взаимности: одна пара — один вердикт, проза против своей же
    # таблицы, виджет со своими оговорками и ширина на самом узком экране.
    ("взаимный вердикт совпадает у обеих страниц",
     g_reciprocal_verdicts_agree),
    ("процент в прозе совпадает с таблицей страницы",
     g_prose_ratio_matches_table),
    ("виджет несёт оговорки вместе с вердиктом",
     g_embed_verdict_carries_limits),
    ("узкая колонка держит длинное слово", g_narrow_column_holds_text),
    # Волна эталона: откуда гейт берёт ожидаемое и чем это доказано.
    ("текстовые функции из известных ответов",
     g_text_functions_known_answers),
    ("эталон не берётся у проверяемого",
     g_reference_is_not_the_code_under_test),
    # Волна учёта: чем доказано, что проверок ровно столько, сколько видно.
    ("величина генератора объявлена эталоном",
     g_reference_constants_declared),
    ("учёт гейтов и проб полон", g_gate_registry_is_complete),
    ("у тихой ветки есть имя", g_silent_skips_are_named),
    # Волна предмета: вся строка таблицы пары про один предмет, и
    # предмет этот назван, а не подразумевается порядком аргументов.
    ("строка таблицы пары про один предмет", g_pair_row_one_subject),
    # Волна учёта, вторая половина: счёт самого набора — тоже
    # величина, и пересчитывать её обязан гейт, а не читатель README.
    ("README считает гейты по факту", g_readme_counts_the_gates),
    # Волна счёта: физическая величина, набранная руками в шаблоне прозы
    # рядом с посчитанными числами, которым она противоречит. По собранному
    # такое не отличить от исправного — читается ИСХОДНИК.
    ("величина в прозе посчитана или объявлена",
     g_prose_quantities_declared),
    ("отношение посчитано по числам рядом",
     g_relations_computed),
    ("объявленный набор совпадает с напечатанным",
     g_declared_sets_match_pages),
    ("правила облика, названные владельцем, держатся", g_reader_rules),
    ("поиск отвечает по габариту", g_search_answers_by_size),
    ("раскрытие переживает подключение сети",
     g_ad_disclosure_survives_the_network),
]

GATE_COUNT = 93          # гейт, переставший запускаться, выглядит пройденным


def run(files, quiet=False):
    assert len(GATES) == GATE_COUNT, \
        "гейтов %d, объявлено %d" % (len(GATES), GATE_COUNT)
    failed = 0
    for name, fn in GATES:
        problems = fn(files)
        if problems:
            failed += 1
            if not quiet:
                print("  ПРОВАЛ  %s" % name)
                for x in problems[:5]:
                    print("          %s" % x)
                if len(problems) > 5:
                    print("          ... и ещё %d" % (len(problems) - 5))
        elif not quiet:
            print("  пройден %s" % name)
    return failed


# --------------------------------------------------------------- отпечаток

def content_hash(files, content_date):
    body = "".join(x for p, x in sorted(files.items())
                   if not p.endswith(("sitemap.xml", "robots.txt")))
    body = body.replace(content_date.isoformat(), "")
    body = body.replace(content_date.strftime("%d %B %Y"), "")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def stamp_verdict(new_hash, content_date, old, today=None):
    """ЧИСТАЯ функция, чтобы её можно было проверить известными ответами.

    Дата содержимого — обещание «в этот день сайт менялся последний раз»; она
    уходит в lastmod карты. Обещание ложно только тогда, когда содержимое
    поменялось ПОЗЖЕ названного дня. Правка в тот же день, который дата и
    называет, ничего не устаревает: сверяем с ЧАСАМИ, а не с самим вводом.
    """
    if not old or old["hash"] == new_hash:
        return None
    if old["date"] != content_date.isoformat():
        return None
    if today is not None and content_date >= today:
        return None
    return ("содержимое изменилось, а CONTENT_DATE осталась %s — "
            "сдвиньте её в render.py" % content_date.isoformat())


def stamp(files, content_date, path=None, today=None):
    """Сверить отпечаток содержимого и, ТОЛЬКО НА ЧИСТОМ ПРОГОНЕ, сдвинуть.

    Эталон переписывался ВСЕГДА — в том числе на том самом прогоне, который
    жаловался. Беда оставалась на месте, а вторая проверка её уже не видела:
    один прогон краснел, второй печатал «пройден» над тем же дефектом.
    Проверка, которая не может провалиться дважды, — не проверка.

    Возвращается пара: жалоба (или None) и ПРИЧИНА, по которой сверка не
    выполнялась вовсе. Вторую печатать «пройдено» нельзя — это ровно тот
    зелёный вердикт над пустой выборкой, из-за которого у этого сайта
    двадцать пять гейтов ничего не проверяли.
    """
    h = content_hash(files, content_date)
    if path is None:
        if not os.path.isdir(STAMP_DIR):
            os.makedirs(STAMP_DIR)
        path = os.path.join(STAMP_DIR, "batterycross.json")
    old = json.load(io.open(path, encoding="utf-8")) \
        if os.path.isfile(path) else None
    if today is None:
        today = _date.today()
    verdict = stamp_verdict(h, content_date, old, today)
    if verdict is None:
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            json.dumps({"hash": h, "date": content_date.isoformat()},
                       indent=1))
    if old is None:
        return verdict, "эталона на диске не было — сверять было не с чем"
    if content_date >= today:
        return verdict, ("CONTENT_DATE это сегодняшний день: правка в тот "
                         "день, который дата и называет, ничего не устаревает")
    return verdict, None


def _dead_end_to_index(c):
    t = c["index.html"]
    m = re.search(r'"/discontinued/#d-([a-z0-9]+)"', t)
    assert m, "в указателе нет ни одного якоря витрины снятых"
    c["index.html"] = t.replace(m.group(0), '"/codes/#c-%s"' % m.group(1), 1)


def stamp_selftest():
    from datetime import date as _d
    day = _d(2026, 9, 1)
    now = _d(2026, 9, 5)
    old = {"hash": "aaaa", "date": "2026-09-01"}
    cases = [("текст изменился, дата стоит", "bbbb", day, old, now, True),
             ("ничего не изменилось", "aaaa", day, old, now, False),
             ("текст изменился и дата сдвинута", "bbbb", _d(2026, 9, 2), old,
              now, False),
             ("эталона ещё нет", "bbbb", day, None, now, False),
             ("правка в тот же день, который названа датой", "bbbb", day, old,
              day, False),
             ("дата в будущем", "bbbb", _d(2026, 9, 9),
              {"hash": "aaaa", "date": "2026-09-09"}, now, False)]
    ok = True
    for name, h, d, o, n, want in cases:
        if (stamp_verdict(h, d, o, n) is not None) != want:
            print("  ОТПЕЧАТОК ОШИБСЯ  %s" % name)
            ok = False
        else:
            print("  верно             отпечаток: %s" % name)

    # КРУГОВОЙ ПРОГОН ПО ДИСКУ. Чистая функция была верна и раньше — врала
    # ОБВЯЗКА: эталон переписывался и на жалующемся прогоне, поэтому дефект
    # виден был ровно один раз. Здесь проверяется именно повтор.
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "stamp.json")
        one, two = {"a.html": "one"}, {"a.html": "two"}
        first, why = stamp(one, day, path, now)
        if first is not None or not why:
            print("  ОТПЕЧАТОК ОШИБСЯ  первый прогон обязан завести эталон "
                  "и сказать, что сверять было не с чем")
            ok = False
        else:
            print("  верно             отпечаток: первый прогон заводит "
                  "эталон и не притворяется проверкой")
        said = [stamp(two, day, path, now)[0] for _ in range(3)]
        if not all(said):
            print("  ОТПЕЧАТОК ОШИБСЯ  жалоба гаснет на повторе: %s"
                  % [x is not None for x in said])
            ok = False
        else:
            print("  верно             отпечаток: жалоба держится на "
                  "повторе, эталон на ней не сдвигается")
        moved = stamp(two, _d(2026, 9, 2), path, now)
        if moved[0] is not None:
            print("  ОТПЕЧАТОК ОШИБСЯ  сдвинутая дата не принимается")
            ok = False
        elif stamp(two, _d(2026, 9, 2), path, now)[0] is not None:
            print("  ОТПЕЧАТОК ОШИБСЯ  чистый прогон не сдвинул эталон")
            ok = False
        else:
            print("  верно             отпечаток: чистый прогон сдвигает "
                  "эталон")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


# ------------------------------------------------------------ самопроверка

_SAVED = {}


def _ship_css(c, old, new):
    """Довести подмену стиля ДО ОТДАННЫХ БАЙТОВ.

    Гейты облика читают таблицу так, как её получает браузер, а не текст
    модуля. Поломка, оставшаяся в модуле, до них бы не доехала — и молча
    перестала бы что-либо доказывать, ровно как «шкала кодирует отклонение»
    перестала быть доказанной, когда штрих уехал с 55,0 на 54,0.
    """
    hit = 0
    for k, v in list(c.items()):
        if k.endswith(".html") and old in v:
            c[k] = v.replace(old, new)
            hit += 1
    assert hit, "поломка мимо отданных байтов: %r" % old[:40]
    _sheets_forget()


def _break_ad_css(c):
    """Подменить размер места и в модуле, и в отданных байтах."""
    import design
    _SAVED["ad"] = design.AD_CSS
    design.AD_CSS = design.AD_CSS.replace("width:300px;height:600px",
                                          "width:256px;height:600px")
    _ship_css(c, "width:300px;height:600px", "width:256px;height:600px")


def _break_article_rule(c):
    """Сломать САМО ПРАВИЛО, а не страницу: гейт обязан покраснеть и на этом,
    иначе он всего лишь сверяет вывод функции с ней же."""
    import prose
    _SAVED["article"] = prose.article
    prose.article = lambda w, cap=False: ("An" if cap else "an")


def _break_draw_css(c):
    import design
    _SAVED["draw"] = design.CSS
    design.CSS = design.CSS.replace(".bx-draw{max-width:none",
                                    ".bx-draw{max-width:100%")
    _ship_css(c, ".bx-draw{max-width:none", ".bx-draw{max-width:100%")


def _break_iec_table(c):
    """Сломать САМУ таблицу полных форм: гейт обязан покраснеть на известных
    ответах, а не только на странице."""
    import cells
    _SAVED["iec"] = dict(cells.IEC_LONG_FORM)
    cells.IEC_LONG_FORM["LR54"] = "LR1131"


def _break_consequence_class(c):
    """Сломать САМУ функцию класса: гейт обязан покраснеть на известных
    ответах, а не только на странице, которую она породила."""
    import cells
    _SAVED["klass"] = cells.consequence_class
    cells.consequence_class = lambda ratio: (
        None if ratio is None else ("wrong" if abs(ratio) > 0.199 else "same"))


def _break_scale_position(c):
    """Сломать ГЕОМЕТРИЮ: вернуть шкалу к нормировке по краям набора, при
    которой 3% и 700% рисуются одинаково."""
    import cells
    _SAVED["pos"] = cells.scale_position
    cells.scale_position = lambda ratio: (
        None if ratio is None else (50.0 if not ratio
                                    else (100.0 if ratio > 0 else 0.0)))


def _break_source_bytes(c):
    """Управляющий байт в ИСХОДНИКЕ, а не в выкладке: именно оттуда он и
    приехал на сайт."""
    _SAVED["src"] = dict(_sources())
    _SRC["design.py"] = _SRC.get("design.py", "") + chr(0x82)


def _break_stamped(c):
    p = next(k for k, v in c.items()
             if k.endswith(".html") and '<p class="bx-also">Also stamped '
             in v)
    c[p] = c[p].replace('<p class="bx-also">Also stamped ',
                        '<p class="bx-also">Also stamped ZZ9999X, ', 1)


def _ad_page(c):
    """Страница с местом в потоке — берётся из самой сборки, а не набирается
    именем: имя устаревает молча."""
    return next(k for k, v in sorted(c.items())
                if k.endswith(".html") and "bx-ad bx-ad-flow" in v)


def _ld_page(c):
    return next(k for k, v in sorted(c.items())
                if k.endswith(".html") and '"@type":"Product"' in v)


# Место в том виде, в каком оно отдаётся СЕЙЧАС. Фикстура несла разметку
# заглушки — `bx-ad-lab` и `bx-ad-note`, — а этих классов в стилях больше
# нет: поломка краснела бы «использован необъявленный класс», то есть по
# другому правилу, чем задумано, и при этом выглядела бы сработавшей.
AD_SLOT_HTML = ('<div class="bx-ad bx-ad-flow"><a class="bx-house" href="/">'
                '<span class="bx-ad-cap">From BatteryCross</span>'
                '<span class="bx-house-h">x</span>'
                '<span class="bx-house-s">y</span></a></div>')


def _break_carries_ads(c):
    """Сломать САМО ПРАВИЛО, а не страницу: гейт обязан краснеть и на
    известных ответах, иначе он лишь сверяет вывод функции с ней же."""
    import render as rd
    _SAVED["ads"] = rd.carries_ads
    rd.carries_ads = lambda path, body: True


def _strip_ads(c):
    """Убрать инвентарь СО ВСЕХ страниц — ровно та сборка, которая уезжала
    при выключенном флаге и на которой оба рекламных гейта печатали
    «пройден»."""
    for k, v in list(c.items()):
        if k.endswith(".html"):
            c[k] = re.sub(r'<div class="bx-ad .*?</div>', "", v, flags=re.S)


def _ad_on_legal(c):
    """Объявление на юридической странице: прямой запрет правил сети, а
    аккаунт у нас один на все сайты фермы."""
    c["privacy/index.html"] = c["privacy/index.html"].replace(
        "</h1>", "</h1>" + AD_SLOT_HTML, 1)


def _pull_flow_slot(c, p):
    m = re.search(r'<div class="bx-ad bx-ad-flow">.*?</div>', c[p], re.S)
    return m.group(0)


def _ad_to_top(c):
    """Объявление первым экраном — то, ради чего человек НЕ приходил."""
    p = _ad_page(c)
    slot = _pull_flow_slot(c, p)
    c[p] = c[p].replace(slot, "", 1).replace(
        '<div class="bx-main">', '<div class="bx-main">' + slot, 1)


def _ad_to_bottom(c):
    """Объявление в самом хвосте колонки — ровно туда его дописывал запасной
    путь, когда метки в разметке не стояло: под блоком методики, где оно не
    стоит ничего."""
    p = _ad_page(c)
    slot = _pull_flow_slot(c, p)
    t = c[p].replace(slot, "", 1)
    i = t.index('</div><aside class="bx-side">')
    c[p] = t[:i] + slot + t[i:]


def _drop_flow_ad(c):
    p = _ad_page(c)
    c[p] = re.sub(r'<div class="bx-ad bx-ad-flow">.*?</div>', "", c[p],
                  count=1, flags=re.S)


def _ld_add_field(c):
    """Поле, которого у сайта нет: рейтинга никто не ставил."""
    p = _ld_page(c)
    c[p] = c[p].replace('{"@context":"https://schema.org","@type":"Product",',
                        '{"@context":"https://schema.org","@type":"Product",'
                        '"author":"staff",', 1)


def _ld_fake_value(c):
    """Величина, которой на странице глазами нет."""
    p = _ld_page(c)
    c[p] = re.sub(r'\{"@type":"PropertyValue","name":"[^"]*","value":"[^"]*"',
                  '{"@type":"PropertyValue","name":"Diameter",'
                  '"value":"98765"', c[p], count=1)


def _ld_break_json(c):
    p = _ld_page(c)
    c[p] = c[p].replace('"@type":"Product"', '"@type":"Product",,', 1)


def _ld_drop(c):
    p = _ld_page(c)
    c[p] = re.sub(r'<script type="application/ld\+json">.*?</script>', "",
                  c[p], count=1, flags=re.S)


def _ld_fake_crumb(c):
    p = _ld_page(c)
    c[p] = c[p].replace('"@type":"ListItem","position":1,"name":"Index"',
                        '"@type":"ListItem","position":1,"name":"Home"', 1)


def _desc_same(c):
    """Одно описание на десятках страниц — то, что стояло на 125."""
    pages = [k for k, v in sorted(c.items())
             if k.endswith(".html") and 'content="cell"' in v][:15]
    for k in pages:
        c[k] = re.sub(r'<meta name="description" content="[^"]*"',
                      '<meta name="description" content="A battery cell page '
                      'on BatteryCross with the figures behind it."', c[k])


def _desc_one_template(c):
    """Разные коды, ОДНА фраза: скелет описания повторяется, а различает их
    подстановка, а не расчёт."""
    for k, v in sorted(c.items()):
        if not (k.endswith(".html") and 'content="cell"' in v):
            continue
        code = re.search(r"<h1>([^<]*)</h1>", v).group(1)
        c[k] = re.sub(
            r'<meta name="description" content="[^"]*"',
            '<meta name="description" content="%s is no longer listed by '
            'Energizer. What still fits its compartment, what the voltage '
            'difference costs, and every published figure."' % code, v)



# --- поломки для правил объёма, источников, печати и виджетов ---------------

def _thin_page_stays_indexed(c):
    """Тонкая страница снова объявлена индексируемой. Ровно то состояние, в
    котором сайт уезжал: 164 страницы ниже пола и все в выдаче.

    СТРАНИЦА ВЫБИРАЕТСЯ ПО ВЕЛИЧИНЕ, А НЕ ПО АЛФАВИТУ. Прежняя версия брала
    первую попавшуюся страницу с noindex — и когда три элемента переросли
    пол, первой оказалась 404-я, которая ниже пола по построению и гейтом
    освобождена: поломка перестала срабатывать, а виноват был не гейт.
    """
    import render as rd
    for p, t in sorted(c.items()):
        if not p.endswith("index.html") or rd.NOINDEX_META not in t \
                or 'content="embed"' in t:
            continue
        if rd.page_words(t) >= rd.WORD_FLOOR:
            continue
        c[p] = t.replace(rd.NOINDEX_META, rd.INDEX_META, 1)
        return
    raise AssertionError("ниже пола нет ни одной страницы — ломать нечего")


def _floor_page_gutted(c):
    """Индексируемая страница ужата ниже пола: половина колонки вырезана."""
    import render as rd
    for p, t in sorted(c.items()):
        if not p.endswith("index.html") or rd.INDEX_META not in t:
            continue
        if rd.page_words(t) < rd.WORD_FLOOR * 1.2:
            continue
        col = rd.main_column(t)
        assert col, "основная колонка не нашлась"
        c[p] = t.replace(col, col[:len(col) // 6], 1)
        return
    raise AssertionError("нет страницы, которую можно ужать")


def _twin_scope_shrunk(c):
    """Сузить САМУ ОБЛАСТЬ гейта близнецов обратно к четверти текста.

    Это и есть поломка, которую надо ловить: корпус в порядке, а мерить его
    стали одним абзацем из четырёх. Гейт, который на это не краснеет, не
    доказывает ничего.
    """
    import render as rd
    _SAVED["own_prose"] = rd.own_prose

    def quarter(html):
        keep = []
        m = re.search(r'<p class="bx-lead">(.*?)</p>', html, re.S)
        if m:
            keep.append(re.sub(r"<[^>]+>", " ", m.group(1)))
        return " ".join(keep)

    rd.own_prose = quarter


def _twin_pages_made_alike(c):
    """Две страницы сделаны близнецами по ВСЕМУ тексту, а не по одному
    абзацу: старая область этого не видела."""
    ps = sorted(_cells(c))
    a, b = ps[0], ps[1]
    col_a = re.search(r'<div class="bx-main">(.*)', c[a], re.S).group(1)
    col_b = re.search(r'<div class="bx-main">(.*)', c[b], re.S).group(1)
    c[b] = c[b].replace(col_b, col_a, 1)


def _hazard_removed(c):
    """Дымовой извещатель вычеркнут с девятивольтовой страницы."""
    for p, t in sorted(c.items()):
        if "smoke alarm" in t:
            c[p] = t.replace("smoke alarm", "portable device")
            return
    raise AssertionError("на сайте нет ни одного упоминания извещателя")


def _ingest_note_removed(c):
    """Телефон вычёркивается на странице КНОПОЧНОГО ЭЛЕМЕНТА, а не на первой
    попавшейся: ломалка обязана ходить тем же признаком, что и гейт, иначе
    она доказывает красноту правила, которого больше нет."""
    import depth as D
    import render as rd
    for cell in rd.CELLS:
        if not D.hazard_kind(cell):
            continue
        key = rd.slug(cell) + "/index.html"
        if key in c and "1-800-222-1222" in c[key]:
            c[key] = c[key].replace("1-800-222-1222", "the number on the pack")
            return
    raise AssertionError("нет страницы диска с телефоном — ломать нечего")


def _break_reader_rule_measure(c):
    """Вернуть сужение прозы. Правило владельца — «такие текста давать на всю
    ширину страницы», и просил он его ЧЕТЫРЕЖДЫ; сам гейт был добавлен, а
    доказать, что он краснеет, забыли — то есть проверки четырёх правил,
    названных владельцем вслух, могло не быть вовсе."""
    for p, t in sorted(c.items()):
        if ".bx-lead{" in t:
            c[p] = t.replace(".bx-lead{", ".bx-lead{max-width:var(--measure);",
                             1)
            return
    raise AssertionError("в сборке нет правила .bx-lead — ломать нечего")


def _break_reader_rule_sticky(c):
    """Открепить шапку: второе из четырёх правил владельца."""
    for p, t in sorted(c.items()):
        if ".bx-mast{" in t and "position:sticky" in t:
            c[p] = t.replace("position:sticky;top:0", "position:static", 1)
            return
    raise AssertionError("липкой шапки в сборке нет — ломать нечего")


def _break_search_index_gone(c):
    """Указатель вырезан отовсюду. Гейт, у которого исчез источник, обязан
    покраснеть, а не отчитаться о нуле проверенных габаритов."""
    n = 0
    for p, t in list(c.items()):
        if 'id="bx-index"' in t:
            c[p] = re.sub(r'<script type="application/json" id="bx-index">'
                          r'.*?</script>', "", t, flags=re.S)
            n += 1
    if not n:
        raise AssertionError("указателя нет ни на одной странице — "
                             "ломать нечего")


def _break_search_name_like_size(c):
    """Обозначение, внутри которого стоит разделитель размера.

    Ровно этот класс дефекта и был внесён починкой размерного запроса:
    признак «две цифры и нет букв» уводил в размерный проход имена вида
    «3-0316», и 19 имён из 767 переставали находить сами себя. Ломалка
    добавляет в указатель имя «12 34» — поиск обязан продолжать находить
    его по имени, иначе починка одного запроса оплачена поломкой другого.
    """
    for p in sorted(c):
        m = re.search(r'(<script type="application/json" id="bx-index">)'
                      r'(.*?)(</script>)', c[p], re.S)
        if not m:
            continue
        J = json.loads(m.group(2))
        # Габарит строки НЕ совпадает с её именем — иначе ложь перестаёт
        # быть ложью: размерный проход нашёл бы «12 34» по её же габариту
        # 12x34, и гейт остался бы зелёным на сломанном поиске.
        J["r"] = J["r"] + ";12 34|0||0|5.1x5.1|1"
        c[p] = (c[p][:m.start(2)] + json.dumps(J, ensure_ascii=False)
                + c[p][m.end(2):])
        return
    raise AssertionError("указателя нет — ломать нечего")


def _source_record_invented(c):
    """Номер записи, которого в снимке нет."""
    cell = next(p for p, t in sorted(c.items())
                if 'class="bx-refs"' in t)
    c[cell] = re.sub(r"catalog record \d+", "catalog record 999999", c[cell],
                     count=1)


def _source_sheet_invented(c):
    cell = next(p for p, t in sorted(c.items()) if 'class="bx-refs"' in t)
    c[cell] = re.sub(r'href="https://data\.energizer\.com/pdfs/[^"]+"',
                     'href="https://data.energizer.com/pdfs/nosuch.pdf"',
                     c[cell], count=1)


def _source_list_dropped(c):
    cell = next(p for p, t in sorted(c.items()) if 'class="bx-refs"' in t)
    c[cell] = re.sub(r'<ol class="bx-refs">.*?</ol>', "", c[cell], count=1,
                     flags=re.S)


def _break_print_css(c):
    """Снять правила печати из таблицы стилей — и из модуля, и из отданного."""
    import design
    _SAVED["print"] = design.CSS
    design.CSS = design.CSS.replace(
        "@media print{", "@media screen and (min-width:99999px){", 1)
    _ship_css(c, "@media print{", "@media screen and (min-width:99999px){")


def _about_dropped(c):
    del c["about/index.html"]


def _about_unlinked(c):
    """About перестала быть в подвале: страница есть, дойти до неё нельзя."""
    for p, t in sorted(c.items()):
        if p.endswith(".html") and 'href="/about/"' in t:
            c[p] = t.replace('href="/about/"', 'href="/method/"')


def _dataset_dropped(c):
    import render as rd
    del c[rd.DATASET_LATEST.lstrip("/")]


def _dataset_diverges(c):
    """Датированный файл и latest разошлись — постоянная ссылка перестала
    указывать на то, что цитировали."""
    import render as rd
    key = rd.DATASET_LATEST.lstrip("/")
    lines = c[key].split(chr(10))
    head = lines[0].split(",")
    i = head.index("listed_by_energizer")
    cols = lines[1].split(",")
    assert cols[i] in ("yes", "no"), "в колонке статуса не то: %s" % cols[i]
    cols[i] = "no" if cols[i] == "yes" else "yes"
    lines[1] = ",".join(cols)
    c[key] = chr(10).join(lines)


def _dataset_volts_wrong(c):
    import render as rd
    dated = rd.DATASET_PATH.lstrip("/") % rd.DATA_SNAPSHOT.isoformat()
    lines = c[dated].split(chr(10))
    head = lines[0].split(",")
    i = head.index("volts")
    cols = lines[1].split(",")
    cols[i] = "99"
    lines[1] = ",".join(cols)
    c[dated] = chr(10).join(lines)
    c[rd.DATASET_LATEST.lstrip("/")] = c[dated]


def _embed_gets_a_script(c):
    p = next(iter(sorted(_embeds(c))))
    c[p] = c[p].replace("</body>", "<script>var x=1;</script></body>", 1)


def _embed_becomes_indexable(c):
    p = next(iter(sorted(_embeds(c))))
    c[p] = c[p].replace('content="noindex, follow"', 'content="index, follow"',
                        1)


def _embed_loses_backlink(c):
    p = next(iter(sorted(_embeds(c))))
    # Атрибуты у ссылки допустимы: после `target="_top"` прежний шаблон
    # перестал совпадать, поломка стала мимо цели, и гейт выглядел
    # проверенным, ничего не проверив.
    c[p] = re.sub(r'<a href="https://[^"]*"[^>]*>batterycross\.com</a>',
                  "batterycross.com", c[p], count=1)

def _css_swap(c, old, new, key="look"):
    """Подменить кусок ОБЩЕГО CSS на время одной проверки — В ОБОИХ МЕСТАХ.

    Гейты облика читают ОТДАННЫЕ байты: дефект живёт в тексте таблицы
    стилей и доезжает до каждой страницы одинаково, но доказывать надо на
    том, что получает браузер. Поэтому подмена идёт и в модуль, и в
    выкладку, и обе обязаны попасть в цель.
    """
    import design
    _SAVED.setdefault(key, design.CSS)
    assert old in design.CSS, "поломка мимо цели: %r нет в CSS" % old[:40]
    design.CSS = design.CSS.replace(old, new, 1)
    _ship_css(c, old, new)


def _break_colour_only_dark(c):
    """Цвет, названный ТОЛЬКО в тёмной теме, — ровно та форма, из-за которой
    у нас карточка осталась светлой внутри тёмной полосы при 1,07:1."""
    _css_swap(c, "    --metal:#6c757c;\n",
              "    --metal:#6c757c;--card:#2a3038;\n")


def _break_colour_alias(c):
    """Цвет через var() другого цвета: алиас вычисляется на :root и
    наследуется ЧИСЛОМ, поэтому смена темы на контейнере его не трогает."""
    _css_swap(c, "  --metal:#7c848b;", "  --metal:var(--sunk);")


def _break_colour_literal(c):
    """Литеральный цвет в правиле, а не в токене."""
    _css_swap(c, ".bx-card{border:var(--w2) solid var(--line-3);"
              "background:var(--panel);",
              ".bx-card{border:var(--w2) solid var(--line-3);"
              "background:#eeeeee;")


def _break_contrast_light(c):
    """Вернуть заливке силуэта прежнюю светлоту: 1,69:1 к панели при 3:1."""
    _css_swap(c, "  --metal:#7c848b;", "  --metal:#b9c1c7;")


def _break_contrast_dark(c):
    """Вернуть обводке чертежа прежний почти-чёрный: 1,04:1 к тёмной панели.

    Ломается ИМЕННО тёмная половина пары: светлая при этом остаётся верной,
    и в этом весь дефект — картинка значила разное в зависимости от
    настройки операционной системы.
    """
    _css_swap(c, "    --line-3:#e8ebed;", "    --line-3:#12171b;")


def _break_contrast_formula(c):
    """Сломать САМУ считалку контраста: гейт, у которого верны только
    данные, молчит одинаково при любой формуле."""
    _SAVED["contrast"] = globals()["contrast"]
    globals()["contrast"] = lambda a, b: 21.0


def _break_second_accent(c):
    """Вернуть светофор: второй акцент отменяет первый.

    Зелёный значил «встаёт» в одном столбце и «то же напряжение» в соседнем
    — два независимых вердикта на один цвет.
    """
    _css_swap(c, "  --signal:#a13600;",
              "  --signal:#a13600;\n  --ok:#1f4f2e;")


def _break_signal_job(c):
    """Добавить сигналу шестую работу: «вы здесь» в меню."""
    _css_swap(c, ".bx-here{color:var(--ink);font-weight:700}",
              ".bx-here{color:var(--ink);font-weight:700;"
              "border-bottom:var(--w2) solid var(--signal)}")


def _break_type_off_scale(c):
    """Кегль мимо шкалы: пятнадцатая ступень, набранная руками."""
    _css_swap(c, ".bx-cap{font:var(--t-micro)/1.4 var(--mono);",
              ".bx-cap{font:.5625rem/1.4 var(--mono);")


def _break_heading_smaller_than_body(c):
    """Заголовок раздела мельче текста, который он открывает."""
    _css_swap(c, "h2{font:700 var(--t-lead)/1.25 var(--mono);",
              "h2{font:700 var(--t-micro)/1.25 var(--mono);")


def _break_spacing_by_hand(c):
    """Отступ, набранный числом: их было девять штук рядом с объявленным
    шагом."""
    _css_swap(c, ".bx-cap{font:var(--t-micro)/1.4 var(--mono);",
              ".bx-cap{margin-left:3px;"
              "font:var(--t-micro)/1.4 var(--mono);")


def _break_spacing_fractional(c):
    """Дробный ритм: множитель .8 при шаге 7 давал 5,6 px."""
    _css_swap(c, "  --u:8px;", "  --u:7px;")


def _break_spacing_stale_exempt(c):
    """Разрешение, которым никто не пользуется: дыра, открытая
    заранее и незаметно."""
    _SAVED.setdefault("exempt", dict(SPACING_EXEMPT))
    SPACING_EXEMPT["37px"] = "ничей"


def _break_ad_breakpoint(c):
    """Вернуть перелом формата на 1084 px при колонке, дорастающей до 728 px
    только к 1092: ровно та полоса, в которой растяжка наезжала на башню на
    47 пикселей без всякой полосы прокрутки."""
    import design
    _SAVED.setdefault("ad", design.AD_CSS)
    design.AD_CSS = design.AD_CSS.replace("@media (min-width:1109px)",
                                          "@media (min-width:1092px)")


def _break_ad_no_format(c):
    """Снять узкий формат: на 320 px в колонку 304 px рисуется 336 px."""
    import design
    _SAVED.setdefault("ad", design.AD_CSS)
    design.AD_CSS = design.AD_CSS.replace(
        "@media (max-width:368px){.bx-ad-flow{width:300px;height:250px}}\n", "")


def _break_answer_below_strip(c):
    """Вернуть полосу характеристик выше таблицы замен: пока она стояла там,
    ответ уезжал на 912-й пиксель при экране 1024x800."""
    p = next(k for k, v in sorted(c.items())
             if k.endswith(".html") and 'id="fits"' in v)
    c[p] = c[p].replace("<h2>What fits",
                        '<div class="bx-strip"></div><h2>What fits', 1)


def _break_answer_below_aliases(c):
    """Вернуть строку чужих маркировок выше таблицы замен."""
    p = next(k for k, v in sorted(c.items())
             if k.endswith(".html") and 'id="fits"' in v)
    c[p] = c[p].replace("<h2>What fits",
                        '<p class="bx-also">Also stamped X</p><h2>What fits', 1)


def _break_answer_sample_empty(c):
    """Снять метку ответа со ВСЕХ страниц. Пустая выборка обязана краснеть:
    два рекламных гейта у нас печатали «пройден» над нулём страниц."""
    for k, v in list(c.items()):
        if k.endswith(".html"):
            c[k] = v.replace('id="fits"', 'id="not-fits"')


def _break_wc(c):
    """Сломать САМ счётчик слов. Пол объёма ставит он: «&mdash;» считалось
    словом «mdash» 125 раз на одной странице, и это не отчёт, а отбор."""
    import prose
    _SAVED["wc"] = prose.wc
    prose.wc = lambda text: 9999


def _break_page_words(c):
    """Завысить счёт страницы. Проверяющий завысил его втрое: двадцать
    страниц ниже пола уехали в карту сайта при семидесяти семи зелёных."""
    import render as rd
    _SAVED["pw"] = rd.page_words
    rd.page_words = lambda html: 29997


def _break_jaccard(c):
    """Сходство, всегда равное нулю: отбор перестаёт отсеивать близнецов, и
    оба гейта близнецов печатают его же ноль как свой ответ."""
    import render as rd
    _SAVED["jac"] = rd.jaccard
    rd.jaccard = lambda a, b: 0.0


def _break_shingles(c):
    """Пустая черепица: сравнивать становится нечего, и сходство выходит
    нулевым по другой причине, чем у сломанного Жаккара."""
    import render as rd
    _SAVED["shg"] = rd._shingles
    rd._shingles = lambda text, pattern: set()


def _break_shell_form(c):
    """Всё круглое снова зовётся монетой — та самая функция и тот самый
    адрес, который назван в оговорке гейта."""
    import cells
    _SAVED["form"] = cells.shell_form
    cells.shell_form = lambda s: "coin"


def _break_window_for(c):
    """Окно абзаца, в которое влезает что угодно: гейт «ответ первым»
    печатал «пройден» на любой прозе."""
    import render as rd
    _SAVED["win"] = rd.window_for
    rd.window_for = lambda h2: (0, 10 ** 6)


def _shell_head_swapped(c):
    """Цилиндр, выложенный по адресу монеты. Страницы берутся ИЗ СБОРКИ:
    набранный руками путь устаревает молча и роняет самопроверку KeyError
    вместо того, чтобы что-то доказать."""
    src = next(k for k in sorted(c) if k.startswith("shell/cylinder-")
               and k.endswith("index.html"))
    c["shell/coin-" + src.split("shell/cylinder-", 1)[1]] = c[src]


def _shell_head_unknown(c):
    src = next(k for k in sorted(c) if k.startswith("shell/coin-")
               and k.endswith("index.html"))
    c["shell/wedge-" + src.split("shell/coin-", 1)[1]] = c[src]


def _shell_dims_lie(c):
    """Габарит на странице разошёлся с адресом. Адрес виден человеку и уходит
    в выдачу; проверять его можно только НАПЕЧАТАННЫМ габаритом."""
    p = next(k for k in sorted(c) if k.startswith("shell/")
             and k.endswith("index.html"))
    c[p] = re.sub(r"<h1[^>]*>[^<]*</h1>", "<h1>99 x 99 mm</h1>", c[p],
                  count=1)


def _rule_outside_the_sheet(c):
    """Правило облика, приехавшее АТРИБУТОМ: мимо таблицы стилей и мимо
    области всех гейтов облика разом."""
    c["index.html"] = c["index.html"].replace(
        "<h1", '<h1 style="color:#ff0000"', 1)
    _sheets_forget()


def _second_style_element(c):
    """Второй элемент style: правило, которого в объявленной таблице нет
    вовсе, а браузер его применяет."""
    for k, v in list(c.items()):
        if k.endswith(".html"):
            c[k] = v.replace("</body>",
                             "<style>.bx-card{background:#eeeeee}</style>"
                             "</body>")
    _sheets_forget()


def _unwatch_a_function(c):
    """Снять функцию с наблюдения: гейты её зовут, подмены для неё нет —
    ровно то состояние, в котором были все семьдесят семь гейтов."""
    _SAVED.setdefault("stubs", dict(REFERENCE_STUBS))
    REFERENCE_STUBS.pop(("render", "page_words"))


def _watch_a_function_nobody_calls(c):
    """Обещание проверки, которой нет: подмена объявлена, а звать функцию
    некому. Описанный и несуществующий рычаг хуже отсутствующего."""
    _SAVED.setdefault("stubs", dict(REFERENCE_STUBS))
    REFERENCE_STUBS[("render", "robots")] = lambda: (lambda: "")


def _excuse_a_gate_that_does_not_call(c):
    """Освобождение, выданное гейту, который функцию не зовёт: запись,
    которая ничего не значит, но выглядит объяснением."""
    _SAVED.setdefault("excuse", dict(NOT_A_REFERENCE))
    NOT_A_REFERENCE[("g_language", "render", "page_words")] = "выдумка"


def _stale_excuse(c):
    """Освобождение, выданное гейту, который на подмене КРАСНЕЕТ: запись
    уверяет, что функция ему не эталон, а он ею и живёт."""
    _SAVED.setdefault("excuse", dict(NOT_A_REFERENCE))
    NOT_A_REFERENCE[("g_word_floor", "render", "page_words")] = "отговорка"


def _gate_that_cannot_fail(c):
    """Подменить гейт на такой, который эталонную функцию зовёт и НИКОГДА не
    жалуется. Это и есть та форма, ради которой мета-гейт написан: сайт при
    ней цел, гейт зелен, а проверки нет."""
    import render as rd

    def g_word_floor(files):        # имя обязано совпасть: по нему ищут
        rd.page_words(next(iter(files.values()), ""))
        return []

    i = next(k for k, item in enumerate(GATES)
             if item[0] == "пол объёма держится")
    _SAVED["gates_entry"] = (i, GATES[i])
    GATES[i] = (GATES[i][0], g_word_floor)


EXTRA_FITS_TABLE = ('<table class="bx-fits"><thead><tr>'
                    '<th>Other cell</th><th>Fit</th></tr></thead><tbody>'
                    '<tr><th>ZZ1</th><td>drop-in</td></tr></tbody></table>')


def _unnamed_silent_skip(c):
    """Снять имя с тихой ветки: пропуск, о котором никто не решал, — ровно
    тот, из-за которого проба осматривает меньше, чем отчитывается."""
    _SAVED["skips"] = set(SILENT_SKIPS)
    SILENT_SKIPS.remove(("g_twins", "not m"))


def _stale_silent_skip(c):
    """Объявить тихую ветку, которой в исходнике нет: запись, которая ничего
    не значит, но выглядит объяснением."""
    _SAVED["skips"] = set(SILENT_SKIPS)
    SILENT_SKIPS.add(("g_language", "выдумка"))


def _hazard_page_off_the_slug(c):
    """Страница элемента лежит по ДРУГОМУ адресу: запись перестаёт находить
    свою страницу, и самая дорогая проверка сайта молча её не осматривает —
    ровно то состояние, в котором 69 записей из 215 не осматривались."""
    p = sorted(_cells(c))[0]
    c[p[:-len("index.html")] + "x/index.html"] = c.pop(p)


def _headline_volts_drift(c):
    """Напечатанное напряжение уехало с девятивольтовой страницы: отбор по
    полю записи и отбор по НАПЕЧАТАННОМУ расходятся, и правило про дымовой
    извещатель проверялось бы по списку, которого на страницах нет."""
    import depth as D
    lo, hi = D.ALARM_VOLTS
    for p, t in sorted(_cells(c).items()):
        v = _own_volts(t)
        if v is not None and lo <= v <= hi:
            c[p] = re.sub(r'(<span class="bx-val">)[\d.]+',
                          lambda m: m.group(1) + "1.5", t, count=1)
            return
    raise AssertionError("в сборке нет ни одной девятивольтовой страницы")


def _extra_fits_table(c):
    """Третья таблица замен, шапки которой никто не объявлял: её строки не
    читает ни один гейт, а выглядит она такой же, как две проверяемые."""
    p = sorted(_cells(c))[0]
    c[p] = c[p].replace("</body>", EXTRA_FITS_TABLE + "</body>", 1)


def _exempt_a_cell_page(c):
    """Освободить от пола объёма СТРАНИЦУ СОДЕРЖИМОГО: освобождение
    задумано для служебных страниц, а выключает пол постранично кому
    угодно."""
    import render as rd
    p = sorted(_cells(c))[0]
    _stub("render", "FLOOR_EXEMPT",
          tuple(rd.FLOOR_EXEMPT) + ("/" + p[:-len("index.html")],))


def _hide_a_source(c):
    """Убрать исходник из осмотра. _sources берёт файл, только если он лежит
    на диске: переименованный модуль просто переставал осматриваться, и
    гейт управляющих байтов не замечал, что читает на один файл меньше."""
    _SAVED["src"] = dict(_sources())
    _SRC.pop("prose.py")


def _rule_after_ad_sheet(c):
    """Правило, дописанное ПОСЛЕ рекламного листа: стилистически безупречное
    и в design.py отсутствующее. Сверялась только первая половина отданной
    таблицы, и такое правило уезжало на 177 страниц при всех зелёных."""
    emb = _embeds(c)
    n = 0
    for k, v in list(c.items()):
        if k.endswith(".html") and k not in emb and "</style>" in v:
            c[k] = v.replace("</style>", ".bx-main{color:var(--ink)}</style>",
                             1)
            n += 1
    assert n, "в отданных байтах нет таблицы стилей сайта"
    _sheets_forget()


def _rule_in_embed_sheet(c):
    """То же в листе виджета: третья отданная таблица не сверялась ни с чем
    вовсе, и её обещали учтённой побайтово вместе с двумя другими."""
    n = 0
    for k in sorted(_embeds(c)):
        c[k] = c[k].replace("</style>", ".bx-lab{color:var(--ink)}</style>", 1)
        n += 1
    assert n, "в сборке нет ни одного виджета"
    _sheets_forget()


def _reach_by_getattr(c):
    """Гейт, зовущий функцию генератора ВЫЧИСЛЕННЫМ ИМЕНЕМ. Разбор видел
    ровно одно написание — rd.page_words(...), — и такой гейт проезжал мимо
    охвата, оставаясь зелёным на любой подмене."""
    _SAVED["src"] = dict(_sources())
    plant = ["def g_planted_by_name(files):",
             "    import render as rd",
             "    got = getattr(rd, 'page_' + 'words')",
             "    return [] if got else ['нечего']"]
    _SRC["gates.py"] = (_SRC["gates.py"] + chr(10) + chr(10)
                        + chr(10).join(plant) + chr(10))
    _REACH_MEMO[:] = [None, None]


def _reach_by_from_import(c):
    """Имя генератора, взятое через from ... import: обращение без имени
    модуля разбор не видит, и охват стал бы неполным молча."""
    _SAVED["src"] = dict(_sources())
    plant = ["from render import page_words",
             "",
             "def g_planted_import(files):",
             "    return [] if page_words else ['нечего']"]
    _SRC["gates.py"] = (_SRC["gates.py"] + chr(10) + chr(10)
                        + chr(10).join(plant) + chr(10))
    _REACH_MEMO[:] = [None, None]


def _blind_generator_module(c):
    """Модуль генератора, который не импортируется. Здесь стояло тихое
    mods[name] = None, и такой модуль вычёркивал из охвата все свои функции
    разом: мета-гейт печатал «пройден», проверив на шестую часть меньше."""
    _SAVED["refmods"] = REF_MODULES
    globals()["REF_MODULES"] = tuple(REF_MODULES) + ("nosuchgenerator",)
    _REACH_MEMO[:] = [None, None]


def _gate_missing_from_set(c):
    """Убрать гейт из набора, оставив определение в исходнике: ровно то
    состояние, в котором проба эталоном молча его не касалась — fn_name.get
    возвращал None, и дальше стояло continue."""
    _SAVED["gates_all"] = list(GATES)
    i = next(k for k, item in enumerate(GATES)
             if item[1].__name__ == "g_word_floor")
    del GATES[i]


def _gate_as_lambda(c):
    """Положить в набор лямбду: имени определения у неё нет, и все три пробы
    искали бы её по имени и не нашли — молча."""
    i = next(k for k, item in enumerate(GATES)
             if item[1].__name__ == "g_robots")
    _SAVED["gates_entry"] = (i, GATES[i])
    GATES[i] = (GATES[i][0], lambda files: ["нечего"])


def _gate_off_the_register(c):
    """Определение гейта осталось в исходнике, а из набора его убрали:
    выключенная проверка, о выключении которой никто не объявлял."""
    _SAVED["gates_all"] = list(GATES)
    i = next(k for k, item in enumerate(GATES)
             if item[1].__name__ == "g_robots")
    del GATES[i]


def _stale_blind_list(c):
    """Числить не берущим у генератора гейт, который берёт. Список нужен
    ради обратной стороны: гейт, ПЕРЕСТАВШИЙ дотягиваться до генератора,
    тихо переезжает в него — и запись про берущего делает это невидимым."""
    _SAVED["blind"] = set(NO_REFERENCE_GATES)
    NO_REFERENCE_GATES.add("g_word_floor")


def _undeclared_extra_check(c):
    """Снять объявление с проверки, которая печатается рядом с гейтами:
    ровно так проверка даты содержимого выглядела восемьдесят третьим
    гейтом, не будучи проверенной ничем."""
    _SAVED["extra"] = dict(EXTRA_CHECKS)
    EXTRA_CHECKS.clear()


def _break_floor_exempt(c):
    """Дописать в список исключений НАСТОЯЩУЮ тонкую страницу. Пол объёма
    выключается постранично, гейт читал ТОТ ЖЕ список, и семь таких страниц
    уезжали в карту сайта индексируемыми при всех зелёных гейтах — 123 слова
    при объявленном поле в 1500."""
    import render as rd
    _stub("render", "FLOOR_EXEMPT", tuple(rd.FLOOR_EXEMPT) + ("/size/9v/",))


def _unpin_a_constant(c):
    """Снять пин с порога: гейт снова брал бы ожидаемое у той же строки
    кода, которая его напечатала."""
    _SAVED["consts"] = dict(REFERENCE_CONSTS)
    REFERENCE_CONSTS.pop(("render", "WORD_FLOOR"))


def _pin_a_constant_nobody_reads(c):
    """Обещание проверки, которой нет: величина объявлена эталоном, а ни
    один гейт её не читает."""
    _SAVED["consts"] = dict(REFERENCE_CONSTS)
    REFERENCE_CONSTS[("render", "CONTENT_DATE")] = ("pin", _date(2000, 1, 1))


def _stub(modname, attr, fake):
    """Подменить функцию модуля на время одной проверки и запомнить прежнюю.
    Возврат — в _restore_css, вместе со всеми остальными подменами."""
    import importlib
    m = importlib.import_module(modname)
    _SAVED.setdefault("attrs", []).append((m, attr, getattr(m, attr)))
    setattr(m, attr, fake)
    _sheets_forget()


def _restore_css():
    import design
    _sheets_forget()
    if "wc" in _SAVED:
        import prose
        prose.wc = _SAVED.pop("wc")
    if "pw" in _SAVED:
        import render as rd
        rd.page_words = _SAVED.pop("pw")
    if "jac" in _SAVED:
        import render as rd
        rd.jaccard = _SAVED.pop("jac")
    if "shg" in _SAVED:
        import render as rd
        rd._shingles = _SAVED.pop("shg")
    if "win" in _SAVED:
        import render as rd
        rd.window_for = _SAVED.pop("win")
    if "form" in _SAVED:
        import cells
        cells.shell_form = _SAVED.pop("form")
    if "stubs" in _SAVED:
        REFERENCE_STUBS.clear()
        REFERENCE_STUBS.update(_SAVED.pop("stubs"))
    if "excuse" in _SAVED:
        NOT_A_REFERENCE.clear()
        NOT_A_REFERENCE.update(_SAVED.pop("excuse"))
    if "attrs" in _SAVED:
        for m, attr, old in reversed(_SAVED.pop("attrs")):
            setattr(m, attr, old)
    if "look" in _SAVED:
        # Ключ приходит ЗНАЧЕНИЕМ ПО УМОЛЧАНИЮ у _css_swap, и по имени
        # `_SAVED["look"]` его в исходнике не найти. Ветка не мёртвая.
        design.CSS = _SAVED.pop("look")
    if "exempt" in _SAVED:
        SPACING_EXEMPT.clear()
        SPACING_EXEMPT.update(_SAVED.pop("exempt"))
    if "contrast" in _SAVED:
        globals()["contrast"] = _SAVED.pop("contrast")
    if "ad" in _SAVED:
        design.AD_CSS = _SAVED.pop("ad")
    if "draw" in _SAVED:
        design.CSS = _SAVED.pop("draw")
    if "print" in _SAVED:
        design.CSS = _SAVED.pop("print")
    if "own_prose" in _SAVED:
        import render as rd
        rd.own_prose = _SAVED.pop("own_prose")
    if "article" in _SAVED:
        import prose
        prose.article = _SAVED.pop("article")
    if "iec" in _SAVED:
        import cells
        cells.IEC_LONG_FORM.clear()
        cells.IEC_LONG_FORM.update(_SAVED.pop("iec"))
    if "src" in _SAVED:
        _SRC.clear()
        _SRC.update(_SAVED.pop("src"))
    if "doc" in _SAVED:
        _DOC.clear()
        _DOC.update(_SAVED.pop("doc"))
    if "klass" in _SAVED:
        import cells
        cells.consequence_class = _SAVED.pop("klass")
    if "pos" in _SAVED:
        import cells
        cells.scale_position = _SAVED.pop("pos")
    if "ads" in _SAVED:
        import render as rd
        rd.carries_ads = _SAVED.pop("ads")
    if "gates_entry" in _SAVED:
        i, item = _SAVED.pop("gates_entry")
        GATES[i] = item
    if "scrollbar" in _SAVED:
        import design
        design.SCROLLBAR = _SAVED.pop("scrollbar")
    if "main_px" in _SAVED:
        import design
        design.main_px = _SAVED.pop("main_px")
    if "gates_all" in _SAVED:
        GATES[:] = _SAVED.pop("gates_all")
    if "blind" in _SAVED:
        NO_REFERENCE_GATES.clear()
        NO_REFERENCE_GATES.update(_SAVED.pop("blind"))
    if "extra" in _SAVED:
        EXTRA_CHECKS.clear()
        EXTRA_CHECKS.update(_SAVED.pop("extra"))
    if "consts" in _SAVED:
        REFERENCE_CONSTS.clear()
        REFERENCE_CONSTS.update(_SAVED.pop("consts"))
    if "skips" in _SAVED:
        SILENT_SKIPS.clear()
        SILENT_SKIPS.update(_SAVED.pop("skips"))
    if "refmods" in _SAVED:
        globals()["REF_MODULES"] = _SAVED.pop("refmods")
    _REACH_MEMO[:] = [None, None]
    # ЧТО СОХРАНЕНО И НЕ ВЕРНУЛОСЬ, ТО ОТРАВЛЯЕТ ВСЕ СЛЕДУЮЩИЕ ПОЛОМКИ
    # МОЛЧА: поломка под новым ключом просто не восстанавливалась бы, и
    # дальше краснело бы не то, что ломали. Ключ без возврата — провал.
    assert not _SAVED, ("поломка сохранила и не вернула: %s"
                        % ", ".join(sorted(_SAVED)))


def _in_lead(html, old, new):
    """Заменить строку ВНУТРИ подводки, а не где придётся на странице.

    Поломка, попавшая мимо цели, оставляет гейт зелёным и при этом выглядит
    проверкой: у нас так «первый абзац за h2» бил в подпись к столбцам.
    """
    m = re.search(r'<p class="bx-lead">(.*?)</p>', html, re.S)
    assert m, "на странице нет подводки"
    lead = m.group(1)
    assert old in lead, "в подводке нет «%s»" % old
    return html[:m.start(1)] + lead.replace(old, new, 1) + html[m.end(1):]


def _lead_of(html):
    m = re.search(r'<p class="bx-lead">(.*?)</p>', html, re.S)
    return m.group(1) if m else ""


def _page_with_lead(c, pattern):
    """Страница, у которой ИСКОМОЕ СТОИТ В ПОДВОДКЕ, а не где-то на ней.

    Прежний отбор брал страницу по всему тексту, и поломка била мимо: слова
    класса живут ещё и в легенде шкалы, и в таблице замен.
    """
    for k, v in sorted(c.items()):
        if k.endswith(".html") and re.search(pattern, _lead_of(v)):
            return k
    raise AssertionError("нет страницы, у которой в подводке %s" % pattern)


def _silent_gate(c):
    """Подсунуть в набор гейт, который на пустой выборке печатает «пройден».

    Мета-гейт обязан покраснеть на этом: разовой чисткой правило не держится,
    а следующий написанный гейт о нём не знает.
    """
    for i, (name, fn) in enumerate(GATES):
        if fn is g_empty_sample_is_a_failure:
            continue
        _SAVED["gates_entry"] = (i, GATES[i])
        GATES[i] = (name, lambda files: [])
        return
    raise AssertionError("в наборе нет ни одного гейта, кроме мета-гейта")


def _lookup_loses_a_page(c):
    """Страница остаётся на сайте, а поиск перестаёт её находить."""
    t = c["index.html"]
    m = re.search(r'(<script type="application/json" id="bx-index">)(.*?)'
                  r"(</script>)", t, re.S)
    assert m, "на главной нет блока данных поиска"
    d = json.loads(m.group(2))
    url = None
    for h in d["h"]:
        page = h.split("#")[0].strip("/")
        if page and 'content="cell"' in c.get(page + "/index.html", ""):
            url = h.split("#")[0]
            break
    assert url, "в указателе нет ни одной страницы элемента"
    d["h"] = ["/codes/" if x.split("#")[0] == url else x for x in d["h"]]
    c["index.html"] = t[:m.start(2)] + json.dumps(d) + t[m.end(2):]


def _page_type_undeclared(c):
    """Новый вид страницы, не объявленный ни в одном из двух списков области.
    Гейт обязан сказать, что не знает, обязан ли поиск её находить."""
    p = next(k for k, v in sorted(c.items()) if 'content="cell"' in v)
    c[p] = c[p].replace('name="page-type" content="cell"',
                        'name="page-type" content="widget"', 1)


def _pins_collapse(c):
    """Все штрихи одной шкалы сведены в одну точку: разные величины —
    одинаковая картинка, ровно как было на всех 57 шкалах."""
    p = next(k for k, v in sorted(c.items())
             if v.count('class="bx-scale-pin bx-scale-pin-off"') > 1)
    c[p] = re.sub(r'(class="bx-scale-pin bx-scale-pin-off" style="left:)'
                  r'[\d.]+(%")', r"\g<1>50.0\g<2>", c[p])


def _band_varies(c):
    """Полоса класса, объявленная ПОСТОЯННОЙ, начинает гулять от страницы к
    странице — то есть притворяется кодировкой, ничего не кодируя."""
    p = next(k for k, v in sorted(c.items())
             if 'class="bx-scale-band" style="left:' in v)
    c[p] = re.sub(r'(class="bx-scale-band" style="left:)([\d.]+)',
                  lambda m: m.group(1) + ("%.1f" % (float(m.group(2)) + 1)),
                  c[p], count=1)


def _break_scrollbar(c):
    """Убрать резерв под полосу прокрутки: ширина колонки поедет на 17 px, и
    именно эти 17 px однажды наехали объявлением на башню без всякой
    прокрутки."""
    import design
    _SAVED["scrollbar"] = design.SCROLLBAR
    design.SCROLLBAR = 0


def _break_main_px(c):
    """Сломать САМУ функцию ширины колонки. Гейт «формат влезает в колонку»
    спрашивает у неё же, поэтому остался бы зелёным."""
    import design
    _SAVED["main_px"] = design.main_px
    design.main_px = lambda view, L=None: 9999


def _lead_class_swapped(c):
    """Оговорка класса подменена соседней: числа те же, последствие другое.
    Ровно так «-20,0%» был «wrong class» на 14 строках и «reads off» на 3."""
    p = _page_with_lead(c, "a higher voltage class")
    c[p] = _in_lead(c[p], "a higher voltage class", "a shade high")


def _lead_same_volts_lie(c):
    """«То же напряжение» указывает на чужую величину: «7.2H5 carries the
    same 7.2 V» уже стояло у нас на девятивольтовой странице."""
    p = _page_with_lead(c, r"(?:runs|at) the same [\d.]+ V")
    m = re.search(r"(?:runs|at) the same ([\d.]+) V", _lead_of(c[p]))
    old = "the same %s V" % m.group(1)
    new = "the same %.1f V" % (float(m.group(1)) * 2 + 1)
    c[p] = _in_lead(c[p], old, new)


def _shift_number(c, path, pattern, delta):
    """Сдвинуть НАПЕЧАТАННОЕ число на единицу, ничего больше не трогая."""
    t = c[path]
    m = re.search(pattern, t)
    assert m, "на %s нет числа по образцу %s" % (path, pattern)
    c[path] = t[:m.start(1)] + str(int(m.group(1)) + delta) + t[m.end(1):]


def _hub_count_over(c):
    p = next(k for k, v in sorted(c.items())
             if 'name="page-type" content="hub"' in v)
    _shift_number(c, p, r"(\d+) designations? (?:carry|share)", 1)


def _hub_count_under(c):
    p = next(k for k, v in sorted(c.items())
             if 'name="page-type" content="hub"' in v)
    _shift_number(c, p, r"(\d+) designations? (?:carry|share)", -1)


def _shell_claim_diverges(c):
    """Страница элемента обещает оболочку не того размера, чем та страница,
    на которую сама же и ссылается."""
    p = next(k for k, v in sorted(c.items())
             if "against a shell that holds " in v and "/shell/" in v)
    _shift_number(c, p, r"against a shell that holds (\d+) designation", 1)


def _home_gone_count_diverges(c):
    _shift_number(c, "index.html", r"against (\d+) it does not", 1)


def _disc_count_over(c):
    _shift_number(c, "discontinued/index.html", r"The (\d+) listed here", 1)


def _disc_count_under(c):
    _shift_number(c, "discontinued/index.html", r"The (\d+) listed here", -1)


def _break_answer(c, path):
    """Укоротить АБЗАЦ РАЗБОРА первого не-константного раздела.

    Ищется тот же абзац, который ищет гейт: первый <p>, не являющийся
    подписью. Подпись ломать бессмысленно — гейт её и не читает.
    """
    t = c[path]
    for chunk in re.split(r"<h2>", t)[1:]:
        h2 = chunk.split("</h2>")[0]
        if h2 in P.CONSTANT_HEADS:
            continue
        import render as rd
        if h2 in rd.FIGURE_HEADS:
            continue
        sect = chunk.split("</h2>", 1)[1] if "</h2>" in chunk else ""
        for m in re.finditer(r"<p([^>]*)>(.*?)</p>", sect, re.S):
            if any(k in m.group(1) for k in NOT_THE_ANSWER):
                continue
            c[path] = t.replace(m.group(0),
                                "<p%s>Too short.</p>" % m.group(1), 1)
            return
    raise AssertionError("не нашлось абзаца разбора, который можно сломать")


def _break_figure(c, path):
    """Снять чертёж из раздела, объявленного разделом чертежа.

    Исключение для «Drawn to scale» объявлено ЯВНО, и цена объявления —
    вот эта поломка: раздел без чертежа обязан краснеть, иначе исключение
    превращается в дыру.
    """
    t = c[path]
    assert 'class="bx-fig"' in t, "на странице нет ни одного чертежа"
    c[path] = t.replace('class="bx-fig"', 'class="bx-nofig"')


def _break_scale_band(c):
    """Растянуть полосу класса во всю дорожку — то, что стояло на всех 57
    страницах со шкалой. Края берутся ИЗ СТРАНИЦЫ: набранные здесь руками,
    они пережили бы смену меры класса и промахнулись бы молча."""
    n = 0
    for p in sorted(c):
        if not p.endswith(".html"):
            continue
        for m in re.finditer(r'class="bx-scale-band" style="left:[\d.]+%;'
                             r'right:[\d.]+%"', c[p]):
            c[p] = c[p].replace(
                m.group(0),
                'class="bx-scale-band" style="left:0.0%;right:0.0%"')
            n += 1
            break
    assert n, "в сборке нет ни одной полосы класса"


def _break_scale_pin(c):
    """Сдвинуть ОДИН штрих на край дорожки. Число берётся из самой страницы:
    набранное руками «left:55.0%» пережило смену меры класса, штрих переехал
    на 54.0, и поломка перестала попадать в цель, оставив гейт зелёным."""
    for p in sorted(c):
        if not p.endswith(".html"):
            continue
        for m in re.finditer(r'bx-scale-pin-off" style="left:([\d.]+)%"',
                             c[p]):
            if float(m.group(1)) == 100.0:
                continue
            c[p] = (c[p][:m.start()]
                    + 'bx-scale-pin-off" style="left:100.0%"'
                    + c[p][m.end():])
            return
    raise AssertionError("в сборке нет ни одного штриха шкалы")


def _break_reciprocal(c):
    """Вернуть в СОБРАННУЮ страницу ровно тот дефект, который гейт три волны
    не видел: перевёрнутый знак процента В ТАБЛИЦЕ СНЯТЫХ.

    Ломается строка таблицы «Discontinued cell», а не «Cell», и это часть
    поломки: прежний гейт читал только вторую, был написан на одиннадцати
    парах её формы и печатал «пройден» над 113 парами, где одна сторона
    стоит в первой. Перевёрнутый здесь знак — это та самая ячейка, где
    процент считается от снятого, а напечатан рядом с напряжением снятого:
    обе страницы пары начинают печатать одну цифру с одним знаком.

    Ломается СОБРАННАЯ страница, а не функция: гейт сверяет две страницы
    между собой, и функция, подменённая после сборки, их уже не коснётся.
    """
    where = {}
    for p in _cells(c):
        code = _code_of(c[p])
        if code:
            where[code] = p
    for p in sorted(_cells(c)):
        me = _code_of(c[p])
        for code, r in sorted(_fits_rows(c[p], T_GONE).items()):
            q = where.get(code)
            if not q or not r["pct"]:
                continue
            back = dict(_fits_rows(c[q], T_LIVE))
            back.update(_fits_rows(c[q], T_GONE))
            if me not in back:
                continue
            j0 = c[p].find(">%s</a></th>" % code)
            end = c[p].find("</tr>", j0)
            assert j0 > 0 and end > j0, "строка снятого не нашлась"
            row = c[p][j0:end]
            m = re.search(r'([-+])(\d+(?:\.\d+)?%)<span class="bx-vtag">',
                          row)
            assert m, "в строке снятого нет знакового процента"
            flipped = ("-" if m.group(1) == "+" else "+") + m.group(2)
            new = row[:m.start()] + flipped + row[m.start() + len(m.group(1))
                                                  + len(m.group(2)):]
            assert new != row, "поломка прошла мимо строки"
            c[p] = c[p][:j0] + new + c[p][end:]
            return
    raise AssertionError("в сборке нет ни одной взаимной пары со стороной в "
                         "таблице снятых")


def _break_prose_ratio(c):
    """Перевернуть знак процента В ПРОЗЕ, оставив таблицу как есть: ровно та
    форма, в которой абзац четырнадцати страниц спорил со своей таблицей."""
    p = _page_with_lead(c, r"[-+−]\d")
    m = re.search(r"[-+−](\d+(?:\.\d+)?%)", _lead_of(c[p]))
    assert m, "в подводке нет знакового процента"
    old = m.group(0)
    c[p] = _in_lead(c[p], old,
                    ("-" if old[0] == "+" else "+") + m.group(1))


def _break_prose_ratio_outside(c):
    """Поставить знаковый процент в прозу витрины — туда, где правила сверки
    нет. Область гейта — часть гейта, и вторая её сторона тоже проверяется."""
    for p in sorted(_site_pages(c)):
        if p in _cells(c) or '<div class="bx-main">' not in c[p]:
            continue
        m = re.search(r'<p class="bx-lead">(.*?)</p>', c[p], re.S)
        if not m:
            continue
        c[p] = _in_lead(c[p], m.group(1)[:20], m.group(1)[:20] + " +9.9% ")
        return
    raise AssertionError("нет витрины с подводкой")


def _break_embed_limits(c):
    """Снять с виджета блок границ применимости — то состояние, в котором
    сто сорок шесть виджетов уезжали на чужие страницы."""
    p = sorted(_embeds(c))[0]
    m = re.search(r'<p class="bx-limits">.*?</p>', c[p], re.S)
    assert m, "в виджете нет блока границ"
    c[p] = c[p][:m.start()] + c[p][m.end():]


def _break_embed_chemistry(c):
    """Убрать из виджета столбец химии: вердикт по напряжению остаётся, а
    цена аккумулятора и цинк-воздушного элемента исчезает."""
    p = sorted(_embeds(c))[0]
    assert "<th>Chemistry</th>" in c[p], "в виджете нет столбца химии"
    c[p] = c[p].replace("<th>Chemistry</th>", "<th>Notes</th>", 1)


def _break_wrap_rule(c):
    """Снять правило переноса С ОТДАННЫХ БАЙТОВ: это и есть та сборка, на
    которой главная ехала вправо на 16 px при экране 320."""
    n = 0
    for p in list(c):
        if p.endswith(".html") and "overflow-wrap:break-word" in c[p]:
            c[p] = c[p].replace("overflow-wrap:break-word",
                                "overflow-wrap:normal")
            n += 1
    assert n, "в отданных байтах нет правила переноса"



def _break_readme_count(c):
    """Счёт гейтов в README переписывается на прежний: «82» вместо
    настоящего. Ровно та правка, которой НЕ БЫЛО три круга подряд, — и
    единственный гейт, который обязан её увидеть, читает не выкладку, а
    README с диска, поэтому портится кэш, а не отданные байты."""
    _SAVED["doc"] = dict(_DOC)
    doc = _readme()
    spoiled = doc.replace("# %d гейтов по собранному" % len(GATES),
                          "# 82 гейта по собранному", 1)
    assert spoiled != doc, "в README нет строки со счётом гейтов"
    _DOC["README.md"] = spoiled


def _break_gone_fit_word(c):
    """Слово посадки в строке таблицы СНЯТЫХ переворачивается на прежнее:
    «too tall» становится «sits lower». Это ровно тот дефект, что стоял на
    102 строках сайта, и ловить его обязан именно этот гейт: три волны
    постолбцовых проверок были над ним зелёными.
    """
    hit = False
    for k in sorted(c):
        v = c[k]
        if not k.endswith(".html") or T_GONE not in v:
            continue
        for b in re.finditer(r'<table class="bx-fits">.*?</table>', v, re.S):
            if T_GONE not in b.group(0):
                continue
            spoiled = b.group(0).replace(
                '<td class="bx-fit bx-fit-taller">too tall</td>',
                '<td class="bx-fit bx-fit-shorter">sits lower</td>', 1)
            if spoiled == b.group(0):
                continue
            c[k] = v[:b.start()] + spoiled + v[b.end():]
            hit = True
            break
        if hit:
            break
    assert hit, "поломка мимо цели: «too tall» в таблице снятых не нашлось"


def _break_prose_quantity(c):
    """Вернуть в шаблон НАБРАННУЮ РУКАМИ величину: «the same %s» снова
    становится «the same 3 V».

    Это ровно то состояние, в котором сайт печатал «они одного напряжения,
    3 В» о наборе, куда попадали элементы на 1,4 и 1,5 В. Портится ИСХОДНИК,
    а не отданные байты: по отданным байтам эта фраза не отличается от
    исправной — она грамматична, число правдоподобно, и увидеть подмену
    можно только там, где видно, что величину никто не считал.
    """
    _SAVED["src"] = dict(_sources())
    text = _SRC["depth.py"]
    # Якорь переехал вместе с текстом: блок опасности вынесен из duty в
    # свою секцию, и разбор соседей по глубине теперь стоит в
    # `_coinlithium`, а не в `_ingest`. Поломка обязана ходить за текстом —
    # иначе она однажды «не найдёт цель» и роняет самопроверку, а выглядит
    # это как поломка гейта, а не как переезд шаблона.
    old = 'say += ("They are one voltage, %s; depth is the only thing that "'
    assert old in text, "поломка мимо цели: шаблона о соседях по глубине нет"
    _SRC["depth.py"] = text.replace(
        old,
        'say += ("They are one voltage, 3 V; depth is the only thing that "', 1)

def _break_hub_threshold(c):
    """Сдвинуть НАПЕЧАТАННЫЙ порог оболочки на единицу.

    Раньше порог стоял в прозе СЛОВОМ «three», и эта поломка меняла слово на
    «four» — то есть проверяла орфографию, а не величину. Подмена самой
    константы MIN_HUB с 3 на 4 при этом проходила 88 гейтов из 88: сайт
    публиковал шесть оболочек при пороге 4 и печатал «three». Теперь порог
    печатается цифрой из константы, гейт сверяет напечатанное С КОНСТАНТОЙ, и
    ломается именно это.
    """
    home = c["index.html"]
    m = re.search(r"envelopes that carry (\d+)", home)
    assert m, "поломка мимо цели: порог оболочки на главной не напечатан"
    c["index.html"] = (home[:m.start(1)] + str(int(m.group(1)) + 1)
                       + home[m.end(1):])


def _break_relation_word(c):
    """Вернуть НАБРАННОЕ отношение на место посчитанного: «the same nominal»
    снова становится «roughly double».

    Это ровно то состояние, в котором сайт печатал «runs at 1.5 V, roughly
    double the nominal of the alkaline and silver classes» на семнадцати
    страницах: напряжение подставлено, отношение набрано, и полтора вольта
    против полутора — это столько же, а не вдвое.
    """
    hit = 0
    for p in list(c):
        if "the same nominal the alkaline and silver classes carry" not in c[p]:
            continue
        c[p] = c[p].replace(
            "the same nominal the alkaline and silver classes carry",
            "roughly double the nominal of the alkaline and silver classes", 1)
        hit += 1
    assert hit, "поломка мимо цели: заметки о равном номинале лития нет"


def _break_showcase_truncated(c):
    """Снять со среза счёт «и ещё N»: перечень снова утверждает «здесь все»,
    и R6 пропадает из витрины главной ровно так, как пропадала."""
    home = c["index.html"]
    assert " and 1 more" in home, "поломка мимо цели: счёта «и ещё» нет"
    c["index.html"] = home.replace(" and 1 more", "", 1)


def _break_kinds_count(c):
    """Разойтись числом с объявленным набором: «adds 7 kinds of value» снова
    становится тем «five things», которое стояло рядом со списком из семи."""
    home = c["index.html"]
    m = None
    for n in range(2, 20):
        if "adds %d kinds of value" % n in home:
            m = n
            break
    assert m is not None, "поломка мимо цели: числа вычисляемых видов нет"
    c["index.html"] = home.replace("adds %d kinds of value" % m,
                                   "adds %d kinds of value" % (m - 2), 1)


def selftest():
    import render as rd
    files, _stats, _acc, _cs = rd.assemble()
    print("собрано файлов: %d" % len(files))
    if run(files, quiet=True):
        print("СБОРКА НЕ ПРОХОДИТ СОБСТВЕННЫЕ ГЕЙТЫ")
        run(files)
        return 1

    cell = next(p for p in _cells(files))
    other = next(p for p in _cells(files) if p != cell)

    def broken(fn):
        c = dict(files)
        fn(c)
        return c

    breaks = [
        ("язык страницы английский",
         lambda c: c.__setitem__(cell, c[cell].replace("<h1>", "<h1>Элемент "))),
        ("нет управляющих байтов",
         lambda c: c.__setitem__(cell, c[cell] + chr(1))),
        ("браузер не ходит наружу",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>", '<img src="cdn.example.com/x.png"></body>'))),
        ("скрипт один, встроенный, короткий",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>", '<script src="/x.js"></script></body>'))),
        ("скрипт не строит разметку",
         lambda c: c.__setitem__("codes/index.html",
                                 c["codes/index.html"].replace(
                                     "</script>",
                                     "var x=document.body.innerHTML;</script>",
                                     1))),
        ("голова страницы заполнена верно",
         lambda c: c.__setitem__(cell, c[cell].replace("<h1>", "<h1>x</h1><h1>",
                                                       1))),
        ("внутренние ссылки ведут на существующее",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>", '<a href="/no-such-page/">x</a></body>'))),
        ("нет страниц-сирот",
         lambda c: c.__setitem__("lonely/index.html", c[cell])),
        ("карта сайта совпадает с сайтом",
         lambda c: c.__setitem__("sitemap.xml", c["sitemap.xml"].replace(
             "</urlset>",
             "<url><loc>https://batterycross.com/ghost/</loc></url></urlset>"))),
        ("robots указывает карту",
         lambda c: c.__setitem__("robots.txt", "User-agent: *\nAllow: /\n")),
        ("политика совпадает с разметкой",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>", "<script>gtag('config','X')</script></body>"))),
        # Поломка бьёт по АБЗАЦУ РАЗБОРА, а не по первому <p> за заголовком.
        # Прежняя ломала «первый <p> сразу за </h2>», и когда таблицу подняли
        # выше разбора, под удар попала подпись к столбцам — которую гейт
        # правильно пропускает. Поломка стала мимо цели, а гейт при этом
        # выглядел проверенным: ровно тот случай, ради которого самопроверка
        # и считает несработавшие поломки.
        ("ответ первым в каждом разделе", lambda c: _break_answer(c, cell)),
        ("ответ первым в каждом разделе", lambda c: _break_figure(c, cell)),
        ("нет близнецов по прозе",
         lambda c: c.__setitem__(other, c[cell])),
        # ГЛАВНОЕ ОБЕЩАНИЕ — ДВЕ ПОЛОМКИ РАЗНОГО РОДА: исчезнувший источник
        # и запрос, уведённый не в тот проход.
        # Обязательное раскрытие, вычеркнутое из отданной политики.
        ("раскрытие переживает подключение сети",
         lambda c: c.__setitem__("privacy/index.html",
                                 c["privacy/index.html"].replace(
                                     "previous visits to this and other "
                                     "sites", "previous visits"))),
        ("раскрытие переживает подключение сети",
         lambda c: c.__setitem__("privacy/index.html",
                                 c["privacy/index.html"].replace(
                                     'rel="nofollow noopener"', ""))),
        ("браузер не ходит наружу",
         lambda c: c.__setitem__("contact/index.html",
                                 c["contact/index.html"].replace(
                                     "<!--email_off-->", "", 1))),
        # Четыре правила, названные владельцем вслух. Гейт на них был,
        # а доказательства красноты не было ни одного.
        ("правила облика, названные владельцем, держатся",
         _break_reader_rule_measure),
        ("правила облика, названные владельцем, держатся",
         _break_reader_rule_sticky),
        ("поиск отвечает по габариту", _break_search_index_gone),
        ("поиск отвечает по габариту", _break_search_name_like_size),
        ("чертёж не врёт масштабом",
         lambda c: c.__setitem__(cell, re.sub(
             r'(<rect[^>]*width=")([\d.]+)(")', r"\g<1>999\g<3>", c[cell],
             count=1))),
        ("посадка и электрика раздельно",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>fully compatible</p><h1>", 1))),
        ("оговорки безопасности на месте",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "Before you swap anything", "Notes"))),
        ("нет пустых рекламных мест",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>", '<div class="bx-ad bx-ad-leader"></div></body>'))),
        # Класс надо убрать СО ВСЕХ страниц: пока он встречается хоть на
        # одной, гейт прав, что он применяется. Первая версия ломала одну
        # страницу и гейт молчал — справедливо.
        ("объявленные классы применяются",
         lambda c: [c.__setitem__(k, v.replace('class="bx-brand"',
                                               'class="bx-brand-x"'))
                    for k, v in list(c.items()) if k.endswith(".html")]),
        ("химия не спорит с обозначением",
         lambda c: c.__setitem__(cell, re.sub(
             r"<h1>[^<]+</h1>", "<h1>MR44</h1>", c[cell], count=1))),
        # Эти два гейта читают СТИЛЬ, а не файлы, поэтому ломается стиль.
        ("рекламные места точного размера", _break_ad_css),
        ("чертёж не ужимается по ширине", _break_draw_css),
        ("ссылки ведут на страницу, а не в указатель",
         lambda c: c.__setitem__(cell, re.sub(
             r'(<table class="bx-fits">.*?)<a href="/[a-z0-9-]+/"',
             r'\g<1><a href="/codes/"', c[cell], count=1, flags=re.S))),
        ("числа в прозе совпадают с сайтом", _break_hub_threshold),
        ("нет ссылок на самих себя",
         lambda c: c.__setitem__("codes/index.html",
                                 c["codes/index.html"].replace(
                                     "</body>",
                                     '<a href="/codes/">loop</a></body>', 1))),
    ]

    # Ветки, добавленные позже основной поломки, ломаются ОТДЕЛЬНО: гейт,
    # покрасневший на одной ветке, ничего не говорит про остальные. Блок
    # данных на главной появился после того, как гейт уже был написан.
    breaks += [
        ("скрипт один, встроенный, короткий",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "</body>",
             chr(60) + 'script type="application/json" id="two">[]'
             + chr(60) + "/script></body>"))),
        ("скрипт один, встроенный, короткий",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             'type="application/json" id="bx-index"',
             'type="application/json" src="/i.json" id="bx-index"', 1))),
        ("скрипт один, встроенный, короткий",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "</body>", chr(60) + "script>var z=1;" + chr(60)
             + "/script></body>"))),
    ]
    breaks += [
        ("нет двойного экранирования",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>&amp;mdash;</p><h1>", 1))),
        ("посадка и электрика раздельно",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>It is a different voltage class, but that shows up "
             "as a reading, not as a failure.</p><h1>", 1))),
        ("посадка и электрика раздельно",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>Everything listed is deeper, so add a spacer.</p>"
             "<h1>", 1))),
        ("посадка и электрика раздельно",
         lambda c: c.__setitem__(
             "discontinued/index.html",
             re.sub(r'<span class="bx-v bx-v-[a-z]+">.*?</span></span>',
                    "&mdash;", c["discontinued/index.html"], count=1,
                    flags=re.S))),
        ("названия химий целые",
         lambda c: c.__setitem__(
             "sizes/index.html",
             c["sizes/index.html"].replace("nickel-metal hydride",
                                           "nickel-me", 1))),
        ("снятый не говорит о себе в настоящем",
         lambda c: c.__setitem__(
             "3-0316/index.html",
             c["3-0316/index.html"].replace("It reached shelves",
                                            "It reaches shelves", 1))),
        ("число согласовано с глаголом",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>The 1 option below share the diameter.</p><h1>", 1))),
        ("артикль согласован со звуком",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>This is a AA cell.</p><h1>", 1))),
        ("артикль согласован со звуком", _break_article_rule),
        ("число согласовано с глаголом",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>1 designation of the 6 here are discontinued.</p><h1>",
             1))),
        ("сказано, для скольких замены нет",
         lambda c: c.__setitem__(
             "discontinued/index.html",
             c["discontinued/index.html"].replace(
                 "none in this catalog", "no match", 1))),
        ("адрес оболочки называет её форму", _shell_head_swapped),
        ("адрес оболочки называет её форму", _shell_head_unknown),
        ("адрес оболочки называет её форму", _shell_dims_lie),
        ("адрес оболочки называет её форму", _break_shell_form),
        ("выкладка совпадает с генератором",
         lambda c: c.__setitem__(cell, c[cell] + "<!-- not on disk -->")),
        ("числа в прозе совпадают с сайтом",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "the list of", "the list of x", 1))),
        ("применённые классы объявлены",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'class="bx-wrap"', 'class="bx-wrap bx-nowhere"', 1))),
        ("поиск ведёт на существующее",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             '"/sr44/"', '"/no-such-cell/"'))),
        ("поиск ведёт на существующее",
         lambda c: c.__setitem__("mr9/index.html",
                                 c["mr9/index.html"].replace("PX625", "PX62X"))),
        ("поиск ведёт на существующее",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             'id="bx-q"', 'id="bx-gone"', 1))),
        ("скрипт не строит разметку",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             '"application/json" id="bx-index">{', '"application/json" '
             'id="bx-index">{{', 1))),
        ("скрипт не строит разметку",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             '"application/json" id="bx-index">{', '"application/json" '
             'id="bx-index">{' + chr(60) + 'b ', 1))),
    ]
    # Ветки, добавленные после разбора выкладки: каждая ломается ОТДЕЛЬНО.
    breaks += [
        ("нет управляющих байтов",
         lambda c: c.__setitem__(cell, c[cell] + chr(0x82))),
        ("нет управляющих байтов",
         lambda c: c.__setitem__(cell, c[cell] + chr(0x7F))),
        ("нет управляющих байтов", _break_source_bytes),
        ("в ячейках нет заглушек",
         lambda c: c.__setitem__("size/d/index.html",
                                 c["size/d/index.html"].replace(
                                     "<td>1.5 V</td>", "<td>unknown</td>", 1))),
        ("в ячейках нет заглушек",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</tbody>", "<tr><th>x</th><td>None</td></tr></tbody>", 1))),
        ("вытисненное прослеживается до снимка", _break_stamped),
        ("полная форма МЭК из известных ответов", _break_iec_table),
        ("полная форма МЭК из известных ответов",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             'LR1130|', 'LR15111|', 1))),
        ("ключи указателя уникальны и посчитаны",
         lambda c: c.__setitem__("codes/index.html",
                                 c["codes/index.html"].replace(
                                     '<ul class="bx-ix" role="list">',
                                     '<ul class="bx-ix" role="list">'
                                     '<li data-k="lr44">'
                                     '<a href="/lr44/">LR44</a></li>', 1))),
        ("утверждение о полноте посчитано",
         lambda c: c.__setitem__("size/j/index.html",
                                 c["size/j/index.html"].replace(
                                     "<td>6 V</td>", "<td>&mdash;</td>", 1))),
        ("числа в заметках о химии из записей",
         lambda c: c.__setitem__(
             "mr9/index.html",
             c["mr9/index.html"].replace("held a very flat 1.4 V",
                                         "held a very flat 1.35 V", 1))),
        ("химия не спорит с обозначением",
         lambda c: c.__setitem__("mr43/index.html",
                                 c["mr43/index.html"].replace(
                                     "The two disagree", "They agree", 1))),
        ("утверждения ограничены данными",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>Mercury cells are no longer made anywhere.</p><h1>",
             1))),
        ("утверждения ограничены данными",
         lambda c: c.__setitem__(
             "mr9/index.html",
             c["mr9/index.html"].replace(
                 "<h1>", "<p>Nothing shares this exact size.</p><h1>", 1))),
    ]
    # Напряжение: две чистые функции, метка, геометрия и проза —
    # каждая ветка ломается ОТДЕЛЬНО.
    breaks += [
        ("напряжение считается двумя функциями", _break_consequence_class),
        ("напряжение считается двумя функциями", _break_scale_position),
        # Один и тот же процент с двумя разными метками — тот самый
        # случай: «-20,0%» стояло как wrong class на 14 строках и как reads
        # off на 3.
        ("метка совпадает с напечатанным процентом",
         lambda c: c.__setitem__("lr6/index.html", c["lr6/index.html"].replace(
             '"bx-v bx-v-calibration"', '"bx-v bx-v-wrong"', 1))),
        ("метка совпадает с напечатанным процентом",
         lambda c: c.__setitem__("lr6/index.html", c["lr6/index.html"].replace(
             '<span class="bx-vtag">reads off', '<span class="bx-vtag">same volts',
             1))),
        ("метка совпадает с напечатанным процентом",
         lambda c: [c.__setitem__(k, re.sub(r'class="bx-v bx-v-[a-z]+"',
                                            'class="bx-v bx-v-none"', v))
                    for k, v in list(c.items()) if k.endswith(".html")]),
        # Полоса во всю дорожку и штрихи по краям — то, что стояло на
        # всех 57 страницах со шкалой.
        ("шкала кодирует отклонение", _break_scale_band),
        ("шкала кодирует отклонение", _break_scale_pin),
        ("шкала кодирует отклонение",
         lambda c: [c.__setitem__(k, v.replace(
             "The axis is the difference from this cell", "The axis"))
                    for k, v in list(c.items()) if k.endswith(".html")]),
        # Голый вердикт посадки в абзаце-ответе — то, что стояло на 23
        # страницах при переходе до 700%.
        ("вердикт посадки в прозе несёт напряжение",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", '<p class="bx-lead">The closest listed cell, A27, fits '
             "but sits lower.</p><h1>", 1))),
        ("вердикт посадки в прозе несёт напряжение",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>LR44 and SR44 drop into the same slot.</p><h1>", 1))),
        # Расширенная ОБЛАСТЬ оговорок: витрина снятых делает 64
        # рекомендации, и гейт обязан смотреть и туда.
        ("оговорки безопасности на месте",
         lambda c: c.__setitem__(
             "discontinued/index.html",
             c["discontinued/index.html"].replace(
                 "Before you swap anything", "Notes", 1))),
        # Пустая выборка ОБЯЗАНА краснеть.
        ("оговорки безопасности на месте",
         lambda c: [c.__setitem__(k, v.replace('class="bx-vtag"',
                                               'class="bx-vt"')
                                  .replace("Closest current", "Closest"))
                    for k, v in list(c.items()) if k.endswith(".html")]),
    ]
    # Деньги и доверие: инвентарь, карточка ссылки, структурные данные,
    # публичный адрес, описания. Каждая ветка ломается ОТДЕЛЬНО.
    breaks += [
        ("инвентарь заводится по содержимому", _strip_ads),
        ("инвентарь заводится по содержимому", _ad_on_legal),
        ("инвентарь заводится по содержимому", _break_carries_ads),
        ("нет пустых рекламных мест", _strip_ads),
        ("объявление ниже ответа", _ad_to_top),
        ("объявление ниже ответа", _ad_to_bottom),
        ("объявление ниже ответа", _drop_flow_ad),
        ("публичный адрес на своём домене",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "hello@batterycross.com", "info@bilingoplus.com"))),
        ("публичный адрес на своём домене",
         lambda c: c.__setitem__("contact/index.html",
                                 c["contact/index.html"].replace(
                                     "mailto:hello@batterycross.com",
                                     "mailto:hello@example.net", 1))),
        ("карточка ссылки совпадает с головой",
         lambda c: c.__setitem__(cell, c[cell].replace(
             '<meta property="og:title" content="',
             '<meta property="og:title" content="Cheap batteries ', 1))),
        ("карточка ссылки совпадает с головой",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'name="twitter:card" content="summary"',
             'name="twitter:card" content="summary_large_image"', 1))),
        ("карточка ссылки совпадает с головой",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</head>", '<meta property="og:image" '
             'content="https://batterycross.com/card.png"></head>', 1))),
        ("структурные данные совпадают с видимым", _ld_add_field),
        ("структурные данные совпадают с видимым", _ld_fake_value),
        ("структурные данные совпадают с видимым", _ld_break_json),
        ("структурные данные совпадают с видимым", _ld_drop),
        ("структурные данные совпадают с видимым", _ld_fake_crumb),
        ("описания различаются своими величинами", _desc_same),
        ("описания различаются своими величинами", _desc_one_template),
        # Политика и разметка расходятся в ОБЕ стороны, и обе ловятся.
        ("политика совпадает с разметкой",
         lambda c: c.__setitem__("privacy/index.html",
                                 c["privacy/index.html"].replace(
                                     'data-hosts="none"',
                                     'data-host="cdn.example.com"', 1))),
        ("политика совпадает с разметкой",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>",
             '<img src="https://cdn.example.com/x.png"></body>', 1))),
        ("политика совпадает с разметкой",
         lambda c: c.__setitem__("privacy/index.html",
                                 c["privacy/index.html"].replace(
                                     'data-ads="none"', 'data-x="none"', 1))),

        # --- поиск: главное действие сайта, и каждая его половина ломается.
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace('id="bx-q"',
                                                       'id="bx-was"', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             '<form class="bx-find" id="bx-find"',
             '<form class="bx-find" id="bx-find" hidden', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'action="/codes/"', 'action="/nowhere/"', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             ' name="q"', "", 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'id="bx-nojs"', 'id="bx-was-nojs"', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'id="bx-none"', 'id="bx-was-none"', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'id="bx-n"', 'id="bx-was-n"', 1))),
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'id="bx-res"', 'id="bx-was-res"', 1))),
        # Указатель обязан быть ОДИН: два разных на одном сайте разойдутся.
        ("поиск на каждой странице",
         lambda c: c.__setitem__(cell, c[cell].replace(
             'id="bx-index">{', 'id="bx-index">{"z":1,', 1))),

        ("поиск отвечает на набранное",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "AA|", "QQ|", 1))),
        ("поиск отвечает на набранное",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "AG13|", "XG13|", 1))),
        ("поиск отвечает на набранное",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "|20x3.2|", "|21x3.2|"))),
        ("поиск отвечает на набранное",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "SR626|", "SR627|", 1))),

        ("в указателе нет тупиков",
         lambda c: c.__setitem__("codes/index.html",
                                 c["codes/index.html"].replace('id="c-',
                                                               'id="q-'))),
        ("в указателе нет тупиков", _dead_end_to_index),

        ("обещанное про поиск выполняется",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h1>", "<p>Import markings like AG13 are not in this "
             "data.</p><h1>", 1))),
        ("обещанное про поиск выполняется",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "a bare <b>20</b> lists the designations 20 mm across",
             "a bare <b>77</b> lists the designations 77 mm across", 1))),
        ("обещанное про поиск выполняется",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "h.length<12", "h.length<3", 1))),
        ("обещанное про поиск выполняется",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             'placeholder="CR2032, AG13, AA, 20 x 3.2"',
             'placeholder="CR2032, AG13, AA, ZX9999"', 1))),
        ("обещанное про поиск выполняется",
         lambda c: c.__setitem__("index.html", c["index.html"].replace(
             "V13GA|", "W13GA|", 1))),

        # --- пол объёма: обе стороны правила, и САМА область гейта близнецов
        ("пол объёма держится", _thin_page_stays_indexed),
        ("пол объёма держится", _floor_page_gutted),
        ("пол объёма держится",
         lambda c: c.__setitem__("sitemap.xml", c["sitemap.xml"].replace(
             "</urlset>",
             "<url><loc>https://batterycross.com/shells/</loc></url>"
             "</urlset>", 1))),
        ("гейт близнецов читает весь текст", _twin_scope_shrunk),
        ("гейт близнецов читает весь текст", _twin_pages_made_alike),
        ("гейт близнецов читает весь текст",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "<h2>Before you swap anything</h2>",
             "<h2>Before you swap something</h2>", 1))),

        # --- два случая, где неверная замена действительно вредит
        ("опасные применения названы", _hazard_removed),
        ("опасные применения названы", _ingest_note_removed),
        ("опасные применения названы",
         lambda c: c.__setitem__("cr2032/index.html",
                                 c["cr2032/index.html"].replace(
                                     "Reese", "Some", 1))),

        # --- источники
        ("источники пронумерованы и настоящие", _source_record_invented),
        ("источники пронумерованы и настоящие", _source_sheet_invented),
        ("источники пронумерованы и настоящие", _source_list_dropped),
        ("источники пронумерованы и настоящие",
         lambda c: c.__setitem__(cell, c[cell].replace(
             '<span class="bx-refno">[1]</span>',
             '<span class="bx-refno">[4]</span>', 1))),

        # --- печать
        ("печать не режет таблицу и чертёж", _break_print_css),
        ("печать не режет таблицу и чертёж",
         lambda c: c.__setitem__(cell, c[cell].replace("@media print", "@media x", 1))),

        # --- институциональная оболочка
        ("институциональная оболочка на месте", _about_dropped),
        ("институциональная оболочка на месте", _about_unlinked),
        ("институциональная оболочка на месте",
         lambda c: c.__setitem__("about/index.html",
                                 c["about/index.html"].replace(
                                     "BiLingoPlus LLC", "A Person", 1))),

        # --- набор данных
        ("набор данных опубликован и сходится", _dataset_dropped),
        ("набор данных опубликован и сходится", _dataset_diverges),
        ("набор данных опубликован и сходится", _dataset_volts_wrong),

        # --- виджеты
        ("виджеты остаются фрагментами", _embed_gets_a_script),
        ("виджеты остаются фрагментами", _embed_becomes_indexable),
        ("виджеты остаются фрагментами", _embed_loses_backlink),
        # ------------------------------------- художественная волна
        ("цвета парны и объявлены на голом :root", _break_colour_only_dark),
        ("цвета парны и объявлены на голом :root", _break_colour_alias),
        ("цвета парны и объявлены на голом :root", _break_colour_literal),
        ("контраст пар держится", _break_contrast_light),
        ("контраст пар держится", _break_contrast_dark),
        ("контраст пар держится", _break_contrast_formula),
        ("один сигнал — одна работа", _break_second_accent),
        ("один сигнал — одна работа", _break_signal_job),
        ("кегль из одной шкалы", _break_type_off_scale),
        ("кегль из одной шкалы", _break_heading_smaller_than_body),
        ("отступы из одного шага", _break_spacing_by_hand),
        ("отступы из одного шага", _break_spacing_fractional),
        ("отступы из одного шага", _break_spacing_stale_exempt),
        ("формат места влезает в колонку", _break_ad_breakpoint),
        ("формат места влезает в колонку", _break_ad_no_format),
        ("ответ выше справочных величин", _break_answer_below_strip),
        ("ответ выше справочных величин", _break_answer_below_aliases),
        ("ответ выше справочных величин", _break_answer_sample_empty),

        # --------------------------------- волна аудита сентября 2026
        # Область гейта, эталон гейта и кодирование картинкой.
        ("пустая выборка роняет каждый гейт", _silent_gate),
        ("пустая выборка роняет каждый гейт", lambda c: c.clear()),
        ("поиск находит каждую опубликованную страницу",
         _lookup_loses_a_page),
        ("поиск находит каждую опубликованную страницу",
         _page_type_undeclared),
        ("геометрия меняется вместе с величиной", _pins_collapse),
        ("геометрия меняется вместе с величиной", _band_varies),
        ("арифметика раскладки из известных ответов", _break_scrollbar),
        ("арифметика раскладки из известных ответов", _break_main_px),
        ("класс в подводке следует из отношения", _lead_class_swapped),
        ("класс в подводке следует из отношения", _lead_same_volts_lie),
        # Сломать САМУ функцию класса: подводка при этом не меняется, и
        # гейт, согласный с прозой, остался бы зелёным.
        ("класс в подводке следует из отношения",
         _break_consequence_class),
        # Счётные утверждения — В ОБЕ СТОРОНЫ: проза обещает больше
        # посчитанного и проза обещает меньше посчитанного.
        ("счётные утверждения посчитаны", _hub_count_over),
        ("счётные утверждения посчитаны", _hub_count_under),
        ("счётные утверждения посчитаны", _shell_claim_diverges),
        ("счётные утверждения посчитаны", _home_gone_count_diverges),
        ("числа в прозе совпадают с сайтом", _disc_count_over),
        ("числа в прозе совпадают с сайтом", _disc_count_under),
        # Пустая ячейка — то же напечатанное «ничто», только молча.
        ("в ячейках нет заглушек",
         lambda c: c.__setitem__(cell, c[cell].replace(
             "</body>",
             "<table><tr><th>x</th><td></td></tr></table></body>", 1))),
        # Заголовок — тоже опубликованное обозначение.
        ("вытисненное прослеживается до снимка",
         lambda c: c.__setitem__(cell, re.sub(
             r"<h1>[^<]+</h1>", "<h1>ZZ9999X</h1>", c[cell], count=1))),
        # Взаимность: одна пара — один вердикт, и ломается он на одной из
        # двух страниц, а видно это только при сверке их между собой.
        ("взаимный вердикт совпадает у обеих страниц", _break_reciprocal),
        # Проза против своей же таблицы — В ОБЕ СТОРОНЫ смысла нет: знак и
        # есть направление, и перевёрнутый знак это другое утверждение.
        ("процент в прозе совпадает с таблицей страницы", _break_prose_ratio),
        ("процент в прозе совпадает с таблицей страницы",
         _break_prose_ratio_outside),
        # Виджет: и оговорки, и столбец, который их несёт.
        ("виджет несёт оговорки вместе с вердиктом", _break_embed_limits),
        ("виджет несёт оговорки вместе с вердиктом", _break_embed_chemistry),
        # Ширина: правило переноса снимается с отданных байтов.
        ("узкая колонка держит длинное слово", _break_wrap_rule),

        # ------------------------------ ВОЛНА ЭТАЛОНА: сентябрь 2026
        # Ломается САМА ФУНКЦИЯ, а не страница. Проверяющий сделал ровно
        # это и получил семьдесят семь зелёных гейтов: сайт при такой
        # поломке не портится, портится ОТБОР — какие страницы уедут в
        # индекс, какие будут отсеяны близнецами, каким адресом назовётся
        # оболочка.
        ("текстовые функции из известных ответов", _break_wc),
        ("текстовые функции из известных ответов", _break_page_words),
        ("текстовые функции из известных ответов", _break_jaccard),
        ("текстовые функции из известных ответов", _break_shingles),
        ("текстовые функции из известных ответов", _break_shell_form),
        ("текстовые функции из известных ответов", _break_window_for),
        ("пол объёма держится", _break_page_words),
        ("нет близнецов по прозе", _break_jaccard),
        ("нет близнецов по прозе", _break_shingles),
        ("гейт близнецов читает весь текст", _break_jaccard),
        ("гейт близнецов читает весь текст", _break_wc),
        ("ответ первым в каждом разделе", _break_window_for),
        ("ответ первым в каждом разделе", _break_wc),
        # Химия: поле записи обязано НАХОДИТЬСЯ, иначе сверка буквы с полем
        # не выполняется ни разу, а гейт печатает «пройден».
        ("химия не спорит с обозначением",
         lambda c: _stub("cells", "_s", lambda row, key: "mercuric oxide")),
        # Облик: правило, приехавшее МИМО объявленной таблицы стилей.
        ("цвета парны и объявлены на голом :root", _rule_outside_the_sheet),
        ("цвета парны и объявлены на голом :root", _second_style_element),
        ("объявленные классы применяются",
         lambda c: _stub("design", "strip_comments", lambda css: css[:40])),
        # Мета-гейт: четыре вида дыры в его собственном учёте.
        ("эталон не берётся у проверяемого", _unwatch_a_function),
        ("эталон не берётся у проверяемого", _watch_a_function_nobody_calls),
        ("эталон не берётся у проверяемого",
         _excuse_a_gate_that_does_not_call),
        ("эталон не берётся у проверяемого", _stale_excuse),
        ("эталон не берётся у проверяемого", _gate_that_cannot_fail),
        # Мета-гейт эталона: четыре способа выпасть из его охвата МОЛЧА.
        ("эталон не берётся у проверяемого", _reach_by_getattr),
        ("эталон не берётся у проверяемого", _reach_by_from_import),
        ("эталон не берётся у проверяемого", _blind_generator_module),
        ("эталон не берётся у проверяемого", _gate_missing_from_set),
        # Величины генератора: пин, лишняя запись и выключенный пол объёма.
        ("величина генератора объявлена эталоном", _break_floor_exempt),
        ("величина генератора объявлена эталоном", _unpin_a_constant),
        ("величина генератора объявлена эталоном",
         _pin_a_constant_nobody_reads),
        # Учёт: гейт без имени, гейт мимо набора, устаревшая запись и
        # проверка, которая печатается как гейт, не будучи объявленной.
        ("учёт гейтов и проб полон", _gate_as_lambda),
        ("учёт гейтов и проб полон", _gate_off_the_register),
        ("учёт гейтов и проб полон", _stale_blind_list),
        ("учёт гейтов и проб полон", _undeclared_extra_check),
        # Пропавший исходник и две несверявшиеся отданные таблицы стилей.
        ("нет управляющих байтов", _hide_a_source),
        ("цвета парны и объявлены на голом :root", _rule_after_ad_sheet),
        ("цвета парны и объявлены на голом :root", _rule_in_embed_sheet),
        # Тихие пропуски ВНУТРИ гейтов: запись без страницы, отбор по одной
        # стороне, незнакомая таблица и освобождение, выданное содержимому.
        ("опасные применения названы", _hazard_page_off_the_slug),
        ("опасные применения названы", _headline_volts_drift),
        ("взаимный вердикт совпадает у обеих страниц", _extra_fits_table),
        ("пол объёма держится", _exempt_a_cell_page),
        # Общее правило волны: у тихой ветки есть имя, и обе стороны.
        ("у тихой ветки есть имя", _unnamed_silent_skip),
        ("у тихой ветки есть имя", _stale_silent_skip),
        # Слово посадки в строке СНЯТОГО, перевёрнутое обратно.
        ("строка таблицы пары про один предмет", _break_gone_fit_word),
        # Счёт гейтов в README, отставший от набора.
        ("README считает гейты по факту", _break_readme_count),
        ("величина в прозе посчитана или объявлена", _break_prose_quantity),
        # Волна отношений: набранное сравнение, срез без счёта и
        # число, разошедшееся с объявленным набором.
        ("отношение посчитано по числам рядом", _break_relation_word),
        ("отношение посчитано по числам рядом",
         _break_showcase_truncated),
        ("объявленный набор совпадает с напечатанным",
         _break_kinds_count),
    ]
    assert {n for n, _ in breaks} == {n for n, _ in GATES}, (
        "поломки и гейты не совпадают по именам")
    assert len(GATES) == GATE_COUNT

    ok = stamp_selftest()
    for name, fn in breaks:
        gate = dict(GATES)[name]
        result = gate(broken(fn))
        _restore_css()
        if not result:
            print("  ГЕЙТ НЕ СРАБОТАЛ  %s" % name)
            ok = False
        else:
            print("  краснеет          %s" % name)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    import render as rd
    files, _s, _a, _c = rd.assemble()
    failed = run(files)
    stale, asleep = stamp(files, rd.CONTENT_DATE)
    if stale:
        print("  ПРОВАЛ  дата содержимого")
        print("          %s" % stale)
        failed += 1
    elif asleep:
        # НЕ «ПРОЙДЕН». Сверка не выполнялась, и печатать её выполненной —
        # то же самое, что зелёный гейт над пустой выборкой.
        print("  НЕ ПРОВЕРЕНО дата содержимого: %s" % asleep)
    else:
        print("  пройден дата содержимого совпадает с содержимым")
    sys.exit(1 if failed else 0)
