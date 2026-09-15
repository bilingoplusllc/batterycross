# -*- coding: utf-8 -*-
"""BatteryCross — сборка всего сайта в dist/. Стандартная библиотека, ноль сети.

АНАТОМИЯ СТРАНИЦЫ ЭЛЕМЕНТА ([PLAYBOOK §1]):

  1 заголовок       обозначение и чужие имена, под которыми его ищут
  2 главное число   что это и чем заменить — выше сгиба
  3 ОТЛИЧИЕ         вычисленное, чего нет у источника
  4 ПОСАДКА         что встанет и чем обернётся — ради этого сайт и есть
  5 чертёж          силуэт в масштабе и семья габарита
  6 таблица         все опубликованные величины, не урезанные
  7 «а это много?»  место по запасу энергии среди соседей по оболочке
  8 границы         чего мы не видим — на этом сайте не формальность
  9 соседи + метод

Тексты живут в prose.py и ветвятся по ФОРМЕ данных (решение D-013), облик — в
design.py, геометрия чертежей — в draw.py. Здесь только сборка.

ГЕЙТЫ В gates.py, и каждый умеет падать: `python gates.py --selftest`.
"""
import io
import json
import os
import re
import shutil
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cells as C  # noqa: E402
import depth as D  # noqa: E402
import design  # noqa: E402
import draw  # noqa: E402
import prose as P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dist")

SITE, DOMAIN = "BatteryCross", "batterycross.com"
PUBLISHER = "BiLingoPlus LLC"

# ИМЯ В ПОДВАЛЕ — ИМЯ САЙТА, А НЕ ЮРЛИЦА.
#
# «BiLingoPlus LLC» на 176 страницах сайта про элементы питания ничего не
# объясняет и вызывает лишний вопрос: человек пришёл узнать, что подойдёт
# вместо снятого с производства элемента, и видит имя бюро локализации.
# Юридической нужды в этом нет: право на знак копирайта не зависит от
# формы записи, а установить владельца можно на страницах terms, privacy,
# about и contact, где юрлицо названо полностью и с юрисдикцией.
#
# Поэтому в подвале и в строке цитирования стоит BatteryCross, а юрлицо
# остаётся там, где оно и означает что-то: в условиях, политике и контактах.
FOOT_NAME = SITE
# ПУБЛИЧНЫЙ АДРЕС — НА СВОЁМ ДОМЕНЕ. Стоял info@bilingoplus.com: ящик
# поддержки платящих клиентов Cardwright и GridScoop, напечатанный 331 раз в
# подвале рекламного сайта. Две писаные нормы сразу: письмо про даташит не
# должно падать туда, где лежат просьбы о лицензионном ключе, и сайты ветки
# не ссылаются на bilingoplus.com. Юридическое имя издателя остаётся: §8
# требует названного издателя, и это другое.
CONTACT = "hello@batterycross.com"


def mail_link(addr=None):
    """Почтовая ссылка ОДНИМ печатником, и всегда в обёртке.

    Cloudflare по умолчанию переписывает адреса в разметке на
    «[email protected]» и дописывает свой скрипт на каждую страницу —
    у нас это уже случалось на соседнем сайте. Обёртка `email_off` это
    выключает, и стояла она только в подвале: лид страницы Contact и абзац
    Corrections на About оставались незащищёнными, хотя README утверждал
    обратное.
    """
    a = addr or CONTACT
    return ('<!--email_off--><a href="mailto:%s">%s</a><!--/email_off-->'
            % (a, a))
# Дата СНИМКА, а не сборки: имя выгружаемого CSV и строка цитирования обязаны
# указывать на день, когда данные забраны, иначе постоянная ссылка меняется
# при каждой пересборке и цитировать её нельзя.
DATA_SNAPSHOT = date(2026, 9, 1)


def snap_date():
    """Дата снимка СЛОВАМИ. ОДНА функция на сайт: строка цитирования несла
    «retrieved 1 September 2026» НАБРАННЫМИ РУКАМИ в трёх строках над самой
    датой, и правка DATA_SNAPSHOT сдвинула бы одну и не сдвинула вторую."""
    return DATA_SNAPSHOT.strftime("%d %B %Y").lstrip("0")


DATA_VINTAGE = "Energizer technical data, retrieved " + snap_date()
CONTENT_DATE = date(2026, 9, 15)

# Ни счётчика, ни кук. Флаг читают разметка, текст политики и гейт — втроём
# они разойтись не могут.
ANALYTICS = False
COOKIES = False

# ВСЁ СТОРОННЕЕ, ЗА ЧЕМ ПОЙДЁТ БРАУЗЕР, — здесь, и только здесь. Пусто.
# Утверждение о приватности — это утверждение о том, что ГРУЗИТ БРАУЗЕР, а не
# о том, что мы написали: на студийном сайте политика отрицала аналитику, пока
# хост вставлял счётчик на каждую страницу. Гейт сверяет три стороны — этот
# список, текст политики и адреса в собранной разметке — и краснеет на любом
# расхождении В ЛЮБУЮ СТОРОНУ: и на неназванном госте, и на названном госте,
# которого на страницах нет.
# (имя, хост, зачем, ставит ли куки)
THIRD_PARTIES = ()

# Реклама больше НЕ ФЛАГ. Гейт, стоявший внутри условия `if not rd.ADS`, был
# структурно неспособен покраснеть на той сборке, которая уезжает: сайт,
# живущий с рекламы, отгружался без единого места. Места теперь рисуются
# всегда, а сколько их и где — решает содержимое страницы.
#
# Место заводится только там, где есть что читать. Реклама на странице в
# 56 слов — это «недостаточно содержимого» в правилах сети, то есть риск на
# весь аккаунт, а он у нас один на все сайты.
AD_MIN_WORDS = 300
AD_MARK = "<!--bx-ad-flow-->"
# Пути, на которых рекламы не бывает никогда, сколько бы слов там ни было:
# страница ошибки (прямой запрет правил сети) и юридические страницы, где
# объявление рядом с текстом об ответственности выглядит ровно так, как оно
# выглядит.
AD_NEVER = ("/404.html", "/privacy/", "/terms/", "/contact/", "/about/")

MIN_FACTS = 3
# Окно описания в голове страницы. Верхняя граница — то, что помещается в
# сниппет; нижняя — порог, ниже которого описание перестаёт быть описанием.
DESC_MIN, DESC_MAX = 50, 158
TWIN_TEXT = 0.70        # по видимому тексту: то, что видят читатель и поиск
TWIN_SKELETON = 0.95    # по скелету фразы: ловит «тот же абзац, другое число»
MIN_HUB = 3

# ТРИ КОЛОНКИ ОТВЕТА — и число их печатается отсюда, а не словом. Это те же
# заголовки, что стоят в таблицах пар: «three questions in three separate
# columns» не сверялось ни с одной из них.
ANSWER_COLUMNS = ("Fit", "Voltage", "Chemistry")

# Объявление рекламных мест живёт РЯДОМ С РАСКЛАДКОЙ, потому что вопрос
# «влезает ли 728 px» — вопрос о ширине колонки, а её задаёт CSS. Одно имя,
# один источник.
AD_SLOTS = design.AD_SLOTS

esc, mm, volts, chem = P.esc, P.mm, P.volts, P.chem
QUOTE = P.QUOTE

ICON = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        "<rect width='32' height='32' rx='5' fill='%230d1114'/>"
        "<rect x='7' y='11' width='18' height='10' rx='2' fill='%23a13600'/>"
        "<rect x='25' y='14' width='3' height='4' fill='%23a13600'/>"
        "</svg>").replace("<", "%3C").replace(">", "%3E")

NAV = (("/", "Index"), ("/shells/", "Shells"), ("/sizes/", "Sizes"),
       ("/discontinued/", "Discontinued"), ("/codes/", "All codes"))

FOOT = (("/", "Index"), ("/codes/", "All codes"), ("/method/", "Method"),
        ("/about/", "About"), ("/privacy/", "Privacy"), ("/terms/", "Terms"),
        ("/contact/", "Contact"))

DISCLAIMER = (
    "BatteryCross is an independent reference. It is not affiliated with, "
    "endorsed by, or connected to any battery manufacturer or standards body. "
    "Figures are reproduced from published manufacturer data; the comparisons "
    "between them are ours. A cell that fits a compartment is not always a "
    "safe substitute.")


# ------------------------------------------------------------------ реклама

# СВОЯ ВРЕЗКА В РЕКЛАМНОМ МЕСТЕ. Набор страниц, а не набор слов: каждая
# строка ведёт на витрину, которая у сайта уже есть.
HOUSE_CAP = "From BatteryCross"

HOUSE_ADS = (
    # БЕЗ ЧИСЕЛ. Здесь стояли «215 кодов» и «125 обозначений» — величины,
    # набранные руками в тексте, который печатается на 155 страницах. Снимок
    # обновится, числа останутся, и никто их не сверит: гейт прозы поймал
    # это на первой же сборке.
    ("/codes/", "Every designation in one page",
     "Each code with what it measures and what it replaces"),
    ("/discontinued/", "The cell you found is not made any more",
     "What takes the place of each designation that stopped"),
    ("/method/", "Where these numbers come from",
     "The manufacturer's own datasheets, the parse rules, and what this "
     "site cannot tell you"),
    ("/data/latest.csv", "The whole snapshot, as one CSV",
     "Every measurement on the site in one file, with the date it was taken"),
)


def house_creative(path, n):
    """Место, в котором нечего показать, — это либо пустая серая коробка с
    подписью «Advertisement» (312 таких стояло на 156 страницах этого сайта),
    либо узел, спрятанный стилем, который всё равно остаётся ребёнком и
    ломает правила «последний теряет линию».

    Поэтому пока сеть не подключена, место занято НАШИМ, и подпись говорит,
    чьё это: выдать своё за оплаченное — обман, а объявить сайт недоделанным
    на каждой второй странице — приглашение рецензенту сети отказать.
    Решение не новое: keepsuntil и districtbyzip сделали так же, и этот сайт
    был единственным, кого оставили позади.

    Ссылка на страницу, где человек уже стоит, — петля, поэтому текущий адрес
    из набора вычёркивается.
    """
    pool = [x for x in HOUSE_ADS if x[0] != path]
    href, head, line = pool[n % len(pool)]
    return ('<a class="bx-house" href="%s">'
            '<span class="bx-ad-cap">%s</span>'
            '<span class="bx-house-h">%s</span>'
            '<span class="bx-house-s">%s</span></a>'
            % (href, esc(HOUSE_CAP), esc(head), esc(line)))


def ad_slot(cls, path, n=0):
    """Одно рекламное место — ВСЕГДА с содержимым внутри. Пустая коробка в
    разметке однажды сломала у нас пять правил отступов на 157 страницах:
    display:none не выводит узел из :last-child.

    Слово «Advertisement» печатается ВМЕСТЕ С РЕКЛАМОЙ и только с ней: оно
    обязательно, когда место оплачено, и бессмысленно, когда в нём наше.
    """
    nets = [x for x in THIRD_PARTIES if x[2] == "advertising"]
    if not nets:
        return '<div class="bx-ad %s">%s</div>' % (cls,
                                                   house_creative(path, n))
    return ('<div class="bx-ad %s"><span class="bx-ad-cap">Advertisement</span>'
            '<span class="bx-house-s">Served by %s</span></div>'
            % (cls, esc(nets[0][0])))


def visible_words(html):
    """Слова, которые увидит читатель. Стиль и скрипт вычищаются ВМЕСТЕ:
    иначе «text-align:right» считается словом «right», а их 973."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                  flags=re.S)
    return P.wc(body)


def carries_ads(path, body):
    """Заводится ли на этой странице инвентарь. Считается ПО СОДЕРЖИМОМУ, а не
    по типу страницы: витрина оболочки в 137 слов и страница элемента в 900
    отличаются не типом, а тем, есть ли рядом с объявлением что читать."""
    if path in AD_NEVER:
        return False
    return visible_words(body) >= AD_MIN_WORDS


def place_flow_ad(body, path):
    """Объявление в потоке НИКОГДА не стоит выше ответа.

    Место встаёт по метке AD_MARK, а если разметчик её не поставил — после
    первой секции. Дописывание в начало превращало бы первый экран в рекламу
    на сайте, куда приходят за ответом.
    """
    slot = ad_slot("bx-ad-flow", path, 0)
    if AD_MARK in body:
        return body.replace(AD_MARK, slot, 1)
    i = body.find("</section>")
    if i >= 0:
        j = i + len("</section>")
        return body[:j] + slot + body[j:]
    return body + slot


# ------------------------------------ карточка ссылки и структурные данные

def unesc(s):
    """Обратно из разметки в текст. Порядок не случаен: «&amp;» разбирается
    ПОСЛЕДНИМ, иначе «&amp;lt;» распустилось бы дважды."""
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", P.QUOTE),
                 ("&mdash;", chr(8212)), ("&ndash;", chr(8211)),
                 ("&rsquo;", chr(8217)), ("&middot;", chr(183)),
                 ("&nbsp;", " "), ("&amp;", "&")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def share_meta(path, title, desc):
    """Карточка ссылки. Заголовок и описание — ТЕ ЖЕ, что в голове страницы:
    два места, где написано одно и то же, расходятся, а одно не может.

    Картинки НЕТ и она не выдумывается. Растровых изображений на сайте ноль,
    а `og:image`, указывающий на SVG, большинство площадок не разворачивает
    вовсе. Карточка `summary` — та, которая у нас на самом деле есть.
    """
    url = "https://%s%s" % (DOMAIN, path)
    out = ""
    for k, v in (("og:type", "website"), ("og:site_name", SITE),
                 ("og:title", title), ("og:description", desc),
                 ("og:url", url), ("og:locale", "en_US")):
        out += '<meta property="%s" content="%s">\n' % (k, esc(v))
    for k, v in (("twitter:card", "summary"), ("twitter:title", title),
                 ("twitter:description", desc)):
        out += '<meta name="%s" content="%s">\n' % (k, esc(v))
    return out


# Типы, которые сайт имеет право объявить. Всё, чего в списке нет, гейт
# считает выдумкой: рейтинги, авторы и даты, которых у сайта нет, в разметку
# не попадают именно потому, что попасть им неоткуда.
LD_TYPES = ("Organization", "WebSite", "BreadcrumbList", "ListItem",
            "Product", "PropertyValue")


def ld_json(nodes):
    """Блок структурных данных. Инертный текст, а не код: браузер его не
    исполняет и никуда за ним не идёт (`@context` — идентификатор словаря, а
    не адрес загрузки). Знак «<» пишется экранированной формой, иначе из
    блока данных можно было бы выйти раньше времени."""
    if not nodes:
        return ""
    txt = json.dumps(nodes, ensure_ascii=True, separators=(",", ":"),
                     sort_keys=False)
    txt = txt.replace("<", chr(92) + "u003c")
    return '<script type="application/ld+json">%s</script>\n' % txt


def crumb_ld(path, body):
    """Цепочка — из ВИДИМОЙ цепочки на самой странице, а не собранная рядом
    второй раз. Разметка, утверждающая путь, которого читатель не видит, —
    ровно то расхождение, за которое снимают расширенный сниппет."""
    m = re.search(r'<p class="bx-crumb">(.*?)</p>', body, re.S)
    if not m:
        return None
    inner, items, pos = m.group(1), [], 0
    for a in re.finditer(r'<a href="([^"]*)">(.*?)</a>', inner):
        items.append((unesc(re.sub(r"<[^>]+>", " ", a.group(2))), a.group(1)))
        pos = a.end()
    tail = re.sub(r"^\s*/\s*", "", unesc(re.sub(r"<[^>]+>", " ", inner[pos:])))
    if tail:
        items.append((tail, path))
    if len(items) < 2:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n,
                 "item": "https://%s%s" % (DOMAIN, u)}
                for i, (n, u) in enumerate(items)]}


def product_ld(cell, s, path, desc):
    """Величины элемента машине — РОВНО те, что напечатаны человеку.

    Каждое значение печатается тем же принтером, что и ячейка таблицы, и гейт
    ищет его в видимом тексте страницы. Ни рейтинга, ни автора, ни цены, ни
    изготовителя: обозначение принадлежит стандарту, а не заводу, и придумать
    здесь бренд означало бы соврать в машиночитаемом виде.
    """
    props = []

    def prop(name, value, unit=None):
        if value in (None, "", P.NOT_PUBLISHED):
            return
        d = {"@type": "PropertyValue", "name": name, "value": value}
        if unit:
            d["unitText"] = unit
        props.append(d)

    form = (s["shell"] or ("none",))[0]
    if form == "round":
        prop("Diameter", mm(cell.get("diameter")), "mm")
    else:
        prop("Length", mm(cell.get("length")), "mm")
        prop("Width", mm(cell.get("width")), "mm")
    prop("Height", mm(cell.get("height")), "mm")
    if cell.get("volts"):
        # То же число и тем же способом, что в полосе величин: «3», а не «3 V».
        # Единица объявлена отдельным полем, и печатать её дважды значило бы
        # получить «3 V V» в машиночитаемом виде.
        prop("Nominal voltage",
             ("%.2f" % cell["volts"]).rstrip("0").rstrip("."), "V")
    if cell.get("mah"):
        prop("Capacity", mm(cell["mah"]), "mAh")
    prop("Chemistry", chem(cell))
    prop("In the Energizer catalog", "Listed" if cell["active"]
         else "Not listed")
    node = {"@context": "https://schema.org", "@type": "Product",
            "name": cell["code"],
            "description": desc,
            "url": "https://%s%s" % (DOMAIN, path),
            "additionalProperty": props}
    if cell.get("aliases"):
        node["alternateName"] = list(cell["aliases"])
    return node


def site_ld(desc):
    """Издатель и сайт — на главной и только там. У издателя напечатаны имя и
    адрес почты, которые стоят в подвале КАЖДОЙ страницы, и ссылка на
    методику; адреса самой компании здесь нет, потому что сайты этой ветки на
    неё не ссылаются."""
    pub = "https://%s/#publisher" % DOMAIN
    return [
        {"@context": "https://schema.org", "@type": "Organization",
         # Имя, которое видит человек, и имя юрлица — разные поля.
         # Гейт «структурные данные совпадают с видимым» поймал это
         # сразу: имя в разметке было «BiLingoPlus LLC», а глазами
         # его на странице больше нет. schema.org для того и держит
         # legalName отдельно от name.
         "@id": pub, "name": SITE, "legalName": PUBLISHER,
         "email": CONTACT,
         "publishingPrinciples": "https://%s/method/" % DOMAIN},
        {"@context": "https://schema.org", "@type": "WebSite",
         "@id": "https://%s/#website" % DOMAIN, "name": SITE,
         "url": "https://%s/" % DOMAIN, "inLanguage": "en-US",
         "description": desc, "publisher": {"@id": pub}},
    ]


def slug(cell):
    return C.slug(cell)


link_to, shell_slug = C.link_to, C.shell_slug


def size_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


# ------------------------------------------------------------------ оболочка

def shell_html(path, title, desc, body, side="", index=True, ptype="page",
               ld=None):
    # Текущая страница в навигации — не ссылка, а метка. Так человек видит,
    # где он, и не нажимает туда, где уже стоит.
    def _nav(items):
        out = ""
        for h, label in items:
            if h == path:
                out += ('<span class="bx-here" aria-current="page">%s</span>'
                        % esc(label))
            else:
                out += '<a href="%s">%s</a>' % (h, esc(label))
        return out

    nav, foot = _nav(NAV), _nav(FOOT)
    # На главной логотип — не ссылка на главную.
    brand = ('<span class="bx-brand">BATTERYCROSS</span>' if path == "/"
             else '<a class="bx-brand" href="/">BATTERYCROSS</a>')
    robots = ("index, follow, max-image-preview:large" if index
              else "noindex, follow")
    sc = "<script>%s</script>" % FINDER
    # Цепочка читается ДО вставки места: объявление в потоке не имеет к ней
    # отношения, и порядок не должен на неё влиять.
    nodes = list(ld or [])
    cr = crumb_ld(path, body)
    if cr:
        nodes.append(cr)
    # ИНВЕНТАРЬ ЗАВОДИТСЯ ЗДЕСЬ — на общем пути ВСЕХ страниц, и решает его
    # СОДЕРЖИМОЕ, а не тип. Пока решение стояло внутри сборщика страницы
    # элемента, тридцать страниц — витрины, указатель, главная, методика —
    # не несли ни одного места вовсе, а оба рекламных гейта были зелёные.
    # Число слов считается ДО вставки: собственные слова объявления не могут
    # оправдывать его присутствие.
    if carries_ads(path, body):
        body = place_flow_ad(body, path)
        # Второе место на странице показывает ДРУГУЮ врезку: две одинаковые
        # на одном экране — это одно объявление, напечатанное дважды.
        side += ad_slot("bx-ad-tower", path, 1)
    else:
        # Метка без места — просто комментарий; убираем, чтобы в отгруженной
        # разметке не оставалось следов несуществующего инвентаря.
        body = body.replace(AD_MARK, "")
    # ГЛАВНОЕ ДЕЙСТВИЕ САЙТА — на КАЖДОЙ странице, и решается это ЗДЕСЬ, на
    # общем пути: поле стояло на двух страницах из 164, и обе — не те, на
    # которые приводит выдача. Ставится ПОСЛЕ рекламы, потому что собственные
    # слова поля не имеют права оправдывать место под объявление, ровно как
    # собственный текст коробки.
    if 'id="bx-find"' not in body:
        i = body.find("<h1")
        fh = finder_html(here=path)
        body = (body[:i] + fh + body[i:]) if i >= 0 else fh + body
    body += SEARCH_BLOCK
    cols = ('<div class="bx-cols"><div class="bx-main">%s</div>'
            '<aside class="bx-side">%s</aside></div>' % (body, side)
            if side else '<div class="bx-main">%s</div>' % body)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="robots" content="%(robots)s">
<meta name="page-type" content="%(ptype)s">
<link rel="canonical" href="https://%(domain)s%(path)s">
%(share)s%(ld)s
<link rel="icon" href="data:image/svg+xml,%(icon)s">
<style>%(css)s</style>
</head>
<body>
<a class="bx-skip" href="#main">Skip to the content</a>
<header class="bx-mast"><div class="bx-mast-in"><div class="bx-top">
%(brand)s
<span class="bx-strap">Cell cross-reference, drawn to size</span>
<nav class="bx-nav" aria-label="Main">%(nav)s</nav>
</div></div></header>
<div class="bx-wrap" id="main">
%(cols)s
</div>
<footer class="bx-foot"><div class="bx-foot-in">
<p>%(disc)s</p>
<nav aria-label="Site information">%(foot)s</nav>
<p>&copy; %(year)d %(owner)s &middot; <!--email_off--><a href="mailto:%(mail)s">%(mail)s</a><!--/email_off-->
&middot; Data: %(vintage)s</p>
</div></footer>%(sc)s
</body>
</html>
""" % {"title": esc(title), "desc": esc(desc), "domain": DOMAIN, "path": path,
       "icon": ICON, "css": design.strip_comments(
           design.CSS + design.AD_CSS), "cols": cols, "disc": esc(DISCLAIMER),
       "nav": nav, "foot": foot, "brand": brand, "year": CONTENT_DATE.year, "pub": PUBLISHER, "owner": FOOT_NAME,
       "mail": CONTACT, "vintage": esc(DATA_VINTAGE), "robots": robots,
       "ptype": ptype, "sc": sc, "share": share_meta(path, title, desc),
       "ld": ld_json(nodes)}


