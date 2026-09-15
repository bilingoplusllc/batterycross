# -*- coding: utf-8 -*-
"""BatteryCross — глубина страницы элемента: пять блоков сверх ответа.

ЗАЧЕМ. PLAYBOOK §1 требует 1500-4000 слов разбора на том же URL, и на этом
держится вся лестница дохода: сеть проверяет объём ПОСТРАНИЧНО по всему
инвентарю. Медиана страницы элемента была 994 слова, ни одна из 166 не
дотягивала.

ЧЕМ ЭТО НЕ ЯВЛЯЕТСЯ. Не добавлением слов. KeepsUntil набрал 593 страницы с
медианой сходства прозы 0,82, и Google их не взял. Правило D-013: проза
ветвится по ФОРМЕ данных, а не по значениям, и в абзаце стоят ИМЕНА соседей —
самое непохожее, что страница может сказать.

Форма, по которой ветвится каждый блок здесь:

  duty      что этим элементом ПИТАЮТ: класс прибора выводится из химии,
            формы, диаметра и напряжения. Внутри класса — вторая развилка по
            тому, что о ЭТОМ элементе опубликовано.
  figures   какие поля даташита у этого элемента ЕСТЬ: импеданс, отсечка,
            диапазон температур, саморазряд. Молчание источника — тоже форма.
  markings  какие ЧУЖИЕ имена ведут к этому элементу и ЧЬЯ это условность.
  mistaken  чем его путают: соседом по коду, соседом по диаметру, соседом по
            имени типоразмера.
  sources   сколько записей производителя за ним стоит и какие.

Каждый абзац несёт величину, ПОСЧИТАННУЮ для этой страницы. Абзац, годный
любой странице, факта не несёт.
"""
import re

import cells as C
import prose as P

esc, mm, listing, plural, wc = P.esc, P.mm, P.listing, P.plural, P.wc
volts_num, chem, pct_signed = P.volts_num, P.chem, P.pct_signed

# Область действия любого утверждения о полноте. ОДНА строка на весь сайт:
# «ничего такого не существует» и «в этом каталоге такого нет» — разные
# утверждения, и первое мы доказать не можем ни для одного поля.
SCOPE = "in the Energizer data this site reads"

# Границы «девятивольтового» по напряжению. ОДНО объявление на сайт и на
# гейт: правило, набранное в двух местах, однажды разойдётся, и разойдётся
# оно там, где речь о дымовом извещателе.
ALARM_VOLTS = (8.4, 9.6)

# Верхний край окна «почти тот же диаметр»: дальше это уже другой размер, а
# не то, что путают на столе. Нижний край — допуск посадки C.FIT_MM, и
# именно поэтому в этом окне НЕ БЫВАЕТ десятой доли миллиметра, которую
# шаблон печатал здесь на 175 строках.
NEAR_MM = 1.2

# Вердикт посадки ГЛАГОЛОМ. prose.FIT_WORD — это ярлык для ячейки таблицы
# («drop-in»), и подставленный в предложение он дал «it drop-in and runs 9 V».
FIT_VERB = {
    "drop-in": "drops straight in",
    "shorter": "enters and sits lower",
    "taller": "goes in and stands too tall",
    "wider": "will not enter, being too wide",
    "narrower": "rattles, being too narrow",
}

# Окно абзаца: как в prose, блоки делятся на ОТВЕЧАЮЩИЕ и ВВОДЯЩИЕ список
# ниже. Заголовки объявляются здесь же, рядом с текстом, который их печатает:
# список, продублированный в render.py, однажды уже развёл копии.
HEAD_KIND = {}


def _head(title, kind):
    HEAD_KIND[title] = kind
    return title


# ------------------------------------------------------------------ утилиты

def _num(x, digits=0):
    return ("%%.%df" % digits) % x


def _word(n, one, many=None):
    """Только СЛОВО в нужном числе, без самого числа. P.plural печатает
    «3 figures» целиком, и там, где число уже стоит в предложении, нужна
    именно форма слова, а не вторая копия величины."""
    return one if n == 1 else (many or one + "s")


def _name(c):
    return esc(c["code"])


def _names(cs, n=3):
    return listing([esc(c["code"]) for c in cs[:n]])


def _degrees(v):
    """Температура в градусах Цельсия и Фаренгейта: сайт американский, а
    источник печатает Цельсий. Обе величины — из ОДНОГО числа."""
    f = v * 9.0 / 5.0 + 32.0
    return "%s C (%s F)" % (_num(v), _num(f))


def _window(head):
    kind = HEAD_KIND.get(head, "answer")
    return ((P.INTRO_MIN, P.INTRO_MAX) if kind == "intro"
            else (P.ANSWER_MIN, P.ANSWER_MAX))


def _fill(head, lead, extras):
    """Рамка плюс ПОСЧИТАННЫЕ добавки, пока абзац не дорастёт до окна, и
    остаток — списком ниже.

    Это тот же приём, что в prose.compose, с одной разницей: здесь важно, ЧТО
    именно ушло в абзац. Добавка, поднятая в текст, не должна повториться
    строкой списка — повтор одной и той же фразы дважды на экране читается
    как сбой шаблона, потому что это он и есть.
    """
    lo, hi = _window(head)
    body, left = lead, []
    for piece in extras:
        if wc(body) >= lo or not piece or wc(body + " " + piece) > hi:
            left.append(piece)
            continue
        body += " " + piece
    return body, left


def _para(head, body):
    return "<h2>%s</h2><p>%s</p>" % (esc(head), body)


def _paras(head, lead, extras, tail=()):
    """Заголовок, первый абзац в окне и ВТОРОЙ абзац из того, что в первый не
    влезло.

    Второй абзац — не послабление окна, а ещё одно окно: правило «абзац в
    рамке и с числом» проверяет ПЕРВЫЙ абзац за заголовком, поэтому второй
    собирается по тем же правилам вручную и складывается только из
    ПОСЧИТАННЫХ добавок. Пусто — значит второго абзаца нет; выдумывать текст
    ради длины и есть та болезнь, от которой умер KeepsUntil.
    """
    lo, hi = _window(head)
    body, left = _fill(head, lead, list(extras))
    second, rest = "", []
    for piece in left + list(tail):
        if not piece:
            continue
        if second and wc(second + " " + piece) > hi:
            rest.append(piece)
            continue
        second = piece if not second else (second + " " + piece)
    if wc(second) < lo:
        # Слишком короткий второй абзац — это обрывок, а не мысль. Тогда его
        # содержимое уходит в список ниже, где короткая строка уместна.
        rest = ([second] if second else []) + rest
        second = ""
    html = _para(head, body)
    if second:
        html += "<p>%s</p>" % second
    return html, rest


def _ul(items):
    items = [i for i in items if i]
    if not items:
        return ""
    return ('<ul class="bx-nb" role="list">%s</ul>'
            % "".join("<li>%s</li>" % i for i in items))


def _dl(pairs):
    pairs = [(t, d) for t, d in pairs if t and d]
    if not pairs:
        return ""
    return ('<dl class="bx-gloss">%s</dl>'
            % "".join("<dt>%s</dt><dd>%s</dd>" % (esc(t), d)
                      for t, d in pairs))


def _same_shell(cell, cs):
    sh = C.shell(cell)
    if not sh:
        return []
    return sorted((c for c in cs
                   if c["code"] != cell["code"] and C.shell(c) == sh),
                  key=lambda c: c["code"])


def _kin_by_chem(cell, others, want):
    return [c for c in others if chem(c) == want]


# ------------------------------------------------- 1. ЧТО ЭТИМ ПИТАЮТ (duty)

def duty_kind(cell, s):
    """Класс прибора выводится из ФОРМЫ записи, а не назначается вручную.

    Ни одно из этих слов не взято из каталога: производитель не пишет, во что
    элемент ставят. Вывод делается по химии, форме корпуса, диаметру и
    напряжению — и потому он воспроизводим и проверяем гейтом.
    """
    ch = chem(cell)
    coin = C.is_coin(cell)
    d = cell.get("diameter") or 0.0
    v = cell.get("volts") or 0.0
    size = cell.get("size") or ""
    # ДЕВЯТИВОЛЬТОВЫЕ РЕШАЮТСЯ ПЕРВЫМИ и по напряжению, а не по форме: в
    # американском доме за этим напряжением чаще всего стоит дымовой
    # извещатель, и это перевешивает то, что внутри корпуса столбик кнопок,
    # цинк-воздух или уголь. Пока правило стояло после «Button Stack» и
    # химий, пять девятивольтовых страниц молчали об извещателе. Двенадцать
    # вольт сюда НЕ ВХОДЯТ: A23 и её родня живут в брелоках, а не в
    # извещателях, и одна рамка на два разных последствия у нас уже была.
    if ALARM_VOLTS[0] <= v <= ALARM_VOLTS[1]:
        return "alarm"
    if ch == "zinc air":
        return "hearing"
    if ch == "mercuric oxide":
        return "meter"
    if ch == "nickel-metal hydride":
        return "rechargeable"
    # ОПАСНОСТЬ ПРОГЛАТЫВАНИЯ ЗДЕСЬ БОЛЬШЕ НЕ РЕШАЕТСЯ. Она ортогональна
    # работе прибора и живёт в своей секции (`hazard_block`), с признаком по
    # геометрии нормы. Пока она стояла здесь, переключатель был однослотовым:
    # страница получала ЛИБО предупреждение, ЛИБО разбор того, ради чего на
    # неё пришли, — и 59 кнопочных элементов из 74 молчали об опасности,
    # потому что их химия уводила в другую ветку этого же `if`.
    if coin and ch == "lithium":
        return "coinlithium"
    if coin and ch in ("silver oxide", "alkaline"):
        return "watch"
    if size == "Button Stack":
        return "stack"
    if ch == "lithium":
        return "photo"
    if size in P.POPULAR_SIZES and coin is False:
        return "household"
    if s["form"] == "box":
        return "pack"
    return "other"


