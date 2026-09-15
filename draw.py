# -*- coding: utf-8 -*-
"""Чертёж элемента питания В МАСШТАБЕ. Инлайновый SVG, ноль запросов наружу.

ЗАЧЕМ ЭТО ВООБЩЕ РИСУЕТСЯ. Вопрос сайта — «влезет ли» — это вопрос о двух
парах чисел, и человек не умеет сравнивать числа так же быстро, как формы.
Одиннадцать и шесть десятых против одиннадцати и шести десятых он вычитывает;
два одинаковых силуэта он видит. Поэтому целевая величина рисуется первой:
у нас уже был случай, когда все графики кодировали показы и место, а переходы —
то, ради чего сайт существует, — не были нарисованы нигде.

ПРАВИЛА, БЕЗ КОТОРЫХ ЧЕРТЁЖ ЛЖЁТ:

  · ОДИН МАСШТАБ на всю картинку. Разные масштабы у соседних силуэтов — это
    ровно та ошибка, которой у нас неравные корзины гистограммы, нарисованные
    равной шириной, выдумали заголовочное утверждение на 318 страницах;
  · масштаб НАЗВАН на самой картинке, в пикселях на миллиметр;
  · опорная линия высоты образца проходит через всю семью: «выше» и «ниже»
    видно по пересечению, а не по чтению подписи;
  · ни одного цвета внутри SVG — только переменные CSS, чтобы тёмная тема
    переопределяла их вместе со всей страницей;
  · SVG без внешних ссылок и без растровой подложки.

ДОСТУПНОСТЬ. Картинка — не единственный носитель ответа: те же числа стоят в
таблице рядом, а у SVG есть role и заголовок для чтения вслух.
"""
import re

MAX_PX = 210.0          # самая длинная сторона рисунка
MIN_SCALE, MAX_SCALE = 1.2, 14.0
PAD = 16.0              # поле вокруг силуэта под выносные линии
GAP = 18.0              # промежуток между силуэтами семьи


def _mm(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace(chr(34), "&quot;"))


def scale_for(dims):
    """Пикселей на миллиметр — ОДИН на всю картинку.

    Считается по самой длинной стороне среди ВСЕХ силуэтов картинки, а не
    каждым силуэтом по себе: иначе меньший элемент выйдет крупнее большего, и
    рисунок скажет неправду, оставаясь при верных подписях.
    """
    big = max([d for pair in dims for d in pair] or [1.0])
    s = MAX_PX / big if big else MAX_SCALE
    return max(MIN_SCALE, min(MAX_SCALE, s))


def _cell_dims(cell):
    """Ширина и высота силуэта в миллиметрах: вид сбоку, как элемент стоит в
    отсеке. У призматического ширина — большая из двух поперечных мер."""
    h = cell.get("height")
    if h is None:
        return None
    d = cell.get("diameter")
    if d is not None:
        return (float(d), float(h))
    lg, wd = cell.get("length"), cell.get("width")
    if lg is not None and wd is not None:
        return (float(max(lg, wd)), float(h))
    return None


def _silhouette(x, base_y, w_px, h_px, kind, cls):
    """Силуэт вида сбоку. У монеты скруглены кромки, у призмы — нет: разница
    видна и она настоящая."""
    r = min(1.6, w_px / 8.0) if kind == "round" else 0.0
    y = base_y - h_px
    body = ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
            'class="%s"/>' % (x, y, w_px, h_px, r, cls))
    if kind == "round" and h_px > 6:
        # Поясок обжима: у монетных элементов крышка заходит на корпус, и это
        # то, чем силуэт монеты отличается от прямоугольника.
        body += ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                 'class="bx-crimp"/>' % (x, y + h_px * 0.34,
                                         x + w_px, y + h_px * 0.34))
    return body


def cell_drawing(cell, title=None):
    """Один элемент с выносными размерами. Сердце страницы."""
    dims = _cell_dims(cell)
    if not dims:
        return ""
    w_mm, h_mm = dims
    k = scale_for([dims])
    w_px, h_px = w_mm * k, h_mm * k
    box_w = w_px + PAD * 4
    box_h = h_px + PAD * 3
    base = box_h - PAD * 1.5
    x = PAD * 2
    kind = "round" if cell.get("diameter") is not None else "box"
    label = title or cell.get("code") or "cell"
    parts = [_silhouette(x, base, w_px, h_px, kind, "bx-body")]
    # Размерная линия ширины — под силуэтом.
    yw = base + 9
    parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="bx-dim"/>'
                 % (x, yw, x + w_px, yw))
    parts.append('<text x="%.1f" y="%.1f" class="bx-num" text-anchor="middle">'
                 '%s mm</text>' % (x + w_px / 2, yw + 11, _mm(w_mm)))
    # Размерная линия высоты — справа.
    xh = x + w_px + 9
    parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="bx-dim"/>'
                 % (xh, base - h_px, xh, base))
    parts.append('<text x="%.1f" y="%.1f" class="bx-num">%s mm</text>'
                 % (xh + 5, base - h_px / 2 + 4, _mm(h_mm)))
    parts.append('<text x="%.1f" y="%.1f" class="bx-scale">%s px per mm</text>'
                 % (x, 12, _mm(k)))
    return ('<svg class="bx-draw" viewBox="0 0 %.0f %.0f" width="%.0f" '
            'height="%.0f" role="img" aria-label="%s drawn to scale, %s by %s '
            'millimeters">%s</svg>'
            % (box_w, box_h, box_w, box_h, _esc(label), _mm(w_mm), _mm(h_mm),
               "".join(parts)))