# --------------------------------------------------------------- части страницы

def strip_block(cell, s):
    """Полоса величин: то, за чем пришли, крупно и в одну строку."""
    cells = []

    def box(k, v, unit=""):
        cells.append('<div class="bx-cellv"><span class="bx-k">%s</span>'
                     '<span class="bx-val">%s</span>'
                     '<span class="bx-unit">%s</span></div>'
                     % (esc(k), esc(v), esc(unit)))

    if cell.get("volts"):
        # Шкала УШЛА ИЗ ЯЧЕЙКИ полосы: в колонке шириной 140 px дорожка была
        # серым обрубком в 10 px высотой, на котором никакое положение штриха
        # ничего не значило, и число рядом читалось первым. Теперь она стоит
        # под полосой во всю ширину колонки.
        cells.append('<div class="bx-cellv"><span class="bx-k">Nominal</span>'
                     '<span class="bx-val">%s</span>'
                     '<span class="bx-unit">V</span></div>'
                     % ("%.2f" % cell["volts"]).rstrip("0").rstrip("."))
    if s["shell"] and s["shell"][0] == "round":
        box("Diameter", mm(cell.get("diameter")), "mm")
        box("Height", mm(cell.get("height")), "mm")
    elif s["shell"]:
        box("Footprint", "%s x %s" % (mm(cell.get("length")),
                                      mm(cell.get("width"))), "mm")
        box("Height", mm(cell.get("height")), "mm")
    if cell.get("mah"):
        box("Capacity", mm(cell["mah"]), "mAh")
    # Формулировка ровно та, что мы знаем: каталог у нас ОДНОГО изготовителя,
    # и его поле status говорит про его номер изделия, а не про судьбу
    # обозначения в мире. «Discontinued» однажды объявило снятой обычную
    # «Крону» на 9 В, которая лежит в каждом киоске.
    cells.append('<div class="bx-cellv"><span class="bx-k">In the Energizer '
                 'catalog</span><span class="bx-state %s">%s</span></div>'
                 % ("bx-state-on" if cell["active"] else "bx-state-off",
                    "Listed" if cell["active"] else "Not listed"))
    return '<div class="bx-strip">%s</div>' % "".join(cells)


def _axis_end(pct):
    """Подпись конца дорожки, ВЫВЕДЕННАЯ из величины этого конца.

    Слева ноль вольт (-100% от номинала), справа кратность: +1000% это
    вдесятеро выше. Оба конца задаются C.V_AXIS_*, и обе подписи считаются
    отсюда — иначе правка величины двигает штрих и оставляет слово.
    """
    txt = ("&minus;" if pct < 0 else "+") + P.pct_num(abs(pct)) + "%"
    if pct < 0:
        return txt + ", no volts at all"
    # «Вдесятеро сверх» — это САМ процент, делённый на сто: +1000% значит
    # на десять раз БОЛЬШЕ, а не одиннадцать раз всего. Направление у
    # кратности такое же спрашиваемое, как у знака процента.
    return "%s, %s times over" % (txt, P.mm(pct / 100.0))


def voltage_scale(cell, s):
    """Шкала напряжения: отклонение видно ПОЛОЖЕНИЕМ раньше, чем прочитано.

    Ось АБСОЛЮТНАЯ и одна на весь сайт: центр — этот элемент, влево ниже,
    вправо выше, ядро линейно до КРАЯ КЛАССА (-20% вниз, +25% вверх — это
    один и тот же разрыв в 20% большего номинала, отсчитанный от разных
    чисел), дальше логарифм до концов оси (ноль вольт слева, вдесятеро
    больше справа). Место штриха считает cells.scale_position, то есть та же
    величина, которая печатается в таблице процентом.

    Прежняя шкала нормировалась на min и max НАБОРА САМОЙ СТРАНИЦЫ: полоса
    занимала всю дорожку на всех 57 страницах, 133 штриха из 160 стояли ровно
    на 0% или 100%, и разница в 3% рисовалась той же парой отметок, что
    разница в 700%.
    """
    v = cell.get("volts")
    # В шкалу входит только то, что ВЛЕЗАЕТ в это гнездо: с «too tall» она
    # растягивалась втрое и прятала ровно то различие, ради которого есть.
    # Соседи с ТЕМ ЖЕ напряжением штриха не получают: он встал бы ровно под
    # штрихом этого элемента и не сообщил бы ничего.
    peers = sorted({r["cell"]["volts"] for r in s["reps"]
                    if r["fit"] in ("drop-in", "shorter")
                    and r["cell"].get("volts")})
    if not v:
        return ""
    others = [pv for pv in peers if abs(pv - v) > 1e-9]
    if not others:
        return ""
    pins = ""
    marks, pcts = [], []
    for pv in others:
        r = C.signed_ratio(v, pv)
        pins += ('<span class="bx-scale-pin bx-scale-pin-off" '
                 'style="left:%.1f%%"></span>' % C.scale_position(r))
        marks.append("%s at %s" % (P.volts_num(pv),
                                   P.pct_signed(C.signed_pct(r))))
        pcts.append(C.signed_pct(r))
    # Края зоны — У ФУНКЦИИ КЛАССА, а не набраны как +-V_SERIOUS_PCT.
    # Мера класса симметрична по ПАРЕ, а не по этому элементу: вниз граница
    # приходится на -20%, вверх на +25%, и пока зона рисовалась симметрично,
    # штрих +25.0% стоял ВНЕ полосы с меткой «reads off» рядом.
    lo = C.scale_position(C.class_edge(-1))
    hi = C.scale_position(C.class_edge(1))
    # Ветвление по ФОРМЕ данных: где отметка одна, «две не совпадут» — не
    # утверждение, а шаблон с подставленным числом.
    # Крайние отметки берутся СО ЗНАКОМ: у -3,3% и +3,3% модуль один, а места
    # на дорожке разные, и «две не совпадут» — про места, а не про модули.
    near, far = min(pcts), max(pcts)
    if far - near > 0.05:
        proof = ("so the %s mark and the %s mark on this track cannot land in "
                 "the same place." % (P.pct_signed(near), P.pct_signed(far)))
    else:
        proof = ("so %s puts the mark in one place here and in the same place "
                 "on every other page of this site."
                 % P.pct_signed(far))
    # «Входит в отсек», а не «подходит»: набор шкалы — то, что влезает,
    # а влезает и то, что стоит ниже контакта. Слово «подходит» на этом
    # сайте обещает больше, чем мы проверили.
    return ('<div class="bx-scale-v" role="img" aria-label="How far each cell '
            'that enters this compartment sits from this one at %s: %s">'
            '<span class="bx-scale-cap">How far each cell that enters this '
            'compartment sits from this one&rsquo;s %s</span>'
            '<div class="bx-scale-track">'
            '<span class="bx-scale-band" style="left:%.1f%%;right:%.1f%%">'
            '</span>%s'
            '<span class="bx-scale-pin" style="left:%.1f%%"></span></div>'
            '<div class="bx-scale-ends"><span>%s</span>'
            '<span>this cell</span><span>%s</span></div>'
            '<p class="bx-scale-note">The axis is the difference from this '
            'cell, not a range of volts: the centre is %s and the ruled '
            'middle is the class where a substitute still runs and only '
            'reads off &mdash; a gap within %s%% of the higher of the two '
            'nominals, which counted from this cell reaches %s%% below and '
            '%s%% above. One gap, two readings: the other cell&rsquo;s page '
            'prints the other figure for this same pair and lands on the '
            'same class. Outside those two rules the class changes. The '
            'middle is drawn straight and the outer fifth of each side is '
            'compressed, %s</p></div>'
            % (P.volts_num(v), P.esc(P.listing(marks)), P.volts_num(v),
               lo, 100.0 - hi, pins, C.scale_position(0.0),
               # Концы дорожки были набраны руками рядом с C.V_AXIS_LOW_PCT и
               # C.V_AXIS_HIGH_PCT, которые эти же концы и задают: подпись,
               # не выведенная из величины, переживёт её правку.
               _axis_end(C.V_AXIS_LOW_PCT), _axis_end(C.V_AXIS_HIGH_PCT),
               P.volts_num(v), P.pct_num(C.V_SERIOUS_PCT),
               P.pct_num(C.V_SERIOUS_PCT),
               P.pct_num(abs(C.class_edge(1)) * 100.0), proof))


def draw_legend():
    """Ключ к условным знакам ЧЕРТЕЖА, и стоит он внутри чертежа.

    Прежде это была карточка «How to read this page» в боковой колонке, и
    там она была неверна дважды. На широком экране она стояла на 96-м
    пикселе — то есть ЛЕГЕНДА ПЕРЕД ТЕМ, ЧТО ОБЪЯСНЯЕТ. На телефоне
    боковая колонка становится хвостом одноколоночной сетки, и замер дал
    её на 4491-м пикселе страницы высотой 5210: ключ к сплошному и
    пунктирному силуэту приезжал ПОСЛЕ всех силуэтов, которые объясняет.
    А на десяти витринах типоразмеров чертежа нет вовсе, и легенда
    объясняла там знаки, которых на странице нет ни одного.

    Слов здесь ровно столько, сколько нужно на подпись: длинный общий
    текст, побайтово одинаковый на 130 страницах, — это близнец, а обе
    метрики сходства считаются по всей основной колонке.
    """
    rows = [("bx-swatch-solid", "This cell"),
            ("bx-swatch-dashed", "Another cell, same scale")]
    return ('<div class="bx-key">%s</div>'
            % "".join('<span class="bx-swatch %s"></span><span>%s</span>'
                      % (c, esc(a)) for c, a in rows))


def drawing_block(cell, s, cs):
    """Чертежи: сам элемент и семья габарита в ОДНОМ масштабе."""
    one = draw.cell_drawing(cell)
    if not one:
        return ""
    out = ('<h2>Drawn to scale</h2>'
           '<div class="bx-fig">%s<p class="bx-cap">%s, side elevation, '
           'from the published figures</p></div>' % (one, esc(cell["code"])))
    kin = s["family"] + [c for c in s["siblings"] if c not in s["family"]]
    fam = draw.family_drawing(cell, kin) if kin else ""
    if fam:
        out += ('<div class="bx-fig">%s<p class="bx-cap">The same scale for '
                'all of them. The dashed line marks the height of %s: a '
                'silhouette that stops short of it will not reach the '
                'contact, one that crosses it will not let the cover '
                'close.</p>%s</div>' % (fam, esc(cell["code"]), draw_legend()))
    return out


def shell_card(cell, s):
    kin = s["family"]
    if not kin:
        return ""
    li = "".join('<li><a href="%s">%s</a> &mdash; %s</li>'
                 % (link_to(c), esc(c["code"]), volts(c)) for c in kin[:8])
    sl = shell_slug(s["shell"])
    # Ссылка на хаб только если хаб есть: у оболочки с двумя жильцами страницы
    # не заводится, и ссылка на неё была бы тупиком.
    more = ('<p class="bx-cap"><a href="/shell/%s/">All %d in this shell</a></p>'
            % (sl, len(kin) + 1)) if sl and sl in C.SHELL_HUBS else ""
    return ('<div class="bx-card"><h3>In this shell</h3>'
            '<ul class="bx-nb" role="list">%s</ul>%s</div>' % (li, more))


def page_desc(cell, s):
    """Описание страницы СЧИТАЕТСЯ по её собственным величинам.

    Сто двадцать пять описаний были одним и тем же предложением, в котором
    менялся только код. Поиск такое переписывает — то есть сниппет на большей
    части корпуса перестаёт быть нашим. В описание идёт ровно то, за чем
    человек пришёл: габарит, напряжение и ближайшая замена с её последствием,
    и всё это ветвится по ФОРМЕ данных, а не по типу страницы.
    """
    code = cell["code"]
    alias = (cell.get("aliases") or [None])[0]
    ident = "%s (%s)" % (code, alias) if alias else code
    parts = [ident]
    if C.shell_label(s["shell"]):
        parts.append(C.shell_label(s["shell"]))
    if cell.get("volts"):
        parts.append(volts(cell))
    head = ", ".join(parts)
    if not cell["active"]:
        head += ", no longer in the Energizer catalog"

    same = [d for d in s["dropin"] if d["volt"]
            and C.consequence_class(d["volt"]["ratio"]) == "same"]
    b = s["best"]
    if same:
        names = [d["cell"]["code"] for d in same[:2]]
        tail = ("%s %s into the same slot at the same voltage."
                % (P.listing(names), P.verb(len(names), "drop")))
    elif s["dropin"]:
        d = s["dropin"][0]
        cost = (P.v_short(C.signed_pct(d["volt"]["ratio"])) if d["volt"]
                else "a voltage the maker does not publish")
        tail = ("%s enters the same slot at %s, %s."
                % (d["cell"]["code"], volts(d["cell"]), cost))
    elif b:
        tail = ("Nothing Energizer still lists drops straight in; the closest "
                "is %s, %s mm tall against %s."
                % (b["cell"]["code"], mm(b["cell"].get("height")),
                   mm(cell.get("height"))))
    else:
        tail = "Nothing Energizer still lists shares this envelope."
    desc = "%s. %s" % (head, tail)
    if len(desc) > DESC_MAX:
        desc = "%s. %s" % (head, tail.split(";")[0].rstrip(".") + ".")
    while len(desc) > DESC_MAX and " " in desc:
        desc = desc[:desc.rindex(" ")].rstrip(" ,;") + "."
    if len(desc) < DESC_MIN:
        desc += " Every published figure, drawn to size."
    return desc


def product_page(cell, s, cs, hubs):
    code = cell["code"]
    alias = (cell.get("aliases") or [None])[0]
    head = "%s%s — %s, %s" % (code, (" (%s)" % alias) if alias else "",
                              C.shell_label(s["shell"]) or "size unpublished",
                              volts(cell))
    if len(head) > 60:
        head = "%s — %s, %s" % (code, C.shell_label(s["shell"]) or "cell",
                                volts(cell))
    if len(head) > 60:
        head = "%s — %s cell" % (code, chem(cell))
    desc = page_desc(cell, s)
    crumb = '<p class="bx-crumb"><a href="/">Index</a>'
    sl = shell_slug(s["shell"])
    if sl and sl in hubs:
        crumb += ' / <a href="/shell/%s/">Shell %s</a>' % (
            sl, esc(C.shell_label(s["shell"])))
    crumb += " / %s</p>" % esc(code)
    body = (crumb + "<h1>%s</h1>" % esc(code)
            # ОТВЕТ РАНЬШЕ СПРАВОЧНЫХ ВЕЛИЧИН, и «раньше» значит РАНЬШЕ ВСЕГО.
            # Замер в браузере на собранной странице: таблица замен начиналась
            # на 912-м пикселе при экране 1024x800 и на 1061-м при 375x667 —
            # полтора экрана прокрутки до того, ради чего сайт существует.
            # Выше неё стояли: список чужих маркировок этого элемента, полоса
            # характеристик ТОГО ЖЕ элемента, шкала напряжения и целый раздел
            # прозы. Всё это — про элемент, который у человека УЖЕ В РУКЕ.
            # Теперь под заголовком стоит фраза-ответ, а сразу за ней таблица;
            # справочные величины начинаются ниже.
            + P.headline_block(cell, s)
            # ПЛАШКА ОПАСНОСТИ — ВЫШЕ ТАБЛИЦЫ ЗАМЕН, и это её единственное
            # верное место. Первая попытка поставила её после fit_block —
            # то есть ПОСЛЕ таблицы, — и вышло ровно то, на что смотреть
            # больно: страница /lr44/ печатает «SR44 drops straight in» на
            # 3,3% высоты, а предупреждение стояло на 9,4%, ниже сгиба. На
            # 2 934 словах этой страницы слов hazard, swallow, danger, warn,
            # child и poison не было НИ ОДНОГО.
            #   Выше плашки стоит только ответ одной фразой — то, ради чего
            # человек пришёл. Ниже — всё остальное.
            + D.hazard_block(cell, s, cs)
            + P.fit_block(cell, s)
            + ('<p class="bx-also">Also stamped %s</p>'
               % esc(", ".join(cell["aliases"])) if cell.get("aliases")
               else "")
            + strip_block(cell, s)
            + voltage_scale(cell, s)
            + P.difference_block(cell, s)
            + P.replaces_block(cell, s, cs)
            + P.chemistry_block(cell, s)
            # МЕСТО В ПОТОКЕ — ЗДЕСЬ, и ни строкой выше. Всё, ради чего
            # человек пришёл, уже прочитано: чем заменить, что это стоит по
            # напряжению и какая химия. Ниже начинается справочная часть —
            # чертёж, таблица, ранг. Объявление, вставленное дописыванием в
            # конец, стояло под блоком методики и не стоило ничего.
            + AD_MARK
            # ВО ЧТО ЭТО СТАВЯТ — сразу за ответом и ВЫШЕ справочной части:
            # «где неверная замена действительно вредит» человек читает не
            # после таблицы импеданса. Два случая, ради которых блок и
            # заведён, — дымовой извещатель на «Кроне» и проглоченный
            # литиевый диск — на сайте не упоминались ни разу.
            + D.duty_block(cell, s, cs)
            + drawing_block(cell, s, cs)
            + P.table_block(cell, s)
            + D.figures_block(cell, s, cs)
            + P.rank_block(cell, s)
            + D.place_block(cell, s, cs)
            + D.markings_block(cell, s, cs)
            + D.mistaken_block(cell, s, cs)
            + D.gaps_block(cell, s, cs)
            + P.applies_block()
            + P.neighbours_block(cell, s, cs)
            + P.method_block(DATA_VINTAGE)
            # ИСТОЧНИКИ ПОСЛЕДНИМИ и с номерами. Сайт печатал «Source:
            # Energizer technical data» 166 раз и не давал проверить ни одну
            # цифру: ноль внешних адресов на весь корпус.
            + D.sources_block(cell, s, cs, DATA_VINTAGE)
            + embed_offer(cell))
    side = shell_card(cell, s)
    path = "/%s/" % slug(cell)
    return shell_html(path, head, desc, body, side=side, ptype="cell",
                      ld=[product_ld(cell, s, path, desc)])


# ------------------------------------------------------------------- витрины

def rank_table(rows, head=("Cell", "Detail"), here=None, anchor=None):
    """Таблица витрины. Снятая с производства строка помечена КЛАССОМ, а не
    только словом в ячейке: состояние читается раньше, чем текст.

    `here` — адрес страницы, на которой таблица стоит. Ссылка на самоё себя
    это петля: человек нажимает и остаётся на месте без единого слова. Петля
    хуже отсутствия ссылки, потому что отсутствие хотя бы честно.
    """
    th = "".join("<th>%s</th>" % esc(h) for h in head)
    body = ""
    for row in rows:
        sl, code, cols = row[0], row[1], row[2]
        gone = any(str(c).strip() == "Not listed" for c in cols)
        href = sl if sl.startswith("/") else "/%s/" % sl
        name = (esc(code) if href == here
                else '<a href="%s">%s</a>' % (href, esc(code)))
        # Якорь на строку: поиск с любой другой страницы ведёт человека не
        # «куда-то в витрину», а к своему коду, рядом с которым уже назван
        # ближайший текущий элемент.
        rid = (' id="%s%s"' % (anchor, _index_key(code))) if anchor else ""
        body += ('<tr%s%s><th>%s</th>%s</tr>'
                 % (rid, ' class="bx-gone"' if gone else "", name,
                    "".join("<td>%s</td>" % c for c in cols)))
    return ('<div class="bx-tw"><table><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></div>' % (th, body))


def cell_row(c, s=None):
    """Строка витрины. Адрес — через общую функцию разрешения: у элемента без
    своей страницы ссылка ведёт на его оболочку, а не в никуда."""
    # esc(None) возвращал непустую строку «None», она истинна, и «or mdash»
    # не срабатывал никогда. Проверяем САМУ величину, а не её экранирование.
    lab = C.shell_label(C.shell(c))
    return (link_to(c), c["code"],
            [(esc(lab) if lab else "&mdash;"), volts(c),
             esc(chem(c)),
             "Listed" if c["active"] else "Not listed"])