DUTY_HEAD = {
    "hearing": _head("A cell that starts working when the tab comes off",
                     "answer"),
    "meter": _head("The instruments this cell was calibrated into", "answer"),
    "rechargeable": _head("Why this one is not a substitute for anything",
                          "answer"),
    "coinlithium": _head("What a lithium coin is asked to hold", "answer"),
    "watch": _head("What a watch movement does with this cell", "answer"),
    "stack": _head("Several cells in one can, and what that costs", "answer"),
    "alarm": _head("What a smoke alarm needs from a cell this size", "answer"),
    "photo": _head("Built for a load that alkaline cannot hold", "answer"),
    "household": _head("The household slot this size sits in", "answer"),
    "pack": _head("A multi-cell battery, not a cell", "answer"),
    "other": _head("Where this compartment is unforgiving", "answer"),
}


def _hearing(cell, s, cs, kin):
    mah = cell.get("mah")
    lead = ("Zinc air takes its oxygen from the room. The sealed tab on the "
            "face is what keeps the cell asleep, and pulling it starts the "
            "clock whether the aid is switched on or not.")
    if mah:
        lead += (" Energizer publishes %s mAh for %s, and that figure assumes "
                 "air reaching the holes." % (mm(mah), _name(cell)))
    else:
        lead += (" No capacity figure is published for %s, so how long it "
                 "lasts after the tab comes off is not a number this catalog "
                 "gives." % _name(cell))
    same = _same_shell(cell, cs)
    others = [c for c in same if chem(c) != "zinc air"]
    facts = []
    if others:
        facts.append("A sealed compartment starves it. %s in this envelope "
                     "%s not need air, which is why %s is the wrong swap "
                     "into a watch case that closes on a gasket."
                     % (_names(others), P.verb(len(others[:3]), "do"),
                        _name(cell)))
    if cell.get("volts"):
        facts.append("Nominal %s, which is below every alkaline and silver "
                     "oxide cell of this envelope and is what the aid's "
                     "amplifier is tuned to." % volts_num(cell["volts"]))
    facts.append("Hearing aids are medical devices. Their manufacturers name "
                 "the cell on the case and in the manual, and that name wins "
                 "over any table, including this one.")
    return lead, facts


def _meter(cell, s, cs, kin):
    v = cell.get("volts")
    best = s.get("best")
    lead = ("Mercuric oxide was chosen for one property: it held its voltage "
            "almost flat until it died, so a light meter or an exposure "
            "circuit could be calibrated against it and stay calibrated.")
    if v:
        lead += (" %s is a %s cell, and the chemistry is banned for consumer "
                 "sale in the United States and the European Union."
                 % (_name(cell), volts_num(v)))
    facts = []
    if best and best.get("volt"):
        facts.append("The closest cell %s is %s at %s, which is %s away. On a "
                     "meter that is not a rounding error, it is the exposure."
                     % (SCOPE, _name(best["cell"]),
                        volts_num(best["cell"].get("volts")),
                        pct_signed(best["volt"]["pct"])))
    za = [c for c in cs if chem(c) == "zinc air"
          and c.get("volts") and abs(c["volts"] - (v or 0)) <= 0.06]
    if za:
        facts.append("Zinc air comes closest in voltage and is still made: "
                     "%s %s %s. It is a different envelope and a different "
                     "discharge life, and it is the direction the "
                     "photographic trade took."
                     % (_names(za), P.verb(len(za[:3]), "run"),
                        volts_num(za[0].get("volts"))))
    facts.append("A cell that reads off does not announce itself. The needle "
                 "moves, the numbers look plausible, and the exposure is "
                 "wrong by a fixed amount every time.")
    return lead, facts


def _rechargeable(cell, s, cs, kin):
    v = cell.get("volts")
    same = _same_shell(cell, cs)
    prim = [c for c in same if chem(c) not in ("nickel-metal hydride",)]
    # Слово о посадке НЕ ВЫХОДИТ без напряжения в том же предложении: гейт
    # прав, и правило это сайта, а не гейта.
    lead = ("%s is a rechargeable cell at %s, and no rechargeable cell is a "
            "drop-in for a primary one whatever the caliper says: the "
            "voltage is the objection, not the size."
            % (_name(cell), volts_num(cell.get("volts"))))
    if prim and prim[0].get("volts") and v:
        # РАМКА СТРАНИЦЫ: величина называется так же, как в таблице выше —
        # чужой элемент против этого. Здесь стояла своя арифметика от ЧУЖОГО
        # напряжения, и абзац печатал -20,0% там, где таблица той же страницы
        # печатала для того же элемента +25,0%.
        lead += (" It measures the same as %s, which runs %s against this "
                 "cell's %s, %s."
                 % (_name(prim[0]), volts_num(prim[0]["volts"]),
                    volts_num(v), P.volt_pct(cell, prim[0])))
    elif v:
        lead += (" Nominal %s, against the %s a primary cell of this shape "
                 "delivers." % (volts_num(v),
                                volts_num(P.CHEM_VOLTS.get("alkaline"))))
    facts = []
    facts.append("The gap is not the whole story. A nickel-metal hydride cell "
                 "holds its voltage flat and then falls off a cliff, so a "
                 "device that warns you before it dies will not warn you.")
    if cell.get("mah"):
        facts.append("Published capacity %s mAh, and it is measured on a "
                     "charge-discharge cycle, not on the shelf: this cell "
                     "loses charge sitting in a drawer." % mm(cell["mah"]))
    if prim:
        # Подлежащих в _names до трёх, а глагол и «the cell» были набраны в
        # единственном: «FR03, LR03 and R03 occupies ... and is the cell».
        # Заодно уходит утверждение единственности, сказанное о списке.
        n_prim = len(prim[:3])
        facts.append("%s %s the same envelope, %s, and %s the %s the "
                     "compartment was drawn for."
                     % (_names(prim), P.verb(n_prim, "occupy"),
                        esc(C.shell_label(C.shell(cell))),
                        P.verb(n_prim, "are"), _word(n_prim, "cell")))
    return lead, facts


def _coinlithium(cell, s, cs, kin):
    """Литиевая монета — ЧТО ОНА ДЕРЖИТ. Опасность проглатывания отсюда
    убрана: она стоит выше, своей секцией, на всех кнопочных элементах, а не
    только на литиевых. Здесь осталось то, ради чего на страницу приходят и
    чего нет больше нигде: соседи по диаметру, их напряжения и ёмкость.
    """
    d = cell.get("diameter")
    v = cell.get("volts")
    lead = ("A lithium coin %s mm across holds %s with almost no self-discharge, "
            "which is why sockets that must remember something for years are "
            "cut for this shape." % (mm(d), volts_num(v)))
    facts = []
    if cell.get("mah"):
        facts.append("Published capacity %s mAh. In a memory-backup socket "
                     "that is measured in years rather than hours; under a "
                     "camera or a transmitter load it is measured in shots."
                     % mm(cell["mah"]))
    same = _same_shell(cell, cs)
    sib = s.get("siblings") or []
    if sib:
        # «Те же 3 В» было НАБРАНО РУКАМИ и сказано о наборе «тот же диаметр,
        # другая глубина», который про напряжение не говорит ничего: на
        # /cr1616/ в этот же список попадали LR52 (1,5 В) и MR52 (1,4 В), и
        # страница печатала ровно наоборот тому, ради чего сайт заведён.
        # Свойство набора СЧИТАЕТСЯ ПО НАБОРУ — и по тому, который НАЗВАН.
        named = sib[:4]
        vs = sorted({c["volts"] for c in named + [cell] if c.get("volts")})
        say = "Same diameter, other depths: %s. " % _names(named, 4)
        if len(vs) == 1:
            say += ("They are one voltage, %s; depth is the only thing that "
                    "changes." % volts_num(vs[0]))
        elif vs:
            say += ("They are not one voltage: this diameter carries %s. "
                    "Depth is not the only thing that changes here."
                    % listing([volts_num(x) for x in vs]))
        else:
            say += "No nominal voltage is published for any of them."
        facts.append(say)
    elif same:
        facts.append("%s shares this exact envelope %s. Nothing about the "
                     "outside tells the two apart on a table."
                     % (_names(same), esc(C.shell_label(C.shell(cell)))))
    return lead, facts


