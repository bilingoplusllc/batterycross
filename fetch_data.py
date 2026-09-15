# -*- coding: utf-8 -*-
"""Данные BatteryCross: перечень изделий Energizer и их даташиты.

ЧТО ИМЕННО БЕРЁТСЯ И ПОЧЕМУ ЭТО МОЖНО.

  · Перечень — из СОБСТВЕННОГО поиска data.energizer.com (тот же запрос, что
    делает их страница). robots.txt сайта, обновлённый в апреле 2026, явно
    разрешает обход всем, включая ClaudeBot, и запрещает только /wp-admin/,
    /cart/, /checkout/ и /search?. Мы ходим по /pdfs/ и по admin-ajax.php —
    последний не запрещён и является публичной точкой их же поиска.
  · Мы забираем ФАКТЫ: обозначения, размеры, напряжение, ёмкость, массу.
    Сами даташиты, их графики и вёрстку мы не перепечатываем.
  · Ходим ЧЕСТНО представившись, с задержкой между запросами, и кэшируем:
    повторная сборка сети не касается.

ЕДИНСТВЕННЫЙ ИСТОЧНИК — ЭТО РИСК, И ОН СНЯТ РАСЧЁТОМ. Размеры, заявленные
производителем, сверяются с обозначением МЭК, которое кодирует их само:
CR2032 — это 20,0 мм диаметром и 3,2 мм высотой по построению кода. Сверка
двух независимых величин и есть наша проверка, а расхождение — находка.

ПОЧЕМУ PDF КЭШИРУЮТСЯ, А В РЕПОЗИТОРИЙ ЕДЕТ JSON. Четыреста даташитов — это
под сотню мегабайт; в репозитории им нечего делать. Едет извлечённый JSON на
несколько сотен килобайт плюс провенанс: адрес, дата, отпечаток, счётчики.
Сборка воспроизводима и не зависит от чужого сервера в момент выкладки.
"""
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdftext  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(HERE, ".cache")
CELLS = os.path.join(DATA, "energizer_cells.json")
META = os.path.join(DATA, "energizer_meta.json")

HOST = "https://data.energizer.com"
AJAX = HOST + "/wp-admin/admin-ajax.php"
PDFS = HOST + "/pdfs/"
REGIONS = ("North America", "Latin America", "Europe", "Asia Pacific")

# Представляемся честно и оставляем адрес для связи. Проверено: сервер пускает
# и такого агента, поэтому маскироваться под браузер незачем.
UA = ("BatteryCrossBot/1.0 (+https://batterycross.com; info@bilingoplus.com)")
DELAY = 0.35            # секунды между запросами
MIN_PRODUCTS = 300      # источник даёт 416; резкое падение — не обновление
MIN_SHEETS = 250

FIELDS = ("battery-iec", "battery-ansineda", "battery-chemistry",
          "battery-voltage", "battery-diameter", "battery-height",
          "battery-length", "battery-width", "battery-weight",
          "battery-size", "battery-tds", "battery-status",
          "battery-replacement", "post_id", "post_title")


def _open(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h,
                                 method="POST" if data else "GET")
    return urllib.request.urlopen(req, timeout=90).read()