def shell_gone_block(members, live, gone, here=None):
    """Чем закрыть отсек, для которого обозначение снято.

    Прежде здесь стояла одна фраза на все случаи: «anything else in this table
    is the same size, and the voltage column says what the swap costs». Для
    цинк-воздушного PR44 это неправда: его цена в часах — не 6,9% вольта, а
    то, что он начинает разряжаться, как только снята наклейка, и задыхается в
    закрытом отсеке. Одна рамка оговорки на случаи, последствия которых
    несопоставимы, — ровно то, из-за чего у нас уже выходило «все тоньше,
    подложите прокладку» там, где всё было выше.

    Теперь строка на КАЖДЫЙ выпускаемый элемент оболочки: отклонение
    напряжения от снятого — из тех же двух функций, что и на страницах
    элементов, и отдельным столбцом то, чего проценты не выражают.
    """
    if not gone:
        return ""
    ref = gone[0]
    intro = ("%s of the %s here %s no longer listed by Energizer: %s."
             % (P.plural(len(gone), "designation"), len(members),
                "is" if len(gone) == 1 else "are",
                esc(P.listing([c["code"] for c in gone[:6]]))))
    if not live:
        return ("<h2>What is gone from this shell</h2><p>%s Energizer lists "
                "nothing else in this envelope at all, so the compartment has "
                "no answer in this catalog &mdash; which is a statement about "
                "the catalog, not about the world.</p>" % intro)
    if len(gone) > 1:
        intro += (" The table below measures each still-listed cell against "
                  "%s; the others carry their own figures on their own pages."
                  % esc(ref["code"]))
    else:
        intro += (" The compartment is the same size for the rest, and that "
                  "is the only thing the size settles.")
    rows = ""
    for c in live:
        v = C.voltage_gap(ref, c)
        cav = P.caveat_words(C.chemistry_caveat(ref, c))
        if cav:
            other = cav[0].upper() + cav[1:]
        elif chem(c) != chem(ref):
            other = ("%s rather than %s, so it empties along a different "
                     "curve" % (chem(c), chem(ref)))
            other = other[0].upper() + other[1:]
        else:
            other = ("Same chemistry, so the voltage column is the whole "
                     "difference")
        href = C.link_to(c)
        # У элемента без своей страницы адрес ведёт на его оболочку — а
        # таблица стоит как раз на ней. Петля хуже отсутствия ссылки.
        name = (esc(c["code"]) if href == here
                else '<a href="%s">%s</a>' % (href, esc(c["code"])))
        rows += ('<tr><th>%s</th>'
                 '<td class="bx-v bx-v-%s">%s %s<span class="bx-vtag">%s'
                 '</span></td><td>%s</td></tr>'
                 % (name,
                    (v["class"] if v else "unknown"), volts(c),
                    P.pct_signed(v["pct"]) if v else "&mdash;",
                    P.V_TAG.get(v["class"], "unknown") if v else "unknown",
                    esc(other)))
    return ('<h2>What is gone from this shell</h2><p>%s</p>'
            '<p class="bx-legend">Fit answers whether it enters the '
            'compartment; every cell here shares the envelope, so fit is '
            'already settled. Voltage answers whether the circuit will '
            'notice, and chemistry answers what the voltage column cannot '
            'say. %s</p>'
            # НЕ bx-fits: в этой таблице нет столбца посадки (её решает
            # сама оболочка), а bx-fits запрещает перенос в ячейке — третий
            # столбец здесь предложение, а не слово.
            '<div class="bx-tw"><table><thead><tr>'
            '<th>Still listed</th><th>Voltage against %s</th>'
            '<th>What the percentage does not say</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            % (intro, P.SUBSTITUTE_CAVEAT, esc(ref["code"]), rows))


def shell_lead(members, live, gone, vs):
    """Подводка витрины оболочки: рамка по ФОРМЕ данных плюс факт, которого
    нет ни на одной другой витрине.

    Один шаблон на все витрины делал их близнецами — страницы «C» и «D»
    совпадали слово в слово. Гейт близнецов их не видел, потому что смотрел
    только на страницы элементов; теперь смотрит на все типы, и подводка
    обязана нести СВОЁ.
    """
    n = P.plural(len(members), "designation")
    chems = sorted({chem(c) for c in members})
    mah = sorted(((c["mah"], c) for c in members if c.get("mah")),
                 key=lambda x: (x[0], x[1]["code"]))
    byv = sorted([c for c in members if c.get("volts")],
                 key=lambda c: c["volts"])
    vlist = P.listing(["%s V" % ("%.2f" % v).rstrip("0").rstrip(".")
                       for v in vs])

    # Первая фраза — рамка: она отвечает на вопрос, который у ЭТОЙ оболочки
    # главный.
    if len(vs) >= 2:
        lo, hi = byv[0], byv[-1]
        head = ("%s carry this exact envelope and they disagree on voltage: "
                "%s runs %s where %s runs %s, %s%% apart. The compartment "
                "cannot tell them apart and the circuit can."
                % (n, esc(lo["code"]), volts(lo), esc(hi["code"]), volts(hi),
                   P.pct_num(C.gap_pct(lo["volts"], hi["volts"]))))
    elif len(chems) >= 3:
        head = ("%s carry this exact envelope at %s, and the insides differ "
                "%s ways: %s. Same hole, same nominal volts, different "
                "behaviour as they empty."
                % (n, vlist, len(chems), P.listing(chems)))
    elif gone and not live:
        head = ("%s carry this exact envelope at %s and Energizer lists none "
                "of them now: %s. Compartments outlive catalogs, which is "
                "why the page is here."
                % (n, vlist, P.listing([c["code"] for c in members[:4]])))
    elif gone:
        head = ("%s carry this exact envelope at %s, and %s of them %s gone "
                "from the catalog: %s. What is left fits the same opening."
                % (n, vlist, len(gone), P.verb(len(gone), "are"),
                   P.listing([c["code"] for c in gone[:3]])))
    elif len(chems) == 2:
        # Число химий стояло словом внутри ветки, которая его же и считает.
        head = ("%s carry this exact envelope at %s in %s, %s. "
                "The opening does not choose between them; the discharge "
                "curve does."
                % (n, vlist, P.plural(len(chems), "chemistry", "chemistries"),
                   P.listing(chems)))
    else:
        head = ("%s carry this exact envelope at %s, all of them %s and all "
                "still listed. Nothing here separates them but the number on "
                "the wrapper." % (n, vlist, chems[0] if chems else "alike"))

    # Вторая фраза — факт, свой у каждой оболочки: ёмкости или соседи.
    if len(mah) >= 2 and mah[0][0] and mah[-1][0] > mah[0][0] * 1.05:
        tail = (" Capacity is where they part: %s holds %s mAh and %s holds "
                "%s, %s times as much."
                % (esc(mah[0][1]["code"]), P.mm(mah[0][0]),
                   esc(mah[-1][1]["code"]), P.mm(mah[-1][0]),
                   ("%.1f" % (mah[-1][0] / mah[0][0])).rstrip("0").rstrip(".")))
    elif len(mah) == 1:
        tail = (" Only one capacity is published in this shell: %s mAh for "
                "%s, so the rest cannot be ranked by how long they last."
                % (P.mm(mah[0][0]), esc(mah[0][1]["code"])))
    else:
        tail = (" The maker publishes no capacity for anything in this shell, "
                "so nothing here can be ranked by running time.")
    named = sorted({c.get("size") for c in members
                    if c.get("size") in P.POPULAR_SIZES})
    if len(named) == 1:
        where = (" On a shop shelf this envelope is the %s size, and that "
                 "name is what the packet will say." % esc(named[0]))
    elif named:
        where = (" Shops call cells of this envelope %s, so the packet may "
                 "not match the measurement." % P.listing([esc(x) for x in named]))
    else:
        where = (" This envelope has no household name, so the code on the "
                 "cell is the only handle on it.")
    return head + tail + where


def shell_hubs(accepted, cs):
    """Страница на каждую населённую оболочку: «что вообще бывает 11,6 x 5,4».

    Комбинаторика — способ считать, а не корпус ([D-012]): оболочка получает
    страницу, только если в ней есть о чём сказать, то есть не меньше трёх
    обозначений.
    """
    out, groups = {}, {}
    for c in cs:
        s = C.shell(c)
        if s:
            groups.setdefault(s, []).append(c)
    pub = {x["code"] for x, _s in accepted}
    for s, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(members) < MIN_HUB:
            continue
        sl = shell_slug(s)
        members.sort(key=lambda c: (not c["active"], c["code"]))
        live = [c for c in members if c["active"]]
        gone = [c for c in members if not c["active"]]
        vs = sorted({c["volts"] for c in members if c.get("volts")})
        rows = [cell_row(c) for c in members]
        lead = shell_lead(members, live, gone, vs)
        ref = next((c for c in members if c["code"] in pub), members[0])
        fig = draw.family_drawing(ref, [c for c in members if c is not ref])
        body = ('<p class="bx-crumb"><a href="/">Index</a> / '
                '<a href="/shells/">Shells</a> / %s</p>' % esc(C.shell_label(s))
                + "<h1>%s</h1>" % esc(C.shell_label(s))
                + '<p class="bx-lead">%s</p>' % lead
                + (('<div class="bx-fig">%s<p class="bx-cap">Every cell in '
                    'this shell at one scale</p></div>' % fig) if fig else "")
                + rank_table(rows, ("Cell", "Envelope", "Volts",
                                    "Chemistry", "Energizer"),
                             here="/shell/%s/" % sl)
                + stamped_line(members)
                # Ответ витрины — сама таблица оболочки; место идёт под ней.
                + AD_MARK
                # Глагол считается вместе с подлежащим: вписанный одной
                # формой, он дал «1 designation ... are» на шести живых
                # страницах при всех зелёных гейтах.
                + shell_gone_block(members, live, gone,
                                   here="/shell/%s/" % sl)
                # Рекомендация без границ применимости — это рекомендация без
                # границ. Блок стоит там, где стоит вердикт, а не там, где тип
                # страницы равен «cell».
                + (P.applies_block() if gone else ""))
        out["/shell/%s/" % sl] = shell_html(
            "/shell/%s/" % sl, "%s cells — what fits" % C.shell_label(s),
            ("Every battery designation made at %s: voltages, chemistries and "
             "which are still in production." % C.shell_label(s))[:158],
            body, ptype="hub")
    return out


def stamped_line(members):
    """Все чужие имена элементов витрины, одной строкой.

    Человек приходит сюда по коду, вытисненному на корпусе: поиск отправляет
    на витрину каждого, у кого нет своей страницы. Если этого имени на
    витрине нет, переход выглядит промахом — за «1015» отправляли на страницу
    пальчиковой оболочки, где строки «1015» не было вовсе.
    """
    names = []
    for c in members:
        for a in [c["code"]] + list(c.get("aliases") or []):
            if a not in names:
                names.append(a)
    if len(names) <= len(members):
        return ""
    return ('<p class="bx-legend">Also stamped on cells in this table: '
            '%s.</p>' % esc(", ".join(names)))


def popular_groups(cs):
    """Ходовые типоразмеры и их состав. Страница заводится на имя, за которым
    стоит не меньше двух обозначений: на одно смотреть незачем."""
    groups = {}
    for c in cs:
        if c.get("size") in P.POPULAR_SIZES:
            groups.setdefault(c["size"], []).append(c)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def size_hubs(cs):
    """Страница на ходовой типоразмер: AA, AAA, C, D, «Крона»."""
    out = {}
    for name, members in sorted(popular_groups(cs).items()):
        members.sort(key=lambda c: (not c["active"], -(c.get("mah") or 0)))
        vs = sorted({c["volts"] for c in members if c.get("volts")})
        mah = sorted([c["mah"] for c in members if c.get("mah")])
        rows = [cell_row(c) for c in members]
        # Обе половины фразы утверждали РАЗЛИЧИЕ и печатались даже там, где
        # различия нет: «running 625 to 625 mAh, a spread of 1.0 times» и «they
        # do not all deliver the same voltage: 1.5 V».
        if len(mah) >= 2 and mah[0] and mah[-1] > mah[0] * 1.05:
            spread = ("%s to %s mAh, a spread of %.1f times"
                      % (mm(mah[0]), mm(mah[-1]), mah[-1] / max(mah[0], 1)))
        elif mah and mah[0]:
            spread = "%s mAh wherever the maker publishes a figure" % mm(mah[0])
        else:
            spread = "capacities the maker does not publish for every entry"
        vlist = P.listing(["%s V" % ("%.2f" % v).rstrip("0").rstrip(".")
                           for v in vs])
        # Множество vs строилось ПО ТЕМ, У КОГО напряжение есть, а фраза
        # утверждала обо ВСЕХ участниках, включая отфильтрованных: /size/f/
        # обещала «every one of them delivers 1.5 V» над строкой, в которой
        # напряжения не было вовсе. Утверждение о полноте печатается только
        # из посчитанной величины — и молчащие считаются тоже.
        silent = [c for c in members if not c.get("volts")]
        if len(vs) > 1 and silent:
            volt_clause = ("and they do not all deliver the same voltage: %s, "
                           "with %s here carrying no published figure at all"
                           % (vlist, P.plural(len(silent), "designation")))
        elif len(vs) > 1:
            volt_clause = ("and they do not all deliver the same voltage: %s"
                           % vlist)
        elif vs and silent:
            volt_clause = ("and the maker publishes %s for %d of the %d, "
                           "leaving %s without a published voltage"
                           % (vlist, len(members) - len(silent), len(members),
                              P.plural(len(silent), "designation")))
        elif vs:
            volt_clause = "and every one of them delivers %s" % vlist
        else:
            volt_clause = "and the maker publishes no voltage for any of them"
        lead = ("%s %s is a shape, not a specification. %s share it here, "
                "running %s, %s."
                % (P.article(name, cap=True), name,
                   P.plural(len(members), "designation"), spread, volt_clause))
        body = ('<p class="bx-crumb"><a href="/">Index</a> / '
                '<a href="/sizes/">Sizes</a> / %s</p>' % esc(name)
                + "<h1>%s</h1>" % esc(name)
                + '<p class="bx-lead">%s</p>' % lead
                + rank_table(rows, ("Cell", "Envelope", "Volts",
                                    "Chemistry", "Energizer"),
                             here="/size/%s/" % size_slug(name))
                + stamped_line(members)
                + AD_MARK)
        out["/size/%s/" % size_slug(name)] = shell_html(
            "/size/%s/" % size_slug(name),
            "%s batteries — every designation" % name,
            ("Every designation sold as %s %s battery: voltages, chemistries, "
             "capacities and what is still made."
             % (P.article(name), name))[:158],
            body, ptype="hub")
    return out


# ------------------------------------------------------ ПОИСК: ОДИН НА САЙТ
#
# Главное действие справочника стояло на ДВУХ страницах из 164, и обе — не те,
# на которые приходят из выдачи. Теперь поле заводится в shell_html, то есть на
# общем пути ВСЕХ страниц, и модуль ровно один: два разных поиска на одном
# сайте расходились в поведении и в подписи к полю.
#
# Без скрипта поле не мёртвое: форма отправляется на /codes/, где лежат все
# имена и никакого скрипта не нужно. Теряются только подсказки по мере набора.

FIND_LABEL = ("Find a cell &mdash; type the code stamped on it, "
              "or its size in millimeters")
FIND_HINT = "CR2032, AG13, AA, 20 x 3.2"

# Сообщение о промахе НЕ ОБЪЯСНЯЕТ человеку, что его код чужой: набравшему
# «AA» сайт отвечал, что AA принадлежит другой компании и в данных её нет.
# Теперь и AG13, и V13GA в указателе есть, а промах говорит только то, что
# знает: здесь не нашлось, и вот второй путь.
FINDER_NONE = ('<p class="bx-find-none" id="bx-none" role="status" hidden>'
               "Nothing here matches that. If the code has worn off, measure "
               "the cell and type the millimeters instead &mdash; 20 x 3.2, "
               "or just 20, and this box answers from the size.</p>")

FINDER_NOJS = ('<p class="bx-legend" id="bx-nojs">Suggestions as you type '
               "need scripts. Without them this box still goes to the "
               '<a href="/codes/">code index</a>, which needs none.</p>')

# То же самое на самом указателе: ссылка на страницу, где стоишь, — петля.
FINDER_NOJS_HERE = ('<p class="bx-legend" id="bx-nojs">Suggestions as you '
                    "type need scripts. Without them the index below still "
                    "works, and it needs none.</p>")


def finder_html(hero=False, here=""):
    """Разметка поля. Поле ЕСТЬ В РАЗМЕТКЕ, а не показывается скриптом:
    показанное скриптом не попадает в первую отрисовку вовсе."""
    return ('<form class="bx-find%s" id="bx-find" role="search" '
            'action="/codes/" method="get">'
            '<div class="bx-find-bar">'
            '<label class="bx-k" for="bx-q">%s</label>'
            '<input type="search" id="bx-q" name="q" autocomplete="off" '
            'placeholder="%s">'
            '<span class="bx-find-n" id="bx-n" role="status"></span></div>'
            '<ul class="bx-res" id="bx-res" role="list" hidden></ul>'
            "%s%s</form>"
            % (" bx-hero" if hero else "", FIND_LABEL, FIND_HINT,
               FINDER_NONE,
               FINDER_NOJS_HERE if here == "/codes/" else FINDER_NOJS))


# Скрипт читает инертный блок данных и ПЕРЕКЛЮЧАЕТ состояние; разметки внутри
# нет ни одной, строки собираются через createElement. Обратных слэшей в теле
# нет — на этом сайте эскейп уже становился управляющим байтом.
#
# Порядок ярусов и есть ответ на «поиск не находит того, что набирают»:
#   1 точное совпадение ключа        «aa», «ag13», «357», «d»
#   2 габарит                        «20» = всё диаметром 20 мм, «20 x 3.2»
#   3 начало кода                    «cr20» = недобранный код
#   4 вхождение                      последняя надежда, от двух знаков
#   5 укорочение запроса             «sr920sw» -> «sr92» -> SR921
# Кандидаты строятся до ярусов: строка целиком без разделителей, каждое слово
# по отдельности (одно чужое слово больше не убивает запрос) и форма без
# часового суффикса SW/W/S/N/P/B.
# Допуск подбора габарита, мм. Линейка даёт целые миллиметры, а каталог —
# десятые: 14,5 x 50,5 читается как «14 x 50», и это отклонение в половину
# миллиметра по обеим сторонам. Миллиметр берёт и такое чтение, и небольшую
# ошибку от руки, а порядок ПО БЛИЗОСТИ оставляет самый точный ответ первым.
# Число объявлено здесь ОДИН раз и подставляется в поиск подстановкой: два
# экземпляра одного допуска однажды разойдутся.
FIND_TOL_MM = 1

# Сколько строк показывает выпадашка. Число стоит в скрипте ДВАЖДЫ — в общем
# наборщике и в подборе ближайшего габарита, — и потому объявлено здесь один
# раз и подставляется. Набранное в двух местах, оно уже успело подвести: гейт
# требует найти «h.length<12» в отданном скрипте, ломалка меняла ПЕРВОЕ
# вхождение, второе оставалось — и проверка обещания «список показывает 12»
# молча позеленела над сломанным поиском.
FIND_SHOWN = 12

FINDER = (
    "(function(){var D=document;function G(x){return D.getElementById(x)}"
    "var b=G('bx-index');if(!b)return;"
    "var J;try{J=JSON.parse(b.textContent)}catch(e){return}"
    "var f=G('bx-find'),q=G('bx-q'),o=G('bx-res'),z=G('bx-none'),"
    "m=G('bx-n'),j=G('bx-nojs');"
    "if(!f||!q||!o||!z||!m||!j)return;j.hidden=1;"
    "function N(v){return v.replace(/[^a-z0-9]/gi,'').toLowerCase()}"
    "var W=J.w,H=J.h,R=J.r.split(';'),K=[],i,F='',TOL=" + str(FIND_TOL_MM) + ";"
    "for(i=0;i<R.length;i++){R[i]=R[i].split('|');K[i]=N(R[i][0])}"
    "function P(i){var e=R[i],l=D.createElement('li'),"
    "a=D.createElement('a'),s=D.createElement('span');"
    "a.href=H[e[1]];a.textContent=e[0];s.className='bx-res-what';"
    "s.textContent=' '+e[2]+(+e[5]&&e[4]?e[4].replace(/x/g,' x ')"
    "+' mm, ':'')+W[e[3]];l.appendChild(a);l.appendChild(s);"
    "o.appendChild(l);if(!F)F=H[e[1]]}"
    "function run(){var v=q.value,h=[],u={},g,k,C=[],A=0,"
    "t=v.toLowerCase().replace(/volts?/g,'v'),p=t.split(/[^a-z0-9.]+/),w=N(t),"
    "n=v.match(/[0-9]+(?:[.,][0-9]+)?/g),d=n?n.map(function(x){"
    "return parseFloat(x.replace(',','.'))+''}).join('x'):'';"
    # z.hidden=m.textContent='' экономило два байта и ВЕШАЛО сообщение о
    # промахе над пустым полем на всех 166 страницах: пустая строка ложна.
    # Ни один гейт этого не увидел — состояние живёт в браузере.
    "o.textContent='';F='';o.hidden=!w;m.textContent='';z.hidden=1;"
    "if(!w)return;C.push(w);"
    "for(g=0;g<p.length;g++){k=N(p[g]);if(k&&C.indexOf(k)<0)C.push(k)}"
    "for(g=0;g<C.length;g++){k=C[g].replace(/(sw|w|s|n|p|b)$/,'');"
    "if(k.length>2&&C.indexOf(k)<0)C.push(k)}"
    "function S(T){for(var i=0;i<K.length&&h.length<" + str(FIND_SHOWN) + ";i++)"
    "if(!u[i]&&T(K[i],i)){u[i]=1;h.push(i)}}"
    # БЛИЖАЙШИЙ ГАБАРИТ. Строка на главной обещает, что «линейки достаточно»,
    # а линейка даёт целые миллиметры: 14,5 x 50,5 читается как «14 x 50».
    # Точное совпадение таких чтений не находит, поэтому ниже допуск в
    # миллиметр и порядок ПО БЛИЗОСТИ — первым идёт самый близкий, и именно
    # на него уходит Enter.
    "function NEAR(s){var qn=s.split('x'),i,r,rn,j,dd,mx,B=[];"
    "for(i=0;i<qn.length;i++)qn[i]=+qn[i];"
    "for(i=0;i<R.length;i++){r=R[i][4];if(!r)continue;rn=r.split('x');"
    "if(rn.length!=qn.length)continue;mx=0;"
    "for(j=0;j<qn.length;j++){dd=Math.abs(+rn[j]-qn[j]);"
    "if(dd>TOL){mx=-1;break}if(dd>mx)mx=dd}"
    "if(mx<0)continue;B.push([mx,i])}"
    "B.sort(function(a,b){return a[0]-b[0]});"
    "for(i=0;i<B.length&&h.length<" + str(FIND_SHOWN) + ";i++)"
    "if(!u[B[i][1]]){u[B[i][1]]=1;h.push(B[i][1]);A=1}}"
    # ЗАПРОС-ГАБАРИТ РЕШАЕТСЯ ПЕРВЫМ И ОТДЕЛЬНО. Ярус точного совпадения по
    # ИМЕНИ стоял раньше размерного, а «50.5» после нормализации даёт «505» —
    # настоящее обозначение. Поэтому «14.5 x 50.5» (это AA) уводило на
    # 22,5-вольтовую батарею 15F15, «34.1 x 57.5» (это D) — на часовой
    # элемент 7,9 x 1,4 мм: 17 промахов на 113 размерах из собственных данных.
    #   И обломки запроса больше не гуляют по ярусам имён: «20 x 3.2» давало
    # 12 строк, из которых 5 притащил огрызок «20» (200, 201, 203, 204,
    # 20F20) — по всему корпусу так набиралось 876 чужих строк из 1309.
    #   Признак — РАЗДЕЛИТЕЛЬ, а не число: у одиночного «20» работа своя, оно
    # перечисляет обозначения, и об этом написано на главной.
    # РАЗДЕЛИТЕЛЬ РАЗМЕРА, а не просто два числа. Первая версия признака
    # спрашивала «есть ли в запросе две цифры и нет ли букв» — и уводила в
    # размерный проход обозначения вида «3-0316» и «3-312»: 19 имён из 767
    # переставали находить сами себя. Дефис — это часть имени, икс и пробел —
    # это «на».
    "var y=t.replace(/mm/g,''),"
    "sz=/[0-9] *[x*] *[0-9]|[0-9] +[0-9]/.test(y)&&d.indexOf('x')>0"
    "&&!/[a-ln-wyz]/i.test(y),e2;"
    "if(sz){e2=d.split('x');e2=e2.length==2?e2[1]+'x'+e2[0]:'';"
    "S(function(x,i){return R[i][4]===d||R[i][4].indexOf(d+'x')===0});"
    # Штангенциркуль не знает, где диаметр: «3.2 x 20» — то же, что «20 x 3.2».
    "if(!h.length&&e2)"
    "S(function(x,i){return R[i][4]===e2||R[i][4].indexOf(e2+'x')===0});"
    "if(!h.length)NEAR(d)}"
    "else{for(g=0;g<C.length;g++)S(function(x){return x===C[g]});"
    "for(g=0;g<C.length;g++)S(function(x){return x.indexOf(C[g])===0});"
    "for(g=0;g<C.length;g++)if(C[g].length>1)"
    "S(function(x){return x.indexOf(C[g])>0});"
    "k=C[0];while(!h.length&&k.length>3){k=k.slice(0,-1);"
    "S(function(x){return x.indexOf(k)===0})}}"
    "for(g=0;g<h.length;g++)P(h[g]);"
    # СКОЛЬКО И КАКИХ. «12 shown» стояло и над точным попаданием, и над
    # подбором по допуску: одно и то же слово о двух разных ответах.
    "z.hidden=h.length>0;m.textContent=h.length?h.length+(A?' near that size'"
    ":' shown'):''}"
    "function go(e){if(F){e.preventDefault();location.href=F}}"
    "q.addEventListener('input',run);f.addEventListener('submit',go);"
    "q.addEventListener('keydown',function(e){"
    "if(e.keyCode==13||e.key=='Enter')go(e)});"
    "run()})();")


def _index_key(name):
    """Ключ сравнения имён — ОДИН на весь сайт: указатель, поиск и свёртка.

    Человек набирает так, как прочёл: «cr-2032», «CR2032», «cr 2032».
    """
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _dest_rank(href):
    """Насколько адрес ОТВЕЧАЕТ на вопрос. Страница элемента отвечает,
    витрина отвечает наполовину, отсутствие адреса не отвечает вовсе.

    Две строки с одним обозначением и разными адресами — это не выбор:
    «15LF» вёл и на /fr14505/, и в витрину оболочки, и обе строки выглядели
    одинаково.
    """
    if not href:
        return 2
    if href.startswith(("/shell/", "/size/")):
        return 1
    return 0


def _index_entries(cs):
    """Строки указателя кодов. Отдельной функцией, потому что их ЧИСЛО
    называется на главной, а величина, посчитанная в двух местах, у нас уже
    расходилась публично.
    """
    entries = []
    for c in cs:
        href = link_to(c)
        # Ссылка на сам указатель — петля: человек нажимает и остаётся на
        # месте без единого слова объяснения. Вместо неё строка описывает
        # элемент прямо здесь: код известен, страницы нет, вот что это такое.
        if href == "/codes/":
            href = None
        # ВСЕ имена, а не первые шесть: обрезанный на шестом EPX76 переставал
        # находиться, а именно за ним человек и приходит.
        for name in C.findable_codes(c):
            entries.append((name, href, c))
    # Ключ свёртки — ИМЯ БЕЗ РАЗДЕЛИТЕЛЕЙ, тот же, по которому сравнивает
    # поиск. По коду в верхнем регистре «15-LF» и «15LF» оставались двумя
    # строками, и одна вела на страницу элемента, а вторая в витрину
    # оболочки: выбор из одного, притворяющийся выбором из двух.
    best = {}
    for code, href, cell in entries:
        key = _index_key(code)
        if not key:
            continue
        rank = (_dest_rank(href), len(code), code)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, (code, href, cell))
    return sorted((v[1] for v in best.values()),
                  key=lambda x: (x[0].upper(), x[1] or "~"))