def _watch(cell, s, cs, kin):
    ch = chem(cell)
    same = _same_shell(cell, cs)
    twin = [c for c in same if chem(c) != ch]
    lead = ("A quartz movement pulls a short pulse through the cell every "
            "second and reads the voltage between pulses. That is why the "
            "chemistry in this envelope matters more than the size does.")
    if ch == "silver oxide":
        lead += (" Silver oxide holds %s nearly flat until it is spent."
                 % volts_num(cell.get("volts")))
    else:
        lead += (" Alkaline at %s sags as it discharges, and the movement "
                 "reads that sag as a dying cell."
                 % volts_num(cell.get("volts")))
    facts = []
    if twin and twin[0].get("volts") and cell.get("volts"):
        o = twin[0]
        # «%s against this cell's %s» называет ЧУЖОЕ напряжение против
        # своего — значит и процент считается в ту же сторону. Своя
        # арифметика здесь делила на чужое напряжение и меняла знак: на
        # четырнадцати страницах стояло «1.55 V against this cell's 1.5 V,
        # -3.2%» при +3.3% в таблице той же страницы.
        facts.append("%s is the same %s in %s: %s against this cell's %s, "
                     "%s. The case cannot tell them apart; the movement can."
                     % (_name(o), esc(C.shell_label(C.shell(cell))),
                        esc(chem(o)), volts_num(o.get("volts")),
                        volts_num(cell["volts"]), P.volt_pct(cell, o)))
    if cell.get("ohms_lo") and cell.get("ohms_hi"):
        facts.append("Internal impedance %s to %s ohms, published by the "
                     "maker. That is the figure the stepper motor pulse sees, "
                     "and it rises as the cell ages."
                     % (mm(cell["ohms_lo"]), mm(cell["ohms_hi"])))
    elif cell.get("mah"):
        facts.append("Published capacity %s mAh. A movement drawing a few "
                     "microamps between pulses turns that into years, which "
                     "is why a watch cell is judged on shelf life."
                     % mm(cell["mah"]))
    if not cell["active"]:
        facts.append("Energizer no longer lists %s, so the cell in the case "
                     "of an older watch may have no current part under this "
                     "designation at all." % _name(cell))
    return lead, facts


def _stack(cell, s, cs, kin):
    v = cell.get("volts") or 0.0
    unit = None
    n = 0
    for base in (1.5, 1.55, 3.0):
        k = v / base
        if abs(k - round(k)) < 0.02 and round(k) >= 2:
            n, unit = int(round(k)), base
            break
    lead = ("This is not one cell. It is a stack sealed in one can, which is "
            "why the voltage is a multiple and the diameter is not.")
    if n:
        lead += (" %s at %s is %d cells of %s in series."
                 % (_name(cell), volts_num(v), n, volts_num(unit)))
    else:
        lead += (" %s delivers %s from a column of cells the maker does not "
                 "count for you." % (_name(cell), volts_num(v)))
    facts = []
    facts.append("A series stack is only as good as its worst cell. One weak "
                 "element takes the whole can down, and nothing on the "
                 "outside shows which one it was.")
    if n and unit:
        singles = [c for c in cs if c.get("volts")
                   and abs(c["volts"] - unit) < 0.01 and C.is_coin(c)
                   and c.get("diameter")
                   and abs(c["diameter"] - (cell.get("diameter") or 0)) <= 1.0]
        if singles:
            facts.append("The unit inside is the same width as %s, a single "
                         "%s cell of this diameter."
                         % (_names(singles, 2), volts_num(unit)))
    if cell.get("mah"):
        facts.append("Published capacity %s mAh for the whole stack, not per "
                     "cell: capacity does not add in series, voltage does."
                     % mm(cell["mah"]))
    return lead, facts


def _alarm(cell, s, cs, kin):
    v = cell.get("volts")
    kin_all = s.get("size_kin") or []
    # Артикль по ЗВУКУ: «a 8.4 V cell» стояло на живой странице.
    lead = ("In a United States home the commonest thing behind %s %s cell is "
            "a smoke alarm, and an alarm is the one device that has to warn "
            "you before it stops."
            % (P.article(volts_num(v)), volts_num(v)))
    if cell.get("mah"):
        lead += (" Energizer publishes %s mAh for %s." % (mm(cell["mah"]),
                                                          _name(cell)))
    facts = []
    # Сравнение «то же напряжение, та же форма» делается ТОЛЬКО с теми, у кого
    # напряжение и правда то же: на странице 9 В стояло «7.2H5 carries the
    # same 7.2 V», и «то же» относилось к чужой величине.
    same_v = [c for c in kin_all if c.get("mah") and c.get("volts") == v]
    withmah = sorted(((c["mah"], c) for c in same_v), key=lambda x: -x[0])
    if withmah and cell.get("mah"):
        lo = withmah[-1]
        if lo[0] < cell["mah"]:
            facts.append("%s carries the same %s in the same shape and is "
                         "published at %s mAh, %s of this cell. Same "
                         "compartment, a fraction of the run."
                         % (_name(lo[1]), volts_num(v), mm(lo[0]),
                            _num(100.0 * lo[0] / cell["mah"]) + "%"))
    nimh = [c for c in kin_all if chem(c) == "nickel-metal hydride"]
    if nimh:
        facts.append("%s fits the same clip and is rechargeable at %s. Its "
                     "voltage falls off a cliff instead of drifting down, so "
                     "the low-battery chirp an alarm is tuned to may never "
                     "arrive." % (_names(nimh), volts_num(nimh[0].get("volts"))))
    facts.append("Alarm manufacturers name an acceptable cell on the unit and "
                 "in the manual. Where a device is a safety device, that name "
                 "settles it and this table does not.")
    return lead, facts


def _photo(cell, s, cs, kin):
    v = cell.get("volts")
    lead = ("Lithium is here for current, not for size. %s delivers %s and "
            "holds it under a load that would drag an alkaline cell of the "
            "same envelope down within seconds." % (_name(cell), volts_num(v)))
    facts = []
    if cell.get("op_lo") is not None:
        facts.append("Energizer publishes an operating range down to %s for "
                     "this cell, which is the reason it turns up in outdoor "
                     "and automotive equipment." % _degrees(cell["op_lo"]))
    if cell.get("mah") and cell.get("cc"):
        facts.append("%s mAh in %s cubic centimeters. Density is the whole "
                     "argument for the chemistry, and it is why the "
                     "compartment is small."
                     % (mm(cell["mah"]), P.cc_num(cell["cc"])))
    same = _same_shell(cell, cs)
    if same:
        facts.append("%s shares this envelope %s at a different voltage, so "
                     "the compartment alone will not tell you which one the "
                     "equipment expects." % (_names(same), SCOPE))
    else:
        facts.append("Nothing else %s shares this envelope, so a cell that "
                     "fits the holder is almost certainly this one." % SCOPE)
    return lead, facts


def _household(cell, s, cs, kin):
    size = cell.get("size")
    kin_all = s.get("size_kin") or []
    chems = sorted({chem(c) for c in kin_all} - {chem(cell)})
    # Подставлялся ОДИН артикль и ни разу само имя: все 22 страницы с этим
    # предложением читались «3-315 is an, which is a shape» — и печатали
    # размер верно двумя предложениями ниже.
    lead = ("%s is %s %s, which is a shape rather than a specification: %s "
            "%s the same slot %s under different chemistries."
            % (_name(cell), P.article(esc(size)), esc(size),
               plural(len(kin_all) + 1, "designation"),
               P.verb(len(kin_all) + 1, "share"), SCOPE))
    if cell.get("mah"):
        lead += (" This one is %s at %s mAh." % (esc(chem(cell)),
                                                 mm(cell["mah"])))
    facts = []
    withmah = sorted(((c.get("mah"), c) for c in kin_all if c.get("mah")),
                     key=lambda x: -x[0])
    if withmah and cell.get("mah"):
        top, low = withmah[0], withmah[-1]
        if top[1]["code"] != cell["code"] or low[1]["code"] != cell["code"]:
            facts.append("Across the %s the published capacity runs from %s "
                         "mAh (%s) to %s mAh (%s). The compartment does not "
                         "change; the run time changes by %sx."
                         % (esc(size), mm(top[0]), _name(top[1]),
                            mm(low[0]), _name(low[1]),
                            _num(top[0] / low[0], 1) if low[0] else "?"))
    if chems:
        facts.append("The other chemistries in this slot are %s, and only the "
                     "label says which one is in your hand."
                     % listing([esc(x) for x in chems]))
    if chem(cell) == "alkaline":
        facts.append("An alkaline cell left in a device it is not powering is "
                     "the commonest way this size ruins equipment: the leak "
                     "happens on the shelf, not under load.")
    return lead, facts


def _pack(cell, s, cs, kin):
    sh = C.shell(cell)
    v = cell.get("volts")
    lead = ("A box %s is a battery in the older sense: several cells wired "
            "inside one case, with terminals on the outside and no way to "
            "look in." % esc(C.shell_label(sh)))
    if v:
        lead += (" %s delivers %s, and the case is the only part a "
                 "compartment measures." % (_name(cell), volts_num(v)))
    facts = []
    same = _same_shell(cell, cs)
    if same:
        facts.append("%s %s the same case %s. Identical outside, and the "
                     "voltage column is where they part."
                     % (_names(same), P.verb(len(same[:3]), "share"), SCOPE))
    if cell.get("mah"):
        facts.append("Published capacity %s mAh for the assembled battery. "
                     "The figure belongs to the pack, not to any cell in it."
                     % mm(cell["mah"]))
    facts.append("A pack that fits the clip can still be the wrong pack: "
                 "terminal spacing and polarity are set by the case, and this "
                 "site measures the case.")
    return lead, facts


def _other(cell, s, cs, kin):
    reps = s.get("reps") or []
    dropin = s.get("dropin") or []
    sh = C.shell(cell)
    lead = ("%s measures %s, and what that compartment forgives is the "
            "question this page exists for."
            % (_name(cell), esc(C.shell_label(sh)) if sh else "no published size"))
    if dropin:
        lead += (" %s %s it exactly, which settles the size and settles "
                 "nothing else." % (_names(dropin),
                                    P.verb(len(dropin[:3]), "match")))
    elif reps:
        lead += (" Nothing %s matches it exactly; the nearest is %s."
                 % (SCOPE, _name(reps[0]["cell"])))
    else:
        lead += (" Nothing %s measures close enough to compare against it at "
                 "all." % SCOPE)
    facts = []
    if cell.get("volts"):
        # Предмет НАЗВАН. Предыдущее предложение называет ближайший
        # чужой элемент, и «Nominal 4.5 V» читалось про него: на /3lr50/
        # это было сказано о CR17345, который работает на 3 В.
        facts.append("%s is nominal %s. A compartment holds a size; a "
                     "circuit expects a voltage; nothing on the outside of "
                     "the cell reports the second one."
                     % (_name(cell), volts_num(cell["volts"])))
    if cell.get("mah"):
        facts.append("Published capacity %s mAh, which is what a swap costs "
                     "or gains in run time before anything else is "
                     "considered." % mm(cell["mah"]))
    facts.append("Where the equipment matters, the maker of the equipment "
                 "names the cell. That name outranks any cross-reference, "
                 "this one included.")
    return lead, facts


