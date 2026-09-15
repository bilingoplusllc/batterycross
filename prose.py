# -*- coding: utf-8 -*-
"""Проза BatteryCross. Ветвится по ФОРМЕ данных, а не подставляет числа в скелет.

ПОЧЕМУ ЭТОТ ФАЙЛ УСТРОЕН ТАК. На KeepsUntil первая сборка дала 593 страницы, и
гейт близнецов оставил пять: медиана сходства прозы 0,82, десятая часть пар —
побайтово одинаковый текст. Причина была одна: один шаблон абзаца с
подставленными числами, то есть дословно то, что Google называет scaled content
abuse. Решение D-013 закрепило правило, и здесь оно применяется с первой
страницы, а не после сборки корпуса.

ФОРМА ДАННЫХ ЗДЕСЬ — ЭТО:
  · выпускается элемент или снят (снятых две трети, и это главный раздел);
  · есть ли полная замена, только более низкая, или нет никакой;
  · чем оборачивается разница напряжений у лучшей замены;
  · сходится ли обозначение МЭК с заявленным размером;
  · сколько обозначений живёт в той же оболочке;
  · круглый корпус или призматический;
  · известна ли ёмкость и где элемент по плотности энергии.

Форма выбирает, ЧТО сказать первым; величина — КАК это сказать.

ЯЗЫК САЙТА АНГЛИЙСКИЙ, американское написание.

БЕЗОПАСНОСТЬ ВЫШЕ КРАСОТЫ. Ни одна фраза не имеет права сказать «подойдёт», не
сказав, что именно подойдёт: посадка и электрика называются раздельно всегда.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cells as C  # noqa: E402

# Два окна абзаца: отвечающий на запрос блок обязан быть самодостаточным
# пассажем, вводящий стоящую ниже таблицу — не обязан и, раздутый, набирается
# водой, а вода у всех страниц одинаковая.
ANSWER_MIN, ANSWER_MAX = 35, 72
INTRO_MIN, INTRO_MAX = 18, 56

QUOTE = chr(34)

# Имена типоразмеров, которые человек ВБИВАЕТ В ПОИСК. «Miniature», «Other» и
# «Multi Cell» — это рубрики каталога производителя, а не то, чем предмет
# называют вслух, и в этот список они не входят.
POPULAR_SIZES = ("AA", "AAA", "AAAA", "C", "D", "N", "9V", "J", "F", "Lantern")

# Один словарь на весь сайт: название химии, приведённое к одному слову,
# нужно и прозе, и сверке буквы обозначения с полем записи.
CHEM_SHORT = C.CHEM_CANON

# Характерное напряжение каждой химии, ПОСЧИТАННОЕ по снимку. Заполняется
# один раз в context(): число в прозе не набирается руками.
CHEM_VOLTS = {}

# Пересечение оболочек лития с щелочными и серебряными, ПОСЧИТАННОЕ по
# снимку: (сколько, из скольких). Заполняется в context().
CHEM_SHARE = {}

# Отношение двух величин — тоже величина. Набранное «roughly double» стояло
# на 33 страницах, из которых 17 печатали 1,5 В: это не вдвое, это столько
# же. Слово выбирается ПО ЧИСЛУ, а не по химии.
RATIO_UP = {2: "roughly double the nominal of %s",
            3: "roughly three times the nominal of %s",
            4: "roughly four times the nominal of %s",
            5: "roughly five times the nominal of %s",
            6: "roughly six times the nominal of %s",
            8: "roughly eight times the nominal of %s"}
RATIO_DOWN = {2: "roughly half the nominal of %s",
              3: "roughly a third of the nominal of %s",
              4: "roughly a quarter of the nominal of %s"}
RATIO_SAME = "the same nominal %s carry"


def ratio_phrase(v, bases, noun):
    """Во сколько раз `v` больше каждой из `bases` — словами, ПОСЧИТАННО.

    Ответ обязан совпасть по ВСЕМ основаниям: если 3 В это «вдвое» и против
    щелочного, и против серебряного, слово одно; если основания разводят его
    на разные слова, отношение не называется вовсе и возвращается None —
    предложение тогда печатает сами числа. Кратность округляется, только
    когда она и правда близка к целому (8 %), иначе отношения нет.
    """
    bases = [b for b in bases if b]
    if not v or not bases:
        return None
    words = set()
    for b in bases:
        r = float(v) / float(b)
        if 0.95 <= r <= 1.05:
            words.add(RATIO_SAME % noun)
            continue
        table = RATIO_DOWN if r < 1 else RATIO_UP
        x = (1.0 / r) if r < 1 else r
        n = int(round(x))
        if n >= 2 and abs(x - n) <= 0.08 * n and n in table:
            words.add(table[n] % noun)
        else:
            words.add(None)
    if len(words) != 1 or None in words:
        return None
    return words.pop()


def ratio_selftest():
    """Известные ответы для отношения: чистую функцию проверяют не тем же
    выражением, которым её написали, а списком правды."""
    n = "the alkaline and silver classes"
    known = [((3.0, [1.5, 1.55]), "roughly double the nominal of " + n),
             ((1.5, [1.5, 1.55]), "the same nominal " + n + " carry"),
             ((9.0, [1.5, 1.55]), "roughly six times the nominal of " + n),
             ((6.0, [1.5, 1.55]), "roughly four times the nominal of " + n),
             ((1.2, [1.5, 1.55]), None),
             ((3.0, [1.5, 0.9]), None),
             ((None, [1.5]), None),
             ((3.0, []), None)]
    bad = []
    for (v, bs), want in known:
        got = ratio_phrase(v, bs, n)
        if got != want:
            bad.append((v, bs, want, got))
    return bad

# Что означает разница напряжений. Формулировки разные по СМЫСЛУ, а не по
# синонимике: у каждого класса своё последствие, и оно называется словами.
# Что означает разница напряжений. У КАЖДОГО класса И У КАЖДОГО
# НАПРАВЛЕНИЯ свои слова: «прибор увидит меньше, чем ждёт» и «прибор увидит
# больше, чем ждёт» — разные последствия, а не одно с другим знаком. Одна
# рамка на оба направления уже стоила ферме девяти страниц с советом наоборот.
V_MEANING = {
    ("same", 0): "the same working voltage",
    ("minor", 1): "a few hundredths of a volt above, which almost nothing "
                  "notices",
    ("minor", -1): "a few hundredths of a volt below, which almost nothing "
                   "notices",
    ("calibration", 1): "high enough that a calibrated instrument reads above "
                        "true",
    ("calibration", -1): "low enough that a calibrated instrument reads below "
                         "true",
    ("wrong", 1): "a higher voltage class altogether",
    ("wrong", -1): "a lower voltage class altogether",
}

# То же самое в подводке, где последствие называется на КАЖДОГО кандидата.
V_SHORT = {
    ("same", 0): "the same working voltage",
    ("minor", 1): "a shade high",
    ("minor", -1): "a shade low",
    ("calibration", 1): "which reads high",
    ("calibration", -1): "which reads low",
    ("wrong", 1): "a higher voltage class",
    ("wrong", -1): "a lower voltage class",
}

# Последствие химии, которого столбец напряжения НЕ ВЫРАЖАЕТ. Цена
# цинк-воздушного элемента в часах — не 6,9% вольта. Ключи приходят из
# cells.chemistry_caveat, слова живут здесь.
CAVEAT_WORDS = {
    "rechargeable": "it is rechargeable, and a rechargeable cell is never a "
                    "drop-in for a primary one whatever the size",
    "air": "it is zinc air, which begins discharging the moment its tab comes "
           "off and needs the air a closed compartment does not give it",
    "carbon": "it is carbon zinc, which holds a fraction of the charge at the "
              "same nominal volts and is the chemistry that leaks",
}

CAVEAT_SHORT = {
    "rechargeable": "rechargeable, never a drop-in",
    "air": "zinc air, which must breathe",
    "carbon": "carbon zinc, which holds far less",
}


def _v_key(pct):
    """Класс от consequence_class плюс направление от знака ТОГО ЖЕ процента."""
    klass = C.consequence_class(pct / 100.0)
    return ("same", 0) if klass == "same" else (klass, 1 if pct > 0 else -1)


def v_meaning(pct):
    """Последствие СЛОВАМИ, полной фразой."""
    return V_MEANING[_v_key(pct)]


def v_short(pct):
    """Оно же коротко: для подводки, где кандидатов несколько."""
    return V_SHORT[_v_key(pct)]


def caveat_words(key):
    return CAVEAT_WORDS[key] if key else None


def caveat_short(key):
    return CAVEAT_SHORT[key] if key else None


# Буквы, чьё НАЗВАНИЕ начинается с гласного звука: эй, и, эф, эйч, ай, эл,
# эм, эн, оу, ар, эс, экс. Обозначения читаются по буквам, поэтому «an LR44»,
# но «a CR2032».
_AN_LETTERS = set("AEFHILMNORSX")

# Слова, у которых буква и звук расходятся. Список короткий намеренно: он
# закрывает то, что реально встречается в тексте справочника.
_AN_WORDS = ("hour", "honest", "honour", "honor", "heir")
_A_WORDS = ("unit", "united", "unique", "useful", "user", "usual", "one",
            "once", "european", "universal", "uniform", "utility")


# Неправильные формы: остальные получаются по правилу.
_VERB_IRREGULAR = {"are": "is", "have": "has", "do": "does", "were": "was",
                   "go": "goes"}


def verb(n, plural_form):
    """Форма глагола по числу подлежащего.

    Шаблоны писались с глаголом во множественном, а подлежащее считается: на
    живых страницах вышло «1 cell sit», «1 designation out of production
    share», «The 1 option below share the diameter».
    """
    if n != 1:
        return plural_form
    w = plural_form
    if w in _VERB_IRREGULAR:
        return _VERB_IRREGULAR[w]
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    return w + "s"


def verb_selftest():
    known = [(1, "share", "shares"), (2, "share", "share"),
             (1, "sit", "sits"), (1, "run", "runs"), (1, "carry", "carries"),
             (1, "differ", "differs"), (1, "are", "is"), (2, "are", "are"),
             (1, "have", "has"), (1, "do", "does"), (1, "reach", "reaches"),
             (1, "fit", "fits"), (1, "go", "goes"), (0, "share", "share")]
    return [(n, w, want, verb(n, w)) for n, w, want in known
            if verb(n, w) != want]


def article(word, cap=False):
    """«a» или «an» перед словом — по звуку, а не по букве."""
    w = word.strip()
    while w and not (w[0].isalnum()):
        w = w[1:]
    if not w:
        return "A" if cap else "a"
    low = w.lower()
    if low.startswith(_AN_WORDS):
        out = "an"
    elif low.startswith(_A_WORDS):
        out = "a"
    elif w[0].isdigit():
        # Цифры читаются по одной: восемь — единственная, начинающаяся с
        # гласного звука.
        out = "an" if w[0] == "8" else "a"
    elif w.isupper() or len(w) == 1:
        out = "an" if w[0].upper() in _AN_LETTERS else "a"
    else:
        out = "an" if low[0] in "aeiou" else "a"
    return out.capitalize() if cap else out


def article_selftest():
    """Известные ответы. Гейт, сверяющий вывод с той же функцией, которую он
    проверяет, соглашается сам с собой — поэтому здесь список правды."""
    known = [
        ("AA", "an"), ("AAA", "an"), ("AAAA", "an"), ("C", "a"), ("D", "a"),
        ("N", "an"), ("F", "an"), ("J", "a"), ("9V", "a"), ("Lantern", "a"),
        ("alkaline", "an"), ("lithium", "a"), ("silver oxide", "a"),
        ("zinc air", "a"), ("mercuric oxide", "a"), ("carbon zinc", "a"),
        ("nickel-metal hydride", "a"), ("manganese dioxide", "a"),
        ("LR44", "an"), ("CR2032", "a"), ("EPX625", "an"), ("PX625", "a"),
        ("MR9", "an"), ("SR44", "an"), ("HR03", "an"), ("R6", "an"),
        ("8LR932", "an"), ("1811A", "a"), ("hour", "an"), ("unit", "a"),
        ("instrument", "an"), ("compartment", "a"), ("honest", "an"),
    ]
    bad = [(w, want, article(w)) for w, want in known if article(w) != want]
    return bad


def esc(s):
    # str(None) давал непустую строку «None», она истинна, и запасной вариант
    # «esc(...) or mdash» не срабатывал НИКОГДА: питоновский None стоял
    # значением ячейки на четырёх витринах типоразмеров.
    if s is None:
        return ""
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace(QUOTE, "&quot;")


# Ссылка на знак — НЕ слово. «&mdash;» проходило вычистку тегов целым и
# совпадало со словом «mdash»: на /discontinued/ таких ссылок 125, счётчик
# печатал 1543 слова там, где видимых 1419, при поле объёма 1500 — и
# страница уезжала в индекс и в карту сайта ниже пола. Пол ставит ЭТОТ
# счётчик, поэтому ошибка счётчика была ошибкой отбора, а не отчёта.
CHAR_REF = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}"
                      r"|[A-Za-z][A-Za-z0-9]{1,31});")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def wc(text):
    """Видимые слова. Вычищаются ОБЕ невидимые вещи: разметка и ссылки на
    знаки. Тег словом не считался никогда, ссылка на знак считалась."""
    return len(WORD.findall(CHAR_REF.sub(" ",
                                         re.sub(r"<[^>]+>", " ", text))))


def mm(v):
    return C._mm(v) if v is not None else NOT_PUBLISHED


# ОДНО ПРЕДЛОЖЕНИЕ НА ВЕСЬ САЙТ, И ОНО САМОЕ ВАЖНОЕ. Стояло оно только в
# подвале — на 98% высоты страницы, — а витрины делают конкретные
# рекомендации «меняй это на то» в первой четверти. Оговорка, которую видно
# после решения, не оговорка. Живёт здесь, потому что печатают её три разных
# модуля, а три копии одной фразы однажды разойдутся — у нас это уже было с
# «roughly double» на 17 страницах.
SUBSTITUTE_CAVEAT = "A cell that fits is not always a safe substitute."


def chem(cell):
    c = cell.get("chemistry") or ""
    return CHEM_SHORT.get(c, c.lower() or "unspecified chemistry")


def pct_num(x):
    """Процент числом. Десятая доля у трёхзначного значения — шум: «+700.0%»
    ничего не уточняет по сравнению с «+700%»."""
    return ("%.0f" % x) if abs(x) >= 100 else ("%.1f" % x)


def pct_signed(x):
    """Знаковый процент ОДНИМ правилом на весь сайт.

    Десятая доля у трёхзначного значения — шум: «+700.0%» не уточняет ничего
    против «+700%». А «+0.0%» — не число, а артефакт округления со знаком.
    """
    if abs(x) < 0.05:
        return "0%"
    return ("%+.0f%%" % x) if abs(x) >= 100 else ("%+.1f%%" % x)


def volt_pct(base, other):
    """ЕДИНСТВЕННЫЙ способ напечатать отношение напряжений В ПРОЗЕ.

    База — элемент ЭТОЙ страницы, other — тот, о ком фраза. И база, и знак
    берутся у cells.voltage_gap, то есть у той же функции, что печатает
    столбец «Voltage» в таблице страницы: разойтись им негде.

    Зачем функция. В depth.py стояли ДВЕ собственные арифметики, и обе
    считали не в ту сторону: «SR54 is the same 11.6 x 3.1 mm in silver oxide:
    1.55 V against this cell's 1.5 V, -3.2%» на четырнадцати страницах, где
    таблица четырьмя сотнями слов ниже печатала для SR54 +3.3%. Перевёрнуты
    были И база, И знак, потому что направление подразумевалось предлогом
    «against» в шаблоне, а не спрашивалось у данных.
    """
    g = C.voltage_gap(base, other)
    return pct_signed(g["pct"]) if g else None


# pct_shift здесь была и переворачивала знак ни для кого: ни одного
# вызова на весь сайт. Оставленный переворот направления — это заряженное
# ружьё, и на этой ферме такое уже стреляло.

# Пропуск НАЗЫВАЕТСЯ, а не печатается словом «unknown»: «unknown» читается
# как измеренное значение, которого никто не знает, а на деле производитель
# просто не публикует цифру.
NOT_PUBLISHED = "not published"


def volts_num(v):
    """Напряжение числом ОДНИМ правилом на весь сайт."""
    return ("%.2f" % v).rstrip("0").rstrip(".") + " V" if v else NOT_PUBLISHED


def cc_num(v):
    """Объём В ТОМ ВИДЕ, В КАКОМ ОН ПЕЧАТАЕТСЯ. ОДНО правило на весь сайт.

    Печаталось через mm(), то есть десятой долей, и у монеты 6,8 x 2,6 мм
    это «0»: страница печатала «шаг вниз по объёму: 0 кубических сантиметров
    против 0 у этого элемента» на 45 строках, а таблица рядом — «Volume 0
    cc». Ниже кубического сантиметра печатаются ДВЕ ЗНАЧАЩИЕ цифры: 0,094 и
    0,075 — разные числа, и разными они обязаны быть и на бумаге.
    """
    if v is None:
        return NOT_PUBLISHED
    if v >= 1.0:
        return ("%.1f" % v).rstrip("0").rstrip(".")
    return "%.2g" % v


def volts(cell):
    return volts_num(cell.get("volts"))


def listing(names):
    names = [str(n) for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return "%s and %s" % (names[0], names[1])
    return "%s and %s" % (", ".join(names[:-1]), names[-1])


def compose(lead, extras, lo=None, hi=None):
    """Рамка плюс добавки, пока абзац не дорастёт до нижней границы. Добавка,
    выбивающая за верхнюю, пропускается, а не обрезается."""
    lo = ANSWER_MIN if lo is None else lo
    hi = ANSWER_MAX if hi is None else hi
    body = lead
    for piece in extras:
        if wc(body) >= lo:
            break
        if not piece or wc(body + " " + piece) > hi:
            continue
        body += " " + piece
    return body


# -------------------------------------------------------------------- форма

def context(cs):
    """Что нужно знать о КОРПУСЕ, чтобы утверждение об элементе проверялось."""
    dens = sorted(x for x in (C.density_mwh_cc(c) for c in cs) if x)
    shells = {}
    for c in cs:
        s = C.shell(c)
        if s:
            shells.setdefault(s, []).append(c)
    CHEM_VOLTS.clear()
    CHEM_VOLTS.update(C.typical_volts_map(cs))
    CHEM_SHARE.clear()
    CHEM_SHARE["lithium"] = C.chem_envelope_overlap(
        cs, "lithium", ("alkaline", "silver oxide"))
    return {"dens": dens, "shells": shells, "total": len(cs),
            "ranks": C.rank_in_shell(cs),
            "obsolete": sum(1 for c in cs if not c["active"]),
            "active": sum(1 for c in cs if c["active"])}


def pct_below(sorted_vals, v):
    if not sorted_vals or v is None:
        return None
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] < v:
            lo = mid + 1
        else:
            hi = mid
    return int(round(100.0 * lo / len(sorted_vals)))


def shape(cell, cs, ctx):
    """Признаки, а не значения. По ним выбирается, ЧТО сказать."""
    fam = C.family(cell, cs)
    reps = C.replacements(cell, cs)
    drop = [r for r in reps if r["fit"] == "drop-in"]
    s = {
        "family": fam,
        "reps": reps,
        "dropin": drop,
        "best": reps[0] if reps else None,
        "shell": C.shell(cell),
        "form": (C.shell(cell) or ("none",))[0],
        "code": cell.get("code_check"),
        "rank": ctx["ranks"].get(cell["code"]),
        "energy": C.energy_mwh(cell),
        "dens": C.density_mwh_cc(cell),
        "active": cell["active"],
        "n_alias": len(cell.get("aliases") or []),
        "corpus": ctx["total"],
        "n_obsolete": ctx["obsolete"],
    }
    s["dens_pct"] = pct_below(ctx["dens"], s["dens"])
    # Родня по диаметру, но другой толщины: CR2032 / 2025 / 2016 / 2012.
    s["siblings"] = []
    if s["form"] == "round":
        d = s["shell"][1]
        coin = C.is_coin(cell)
        # Расстояния — через fit_gap, то есть по НАПЕЧАТАННЫМ десятым: сырое
        # вычитание несёт двоичный хвост (11.6 - 11.3 = 0.30000000000000004),
        # и «2 cells share this diameter» стояло там, где напечатанные
        # диаметры дают восемь. Обе границы страдали, и в разные стороны.
        s["siblings"] = sorted(
            (c for c in cs
             if c["code"] != cell["code"] and C.shell(c)
             and C.shell(c)[0] == "round"
             and abs(C.fit_gap(C.shell(c)[1], d)) <= C.FIT_MM
             and abs(C.fit_gap(C.shell(c)[2], s["shell"][2])) > C.FIT_MM
             # Тот же ДИАМЕТР — ещё не тот же класс предмета: монета и
             # цилиндр живут в разных отсеках и лестницы не образуют.
             and C.is_coin(c) == coin),
            key=lambda c: C.shell(c)[2])
    # Следует ли ёмкость за толщиной. Считается по ближайшей ступени той же
    # химии: если мА·ч на миллиметр совпадают в пределах десятой, объём внутри
    # оболочки расходуется одинаково, и это можно сказать вслух.
    s["scaling"] = None
    if s["siblings"] and cell.get("mah") and s["shell"]:
        same = [c for c in s["siblings"]
                if c.get("mah") and chem(c) == chem(cell)]
        if same:
            near = min(same, key=lambda c: abs(C.shell(c)[2] - s["shell"][2]))
            h1, h2 = s["shell"][2], C.shell(near)[2]
            if h1 > 0 and h2 > 0:
                a, b = cell["mah"] / h1, near["mah"] / h2
                if b > 0 and abs(a - b) / b <= 0.12:
                    s["scaling"] = (near, round(a, 1))
    # Родня по ходовому имени типоразмера: все AA, все D, все «Кроны».
    # Здесь живёт самое полезное сравнение сайта — что даёт одна и та же
    # оболочка при разной химии.
    s["popular"] = cell.get("size") if cell.get("size") in POPULAR_SIZES else None
    s["size_kin"] = []
    if s["popular"]:
        s["size_kin"] = [c for c in cs
                         if c["code"] != cell["code"] and c.get("size") == s["popular"]]
    kin_mah = [(c.get("mah"), c) for c in s["size_kin"] if c.get("mah")]
    s["size_mah"] = sorted(kin_mah, key=lambda x: -x[0])
    s["size_volts"] = sorted({c.get("volts") for c in s["size_kin"]
                              if c.get("volts")})
    s["v_class"] = s["best"]["volt"]["class"] if (
        s["best"] and s["best"]["volt"]) else None
    s["lead"] = _lead(cell, s)
    return s


def _lead(cell, s):
    """Что на этой странице главное. Порядок — по силе сигнала и по тому, что
    человеку нужнее: снятому элементу важнее замена, чем плотность энергии."""
    if not s["active"]:
        if not s["reps"]:
            # Самая населённая ветка корпуса: восемьдесят один снятый элемент
            # без замены. Одна рамка на все восемьдесят одну — это ровно тот
            # шаблон с подставленными числами, из-за которого на KeepsUntil
            # выжило пять страниц из 593. Дробим по тому, ЧТО ещё осталось.
            if "Mercury" in (cell.get("chemistry") or ""):
                return "gone_mercury"
            if len(s["siblings"]) >= 2:
                return "gone_siblings"
            if s["family"]:
                return "gone_family_gone"
            return "gone_nothing"
        if s["v_class"] == "calibration":
            return "gone_voltage_trap"
        if s["v_class"] == "wrong":
            # ОТДЕЛЬНАЯ рамка, а не та же с другим числом: «прибор покажет
            # не то» и «прибор сгорит» — разные последствия, и сайт про это.
            return "gone_voltage_wrong"
        if s["dropin"]:
            return "gone_dropin"
        # Направление промаха берётся из ДАННЫХ, а не из названия рамки:
        # «все тоньше» стояло на девяти страницах, где всё было ВЫШЕ.
        if s["reps"] and s["reps"][0]["fit"] == "taller":
            return "gone_taller_only"
        return "gone_shorter_only"
    # Ходовое имя типоразмера бьёт всё остальное: для «пальчиковой» главный
    # факт — что она пальчиковая, а не что её код округляет диаметр.
    if s["popular"] and len(s["size_kin"]) >= 2:
        vs = s["size_volts"] + ([cell["volts"]] if cell.get("volts") else [])
        # Разброс тоже считается ОДНОЙ функцией, чтобы рамка выбиралась по
        # той же величине, какую страница потом печатает.
        if len(set(vs)) >= 2 and abs(C.signed_pct(
                C.signed_ratio(min(vs), max(vs)))) > 10.0:
            return "size_volt_spread"
        if cell.get("mah") and s["size_mah"]:
            top = s["size_mah"][0][0]
            low = s["size_mah"][-1][0]
            if cell["mah"] >= top:
                return "size_leader"
            if cell["mah"] <= low:
                return "size_laggard"
            if top / max(low, 1) >= 2:
                return "size_chem_spread"
        return "size_named"
    if s["code"] and s["code"]["verdict"] == "differs":
        return "code_differs"
    if s["code"] and s["code"]["verdict"] == "rounded":
        return "code_rounded"
    if len(s["dropin"]) >= 2:
        return "crowded_shell"
    if s["dropin"] and s["v_class"] in ("calibration", "wrong"):
        return "fits_but_wrong"
    if s["dropin"]:
        return "one_swap"
    if len(s["siblings"]) >= 2:
        # Одна рамка на тридцать ступеней — это снова один абзац, повторённый
        # тридцать раз. Ступень различается ПОЛОЖЕНИЕМ и тем, следует ли
        # ёмкость за толщиной: у монет одной химии следует почти линейно, и
        # это проверяемое утверждение, а не оборот речи.
        hs = [C.shell(c)[2] for c in s["siblings"]]
        here = s["shell"][2]
        if here > max(hs):
            return "ladder_top"
        if here < min(hs):
            return "ladder_bottom"
        if s["scaling"] is not None:
            return "ladder_scaling"
        return "thickness_ladder"
    if s["dens_pct"] is not None and s["dens_pct"] >= 85:
        return "dense"
    if s["form"] == "box":
        return "prismatic"
    if not s["family"]:
        return "alone"
    return "plain"


HEADS = {
    "gone_mercury": "A mercury cell, and why nothing is a straight swap",
    "gone_siblings": "Unlisted, and the near misses are all the wrong depth",
    "gone_family_gone": "The whole shell left the catalog together",
    "gone_nothing": "Unlisted, and nothing in the catalog is this size",
    "gone_voltage_trap": "Unlisted, and what fits runs at the wrong volts",
    "gone_voltage_wrong": "Unlisted, and nothing that fits is the right class",
    "gone_taller_only": "Unlisted, and everything listed is deeper",
    "gone_dropin": "Unlisted, but something drops straight in",
    "gone_shorter_only": "Unlisted, and the listed cells are all thinner",
    "code_differs": "The code and the cell disagree",
    "code_rounded": "What the designation encodes, and what it rounds off",
    "crowded_shell": "Several cells share this shell",
    "fits_but_wrong": "It fits the compartment, not the circuit",
    "one_swap": "One straight swap, and what it changes",
    "size_volt_spread": "Same size, and not the same voltage",
    "size_leader": "The most capacity this size is made in",
    "size_laggard": "The least capacity this size is made in",
    "size_chem_spread": "One size, several chemistries, very different totals",
    "size_named": "What this size means and what else comes in it",
    "thickness_ladder": "One rung on a ladder of thicknesses",
    "ladder_top": "The deepest cell this diameter comes in",
    "ladder_bottom": "The thinnest rung of its diameter",
    "ladder_scaling": "Capacity tracks depth almost exactly here",
    "dense": "More energy per cubic centimeter than most",
    "prismatic": "A box, not a coin",
    "alone": "Nothing else in the data is this size",
    "plain": "What this cell is, and what it sits next to",
}


# --------------------------------------------------------- ведущие рамки
#
# Правило файла: ни одна фраза не должна годиться любому элементу. Если
# предложение можно поставить на любую страницу, не соврав, — оно не несёт
# факта. Исключений два, и оба служебные: границы применимости и метод.


def plural(n, one, many=None):
    """Согласование числа. «1 other current cells» — мелочь, которая читается
    как машина, а не как текст."""
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def span(lo, hi, one, many):
    """Диапазон печатается диапазоном ТОЛЬКО когда его концы разные.

    Сравниваются НАПЕЧАТАННЫЕ концы — те самые значения, что видит читатель:
    «at depths from 50.5 to 50.5 mm» стояло на восемнадцати страницах, и это
    не диапазон, а сбой шаблона. Форм две, потому что одна величина и две
    величины требуют РАЗНЫХ слов, а не одного шаблона с повтором.
    """
    lo, hi = str(lo), str(hi)
    return (one % lo) if lo == hi else (many % (lo, hi))


def span_selftest():
    """Известные ответы: вырожденный диапазон обязан терять слово «from»."""
    bad = []
    for args, want in (
            (("50.5", "50.5", "at %s mm", "from %s to %s mm"), "at 50.5 mm"),
            (("2", "3.2", "at %s mm", "from %s to %s mm"), "from 2 to 3.2 mm"),
            ((27, 27, "%s mm", "%s to %s mm"), "27 mm")):
        got = span(*args)
        if got != want:
            bad.append((args, want, got))
    return bad


def _name(cell):
    """Как называть элемент в тексте: код плюс самое ходовое чужое имя.
    Именно чужое имя вытиснено на корпусе и вбито в поиск."""
    alias = (cell.get("aliases") or [None])[0]
    return "%s (also %s)" % (cell["code"], alias) if alias else cell["code"]


def _fit_clause(fit):
    """То же, но БЕЗ собственного «but»: оборот встаёт в предложение, где
    союз уже есть. «A27 fits but sits lower but runs 700% off» стояло на
    живой странице."""
    # «Sits lower» рядом с процентом напряжения читается как НАПРЯЖЕНИЕ ниже,
    # а речь о глубине: «A27 sits lower at 12 V, +700%» — «ниже» и «выше» в
    # одной фразе о разных величинах. Посадка называется словом о стоянке.
    return {"drop-in": "drops straight in",
            "shorter": "goes in and stands shorter",
            "taller": "is too tall to close",
            "wider": "is too wide to enter",
            "narrower": "is too narrow to hold contact"}.get(fit, "fits")


def _fit_words(fit):
    return {"drop-in": "drops straight in",
            "shorter": "fits but sits lower",
            "taller": "is too tall to close",
            "wider": "is too wide to enter",
            "narrower": "is too narrow to hold contact"}.get(fit, "fits")


def _l_gone_mercury(cell, s):
    n = len([r for r in s["siblings"]]) or 0
    # «Больше нигде не делают» — утверждение о мире, а мы читаем каталог
    # ОДНОГО производителя. Правда, которую мы знаем: химия запрещена к
    # продаже населению в США и ЕС, и в этих данных ей нет равного.
    return ("This is a mercuric oxide cell, and mercury cells are banned "
            "from consumer sale in the United States and the European "
            "Union: the chemistry was outlawed, not merely retired. Nothing "
            "Energizer still lists holds %s the way it did, and the "
            "%s shell has %d neighbors of other depths but no equal."
            % (volts(cell), C.shell_label(s["shell"]), n))


def _l_gone_siblings(cell, s):
    sib = s["siblings"]
    lo, hi = C.shell(sib[0])[2], C.shell(sib[-1])[2]
    live = [c for c in sib if c.get("active")]
    # «Выжившие» были посчитаны по ВСЕМ соседям, включая снятые: страница
    # предлагала как уцелевший ртутный элемент, о котором сама же пишет, что
    # такие не делают нигде.
    if live:
        who = ("%s still in the catalog %s the diameter and %s on depth"
               % (plural(len(live), "cell"), verb(len(live), "share"),
                  verb(len(live), "miss")))
    else:
        who = ("what shares the diameter is out of production too, and all of "
               "it misses on depth")
    # Дизъюнкция — утверждение о МНОЖЕСТВЕ, и обе её стороны обязаны в этом
    # множестве быть. «Either rattles or refuses to let the cover close»
    # печаталось там, где все соседи ВЫШЕ и ни один не болтается: каждый
    # элемент подходил под одну из половин, а вместе они врали о наборе.
    here = s["shell"][2]
    short = [c for c in sib if C.fit_gap(here, C.shell(c)[2]) < 0]
    tall = [c for c in sib if C.fit_gap(here, C.shell(c)[2]) > 0]
    if short and tall:
        tail = ("%d of them stand off the contact and %d stop the cover "
                "closing" % (len(short), len(tall)))
    elif tall:
        tail = ("every one of them stops the cover closing, and none of them "
                "is loose")
    else:
        tail = ("every one of them stands off the contact, and none of them "
                "is too tall")
    return ("This catalog holds nothing at %s. %s: %d cells %s against this "
            "one's %s mm, so %s."
            % (C.shell_label(s["shell"]), who[0].upper() + who[1:], len(sib),
               span(mm(lo), mm(hi), "stand %s mm tall",
                    "run from %s to %s mm tall"),
               mm(here), tail))


def _l_gone_family_gone(cell, s):
    fam = s["family"]
    return ("This cell and its %d shell-mates went out of production together, "
            "which is why a compartment built for %s now has nothing to put in "
            "it: %s are the same size and none of them is made either."
            % (len(fam), C.shell_label(s["shell"]),
               listing([c["code"] for c in fam[:3]])))


def _l_gone_nothing(cell, s):
    return ("Energizer no longer lists a part under %s, and its catalog holds "
            "nothing else at %s. That "
            "is the honest answer: %s %s cell of this exact size is not "
            "something you can buy, and the closest options change either the "
            "depth or the voltage."
            % (_name(cell), C.shell_label(s["shell"]),
               article(chem(cell)), chem(cell)))


def _l_gone_voltage_trap(cell, s):
    b = s["best"]
    return ("Energizer no longer lists %s, and what fits the compartment does "
            "not match "
            "the circuit: %s %s but runs %s%% off, %s. In a meter or a camera "
            "calibrated for this cell, that shows up as a reading, not as a "
            "failure."
            % (_name(cell), b["cell"]["code"], _fit_clause(b["fit"]),
               pct_num(abs(b["volt"]["pct"])), v_meaning(b["volt"]["pct"])))


def _l_gone_voltage_wrong(cell, s):
    """Класс «wrong» — это НЕ сползшее показание.

    Прежде здесь стоял тот же текст, что и для класса «calibration», и на
    тринадцати страницах разница до 700% подавалась как «покажет не то».
    """
    b = s["best"]
    return ("Energizer no longer lists %s, and nothing listed that fits the "
            "compartment is the right voltage: %s %s, but it runs %s against "
            "this cell's %s — %s%% away, %s. A device built for this cell is "
            "not built for that one, and the compartment accepting it says "
            "nothing about the circuit surviving it."
            % (_name(cell), b["cell"]["code"], _fit_clause(b["fit"]),
               volts(b["cell"]), volts(cell),
               pct_num(abs(b["volt"]["pct"])),
               v_meaning(b["volt"]["pct"])))


def _l_gone_taller_only(cell, s):
    """Всё, что есть в каталоге этого диаметра, ГЛУБЖЕ.

    Зеркальная рамка к «all thinner»: прежде обе печатались одним текстом, и
    девять страниц советовали прокладку под элемент, который и так не даёт
    закрыть крышку.
    """
    b = s["reps"][0]
    return ("Energizer no longer lists %s, and everything listed at this "
            "diameter is deeper: %s stands %s mm where this one stands %s. "
            "It will go into the opening and it will not let the cover close, "
            "so there is nothing here to shim or pack out."
            % (_name(cell), b["cell"]["code"], mm(C.shell(b["cell"])[2]),
               mm(s["shell"][2])))


def _l_gone_dropin(cell, s):
    b = s["dropin"][0]
    others = len(s["dropin"]) - 1
    tail = (" %s fits the same slot." % plural(others, "other current cell")
            if others == 1 else
            (" %s fit the same slot." % plural(others, "other current cell")
             if others else ""))
    return ("%s has left the Energizer catalog, but the swap is easy: %s is the same %s "
            "and runs at %s against this cell's %s.%s"
            % (_name(cell), b["cell"]["code"], C.shell_label(s["shell"]),
               volts(b["cell"]), volts(cell), tail))


def _l_gone_shorter_only(cell, s):
    # Рамка выбирается ТОЛЬКО когда reps[0] действительно ниже: направление
    # проверяется по данным в _lead, а не подразумевается названием.
    b = s["reps"][0]
    # Две правки в одном предложении. «6.1 tall» — цифра без единицы:
    # величина, оторванная от своего существительного, это утверждение,
    # которого на странице нет. И вердикт посадки («fits») обязан выйти с
    # последствием по напряжению — правило сайта, а не украшение.
    return ("Energizer no longer lists %s, and every listed cell that fits is "
            "thinner: %s is %s mm tall where this one is %s, and runs %s "
            "against this cell's %s. It will enter the compartment and may "
            "not reach the contact without a spacer."
            % (_name(cell), b["cell"]["code"], mm(C.shell(b["cell"])[2]),
               mm(s["shell"][2]), volts(b["cell"]), volts(cell)))


def _l_code_differs(cell, s):
    k = s["code"]
    return ("The designation and the cell do not agree. %s encodes %s mm "
            "across and %s mm tall, while the published figures are %s and %s. "
            "The code is a name, not a measurement, and where the two part "
            "company the measurement wins."
            % (cell["code"], mm(k["d_code"]), mm(k["h_code"]),
               mm(k["d_real"]), mm(k["h_real"])))


def _l_code_rounded(cell, s):
    k = s["code"]
    return ("The number in the name is rounded. %s encodes a diameter of %s "
            "mm, but the cell measures %s mm: the standard writes whole "
            "millimeters and drops the remainder. The height, %s mm, is "
            "carried exactly."
            % (cell["code"], mm(k["d_code"]), mm(k["d_real"]),
               mm(k["h_real"])))


def _l_crowded_shell(cell, s):
    """Рамка называет СОСЕДЕЙ ПОИМЁННО и разницу с КАЖДЫМ.

    Первая версия называла их число и набор напряжений, а это у всех жильцов
    одной оболочки одно и то же: страницы LR44, SR44 и PR44 вышли почти
    дословно одинаковыми. Имя соседа и отклонение от ЭТОГО элемента — величины,
    которые у каждой страницы свои по построению.
    """
    drop = s["dropin"]
    bits = []
    for d in drop[:3]:
        v = d["volt"]
        if not v:
            bits.append(d["cell"]["code"])
        elif v["class"] == "same":
            bits.append("%s at the same volts" % d["cell"]["code"])
        else:
            bits.append("%s %s%% %s" % (d["cell"]["code"], abs(v["pct"]),
                                        "high" if v["pct"] > 0 else "low"))
    return ("%s drop into the same %s slot as this one: %s. The compartment "
            "takes all of them and the circuit does not, which is the whole "
            "difference between fitting and working."
            % (plural(len(drop), "current cell"), C.shell_label(s["shell"]),
               listing(bits)))


def _l_fits_but_wrong(cell, s):
    b = s["dropin"][0]
    # Процент печатается ЗНАКОВЫМ и одним владельцем: «runs 10.7% off» несло
    # направление словом «off», то есть не несло его вовсе, и мимо гейта
    # согласия с таблицей проезжало беззнаковым.
    return ("The only current cell of this size is the wrong voltage for it. "
            "%s matches %s exactly and runs %s against this cell's %s, which "
            "is %s. It goes in; whether it belongs there depends on what the "
            "device does with the difference."
            % (b["cell"]["code"], C.shell_label(s["shell"]),
               volt_pct(cell, b["cell"]), volts(cell),
               v_meaning(b["volt"]["pct"])))


def _l_one_swap(cell, s):
    b = s["dropin"][0]
    return ("One cell in the data is the same size and current: %s, %s against "
            "this one's %s, %s. Everything else at %s is either unlisted "
            "or a different depth."
            % (b["cell"]["code"], volts(b["cell"]), volts(cell),
               v_meaning(b["volt"]["pct"]), C.shell_label(s["shell"])))


def _l_thickness_ladder(cell, s):
    sib = s["siblings"]
    lo, hi = C.shell(sib[0])[2], C.shell(sib[-1])[2]
    nearest = min(sib, key=lambda c: abs(C.shell(c)[2] - s["shell"][2]))
    # Диапазон — через span(): концы, совпавшие по напечатанному, диапазоном
    # не печатаются. Здесь они пока не совпадали, но шаблон без защиты — это
    # «from 50.5 to 50.5 mm», ждущее своих данных.
    return ("This is one rung of a ladder: %s %s the %s mm diameter and "
            "%s only in depth, %s against this one's %s. "
            "The nearest rung, %s, is %s mm — the same hole, less inside it."
            % (plural(len(sib), "other cell"), verb(len(sib), "share"),
               verb(len(sib), "differ"), mm(s["shell"][1]),
               span(mm(lo), mm(hi), "standing at %s mm",
                    "running %s to %s mm"),
               mm(s["shell"][2]), nearest["code"],
               mm(C.shell(nearest)[2])))


def _l_dense(cell, s):
    return ("For its size this cell carries more than most: %d milliwatt-hours "
            "in %s cubic centimeters, which is %d mWh per cc and denser than "
            "%d%% of everything measured here. Chemistry, not size, is what "
            "buys that."
            % (round(s["energy"]), mm(cell.get("cc")), round(s["dens"]),
               s["dens_pct"]))


def _l_prismatic(cell, s):
    return ("This one is a box, not a coin: %s, so it has two cross-sections "
            "to match instead of one diameter. A cell that is right on width "
            "and wrong on length will not enter, and the terminals sit on top "
            "rather than on the faces."
            % C.shell_label(s["shell"]))


def _l_alone(cell, s):
    return ("Nothing else in the data is %s. This cell has the shell to "
            "itself, which means a device built around it has no second "
            "source: the search for a replacement starts by changing the "
            "compartment, not the cell."
            % C.shell_label(s["shell"]))


def _l_plain(cell, s):
    # Рамка выбирается ПОСЛЕ проверки «if not s['family']», то есть соседи по
    # габариту здесь есть всегда. Прежний текст утверждал обратное — и был
    # ложью по построению, на каждой странице, где печатался.
    return ("%s is %s %s cell at %s, measuring %s. It is current, %s of that "
            "exact size %s alongside it in the data, and the figures below "
            "are the manufacturer's own."
            % (_name(cell), article(chem(cell)), chem(cell), volts(cell),
               C.shell_label(s["shell"]),
               plural(len(s["family"]), "other designation"),
               verb(len(s["family"]), "stand")))


def _l_size_volt_spread(cell, s):
    """Одна оболочка, разные напряжения. Самый практически важный случай:
    аккумулятор 1,2 В входит туда же, куда щелочной 1,5 В."""
    others = sorted({c.get("volts") for c in s["size_kin"] if c.get("volts")}
                    - {cell.get("volts")})
    ex = min(s["size_kin"],
             key=lambda c: abs((c.get("volts") or 0) - (cell.get("volts") or 0))
             if c.get("volts") and c.get("volts") != cell.get("volts") else 99)
    # Величина и её направление СПРАШИВАЮТСЯ У ДАННЫХ одной функцией. Здесь
    # стояла своя арифметика по модулю, и она печатала «gap is 20%» там, где
    # шкала рядом рисовала совсем другую ось.
    g = C.voltage_gap(cell, ex)
    return ("The %s compartment takes cells of more than one voltage. This one "
            "is %s; %s in the same size runs %s, %s of this cell &mdash; %s. "
            "Nothing about the shape warns you, which is why the label "
            "matters more here than the size does."
            % (s["popular"], volts(cell), ex["code"], volts(ex),
               pct_signed(g["pct"]), v_meaning(g["pct"])))


def _l_size_leader(cell, s):
    """Наибольшая ёмкость типоразмера — и ЧТО это даёт против следующего.

    «Следующий вниз» брался первым из отсортированного списка, а первым там
    стоит сам этот элемент, когда ёмкости равны: выходило «на 625 мАч против
    625 мАч, примерно 1 times the running time». Ничья — это ничья, и
    называть её надо ничьёй.
    """
    mine = cell.get("mah") or 0
    lower = [x for x in s["size_mah"] if x[0] and x[0] < mine - 0.5]
    same = [x for x in s["size_mah"]
            if x[0] and abs(x[0] - mine) <= 0.5
            and x[1]["code"] != cell["code"]]
    if same:
        return ("%s in this size %s the same %s mAh, so the highest capacity "
                "the size is made in is shared rather than held. What "
                "separates them is chemistry and price, not running time."
                % (plural(len(same), "other designation"),
                   verb(len(same), "hold"), mm(mine)))
    if not lower:
        return ("At %s mAh this is the highest capacity published for the "
                "size, and the maker publishes no figure for the rest of it, "
                "so there is nothing here to compare it against."
                % mm(mine))
    second = lower[0]
    ratio = mine / second[0]
    return ("No %s holds more. At %s mAh this is the highest capacity the "
            "size is made in, against %s mAh for %s, the next one down. Same "
            "compartment, same voltage class, and %s the running time."
            % (s["popular"], mm(mine), mm(second[0]), second[1]["code"],
               ("%.1f times" % ratio) if ratio >= 1.05 else "barely more of"))


def _l_size_laggard(cell, s):
    top = s["size_mah"][0] if s["size_mah"] else None
    return ("This is the least %s %s is made to hold: %s mAh, where %s in the "
            "same shell carries %s. The size tells you what fits; it tells you "
            "nothing about how long it lasts."
            % (article(s["popular"]), s["popular"], mm(cell.get("mah")),
               top[1]["code"] if top else "the best of them",
               (mm(top[0]) + " mAh") if top else "several times more"))


def _l_size_chem_spread(cell, s):
    top, low = s["size_mah"][0], s["size_mah"][-1]
    chems = sorted({chem(c) for c in s["size_kin"]} | {chem(cell)})
    return ("%s %s is a shape, not a specification. The %s the data lists in "
            "this size run from %s mAh to %s mAh, a spread of %.1f times, and "
            "this one sits at %s mAh."
            % (article(s["popular"], cap=True), s["popular"],
               plural(len(chems), "chemistry", "chemistries"),
               mm(low[0]), mm(top[0]), top[0] / max(low[0], 1),
               mm(cell.get("mah"))))


def _l_size_named(cell, s):
    chems = sorted({chem(c) for c in s["size_kin"]} | {chem(cell)})
    return ("This is the %s %s: %s, %s, %s. The size is also made in %s, all "
            "of which enter the same compartment and none of which behave the "
            "same way as they empty."
            % (chem(cell), s["popular"], volts(cell),
               C.shell_label(s["shell"]) or "size not published",
               "in the catalog" if s["active"] else "no longer listed",
               listing([c for c in chems if c != chem(cell)][:3])))


def _l_ladder_top(cell, s):
    sib = s["siblings"]
    thin = min(sib, key=lambda c: C.shell(c)[2])
    return ("No coin cell at %s mm across is deeper than this. %s %s the "
            "diameter and every one of them is shorter, down to %s mm for %s, "
            "so a compartment built for this cell will take any of them and "
            "leave a gap."
            % (mm(s["shell"][1]), plural(len(sib), "other cell"),
               verb(len(sib), "share"),
               mm(C.shell(thin)[2]), thin["code"]))


def _l_ladder_bottom(cell, s):
    sib = s["siblings"]
    thick = max(sib, key=lambda c: C.shell(c)[2])
    return ("This is the thinnest coin cell made at %s mm across, %s mm "
            "deep. The %s at this diameter are all taller, up to %s mm, which "
            "means the "
            "swap runs one way only: they will not go where this one fits."
            % (mm(s["shell"][1]), mm(s["shell"][2]),
               plural(len(sib), "other cell"), mm(C.shell(thick)[2])))


def _l_ladder_scaling(cell, s):
    near, per = s["scaling"]
    return ("Depth buys capacity here at a steady rate. This cell holds %s mAh "
            "in %s mm and %s holds %s in %s mm, which is the same %s mAh per "
            "millimeter of depth: the chemistry fills the shell evenly and the "
            "only variable is how much shell there is."
            % (mm(cell.get("mah")), mm(s["shell"][2]), near["code"],
               mm(near.get("mah")), mm(C.shell(near)[2]), mm(per)))


LEAD_WRITERS = {
    "size_volt_spread": _l_size_volt_spread,
    "size_leader": _l_size_leader,
    "size_laggard": _l_size_laggard,
    "size_chem_spread": _l_size_chem_spread,
    "size_named": _l_size_named,
    "ladder_top": _l_ladder_top,
    "ladder_bottom": _l_ladder_bottom,
    "ladder_scaling": _l_ladder_scaling,
    "gone_mercury": _l_gone_mercury,
    "gone_siblings": _l_gone_siblings,
    "gone_family_gone": _l_gone_family_gone,
    "gone_nothing": _l_gone_nothing,
    "gone_voltage_trap": _l_gone_voltage_trap,
    "gone_voltage_wrong": _l_gone_voltage_wrong,
    "gone_taller_only": _l_gone_taller_only,
    "gone_dropin": _l_gone_dropin,
    "gone_shorter_only": _l_gone_shorter_only,
    "code_differs": _l_code_differs,
    "code_rounded": _l_code_rounded,
    "crowded_shell": _l_crowded_shell,
    "fits_but_wrong": _l_fits_but_wrong,
    "one_swap": _l_one_swap,
    "thickness_ladder": _l_thickness_ladder,
    "dense": _l_dense,
    "prismatic": _l_prismatic,
    "alone": _l_alone,
    "plain": _l_plain,
}


# ------------------------------------------------------------ добавки
#
# Ведущий сигнал уже потрачен на рамку. Остальные идут добавками в порядке
# силы, и каждая тоже ветвится: короткая добавка, повторяющаяся дословно на
# половине корпуса, вернула бы нас туда, откуда мы ушли.

def _s_aliases(cell, s):
    a = cell.get("aliases") or []
    if not a:
        return ""
    return ("The same cell is stamped %s depending on who made it."
            % listing(a[:4]))


def _s_energy(cell, s):
    if not s["energy"]:
        return ""
    return ("It holds about %d milliwatt-hours, %s mAh at %s."
            % (round(s["energy"]), mm(cell.get("mah")), volts(cell)))


def _s_rank(cell, s):
    r = s["rank"]
    if not r or r[1] < 2:
        return ""
    return ("Among the %d cells measured in this shell it ranks %d by stored "
            "energy." % (r[1], r[0]))


def _s_code(cell, s):
    k = s["code"]
    if not k or k["verdict"] == "differs":
        return ""
    return ("The designation itself encodes %s mm by %s mm, which is how the "
            "size can be checked without trusting anyone."
            % (mm(k["d_code"]), mm(k["h_code"])))


def _s_impedance(cell, s):
    if not cell.get("ohms_lo"):
        return ""
    return ("Internal impedance runs %s to %s ohms, which is what decides "
            "whether it can drive a pulse."
            % (mm(cell["ohms_lo"]), mm(cell["ohms_hi"])))


def _s_hours(cell, s):
    if not cell.get("hours") or not cell.get("load_ohms"):
        return ""
    return ("The manufacturer measures %s hours into %s ohms."
            % (mm(cell["hours"]), mm(cell["load_ohms"])))


def _s_family(cell, s):
    if not s["family"]:
        return ""
    return ("%s %s the shell: %s."
            % (plural(len(s["family"]), "other designation"),
               verb(len(s["family"]), "share"),
               listing([c["code"] for c in s["family"][:4]])))


def _s_regions(cell, s):
    r = cell.get("regions") or []
    if len(r) >= 4 or not r:
        return ""
    return "The maker lists it for %s only." % listing(r)


def _s_grams(cell, s):
    if not cell.get("grams"):
        return ""
    return "It weighs %s grams." % mm(cell["grams"])


SUPPORT_WRITERS = [
    ("aliases", _s_aliases), ("energy", _s_energy), ("family", _s_family),
    ("rank", _s_rank), ("code", _s_code), ("impedance", _s_impedance),
    ("hours", _s_hours), ("regions", _s_regions), ("grams", _s_grams),
]

# Какой сигнал уже израсходован рамкой — добавкой он идти не должен, иначе
# абзац дважды скажет одно и то же разными словами.
LEAD_USES = {
    "code_differs": ("code",), "code_rounded": ("code",),
    "dense": ("energy",), "crowded_shell": ("family",),
    "thickness_ladder": ("family",), "gone_family_gone": ("family",),
    "ladder_top": ("family",), "ladder_bottom": ("family",),
    "ladder_scaling": ("family", "energy"),
    "size_leader": ("energy",), "size_laggard": ("energy",),
    "size_chem_spread": ("energy",),
    "gone_siblings": ("family",), "alone": ("family",),
}


def difference_block(cell, s):
    """Блок ОТЛИЧИЯ: рамка по форме данных плюс добавки до нижней границы."""
    body = LEAD_WRITERS[s["lead"]](cell, s)
    used = set(LEAD_USES.get(s["lead"], ()))
    for key, writer in SUPPORT_WRITERS:
        if wc(body) >= ANSWER_MIN:
            break
        if key in used:
            continue
        piece = writer(cell, s)
        if not piece or wc(body + " " + piece) > ANSWER_MAX:
            continue
        body += " " + piece
        used.add(key)
    return "<h2>%s</h2><p>%s</p>" % (esc(HEADS[s["lead"]]), body)


# --------------------------------------------------------- остальные блоки

FIT_WORD = {
    "drop-in": "drop-in",
    "shorter": "sits lower",
    "taller": "too tall",
    "wider": "too wide",
    "narrower": "too narrow",
}

# Класс отклонения напряжения — короткой меткой. Слова разные по СМЫСЛУ:
# «same» и «wrong» отвечают на разные вопросы, а не на один с разной силой.
V_TAG = {
    "same": "same volts",
    "minor": "close enough",
    "calibration": "reads off",
    "wrong": "wrong class",
}


def _swap_clause(cell, r):
    """Одна замена — одной фразой, где ПОСАДКА и НАПРЯЖЕНИЕ стоят рядом и
    названы порознь.

    Собирается из тех же двух функций, что и метка в таблице, поэтому
    разойтись им негде. Ни одна ветка не возвращает слово о посадке без
    последствия: ради этого правила сайт и существует.
    """
    c, v = r["cell"], r["volt"]
    who = "<b>%s</b>" % esc(c["code"])
    if not v:
        body = ("%s %s, and the maker publishes no voltage for it"
                % (who, _fit_clause(r["fit"])))
    elif v["class"] == "same":
        body = "%s %s, and runs the same %s" % (who, _fit_clause(r["fit"]),
                                                volts(cell))
    else:
        body = ("%s %s, and runs %s &mdash; %s, %s"
                % (who, _fit_clause(r["fit"]), volts(c),
                   pct_signed(v["pct"]), v_short(v["pct"])))
    cav = caveat_short(C.chemistry_caveat(cell, c))
    return body + (", and it is %s" % cav if cav else "")


def _lead_admits(cell, r):
    """Пускать ли замену в абзац-ответ БЕЗ оговорки.

    Без оговорки — только то, что совпало по обеим осям: класс последствия
    «same» и никакой химии, чью цену процент не выражает. Всё остальное в
    абзац попадает ТОЛЬКО вместе со своим последствием.
    """
    v = r["volt"]
    return bool(v) and v["class"] == "same" \
        and C.chemistry_caveat(cell, r["cell"]) is None


def headline_block(cell, s):
    """Ответ выше сгиба. Что это и что с этим делать — в одном предложении.

    ПРАВИЛО ЭТОГО АБЗАЦА: слово о посадке не выходит отсюда без последствия по
    напряжению. Двадцать восемь страниц вели фразой «The closest listed cell,
    A27, fits but sits lower» при переходе 1,5 -> 12 В, а двумя абзацами ниже
    сами же писали «другой класс напряжения»; и пять страниц называли
    подходящим аккумулятор ровно там, где ниже написано, что аккумулятор не
    бывает прямой заменой. Кого сюда пускать, решают consequence_class и
    chemistry_caveat, и больше никто.
    """
    what = "%s, %s, %s" % (chem(cell), volts(cell),
                           C.shell_label(s["shell"]) or "size not published")
    # Причастие, а не глагол: страница снятого элемента не говорит о себе в
    # настоящем времени, и гейт это проверяет.
    if s["popular"]:
        what += ", known as %s %s cell" % (article(s["popular"]), s["popular"])
    if not s["active"] and s["reps"]:
        b = s["dropin"][0] if s["dropin"] else s["reps"][0]
        v = b["volt"]
        klass = v["class"] if v else None
        if klass == "wrong":
            # «Ближайшим» это не называется вовсе: слово обещает близость,
            # которой нет. Отдельная рамка — отдельные слова.
            tail = ("Not listed by Energizer, and nothing it still lists is "
                    "the right voltage class for this compartment: %s. Not a "
                    "substitute." % _swap_clause(cell, b))
        elif klass == "calibration":
            tail = ("Not listed by Energizer, and what still fits does not "
                    "match the circuit: %s." % _swap_clause(cell, b))
        else:
            tail = ("Not listed by Energizer. The closest it still lists: %s."
                    % _swap_clause(cell, b))
    elif not s["active"]:
        tail = ("Not listed by Energizer, and nothing in its catalog shares "
                "this size.")
    elif s["dropin"]:
        clean = [d for d in s["dropin"] if _lead_admits(cell, d)]
        flagged = [d for d in s["dropin"] if not _lead_admits(cell, d)]
        parts = []
        if clean:
            parts.append("<b>%s</b> %s the same slot at the same %s"
                         % (esc(listing([d["cell"]["code"]
                                         for d in clean[:3]])),
                            verb(len(clean[:3]), "take"), volts(cell)))
        for d in flagged[:2]:
            parts.append(_swap_clause(cell, d))
        tail = "Current. %s." % "; ".join(parts)
    elif s["family"]:
        # Ничего действующего того же габарита нет, но СНЯТЫЕ есть, и они
        # перечислены ниже на этой же странице.
        tail = ("Current, and the only other cells this size are ones "
                "Energizer no longer lists: %s."
                % esc(listing([c["code"] for c in s["family"][:3]])))
    else:
        tail = "Current, and nothing else in the data shares its size."
    return ('<p class="bx-lead"><b>%s</b> &mdash; %s. %s</p>'
            % (esc(cell["code"]), esc(what), tail))


def fit_block(cell, s):
    """Блок, ради которого сайт существует: что встанет и чем это обернётся.

    Посадка и электрика — ДВА РАЗНЫХ столбца, и они не сливаются в одну оценку
    ни при каких условиях. Слово «подходит» здесь не встречается в одиночку.

    Шесть рамок по составу списка: одна замена, несколько одной химии,
    несколько разных химий, только более низкие, ловушка по напряжению,
    ничего. Одна рамка давала 98% общих пятёрок слов.
    """
    reps = s["reps"]
    if not reps:
        return ""
    rows = ""
    for r in reps[:12]:
        c = r["cell"]
        v = r["volt"]
        vtag = V_TAG.get(v["class"], "unknown") if v else "unknown"
        vpct = pct_signed(v["pct"]) if v else "&mdash;"
        rows += ('<tr><th><a href="%s">%s</a></th>'
                 '<td class="bx-fit bx-fit-%s">%s</td>'
                 '<td class="bx-v bx-v-%s">%s %s<span class="bx-vtag">%s'
                 '</span></td><td>%s</td><td>%s</td></tr>'
                 % (C.link_to(c), esc(c["code"]), r["fit"],
                    FIT_WORD.get(r["fit"], r["fit"]),
                    (v["class"] if v else "unknown"), volts(c), vpct,
                    V_TAG.get(v["class"], "unknown") if v else "unknown",
                    esc(chem(c)),
                    (mm(c.get("mah")) + " mAh") if c.get("mah") else "&mdash;"))
    drop = s["dropin"]
    chems = sorted({chem(d["cell"]) for d in drop}) if drop else []
    # Самая далёкая замена берётся ЦЕЛИКОМ, а не одним модулем процента:
    # «spread by 20%» без знака и без имени спорило с осью, нарисованной над
    # ним, на четырнадцати страницах.
    far = max((d for d in drop if d["volt"]),
              key=lambda d: abs(d["volt"]["pct"]), default=None)
    if not drop:
        depths = sorted(C.shell(r["cell"])[2] for r in reps[:12])
        # Ветвление по ФОРМЕ данных: у одного варианта нет диапазона, и
        # «run 28.2 to 28.2 mm» — это не диапазон, а сбой шаблона.
        here = s["shell"][2]
        n = len(reps[:12])
        if depths[0] > here:
            tail = ("every one of them is deeper than this cell, so the "
                    "question is not the contact but the cover: a deeper cell "
                    "goes into the opening and stops the lid closing.")
        elif depths[-1] < here:
            tail = ("every one of them is shallower, so each stands off the "
                    "contact by the difference — a spring may take that up "
                    "and a flat tab will not.")
        else:
            tail = ("some are shallower and some deeper, so read the depth "
                    "column: short of this cell is a contact problem, past it "
                    "is a cover problem.")
        if n == 1:
            lead = ("Nothing Energizer still lists is the same depth. The "
                    "one option below "
                    "shares the diameter and stands %s mm against this cell's "
                    "%s, and %s"
                    % (mm(depths[0]), mm(here), tail))
        else:
            lead = ("Nothing Energizer still lists is the same depth. The %s "
                    "below share the "
                    "diameter and %s against this cell's %s, and "
                    "%s"
                    % (plural(n, "option"),
                       span(mm(depths[0]), mm(depths[-1]),
                            "stand at %s mm", "run %s to %s mm"),
                       mm(here), tail))
    elif len(drop) == 1 and drop[0]["volt"] \
            and drop[0]["volt"]["class"] == "same":
        # Величина ПЕЧАТАЕТСЯ, а не подразумевается словом «same»: фраза о
        # посадке обязана нести число напряжения, а не отсылку к нему.
        lead = ("One cell matches on both counts: %s is the same size and the "
                "same %s. The rest of the table trades depth for "
                "availability." % (drop[0]["cell"]["code"], volts(cell)))
    elif len(drop) == 1:
        lead = ("One cell is the same size, and it is not the same voltage: "
                "%s runs %s against this one, %s. Whether that matters is a "
                "question about the device, not about the cell."
                % (drop[0]["cell"]["code"],
                   pct_signed(drop[0]["volt"]["pct"]),
                   v_meaning(drop[0]["volt"]["pct"])))
    elif len(chems) == 1:
        lead = ("%s drop in, and all of them are %s: the choice among them is "
                "capacity and price, not chemistry."
                % (plural(len(drop), "cell"), chems[0]))
    elif far is not None and C.consequence_class(
            far["volt"]["ratio"]) not in ("same", "minor"):
        # Называется ОДНА величина с направлением и её последствие, а не
        # безымянный «разброс»: у 1,2 против 1,5 и 1,5 против 1,2 разные
        # последствия и один и тот же модуль.
        lead = ("%s drop in and they are not equivalent: of those, %s sits "
                "furthest at %s of this cell&rsquo;s %s, %s."
                % (plural(len(drop), "cell"), far["cell"]["code"],
                   pct_signed(far["volt"]["pct"]), volts(cell),
                   v_meaning(far["volt"]["pct"])))
    else:
        lead = ("%s drop in, spanning %s. They fit the same hole; what "
                "separates them is how they hold voltage as they empty."
                % (plural(len(drop), "cell"), listing(chems)))
    # Пояснение к столбцам — ПОДПИСЬ ТАБЛИЦЫ, а не ответ на запрос. Стоит вне
    # сравниваемого абзаца и потому не делает страницы близнецами; внутри
    # абзаца оно давало две трети общих пятёрок слов на сто двенадцати
    # страницах.
    # Заголовок обещает ровно то, что в таблице. Прежний — «What will
    # physically fit» — обещал только подходящее, а строки «too tall» и «3 V»
    # в ней есть и нужны: человеку важно знать, что похожее НЕ встанет.
    # ПОРЯДОК ВНУТРИ РАЗДЕЛА: заголовок, подпись к столбцам в две строки,
    # ТАБЛИЦА, и только потом разбор. Разбор — это второй ответ; первый уже
    # сказан фразой под заголовком страницы. Пока абзац разбора стоял над
    # таблицей, он один отодвигал её ещё на две сотни пикселей вниз, а
    # человек, пришедший с кодом, ищет глазами строку со своим кодом, а не
    # предложение о ней.
    return ('<h2>What fits the compartment, and what does not</h2>'
            '<p class="bx-legend">Fit answers whether it enters the '
            'compartment. Voltage answers whether the circuit will notice. '
            '%s</p>'
            '<div class="bx-tw" id="fits"><table class="bx-fits">'
            '<thead><tr>'
            '<th>Cell</th><th>Fit</th><th>Voltage</th><th>Chemistry</th>'
            '<th>Capacity</th></tr></thead><tbody>%s</tbody></table></div>'
            '<p>%s</p>'
            % (SUBSTITUTE_CAVEAT, rows,
               compose(lead, [], INTRO_MIN, INTRO_MAX)))

def replaces_block(cell, s, cs):
    """«Во что это можно поставить» — обратная сторона цепочки замен.

    Человек с кодом снятого элемента приходит на страницу снятого и получает
    ответ. Человек, держащий выпускаемый элемент, приходит на его страницу — и
    первая версия молчала о том, что этот элемент кого-то заменяет. Между тем
    именно это отвечает на вопрос «а подойдёт ли он в мой старый прибор».
    """
    reps = C.replaces(cell, cs)
    if not reps:
        return ""
    rows = ""
    # ПЕЧАТАЮТСЯ ВСЕ, и подводка ниже считает по тому же списку. Пока стояло
    # reps[:10], счёт, класс и разрыв в подводке брались по ПОЛНОМУ списку, а
    # таблица показывала часть: фраза «разрыв доходит до N%» могла назвать
    # строку, которой на странице нет. Сегодня максимум девять строк, то есть
    # обрезка не срабатывала ни разу, — тем дешевле её снять.
    for r in reps:
        c, v = r["cell"], r["volt"]
        rows += ('<tr><th><a href="%s">%s</a></th>'
                 '<td class="bx-fit bx-fit-%s">%s</td>'
                 '<td class="bx-v bx-v-%s">%s %s<span class="bx-vtag">%s'
                 '</span></td><td>%s</td></tr>'
                 % (C.link_to(c), esc(c["code"]), r["fit"],
                    FIT_WORD.get(r["fit"], r["fit"]),
                    (v["class"] if v else "unknown"), volts(c),
                    pct_signed(v["pct"]) if v else "&mdash;",
                    V_TAG.get(v["class"], "unknown") if v else "unknown",
                    esc(chem(c))))
    # «Gap» — слово симметричное, и число рядом с ним обязано быть таким же:
    # берётся мера ПАРЫ (gap_pct), а не процент стороны. Пока здесь стоял
    # модуль напечатанного процента, подводка меняла величину вместе с тем,
    # с какой страницы на пару смотрят, — при том что классы уже считались
    # по мере пары.
    worst = max((C.gap_pct(cell.get("volts"), r["cell"].get("volts")) or 0.0
                 for r in reps if r["volt"]), default=0)
    order = ("same", "minor", "calibration", "wrong")
    klass = max((r["volt"]["class"] for r in reps if r["volt"]),
                key=lambda k: order.index(k) if k in order else 0,
                default="same")
    n_wrong = sum(1 for r in reps
                  if r["volt"] and r["volt"]["class"] == "wrong")
    if klass in ("same", "minor"):
        lead = ("%s Energizer no longer lists %s at this cell as the "
                "closest thing it does list, and the voltage is the same. If a device was "
                "built for one of them, this is a straight substitution."
                % (plural(len(reps), "designation"), verb(len(reps), "point")))
    elif klass == "calibration":
        lead = ("%s Energizer no longer lists %s at this cell as the "
                "closest thing it does list, and the voltage is not the same: "
                "the gap reaches "
                "%s%%. The device will run, and an instrument calibrated for "
                "the old cell will read off."
                % (plural(len(reps), "designation"), verb(len(reps), "point"),
                   pct_num(worst)))
    else:
        # Класс «wrong» — не «прочтётся не так»: это другой класс напряжения,
        # и строка таблицы обязана сказать это словом, а не только цветом.
        lead = ("%s Energizer no longer lists %s at this cell as the "
                "closest thing it does list, and for %s of them it is a "
                "different voltage "
                "class: the gap reaches %s%%. For those it is not a "
                "substitution — read the voltage column before the fit "
                "column."
                % (plural(len(reps), "designation"), verb(len(reps), "point"),
                   n_wrong, pct_num(worst)))
    # ПОДПИСЬ ОПИСЫВАЕТ ТО, ЧТО ТАБЛИЦА ДЕЛАЕТ. Прежняя объявляла обратную
    # рамку — «как далеко ЭТОТ элемент от старого» — и была верна про число,
    # но число стояло в одной ячейке с напряжением СТАРОГО: «303 — 1.55 V —
    # -3.2%» читается как «303 ниже на 3,2%», хотя 303 выше. Рамка теперь
    # одна на весь сайт, и подпись говорит ровно её.
    return ('<h2>What this cell can stand in for</h2><p>%s</p>'
            '<p class="bx-legend">Every column of a row describes the '
            'discontinued cell it names. Fit reads that way too: it says '
            'whether that cell would enter this compartment, not whether '
            'this one enters its. Voltage is measured against this cell, the '
            'same way everywhere on the page: each row shows the '
            'discontinued cell&rsquo;s own voltage and how far that voltage '
            'sits from this one.</p>'
            '<div class="bx-tw"><table class="bx-fits"><thead><tr>'
            '<th>Discontinued cell</th><th>Fit</th><th>Voltage</th>'
            '<th>Chemistry</th></tr></thead><tbody>%s</tbody></table></div>'
            % (compose(lead, [], INTRO_MIN, INTRO_MAX), rows))


# Свойства химии, которых нет ни в одной таблице. Пишутся ОДИН раз на химию:
# они одинаковы для всех элементов своего рода, и выдумывать их на страницу
# нельзя. Порядок — по цене ошибки для человека.
# Ни одного напряжения, набранного руками: «1.35 V» для ртути спорило с
# собственными данными сайта на двенадцати страницах, где та же страница
# печатала 1,4 В в таблице. Где в заметке стоит %s, туда подставляется
# напряжение ЗАПИСИ того элемента, который эту химию на страницу и привёл.
CHEM_NOTE = {
    "zinc air": ("takes oxygen from the air through the holes in its face. "
                 "It starts discharging the moment the tab comes off and runs "
                 "down in weeks whether the device is used or not, and a "
                 "sealed compartment starves it"),
    "nickel-metal hydride": ("is rechargeable and sits at %s, below the "
                             "nominal of the primary cell whose slot it "
                             "takes. It is never a drop-in for a primary "
                             "cell no matter how well it fits, and a device "
                             "that cuts off early will read it as flat"),
    "silver oxide": ("holds its voltage almost flat until it is spent, which "
                     "is why watches and light meters were built around it"),
    "alkaline": ("drops in voltage steadily as it empties, so a device "
                 "calibrated for a flat discharge will drift as it goes"),
    # Число здесь — из записи ЭТОГО элемента, а не из шаблона: набранные
    # руками «1.35 V» спорили с собственными данными сайта на двенадцати
    # страницах, где та же страница печатала 1,4 В в таблице.
    "mercuric oxide": ("held a very flat %s, which is what old meters "
                       "were calibrated against. The chemistry is banned for "
                       "consumer sale in the United States and the European "
                       "Union, and this site reads one maker's catalog, so "
                       "what still reproduces that voltage is a question it "
                       "cannot answer"),
    # И отношение напряжений, и пересечение оболочек здесь СЧИТАЮТСЯ:
    # набранное «roughly double» печаталось на 33 страницах, из которых 17
    # несли 1,5 В — это не вдвое, это столько же, — а «shares almost none of
    # their holders» была дизъюнкцией над множеством, которое никто не мерил.
    "lithium": None,
    "carbon zinc": ("carries a fraction of the capacity of an alkaline cell "
                    "of the same size and leaks more readily when spent"),
}


LI_CLASSES = "the alkaline and silver classes"


def _lithium_note(c):
    """Заметка про литий: ОБА утверждения — отношение напряжений и общие
    оболочки — считаются по снимку, а не набираются."""
    v = c.get("volts") or CHEM_VOLTS.get("lithium")
    rel = ratio_phrase(v, [CHEM_VOLTS.get("alkaline"),
                           CHEM_VOLTS.get("silver oxide")], LI_CLASSES)
    if rel is None:
        # Отношение не назвалось одним словом по обоим основаниям — печатаем
        # сами числа: «примерно» без множителя утверждением не является.
        rel = ("a nominal %s and %s do not share"
               % (volts_num(CHEM_VOLTS.get("alkaline")),
                  volts_num(CHEM_VOLTS.get("silver oxide"))))
    share, total = CHEM_SHARE.get("lithium") or (0, 0)
    tail = ""
    if total:
        tail = (". Of the %d lithium cells here whose envelope the maker "
                "publishes, %d %s that envelope with an alkaline or silver "
                "cell" % (total, share, verb(share, "share")))
    return "runs at %s, %s%s" % (volts_num(v), rel, tail)


CHEM_NOTE_FN = {"lithium": _lithium_note}


def chem_note(kind, c):
    """Заметка о химии, с числом ИЗ ЗАПИСИ элемента, который её сюда привёл.

    Если у этого элемента напряжения нет, берётся характерное для химии,
    посчитанное по снимку. Руками не набирается ничего.
    """
    if kind in CHEM_NOTE_FN:
        return CHEM_NOTE_FN[kind](c)
    t = CHEM_NOTE.get(kind)
    if not t:
        return None
    if "%s" not in t:
        return t
    v = c.get("volts") or CHEM_VOLTS.get(kind)
    return t % volts_num(v)


def chemistry_block(cell, s):
    """Что меняет химия — для этого элемента и для всего, что в него встаёт.

    Числа отвечают, влезет ли и совпадёт ли напряжение. Здесь то, чего в
    числах нет: воздушно-цинковый задохнётся в закрытом отсеке, аккумулятор
    вообще не первичный элемент, серебряно-оксидный держит напряжение ровно.
    """
    seen, notes = [], []
    for c in [cell] + [r["cell"] for r in s["reps"][:8]]:
        k = chem(c)
        if k in seen or k not in CHEM_NOTE:
            continue
        seen.append(k)
        notes.append("<li><b>%s</b> %s.</li>" % (esc(k.capitalize()),
                                                 chem_note(k, c)))
    if len(notes) < 2:
        return ""
    others = [k for k in seen if k != chem(cell)]
    lead = ("Everything above answers size and voltage. What it cannot answer "
            "is chemistry, and %s in play here beside the %s this cell uses."
            % (plural(len(others), "other kind is", "other kinds are"),
               chem(cell)))
    return ('<h2>What the chemistry changes</h2><p>%s</p>'
            '<ul class="bx-nb" role="list">%s</ul>' % (compose(lead, [], INTRO_MIN,
                                                   INTRO_MAX),
                                           "".join(notes)))


SIZE_WORD = {"diameter": "a diameter of", "height": "a height of",
             "length": "a length of", "width": "a width of"}


def size_dispute_note(cell):
    """Записи, слитые в одно обозначение, публикуют РАЗНЫЕ размеры — и это
    печатается, а не разрешается молча большинством голосов.

    Таблица печатает одно значение (cells._pick), а строка «Also stamped»
    рядом называет все номера изделий группы: утверждение это про НАБОР, и
    /sr41/ печатала высоту 3.6 мм рядом с S312E, чья запись меряет 5.4 мм —
    шесть допусков той же страницы. Химия так обрабатывалась с самого
    начала, геометрия — нет.
    """
    parts = []
    for field in sorted(cell["size_spread"]):
        printed = cell.get(field)
        printed = None if printed is None else round(printed, 1)
        groups = cell["size_spread"][field]
        mine = {n for v, ns in groups if v == printed for n in ns}
        for v, ns in groups:
            if v == printed:
                continue
            # Номер, стоящий и при напечатанной величине, спорящим не
            # называется: одно имя может нести несколько записей.
            only = [n for n in ns if n not in mine]
            if only:
                parts.append("%s %s mm under %s"
                             % (SIZE_WORD[field], mm(v),
                                esc(listing(only[:3]))))
            else:
                # Спор БЕЗ различающего имени — всё равно спор, и молчать о
                # нём нельзя: у /sr60/ записи 1175SO публикуют и 2.1, и
                # 2.2 мм, а страница печатала 2.2 как решённое. Различающего
                # номера нет, поэтому называется сама величина.
                parts.append("%s %s mm under the same part numbers"
                             % (SIZE_WORD[field], mm(v)))
    if not parts:
        return ""
    return ('<p class="bx-legend">The maker&rsquo;s records filed under this '
            "designation do not all publish the same outside size. The table "
            "prints the figure most of them carry; the rest publish %s. "
            "Where the records part company the package in your hand "
            "decides, and this page cannot tell you which record it came "
            "from.</p>" % listing(parts))


def table_block(cell, s):
    """Полная таблица опубликованных величин, не урезанная.

    Рамка называет то, чего НЕТ, и это у каждого элемента своё: у одного не
    опубликована ёмкость, у другого объём, у третьего опубликовано всё.
    """
    rows = []
    missing = []

    def row(k, v):
        if v not in (None, "", "unknown"):
            rows.append("<tr><th>%s</th><td>%s</td></tr>" % (k, v))
        else:
            missing.append(k.lower())

    row("Designation", esc(cell["code"]))
    if cell.get("aliases"):
        rows.append("<tr><th>Also stamped</th><td>%s</td></tr>"
                    % esc(", ".join(cell["aliases"])))
    # Таблица обещает воспроизводить поля производителя без изменений. Там,
    # где буква обозначения спорит с полем, наш выбор нельзя выдавать за
    # поле: печатаются ОБА значения и говорится, откуда каждое.
    if cell.get("chemistry_conflict"):
        row("Chemistry", "%s, from the designation &mdash; the maker&rsquo;s "
                         "record says %s"
            % (esc(cell.get("chemistry") or ""),
               esc(cell["chemistry_conflict"]["record"])))
    else:
        row("Chemistry", esc(cell.get("chemistry") or ""))
    row("Nominal voltage", volts(cell))
    if s["shell"] and s["shell"][0] == "round":
        row("Diameter", mm(cell.get("diameter")) + " mm")
        row("Height", mm(cell.get("height")) + " mm")
    elif s["shell"]:
        row("Length", mm(cell.get("length")) + " mm")
        row("Width", mm(cell.get("width")) + " mm")
        row("Height", mm(cell.get("height")) + " mm")
    else:
        missing.append("dimensions")
    row("Weight", (mm(cell["grams"]) + " g") if cell.get("grams") else None)
    row("Volume", (cc_num(cell["cc"]) + " cc") if cell.get("cc") else None)
    row("Capacity", ("%s mAh to %s V" % (mm(cell["mah"]), mm(cell["cutoff"])))
        if cell.get("mah") and cell.get("cutoff") else
        ((mm(cell["mah"]) + " mAh") if cell.get("mah") else None))
    ours = len(rows)
    row("Stored energy", ("%d mWh" % round(s["energy"])) if s["energy"] else None)
    row("Energy density", ("%d mWh per cc" % round(s["dens"]))
        if s["dens"] else None)
    computed = len(rows) - ours
    if computed:
        rows[ours:] = [x.replace("<th>", '<th class="bx-ours">', 1)
                       for x in rows[ours:]]
    row("Impedance", ("%s to %s ohms" % (mm(cell["ohms_lo"]),
                                         mm(cell["ohms_hi"])))
        if cell.get("ohms_lo") else None)
    row("In the Energizer catalog",
        "Listed" if cell["active"] else "No longer listed")
    row("Listed for", esc(", ".join(cell.get("regions") or [])) or None)

    # Считаются только строки ИЗ ИСТОЧНИКА: наши две названы отдельно.
    known = len(rows) - computed
    if not missing:
        lead = ("Every field the maker fills is filled for this one: %s in "
                "all, from chemistry through to where it is sold."
                % plural(known, "figure"))
    elif len(missing) == 1:
        lead = ("%s are published, and one is not: %s. The row is absent "
                "rather than estimated."
                % (plural(known, "figure"), missing[0]))
    elif "capacity" in missing:
        lead = ("Capacity is missing here, and with it every figure derived "
                "from capacity: %s are published, %s are not."
                % (plural(known, "figure"), plural(len(missing), "field")))
    else:
        lead = ("%s are published and %s left blank, among them %s."
                % (plural(known, "figure"), plural(len(missing), "field"),
                   listing(missing[:3])))
    # Оговорка о НАШИХ строках стоит отдельной строкой под таблицей, а не в
    # подводке: окно абзаца ограничено словами, и добавленный первым пункт
    # съедал бюджет — из подводок пропала строка про то, под какими номерами
    # элемент лежит на полке.
    # Обозначения, которых в снимке нет, не печатаются под словами «Also
    # stamped»: эта строка утверждает, что имя ВЫТИСНЕНО на корпусе.
    # Каждое из них называется своими словами и остаётся находимым.
    named = ""
    if cell.get("iec_long"):
        named += ('<p class="bx-legend">The IEC standard writes this '
                  "designation in full as %s. That form comes from the "
                  "standard, not from a record of the maker&rsquo;s, which "
                  "is why it is not among the markings above.</p>"
                  % esc(cell["iec_long"]))
    if cell.get("px_forms"):
        named += ('<p class="bx-legend">Older equipment, manuals and repair '
                  "notes call it %s &mdash; the same designation without the "
                  "maker&rsquo;s letter in front.</p>"
                  % esc(listing(cell["px_forms"][:3])))
    if cell.get("aliases_other_chem"):
        by = {}
        for a, ch in cell["aliases_other_chem"]:
            by.setdefault(ch, []).append(a)
        for ch in sorted(by):
            named += ('<p class="bx-legend">Energizer files %s under this '
                      "designation as well, but its records give those %s %s "
                      "chemistry rather than %s. They are a different cell, "
                      "not another marking for this one.</p>"
                      % (esc(listing(by[ch][:4])), article(ch), esc(ch),
                         esc(chem(cell))))
    if cell.get("size_spread"):
        named += size_dispute_note(cell)
    if cell.get("chemistry_conflict"):
        cc = cell["chemistry_conflict"]
        named += ('<p class="bx-legend">The maker&rsquo;s record for %s '
                  "carries IEC %s with chemistry %s, and the letter %s in "
                  "that designation is %s by the standard. The two disagree. "
                  "This page follows the designation and prints both, because "
                  "picking one silently would hide a fault in the data.</p>"
                  % (esc(listing(cc["products"][:3]) or cell["code"]),
                     esc(cell["code"]), esc(C.chem_canon(cc["record"])),
                     esc(cell["code"][0]), esc(C.chem_canon(cc["code"]))))

    ours_note = ""
    if computed:
        ours_note = ('<p class="bx-legend">%s in the table %s not the '
                     "maker's but ours: %s. Everything else is reproduced "
                     "without change.</p>"
                     % (plural(computed, "row").capitalize(),
                        verb(computed, "are"),
                        listing(["stored energy",
                                 "energy per cubic centimeter"][:computed])))
    extras = []
    if s["code"]:
        extras.append("The designation encodes %s mm by %s mm, a second and "
                      "independent check on the size rows."
                      % (mm(s["code"]["d_code"]), mm(s["code"]["h_code"])))
    if cell.get("products"):
        # Настоящее время рядом с «No longer listed» — спор страницы с собой.
        extras.append(("It reaches shelves as %s." if cell["active"]
                       else "It reached shelves as %s.")
                      % listing(cell["products"][:4]))
    extras.append("A blank is not a zero.")
    return ('<h2>Every published figure</h2><p>%s</p>'
            '<div class="bx-tw"><table class="bx-spec">%s</table></div>%s'
            % (compose(lead, extras, INTRO_MIN, INTRO_MAX), "".join(rows),
               named + ours_note))

def rank_block(cell, s):
    """«А это много?». Одинокое число ничего не значит.

    Шесть рамок по ФОРМЕ ряда: вершина, дно, ничья, обрыв над головой, тесная
    середина и отсутствие ёмкости вовсе. Одна рамка на всех давала сто
    процентов общих пятёрок слов — то есть один абзац, повторённый сто сорок
    два раза.
    """
    r = s["rank"]
    if not s["energy"]:
        if not s["shell"]:
            return ""
        return ('<h2>Is that a lot of energy?</h2><p>%s</p>'
                % compose("Capacity is not published for this cell, so it is "
                          "absent from the energy ranking rather than placed "
                          "at the bottom of it. What can be compared is size: "
                          "%s, against a shell that holds %s."
                          % (C.shell_label(s["shell"]),
                             plural(len(s["family"]) + 1, "designation")),
                          ["Absent and zero are different answers, and the "
                           "table keeps them apart."]))
    e = round(s["energy"])
    if not r or r[1] < 2:
        return ('<h2>Is that a lot of energy?</h2><p>%s</p>'
                % compose("Nothing else measured shares this shell, so the "
                          "comparison has to go site-wide: %d milliwatt-hours "
                          "in %s cubic centimeters is %d mWh per cc, denser "
                          "than %d%% of every cell measured here."
                          % (e, mm(cell.get("cc")), round(s["dens"] or 0),
                             s["dens_pct"] or 0),
                          ["Density is ours: the maker publishes capacity and "
                           "volume and never divides one by the other."]))
    place, total, energy = r
    peers = [c for c in s["family"] if C.energy_mwh(c)]
    peers.sort(key=lambda c: -C.energy_mwh(c))
    tied = [c for c in peers if abs((C.energy_mwh(c) or 0) - energy) < 0.5]
    above = [c for c in peers if (C.energy_mwh(c) or 0) > energy + 0.5]
    below = [c for c in peers if (C.energy_mwh(c) or 0) < energy - 0.5]
    if tied:
        lead = ("It ties. %s in this shell stores the same %d "
                "milliwatt-hours, so they share place %d of %d instead of "
                "being put in an order the figures do not support."
                % (plural(len(tied), "other cell"), e, place, total))
    elif not above:
        gap = (energy / C.energy_mwh(below[0])) if below else None
        lead = ("Nothing else measured in this shell holds more. At %d "
                "milliwatt-hours it "
                "leads %s, and the next one down carries %s of what it does."
                % (e, plural(total - 1, "other cell"),
                   ("%d%%" % round(100 / gap)) if gap else "less"))
    elif not below:
        top = C.energy_mwh(above[-1])
        lead = ("It holds the least of the %d cells measured in this shell: "
                "%d milliwatt-hours against %d for the one directly above. "
                "Same compartment, different amount of chemistry inside it."
                % (total, e, round(top)))
    else:
        step = C.energy_mwh(above[-1]) / energy
        if step >= 1.5:
            lead = ("There is a cliff directly above it. This cell stores %d "
                    "milliwatt-hours and the next one up stores %d, a jump of "
                    "%d%% inside the same shell, which is chemistry rather "
                    "than volume."
                    % (e, round(C.energy_mwh(above[-1])),
                       round((step - 1) * 100)))
        else:
            lead = ("It sits in the middle of a close field: %d "
                    "milliwatt-hours, rank %d of %d, with the cells either "
                    "side within %d%% of it. In a shell this crowded the "
                    "energy figure is rarely what decides the choice."
                    % (e, place, total, round(abs(step - 1) * 100) or 1))
    # Оговорка о том, КАК считается ранг, верна для всех страниц сразу и
    # потому переехала в блок метода. Добавки здесь — только ВЕЛИЧИНЫ ЭТОГО
    # элемента: короткая ветка добирает до окна фактами, а не связками.
    extras = []
    if s["dens"] and s["dens_pct"] is not None:
        extras.append("Per unit of volume that is %d mWh per cubic "
                      "centimeter, denser than %d%% of everything measured "
                      "here." % (round(s["dens"]), s["dens_pct"]))
    if cell.get("cutoff"):
        extras.append("The capacity figure is measured down to %s V, below "
                      "which the maker stops counting." % mm(cell["cutoff"]))
    if cell.get("ohms_lo"):
        extras.append("Its internal impedance of %s to %s ohms is what "
                      "decides whether it can drive a pulse rather than a "
                      "trickle." % (mm(cell["ohms_lo"]), mm(cell["ohms_hi"])))
    if cell.get("grams"):
        extras.append("It weighs %s grams." % mm(cell["grams"]))
    return '<h2>Is that a lot of energy?</h2><p>%s</p>' % compose(lead, extras)

def neighbours_block(cell, s, cs):
    """Соседи ПО ДАННЫМ, а не по алфавиту. Пять рамок по составу окружения."""
    fam = s["family"]
    sib = s["siblings"]
    picks = fam[:4] + [c for c in sib if c not in fam][:4]
    if len(picks) < 2:
        return ""
    li = "".join('<li><a href="%s">%s</a> &mdash; %s, %s</li>'
                 % (C.link_to(c), esc(c["code"]), C.shell_label(C.shell(c)),
                    volts(c)) for c in picks[:8])
    fam_ch = sorted({chem(c) for c in fam})
    if fam and len(fam_ch) > 1:
        lead = ("The shell is shared across chemistries: %s %s at exactly "
                "this size in %s. Same hole, different insides, different "
                "discharge curve."
                % (plural(len(fam), "cell"), verb(len(fam), "sit"),
                   listing(fam_ch)))
    elif fam and sib:
        lead = ("%s %s at exactly this size, and %s %s the diameter at "
                "other depths. The first group is interchangeable by "
                "measurement; the second is not."
                % (plural(len(fam), "cell"), verb(len(fam), "sit"),
                   "%d more" % len(sib), verb(len(sib), "share")))
    elif fam:
        lead = ("%s sit at exactly this size and nothing else shares the "
                "diameter at another depth, so the shell is a single point "
                "rather than a ladder." % plural(len(fam), "cell"))
    elif len(sib) >= 4:
        depths = sorted(C.shell(c)[2] for c in sib)
        lead = ("Nothing in this data is this exact size, but the diameter "
                "is a well "
                "populated one: %s %s."
                % (plural(len(sib), "cell"),
                   span(mm(depths[0]), mm(depths[-1]),
                        "all measure %s mm deep, and this cell is not that "
                        "depth",
                        "run from %s to %s mm deep, and this cell is one "
                        "point on that scale")))
    else:
        depths = sorted(C.shell(c)[2] for c in sib) if sib else []
        # Голое «Nothing shares this exact size» говорило обо всём мире,
        # тогда как соседние формулировки того же факта были ограничены
        # данными. Область утверждения называется всегда.
        lead = ("Nothing in the Energizer data on this site shares this "
                "exact size. The %s below have the same "
                "diameter and a different depth — %s against this cell's %s — "
                "which is a near miss rather than an alternative."
                % (plural(len(sib), "cell"),
                   ("%s to %s mm" % (mm(depths[0]), mm(depths[-1])))
                   if len(depths) > 1 else ("%s mm" % mm(depths[0])
                                            if depths else "unpublished"),
                   mm(s["shell"][2])))
    return ('<h2>Cells measured next to this one</h2><p>%s</p>'
            '<ul class="bx-nb" role="list">%s</ul>'
            % (compose(lead, [], INTRO_MIN, INTRO_MAX), li))

# Ровно два блока одинаковы у всех страниц, и оба служебные: границы
# применимости и метод. Объявлены общими ЗДЕСЬ и по этому имени исключаются из
# сравнения на близнецов и из правила «ответ первым». Всё остальное обязано
# различаться.
CONSTANT_HEADS = ("Before you swap anything", "Where these numbers come from")

# Заголовки блоков, которые ВВОДЯТ стоящую ниже таблицу, а не отвечают на
# запрос. Список живёт РЯДОМ С БЛОКАМИ, которые его печатают: пока он был
# продублирован в render.py, одна правка заголовка развела копии, и шестьдесят
# страниц провалились по чужому окну абзаца при зелёных гейтах.
INTRO_HEADS = ("What fits the compartment, and what does not",
               "What the chemistry changes",
               "What this cell can stand in for",
               "Every published figure",
               "Cells measured next to this one")


# Чего сайт не видит. Список объявлен, чтобы его ДЛИНА печаталась, а не
# набиралась словом: дописанное четвёртое слепое пятно оставило бы «three».
CANNOT_SEE = (
    "Whether the contacts reach a shorter cell.",
    "Whether the device was calibrated for a chemistry that holds its "
    "voltage flat, which silver oxide does and alkaline does not.",
    "Whether the equipment tolerates the higher current a different "
    "chemistry can deliver.",
)


def applies_block():
    """Границы применимости. На этом сайте они не формальность: неверно
    названная замена портит прибор."""
    return (
        "<h2>Before you swap anything</h2>"
        "<p>Everything here is computed from published dimensions and nominal "
        "voltages. That answers whether a cell enters the compartment and "
        "whether the voltage matches on paper. It does not answer what your "
        "device does with the difference, and it cannot: a cell that fits can "
        "still be the wrong cell.</p>"
        "<p>One more limit, and it is the biggest. This site reads a single "
        "manufacturer&rsquo;s catalog. When a page says a designation is not "
        "listed, that means Energizer no longer offers a part under it "
        "&mdash; not that nobody makes the cell. Other makers may still sell "
        "it, and for common sizes they usually do.</p>"
        "<p>A voltage difference is one relation between two cells, and "
        "this page prints it from the cell it is about &mdash; in every "
        "table on the page, including the one listing cells no longer "
        "made. A figure always belongs to the cell whose voltage is printed "
        "beside it: a cell that runs lower than this one carries a minus "
        "here, one that runs higher carries a plus, and two cells at the "
        "same nominal voltage carry zero. Meet the same pair on the other "
        "cell&rsquo;s page and the sign is the other one, with the figure "
        "taken against that cell instead of this one; where the two run at "
        "the same voltage, both pages print zero. The class beside the "
        "figure is not "
        "read off that figure directly. It is decided on the gap itself, "
        "taken against the higher of the two nominal voltages, so one pair "
        "of cells gets one class whichever page you meet it on: counted from "
        "this side the boundary of the class that still runs falls at %s%% "
        "below and %s%% above, which is the same gap divided once by the "
        "larger nominal and once by the smaller. What genuinely differs "
        "between the two directions is the consequence, and the words carry "
        "it: a cell that runs low makes a calibrated instrument read below "
        "true, and a cell that runs high makes it read above.</p>"
        # Число слепых пятен СЧИТАЕТСЯ по самому списку: «three things»
        # стояло словом рядом с тремя предложениями, и любое четвёртое,
        # дописанное сюда, оставило бы слово прежним.
        "<p>%d things this site cannot see. %s Rechargeable cells are never "
        "a drop-in for primary cells regardless of size.</p>"
        % (pct_num(C.V_SERIOUS_PCT), pct_num(abs(C.class_edge(1)) * 100.0),
           len(CANNOT_SEE), " ".join(CANNOT_SEE)))


def method_block(vintage):
    """Сюда снесены ВСЕ методологические оговорки. Каждая верна для всех
    страниц сразу — значит, повторённая на каждой, она делает страницы
    близнецами и ни одной ничего не добавляет."""
    return (
        "<h2>Where these numbers come from</h2>"
        "<p>Dimensions, voltages, chemistries and capacities are published by "
        "the manufacturer and reproduced without change. Everything else on "
        "the page is ours, computed from those figures: whether one cell fits "
        "where another sat, how far apart their voltages are, stored energy "
        "and energy per cubic centimeter, the rank within a shell, and the "
        "check of the designation against the measured size.</p>"
        "<p>Fit is decided within " + mm(C.FIT_MM) + " mm on every axis, "
        "which is the order of a contact spring's travel. Voltage classes are "
        "decided by consequence, not by roundness, and they are decided on "
        "the gap between two nominal voltages taken against the higher of "
        "the two: %s%% or less of it is the same working voltage, %s%% "
        "starts to matter to a calibrated instrument, and past %s%% it is a "
        "different class altogether. Measuring the gap against the higher "
        "figure is what makes the verdict the same from either cell&rsquo;s "
        "page, while the printed percentage stays counted from the cell you "
        "are reading about. Cells with identical stored energy share a rank "
        "instead of being ordered arbitrarily.</p>"
        "<p>Ranking uses capacity times nominal voltage, because capacity "
        "alone is not comparable across chemistries: 150 mAh at 3 V is twice "
        "the energy of 150 mAh at 1.5 V. Neighbors are chosen by measurement "
        "and never alphabetically, because two cells filed next to each other "
        "by name usually have nothing in common. A blank in any table means "
        "the maker publishes no figure, which is not the same as zero.</p>"
        '<p class="bx-src">Source: %s.</p>'
        % (pct_num(C.V_SAME_PCT), pct_num(C.V_MINOR_PCT),
           pct_num(C.V_SERIOUS_PCT), esc(vintage)))