def code_index(accepted, cs):
    """Указатель ВСЕХ кодов. Человек вбивает то, что вытиснено на корпусе, а
    вытиснено там что угодно: короткая форма МЭК, полная форма, фирменный
    номер, историческая серия PX.

    Разделы по первому знаку и строка перехода работают БЕЗ скрипта. Фильтр
    вставляет сам скрипт: мёртвого поля, обещающего поиск, которого нет, на
    странице не будет.
    """
    uniq = _index_entries(cs)

    groups = {}
    for code, href, cell in uniq:
        head = code[0].upper()
        head = head if head.isalpha() else "0-9"
        groups.setdefault(head, []).append((code, href, cell))
    order = (["0-9"] if "0-9" in groups else []) + sorted(
        k for k in groups if k != "0-9")

    jump = " ".join('<a href="#g-%s">%s</a>'
                    % (esc(k.lower().replace("-", "")), esc(k)) for k in order)
    blocks = ""
    for k in order:
        items = ""
        for code, href, cell in groups[k]:
            key = re.sub(r"[^a-z0-9]", "", code.lower())
            if href:
                items += ('<li data-k="%s" id="c-%s">'
                          '<a href="%s">%s</a></li>'
                          % (key, key, href, esc(code)))
            else:
                # Страницы нет — но код известен, и человек имеет право узнать
                # прямо здесь, что у него в руках.
                what = ", ".join(x for x in (
                    C.shell_label(C.shell(cell)), chem(cell), volts(cell),
                    "listed" if cell["active"] else "not listed") if x)
                # Своя страница есть у строки ВСЕГДА: сюда на неё ведёт
                # якорь из поиска любой другой страницы сайта. Ссылкой она
                # здесь не становится — петля хуже отсутствия ссылки.
                items += ('<li data-k="%s" id="c-%s"><b>%s</b> '
                          '<span class="bx-nolink">%s</span></li>'
                          % (key, key, esc(code), esc(what)))
        blocks += ('<section class="bx-grp" id="g-%s"><h2>%s</h2>'
                   '<ul class="bx-ix" role="list">%s</ul></section>'
                   % (esc(k.lower().replace("-", "")), esc(k), items))

    body = ('<p class="bx-crumb"><a href="/">Index</a> / All codes</p>'
            "<h1>Every code we know</h1>"
            + '<p class="bx-lead">%s, counting every name the manufacturer '
              'prints and, where the standard defines one, the full IEC '
              'form: %s and %s are the same cell. The long form is looked up '
              'in the standard, never computed from a published size. A code '
              'without a page of its own points at the shell it belongs to, '
              'because that page answers the same question.</p>'
            % (P.plural(len(uniq), "entry", "entries"), "LR44", "LR1154")
            + '<p class="bx-legend">Jump to: %s</p>' % jump
            + '<div id="bx-codes">%s</div>' % blocks
            # Указатель и ЕСТЬ ответ этой страницы: место идёт под ним, а не
            # над ним, иначе первым экраном справочника станет объявление.
            + AD_MARK
            + "<h2>Codes this list does not have</h2>"
              "<p>Import markings such as AG13 and SG13, and house codes such "
              "as V13GA or ZA675, are numbering schemes of other companies. "
              "They cannot be derived from a size or from the IEC standard, "
              "and guessing them is the one thing this site will not do. If "
              "your cell carries one of those, measure it instead: the "
              '<a href="/shells/">shell pages</a> are organized by '
              "millimeters, and a caliper answers what a code cannot.</p>")
    return shell_html("/codes/", "Every battery code, cross-referenced",
                      "An index of every battery designation on the site, "
                      "including alternative codes and the full IEC form "
                      "where the standard defines one.",
                      body, ptype="index")


# ТРЕТЬЕ ПРЕДЛОЖЕНИЕ — ГЛАВНОЕ, и раньше его здесь не было. Оговорка
# «элемент, который встал в отсек, не всегда безопасная замена» стояла ТОЛЬКО
# в подвале, на 98% высоты страницы: витрина делает 125 конкретных
# рекомендаций «меняй это на то», и человек, прочитавший строку таблицы,
# до подвала не доходит. Оговорка, которую видно после решения, — не
# оговорка.
LEGEND = ('<p class="bx-legend">Fit answers whether it enters the '
          'compartment. Voltage answers whether the circuit will '
          'notice. ' + P.SUBSTITUTE_CAVEAT + '</p>')


def list_page(path, title, desc, h1, lead, rows, head, hubs_links=None,
              applies=False, anchor=None):
    """applies=True — там, где страница НАЗЫВАЕТ ЗАМЕНУ.

    Витрина снятых делает 64 конкретные рекомендации и до этой правки не несла
    ни одного из трёх защитных блоков сайта: блок стоял на страницах элементов,
    потому что выборка бралась по ТИПУ страницы, а не по содержимому.
    """
    body = ('<p class="bx-crumb"><a href="/">Index</a> / %s</p>' % esc(h1)
            + "<h1>%s</h1>" % esc(h1)
            + '<p class="bx-lead">%s</p>' % lead
            + (LEGEND if applies else "")
            + (rank_table(rows, head, anchor=anchor) if rows else "")
            + AD_MARK
            + (hubs_links or "")
            + (P.applies_block() if applies else ""))
    return shell_html(path, title, desc, body, ptype="index")


def _listed(members, n):
    """Перечисление, которое НЕ врёт о полноте: срез без «и ещё N» — это
    утверждение «здесь все», которого никто не считал. Ровно так с витрины
    главной пропала R6, обычная угольно-цинковая AA."""
    shown = [c["code"] for c in members[:n]]
    more = len(members) - len(shown)
    return esc(P.listing(shown)) + (" and %d more" % more if more else "")


def crowded_block(top):
    """Самая населённая оболочка — и ЧЕМ именно она опасна, по данным.

    Характеризующая фраза была написана руками и разъехалась с данными:
    у победившей оболочки разрыв 1,2 В против 1,5 В, то есть класс «wrong»,
    а текст называл это тем, что «заметит откалиброванный прибор». Класс
    считается той же функцией, что и на страницах элементов.
    """
    n, cell = top[0]
    fam = [cell] + list(C.family(cell, CELLS))
    worst, pair = None, None
    for a in fam:
        for b in fam:
            if a is b:
                continue
            g = C.voltage_gap(a, b)
            if g and (worst is None or abs(g["pct"]) > abs(worst["pct"])):
                worst, pair = g, (a, b)
    if not worst:
        return ""
    said = {"same": "and every one of them runs at the same voltage, so here "
                    "the compartment tells the truth",
            "minor": "and their voltages differ by a few hundredths, which "
                     "almost nothing notices",
            "calibration": "and an instrument calibrated for one reads off "
                           "on another: %s runs %s where %s runs %s, %s%% "
                           "apart"
                           % (esc(pair[1]["code"]), volts(pair[1]),
                              esc(pair[0]["code"]), volts(pair[0]),
                              P.pct_num(C.gap_pct(pair[0].get("volts"),
                                                  pair[1].get("volts")))),
            "wrong": "and they are not all the same voltage class: %s runs "
                     "%s where %s runs %s, %s%% apart"
                     % (esc(pair[1]["code"]), volts(pair[1]),
                        esc(pair[0]["code"]), volts(pair[0]),
                        P.pct_num(C.gap_pct(pair[0].get("volts"),
                                            pair[1].get("volts"))))
            }[worst["class"]]
    return ("<h2>The most crowded shell in the data</h2>"
            "<p>%s carries %s. The compartment cannot tell them apart, %s. "
            "That is the case this reference exists for.</p>"
            % (esc(C.shell_label(C.shell(cell))),
               P.plural(n + 1, "designation"), said))


DATASET_PATH = "/data/batterycross-cells-%s.csv"
DATASET_LATEST = "/data/latest.csv"


def _n_mercury(by_chem):
    """Сколько химий из снимка снято с потребительской продажи. Считается по
    ДАННЫМ, а не набирается рядом с фразой."""
    return sum(1 for n in by_chem if n == "mercuric oxide")


def snapshot_block(cs):
    """Что в снимке — ЧИСЛАМИ, посчитанными из него же. Главная печатала два
    числа и переходила к спискам; человек, решающий, верить ли справочнику,
    первым делом спрашивает, из чего он сложен."""
    by_chem = {}
    for c in cs:
        by_chem.setdefault(P.chem(c), []).append(c)
    order = sorted(by_chem.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rows = "".join(
        "<li><b>%s</b> <span class=\"bx-res-what\">%s, %d still "
        "listed</span></li>"
        % (esc(name), P.plural(len(group), "designation"),
           sum(1 for c in group if c["active"]))
        for name, group in order)
    coins = sum(1 for c in cs if C.is_coin(c) is True)
    cyl = sum(1 for c in cs if C.is_coin(c) is False)
    boxes = sum(1 for c in cs if C.shell(c) and C.shell(c)[0] == "box")
    recs = sum(len(c.get("records") or []) for c in cs)
    sheets = sum(1 for c in cs
                 for r in (c.get("records") or []) if r["tds"])
    return (
        "<h2>What is in this snapshot</h2>"
        "<p>%d designations, assembled from %d catalog records, %d of which "
        "carry a technical data sheet. %d are coins, %d are cylinders and %d "
        "are boxes with three measurements rather than two. %d of the %d "
        "chemistries here %s no longer sold to consumers in the United "
        "States at all, and their pages say so.</p>"
        '<ul class="bx-nb" role="list">%s</ul>'
        "<p>The split that matters is not chemistry but status: %d "
        "designations Energizer still lists against %d it does not. The "
        "second number is the reason this site exists, because a designation "
        "leaving a catalog does not empty the compartment it was sold for."
        "</p>"
        % (len(cs), recs, sheets, coins, cyl, boxes,
           _n_mercury(by_chem), len(by_chem),
           P.verb(_n_mercury(by_chem), "are"), rows,
           sum(1 for c in cs if c["active"]),
           sum(1 for c in cs if not c["active"])))


def reading_block(cs):
    """Как читается ответ — на ЖИВОМ примере из данных, а не на выдуманном.
    Пример выбирается по самой населённой оболочке, то есть меняется вместе
    со снимком и не может протухнуть незаметно."""
    groups = {}
    for c in cs:
        sh = C.shell(c)
        if sh:
            groups.setdefault(sh, []).append(c)
    sh, members = max(groups.items(), key=lambda kv: (len(kv[1]), str(kv[0])))
    members = sorted(members, key=lambda c: c["code"])
    volts = sorted({c["volts"] for c in members if c.get("volts")})
    chems = sorted({P.chem(c) for c in members})
    return (
        "<h2>How to read an answer on this site</h2>"
        # Оба числа — длина ANSWER_COLUMNS, тех самых заголовков, что стоят
        # в таблицах пар. Слово «three» здесь не сверялось ни с чем.
        "<p>Every page answers %d questions in %d separate columns, and "
        "keeps them separate on purpose. <b>Fit</b> is geometry: drop-in, "
        "sits lower, too tall, too wide or too narrow, decided within %s mm "
        "on every axis. <b>Voltage</b> is consequence: same volts, close "
        "enough, reads off, or a different class. <b>Chemistry</b> is "
        "everything the first two cannot see &mdash; a flat discharge curve, "
        "a tab that has to be pulled, a cell that cannot be recharged.</p>"
        "<p>The busiest envelope in this snapshot is %s: %s share it "
        "&mdash; %s &mdash; across %s and %s%s. Every one of them "
        "drops into the same hole. That is exactly the case a single "
        "compatibility column would flatten into one word, and it is why "
        "there are three.</p>"
        % (len(ANSWER_COLUMNS), len(ANSWER_COLUMNS),
           ("%.1f" % C.FIT_MM), esc(C.shell_label(sh)),
           P.plural(len(members), "designation"),
           _listed(members, 6),
           P.plural(len(chems), "chemistry", "chemistries"),
           P.plural(len(volts), "nominal voltage"),
           ("" if not volts else " " + P.span(
               P.volts_num(volts[0]), P.volts_num(volts[-1]),
               "at %s", "from %s to %s"))))


def limits_block(cs):
    """Чего сайт НЕ ДЕЛАЕТ, сказанное вслух и на главной.

    Домен обещает кросс-референс, а источник один. Оговорка, спрятанная на
    странице методики, обещания не снимает: аудит назвал это одним дефектом,
    обесценивающим все страницы разом. Пока второго каталога нет, граница
    печатается там, где читают обещание.
    """
    return (
        "<h2>What this site does not do</h2>"
        "<p>It reads <b>one manufacturer's published data</b> &mdash; "
        "Energizer's, retrieved once and pinned. That is the honest boundary "
        "of every sentence here. When a page says a designation is not "
        "listed, it means Energizer no longer offers a part under it, not "
        "that nobody makes the cell; for common sizes somebody usually "
        "does. Where a page says nothing shares a size or a voltage, read it "
        "as nothing in this catalog, and the pages say it that way.</p>"
        "<p>It carries no brand-to-brand columns, no prices and no shop. It "
        "does not know what your device does with a difference it can "
        "measure: whether the contacts reach a shorter cell, whether the "
        "circuit was calibrated for a chemistry that holds voltage flat, or "
        "whether the equipment tolerates a higher current. Where equipment is "
        "a safety or medical device, its manufacturer names the cell, and "
        "that name outranks this table.</p>")


def busiest_block(cs, hub_paths):
    """Самые населённые оболочки — с ИМЕНАМИ и с тем, что различает жильцов.
    Это лучшее, что на сайте есть, и с главной оно раньше не было видно."""
    groups = {}
    for c in cs:
        sh = C.shell(c)
        if sh:
            groups.setdefault(sh, []).append(c)
    top = sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))[:5]
    rows = ""
    for sh, members in top:
        members = sorted(members, key=lambda c: c["code"])
        volts = sorted({c["volts"] for c in members if c.get("volts")})
        chems = sorted({P.chem(c) for c in members})
        sl = shell_slug(sh)
        label = esc(C.shell_label(sh))
        name = ('<a href="/shell/%s/">%s</a>' % (sl, label)
                if sl in hub_paths else label)
        # Список, обрезанный молча, — утверждение о полноте, которого никто
        # не посчитал: R6, обычная угольно-цинковая AA, пропадала из витрины
        # «оболочек, с которыми приходят», а двумя разделами ниже стояла в
        # том же перечне целиком.
        listed = _listed(members, 5)
        vspan = ("" if not volts else " " + P.span(
            P.volts_num(volts[0]), P.volts_num(volts[-1]),
            "at %s", "from %s to %s"))
        rows += ('<li>%s <span class="bx-res-what">%s &mdash; %s; %s%s'
                 '</span></li>'
                 % (name, listed,
                    P.plural(len(chems), "chemistry", "chemistries"),
                    P.plural(len(volts), "nominal voltage"), vspan))
    return (
        "<h2>The envelopes people arrive with</h2>"
        "<p>An envelope is the published outside size to a tenth of a "
        "millimeter, and it is the unit a compartment actually cares about. "
        "The %d below carry the most designations in this snapshot. In every "
        "one of them a cell that drops straight in can still be the wrong "
        "cell, because the chemistries and the nominal voltages inside a "
        "single envelope do not match.</p>"
        '<ul class="bx-nb" role="list">%s</ul>'
        "<p>That is the case the industry cross-reference chart handles "
        "worst. A chart with one row per size tells the reader that "
        "everything in the row is interchangeable; these %d rows would "
        "each be a lie told in one word. Each envelope here gets its own "
        "page, with every resident drawn at the same scale and the voltage "
        "difference between them stated as a consequence rather than as a "
        "number.</p>" % (len(top), rows, len(top)))