DUTY_WRITERS = {
    "hearing": _hearing, "meter": _meter, "rechargeable": _rechargeable,
    "coinlithium": _coinlithium, "watch": _watch,
    "stack": _stack, "alarm": _alarm, "photo": _photo,
    "household": _household, "pack": _pack, "other": _other,
}


def duty_block(cell, s, cs):
    kind = duty_kind(cell, s)
    head = DUTY_HEAD[kind]
    lead, facts = DUTY_WRITERS[kind](cell, s, cs, s.get("size_kin") or [])
    html, left = _paras(head, lead, facts, _duty_extras(cell, s, cs))
    return html + _ul(left[:4])


# ------------------------------------------- 1a. ОПАСНОСТЬ ПРОГЛАТЫВАНИЯ

# Порог тяжести. НЕ признак попадания под правило: под него попадает вся
# геометрия. 16 мм — диаметр, с которого элемент перестаёт проходить детским
# пищеводом и застревает; ниже него тот же ток течёт, просто реже застревает.
INGEST_MM = 16.0

# Определение КНОПОЧНОГО ЭЛЕМЕНТА взято из нормы дословно и переведено в
# признак записи: 16 CFR 1263.2 — «a single cell battery with a diameter
# greater than the height of the battery». Ни слова про химию. Пока признак
# был химическим («литий»), предупреждение стояло на 15 страницах из 74, и
# самый ходовой бытовой кнопочный элемент LR44 не произносил ни «swallow»,
# ни «poison» ни разу на 2 934 словах.
#   `C.is_coin` — это ровно «высота меньше диаметра», уже посчитанное.
#   «Single cell» — это НЕ сборка: 2MR9 (16,89 x 15,4 мм) стоит из столбика
# кнопок, и норма на неё не распространяется. Ветка названа, а не молчит.
ASSEMBLY_SIZE = "Button Stack"

# Цинк-воздух — единственное исключение, и оно ЗАПИСАНО В САМОЙ НОРМЕ:
# 16 CFR 1263.1(d), «Batteries that do not present an ingestion hazard …
# These are: zinc-air button cell or coin batteries». Печатать на пяти
# слуховых страницах то же, что на литиевых, значит соврать о норме; молчать
# на них — значит соврать о предмете. Поэтому ветка своя.
HAZARD_EXEMPT_CHEM = "zinc air"

def hazard_kind(cell):
    """Попадает ли запись под 16 CFR часть 1263 — ПО ГЕОМЕТРИИ.

    Возвращает `None` (не кнопочный элемент), `"covered"` (норма действует)
    или `"exempt"` (цинк-воздух, выведен решением Комиссии). Функция не
    спрашивает ничего у рендера и ничего у `duty_kind`: гейт, который брал
    выборку у того же кода, что её и решал, у нас уже был зелёным над дырой
    в 59 страниц.
    """
    if C.is_coin(cell) is not True:
        return None
    if (cell.get("size") or "") == ASSEMBLY_SIZE:
        return None
    if chem(cell) == HAZARD_EXEMPT_CHEM:
        return "exempt"
    return "covered"


def hazard_block(cell, s, cs):
    """Единственная на сайте плашка об угрозе жизни. Своя вёрстка, свой
    сигнальный вес и место ВЫШЕ таблицы замен: страница, которая уверенно
    пишет «SR44 drops straight in», обязана к этому моменту уже сказать, с
    чем человек имеет дело.
    """
    kind = hazard_kind(cell)
    if not kind:
        return ""
    d = cell.get("diameter")
    h = cell.get("height")
    v = cell.get("volts") or 0.0
    lead = ("<b>%s is a button cell: %s mm across and %s mm tall.</b> "
            "United States law defines that class by the shape alone — a "
            "single cell battery with a diameter greater than its height, "
            "16 CFR 1263.2 — and not by what is inside it. Swallowed, a cell "
            "this shape can lodge instead of passing, and it is the current, "
            "not the metal, that does the damage."
            % (_name(cell), mm(d), mm(h)))
    # Телефон стоит в самом предложении, а не в отдельной постоянной: проза
    # проверяется разбором ШАБЛОНОВ, и величина, спрятанная в имя, уходит
    # из-под проверки вместе с объяснением, откуда она взялась.
    lead += (" If one has been swallowed, or put in a nose or an ear, call "
             "the United States national Poison Help line at 1-800-222-1222 "
             "straight away and do not wait for symptoms.")
    items = []
    if (d or 0) >= INGEST_MM and v >= 3.0:
        items.append("At %s mm and %s this is the size and the voltage behind "
                     "the most severe reported injuries: lodged against "
                     "tissue, a cell this diameter can burn through it in "
                     "hours, not days." % (mm(d), volts_num(v)))
    else:
        items.append("At %s mm and %s it is under the %s mm diameter that "
                     "lodges most readily — which makes it easier to swallow, "
                     "not safer. The same current runs for as long as it sits."
                     % (mm(d), volts_num(v), mm(INGEST_MM)))
    if kind == "covered":
        items.append("Reese's Law (15 U.S.C. 2056e) and 16 CFR part 1263 put "
                     "child-resistant packaging and a warning label on this "
                     "class; packages manufactured or imported after "
                     "21 September 2024 carry it. That is why the pack is "
                     "hard to open.")
    else:
        items.append("Zinc air is the one exception, and it is written into "
                     "the rule: 16 CFR 1263.1(d) records the Commission's "
                     "determination that zinc-air button cells do not present "
                     "an ingestion hazard, so part 1263 does not cover this "
                     "cell. The determination is about the burn. A swallowed "
                     "object is still a swallowed object, and this one lives "
                     "in the drawer where the pills are.")
    disposal = ("The same rule says what to do with the used cell, in its own "
                "words: dispose of it at once, keep it away from children, "
                "and do NOT put it in household trash (16 CFR 1263.4(b)(3)). "
                "Tape over both faces first — a cell too flat to run a watch "
                "still has enough left to burn.")
    if chem(cell) == "mercuric oxide":
        disposal += (" Mercury cells are hazardous waste on top of that, and "
                     "were withdrawn from United States consumer sale for "
                     "exactly that reason.")
    items.append(disposal)
    return ('<aside class="bx-warn" role="note" aria-labelledby="bx-warn-h">'
            '<p class="bx-warn-sig" id="bx-warn-h">Warning — button cell'
            '</p><p class="bx-warn-lead">%s</p>'
            '<ul class="bx-warn-list" role="list">%s</ul></aside>'
            % (lead, "".join("<li>%s</li>" % i for i in items)))


def _duty_extras(cell, s, cs):
    """Общий хвост фактов, ПОСЧИТАННЫХ для этой страницы. Он стоит после
    ветвевых и добирает страницу там, где источник о ней немногословен."""
    out = []
    reps = s.get("reps") or []
    live = [r for r in reps if r["cell"]["active"]]
    if reps:
        out.append("%s %s close enough to compare against it %s, and %d of "
                   "%s %s still listed."
                   % (plural(len(reps), "cell"), P.verb(len(reps), "measure"),
                      SCOPE, len(live), "them" if len(reps) > 1 else "it",
                      P.verb(len(live), "are")))
        first = reps[0]
        if first.get("volt"):
            out.append("The nearest is %s: it %s and runs %s, %s."
                       % (_name(first["cell"]), FIT_VERB.get(first["fit"],
                                                             "measures close"),
                          volts_num(first["cell"].get("volts")),
                          esc(P.V_TAG.get(first["volt"]["class"],
                                          first["volt"]["class"]))))
    if s.get("rank") and s["rank"][1] > 1:
        out.append("By stored energy it stands %d of %d in its envelope, at "
                   "%s milliwatt-hours."
                   % (s["rank"][0], s["rank"][1], _num(s["rank"][2])))
    if cell.get("regions"):
        out.append("Energizer files it for %s, which is where the part is "
                   "sold rather than where the cell will work."
                   % listing([esc(r) for r in cell["regions"][:4]]))
    if not cell["active"]:
        out.append("Energizer no longer lists %s at all, so whatever goes "
                   "into that compartment next will be a substitution rather "
                   "than a replacement." % _name(cell))
    elif cell.get("products"):
        out.append("The maker still lists it, under %s: %s."
                   % (plural(len(cell["products"]), "product line"),
                      listing([esc(x) for x in cell["products"][:4]])))
    return out


# --------------------------------------- 2. ЧТО ЕЩЁ ЕСТЬ В ДАТАШИТЕ (figures)

FIG_HEAD = {
    "impedance": _head("The number a pulse sees", "intro"),
    "cold": _head("What the maker says about cold", "intro"),
    "cutoff": _head("Where the capacity figure stops counting", "intro"),
    "shelf": _head("What it loses standing still", "intro"),
    "silent": _head("What the datasheet does not say", "intro"),
}