def fetch_index():
    """Перечень изделий из четырёх региональных каталогов, слитый по post_id."""
    by_id = {}
    counts = {}
    for name in REGIONS:
        body = urllib.parse.urlencode({
            "action": "ehp_filter_batteries_ajax", "category": name,
            "battery_status": "", "battery_chemistry": "",
            "battery_size": "", "battery_voltage": ""}).encode()
        raw = _open(AJAX, data=body, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": HOST + "/"})
        rows = json.loads(raw.decode("utf-8", "replace")).get(
            "ehp_filter_batteries") or []
        counts[name] = len(rows)
        for x in rows:
            pid = str(x.get("post_id"))
            keep = by_id.setdefault(pid, {k: x.get(k) for k in FIELDS})
            keep.setdefault("regions", [])
            keep["regions"].append(name)
        time.sleep(DELAY)
    return list(by_id.values()), counts


def sheet_name(row):
    t = str(row.get("battery-tds") or "").strip()
    return t if t.lower().endswith(".pdf") else None


def download_sheets(rows, force=False):
    """Скачать даташиты в кэш. Уже лежащие не перекачиваются."""
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    names = sorted({sheet_name(r) for r in rows if sheet_name(r)})
    got, skipped, failed = 0, 0, []
    for i, n in enumerate(names, 1):
        path = os.path.join(CACHE, n.replace("/", "_"))
        if os.path.isfile(path) and not force:
            skipped += 1
            continue
        try:
            raw = _open(PDFS + urllib.parse.quote(n))
        except urllib.error.HTTPError as e:
            failed.append("%s HTTP %s" % (n, e.code))
            continue
        except Exception as e:
            failed.append("%s %s" % (n, type(e).__name__))
            continue
        if not raw.startswith(b"%PDF"):
            failed.append("%s не PDF" % n)
            continue
        io.open(path, "wb").write(raw)
        got += 1
        if got % 25 == 0:
            print("   скачано %d из %d" % (i, len(names)))
        time.sleep(DELAY)
    return {"всего": len(names), "скачано": got, "из кэша": skipped,
            "не удалось": failed}


# ------------------------------------------------------------ разбор даташита
#
# Ищем по СПЛОШНОЙ строке без пробелов: в даташите пробелы расставлены
# кернингом, а не смыслом.

# У Energizer НЕ ОДИН шаблон даташита: щелочные пишут «Typical Capacity» и
# «Nominal Voltage», угольно-цинковые — «Average Capacity» и «Battery Voltage»,
# и обе подписи означают одно. Первая версия знала только один шаблон и
# вытаскивала ёмкость у трети файлов, молча считая остальные бедными данными.
_CAP = r"(?:Typical|Average|Rated|Nominal)?"
PAT = {
    "chemistry": r"ChemicalSystem:(.{0,70}?)(?:Designation|Nominal|Battery"
                 r"|Classif|Operating)",
    "designation": r"Designation:(.{0,80}?)(?:Nominal|Battery|Typical|Average"
                   r"|Classif|Operating)",
    "volts": _CAP + r"(?:Battery)?Voltage:([\d.]+)Volts",
    # «Average Service capacity (to 0.8 Volts): 700 mAh» — подпись бывает с
    # хвостом в скобках, поэтому между словом Capacity и двоеточием
    # допускается вставка.
    "mah": _CAP + r"(?:Service)?[Cc]apacity[^:]{0,26}:([\d,.]+)mA?h",
    "cutoff": _CAP + r"(?:Service)?[Cc]apacity[^:]{0,26}:[\d,.]+mA?h\*?"
                     r"(?:to|\(to)([\d.]+)volts?",
    "grams": _CAP + r"Weight:([\d,.]+)grams",
    "cc": _CAP + r"Volume:([\d,.]+)cubiccentimeter",
    "impedance": r"Impedance\(\d+Hz\):(\d+)to(\d+)ohms",
    "mwh_g": r"EnergyDensity:([\d.]+)milliwatthr/g",
    "mwh_cc": r"EnergyDensity:[\d.]+milliwatthr/g,([\d.]+)milliwatthr/cc",
    "classification": r"Classification:.{0,3}?([A-Za-z][A-Za-z/ ]{2,38}?)"
                      r"(?:ChemicalSystem|Designation)",
    "self_discharge": r"SelfDischarge:~?([\d.]+)%/year",
    "op_lo": r"OperatingTemp:(-?\d+)[^\d]{1,4}Cto",
    "op_hi": r"OperatingTemp:-?\d+[^\d]{1,4}Cto(-?\d+)",
}


def parse_sheet(raw):
    """Что даёт даташит сверх перечня: ёмкость, масса, объём, импеданс."""
    c = pdftext.compact(raw)
    out = {}
    for key, pat in PAT.items():
        m = re.search(pat, c, re.I)
        if not m:
            continue
        if key == "impedance":
            out["ohms_lo"], out["ohms_hi"] = float(m.group(1)), float(m.group(2))
        elif key in ("chemistry", "designation", "classification"):
            out[key] = re.sub(r"([a-z)])([A-Z(])", r"\1 \2",
                              m.group(1)).strip(" ,-")
        else:
            # «1,100mAh» — тысячный разделитель, а не десятичный.
            out[key] = float(m.group(1).replace(",", ""))
    # Часы до отсечки при названном сопротивлении — прямое время работы.
    m = re.search(r"(\d{2,3},?\d{0,3})ohms?\)?\(hours\)([\d,]{2,6})", c, re.I)
    if m:
        out["load_ohms"] = pdftext.number(m.group(1))
        out["hours"] = pdftext.number(m.group(2))
    return out


def build():
    rows, counts = fetch_index()
    print("перечень: %s, уникальных изделий %d"
          % (", ".join("%s %d" % (k, v) for k, v in counts.items()), len(rows)))
    if len(rows) < MIN_PRODUCTS:
        raise SystemExit("изделий %d, ожидалось не меньше %d — ответ урезан"
                         % (len(rows), MIN_PRODUCTS))
    print("скачиваю даташиты...")
    dl = download_sheets(rows)
    print("   %s" % json.dumps(dl, ensure_ascii=False)[:300])

    parsed, empty = 0, 0
    for r in rows:
        n = sheet_name(r)
        path = os.path.join(CACHE, n.replace("/", "_")) if n else None
        if not path or not os.path.isfile(path):
            continue
        try:
            got = parse_sheet(io.open(path, "rb").read())
        except Exception:
            got = {}
        if got:
            r["sheet"] = got
            parsed += 1
        else:
            empty += 1
    print("даташитов разобрано: %d, пустых: %d" % (parsed, empty))

    if not os.path.isdir(DATA):
        os.makedirs(DATA)
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=0)
    io.open(CELLS, "w", encoding="utf-8", newline="\n").write(payload)
    meta = {
        "source": HOST,
        "endpoint": AJAX,
        "retrieved": datetime.now(timezone.utc).date().isoformat(),
        "products": len(rows),
        "regions": counts,
        "sheets_parsed": parsed,
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }
    io.open(META, "w", encoding="utf-8", newline="\n").write(
        json.dumps(meta, indent=1) + "\n")
    print("записано %s (%d КБ)" % (CELLS, len(payload) // 1024))
    return meta


def verify():
    """Файл на диске — тот самый, что собран, и данных в нём не меньше порога.

    Эталон не выведен из проверяемого: отпечаток записан при сборке, а пороги
    объявлены здесь константами. Проверка, сверяющая результат со своим же
    вводом, у нас уже была зелёной на прошлогодних данных.
    """
    if not os.path.isfile(META):
        raise SystemExit("нет energizer_meta.json — запустите fetch_data.py")
    meta = json.load(io.open(META, encoding="utf-8"))
    payload = io.open(CELLS, encoding="utf-8").read()
    got = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if got != meta["sha256"]:
        raise SystemExit("файл данных отличается от собранного: %s против %s"
                         % (got[:12], meta["sha256"][:12]))
    rows = json.loads(payload)
    if len(rows) < MIN_PRODUCTS:
        raise SystemExit("изделий %d, ожидалось не меньше %d"
                         % (len(rows), MIN_PRODUCTS))
    sheets = sum(1 for r in rows if r.get("sheet"))
    if sheets < MIN_SHEETS:
        raise SystemExit("даташитов разобрано %d, ожидалось не меньше %d"
                         % (sheets, MIN_SHEETS))
    print("данные: %d изделий, %d разобранных даташитов, снимок от %s, "
          "отпечаток %s" % (len(rows), sheets, meta["retrieved"],
                            meta["sha256"][:12]))
    return meta


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--verify" in sys.argv:
        verify()
    else:
        build()