def gone_block(cs):
    """Что значит «снято» — числами того же снимка. Именно за этим приходят."""
    gone = [c for c in cs if not c["active"]]
    sized = [c for c in gone if C.shell(c)]
    with_swap, orphan = [], []
    for c in sized:
        reps = [r for r in C.replacements(c, cs) if r["cell"]["active"]]
        (with_swap if reps else orphan).append(c)
    same_volts = sum(
        1 for c in with_swap
        for r in C.replacements(c, cs)[:1]
        if r["volt"] and r["volt"]["class"] in ("same", "minor"))
    return (
        "<h2>What &ldquo;no longer listed&rdquo; turns out to mean</h2>"
        "<p>%d of the %d designations here are gone from the Energizer "
        "catalog, and that is the state most visitors arrive in. It is not "
        "one situation but three, and the pages say which one applies. For "
        "%d of them the maker publishes the dimensions, which is what it "
        "takes to say anything at all about fit; the other %d cannot be "
        "compared and are listed by name only.</p>"
        "<p>Of the ones that can be compared, %d have something the maker "
        "still lists that enters the same compartment, and for %d of those "
        "the nearest candidate is also the same working voltage or close to "
        "it &mdash; a genuine swap. The remaining %d have nothing of that "
        "size in this catalog at all, which is a statement about the catalog "
        "and not about the world: another manufacturer may still make the "
        "cell, and for common sizes one usually does.</p>"
        % (len(gone), len(cs), len(sized), len(gone) - len(sized),
           len(with_swap), same_volts, len(orphan)))


def markings_intro(cs):
    """Маркировки, которых нет в стандарте. Самый ходовой запрос ниши и то,
    чего нет ни у одного конкурента объяснённым."""
    marks = C.TRADE_MARKINGS
    kinds = {}
    for _m, _iec, whose in marks:
        kinds[whose] = kinds.get(whose, 0) + 1
    return (
        "<h2>AG13, V13GA, 76A: names that are not designations</h2>"
        "<p>The code stamped on a cheap button cell is often not a "
        "designation at all. <b>AG</b> numbers are an importers' convention "
        "with no standards body behind them; <b>V13GA</b>, <b>76A</b>, "
        "<b>RW82</b> and their relatives are retail branding; <b>ZA</b> "
        "numbers are hearing-aid packaging. All of them name an envelope "
        "somebody else already named. This site carries %d such markings and "
        "resolves each to the designation it stands for, labelled with whose "
        "convention it is.</p>"
        "<p>The search box takes them. Type <b>AG13</b> and it answers with "
        "the cell, not with a message about other companies; the same goes "
        "for <b>SG13</b>, <b>ZA675</b>, <b>DL2032</b> and <b>123A</b>. A "
        "marking is only carried where the designation behind it exists in "
        "this data &mdash; inventing the other half of a pair would be "
        "worse than answering nothing. The rule each one follows is on the "
        '<a href="/method/#markings">method page</a>.</p>'
        % len(marks))