def figures_kind(cell):
    """Форма — это НАБОР ЗАПОЛНЕННЫХ ПОЛЕЙ. Молчание источника о поле такая
    же форма, как и число в нём, и говорить о нём надо своими словами."""
    if cell.get("ohms_lo") and cell.get("ohms_hi"):
        return "impedance"
    if cell.get("op_lo") is not None:
        return "cold"
    if cell.get("self_discharge"):
        return "shelf"
    if cell.get("cutoff"):
        return "cutoff"
    return "silent"


def figures_block(cell, s, cs):
    kind = figures_kind(cell)
    rows = []
    if cell.get("ohms_lo") and cell.get("ohms_hi"):
        rows.append(("Internal impedance",
                     "%s to %s ohms as published. A high-impedance cell "
                     "sags under a pulse and recovers between pulses, which "
                     "is what a movement or a sensor sees."
                     % (mm(cell["ohms_lo"]), mm(cell["ohms_hi"]))))
    if cell.get("op_lo") is not None and cell.get("op_hi") is not None:
        rows.append(("Operating range",
                     "%s to %s. Below the lower figure the maker makes no "
                     "claim at all, which is not the same as the cell "
                     "stopping." % (_degrees(cell["op_lo"]),
                                    _degrees(cell["op_hi"]))))
    if cell.get("cutoff"):
        rows.append(("Cutoff voltage",
                     "%s. The published capacity is counted down to this "
                     "voltage; a device that quits higher up sees less than "
                     "the whole figure." % volts_num(cell["cutoff"])))
    if cell.get("self_discharge"):
        rows.append(("Self-discharge",
                     "About %s per year on the shelf, which is the figure "
                     "that decides how a spare stored in a drawer behaves."
                     % (mm(cell["self_discharge"]) + "%")))
    if cell.get("classification"):
        rows.append(("Maker's classification",
                     "%s. That is the maker's own filing word for the part, "
                     "not a standard designation."
                     % esc(cell["classification"])))
    ck = cell.get("code_check") or {}
    if ck.get("verdict") == "exact":
        rows.append(("The code read as a measurement",
                     "%s encodes %s mm across and %s mm tall, and the "
                     "published dimensions agree exactly. On a figure with "
                     "one source that is the only independent check there is."
                     % (_name(cell), mm(ck.get("d_code")),
                        mm(ck.get("h_code")))))
    elif ck.get("verdict") == "rounded":
        rows.append(("The code read as a measurement",
                     "%s encodes %s x %s mm where the sheet measures "
                     "%s x %s mm. The standard writes whole millimeters, so "
                     "that is rounding and not disagreement."
                     % (_name(cell), mm(ck.get("d_code")), mm(ck.get("h_code")),
                        mm(ck.get("d_real")), mm(ck.get("h_real")))))
    if cell.get("grams") and cell.get("cc"):
        rows.append(("Mass against volume",
                     "%s g filling %s cubic centimeters. When the printing "
                     "has worn off, a kitchen scale separates two cells of "
                     "one envelope faster than a caliper does."
                     % (mm(cell["grams"]), P.cc_num(cell["cc"]))))
    if cell.get("regions"):
        rows.append(("Where the part is filed",
                     "%s. That is a statement about the maker's distribution "
                     "and not about where the cell works."
                     % listing([esc(r) for r in cell["regions"]])))
    head = FIG_HEAD[kind]
    lead = _figures_lead(cell, s, cs, kind, len(rows))
    html, _left = _paras(head, lead, _figures_extras(cell, s))
    return html + _dl(rows[:6])


def _figures_extras(cell, s):
    """Добавки к вводному абзацу — тоже посчитанные для ЭТОЙ страницы."""
    out = []
    if cell.get("cc") and cell.get("grams"):
        out.append("The part occupies %s cubic centimeters and weighs %s g."
                   % (P.cc_num(cell["cc"]), mm(cell["grams"])))
    if cell.get("mah") and cell.get("volts"):
        out.append("Capacity and voltage together put %s milliwatt-hours in "
                   "that space." % _num(cell["mah"] * cell["volts"]))
    if cell.get("regions"):
        out.append("Energizer files it for %s."
                   % listing([esc(r) for r in cell["regions"][:3]]))
    return out


def _figures_lead(cell, s, cs, kind, n):
    rest = max(n - 1, 0)
    if kind == "impedance":
        return ("Energizer publishes an impedance band of %s to %s ohms for "
                "%s. It is the least quoted number on the sheet and the one "
                "that decides whether the cell can drive a pulse; %d other "
                "published %s %s below."
                % (mm(cell["ohms_lo"]), mm(cell["ohms_hi"]), _name(cell),
                   rest, _word(rest, "figure"), P.verb(rest, "sit")))
    if kind == "cold":
        return ("The sheet for %s carries an operating range as well as a "
                "capacity, and it reaches %s at the cold end. %d more "
                "published %s %s it, and none of them reaches a "
                "cross-reference table."
                % (_name(cell), _degrees(cell["op_lo"]), rest,
                   _word(rest, "figure"), P.verb(rest, "follow")))
    if kind == "shelf":
        return ("%s is one of the few parts the maker publishes a shelf-loss "
                "figure for at all: about %s per year, beside %d other "
                "published %s."
                % (_name(cell), mm(cell["self_discharge"]) + "%", rest,
                   _word(rest, "figure")))
    if kind == "cutoff":
        return ("A capacity figure means nothing without the voltage it was "
                "counted to. For %s the maker counts down to %s, and %d "
                "published %s %s beside it."
                % (_name(cell), volts_num(cell["cutoff"]), rest,
                   _word(rest, "figure"), P.verb(rest, "sit")))
    return ("Beyond size and voltage the sheet for %s is thin: %d published "
            "%s below, and no impedance, no cutoff and no operating range at "
            "all. That silence is the maker's, not ours."
            % (_name(cell), n, _word(n, "figure")))


# ------------------------------------------- 3. ЧУЖИЕ ИМЕНА (markings) [M3/M7]

MARK_HEAD = {
    "trade": _head("The names on the package that are not designations",
                   "intro"),
    "long": _head("The same cell under its full IEC form", "intro"),
    "px": _head("The mercury-era part numbers", "intro"),
    "otherchem": _head("Names filed here that belong to another chemistry",
                       "intro"),
    "maker": _head("The maker's own part numbers", "intro"),
    "bare": _head("Nothing else is stamped on this one", "intro"),
}

_MARKS = None


def marking_index():
    """Маркировка -> (обозначение, чья условность). Строится ОДИН раз."""
    global _MARKS
    if _MARKS is None:
        _MARKS = {}
        for mark, iec, whose in C.TRADE_MARKINGS:
            _MARKS.setdefault(iec, []).append((mark, whose))
    return _MARKS


def markings_for(cell):
    idx = marking_index()
    out = list(idx.get(cell["code"], ()))
    lng = cell.get("iec_long")
    if lng:
        out += [x for x in idx.get(lng, ()) if x not in out]
    return out


def markings_kind(cell):
    if markings_for(cell):
        return "trade"
    if cell.get("iec_long"):
        return "long"
    if cell.get("px_forms"):
        return "px"
    if cell.get("aliases_other_chem"):
        return "otherchem"
    if cell.get("aliases"):
        return "maker"
    return "bare"


def markings_block(cell, s, cs):
    kind = markings_kind(cell)
    marks = markings_for(cell)
    items = []
    for mark, whose in marks[:4]:
        items.append("<b>%s</b> &mdash; %s." % (esc(mark),
                                                esc(C.MARKING_WHOSE[whose])))
    if cell.get("iec_long"):
        items.append("<b>%s</b> &mdash; the same designation written out in "
                     "full: the standard's long form for %s."
                     % (esc(cell["iec_long"]), _name(cell)))
    for a in (cell.get("px_forms") or [])[:2]:
        items.append("<b>%s</b> &mdash; a mercury-era part number for this "
                     "envelope, carried over by the trade after the "
                     "chemistry left it." % esc(a))
    for a, ch in (cell.get("aliases_other_chem") or [])[:2]:
        items.append("<b>%s</b> &mdash; filed under this designation by the "
                     "maker but recorded as %s, which is a different cell in "
                     "the same shape." % (esc(a), esc(ch)))
    for a in (cell.get("aliases") or [])[:3]:
        items.append("<b>%s</b> &mdash; a manufacturer part number for %s, "
                     "not a standard designation." % (esc(a), _name(cell)))
    head = MARK_HEAD[kind]
    lead = _markings_lead(cell, s, cs, kind, marks, len(items))
    extras = []
    if cell.get("products") and len(cell["products"]) > 1:
        extras.append("The maker's own catalog carries %s under it."
                      % plural(len(cell["products"]), "product line"))
    if cell.get("code_check") and cell["code_check"].get("verdict") == "exact":
        extras.append("The digits themselves are a measurement: %s reads back "
                      "as the size on the caliper." % _name(cell))
    html, left = _paras(head, lead, extras)
    return html + _ul(items[:6] + left[:1])