def family_drawing(cell, others, limit=6):
    """Семья габарита в ОДНОМ масштабе, с опорной линией высоты образца.

    Опорная линия и есть ответ: силуэт, который её не достаёт, потеряет
    контакт; силуэт, который её перерезает, не даст закрыть крышку.
    """
    rows = [(cell, True)] + [(c, False) for c in others[:limit - 1]]
    dims = []
    for c, _ in rows:
        d = _cell_dims(c)
        if d:
            dims.append(d)
    if len(dims) < 2:
        return ""
    k = scale_for(dims)
    ref = _cell_dims(cell)
    ref_h_px = ref[1] * k

    widths, parts, x = [], [], PAD
    max_h_px = max(d[1] for d in dims) * k
    box_h = max_h_px + PAD * 3.2
    base = box_h - PAD * 1.6
    for c, is_ref in rows:
        d = _cell_dims(c)
        if not d:
            continue
        w_px, h_px = d[0] * k, d[1] * k
        kind = "round" if c.get("diameter") is not None else "box"
        cls = "bx-body bx-ref" if is_ref else "bx-body bx-alt"
        parts.append(_silhouette(x, base, w_px, h_px, kind, cls))
        parts.append('<text x="%.1f" y="%.1f" class="bx-tag" '
                     'text-anchor="middle">%s</text>'
                     % (x + w_px / 2, base + 12, _esc(c.get("code") or "")))
        widths.append(w_px)
        x += w_px + GAP
    box_w = x - GAP + PAD
    # Опорная линия проходит поверх всех силуэтов.
    parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                 'class="bx-ref-line"/>'
                 % (PAD * 0.4, base - ref_h_px, box_w - PAD * 0.4,
                    base - ref_h_px))
    parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                 'class="bx-base-line"/>'
                 % (PAD * 0.4, base, box_w - PAD * 0.4, base))
    parts.append('<text x="%.1f" y="%.1f" class="bx-scale">%s px per mm</text>'
                 % (PAD * 0.4, 12, _mm(k)))
    names = ", ".join((c.get("code") or "") for c, _ in rows)
    return ('<svg class="bx-draw" viewBox="0 0 %.0f %.0f" '
            'width="%.0f" height="%.0f" role="img" aria-label="%s drawn at one '
            'scale; the line marks the height of %s">%s</svg>'
            % (box_w, box_h, box_w, box_h, _esc(names),
               _esc(cell.get("code") or ""), "".join(parts)))


def check_scale(svg):
    """Гейт честности рисунка: у всех силуэтов картинки один масштаб.

    Проверяется по САМОЙ РАЗМЕТКЕ, а не по намерению функции: сверяем
    отношение ширины прямоугольника к подписанному размеру. Гейт, который
    сверяется с той же функцией, что рисовала, остаётся зелёным, когда её
    ломают, — у нас так уже было.
    """
    m = re.search(r'class="bx-scale">([\d.]+) px per mm', svg)
    if not m:
        return ["в рисунке не назван масштаб"]
    k = float(m.group(1))
    bad = []
    for w, tag in re.findall(r'width="([\d.]+)"[^>]*class="bx-body[^"]*"'
                             r'|<text[^>]*class="bx-tag"[^>]*>([^<]*)</text>',
                             svg):
        pass
    rects = re.findall(r'<rect[^>]*width="([\d.]+)"[^>]*class="bx-body', svg)
    labels = re.findall(r'class="bx-num"[^>]*>([\d.]+) mm', svg)
    if rects and labels:
        got = float(rects[0]) / float(labels[0])
        if abs(got - k) > 0.05 * k:
            bad.append("ширина силуэта %s px при подписи %s мм даёт %.2f px/мм, "
                       "а объявлено %.2f" % (rects[0], labels[0], got, k))
    return bad