def drawn_block(cs):
    """Чертёж — единственное, чего нет ни у одного конкурента. С главной он
    не был виден вовсе, а «drawn to size» стоит в шапке всех страниц."""
    sized = [c for c in cs if C.shell(c)]
    ds = sorted(c["diameter"] for c in sized if c.get("diameter"))
    return (
        "<h2>Every cell here is drawn, and drawn to one scale per page</h2>"
        "<p>No other reference in this niche draws the cell. A table can tell "
        "you that one cell is %s mm across and another is %s mm; a picture "
        "tells you in one glance which of them is the thing in your hand. "
        "Every page that has published dimensions carries a silhouette, and "
        "where an envelope has neighbours the whole family is drawn side by "
        "side at the same scale, so the comparison is honest by "
        "construction.</p>"
        "<p>The scale is stated on every drawing in pixels per millimeter and "
        "it changes between pages, because a %s mm coin and a %s mm cylinder "
        "cannot share one useful scale. Within a page it never changes: a "
        "drawing is never stretched to fill a column, which is the one thing "
        "that would make a to-scale picture worse than no picture. Hold the "
        "screen against the cell only after reading the scale &mdash; browser "
        "zoom and screen density both move it.</p>"
        % (P.mm(ds[len(ds) // 2] if ds else None),
           P.mm(ds[-1] if ds else None), P.mm(ds[0] if ds else None),
           P.mm(ds[-1] if ds else None)))


def dataset_block():
    """Набор данных и постоянная ссылка для цитирования. PLAYBOOK §7: с
    первого дня, а не после первой сотни ссылок."""
    return (
        '<h2 id="data">The data, and how to cite it</h2>'
        "<p>The whole snapshot is published as a single CSV, dated and "
        "unchanged between rebuilds: "
        '<a href="%s">%s</a>, also served as '
        '<a href="%s">latest.csv</a>. One row per designation, with the '
        "maker's published figures and the values this site computes marked "
        "as ours in the header. Use it, quote it, check us against it.</p>"
        '<p class="bx-src">Cite as: BatteryCross, '
        "<i>BatteryCross cell cross-reference</i>, snapshot %s. "
        'https://%s%s &mdash; method at https://%s/method/.</p>'
        % (DATASET_PATH % DATA_SNAPSHOT.isoformat(),
           ("batterycross-cells-%s.csv" % DATA_SNAPSHOT.isoformat()),
           DATASET_LATEST, DATA_SNAPSHOT.strftime("%d %B %Y"),
           DOMAIN, DATASET_LATEST, DOMAIN))


def home(accepted, cs, hub_paths):
    """Главная строится вокруг ДВУХ путей, потому что людей два сорта.

    Код читается — поле ввода и подсказки по мере набора. Код стёрся — тогда
    мерить: диаметр даёт оболочку, оболочка даёт список того, что бывает
    такого размера. Второго пути нет ни у одного конкурента, и он же —
    единственный ответ человеку с маркировкой, которой в наших данных нет.

    Проверка сценария нашла, что раньше на главной было НОЛЬ полей ввода, а
    единственный маршрут к своему коду — список из 720 строк.
    """
    st = STATS

    # Оболочки для второго пути: настоящие подписи из данных, отсортированные
    # по диаметру, чтобы человек с линейкой шёл по возрастанию.
    hubs = []
    for s, members in sorted(
            ((s, [c for c in cs if C.shell(c) == s])
             for s in {C.shell(c) for c in cs if C.shell(c)}),
            key=lambda kv: (kv[0][0] != "round", kv[0][1], kv[0][2])):
        sl = shell_slug(s)
        if sl in hub_paths:
            hubs.append('<li><a href="/shell/%s/">%s</a> '
                        '<span class="bx-res-what">%s</span></li>'
                        % (sl, esc(C.shell_label(s)),
                           P.plural(len(members), "designation")))

    groups = popular_groups(cs)
    sizes = "".join(
        '<li><a href="/size/%s/">%s</a> '
        '<span class="bx-res-what">%s</span></li>'
        % (size_slug(name), esc(name), P.plural(len(groups[name]), "code"))
        for name in P.POPULAR_SIZES if name in groups)

    top = sorted(((len(C.family(c, cs)), c) for c in cs
                  if C.shell(c)), key=lambda t: -t[0])[:1]

    body = (
        "<h1>What replaces your battery</h1>"
        # Поле — ПЕРВОЕ под заголовком. Оно стояло под подводкой в 55 слов и
        # начиналось на 463-м пикселе: на телефоне 320x568 инструмент, ради
        # которого страницу открыли, лежал ниже сгиба целиком.
        + finder_html(hero=True, here="/")
        + ('<p class="bx-lead">A cross-reference for <b>%d</b> battery '
           "designations, drawn to size. <b>%d</b> of them are no longer in "
           "the Energizer catalog, which is why most people arrive: the code "
           "stamped on the cell has stopped appearing on shelves, and the "
           "question is what is the same size and what the voltage difference "
           "costs.</p>" % (st["cells"], st["gone"]))
        + "<h2>If you only know the household name</h2>"
        + "<p>AA and its relatives are shapes, not specifications: the same "
          "envelope carries cells that differ in voltage and in how much they "
          "hold. Each page lists what is made in that shape and what the "
          "differences cost.</p>"
        + '<ul class="bx-nb bx-row" role="list">%s</ul>' % sizes
        # Место идёт ПОСЛЕ первого ответа и никогда над ним.
        + AD_MARK
        + '<h2 id="measure">If the code has worn off, measure it</h2>'
        # Обещание переписано под то, что инструмент ДЕЛАЕТ. Прежнее — «голое
        # 20 находит каждый элемент 20 мм поперёк» — было неправдой дважды:
        # в размерную ветку голое число не попадало вовсе, а список показывает
        # первые двенадцать строк, и слово «каждый» он не подтверждает.
        + "<p>Type the millimeters into the box above and it answers from "
          "the size: <b>20 x 3.2</b> finds CR2032, <b>11.6 5.4</b> opens the "
          "envelope page and what sits in it, and a bare <b>20</b> lists the "
          "designations 20 mm across. Diameter first, then height; a box "
          "cell takes three figures.</p>"
        + ("<p>A ruler across the diameter, or a caliper if you have one, "
           "is enough to place a cell. These are the %d envelopes that carry "
           "%d "
           "designations or more, sorted small to large; each page shows "
           "everything made at that size, drawn to scale, with what the "
           "voltage differences cost. An envelope is the published dimensions "
           "to a tenth of a millimeter, so a household name covers more "
           "designations than any one envelope under it.</p>"
           % (st["hubs"], MIN_HUB))
        + '<ul class="bx-nb bx-two" role="list">%s</ul>' % "".join(hubs)
        # Два числа снятых стояли в одном экране друг от друга и не
        # объяснялись: 133 обозначения сняты, но размеры производитель
        # публикует для 125 из них, и в витрину попадают только они.
        + '<p class="bx-legend">Of the %d designations Energizer no longer '
          'lists, the %d whose dimensions the maker publishes are '
          '<a href="/discontinued/">listed together</a>; the rest have no '
          'measurements to compare. Every name we know, '
          'including the ones with no page of their own, is in the list '
          'of <a href="/codes/">%d codes</a>.</p>'
          % (st["gone"], st["gone_sized"], st["index_names"])
        + "<h2>What this site computes</h2>"
        # Число и перечень идут ИЗ ОДНОГО объявления C.FACT_KINDS, ключи
        # которого гейт сверяет с тем, что facts() выдаёт на корпусе. Слово
        # «five» стояло рядом со списком из семи видов.
        + ("<p>The maker publishes dimensions, voltages, chemistries and "
           "capacities and stops there. Every page here adds %d kinds of "
           "value that are calculated rather than copied: %s.</p>"
           % (len(C.FACT_KINDS),
              P.listing([d for _k, d in C.FACT_KINDS])))
        + "<p>Fit and voltage are answered separately and never merged into "
          "one verdict. A cell that enters the compartment can still be the "
          "wrong cell, and that distinction is the whole site.</p>"
        + (crowded_block(top) if top and top[0][0] else "")
        + snapshot_block(cs)
        + reading_block(cs)
        + busiest_block(cs, hub_paths)
        + gone_block(cs)
        + markings_intro(cs)
        + drawn_block(cs)
        + limits_block(cs)
        + dataset_block())
    home_desc = ("Type the code stamped on your cell: what physically fits, "
                 "what the voltage difference costs, and every published "
                 "figure behind both.")
    return shell_html("/", "BatteryCross — what replaces your battery",
                      home_desc, body, ptype="index",
                      ld=site_ld(home_desc))


# ------------------------------------------------------------ служебные

def dest_for(name, href, cell):
    """Куда ведёт строка указателя. ПУСТОГО МЕСТА НЕ БЫВАЕТ.

    193 строки из 715 не вели никуда: человек находил свой код и упирался в
    жирный текст. Порядок ответа: своя страница, витрина оболочки, строка
    витрины снятых (она называет ближайший текущий элемент — это ответ, а не
    перекладывание), и в последнюю очередь якорь на собственную строку
    указателя, где код хотя бы описан.
    """
    if href:
        return href
    # Условие ровно то же, по которому строится витрина снятых: снят и
    # габарит опубликован. Разойтись им нечем — предикат один.
    if not cell["active"] and C.shell(cell):
        return "/discontinued/#d-" + _index_key(cell["code"])
    return "/codes/#c-" + _index_key(name)


def _dims_key(cell):
    """Габарит числами, тем же форматом, в каком человек читает
    штангенциркуль: «20x3.2». По нему ищут те, у кого код стёрся."""
    sh = C.shell(cell)
    if not sh:
        return ""
    return "x".join(("%.1f" % v).rstrip("0").rstrip(".") for v in sh[1:])


def search_payload(cs):
    """Указатель поиска — ОДИН на все страницы сайта, и потому сжатый.

    Раньше он лежал только на главной и весил 67 КБ несжатыми. Теперь он
    едет на каждой из 166 страниц, и повторяющееся вынесено в два словаря:
    адреса и «что это». Габарит в строке ОДИН и служит и поиску, и подписи —
    оболочка словами из него же и складывается.

    Поля строки: имя | адрес | канон | описание | габарит | род.
    Род: 0 — обиходное имя или витрина оболочки, 1 — обозначение, 2 — его
    псевдоним, 3 — торговая маркировка. Он же решает порядок при равном
    качестве совпадения: набравший «D» получает типоразмер D, а не 1127MD.
    """
    W, H = [], []
    wi, hi = {}, {}
    rows = []

    def w_of(s):
        if s not in wi:
            wi[s] = len(W)
            W.append(s)
        return wi[s]

    def h_of(s):
        assert s, "строка указателя без адреса"
        if s not in hi:
            hi[s] = len(H)
            H.append(s)
        return hi[s]

    seen = set()

    def add(name, href, canon, what, dims, kind):
        key = _index_key(name)
        assert key and key not in seen, "ключ пуст или повторяется: %s" % name
        assert not set(name) & set("|;"), "разделитель внутри имени: %s" % name
        seen.add(key)
        rows.append("|".join((name, str(h_of(href)), canon, str(w_of(what)),
                              dims, str(kind))))

    # 1. Обиходные имена. Их набирают чаще всего, и до этой правки «AA», «AAA»
    # и «9V» отдавали НОЛЬ строк при живых страницах в сорока пикселях ниже.
    groups = popular_groups(cs)
    for name in P.POPULAR_SIZES:
        if name in groups:
            add(name, "/size/%s/" % size_slug(name), "",
                "household size, %s"
                % P.plural(len(groups[name]), "designation"), "", 0)

    # 2. Витрины оболочек — вход по измерению.
    shells = {}
    for c in cs:
        s = C.shell(c)
        if s and shell_slug(s) in C.SHELL_HUBS:
            shells.setdefault(shell_slug(s), (s, 0))
            shells[shell_slug(s)] = (s, shells[shell_slug(s)][1] + 1)
    for sl, (s, cnt) in sorted(shells.items()):
        add(C.shell_label(s), "/shell/%s/" % sl, "",
            "one envelope, %s" % P.plural(cnt, "designation"),
            "x".join(("%.1f" % v).rstrip("0").rstrip(".") for v in s[1:]), 0)

    # 3. Обозначения и их псевдонимы.
    by_key = {}
    for name, href, c in _index_entries(cs):
        base = ", ".join(x for x in (
            volts(c), chem(c),
            "" if c["active"] else "not listed by Energizer") if x)
        # Человек набирает «357», а страница называется SR44. Не сказать
        # этого в строке результата — значит отправить его переходом,
        # который выглядит промахом.
        canon = "" if name == c["code"] else c["code"] + " " + chr(183) + " "
        add(name, dest_for(name, href, c), canon, base, _dims_key(c),
            1 if name == c["code"] else 2)
        by_key[_index_key(name)] = (name, href, c)

    # 4. Торговые маркировки. Их НЕ печатает наш источник, и обозначениями мы
    # их не объявляем: строка результата говорит, чья это условность. До этого
    # набравший «AG13» получал ноль строк и сообщение о том, что его код
    # принадлежит другой компании, — при том что у верхнего конкурента адрес
    # страницы начинается с ag13.
    for mark, target, whose in C.TRADE_MARKINGS:
        t = by_key.get(_index_key(target))
        if not t or _index_key(mark) in seen:
            continue
        tname, thref, tc = t
        add(mark, dest_for(tname, thref, tc), "",
            "%s; the same cell as %s" % (C.MARKING_WHOSE[whose], target),
            _dims_key(tc), 3)

    # Порядок строк В ДАННЫХ и есть порядок внутри яруса: скрипт идёт по
    # массиву подряд. Род впереди имени — иначе набравший «20» получал
    # 5000LC и 5004LC раньше CR2016 и CR2032, то есть фирменные номера
    # раньше обозначения, которое на элементе и вытиснено.
    rows.sort(key=lambda s: (s.rsplit("|", 1)[1], s.split("|", 1)[0]))
    return {"w": W, "h": H, "r": ";".join(rows)}


def search_block(cs):
    """Инертный блок данных. Строится ОДИН раз за круг сборки и едет на все
    страницы: величина, посчитанная в двух местах, у нас уже расходилась."""
    return ('<script type="application/json" id="bx-index">%s</script>'
            % json.dumps(search_payload(cs), separators=(",", ":"),
                         ensure_ascii=True))


SEARCH_BLOCK = ""

def site_stats(cs, accepted, hubs):
    """Все числа сайта, посчитанные ОДИН раз.

    Величина, посчитанная в двух местах независимо, у нас уже расходилась
    публично; здесь она расходилась на трёх страницах сразу.
    """
    sized = [c for c in cs if C.shell(c)]
    shells = {C.shell(c) for c in sized}
    return {
        "cells": len(cs),
        "sized": len(sized),
        "gone": sum(1 for c in cs if not c["active"]),
        "live": sum(1 for c in cs if c["active"]),
        "gone_sized": sum(1 for c in sized if not c["active"]),
        "live_sized": sum(1 for c in sized if c["active"]),
        "shells": len(shells),
        "hubs": len(hubs),
        "pages": len(accepted),
        "index_names": len(_index_entries(cs)),
    }


STATS = {}
CELLS = []


def markings_table_block(cs):
    """Полная таблица чужих маркировок с УКАЗАНИЕМ, чья это условность.

    Конкуренты печатают эти коды ячейкой таблицы и не объясняют ни одного.
    Объяснённые, они и есть тот запрос, по которому в нишу приходят.

    ДВА УТВЕРЖДЕНИЯ О НАБОРЕ СЧИТАЮТСЯ ПО НАБОРУ. «Три четверти кодов,
    которые люди набирают» — доля, которой у нас нет ни в одном поле: что
    люди набирают, сайт не видит, и величину, которую нечем посчитать, он не
    печатает вовсе. «Ни одна из них не стоит под Also stamped» — проверяемо,
    и было неверно: A76 стоит там на /lr44/, потому что несёт его ЗАПИСЬ
    производителя, а Also stamped печатает именно записи. Считаем пересечение
    по всем страницам, а не по одной.

    Подстановка ИМЕНОВАННАЯ: собранное «+» посреди позиционного «%» отрывает
    хвост от начала строки, и на этой ферме это уже стоило трёх правил CSS.
    """
    rows = []
    for mark, iec, whose in C.TRADE_MARKINGS:
        rows.append("<tr><th>%s</th><td>%s</td><td>%s</td></tr>"
                    % (esc(mark), esc(iec), esc(C.MARKING_WHOSE[whose])))
    stamped = sorted({m for m, _iec, _w in C.TRADE_MARKINGS
                      for c in cs if m in (c.get("aliases") or [])})
    if stamped:
        # Глагол согласуется ЧИСЛОМ, а не на слух: P.verb(1, "do appear")
        # дало «do appears» на странице метода.
        also = ("%s of them &mdash; %s &mdash; %s under <i>Also stamped</i> "
                "on a cell page all the same, because the maker&rsquo;s own "
                "record carries %s as a part number. The rest are not there, "
                % (len(stamped), esc(P.listing(stamped[:4])),
                   P.verb(len(stamped), "appear"),
                   "it" if len(stamped) == 1 else "them"))
    else:
        also = ("None of them is printed under <i>Also stamped</i> on a cell "
                "page, ")
    return (
        '<h2 id="markings">Trade markings, house codes and what they stand '
        "for</h2>"
        "<p>Many of the codes stamped on a cheap cell are not designations at "
        "all, and %(n)s resolved to a designation in the table below. An "
        "<b>AG</b> number is an importers' convention: no standards body "
        "assigns it, no manufacturer is bound by it, and the same AG number "
        "has meant slightly different cells at different times. A house code "
        "&mdash; V13GA, 76A, RW82, KA76 &mdash; is a retailer's or a brand's "
        "part number for a cell somebody else makes. A <b>ZA</b> number is "
        "hearing-aid packaging, colour-coded on the tab.</p>"
        "<p>%(also)s"
        "because that heading claims the string is physically on the cell "
        "under the manufacturer's own record. These are carried separately, "
        "resolved to the designation they stand for, and only where that "
        "designation exists in this data. Where it does not, nothing is "
        "printed: inventing the other half of the pair would look exactly "
        "like knowledge.</p>"
        "<p>A trailing <b>W</b> or <b>SW</b> is different again: it is part "
        "of the standard and means the cell meets the IEC watch "
        "specification, so SR626SW and SR626 are the same envelope with the "
        "suffix describing drain rather than size. The search box strips it "
        "before looking.</p>"
        '<div class="bx-tw"><table><thead><tr><th>Marking</th>'
        "<th>Stands for</th><th>Whose convention</th></tr></thead>"
        "<tbody>%(rows)s</tbody></table></div>"
        % {"rows": "".join(rows), "also": also,
           "n": P.plural(len(rows), "of them is", "of them are")})


def method_sources_block(cs):
    """Источники С НОМЕРАМИ. PLAYBOOK §8 требует URL и нумерацию; сайт
    объявлял источник фразой в подвале и не давал проверить ни одну цифру."""
    recs = sum(len(c.get("records") or []) for c in cs)
    sheets = sum(1 for c in cs for r in (c.get("records") or []) if r["tds"])
    return (
        '<h2 id="sources">Sources, numbered</h2>'
        "<p>Every figure reproduced on this site comes from one of %d "
        "places, and every cell page names the exact records behind it with "
        "a link to the sheet. Across the snapshot that is %d catalog records "
        "and %d technical data sheets.</p>"
        '<ol class="bx-refs">'
        '<li><span class="bx-refno">[1]</span> Energizer product data index, '
        '<a href="%s" rel="nofollow noopener">%s</a> &mdash; the catalog '
        "listing itself: designation, ANSI/NEDA number, chemistry, "
        "dimensions, nominal voltage, weight, region and status. Retrieved "
        "%s.</li>"
        '<li><span class="bx-refno">[2]</span> Energizer technical data '
        'sheets, <a href="%s" rel="nofollow noopener">%s</a> &mdash; one PDF '
        "per product, giving capacity and the cutoff voltage it was counted "
        "to, volume, impedance, operating temperature range and "
        "classification. Each cell page links the sheets it used by "
        "filename.</li>"
        '<li><span class="bx-refno">[3]</span> IEC 60086, the international '
        "standard for primary battery designations, is the authority for the "
        "letters and the four-figure size codes described above. It is not "
        "reproduced here; it is a paid standard, and this site uses only its "
        "publicly documented naming rules.</li>"
        '<li><span class="bx-refno">[4]</span> Reese’s Law, United '
        "States, 2022 &mdash; the federal requirement for child-resistant "
        "packaging and warning labels on button and coin cells, cited on the "
        "coin-cell pages as the reason those packs are hard to open.</li>"
        "</ol>"
        # «There is no third source» стояло ПОД списком, пронумерованным до
        # четырёх, и опровергалось им же. Считается ровно то, что верно:
        # сколько источников дают цифры и сколько файлов открывает сборка.
        "<p>Everything else on the site is arithmetic on the figures in [1] "
        "and [2], and every table marks the rows that are ours. The build "
        "opens %s, assembled from those %d and pinned; [3] and [4] are "
        "cited for a naming rule and a law, and nothing the site computes "
        "comes from either. Where a page would need a figure that is in "
        "neither, it says so instead of guessing.</p>"
        % (len([n for n in (recs, sheets) if n]),
           recs, sheets, C.INDEX_URL, C.INDEX_URL.replace("https://", ""),
           snap_date(), C.TDS_BASE,
           C.TDS_BASE.replace("https://", ""),
           P.plural(len(C.DATA_FILES), "data file"),
           len([n for n in (recs, sheets) if n])))


def limits_method():
    """Известные ограничения и частота обновления — PLAYBOOK §8 прямым
    текстом. Ограничение, не написанное на странице методики, читателю
    неизвестно, а нам известно."""
    return (
        '<h2 id="limits">Known limitations</h2>'
        "<p><b>One manufacturer.</b> The domain says cross-reference and this "
        "snapshot is one catalog. That is the biggest limitation on the site "
        "and it shapes every sentence: a designation missing here is missing "
        "from Energizer's catalog, not from the world, and no page claims "
        "otherwise. Brand-to-brand columns &mdash; the Duracell, Maxell, "
        "Renata and Varta equivalents people also want &mdash; would need "
        "further published catalogs, and until those are read and checked the "
        "site does not pretend to them.</p>"
        "<p><b>Published figures, not measured ones.</b> Nothing here has "
        "been on a caliper or a load bank. Where the maker rounds, the site "
        "carries the rounding and says so; where the maker publishes nothing, "
        "the field is blank rather than estimated, and every cell page lists "
        "which of its fields are blank and what that costs the answer.</p>"
        "<p><b>Fit is geometry only.</b> A drop-in verdict means the outside "
        "dimensions agree within " + P.mm(C.FIT_MM) + " mm. It cannot see a "
        "contact spring's reach, a retaining clip, a polarity difference in a "
        "holder, or a compartment that vents. A cell that fits is not thereby "
        "a safe substitute.</p>"
        "<p><b>Rechargeables are compared but never recommended.</b> They "
        "appear in tables because they share envelopes, always with their "
        "nominal voltage and never as a drop-in for a primary cell.</p>"
        "<p><b>Update frequency.</b> The snapshot is taken deliberately, not "
        "on a schedule, and the date it carries is the date of the data. A "
        "rebuild that changes nothing changes no page. When the catalog is "
        "read again the previous snapshot stays available as a dated CSV, so "
        "the difference between two dates is itself checkable.</p>")


def method_page(cs):
    """Метод отдельной страницей: она объясняет ВЕСЬ сайт и потому не
    повторяется на каждой странице."""
    body = (
        '<p class="bx-crumb"><a href="/">Index</a> / Method</p>'
        "<h1>How this site decides</h1>"
        '<p class="bx-lead">Every number that comes from the manufacturer is '
        "reproduced without change. Everything else is arithmetic on those "
        "numbers, and this page says exactly what arithmetic.</p>"
        "<h2>Fit</h2>"
        "<p>Two cells are a drop-in when every cross-section matches within "
        "%s mm. That tolerance is the order of a contact spring's travel, not "
        "a round number chosen for looks. Outside it the answer is not no: it "
        "is <b>shorter</b>, <b>taller</b>, <b>wider</b> or <b>narrower</b>, "
        "because those are different problems. A shorter cell enters and may "
        "not reach the contact; a taller one will not let the cover close.</p>"
        "<h2>Voltage</h2>"
        "<p>Classes are set by consequence, and the quantity they are set "
        "on is the gap between two nominal voltages taken against the higher "
        "of the two. A pair of cells therefore gets one class, whichever of "
        "the two pages you meet it on. %s%% of that gap or less is the same "
        "working voltage. Up to %s%% is close enough that most circuits will "
        "not notice but a calibrated instrument might. Up to %s%% will run "
        "and will read off — this is where mercury cells at %s and alkaline "
        "at %s sit, and why a light meter built for one misreads on the "
        "other. Beyond that is a different class. The percentage printed "
        "beside a cell is counted from the cell whose page you are reading, "
        "so that last boundary falls at %s%% below it and %s%% above it: one "
        "gap, divided once by the larger nominal and once by the smaller.</p>"
        "<h2>Energy</h2>"
        "<p>Stored energy is capacity times nominal voltage, in "
        "milliwatt-hours, because capacity alone is not comparable across "
        "chemistries: 150 mAh at 3 V is twice the energy of 150 mAh at 1.5 V. "
        "Density divides that by the published volume. Cells with identical "
        "stored energy share a rank rather than being ordered arbitrarily.</p>"
        '<h2 id="words">The words this site uses</h2>'
        "<p>None of these are industry jargon we inherited; they are names we "
        "had to pick, so here is what each one means.</p>"
        '<dl class="bx-gloss">'
        "<dt>Envelope, or shell</dt><dd>The outside size of the cell: a "
        "diameter and a height for a coin, three measurements for a box. It "
        "is what decides whether the cell goes into the compartment at "
        "all.</dd>"
        "<dt>Drop-in</dt><dd>Every measurement matches within %s mm. It "
        "will go in and sit where the old one sat. It says "
        "nothing about voltage.</dd>"
        "<dt>Sits lower</dt><dd>Same diameter, less tall. It will enter, and "
        "the contact may not reach it. A spring usually takes it up; a flat "
        "tab does not.</dd>"
        "<dt>Too tall</dt><dd>Same diameter, taller. It goes in and the cover "
        "will not close over it.</dd>"
        "<dt>Reads off</dt><dd>The voltage is far enough from the original "
        "that an instrument calibrated for the old cell will show a wrong "
        "number. The device still runs. This is the failure people miss.</dd>"
        "<dt>Not listed</dt><dd>Energizer no longer sells a part under this "
        "designation. Other manufacturers may still make the cell.</dd>"
        "</dl>"
        "<h2>What the letters in a designation mean</h2>"
        "<p>An IEC designation is not a serial number; it is a description. "
        "The first letter is the chemistry: <b>L</b> alkaline, <b>S</b> silver "
        "oxide, <b>P</b> zinc air, <b>C</b> and <b>B</b> lithium, <b>M</b> "
        "mercuric oxide, <b>H</b> nickel-metal hydride, and a bare <b>R</b> "
        "carbon zinc. An <b>R</b> after that letter means the cell is round. A "
        "<b>W</b> at the end means it meets the IEC watch standard. That is "
        "why LR44 and SR44 are the same size and different insides, and why a "
        "code beginning with M belongs to a chemistry that is banned from "
        "consumer sale in the United States and the European Union.</p>"
        "<h2>The designation as a second source</h2>"
        "<p>A four-figure IEC code encodes the size: CR2032 means 20 mm across "
        "and 3.2 mm tall. Where such a code exists we check it against the "
        "published dimensions, which is the only independent check available "
        "on a single-source figure. The standard writes whole millimeters, so "
        "a cell measuring 12.5 mm is coded 12 — that is rounding, not "
        "disagreement, and the pages say which one they are looking at.</p>"
        "<h2>Which cells get a page</h2>"
        # Оба порога стояли здесь СЛОВОМ, то есть мимо всякой сверки:
        # подмена MIN_HUB с 3 на 4 в байтовой копии прошла 88 гейтов из 88,
        # а сайт печатал прежнее «three». Числа подставляются из констант.
        "<p>Not all of them. A designation earns a page when at least %d "
        "of those computed values exist for it and when its text differs "
        "materially from every page already published. %d designations are in "
        "the data and %d have a page. Every one of the rest is in the "
        '<a href="/codes/">code index</a>, and those whose envelope carries '
        "%d designations or more are on its shell page as well.</p>"
        '<p class="bx-src">Source: %s. Retrieved once and pinned: the site is '
        "rebuilt deliberately, not on a schedule, so a page never changes "
        "under a reader without the date changing with it.</p>"
        # Ртутные «1,35 В» были набраны руками и спорили с собственными
        # данными сайта: 17 ртутных записей из 24 несут 1,4 В. Обе величины
        # теперь считаются по снимку одной функцией.
        % (("%.1f" % C.FIT_MM),
           P.pct_num(C.V_SAME_PCT), P.pct_num(C.V_MINOR_PCT),
           P.pct_num(C.V_SERIOUS_PCT),
           P.volts_num(P.CHEM_VOLTS.get("mercuric oxide")),
           P.volts_num(P.CHEM_VOLTS.get("alkaline")),
           P.pct_num(C.V_SERIOUS_PCT),
           P.pct_num(abs(C.class_edge(1)) * 100.0),
           # Допуск словаря — та же величина, что и в первом подставленном
           # числе этой страницы, и берётся она оттуда же. Место в кортеже
           # отсчитано по числу спецификаторов ДО фразы: девятое.
           P.mm(C.FIT_MM),
           MIN_FACTS, STATS["cells"], STATS["pages"], MIN_HUB,
           esc(DATA_VINTAGE)))
    # Метка ставится ПОСЛЕ подстановки, а не внутри неё: тело страницы —
    # одна большая неявная склейка литералов с «%» в хвосте, и плюс посреди
    # неё оторвал бы форматирование от начала строки. Что подставилось,
    # проверяется здесь же.
    body += markings_table_block(cs) + method_sources_block(cs) + limits_method()
    anchor = '<h2 id="words">'
    assert body.count(anchor) == 1, "якорь места на /method/ не единственный"
    body = body.replace(anchor, AD_MARK + anchor, 1)
    return shell_html("/method/", "How BatteryCross decides what fits",
                      "The arithmetic behind every comparison on the site: fit "
                      "tolerance, voltage classes, stored energy and the "
                      "designation check.", body, ptype="page")


def guest_block():
    """ЧТО ИМЕННО ГРУЗИТ БРАУЗЕР — печатается из THIRD_PARTIES, того же
    списка, из которого печатается подпись под рекламным местом.

    Прежняя редакция отрицала стороннее одним предложением на все времена:
    «no third-party script loads on any page». Такое предложение верно ровно
    до первого дня заработка и ложно на следующий — а на студийном сайте
    точно такое же отрицание было ложным уже в день, когда его написали,
    потому что счётчик вставлял хост. Утверждение о приватности — это
    утверждение о БАЙТАХ, поэтому оно здесь выводится, а не пишется.
    """
    if not THIRD_PARTIES:
        return ('<p class="bx-legend" data-hosts="none">Nothing on this site '
                "comes from another company. The markup, the style, the "
                "drawings and the icon are all served from %s, and opening a "
                "page here makes no request to any other host: no font "
                "service, no image service, no tag manager, no tracker. That "
                "is a statement about what your browser fetches, and the "
                "build refuses to ship a page whose markup disagrees with "
                "it.</p>" % DOMAIN)
    li = "".join(
        '<li data-host="%s"><b>%s</b> &mdash; %s &mdash; %s. %s</li>'
        % (esc(host), esc(name), esc(host), esc(why),
           "Sets cookies." if ck else "Sets no cookies.")
        for name, host, why, ck in THIRD_PARTIES)
    return ("<p>Opening a page here fetches files from the services below as "
            "well as from %s. Each is named by the host your browser "
            "contacts.</p>"
            '<ul class="bx-nb" role="list">%s</ul>' % (DOMAIN, li))


# ОДИН ИСТОЧНИК РАСКРЫТИЯ НА ОБЕ ВЕТКИ, и разница между ними — ВРЕМЯ
# ГЛАГОЛА, а не состав.
#
# Раньше это были два разных текста: пока сети нет, печаталось всё, чего
# требует Google, а в день подключения сети ветка менялась целиком — на
# четыре предложения без единой ссылки на отказ. То есть абзац, написанный
# «заранее, чтобы не писать второпях», стирался ровно тем событием, ради
# которого был написан, и переключала это одна строка в THIRD_PARTIES.
#
# Google формулировки не даёт («Because publisher sites and laws across
# countries vary, Google is unable to suggest specific privacy policy
# language») и требует трёх СМЫСЛОВ: сторонние поставщики, включая Google,
# используют куки на основании предыдущих посещений ЭТОГО И ДРУГИХ сайтов;
# рекламная кука позволяет ей и партнёрам показывать рекламу; отказ — через
# Ads Settings или aboutads.info. Все три стоят здесь, в одном месте.
#
# Печатать это в НАСТОЯЩЕМ времени на сайте без сети было бы ложью о байтах —
# тем самым, против чего написан весь модуль. Поэтому глаголы подставляются.
AD_DISCLOSURE = (
    "A third-party advertising network, and the other companies it works "
    "with, %(may)s use cookies to serve advertisements based on your "
    "previous visits to this and other sites. Personalized advertising "
    "%(can)s be turned off in the settings of the network concerned; for "
    "Google that is <a href=\"https://adssettings.google.com/\" "
    'rel="nofollow noopener">Ads Settings</a>, and the way its partners use '
    'the data is described at <a href="https://policies.google.com/'
    'technologies/partner-sites" rel="nofollow noopener">Google’s '
    "partner sites page</a>. Opting out of personalized advertising from "
    'many companies at once is done at <a href="https://optout.aboutads.'
    'info/" rel="nofollow noopener">aboutads.info</a>. Where the law '
    "requires consent before such a cookie is set, a consent notice "
    "%(asks)s for it first and %(keeps)s only the answer."
)

FUTURE = {"may": "may", "can": "can", "asks": "will ask",
          "keeps": "will remember"}
PRESENT = {"may": "may", "can": "can", "asks": "asks",
           "keeps": "remembers"}


def ad_privacy_block():
    """Раздел о рекламе — из ТОГО ЖЕ списка, что и место на странице.

    Первый абзац описывает СЕГОДНЯШНЕЕ состояние байтов. Второй — обязательное
    раскрытие, и он печатается ВСЕГДА: без сети в будущем времени и назван
    условным, с сетью в настоящем и с именем сети. Условное утверждение о
    будущем — не ложное утверждение о настоящем, и разница размечена словами.
    """
    nets = [t for t in THIRD_PARTIES if t[2] == "advertising"]
    if nets:
        name, host, _why, _ck = nets[0]
        now = ('<p class="bx-legend" data-ads="%s">Advertising here is served '
               "by %s from %s. Its scripts set cookies of their own and read "
               "cookies already set by that company, which is how an "
               "advertisement is chosen and how a repeat of the same "
               "advertisement is avoided. We never send it your name, your "
               "email or anything you type into the search box on this "
               "site.</p>" % (esc(host), esc(name), esc(host)))
        return now + "<p>%s</p>" % (AD_DISCLOSURE % PRESENT)
    return ('<p class="bx-legend" data-ads="none">This site is built to carry '
            "advertising. No advertising network is connected: nothing is "
            "fetched from one, no advertisement is requested or auctioned, "
            "no advertising cookie is set, and no profile of you exists "
            "here. The slots that will hold advertising currently hold links "
            "to other pages of this site, captioned as ours. The slots and "
            "this paragraph are printed from one list, so the day a network "
            "is connected this page names it.</p>"
            "<p>When that day comes the disclosure below applies. It is "
            "written out now so it is not written in a hurry later, and it "
            "is the same sentence that will stand here then, in the present "
            "tense. %s</p>" % (AD_DISCLOSURE % FUTURE))


def legal_pages():
    """Политика ВЫВОДИТСЯ из списков, а не пишется руками: утверждение о
    приватности касается того, что грузит браузер."""
    an = ("<p>This site runs no analytics of any kind. No page view is "
          "counted and no visitor is identified.</p>") if not ANALYTICS else (
        "<p>This site uses a privacy-focused analytics service to count page "
        "views. It records the page address, the referring site and a coarse "
        "country, and never sets an identifier that follows you between "
        "sites.</p>")
    ck = ("<p>This site sets no cookies and uses no local storage.</p>"
          if not COOKIES else
          "<p>Cookies are used only where you have agreed to them.</p>")
    body = ('<p class="bx-crumb"><a href="/">Index</a> / Privacy</p>'
            "<h1>Privacy</h1>"
            '<p class="bx-lead">This page describes what your browser fetches '
            "when it opens a page on this site, and what is left on your "
            "device afterwards. It is generated from the same lists the pages "
            "are built from, so it cannot describe a site other than the one "
            "you are reading.</p>"
            "<h2>What your browser fetches</h2>" + guest_block()
            + "<h2>Advertising</h2>" + ad_privacy_block()
            + "<h2>Analytics</h2>" + an
            + "<h2>Cookies and storage</h2>" + ck
            + "<h2>What the host sees</h2>"
              "<p>The site is served by Cloudflare Pages. Like any web host it "
              "processes the request itself &mdash; your IP address, the page "
              "requested, your browser string &mdash; to deliver the page and "
              "block abuse. We do not receive those logs as a report and do "
              "not use them to build any profile.</p>"
            + "<h2>Who this is, and email</h2>"
              # ИМЯ ЮРЛИЦА ОБЯЗАНО СТОЯТЬ ЗДЕСЬ. Из подвала и цитаты оно
              # убрано намеренно — имя компании не объясняет справочник о
              # батарейках и вызывает лишний вопрос, — но политика без
              # названной стороны не политика: обещание «удалим по просьбе»
              # даёт КТО-ТО, и адресовать просьбу надо кому-то.
              "<p>This site is published by %s, a Wyoming limited liability "
              "company, and it is the party responsible for the data "
              "described on this page. If you write to %s we keep the "
              "message and your address for as long as it takes to answer, "
              "and delete it afterwards. Ask us to erase it sooner and we "
              "will.</p>" % (PUBLISHER, mail_link())
            + "<h2>Changes</h2><p>This page is generated from the site build, "
              "so it cannot drift from what the pages actually load. Last "
              "changed %s.</p>" % CONTENT_DATE.strftime("%d %B %Y"))
    privacy = shell_html("/privacy/", "Privacy — BatteryCross",
                         "Exactly what a BatteryCross page fetches, what it "
                         "stores on your device, and what the advertising "
                         "space does and does not do.", body)

    body = ('<p class="bx-crumb"><a href="/">Index</a> / Terms</p>'
            "<h1>Terms of use</h1>"
            '<p class="bx-lead">This is a reference site. Use it freely, and '
            "do not use it as the last word on whether a cell is safe in your "
            "equipment.</p>"
            "<h2>Accuracy and what it cannot cover</h2>"
            "<p>Dimensions, voltages and capacities are reproduced from "
            "published manufacturer data. The comparisons are computed by us "
            "and we check the arithmetic. We cannot check your device: whether "
            "its contacts reach a shorter cell, whether it was calibrated for "
            "a chemistry with a flat discharge curve, or whether it tolerates "
            "the current a different chemistry can deliver.</p>"
            "<h2>Not advice</h2>"
            "<p>Nothing here is engineering advice or a safety certification. "
            "A cell that fits a compartment is not always a safe substitute. "
            "Rechargeable cells are never a drop-in for primary cells "
            "regardless of size. Where equipment matters &mdash; medical, "
            "safety or measurement &mdash; confirm with its manufacturer.</p>"
            "<h2>Content and reuse</h2>"
            "<p>The underlying figures are published by their manufacturers "
            "and are facts, not our property. The text, the computed "
            "comparisons, the drawings and the arrangement of this site are "
            "ours. Quote us with a link; do not republish the site "
            "wholesale.</p>"
            "<h2>Liability</h2>"
            "<p>The site is provided as is, without warranty. To the "
            "maximum extent permitted by law, %s is not liable for any "
            "loss arising from use of this site. Nothing here limits "
            "liability that cannot lawfully be limited. These terms are "
            "governed by the law of the State of Wyoming, United "
            "States.</p>"
            # ДАТА У ДОГОВОРА. У политики она стояла, у условий — нет, и
            # «эти условия» без даты не позволяют сказать, какие именно.
            "<p>These terms take effect on %s and apply to the site as it "
            "stands on that date.</p>"
            % (PUBLISHER, CONTENT_DATE.strftime("%d %B %Y")))
    terms = shell_html("/terms/", "Terms of use — BatteryCross",
                       "Terms of use for BatteryCross, including the accuracy "
                       "and substitution disclaimers.", body)

    body = ('<p class="bx-crumb"><a href="/">Index</a> / Contact</p>'
            "<h1>Contact</h1>"
            '<p class="bx-lead">One address, read by a person: '
            "%s.</p>" % mail_link()
            + "<h2>Corrections</h2>"
              "<p>If a figure here does not match the manufacturer's published "
              "data, tell us the page and the row. Source figures are parsed "
              "mechanically, so a mismatch is a bug in our reader and we want "
              "it. If a substitution on this site turned out to be wrong in "
              "practice, we especially want that.</p>"
            + "<h2>Who runs this</h2>"
              "<p>%s, a Wyoming limited liability company. The site is "
              "independent and is not affiliated with any battery "
              "manufacturer or standards body.</p>" % PUBLISHER
            + "<h2>Data</h2><p>Source: %s. Pinned and rebuilt deliberately; "
              "the date on every page is the date of the content, not of the "
              "build.</p>" % esc(DATA_VINTAGE))
    contact = shell_html("/contact/", "Contact — BatteryCross",
                         "How to reach BatteryCross, and how to report a "
                         "figure that does not match the manufacturer.", body)

    body = ('<h1>That page is not here</h1>'
            '<p class="bx-lead">The address did not match a cell on the site. '
            "Not every designation in the data has a page of its own: one is "
            "created where the figures support real comparisons, and the rest "
            "live on their shell page.</p>"
            '<ul class="bx-nb" role="list">'
            '<li><a href="/codes/">Every code we know</a></li>'
            '<li><a href="/shells/">Every shell</a></li>'
            '<li><a href="/">Start from the beginning</a></li></ul>')
    notfound = shell_html("/404.html", "Page not found — BatteryCross",
                          "That address did not match a page on BatteryCross. "
                          "Every designation is listed on the code index.",
                          body, index=False)
    return {"/privacy/": privacy, "/terms/": terms, "/contact/": contact,
            "/404.html": notfound}


# ------------------------------------------------- набор данных и цитирование

# Заголовок ПОМЕЧАЕТ, чьё поле: «ours:» перед тем, что посчитано здесь.
# Без пометки скачавший файл не отличит опубликованное производителем от
# нашей арифметики, а это ровно то различие, ради которого сайт написан.
CSV_COLUMNS = (
    ("designation", lambda c: c["code"]),
    ("kind", lambda c: c["kind"]),
    ("aliases", lambda c: ";".join(c.get("aliases") or [])),
    ("chemistry", lambda c: c.get("chemistry") or ""),
    ("size_name", lambda c: c.get("size") or ""),
    ("volts", lambda c: c.get("volts")),
    ("diameter_mm", lambda c: c.get("diameter")),
    ("height_mm", lambda c: c.get("height")),
    ("length_mm", lambda c: c.get("length")),
    ("width_mm", lambda c: c.get("width")),
    ("grams", lambda c: c.get("grams")),
    ("volume_cc", lambda c: c.get("cc")),
    ("mah", lambda c: c.get("mah")),
    ("cutoff_volts", lambda c: c.get("cutoff")),
    ("impedance_ohms_low", lambda c: c.get("ohms_lo")),
    ("impedance_ohms_high", lambda c: c.get("ohms_hi")),
    ("operating_c_low", lambda c: c.get("op_lo")),
    ("operating_c_high", lambda c: c.get("op_hi")),
    ("listed_by_energizer", lambda c: "yes" if c["active"] else "no"),
    ("regions", lambda c: ";".join(c.get("regions") or [])),
    ("source_record_ids",
     lambda c: ";".join(str(r["id"]) for r in (c.get("records") or []))),
    ("source_datasheets",
     lambda c: ";".join(r["tds"] for r in (c.get("records") or []) if r["tds"])),
    ("ours:iec_long_form", lambda c: c.get("iec_long") or ""),
    ("ours:energy_mwh", lambda c: C.energy_mwh(c)),
    ("ours:density_mwh_cc", lambda c: C.density_mwh_cc(c)),
    ("ours:code_check", lambda c: (c.get("code_check") or {}).get("verdict", "")),
    ("ours:has_page", lambda c: ""),
)


def _csv_cell(v):
    """Экранирование по RFC 4180 и НИЧЕГО больше. Строка с точкой с запятой
    внутри поля остаётся одним полем; строка с кавычкой удваивает кавычку."""
    if v is None:
        return ""
    if isinstance(v, float):
        s = ("%.4f" % v).rstrip("0").rstrip(".")
    else:
        s = str(v)
    if set(s) & set(',"\r\n'):
        return QUOTE + s.replace(QUOTE, QUOTE + QUOTE) + QUOTE
    return s


def dataset_csv(cs, published):
    """Весь снимок одним файлом. PLAYBOOK §7 требует его с первого дня, и это
    единственный артефакт ниши, который можно ЦИТИРОВАТЬ: у конкурентов —
    сканы, PDF и таблицы Joomla."""
    head = ",".join(name for name, _f in CSV_COLUMNS)
    lines = [head]
    for c in sorted(cs, key=lambda c: c["code"]):
        row = []
        for name, fn in CSV_COLUMNS:
            v = ("yes" if c["code"] in published else "no") \
                if name == "ours:has_page" else fn(c)
            row.append(_csv_cell(v))
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def _font_stack(name):
    """Набор шрифтов ЧИТАЕТСЯ из общего CSS, а не набирается второй раз.
    Величина, набранная в двух местах, однажды разойдётся публично."""
    m = re.search(r"--%s:([^;]+);" % name, design.CSS)
    if not m:
        raise ValueError("в CSS не найден набор шрифтов --%s" % name)
    return m.group(1).strip()


# Виджет живёт в ЧУЖОЙ странице и не может опираться на переменные нашей: свои
# цвета он объявляет сам, в обеих темах, иначе на тёмном форуме он выйдет
# чёрным по чёрному. Ноль сторонних загрузок, ноль скриптов.
# Виджет живёт внутри чужой страницы, но правила облика у него те же, и
# нарушал он их ровно там же: цвета вердиктов были набраны шестью литералами
# ПРЯМО В ПРАВИЛАХ, три из них — только внутри media-блока тёмной темы. Это
# та самая форма, из-за которой у нас карточка осталась светлой внутри тёмной
# полосы при 1,07:1. И это был второй светофор на сайте, где сигнальный цвет
# объявлен один. Теперь: все цвета — переменные на голом :root, тёмная тема
# переопределяет ТЕ ЖЕ имена, вердикт «другой класс» несёт сигнал, остальные
# — чернила и вес.
EMBED_CSS = design.strip_comments("""
:root{color-scheme:light dark;--e-paper:#ffffff;--e-ink:#0d1114;
  --e-ink2:#454d54;--e-line:#767e86;--e-signal:#a13600;
  --e-t-micro:.75rem;--e-t-small:.875rem;--e-t-body:1rem;
  --e-t-lead:1.125rem;
  --e-sans:%(sans)s;--e-mono:%(mono)s}
@media (prefers-color-scheme:dark){
  :root{--e-paper:#0d1114;--e-ink:#e8ebed;--e-ink2:#a7b0b8;--e-line:#6c757d;
    --e-signal:#ff8a3d}
}
body{margin:0;font:var(--e-t-body)/1.5 var(--e-sans);background:var(--e-paper);
  color:var(--e-ink);overflow-wrap:break-word}
.bx-emb{padding:12px;max-width:640px}
.bx-emb h1{font:700 var(--e-t-lead)/1.3 var(--e-mono);margin:0 0 6px}
.bx-emb p{margin:0 0 12px;font-size:var(--e-t-small);color:var(--e-ink2)}
.bx-emb a{color:inherit}
.bx-emb table{border-collapse:collapse;width:100%%;font-size:var(--e-t-small)}
.bx-emb th,.bx-emb td{border-bottom:1px solid var(--e-line);padding:6px 8px;
  text-align:left;overflow-wrap:anywhere}
.bx-emb thead th{font:700 var(--e-t-micro)/1.3 var(--e-mono);text-transform:uppercase;
  letter-spacing:.06em;color:var(--e-ink2)}
.bx-emb .bx-from{font:var(--e-t-micro)/1.4 var(--e-mono);text-transform:uppercase;
  letter-spacing:.07em;margin:12px 0 0}
.bx-emb .bx-v{font-family:var(--e-mono);white-space:nowrap}
.bx-emb .bx-vtag{display:block;font:400 var(--e-t-micro)/1.3 var(--e-mono);
  text-transform:uppercase;letter-spacing:.06em;color:var(--e-ink2);
  white-space:normal}
.bx-emb .bx-limits{border-top:2px solid var(--e-line);padding-top:8px}
.bx-emb .bx-v-same,.bx-emb .bx-v-minor{color:var(--e-ink)}
.bx-emb .bx-v-calibration{color:var(--e-ink);font-weight:700}
.bx-emb .bx-v-wrong{color:var(--e-signal);font-weight:700}
@media (max-width:400px){
  .bx-emb{padding:8px}
  .bx-emb th,.bx-emb td{padding:6px 4px}
}
""" % {"sans": _font_stack("sans"), "mono": _font_stack("mono")})


def embed_page(cell, s, cs):
    """Встраиваемый виджет — ТРЕТИЙ обязательный артефакт PLAYBOOK §7.

    Это отдельный документ, а не страница сайта: у него нет шапки, подвала,
    навигации, поля поиска и рекламы, потому что он живёт внутри чужой
    страницы. Скрипта нет вовсе — код собран статически на каждый элемент,
    так что встроивший его форум не получает ни одного стороннего запроса, а
    мы не получаем причины его объяснять. Обратная ссылка — по построению:
    это и есть то, ради чего артефакт заводят.
    """
    rows = ""
    for r in (s.get("reps") or [])[:6]:
        c = r["cell"]
        v = r["volt"]
        # СТОЛБЕЦ ХИМИИ ВОЗВРАЩЁН. Без него виджет печатал «drop-in, -20.0%,
        # reads off» для никель-металлогидридного элемента и не имел ни одного
        # места, где сказано, что аккумулятор не бывает прямой заменой. На
        # странице сайта это говорят и столбец, и раздел химии, и границы
        # применимости; здесь не было ни одного из трёх.
        rows += ('<tr><th>%s</th><td>%s</td>'
                 '<td class="bx-v bx-v-%s">%s %s<span class="bx-vtag">%s'
                 '</span></td><td>%s</td></tr>'
                 % (esc(c["code"]), esc(P.FIT_WORD.get(r["fit"], r["fit"])),
                    esc(v["class"]) if v else "none", volts(c),
                    P.pct_signed(v["pct"]) if v else "",
                    esc(P.V_TAG.get(v["class"], "")) if v else "&mdash;",
                    esc(P.chem(c))))
    if not rows:
        rows = ('<tr><th>&mdash;</th><td colspan="3">Nothing %s measures '
                "close enough to compare.</td></tr>" % D.SCOPE)
    path = "/embed/%s/" % slug(cell)
    href = "https://%s/%s/" % (DOMAIN, slug(cell))
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(code)s — what fits, and what the voltage costs</title>
<meta name="robots" content="noindex, follow">
<meta name="page-type" content="embed">
<link rel="canonical" href="%(href)s">
<style>%(css)s</style>
</head>
<body>
<div class="bx-emb">
<h1>%(code)s &mdash; %(label)s, %(volts)s</h1>
<p>What still fits this compartment, and what the voltage difference costs.
Fit and voltage are separate answers.</p>
<table><thead><tr><th>Cell</th><th>Fit</th><th>Voltage</th>
<th>Chemistry</th></tr></thead><tbody>%(rows)s</tbody></table>
<p class="bx-limits">Fit and voltage are separate answers here and they are
never merged into one: fit is geometry, decided within %(fit)s mm, and
voltage is consequence, decided on the gap against the higher
of the two nominal voltages. Neither of them answers chemistry. Rechargeable
cells are never a drop-in for primary cells regardless of size; a zinc air
cell begins discharging the moment its tab comes off; a device calibrated for
a chemistry that holds its voltage flat will drift on one that sags. These are
one manufacturer&rsquo;s published nominal figures, so a cell that enters the
compartment can still be the wrong cell, and a designation missing from them
is missing from that catalog rather than from the world.</p>
<p class="bx-from">Source: <a href="%(href)s" target="_top">batterycross.com</a> &middot;
%(vintage)s</p>
</div>
</body>
</html>
""" % {"code": esc(cell["code"]), "css": EMBED_CSS, "rows": rows,
       "href": href, "vintage": esc(DATA_VINTAGE), "fit": P.mm(C.FIT_MM),
       "label": esc(C.shell_label(s["shell"]) or "size unpublished"),
       "volts": volts(cell)}


# Высота готового сниппета. Виджет — это заголовок, таблица и три абзаца
# оговорок; 520 точек закрывают его при любом числе строк, какое виджет
# печатает (их не больше шести). Меньше — оговорки уезжают под обрез, а они
# и есть та часть, ради которой виджет вообще отдаётся наружу.
EMBED_H = 520


def embed_offer(cell):
    """Строка «встроить эту таблицу» на странице элемента."""
    # «The same table» было обещанием, которого виджет не держал: в нём не
    # было ни столбца химии, ни одной оговорки этого сайта, а читают его там,
    # где ни того ни другого взять неоткуда.
    return ('<p class="bx-src">Putting this on a forum or a repair page? The '
            'same answer without the site around it &mdash; fit, voltage, '
            'chemistry and the limits that go with them &mdash; is at '
            '<a href="/embed/%s/">/embed/%s/</a>. It loads nothing from '
            'anywhere else. Paste this:</p>'
            '<pre class="bx-snip"><code>&lt;iframe src="https://%s/embed/%s/" '
            'width="100%%" height="%d" loading="lazy" '
            'title="%s replacements"&gt;&lt;/iframe&gt;</code></pre>'
            % (slug(cell), slug(cell), DOMAIN, slug(cell), EMBED_H,
               esc(cell["code"])))


def about_page(cs):
    """About — PLAYBOOK §8, без исключений, и рецензент рекламной сети ищет
    её по имени. Авторство ОРГАНИЗАЦИИ: выдуманных экспертов не заводим."""
    st = STATS
    body = (
        '<p class="bx-crumb"><a href="/">Index</a> / About</p>'
        "<h1>About BatteryCross</h1>"
        '<p class="bx-lead">BatteryCross answers one question: the code on '
        "your cell has stopped appearing on shelves, so what goes in its "
        "place, and what will that cost the thing it powers. Fit and voltage "
        "are answered separately, because they are different questions and "
        "merging them is how a cross-reference table misleads.</p>"
        "<h2>Who publishes it</h2>"
        "<p>%s, a limited liability company registered in the State of "
        "Wyoming, United States. There is no invented author persona here and "
        "there will not be one: the pages are generated by a program the "
        "company writes and maintains, and the company is accountable for "
        "them. The site is independent and is not affiliated with, endorsed "
        "by or connected to any battery manufacturer or standards body.</p>"
        "<h2>Where the numbers come from</h2>"
        "<p>Dimensions, voltages, chemistries, capacities, impedances and "
        "operating ranges are published by the manufacturer and reproduced "
        "without change. This snapshot holds %d designations assembled from "
        "%d catalog records, taken on %s and pinned: the site is rebuilt "
        "deliberately, not on a schedule, so a page does not change under a "
        "reader without the date changing with it. Every cell page carries "
        "numbered references to the exact records and data sheets behind "
        "it.</p>"
        "<p>Everything else is arithmetic on those figures and is marked as "
        "ours: whether one cell fits where another sat and in what sense, how "
        "far apart two voltages are and what that costs, stored energy and "
        "energy per cubic centimeter, the rank within an envelope, and the "
        'check of a designation against its measured size. The '
        '<a href="/method/">method page</a> states each rule and the '
        "tolerance it uses.</p>"
        "<h2>What it does not do</h2>"
        "<p>It reads one manufacturer's catalog. It sells nothing, quotes no "
        "prices and carries no affiliate links. It is not engineering advice "
        "and not a safety certification: a cell that fits a compartment is "
        "not always a safe substitute, rechargeable cells are never a drop-in "
        "for primary cells, and where the equipment is medical or a safety "
        "device its own manufacturer names the cell. Pages say what the "
        "catalog does not contain rather than claiming the world does not "
        "contain it.</p>"
        "<h2>Corrections</h2>"
        "<p>If a figure here does not match the manufacturer's published "
        "data, write to %s with the page and the "
        "row. Source figures are parsed mechanically, so a mismatch is a bug "
        "in our reader and we want it. If a substitution suggested here "
        "turned out to be wrong in practice, we especially want that. "
        "Corrections are made in the source data and the whole site is "
        "rebuilt, so a fix reaches every page that used the figure.</p>"
        "<h2>Reuse</h2>"
        '<p>The underlying figures are facts and not our property. The '
        'complete snapshot is published as <a href="%s">a dated CSV</a> so '
        "that anyone can check us against it or build something else with "
        "it. The text, the computed comparisons, the drawings and the "
        "arrangement are ours; quote them with a link.</p>"
        % (PUBLISHER, st["cells"],
           sum(len(c.get("records") or []) for c in cs),
           DATA_SNAPSHOT.strftime("%d %B %Y"), mail_link(),
           DATASET_LATEST))
    return shell_html("/about/", "About BatteryCross",
                      "Who publishes BatteryCross, where its figures come "
                      "from, what it computes itself, and what it refuses to "
                      "claim.", body, ptype="page")


def sitemap(paths):
    lm = CONTENT_DATE.isoformat()
    urls = "".join("<url><loc>https://%s%s</loc><lastmod>%s</lastmod></url>"
                   % (DOMAIN, p, lm) for p in sorted(paths))
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "%s</urlset>" % urls)


def robots():
    return ("User-agent: *\nAllow: /\n\nSitemap: https://%s/sitemap.xml\n"
            % DOMAIN)


# --------------------------------------------------------------- отбор

def _shingles(text, pattern):
    w = re.findall(pattern, text.lower())
    return {tuple(w[i:i + 5]) for i in range(max(0, len(w) - 4))}


TEXT_PAT = r"[a-z0-9][a-z0-9'.-]*"
SKEL_PAT = r"[a-z][a-z'-]*"


def main_column(html):
    """Основная колонка без шапки, подвала и боковой.

    Считается ГЛУБИНОЙ вложенности, а не «до первого </div>»: внутри колонки
    десятки div, и наивный вариант дал бы пустую выборку, а пустая выборка у
    нас однажды уже печатала «пройден».
    """
    key = '<div class="bx-main">'
    i = html.find(key)
    if i < 0:
        return None
    j, depth_ = i + len(key), 1
    for m in re.finditer(r"<div\b|</div>", html[j:]):
        depth_ += 1 if m.group(0) != "</div>" else -1
        if depth_ == 0:
            return html[j:j + m.start()]
    return None


def own_prose(html):
    """ВЕСЬ видимый текст страницы, который обязан быть своим.

    Было: заголовочный абзац плюс по ОДНОМУ абзацу за каждым не-константным
    h2 — 23,7% видимого текста основной колонки. Три четверти того, что видят
    читатель и Googlebot, не сравнивалось ни одним гейтом близнецов, и пара
    /lr14/ - /lr20/ проходила порог скелета с зазором в одну тысячную.

    Стало: вся основная колонка, из которой вычтено ровно три вещи, и каждая
    по названной причине.
      * два блока из prose.CONSTANT_HEADS — методологические оговорки,
        объявленные общими для всех страниц и написанные один раз. PLAYBOOK
        прямо требует сносить их в общий блок, ИСКЛЮЧЁННЫЙ из сравнения:
        фраза, верная сразу для всех страниц, на каждой из них — чистый
        близнец, и держать её в выборке значит мерить не то;
      * рекламные коробки и поле поиска — обстановка, а не содержимое;
      * script и style — иначе «text-align:right» считается словом «right».

    Порог при этом НЕ ослаблен: 0,70 и 0,95 те же, что были.
    """
    col = main_column(html)
    if col is None:
        return ""
    col = re.sub(r'<div class="bx-ad .*?</div>', " ", col, flags=re.S)
    col = re.sub(r'<form class="bx-find.*?</form>', " ", col, flags=re.S)
    col = re.sub(r"<script.*?</script>|<style.*?</style>", " ", col, flags=re.S)
    keep = []
    for i, part in enumerate(re.split(r"<h2>", col)):
        if i:
            head = re.sub(r"<[^>]+>", "", part.split("</h2>")[0]).strip()
            if head in P.CONSTANT_HEADS:
                continue
        keep.append(part)
    return re.sub(r"<[^>]+>", " ", " ".join(keep))


def jaccard(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


# Кто отклонён и почему, поимённо: сводка по причинам не даёт починить
# страницу, а именно страница и пропадает.
DROPPED = []


def build_cell_pages(cs, ctx, hubs):
    """Отбор и выпуск. Мера успеха — не сколько собрано, а сколько ПЕРЕЖИЛО.

    Гейта близнецов ДВА, и они спрашивают разное. По видимому тексту — то, что
    видят читатель и поиск. По скелету фразы, без чисел и кодов, — «тот же
    абзац с подставленной величиной», ровно та болезнь, из-за которой на
    KeepsUntil выжило пять страниц из 593.
    """
    ranks = C.rank_in_shell(cs)
    stats = {"всего": len(cs), "выпущено": 0, "отклонено": {}}

    DROPPED[:] = []

    def drop(why, code=None):
        stats["отклонено"][why] = stats["отклонено"].get(why, 0) + 1
        DROPPED.append((why, code))

    pages, accepted = {}, []
    seen_text, seen_skel = [], []
    worst_t = worst_s = 0.0
    for cell in sorted(cs, key=lambda c: c["code"]):
        if len(C.facts(cell, cs, ranks)) < MIN_FACTS:
            drop("меньше %d вычисленных величин" % MIN_FACTS, cell["code"])
            continue
        s = P.shape(cell, cs, ctx)
        if not s["shell"]:
            drop("нет опубликованного габарита", cell["code"])
            continue
        html = product_page(cell, s, cs, hubs)
        bad = None
        for chunk in re.split(r"<h2>", html)[1:]:
            h2 = re.sub(r"<[^>]+>", "", chunk.split("</h2>")[0])
            # Два служебных блока объявлены общими для всех страниц и написаны
            # один раз; правило «ответ первым с числом» к ним не относится —
            # они не отвечают на запрос, а очерчивают границы и метод.
            if h2 in P.CONSTANT_HEADS:
                continue
            sect = chunk.split("</h2>", 1)[1] if "</h2>" in chunk else ""
            if h2 in FIGURE_HEADS:
                if 'class="bx-fig"' not in sect:
                    bad = "раздел чертежа без чертежа"
                    break
                continue
            para = section_answer(sect)
            if para is None:
                bad = "раздел без абзаца разбора"
                break
            n = P.wc(para)
            lo, hi = window_for(h2)
            if not lo <= n <= hi:
                bad = "абзац вне окна %d-%d слов" % (lo, hi)
                break
            if not re.search(r"[0-9]", para):
                bad = "абзац без числа"
                break
        if bad:
            drop(bad, cell["code"])
            continue
        text = own_prose(html)
        st, sk = _shingles(text, TEXT_PAT), _shingles(text, SKEL_PAT)
        if not st:
            drop("пустая своя проза", cell["code"])
            continue
        jt = max((jaccard(st, o) for o in seen_text), default=0.0)
        js = max((jaccard(sk, o) for o in seen_skel), default=0.0)
        if jt > TWIN_TEXT:
            drop("близнец по видимому тексту", cell["code"])
            continue
        if js >= TWIN_SKELETON:
            drop("тот же абзац с другой величиной", cell["code"])
            continue
        worst_t, worst_s = max(worst_t, jt), max(worst_s, js)
        seen_text.append(st)
        seen_skel.append(sk)
        pages["/%s/" % slug(cell)] = html
        accepted.append((cell, s))
        stats["выпущено"] += 1
    stats["сходство текста"] = round(worst_t, 3)
    stats["сходство скелета"] = round(worst_s, 3)
    # МЕДИАНА, а не только максимум. По максимуму нельзя судить о корпусе:
    # KeepsUntil собрался с медианой 0,82 при том, что «максимум» звучал
    # так же, как здесь. Считается по ВЫПУЩЕННЫМ страницам, попарно.
    stats["медиана текста"] = _median_pairs(seen_text)
    stats["медиана скелета"] = _median_pairs(seen_skel)
    return accepted, pages, stats


def _median_pairs(sets):
    """Медиана попарного сходства. Выборка меньше двух страниц медианы не
    имеет, и притворяться нулём она не должна."""
    if len(sets) < 2:
        return None
    vals = sorted(jaccard(sets[i], sets[j])
                  for i in range(len(sets)) for j in range(i + 1, len(sets)))
    n = len(vals)
    med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return round(med, 3)


INTRO_HEADS = P.INTRO_HEADS   # один список на весь сайт


# Абзацы, которые НЕ являются разбором раздела: подпись к столбцам, подпись
# к рисунку, строка чужих маркировок, строка источника.
NOT_THE_ANSWER = ("bx-legend", "bx-cap", "bx-also", "bx-src", "bx-nolink")

# Разделы, содержимое которых — ЧЕРТЁЖ, а не абзац прозы. Исключение
# ОБЪЯВЛЕНО, потому что раньше оно существовало молча: правило искало «первый
# <p> сразу за </h2>», а за «<h2>Drawn to scale</h2>» стоит «<div
# class="bx-fig">», регулярка не совпадала — и раздел уходил из-под правила
# незамеченным. У объявленного исключения есть цена: в таком разделе обязан
# СТОЯТЬ чертёж, иначе это просто раздел без содержимого.
FIGURE_HEADS = ("Drawn to scale",)


def section_answer(sect):
    """Абзац РАЗБОРА внутри раздела: первый <p>, который не подпись.

    Правило было «первый <p> сразу за </h2>» и держалось соседством. Когда
    таблицу замен подняли выше разбора — ответ обязан быть виден раньше
    разговора о нём, — между заголовком и разбором встали подпись к столбцам
    и сама таблица, и правило по соседству перестало находить что-либо
    вовсе. Ищем по РОЛИ абзаца.
    """
    for m in re.finditer(r"<p([^>]*)>(.*?)</p>", sect, re.S):
        if any(c in m.group(1) for c in NOT_THE_ANSWER):
            continue
        return re.sub(r"<[^>]+>", " ", m.group(2))
    return None


def window_for(h2):
    """Окно абзаца зависит от того, ОТВЕЧАЕТ он или ВВОДИТ таблицу ниже.
    Требовать сорок слов от подводки — значит требовать воды."""
    if h2 in INTRO_HEADS or D.HEAD_KIND.get(h2) == "intro":
        return P.INTRO_MIN, P.INTRO_MAX
    return P.ANSWER_MIN, P.ANSWER_MAX


# ЗАГОЛОВКИ ПЛОЩАДКИ. Оба живых сайта ветки их несут, этот не нёс ни одного.
#
# РАМКОЙ УПРАВЛЯЕТ X-Frame-Options, А НЕ frame-ancestors, и это вынужденно.
# Cloudflare Pages ДОБАВЛЯЕТ заголовок правила пути к заголовку `/*`, а не
# заменяет его: у /embed/* выходило ДВЕ политики CSP сразу, браузер применяет
# их пересечение, и `frame-ancestors 'none'` из общего правила побеждал
# `frame-ancestors *` из частного. Виджеты не встраивались никуда — проверено
# на живой выкладке, curl отдавал два заголовка content-security-policy.
#   Поэтому frame-ancestors не объявляется вовсе, рамку на сайте запрещает
# X-Frame-Options: DENY, а у /embed/* он СНИМАЕТСЯ оператором `!` — это
# документированный способ Pages убрать унаследованный заголовок, и он
# работает (на виджете X-Frame-Options не приходит).
#
# Развилка здесь не украшение: 145 страниц /embed/* сделаны
# затем, чтобы стоять в чужом iframe на форуме или ремонтном сайте, и страница
# элемента прямо предлагает готовый сниппет. Глухой DENY на всё убил бы ровно
# тот канал распространения, ради которого виджеты и написаны. Поэтому DENY
# на сайт и разрешение на /embed/*, и объявлено это ДВУМЯ заголовками сразу:
# X-Frame-Options старый и понимает только DENY/SAMEORIGIN, а
# frame-ancestors — новый и он тут главный.
#
# ХЭШ ВМЕСТО 'unsafe-inline' НЕ ВЗЯТ СОЗНАТЕЛЬНО. Скрипт на всех страницах
# один и тот же, и один sha256 закрыл бы script-src намертво — но рядом с ним
# в разметке лежат два инертных блока (указатель поиска и структурные
# данные), политика в разных браузерах трактует их по-разному, а проверить
# отданные заголовки можно только на самой площадке: локальный сервер файл
# _headers не читает вовсе. Строгая политика у нас уже дважды молча убивала
# работающий код — сборка зелёная, байты совпадают, функции нет. Ужесточать
# это место можно только с проверкой в браузере ПОСЛЕ выкладки.
#
# Content-Security-Policy без 'unsafe-inline' для скриптов написать нельзя:
# поиск и указатель встроены в страницу намеренно (ноль сторонних запросов —
# решение ветки). Вместо этого запрещено ВСЁ внешнее: default-src 'self',
# connect-src 'none', object-src 'none', base-uri 'none'. Ни один сторонний
# запрос страница сделать не может, а гейт «браузер не ходит наружу»
# проверяет то же самое по отданным байтам с другой стороны.
_YEAR_S = 365 * 24 * 60 * 60

_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'none'; object-src 'none'; "
        "base-uri 'none'; form-action 'none'")

# Комментарии здесь ПО-АНГЛИЙСКИ: это отдаваемый файл, а не исходник, и гейт
# «язык страницы английский» прав, когда краснеет на русском слове в нём.
HEADERS = """/*
  Strict-Transport-Security: max-age=%(year)d; includeSubDomains
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  X-Frame-Options: DENY
  Content-Security-Policy: %(csp)s

# Widgets exist to be framed. Framing is allowed here on purpose: these
# documents carry no header, no navigation, no input and no third-party
# request, so there is nothing in them to click but one link out.
/embed/*
  ! X-Frame-Options

# The dated snapshot carries its date in the filename, so what is served
# at this address will never change.
/data/batterycross-cells-*.csv
  Cache-Control: public, max-age=%(year)d, immutable
""" % {"csp": _CSP, "year": _YEAR_S}

# Адрес страницы — один. Второй адрес того же содержимого делит вес ссылок
# надвое и заводит в выдаче дубль.
REDIRECTS = """/index.html  /  301
"""


def assemble():
    cs = C.build_cells()
    ctx = P.context(cs)

    # Хабы оболочек считаются ДО страниц: хлебная крошка ссылается на них.
    groups = {}
    for c in cs:
        s = C.shell(c)
        if s:
            groups.setdefault(s, []).append(c)
    hubs = {shell_slug(s) for s, m in groups.items() if len(m) >= MIN_HUB}

    # Ссылка ведёт на страницу элемента, если она выпущена, и на страницу
    # его оболочки, если нет. Но состав выпущенного зависит от страниц, а
    # страницы — от ссылок. Считаем до неподвижной точки; множество только
    # сокращается, поэтому цикл сходится. Первая версия без этого дала на
    # KeepsUntil двадцать ссылок в никуда.
    C.SHELL_HUBS = set(hubs)
    C.PUBLISHED = {c["code"] for c in cs}
    globals()["SEARCH_BLOCK"] = search_block(cs)
    accepted, pages, stats = build_cell_pages(cs, ctx, hubs)
    globals()["CELLS"] = cs
    globals()["STATS"] = site_stats(cs, accepted, hubs)
    for _round in range(6):
        got = {c["code"] for c, _s in accepted}
        if got == C.PUBLISHED:
            break
        C.PUBLISHED = got
        globals()["SEARCH_BLOCK"] = search_block(cs)
        accepted, pages, stats = build_cell_pages(cs, ctx, hubs)
        globals()["CELLS"] = cs
        globals()["STATS"] = site_stats(cs, accepted, hubs)
    else:
        raise AssertionError("состав страниц не сошёлся за 6 кругов")
    stats["кругов"] = _round + 1
    pages.update(shell_hubs(accepted, cs))
    pages.update(size_hubs(cs))
    pages["/codes/"] = code_index(accepted, cs)
    pages["/method/"] = method_page(cs)

    shell_rows = []
    for s, members in sorted(groups.items(),
                             key=lambda kv: (-len(kv[1]), str(kv[0]))):
        if len(members) < MIN_HUB:
            continue
        sl = shell_slug(s)
        live = sum(1 for c in members if c["active"])
        shell_rows.append((("shell/%s" % sl), C.shell_label(s),
                           [str(len(members)), str(live),
                            esc(P.listing(sorted({chem(c) for c in members})))]))
    pages["/shells/"] = list_page(
        "/shells/", "Battery shells that carry %d or more codes" % MIN_HUB,
        "Every envelope in the data with %d or more designations in it, "
        "and how many of them are still made." % MIN_HUB,
        "Shells", "An envelope is a diameter and a height, and it is what "
        "decides whether a cell enters the compartment at all. %s here carry "
        "%d designations or more, which is where substitution questions "
        "start." % (P.plural(len(shell_rows), "envelope"), MIN_HUB),
        shell_rows, ("Shell", "Designations", "Still listed", "Chemistries"))

    size_rows = []
    for name in P.POPULAR_SIZES:
        members = [c for c in cs if c.get("size") == name]
        if len(members) < 2:
            continue
        live = sum(1 for c in members if c["active"])
        size_rows.append((("size/%s" % size_slug(name)), name,
                          [str(len(members)), str(live),
                           esc(P.listing(sorted({chem(c) for c in members})))]))
    pages["/sizes/"] = list_page(
        "/sizes/", "Common battery sizes and what comes in them",
        "AA, AAA, C, D and the rest: every designation sold in each, with "
        "voltages and chemistries.",
        "Common sizes", "The name on the packet is a shape, not a "
        "specification. Each of these sizes is made in more than one "
        "chemistry, and more than one of them is made in more than one "
        "voltage.", size_rows, ("Size", "Designations", "Still listed",
                                "Chemistries"))

    gone = sorted((c for c in cs if not c["active"] and C.shell(c)),
                  key=lambda c: c["code"])
    pub = {x["code"] for x, _s in accepted}
    gone_rows = []
    for c in gone:
        reps = C.replacements(c, cs)
        best = reps[0] if reps else None
        gone_rows.append((link_to(c).strip("/"), c["code"],
                          [esc(C.shell_label(C.shell(c))), volts(c),
                           # Единственный ответ страницы обязан быть ССЫЛКОЙ:
                           # человек дочитал до названия замены и упирался в
                           # обычный текст.
                           ('<a href="%s">%s</a>'
                            % (link_to(best["cell"]),
                               esc(best["cell"]["code"]))) if best else
                           # «Ничего такого же размера» — утверждение о
                           # мире, а знаем мы КАТАЛОГ. Человек читает первое
                           # и перестаёт искать.
                           ('<a href="/shell/%s/">none in this catalog</a>'
                            % shell_slug(C.shell(c))
                            if shell_slug(C.shell(c)) in C.SHELL_HUBS
                            else "none in this catalog"),
                           (P.FIT_WORD.get(best["fit"], best["fit"])
                            if best else "&mdash;"),
                           (('<span class="bx-v bx-v-%s">%s %s'
                             '<span class="bx-vtag">%s</span></span>')
                            % (best["volt"]["class"], volts(best["cell"]),
                               P.pct_signed(best["volt"]["pct"]),
                               P.V_TAG.get(best["volt"]["class"], "unknown"))
                            if best and best["volt"] else "&mdash;")]))
    pages["/discontinued/"] = list_page(
        "/discontinued/", "Batteries no longer in the Energizer catalog",
        "Every designation Energizer no longer lists, with published "
        "dimensions, the closest cell it still lists and how that one fits.",
        "No longer in the Energizer catalog",
        "%s no longer have a part in the Energizer catalog. The %d listed here "
        "are the ones "
        "whose dimensions the maker publishes, which is what it takes to say "
        "anything about fit; the remaining %d are in the "
        '<a href="/codes/">code index</a>. The table names the closest '
        "current cell, says in what sense it fits AND what the voltage "
        "difference costs — the two never answer each other. For %d of them "
        "this catalog lists nothing of that size at all, which is a statement "
        "about the catalog and not about the world."
        % (P.plural(STATS["gone"], "designation"), STATS["gone_sized"],
           STATS["gone"] - STATS["gone_sized"],
           sum(1 for r in gone_rows if "none in this catalog" in r[2][2])),
        gone_rows, ("Cell", "Envelope", "Volts", "Closest current", "Fit",
                    "What the swap costs"), applies=True, anchor="d-")

    pages["/"] = home(accepted, cs, hubs)
    pages["/about/"] = about_page(cs)
    # Виджеты — по одному на выпущенный элемент, статические и без скрипта.
    for cell, s in accepted:
        pages["/embed/%s/" % slug(cell)] = embed_page(cell, s, cs)
    pages.update(legal_pages())

    stats["тонких снято с индексации"] = enforce_floor(pages)

    files = {}
    for path, html in pages.items():
        if path.endswith(".html"):
            files[path.lstrip("/")] = html
        else:
            files[(path.strip("/") + "/index.html").lstrip("/")] = html
    # В карту сайта попадает то, что РАЗРЕШЕНО к индексации разметкой самой
    # страницы, а не всё подряд: карта, зовущая робота на noindex-страницу,
    # это приглашение посмотреть на то, что мы сами признали тонким.
    indexed = [p for p, h in pages.items()
               if not p.endswith(".html") and INDEX_META in h]
    files["sitemap.xml"] = sitemap(indexed)
    files["robots.txt"] = robots()
    files["_headers"] = HEADERS
    files["_redirects"] = REDIRECTS
    # Набор данных публикуется ДВУМЯ адресами: датированный — для цитирования,
    # latest — для того, кто хочет свежий. Содержимое одно и то же, поэтому
    # разойтись они не могут.
    csv_text = dataset_csv(cs, {c["code"] for c, _s in accepted})
    files[DATASET_PATH.lstrip("/") % DATA_SNAPSHOT.isoformat()] = csv_text
    files[DATASET_LATEST.lstrip("/")] = csv_text
    return files, stats, accepted, cs


# ---------------------------------------------------------------- пол объёма

# PLAYBOOK §1: 1500-4000 слов разбора на той же странице, и требование
# рекламной сети проверяется ПОСТРАНИЧНО по всему инвентарю. Страница, которая
# до пола не дотягивает, роботу не предлагается: у MileageCurve 238 страниц из
# 353 Google обошёл и НЕ ВЗЯЛ, и это приговор содержанию, а не задержка
# обхода. Она остаётся на месте — по ней ходят люди и внутренние ссылки, — но
# из карты сайта уходит и несёт noindex.
WORD_FLOOR = 1500

# Институциональная оболочка (PLAYBOOK §8) обязана существовать и не обязана
# быть длинной: About, Contact, Privacy, Terms и страница ошибки — не
# содержательный инвентарь, рекламы на них нет вовсе (см. AD_NEVER), и
# требовать от них полутора тысяч слов значило бы разводить воду ровно там,
# где нужна точность. Список ЯВНЫЙ и сверяется гейтом.
FLOOR_EXEMPT = ("/privacy/", "/terms/", "/contact/", "/about/", "/404.html")

INDEX_META = '<meta name="robots" content="index, follow, max-image-preview:large">'
NOINDEX_META = '<meta name="robots" content="noindex, follow">'


def page_words(html):
    """Видимые слова основной колонки без обстановки — та же выборка, по
    которой сеть считает «содержательную» страницу. Реклама и поле поиска
    вычитаются: собственные слова инвентаря не могут оправдывать инвентарь."""
    col = main_column(html)
    if col is None:
        return 0
    col = re.sub(r'<div class="bx-ad .*?</div>', " ", col, flags=re.S)
    col = re.sub(r'<form class="bx-find.*?</form>', " ", col, flags=re.S)
    col = re.sub(r"<script.*?</script>|<style.*?</style>", " ", col, flags=re.S)
    return P.wc(col)


def enforce_floor(pages):
    """Страница ниже пола перестаёт быть индексируемой. Возвращает список
    снятых — их печатает сборка, потому что молча ужавшийся корпус хуже
    громко ужавшегося."""
    thin = []
    for path, html in sorted(pages.items()):
        if path in FLOOR_EXEMPT or page_words(html) >= WORD_FLOOR:
            continue
        if INDEX_META not in html:
            continue          # страница и так закрыта от индексации
        # Подмена литерала: проверяем, что попали ровно один раз и ровно туда.
        assert html.count(INDEX_META) == 1, "метка robots не единственная"
        pages[path] = html.replace(INDEX_META, NOINDEX_META)
        assert NOINDEX_META in pages[path] and INDEX_META not in pages[path]
        thin.append(path)
    return thin


def write(files):
    # Windows держит открытым САМ каталог выкладки, и rmtree падает на
    # последнем rmdir, уже вычистив содержимое. Чистим содержимое, сам
    # каталог оставляем: на диске всё равно ровно то, что собрано.
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            full = os.path.join(OUT, name)
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
    for rel, text in files.items():
        full = os.path.join(OUT, rel.replace("/", os.sep))
        d = os.path.dirname(full)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(full, "w", encoding="utf-8", newline="\n").write(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    files, stats, accepted, cs = assemble()
    write(files)
    print("обозначений в данных:        %d" % stats["всего"])
    print("страниц элементов выпущено:  %d" % stats["выпущено"])
    print("кругов до сходимости ссылок: %d" % stats.get("кругов", 1))
    print("файлов в dist:               %d" % len(files))
    print("сходство по ВСЕМУ видимому тексту (кроме общих блоков):")
    print("  текст:  медиана %.3f, максимум %.3f (порог %.2f)"
          % (stats["медиана текста"], stats["сходство текста"], TWIN_TEXT))
    print("  скелет: медиана %.3f, максимум %.3f (порог %.2f)"
          % (stats["медиана скелета"], stats["сходство скелета"],
             TWIN_SKELETON))
    thin = stats.get("тонких снято с индексации") or []
    print("пол объёма %d слов: %d страниц индексируются, %d сняты"
          % (WORD_FLOOR,
             sum(1 for t in files.values()
                 if isinstance(t, str) and INDEX_META in t), len(thin)))
    if thin:
        print("  сняты: %s" % ", ".join(thin[:24]))
    if stats["отклонено"]:
        print()
        print("отклонено:")
        for k, v in sorted(stats["отклонено"].items(), key=lambda x: -x[1]):
            print("  %-46s %d" % (k, v))