def _markings_lead(cell, s, cs, kind, marks, n):
    n_al = len(cell.get("aliases") or [])
    if kind == "trade":
        whose = sorted({w for _m, w in marks})
        # «Ни одно не напечатано в Also stamped» — утверждение о НАБОРЕ, а
        # строка Also stamped печатает cell["aliases"]. На /lr44/ там стояло
        # A76, названное этой же фразой отсутствующим. Пересечение считается.
        also = [m for m, _w in marks if m in (cell.get("aliases") or [])]
        # Оговорка держится в тех же словах по длине: абзац этого раздела
        # живёт в окне 18-56 слов, и объяснение на две строки роняло /lr44/
        # целиком. Проверка объёма — тоже проверка.
        if not also:
            tail = ("and no standards body stands behind any of them, which "
                    "is why none is printed under Also stamped above")
        elif len(also) <= 3:
            tail = ("and no standards body stands behind any of them, so "
                    "only %s %s under Also stamped above"
                    % (listing([esc(m) for m in also]),
                       P.verb(len(also), "appear")))
        else:
            tail = ("and no standards body stands behind any of them, so %d "
                    "of them appear under Also stamped above" % len(also))
        return ("%s answers to %s outside the standard: %s. %s, %s."
                % (_name(cell), plural(len(marks), "marking"),
                   listing([esc(m) for m, _w in marks[:4]]),
                   listing([esc(C.MARKING_WHOSE[x]).capitalize()
                            for x in whose]), tail))
    if kind == "long":
        return ("The standard writes this designation two ways. %s is the "
                "short form and %s is the same cell written out; a package "
                "may carry either, and %d of the maker's own part %s %s "
                "beside them."
                % (_name(cell), esc(cell["iec_long"]), n_al,
                   _word(n_al, "number"), P.verb(n_al, "sit")))
    if kind == "px":
        return ("Before the chemistry changed, this envelope was sold under "
                "part numbers rather than a designation. %s of them still "
                "turn up on old equipment and in old manuals, alongside %s "
                "current names."
                % (plural(len(cell["px_forms"]), "number"), n_al))
    if kind == "otherchem":
        return ("The maker files %s under this designation with a different "
                "chemistry recorded against %s. Same code, different insides, "
                "and the package is the only place that says which."
                % (plural(len(cell["aliases_other_chem"]), "name"),
                   plural(len(cell["aliases_other_chem"]), "one")))
    if kind == "maker":
        return ("%s carries %s beyond the designation, and every one of them "
                "is a manufacturer part number: a catalog line, not a size "
                "and not a standard."
                % (_name(cell), plural(n_al, "name")))
    same = _same_shell(cell, cs)
    if same:
        return ("Nothing else is printed on %s %s: one designation, no trade "
                "marking, no part number. %s in the same envelope %s named "
                "otherwise, so a marking you are holding is more likely "
                "theirs." % (_name(cell), SCOPE, _names(same),
                             P.verb(len(same[:3]), "are")))
    # «Шесть знаков» было набрано руками и печаталось на 29 страницах, из
    # них на 19 неверно: «346» — три знака, «3-315IWC» — восемь. Считаем.
    return ("Nothing else is printed on %s %s: one designation, no trade "
            "marking, no maker's part number, and no long form in the "
            "standard's table. A cell measuring %s carries its whole identity "
            "in %s."
            % (_name(cell), SCOPE,
               esc(C.shell_label(C.shell(cell)) or "an unpublished size"),
               plural(len(cell["code"]), "character")))


# ------------------------------------------------ 4. С ЧЕМ ПУТАЮТ (mistaken)

# Что обозначения говорят о разнице глубин — по одному ответу на каждый
# посчитанный случай, и ни одного на все три сразу.
CODE_DEPTH = {
    "written": "which the standard writes into both codes",
    "differs": "which the codes disagree with the published sheet about",
    "absent": "which neither designation carries",
}

MIST_HEAD = {
    # «На один знак» было набрано руками и неверно на 77 парах соседей:
    # CR1616 и CR1620 расходятся ДВУМЯ знаками, и знаки эти — глубина.
    # Величину, которую нечем посчитать в заголовке, заголовок не называет.
    "ladder": _head("The cell that differs only in depth", "intro"),
    "chem": _head("The identical cell with different insides", "intro"),
    "diameter": _head("Near the same width, and not the same cell", "intro"),
    "sizename": _head("Sold under the same household name", "intro"),
    "none": _head("Little here to confuse it with", "intro"),
}


def _near_diameter(cell, cs):
    d = cell.get("diameter")
    if d is None:
        return []
    coin = C.is_coin(cell)
    out = []
    for c in cs:
        if c["code"] == cell["code"] or c.get("diameter") is None:
            continue
        if C.is_coin(c) != coin:
            continue
        # Расстояние — по НАПЕЧАТАННЫМ десятым, тем же, что стоят в
        # строке ниже: окно, посчитанное по сырым полям, впускало бы пару,
        # у которой напечатанная разница равна допуску.
        gap = abs(C.fit_gap(d, c["diameter"]))
        if C.FIT_MM < gap <= NEAR_MM:
            out.append((gap, c))
    return [c for _g, c in sorted(out, key=lambda x: (x[0], x[1]["code"]))]


def mistaken_block(cell, s, cs):
    sib = s.get("siblings") or []
    same = _same_shell(cell, cs)
    twin = [c for c in same if chem(c) != chem(cell)]
    near = _near_diameter(cell, cs)
    kin = [c for c in (s.get("size_kin") or []) if c.get("volts")]
    if sib:
        kind = "ladder"
    elif twin:
        kind = "chem"
    elif near:
        kind = "diameter"
    elif kin:
        kind = "sizename"
    else:
        kind = "none"
    items = []
    for c in sib[:3]:
        h = C.shell(c)[2]
        dh = h - C.shell(cell)[2]
        # «Which the standard writes into the code» стояло на всех 314
        # позициях и было верно на 30: у большинства соседей обозначение
        # размера не кодирует вовсе. Ответ СЧИТАЕТСЯ по обоим кодам.
        items.append("<b>%s</b> &mdash; same diameter, %s mm tall against "
                     "this cell's %s: %s mm %s, %s."
                     % (_name(c), mm(h), mm(C.shell(cell)[2]),
                        mm(abs(dh)), "deeper" if dh > 0 else "shallower",
                        CODE_DEPTH[C.code_depth_verdict(cell, c)]))
    for c in twin[:2]:
        items.append("<b>%s</b> &mdash; the same %s in %s at %s. Identical "
                     "on a caliper, different in the circuit."
                     % (_name(c), esc(C.shell_label(C.shell(cell))),
                        esc(chem(c)), volts_num(c.get("volts"))))
    for c in near[:2]:
        # «Десятая доля миллиметра под пальцем» была НАБРАНА РУКАМИ рядом с
        # двумя числами, которые её опровергают: ветка впускает только
        # расстояния от допуска посадки до NEAR_MM, то есть десятой доли
        # здесь не бывает НИКОГДА — 175 строк, 175 неверных. И минимизировала
        # эта фраза ровно то различие, ради которого сайт заведён.
        gap = abs(C.fit_gap(cell["diameter"], c["diameter"]))
        # Вердикт посадки и напряжение стоят в ОДНОМ предложении: правило
        # сайта требует, чтобы слово о посадке не выходило без последствия
        # по электрике, а прежняя разбивка на два предложения прятала код
        # от этой проверки, а не отвечала на неё.
        items.append("<b>%s</b> &mdash; %s mm across at %s against %s mm "
                     "here, %s mm apart: %s in this holder."
                     % (_name(c), mm(c["diameter"]), volts_num(c.get("volts")),
                        mm(cell["diameter"]), mm(gap),
                        "too wide to enter" if c["diameter"] > cell["diameter"]
                        else "loose"))
    for c in kin[:2]:
        if c.get("volts") and cell.get("volts") and c["volts"] != cell["volts"]:
            items.append("<b>%s</b> &mdash; sold as the same %s and rated %s "
                         "against this cell's %s."
                         % (_name(c), esc(cell.get("size") or "size"),
                            volts_num(c["volts"]), volts_num(cell["volts"])))
    head = MIST_HEAD[kind]
    lead = _mistaken_lead(cell, s, cs, kind, sib, twin, near, kin)
    extras = []
    if s.get("rank") and len(s["rank"]) >= 2:
        # Ранг без итога — не ранг: «#37» без «из 57» у нас уже уезжало.
        extras.append("It stands %d of %d in this envelope by stored energy."
                      % (s["rank"][0], s["rank"][1]))
    if cell.get("grams"):
        extras.append("On a scale the difference shows before it shows on a "
                      "caliper: this one weighs %s g." % mm(cell["grams"]))
    html, left = _paras(head, lead, [e for e in extras if e])
    return html + _ul(items[:5] + left[:1])


def _mistaken_lead(cell, s, cs, kind, sib, twin, near, kin):
    if kind == "ladder":
        depths = [C.shell(c)[2] for c in sib]
        # «На один знак» было набрано руками и на 314 названных соседях
        # верно на 20: CR1616 и CR1620 расходятся ДВУМЯ знаками. Из
        # заголовка эту фразу уже убрали, а в лиде она пережила правку
        # дословно. Соседи отобраны по диаметру и глубине — это и сказано.
        return ("The code says the size, so the cells that get confused with "
                "%s are the ones that keep its diameter and change its "
                "depth. %s %s this diameter %s, and every one of them enters "
                "the same opening."
                % (_name(cell), plural(len(sib), "cell"),
                   P.verb(len(sib), "share"),
                   P.span(mm(min(depths)), mm(max(depths)),
                          "at %s mm", "at depths from %s to %s mm")))
    if kind == "chem":
        return ("Nothing about the outside of %s separates it from %s: the "
                "same %s, and %s against this cell's %s. The label is the "
                "whole difference."
                % (_name(cell), _names(twin),
                   esc(C.shell_label(C.shell(cell))),
                   volts_num(twin[0].get("volts")),
                   volts_num(cell.get("volts"))))
    if kind == "diameter":
        return ("No other cell %s measures this exactly, so the confusions "
                "are the near misses: %s %s within a millimeter of this "
                "cell's %s mm and %s not fit its holder."
                % (SCOPE, plural(len(near), "cell"),
                   P.verb(len(near), "sit"), mm(cell.get("diameter")),
                   P.verb(len(near), "do")))
    if kind == "sizename":
        return ("The household name is the trap here. %s %s sold as the same "
                "%s as %s and %s not all deliver the same voltage."
                % (plural(len(kin) + 1, "designation"),
                   P.verb(len(kin) + 1, "are"), esc(cell.get("size") or "size"),
                   _name(cell), P.verb(len(kin) + 1, "do")))
    if cell.get("diameter") is None:
        return ("Little gets confused with %s. Nothing %s shares its %s "
                "envelope, and a box cell has three measurements to agree on "
                "rather than two, which makes a near miss rarer and a wrong "
                "one more obvious."
                % (_name(cell), SCOPE,
                   esc(C.shell_label(C.shell(cell)) or "unpublished")))
    return ("Little gets confused with %s. Nothing %s shares its envelope, "
            "nothing sits within a millimeter of its %s mm, and it carries "
            "%s beyond the designation."
            % (_name(cell), SCOPE, mm(cell.get("diameter")),
               plural(len(cell.get("aliases") or []), "other name")))


# ------------------------------------------------------ 5. ИСТОЧНИКИ [M-8]

SRC_HEAD = {
    "one": _head("The record behind this page", "intro"),
    "many": _head("The records behind this page", "intro"),
    "split": _head("Records that disagree behind this page", "intro"),
}


def sources_kind(cell):
    recs = cell.get("records") or []
    if len({r["chem"] for r in recs if r["chem"]}) > 1 or \
            len({r["status"] for r in recs if r["status"]}) > 1:
        return "split"
    return "one" if len(recs) <= 1 else "many"


def sources_block(cell, s, cs, vintage, method_href="/method/"):
    """Нумерованные ссылки на источник — по одной на запись производителя.

    Сайт печатал «Source: Energizer technical data» в подвале 166 раз и не
    давал проверить ни одну цифру: ноль внешних адресов на весь корпус.
    Ссылка ведёт на ТОТ САМЫЙ файл, из которого разобраны величины.
    """
    recs = cell.get("records") or []
    kind = sources_kind(cell)
    items = []
    for i, r in enumerate(recs[:6], 1):
        url = C.tds_url(r["tds"])
        who = esc(r["title"] or cell["code"])
        bits = ["Energizer catalog record %d" % r["id"]]
        if r["title"] and r["title"].upper() != cell["code"].upper():
            bits.append("listed as %s" % who)
        if r["status"]:
            bits.append(r["status"].lower() + " in the snapshot")
        line = ", ".join(bits) + "."
        if url:
            line += (' Technical data sheet: <a href="%s" rel="nofollow '
                     'noopener">%s</a>.' % (esc(url), esc(r["tds"])))
        elif r["tds"] in C.TDS_MISSING:
            # Имя ЕСТЬ, файла по его адресу НЕТ. Разница названа вслух:
            # «не подан» и «подан, но не опубликован» — разные утверждения о
            # производителе, и второе проверяемо.
            line += (" Technical data sheet %s is named in the record, and "
                     "the manufacturer does not publish it at that address."
                     % esc(r["tds"]))
        else:
            line += " No technical data sheet is filed against this record."
        items.append('<span class="bx-refno">[%d]</span> %s' % (i, line))
    head = SRC_HEAD[kind]
    lead = _sources_lead(cell, recs, kind, vintage)
    lead, _left = _fill(head, lead, _sources_extras(cell, recs))
    return (_para(head, lead)
            + ('<ol class="bx-refs">%s</ol>'
               % "".join("<li>%s</li>" % i for i in items) if items else "")
            + '<p class="bx-src">Every figure above is reproduced from those '
              'records without change; the comparisons are ours and are '
              'described on the <a href="%s">method page</a>. Snapshot: %s.'
              '</p>' % (method_href, esc(vintage)))


def _sources_extras(cell, recs):
    out = []
    if recs:
        ids = [r["id"] for r in recs]
        out.append("Record %s in the maker's own catalog index."
                   % listing([str(i) for i in ids[:3]]))
    if cell.get("regions"):
        out.append("Filed for %s."
                   % listing([esc(r) for r in cell["regions"][:3]]))
    return out


def _sources_lead(cell, recs, kind, vintage):
    tds = [r for r in recs if r["tds"]]
    # СЧИТАЕТСЯ ТО, ЧТО БУДЕТ НАПЕЧАТАНО ССЫЛКОЙ, а не то, у чего есть имя
    # файла: у двух записей сборки имя есть, а производитель по этому адресу
    # отдаёт 404, и ссылку мы не ставим. Обещание «оно ниже по ссылке»
    # считается по тому же признаку, что и сама ссылка.
    lnk = [r for r in recs if C.tds_url(r["tds"])]
    if kind == "split":
        return ("%s is assembled from %s, and they do not agree with each "
                "other on every field. Both sides are numbered below so the "
                "disagreement can be read rather than taken on trust."
                % (_name(cell), plural(len(recs), "catalog record")))
    if kind == "many":
        return ("%s is not one catalog entry. %s carry this designation, %s "
                "of them with a technical data sheet, and each is numbered "
                "below%s."
                % (_name(cell), plural(len(recs), "record"), len(tds),
                   " with a direct link to the sheet the figures came from"
                   if len(lnk) == len(tds) else
                   ", with a link where the maker publishes the sheet"))
    if recs:
        if tds and not lnk:
            return ("Every figure on this page comes from one catalog "
                    "record, number %d, named below. Its technical data "
                    "sheet is named in that record too, and the maker does "
                    "not publish it at the address the record gives, so "
                    "there is nothing here to link to."
                    % recs[0]["id"])
        return ("Every figure on this page comes from one catalog record, "
                "number %d, and it is %s below. %s"
                % (recs[0]["id"], "linked" if lnk else "named",
                   "The sheet is the document the dimensions, voltage and "
                   "capacity were read out of." if tds
                   else "No technical data sheet is filed against it, which "
                        "is why several fields on this page are blank."))
    return ("No catalog record stands behind this designation in the "
            "snapshot, which is why this page carries fewer figures than "
            "most. It is here because %s appears in the maker's own code "
            "index." % _name(cell))


# --------------------------------- 6. МЕСТО СРЕДИ ВСЕГО ИЗМЕРЕННОГО (place)

PLACE_HEAD = {
    "big": _head("The largest thing of its shape here", "intro"),
    "small": _head("The smallest thing of its shape here", "intro"),
    "dense": _head("More energy per cubic centimeter than most", "intro"),
    "thin": _head("Less energy per cubic centimeter than most", "intro"),
    "crowded": _head("A width the catalog keeps returning to", "intro"),
    "lonely": _head("A width almost nothing else uses", "intro"),
}


def _shape_words(cell):
    """Класс предмета словом, в единственном и множественном. ОДНА функция:
    «boxes» — неправильное множественное, и правило «плюс s» дало «boxs» на
    живых страницах."""
    if (C.shell(cell) or ("",))[0] == "box":
        return "box", "boxes"
    one = "coin" if C.is_coin(cell) else "cylinder"
    return one, one + "s"


def _form_kin(cell, cs):
    """Всё того же класса предмета: монеты с монетами, цилиндры с цилиндрами,
    коробки с коробками. Сравнивать монету с цилиндром по объёму бессмысленно,
    и однажды сайт уже ставил цилиндр 7,9 x 39,8 в лестницу часового
    элемента."""
    coin = C.is_coin(cell)
    box = C.shell(cell) and C.shell(cell)[0] == "box"
    out = []
    for c in cs:
        if c["code"] == cell["code"] or not C.shell(c):
            continue
        if box:
            if C.shell(c)[0] == "box":
                out.append(c)
        elif C.shell(c)[0] == "round" and C.is_coin(c) == coin:
            out.append(c)
    return out


def place_kind(cell, s, cs):
    kin = _form_kin(cell, cs)
    vol = cell.get("cc")
    dens = s.get("dens_pct")
    d = cell.get("diameter")
    if vol and kin:
        vols = sorted(c["cc"] for c in kin if c.get("cc"))
        if vols and vol > vols[-1]:
            return "big"
        if vols and vol < vols[0]:
            return "small"
    if dens is not None and dens >= 75:
        return "dense"
    if dens is not None and dens <= 25:
        return "thin"
    if d is not None:
        near = [c for c in kin
                if c.get("diameter") is not None and abs(c["diameter"] - d) <= 0.5]
        return "crowded" if len(near) >= 3 else "lonely"
    return "crowded"


def place_block(cell, s, cs):
    kin = _form_kin(cell, cs)
    kind = place_kind(cell, s, cs)
    head = PLACE_HEAD[kind]
    shape_word, shape_many = _shape_words(cell)
    d = cell.get("diameter")
    near = [c for c in kin if c.get("diameter") is not None and d is not None
            and abs(c["diameter"] - d) <= 0.5]
    live_near = [c for c in near if c["active"]]
    lead = _place_lead(cell, s, cs, kind, kin, near)
    extras = []
    if near:
        extras.append("%s of those %s %s still listed."
                      % (len(live_near), _word(len(live_near), "one"),
                         P.verb(len(live_near), "are")))
    if s.get("dens_pct") is not None and s.get("dens"):
        extras.append("Its %s milliwatt-hours per cubic centimeter sit above "
                      "%d percent of everything here that publishes both a "
                      "capacity and a volume."
                      % (_num(s["dens"]), s["dens_pct"]))
    if cell.get("volts"):
        volt_kin = [c for c in kin if c.get("volts") == cell["volts"]]
        extras.append("%s of the %s %s %s its %s exactly."
                      % (len(volt_kin), len(kin), _word(len(kin), shape_word, shape_many),
                         P.verb(len(volt_kin), "share"),
                         volts_num(cell["volts"])))
    html, left = _paras(head, lead, extras)
    items = []
    if C.shell(cell) and cell.get("cc"):
        smaller = sorted((c for c in kin if c.get("cc") and c["cc"] < cell["cc"]),
                         key=lambda c: -c["cc"])
        bigger = sorted((c for c in kin if c.get("cc") and c["cc"] > cell["cc"]),
                        key=lambda c: c["cc"])
        # Объём печатался десятой долей, и у монеты это «0»: «шаг вниз по
        # объёму: 0 против 0 у этого элемента» на 45 строках, а рядом «0 cc,
        # 127% от этого» — процент считался по НЕнапечатанному значению.
        # Печать — P.cc_num, доля — от НАПЕЧАТАННЫХ величин, и там, где
        # напечатанные цифры совпали, слова «шаг» на странице нет.
        if smaller:
            items.append(_volume_step(cell, smaller[0], "down"))
        if bigger:
            items.append(_volume_step(cell, bigger[0], "up"))
    for c in near[:3]:
        items.append("<b>%s</b> &mdash; %s, %s, %s."
                     % (_name(c), esc(C.shell_label(C.shell(c))),
                        volts_num(c.get("volts")), esc(chem(c))))
    return html + _ul(items[:4] + left[:1])


def _volume_step(cell, c, way):
    """Соседняя ступень по объёму, обеими напечатанными величинами и долей,
    выведенной ИЗ НИХ ЖЕ."""
    here, there = P.cc_num(cell["cc"]), P.cc_num(c["cc"])
    if here == there:
        return ("<b>%s</b> &mdash; the next cell %s by volume, and the "
                "difference does not reach the digit this site prints: %s "
                "cubic centimeters on both." % (_name(c), way, here))
    if way == "down":
        return ("<b>%s</b> &mdash; the next step down by volume: %s cubic "
                "centimeters against this cell's %s."
                % (_name(c), there, here))
    # Доля считается от НАПЕЧАТАННЫХ величин: читатель делит то, что видит.
    return ("<b>%s</b> &mdash; the next step up: %s cubic centimeters, %s%% "
            "of this one."
            % (_name(c), there, _num(100.0 * float(there) / float(here))))


def _place_lead(cell, s, cs, kind, kin, near):
    # Форма слова берётся ОДНОЙ функцией: «51 boxs» напечаталось потому, что
    # правильное множественное знала только одна половина блока.
    shape_word, shape_many = _shape_words(cell)
    if kind == "big":
        return ("Nothing else shaped like this is larger %s. At %s cubic "
                "centimeters %s tops the %s %s the snapshot measures."
                % (SCOPE, mm(cell.get("cc")), _name(cell), len(kin) + 1,
                   _word(len(kin) + 1, shape_word, shape_many)))
    if kind == "small":
        return ("Nothing else shaped like this is smaller %s. %s cubic "
                "centimeters puts %s at the bottom of the %s %s measured "
                "here." % (SCOPE, mm(cell.get("cc")), _name(cell),
                           len(kin) + 1, _word(len(kin) + 1, shape_word, shape_many)))
    if kind == "dense":
        return ("%s packs more into its volume than most of what is measured "
                "here: %s milliwatt-hours per cubic centimeter, above %d "
                "percent of the corpus."
                % (_name(cell), _num(s["dens"]), s["dens_pct"]))
    if kind == "thin":
        return ("%s carries less in its volume than most: %s milliwatt-hours "
                "per cubic centimeter, below %d percent of everything here "
                "that publishes both figures."
                % (_name(cell), _num(s["dens"]), 100 - s["dens_pct"]))
    if kind == "crowded":
        return ("%s mm is a width this catalog keeps coming back to: %s %s "
                "within half a millimeter of it, %s included."
                % (mm(cell.get("diameter")), plural(len(near), shape_word, shape_many),
                   P.verb(len(near), "sit"), _name(cell)))
    return ("%s mm is a width almost nothing else uses. %s %s within half a "
            "millimeter of it %s, which is why the near misses below are "
            "measured rather than listed."
            % (mm(cell.get("diameter")), plural(len(near), shape_word, shape_many),
               P.verb(len(near), "sit"), SCOPE))


# ------------------------------------- 7. ЧЕГО ЭТА СТРАНИЦА НЕ ЗНАЕТ (gaps)
#
# Пропуск в записи — такая же ФОРМА, как заполненное поле, и по нему можно
# ветвиться. Больше того, ветвление по пропускам работает В ПРОТИВОФАЗЕ к
# остальным блокам: чем беднее запись, тем длиннее этот раздел, а бедные
# записи и были самыми тонкими страницами. И ни у одного конкурента в нише
# нет страницы, которая честно говорит, чего она не знает.

GAP_FIELDS = (
    ("mah", "capacity",
     "how long it runs, and every energy figure that depends on it"),
    ("cc", "volume",
     "energy per cubic centimeter, which is how cells of different shapes "
     "are compared here"),
    ("cutoff", "cutoff voltage",
     "what the capacity figure was counted down to, without which the "
     "capacity is a number without a scale"),
    ("grams", "mass",
     "energy per gram, and the one check that separates two cells of one "
     "envelope when the printing has worn off"),
    ("ohms_lo", "impedance",
     "whether the cell can drive a pulse, which is the whole question in a "
     "watch or a sensor"),
    ("op_lo", "operating temperature",
     "whether the maker claims anything at all below freezing"),
    ("volts", "nominal voltage",
     "every comparison on this site except the size"),
)

GAPS_HEAD = {
    "full": _head("Every field the maker fills is filled here", "intro"),
    "one": _head("One figure the maker does not publish", "intro"),
    "few": _head("What this page cannot tell you", "intro"),
    "many": _head("A thin record, and what that costs", "intro"),
}


def gaps_of(cell):
    return [(f, name, what) for f, name, what in GAP_FIELDS
            if not cell.get(f)]


def gaps_kind(cell):
    n = len(gaps_of(cell))
    if n == 0:
        return "full"
    if n == 1:
        return "one"
    return "few" if n <= 3 else "many"


def gaps_block(cell, s, cs):
    gaps = gaps_of(cell)
    kind = gaps_kind(cell)
    head = GAPS_HEAD[kind]
    filled = len(GAP_FIELDS) - len(gaps)
    if kind == "full":
        lead = ("%s is one of the better documented parts here: all %d of the "
                "fields this site reads are filled, which is why the tables "
                "above carry no blanks and every computed figure on the page "
                "has both of its inputs."
                % (_name(cell), len(GAP_FIELDS)))
    elif kind == "one":
        lead = ("One field is empty for %s: %s. A blank means the maker "
                "publishes no figure, which is not the same as zero, and it "
                "is the reason one comparison below is missing rather than "
                "wrong." % (_name(cell), esc(gaps[0][1])))
    elif kind == "few":
        lead = ("%d of the %d fields this site reads are empty for %s: %s. "
                "Everything computed from them is absent from this page "
                "rather than estimated."
                % (len(gaps), len(GAP_FIELDS), _name(cell),
                   listing([esc(g[1]) for g in gaps])))
    else:
        lead = ("The maker's record for %s is thin: %d of %d fields are "
                "blank, and only %d %s filled. What follows from a blank is "
                "an absence on this page, never a guess."
                % (_name(cell), len(gaps), len(GAP_FIELDS), filled,
                   P.verb(filled, "are")))
    extras = []
    recs = cell.get("records") or []
    if recs:
        extras.append("The blanks are the same in all %s behind this "
                      "designation, so they are the catalog's silence and not "
                      "a merge losing a value."
                      % plural(len(recs), "record"))
    if s.get("shell"):
        extras.append("What is not missing is the envelope: %s, published "
                      "and checked against the designation itself."
                      % esc(C.shell_label(s["shell"])))
    html, left = _paras(head, lead, extras)
    items = []
    for _f, name, what in gaps[:4]:
        items.append("<b>No %s</b> &mdash; so this page cannot tell you %s."
                     % (esc(name), what))
    if not items:
        for _f, name, _w in GAP_FIELDS[:3]:
            items.append("<b>%s</b> &mdash; published, and used above."
                         % esc(name).capitalize())
    return html + _ul(items[:4] + left[:1])


# --------------------------------------------------------------- сборка

def blocks(cell, s, cs, vintage):
    """Все пять блоков в порядке чтения. Порядок не случайный: сперва то,
    ради чего человек пришёл (во что это ставят), потом то, что об этом
    опубликовано, потом имена, потом путаница, и только в конце источники."""
    return (duty_block(cell, s, cs)
            + figures_block(cell, s, cs)
            + markings_block(cell, s, cs)
            + mistaken_block(cell, s, cs)
            + sources_block(cell, s, cs, vintage))


def selftest():
    """Известные ответы для функций формы. Гейт, сверяющий вывод с той же
    функцией, которая его посчитала, у нас уже был зелёным на сломанном
    сайте."""
    cs = C.build_cells()
    by = {c["code"]: c for c in cs}
    ctx = P.context(cs)
    want = {"PR44": "hearing", "MR9": "meter", "HR6": "rechargeable",
            "CR2032": "coinlithium", "CR1220": "coinlithium", "SR44": "watch",
            "6LR61": "alarm", "LR6": "household", "CR17345": "photo"}
    bad = []
    for code, kind in want.items():
        c = by.get(code)
        if not c:
            bad.append("%s: нет в данных" % code)
            continue
        got = duty_kind(c, P.shape(c, cs, ctx))
        if got != kind:
            bad.append("%s: класс прибора %s, ожидался %s" % (code, got, kind))
    return bad


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for line in selftest():
        print(line)
    print("depth.selftest готов")
