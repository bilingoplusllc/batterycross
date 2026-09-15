# -*- coding: utf-8 -*-
"""Облик BatteryCross. Одна сырая строка CSS, ноль сборщиков (решение D-009).

НАПРАВЛЕНИЕ: «промышленный каталог». Выбрано из четырёх цельных направлений,
заказанных по BRIEF.md, и вот почему: сайтом пользуются под давлением — элемент
сел, прибор не работает, надо понять, что купить. Плотность, жёсткая сетка и
подпись у каждого условного знака работают на это; красивый крупный рендер
предмета — нет.

Привито от двух проигравших направлений:
  · СТРЕЛОЧНАЯ ШКАЛА напряжения (от «прибора»): отклонение видно положением
    штриха раньше, чем прочитаны проценты. Заказ требовал, чтобы опасность
    читалась до текста, и цифра в ячейке этого не даёт;
  · РАЗРЕЗНОЙ ЧЕРТЁЖ с выносками (от «чертежа») для детального вида.

ЧТО УЖЕ ЗАНЯТО НА ФЕРМЕ И ЧЕГО ЗДЕСЬ НЕТ. Зелёный акцент занят дважды
(MileageCurve, KeepsUntil) — здесь его нет вовсе. Кремово-синяя «документная»
палитра занята FedPay — здесь сталь. Заголовки Georgia поверх гротеска заняты
KeepsUntil — здесь гротеск и моноширинный, без засечек вовсе.

ПРАВИЛА СИСТЕМЫ, которые нельзя нарушать при правках:
  · ОДИН сигнальный цвет и ОДНА его работа: «эта величина вне нормы».
    Сегодня это ровно два носителя — штрих чужого напряжения на шкале и
    ячейка класса wrong в таблице, — и оба говорят одно и то же про одну и ту
    же величину. Второй акцент означает, что первый перестал быть сигналом;
  · ГРАНИЦА рисуется линейкой, а не цветом: края класса на шкале, опорная
    линия чертежа, правило раздела. Цветом помечается СЛУЧАЙ, попавший за
    границу, — и только он;
  · ТРИ веса линейки и ни одного четвёртого: --w1 волосяная между строками
    списка, --w2 средняя закрывает шапку и обводит силуэт, --w3 тяжёлая
    открывает раздел. Чертёж пользуется теми же тремя и никакими другими:
    четыре толщины обводки (1, 1.4, 1.6, 1.8) были четвёртым, пятым и шестым
    весом, просто внутри SVG;
  · ОДИН шаг ритма --u, ВСЕ отступы кратны ему, и множители подобраны так,
    чтобы результат был целым числом пикселей. Прежний --u:7px давал 5,6 и
    9,8 px при множителях .8 и 1.4, а рядом лежали набранные руками 2, 3 и
    4 px — то есть ритм был не один;
  · ОДНА шкала кегля, шесть ступеней и ни одной седьмой. Заголовок раздела
    НИКОГДА не мельче текста, который он открывает;
  · каждый цвет объявлен переменной в :root и переопределён в тёмной теме
    ПОД ТЕМ ЖЕ ИМЕНЕМ. Цвет, объявленный единственный раз внутри media-блока,
    — дефект: у нас так карточка осталась светлой внутри тёмной полосы при
    контрасте 1,07:1. И ни один цвет не объявляется через var() другого
    цвета: алиас вычисляется на :root и наследуется ЧИСЛОМ, поэтому смена
    темы на контейнере его не трогает;
  · нетекстовая графика не тусклее 3:1, текст не тусклее 4,5:1, и проверяется
    ПАРА, а не токен. У силуэта дважды не проверена была именно пара: заливка
    держалась темы, обводка ехала за темой, и в тёмной обводка встала на
    1,04:1 к панели. Пары перечислены в гейте «контраст пар держится», он
    считает их, а не смотрит глазами.

ПЕРЕЛОМЫ РАСКЛАДКИ ЗАДАНЫ В ПИКСЕЛЯХ, А НЕ В rem. Раньше стояло 63rem и
34rem. Рекламное место имеет размер В ПИКСЕЛЯХ и не тянется; пока перелом
колонок мерился в rem, при корневом кегле не 16 px арифметика «влезает ли
728 px в колонку» становилась неверной, а разъезд был бы невидим — реклама
наехала бы на башню без всякой полосы прокрутки. Величина и перелом теперь
меряются одним и тем же, и гейт «формат места влезает в колонку» проходит
ВСЕ ширины от 320 до 1600 и сверяет нарисованное с геометрией.
"""
import re


def strip_comments(css):
    """Убрать комментарии из CSS ПЕРЕД вставкой в страницу.

    Комментарии здесь по-русски, потому что объясняют решения; страница —
    английская. Первая сборка отдала «сталь, четыре, поверхности» на всех 167
    страницах, и это поймал гейт языка, а не глаз.
    """
    out, i = [], 0
    while True:
        j = css.find("/*", i)
        if j < 0:
            out.append(css[i:])
            break
        out.append(css[i:j])
        k = css.find("*/", j + 2)
        if k < 0:
            break
        i = k + 2
    return "".join(out)


CSS = r"""
:root{
  color-scheme:light dark;

  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SFMono-Regular","Cascadia Mono","Segoe UI Mono","DejaVu Sans Mono","Liberation Mono",Menlo,Consolas,monospace;

  /* сталь: четыре поверхности и двое чернил */
  --bg:#d9dce0;
  --panel:#f5f6f7;
  --panel-2:#e7eaec;
  --sunk:#c9cdd1;
  --ink:#0d1114;
  --ink-2:#454d54;

  /* три веса линейки и ни одного четвёртого */
  --line-1:#727a81;
  --line-2:#4e565e;
  --line-3:#0d1114;
  --w1:1px;
  --w2:2px;
  --w3:5px;

  /* ОДИН сигнальный цвет и ОДНА работа: величина вне нормы */
  --signal:#a13600;

  /* Заливка силуэта. Одна на оба чертежа: одиночный и семейный никогда не
     стоят в одной картинке, а два оттенка стали, каждый из которых обязан
     держать 3:1 и к панели, и к обводке, помещались в такое узкое окно
     яркости, что различить их было нельзя всё равно. Роль «этот элемент»
     в семейном чертеже несёт ВЕС ОБВОДКИ, а не оттенок. */
  --metal:#7c848b;

  /* ОДИН шаг ритма. 8, а не 7: при 7 множители .8 и 1.4 давали 5,6 и 9,8 px,
     и рядом с ними лежали набранные руками 2, 3 и 4 px. При 8 целыми
     получаются .25, .5, .75, 1, 1.25, 1.5 и все целые множители. */
  --u:8px;
  --pad:calc(var(--u)*2);

  /* ОДНА шкала кегля. Шесть ступеней, ни одной седьмой, и ни одной ниже
     12 px в тексте страницы. Было четырнадцать разных кеглей, шесть из них
     мельче основного текста, и заголовок раздела (13 px) был МЕЛЬЧЕ текста,
     который открывает (15 px). --t-fig стоит особняком и объявлен отдельно:
     это подпись ВНУТРИ чертежа, где место задано самим предметом. */
  --t-micro:.75rem;
  --t-small:.875rem;
  --t-body:1rem;
  --t-lead:1.125rem;
  --t-big:1.5rem;
  --t-head:clamp(2rem,5vw,3rem);
  --t-fig:10px;

  /* --measure УДАЛЁН 15.09.2026. Проза идёт во всю ширину колонки:
     владелец просил это четырежды, и трижды до того правка делалась
     «по признаку» — чинилось место, на которое показали, а правило
     сужалось до вкуса автора. Переменной больше нет, вернуть сужение
     можно только заведя её заново, а это роняет гейт. */
  --wide:1360px;
  /* Высота закреплённой шапки. Из неё выводятся ДВЕ вещи, которые
     иначе живут независимыми числами и однажды разъедутся: отступ
     цели якоря и прилипание боковой колонки. Ровно этот класс уже
     стоил ферме урока «одна величина — одно отношение». */
  --mast:80px;
}

@media (prefers-color-scheme:dark){
  :root{
    --bg:#0e1114;
    --panel:#171b1f;
    --panel-2:#1f252a;
    --sunk:#262c33;
    --ink:#e8ebed;
    --ink-2:#a7b0b8;
    --line-1:#6c757d;
    --line-2:#828b93;
    --line-3:#e8ebed;
    --signal:#ff8a3d;
    --metal:#6c757c;
  }
}

*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font:400 var(--t-body)/1.55 var(--sans);
  font-variant-numeric:tabular-nums;
  /* Слово, которому негде переноситься, УНОСИТ ВСЮ СТРАНИЦУ вбок: строка
     цитирования держит литерал https://batterycross.com/data/latest.csv,
     это 39 знаков моноширинного кегля .875rem, то есть 328 px в коробке
     304 px, и на 320 px главная ехала вправо на 16 px целиком. Правило
     стоит на body и потому наследуется всем: ловить такие литералы
     поимённо — значит ждать следующего. break-word рвёт слово ТОЛЬКО
     когда иначе оно не влезает, обычный текст не трогает. */
  overflow-wrap:break-word;
}
svg{display:block}
h1,h2,h3,p,ul,ol,table,form,figure{margin:0;padding:0}
ul{list-style:none}
a{color:var(--ink);text-decoration:underline;text-underline-offset:.16em;
  text-decoration-thickness:var(--w1)}
a:hover{text-decoration-thickness:var(--w2)}
:focus-visible{outline:var(--w2) solid var(--ink);
  outline-offset:calc(var(--u)*.25)}
b,strong{font-weight:700}

.bx-skip{position:static;display:block;width:1px;height:1px;overflow:hidden;
  white-space:nowrap;background:var(--panel);color:var(--ink)}
.bx-skip:focus-visible{width:auto;height:auto;padding:var(--u) calc(var(--u)*2)}

/* --------------------------------------------------------------- шапка */
/* Якорь и закреплённая шапка. 52 адреса из 246 в поисковом указателе — это
   ссылки вида /discontinued/#d-xxxx, то есть каждый пятый результат поиска
   высаживает человека в середину таблицы на 133 строки. Без этого правила
   нужная строка уезжает ПОД шапку, и человек не понимает, куда попал. */
:target{scroll-margin-top:calc(var(--mast) + var(--u))}
/* Подсветка цели — ФОНОМ ЯЧЕЕК, а не обводкой строки: outline на
   table-row браузеры рисуют как придётся, и в проверке он не нарисовался
   вовсе. Строка, ради которой человека сюда прислали, обязана быть видна:
   каждый пятый адрес в поисковом указателе — якорь внутрь таблицы на 133
   строки. */
:target>td,:target>th{background:var(--sunk)}
:target:not(tr){outline:var(--w2) solid var(--ink);
  outline-offset:calc(var(--u)*.25)}

.bx-mast{background:var(--panel);border-bottom:var(--w3) solid var(--line-3);
  /* Закреплена: страницы длинные, и вернуться к поиску с середины
     таблицы замен иначе можно только прокруткой вверх. */
  position:sticky;top:0;z-index:20}
.bx-mast-in{max-width:var(--wide);margin:0 auto;padding:calc(var(--u)*2) var(--pad)}
.bx-top{display:flex;flex-wrap:wrap;align-items:baseline;
  gap:var(--u) calc(var(--u)*2);border-bottom:var(--w1) solid var(--line-1);
  padding-bottom:var(--u)}
.bx-brand{font:700 var(--t-lead)/1 var(--mono);letter-spacing:.06em;
  background:var(--ink);color:var(--panel);padding:var(--u) calc(var(--u)*1.5);
  text-decoration:none}
.bx-brand:hover{text-decoration:none}
.bx-strap{font:400 var(--t-micro)/1.3 var(--mono);color:var(--ink-2);
  letter-spacing:.04em;text-transform:uppercase}
/* «Вы здесь» — ВЕСОМ, а не сигнальным цветом. Сигнал означает ровно одно:
   величина вне нормы. Пункт меню, на котором человек стоит, не «вне нормы». */
.bx-here{color:var(--ink);font-weight:700}
.bx-nav{margin-left:auto;display:flex;flex-wrap:wrap;gap:calc(var(--u)*2);
  font:var(--t-micro)/1.3 var(--mono);text-transform:uppercase;
  letter-spacing:.06em}

/* ------------------------------------------------------------- каркас */
.bx-wrap{max-width:var(--wide);margin:0 auto;padding:calc(var(--u)*3) var(--pad)
  calc(var(--u)*7)}
/* align-items:start — чтобы боковая колонка не растягивалась на всю высоту
   разбора: у соседнего сайта фермы ровно эта растяжка дала 1400 px пустого
   поля рядом с текстом. Липкость — не декорация: место 300x600 стоит денег
   ровно столько, сколько его видно, а разбор ниже семи тысяч пикселей. */
.bx-cols{display:grid;grid-template-columns:minmax(0,1fr) 300px;
  gap:calc(var(--u)*4);align-items:start}
.bx-main{min-width:0}
.bx-side{min-width:0;position:sticky;
  /* Было top:16px против шапки в 80px: верхние 24px колонки
     постоянно уезжали ПОД шапку. Сейчас там режется карточка, а с
     подключённой сетью резался бы верх рекламного блока — это уже
     не косметика, а нарушение требований к видимости объявления. */
  top:calc(var(--mast) + var(--u)*2)}
.bx-crumb{font:var(--t-micro)/1.4 var(--mono);color:var(--ink-2);
  text-transform:uppercase;letter-spacing:.06em;margin-bottom:calc(var(--u)*2)}
h1{font:700 var(--t-head)/1.02 var(--mono);letter-spacing:-.01em;
  margin-bottom:var(--u)}
.bx-also{font:var(--t-small)/1.5 var(--mono);color:var(--ink-2);
  margin-bottom:calc(var(--u)*2)}
/* Заголовок раздела КРУПНЕЕ текста, который он открывает. Был 13 px при
   тексте 15 px и читался заголовком только за счёт линейки над ним. */
h2{font:700 var(--t-lead)/1.25 var(--mono);text-transform:uppercase;
  letter-spacing:.06em;color:var(--ink);
  border-top:var(--w3) solid var(--line-3);
  padding-top:var(--u);margin:calc(var(--u)*5) 0 calc(var(--u)*2)}
.bx-main>p{margin-bottom:calc(var(--u)*2)}
.bx-lead{font-size:var(--t-lead);line-height:1.5;
  margin-bottom:calc(var(--u)*3)}
.bx-legend{font:var(--t-small)/1.45 var(--mono);color:var(--ink-2);
  margin-bottom:calc(var(--u)*2)}
.bx-src{font:var(--t-small)/1.45 var(--mono);color:var(--ink-2)}

/* ------------------------------------------------------- полоса величин */
/* Линейки между ячейками — ВЕРХНЯЯ И ЛЕВАЯ у каждой, сдвинутые на свою же
   толщину наружу и срезанные overflow контейнера. Так внутренние рули есть
   все, включая горизонтальные при переносе на две строки, а лишних по краю
   нет ни одного, и :last-child не участвует вовсе: в сетке это последняя
   ячейка ЛЕНТЫ, а не последняя в строке.

   Через зазор сетки на цветном фоне контейнера это же не делается: при
   нечётном числе ячеек хвост последней строки — не ячейка, а голый фон, и
   он вставал сплошным серым прямоугольником рядом с последней величиной.
   Замерено на 375 px, где полоса из пяти величин ложится как 2+2+1. */
.bx-strip{display:grid;
  grid-template-columns:repeat(auto-fit,minmax(calc(var(--u)*18),1fr));
  background:var(--panel);border:var(--w2) solid var(--line-3);
  overflow:hidden;margin-bottom:calc(var(--u)*3)}
.bx-cellv{padding:calc(var(--u)*1.5) calc(var(--u)*2);
  margin:calc(var(--w1)*-1) 0 0 calc(var(--w1)*-1);
  border-top:var(--w1) solid var(--line-1);
  border-left:var(--w1) solid var(--line-1)}
.bx-k{font:var(--t-micro)/1.3 var(--mono);text-transform:uppercase;
  letter-spacing:.09em;color:var(--ink-2);display:block;
  margin-bottom:calc(var(--u)*.25)}
.bx-val{font:700 var(--t-big)/1.1 var(--mono)}
.bx-unit{font:400 var(--t-small)/1 var(--mono);color:var(--ink-2);
  margin-left:calc(var(--u)*.5)}
.bx-state{display:inline-block;font:700 var(--t-micro)/1 var(--mono);
  text-transform:uppercase;letter-spacing:.09em;
  padding:calc(var(--u)*.5) var(--u);border:var(--w2) solid var(--line-3)}
.bx-state-on{background:var(--ink);color:var(--panel)}
.bx-state-off{background:transparent;color:var(--ink);border-style:dashed}

/* --------------------------------------------- стрелочная шкала напряжения */
/* Привито от направления «прибор»: отклонение видно положением штриха
   раньше, чем прочитаны проценты. Дорожка ОГРАНИЧЕНА по ширине: пока она
   тянулась во всю колонку, одно и то же отклонение стояло на разном
   расстоянии от края на разных экранах, а на узком превращалось в серую
   полоску 140x10 px, рядом с которой число читалось первым. */
.bx-scale-v{margin:0 0 calc(var(--u)*3);padding:calc(var(--u)*1.5) calc(var(--u)*2)}
.bx-scale-cap{display:block;font:var(--t-micro)/1.3 var(--mono);
  text-transform:uppercase;letter-spacing:.09em;color:var(--ink-2);
  margin-bottom:calc(var(--u)*.75)}
.bx-scale-track{position:relative;height:calc(var(--u)*3);
  width:min(100%,calc(var(--u)*48));background:var(--sunk);
  border:var(--w1) solid var(--line-2)}
/* Полоса — НЕ данные, а зона класса: до её краёв замена
   ещё работает и только врёт показаниями, за краями это другой класс.
   Края рисуются линией, а не оттенком: заливка на оттенке давала
   1,14:1 в светлой теме, то есть не читалась вовсе. */
.bx-scale-band{position:absolute;top:0;bottom:0;background:var(--panel);
  border-left:var(--w2) solid var(--ink-2);
  border-right:var(--w2) solid var(--ink-2)}
.bx-scale-pin{position:absolute;top:calc(var(--u)*-.5);
  bottom:calc(var(--u)*-.5);width:var(--w2);background:var(--ink)}
.bx-scale-pin-off{background:var(--signal)}
.bx-scale-ends{display:flex;justify-content:space-between;gap:var(--u);
  font:var(--t-micro)/1.4 var(--mono);color:var(--ink-2);
  width:min(100%,calc(var(--u)*48));margin-top:calc(var(--u)*.5)}
/* Мера набора ОДНА на весь сайт. Здесь стояло 62ch: замер правых краёв на
   1440 px дал 532 при общей мере 577, то есть четвёртый край на том же
   экране, поставленный отдельным верным правилом. Мера — что задаёшь, край —
   что видно. */
.bx-scale-note{font:var(--t-small)/1.5 var(--sans);color:var(--ink-2);
  margin:calc(var(--u)*1.5) 0 0;}

/* ------------------------------------------------------------- таблицы */
/* Подсказка о прокрутке — ТЕНЬ У КРАЯ, а не текст: на телефоне таблица
   замен шире колонки, столбцы «Chemistry» и «Capacity» уезжают за край, и
   нативная полоса прокрутки в iOS невидима, пока её не тронут. Две пары
   слоёв: «крышка» цвета панели едет вместе с содержимым (local) и уезжает,
   открывая тень, которая стоит на месте (scroll). */
.bx-tw{overflow-x:auto;border:var(--w2) solid var(--line-3);
  background-color:var(--panel);margin-bottom:calc(var(--u)*3)}
table{border-collapse:collapse;width:100%;font-size:var(--t-small)}
thead th{font:700 var(--t-micro)/1.3 var(--mono);text-transform:uppercase;
  letter-spacing:.09em;color:var(--ink-2);text-align:left;
  padding:var(--u) calc(var(--u)*1.5);
  border-bottom:var(--w2) solid var(--line-2);white-space:nowrap}
tbody th,tbody td{text-align:left;padding:var(--u) calc(var(--u)*1.5);
  border-bottom:var(--w1) solid var(--line-1);vertical-align:top}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
tbody th{font-weight:700;font-family:var(--mono);white-space:nowrap}
.bx-spec th{width:15rem;color:var(--ink-2);font-weight:400;
  text-transform:uppercase;font-size:var(--t-micro);letter-spacing:.09em;
  padding-top:calc(var(--u)*1.25)}
.bx-spec td{font-family:var(--mono)}
.bx-fits td{font-family:var(--mono);white-space:nowrap}
/* Вердикт посадки — ЧЕРНИЛАМИ И ВЕСОМ. Светофор из трёх цветов нёс здесь
   ВТОРОЙ независимый вердикт рядом с первым: зелёный значил «встаёт» в одном
   столбце и «то же напряжение» в соседнем, жёлтый — «сидит ниже» в одном и
   «нужна перекалибровка» в другом. Два смысла на один цвет. Посадка уже
   нарисована силуэтом; здесь она читается словом. */
.bx-fit{font-weight:400;color:var(--ink)}
.bx-fit-drop-in{font-weight:700}
.bx-fit-shorter,.bx-fit-taller{color:var(--ink-2)}
.bx-v{font-family:var(--mono);white-space:nowrap}
.bx-vtag{display:block;font:400 var(--t-micro)/1.3 var(--mono);
  text-transform:uppercase;letter-spacing:.06em;color:var(--ink-2);
  white-space:normal}
.bx-v-same,.bx-v-minor{color:var(--ink)}
.bx-v-calibration{color:var(--ink);font-weight:700}
/* Единственное место в таблице, где работает сигнал: величина ВНЕ НОРМЫ. */
.bx-v-wrong{color:var(--signal);font-weight:700}
.bx-gone td,.bx-gone th{color:var(--ink-2)}

/* ------------------------------------------------------------- чертежи */
.bx-fig{border:var(--w2) solid var(--line-3);background-color:var(--panel);
  padding:calc(var(--u)*2);margin-bottom:calc(var(--u)*3);overflow-x:auto}
.bx-cap{font:var(--t-micro)/1.4 var(--mono);text-transform:uppercase;
  letter-spacing:.09em;color:var(--ink-2);margin-top:var(--u)}
/* ПРАВИЛО, А НЕ УДАЧНАЯ РЕАЛИЗАЦИЯ: чертёж, несущий подписанный масштаб,
   НИКОГДА не ужимается по ширине. Первая версия давала .bx-draw
   max-width:100%, и на 420 px рисунок сжимался, а подпись «14 px per mm»
   оставалась — то есть картинка врала о себе ровно тем способом, каким
   неравные корзины гистограммы, нарисованные равной шириной, выдумали у нас
   заголовочное утверждение на 318 страницах. Не влезает — прокручивается:
   .bx-fig для того и заведён с overflow-x. */
.bx-draw{max-width:none;width:auto;height:auto}
/* Обводка — --line-3, а не отдельный «цвет по металлу». Прежний --on-metal
   был почти-чёрным в обеих темах, а панель под ним темнела: в тёмной теме
   линия чертежа стояла к панели на 1,04:1, то есть чертёж терял ЛИНИЮ —
   ровно то, ради чего чертёж и рисуют. Обе половины пары проверяются теперь
   гейтом: обводка к панели И обводка к заливке. */
.bx-body{fill:var(--metal);stroke:var(--line-3);stroke-width:var(--w1)}
.bx-ref{fill:var(--metal);stroke:var(--line-3);stroke-width:var(--w2)}
.bx-alt{fill:none;stroke:var(--line-2);stroke-width:var(--w1);
  stroke-dasharray:4 2.5}
.bx-crimp{stroke:var(--line-3);stroke-width:var(--w1)}
.bx-dim{stroke:var(--line-2);stroke-width:var(--w1)}
/* Опорная линия — ГРАНИЦА, и рисуется линейкой, как все границы. Сигналом
   она была пятой работой сигнального цвета. */
.bx-ref-line{stroke:var(--line-3);stroke-width:var(--w2);stroke-dasharray:10 4}
.bx-base-line{stroke:var(--line-3);stroke-width:var(--w2)}
.bx-num,.bx-tag,.bx-scale{font-family:var(--mono);fill:var(--ink-2);
  font-size:var(--t-fig)}
.bx-tag{fill:var(--ink)}
.bx-scale{letter-spacing:.08em}

/* --------------------------------------------------------------- списки */
/* ЕДИНСТВЕННАЯ ПЛАШКА ОБ УГРОЗЕ ЖИЗНИ. Отличается ВЕСОМ, а не оттенком:
   самая толстая линейка сайта (--w3) по всем четырём сторонам — больше ни у
   одного блока такой нет, — вторая поверхность под текстом и сигнальное
   слово моноширинным прописным.
     СИГНАЛЬНЫЙ ЦВЕТ СЮДА НЕ ВЗЯТ, и это не забывчивость. У --signal одна
   работа — «эта величина не в норме» на шкале напряжений, — и гейт «один
   сигнал — одна работа» её стережёт. Цвет, значащий две вещи, не значит
   первую. Вдобавок оттенок — единственное, что теряется в печати (блок
   @media print гасит --signal в чёрный), в высокой контрастности и у
   читателя, который цвет не различает; вес не теряется нигде.
     Стояла эта плашка обычным h2 с абзацем — ровно как соседняя рубрика
   «самый глубокий элемент этого диаметра», — и читалась как интересный
   факт. */
/* Готовый сниппет встраивания. Моноширинный, с горизонтальной прокруткой:
   адрес длиннее узкого экрана, а перенос внутри кода делает его не копируемым
   без правки. */
.bx-snip{margin:var(--u) 0 calc(var(--u)*3);padding:var(--u);
  border:var(--w1) solid var(--line-1);background:var(--panel-2);
  overflow-x:auto;font:var(--t-micro)/1.5 var(--mono);white-space:pre}
.bx-warn{border:var(--w3) solid var(--line-3);background:var(--panel-2);
  padding:calc(var(--u)*2);margin:calc(var(--u)*3) 0}
.bx-warn-sig{font:700 var(--t-small)/1.2 var(--mono);text-transform:uppercase;
  letter-spacing:.08em;margin:0 0 var(--u)}
.bx-warn-lead{margin:0}
.bx-warn-list{margin:var(--u) 0 0;padding:0;list-style:none}
.bx-warn-list li{padding:var(--u) 0 0;border-top:var(--w1) solid var(--line-2);
  margin-top:var(--u);font-size:var(--t-small)}
.bx-nb{border:var(--w2) solid var(--line-3);background:var(--panel);
  margin-bottom:calc(var(--u)*3)}
.bx-nb li{padding:var(--u) calc(var(--u)*1.5);
  border-bottom:var(--w1) solid var(--line-1);font-family:var(--mono);
  font-size:var(--t-small)}
.bx-nb li:last-child{border-bottom:0}
.bx-res{margin-top:calc(var(--u)*2)}
.bx-res li{padding:var(--u) 0;border-bottom:var(--w1) solid var(--line-1);
  font:var(--t-lead)/1.4 var(--mono)}
.bx-res li:last-child{border-bottom:0}
.bx-res-what{color:var(--ink-2);font-size:var(--t-small)}
/* Пометка «посчитано нами» — вторыми чернилами, а не сигналом: это
   провенанс, а не тревога. */
.bx-ours{position:relative}
.bx-ours::after{content:" • ours";font:400 var(--t-micro)/1 var(--mono);
  letter-spacing:.06em;color:var(--ink-2);text-transform:uppercase;
  margin-left:calc(var(--u)*.5);white-space:nowrap}
.bx-row{display:grid;
  grid-template-columns:repeat(auto-fit,minmax(calc(var(--u)*11),1fr));
  background:var(--panel);border:var(--w2) solid var(--line-3);
  overflow:hidden}
.bx-row li{text-align:center;padding:calc(var(--u)*1.5) var(--u);
  margin:calc(var(--w1)*-1) 0 0 calc(var(--w1)*-1);
  border-top:var(--w1) solid var(--line-1);
  border-left:var(--w1) solid var(--line-1)}
.bx-row a{font:700 var(--t-lead)/1.2 var(--mono);text-decoration:none;
  border-bottom:var(--w2) solid var(--line-2)}
.bx-row .bx-res-what{display:block;margin-top:calc(var(--u)*.25)}
.bx-two{columns:2;column-gap:calc(var(--u)*4)}
.bx-two li{break-inside:avoid}
@media (max-width:544px){.bx-two{columns:1}}
/* Закреплённая шапка на телефоне обязана быть НИЗКОЙ. .bx-top переносит
   меню на вторую строку (flex-wrap), и на 390 px пять пунктов дают три
   ряда — закреплённая шапка съела бы пятую часть экрана, то есть мешала бы
   ровно тому, ради чего её закрепляли. Меню едет вбок вместо переноса. */
@media (max-width:544px){
  .bx-mast-in{padding:var(--u) var(--pad)}
  .bx-top{flex-wrap:nowrap;overflow-x:auto;padding-bottom:calc(var(--u)*.5)}
  .bx-nav{flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;
    -webkit-overflow-scrolling:touch}
}
/* Поле поиска ОДНО на весь сайт и стоит на каждой странице: главное
   действие справочника было на двух страницах из 164. Компактный вид —
   строкой, на главной он же в рамке и крупным кеглем. */
.bx-find{margin-bottom:calc(var(--u)*3)}
.bx-find-bar{display:flex;gap:var(--u);align-items:center;flex-wrap:wrap}
.bx-find input{font:var(--t-lead)/1.3 var(--mono);
  padding:var(--u) calc(var(--u)*1.5);
  border:var(--w2) solid var(--line-3);background:var(--panel);
  color:var(--ink);width:min(22rem,100%);flex:1 1 12rem}
.bx-find-n{font:var(--t-micro)/1.3 var(--mono);color:var(--ink-2);
  white-space:nowrap}
.bx-hero{border:var(--w3) solid var(--line-3);background:var(--panel);
  padding:calc(var(--u)*3);margin-bottom:calc(var(--u)*3)}
.bx-hero .bx-find-bar{display:block}
.bx-hero input{display:block;width:100%;font:600 var(--t-big)/1.3 var(--mono);
  padding:calc(var(--u)*1.5);margin-top:var(--u);
  border:var(--w2) solid var(--line-3);background:var(--bg);color:var(--ink)}
/* «Ничего не нашлось» — тяжёлая линейка, а не сигнал: пустой ответ поиска
   не является величиной вне нормы. */
.bx-find-none{border-left:var(--w3) solid var(--line-3);
  padding:var(--u) calc(var(--u)*2);background:var(--panel);
  margin-bottom:calc(var(--u)*3);}
.bx-grp{margin-bottom:calc(var(--u)*2)}
.bx-grp h2{margin-top:calc(var(--u)*3)}
.bx-ix{columns:2;column-gap:calc(var(--u)*4);font-family:var(--mono);
  font-size:var(--t-small);margin-bottom:calc(var(--u)*3)}
.bx-ix li{margin-bottom:calc(var(--u)*.25);break-inside:avoid}
.bx-nolink{color:var(--ink-2);font-size:var(--t-micro)}
.bx-gloss{margin-bottom:calc(var(--u)*3)}
.bx-gloss dt{font:700 var(--t-small)/1.4 var(--mono);text-transform:uppercase;
  letter-spacing:.06em;margin-top:calc(var(--u)*2)}
.bx-gloss dd{margin:calc(var(--u)*.25) 0 0}

/* Нумерованные источники. Номер стоит СЛЕВА и моноширинным: ссылка на
   даташит должна читаться как ссылка на документ, а не как строка прозы. */
.bx-refs{margin-bottom:calc(var(--u)*2)}
.bx-refs li{padding:var(--u) 0;border-bottom:var(--w1) solid var(--line-1);
  font-size:var(--t-small)}
.bx-refs li:last-child{border-bottom:0}
.bx-refno{font:700 var(--t-micro)/1 var(--mono);color:var(--ink-2);
  margin-right:calc(var(--u)*1.5)}

/* ---------------------------------------------------- боковая зона */
.bx-card{border:var(--w2) solid var(--line-3);background:var(--panel);
  padding:calc(var(--u)*2);margin-bottom:calc(var(--u)*3)}
.bx-card h3{font:700 var(--t-micro)/1.3 var(--mono);text-transform:uppercase;
  letter-spacing:.09em;color:var(--ink-2);margin-bottom:var(--u)}
/* Легенда условных знаков стоит ВНУТРИ чертежа, который она объясняет.
   В боковой колонке она была на 96-м пикселе сверху на широком экране —
   то есть перед тем, что объясняет, — и на 4491-м из 5210 на телефоне,
   то есть после ВСЕХ чертежей, которые объясняет. */
.bx-key{display:grid;grid-template-columns:calc(var(--u)*4) 1fr;
  gap:var(--u);align-items:center;font:var(--t-small)/1.35 var(--mono);
  margin-top:var(--u)}
.bx-swatch{height:calc(var(--u)*2);border:var(--w2) solid var(--line-3)}
.bx-swatch-solid{background:var(--metal)}
.bx-swatch-dashed{background:transparent;border-color:var(--line-2);
  border-style:dashed}

/* --------------------------------------------------------------- подвал */
.bx-foot{border-top:var(--w3) solid var(--line-3);background:var(--panel);
  margin-top:calc(var(--u)*8)}
.bx-foot-in{max-width:var(--wide);margin:0 auto;
  padding:calc(var(--u)*3) var(--pad);font-size:var(--t-small);
  color:var(--ink-2)}
.bx-foot p{max-width:56rem;margin-bottom:var(--u)}
.bx-foot nav{display:flex;flex-wrap:wrap;gap:calc(var(--u)*2);
  font-family:var(--mono);text-transform:uppercase;letter-spacing:.06em;
  font-size:var(--t-micro);margin:calc(var(--u)*2) 0}

/* --------------------------------------------------------------- узкий */
@media (max-width:1008px){
  .bx-cols{grid-template-columns:minmax(0,1fr)}
  .bx-side{display:contents}
}
@media (max-width:544px){
  .bx-wrap{padding:calc(var(--u)*2) var(--u) calc(var(--u)*5)}
  .bx-ix{columns:1}
  .bx-spec th{width:auto}
}

/* ---------------------------------------------------------------- печать
   Это справочник, который несут к прилавку. На бумаге обе прокручиваемые
   коробки — таблица и чертёж — обрезаются в каждом крупном браузере: правые
   столбцы и большая часть семейного чертежа просто не печатаются. Поэтому
   overflow снимается, ширина отпускается, а адрес ссылки печатается за ней:
   на бумаге синее слово не ведёт никуда. */
@media print{
  :root{--ink:#000;--ink-2:#333;--panel:#fff;--bg:#fff;--panel-2:#fff;
    --sunk:#fff;--line-1:#bbb;--line-2:#888;--line-3:#000;--signal:#000;
    --metal:#ccc}
  body{background:var(--bg);color:var(--ink)}
  .bx-mast,.bx-foot nav,.bx-skip,.bx-side,.bx-find,.bx-res,
  .bx-ad,.bx-ad-flow,.bx-ad-tower{display:none !important}
  .bx-wrap{max-width:none;padding:0}
  .bx-cols{display:block}
  .bx-tw,.bx-fig{overflow:visible !important;width:auto !important;
    max-width:none;border-width:1px;background-image:none}
  table{page-break-inside:auto}
  tr,li,dt,dd{page-break-inside:avoid}
  h1,h2,h3{page-break-after:avoid}
  .bx-fits td{white-space:normal}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:var(--t-micro);
    word-break:break-all}
  .bx-refs a::after{content:" (" attr(href) ")";font-size:var(--t-micro);
    word-break:break-all}
}
"""


# --------------------------------------------------------- РАСКЛАДКА В ЧИСЛАХ

def _one(css, pattern, what):
    """Одно число, ПРОЧИТАННОЕ из CSS. Нет — исключение, а не молчание."""
    m = re.search(pattern, css)
    if not m:
        raise ValueError("в CSS не найдено число: %s" % what)
    return int(m.group(1))


def layout(css=None):
    """Числа раскладки, ВЫНУТЫЕ ИЗ CSS, а не набранные рядом с ним второй раз.

    Реклама перекрывала башню на 47 пикселей в полосе 1009-1083 px: в CSS
    стояло 728 px, в объявлении стояло 728 px, гейт сверял 728 с 728 и был
    прав. КОНТЕЙНЕР не мерил никто. Ширина контейнера считается здесь и
    только здесь, из тех же строк, которые эту ширину и задают.

    Поля страницы читаются МНОЖИТЕЛЕМ шага, а не вторым числом: пока рядом
    стояло «--pad:14px», это было ещё одно место, где ритм можно было
    рассогласовать молча.
    """
    css = CSS if css is None else css
    u = _one(css, r"--u:(\d+)px", "шаг ритма --u")
    return {
        "u": u,
        "pad": u * _one(css, r"--pad:calc\(var\(--u\)\*(\d+)\)", "--pad"),
        "pad_narrow": u,     # в узком media-блоке поля равны шагу ритма
        "wide": _one(css, r"--wide:(\d+)px", "--wide"),
        "side": _one(css, r"\.bx-cols\{[^}]*?grid-template-columns:"
                          r"minmax\(0,1fr\) (\d+)px", "ширина боковой колонки"),
        "gap": u * _one(css, r"\.bx-cols\{[^}]*?gap:calc\(var\(--u\)\*(\d+)\)",
                        "зазор между колонками"),
        "cols_at": _one(css, r"@media \(max-width:(\d+)px\)\{\s*"
                             r"\.bx-cols\{grid-template-columns:minmax\(0,1fr\)\}",
                        "перелом на одну колонку"),
        "narrow_at": _one(css, r"@media \(max-width:(\d+)px\)\{\s*"
                               r"\.bx-wrap\{padding:", "перелом узких полей"),
    }


MIN_VIEW, MAX_VIEW = 320, 1600

# ПОЛОСА ПРОКРУТКИ ЗАНИМАЕТ МЕСТО, А МЕДИАЗАПРОС ЕЁ НЕ ВИДИТ. Медиазапрос
# срабатывает по innerWidth, раскладка меряется по clientWidth, и между ними
# ровно ширина классической полосы прокрутки. Замер в браузере: при
# innerWidth 1092 запрос (min-width:1092px) истинен и рисуется 728x90, а
# основная колонка при clientWidth 1077 всего 713 px — объявление вылезает из
# своей колонки на 15 px, и полосы прокрутки при этом НЕ появляется, то есть
# на экране ничего не выглядит сломанным. Это тот же дефект, ради которого
# переломы переведены из rem в пиксели, просто на 15 пикселей тише.
#
# 17 px — самая широкая классическая полоса из тех, что нам надо пережить.
# Резервируется НА ВСЕХ ширинах: на телефоне полоса накладная и ничего не
# занимает, но окно браузера шириной 360 px на рабочем столе существует, и
# правило, верное иногда, — это не правило.
SCROLLBAR = 17


def main_px(view, L=None):
    """Ширина основной колонки при ширине экрана view. Чистая функция.

    view — ширина, по которой срабатывают МЕДИАЗАПРОСЫ (innerWidth).
    Раскладка при этом меряется по ширине документа, то есть на полосу
    прокрутки меньше.
    """
    L = layout() if L is None else L
    pad = L["pad_narrow"] if view <= L["narrow_at"] else L["pad"]
    content = min(view - SCROLLBAR, L["wide"]) - 2 * pad
    if view <= L["cols_at"]:
        return content
    return content - L["side"] - L["gap"]


def holder_px(cls, view, L=None):
    """Ширина того, ВНУТРИ ЧЕГО стоит место этого класса."""
    L = layout() if L is None else L
    if cls == "bx-ad-tower" and view > L["cols_at"]:
        # Башня стоит в боковой колонке ровно её ширины.
        return L["side"]
    # Ниже перелома .bx-side{display:contents} и башня становится обычной
    # строкой одноколоночной сетки, то есть шириной с основную колонку.
    return main_px(view, L)


# Рекламные места: класс -> какие форматы предлагаются В КАЖДОЙ РАСКЛАДКЕ,
# от крупного к мелкому. Раскладок две, и это не одно и то же место в разной
# ширине: в две колонки поток идёт растяжкой над разбором, в одну колонку
# читатель на телефоне или в узком окне, и прямоугольник в потоке текста
# стоит дороже растяжки во всю меру набора. ОДНО объявление на весь сайт;
# CSS написан отдельно ЛИТЕРАЛОМ, и гейт сверяет две стороны — что рисует CSS
# на каждой ширине и что позволяет геометрия колонки.
AD_SLOTS = {
    "bx-ad-flow": {"cols": [(970, 250), (728, 90), (336, 280),
                            (300, 250), (250, 250)],
                   "one": [(336, 280), (300, 250), (250, 250)]},
    "bx-ad-tower": {"cols": [(300, 600)],
                    "one": [(300, 250), (250, 250)]},
}


def slot_for(cls, view, L=None):
    """Какой формат ДОЛЖЕН стоять при этой ширине экрана: самый крупный из
    предложенных этой раскладке, который целиком помещается в контейнер."""
    L = layout() if L is None else L
    room = holder_px(cls, view, L)
    mode = "one" if view <= L["cols_at"] else "cols"
    for w, h in AD_SLOTS[cls][mode]:
        if w <= room:
            return (w, h)
    return None


# Место существует, ТОЛЬКО когда в нём что-то есть: display:none не выводит
# узел из :last-child, и пятьсот сорок невидимых мест однажды сломали у нас
# пять правил отступов на ста пятидесяти семи страницах.
# Размер места ЗАДАН ТОЧНО, а не «не меньше», и на узком экране МЕНЯЕТСЯ
# ФОРМАТ, а не сплющивается прежний: объявленный 728x90, отрисованный как
# 366x90, оплачивается как ничто. Переломы здесь — ЛИТЕРАЛ, и в этом смысл:
# гейт сверяет их с геометрией колонки, а не с ними же. Числа сдвинулись при
# переходе на шаг 8 px (поля 16 вместо 14, зазор 32 вместо 28) — и сдвинул их
# не глаз, а тот же гейт, покрасневший на 1084 и 1326.
AD_CSS = r"""

/* Место БЕЗ пунктирной рамки и без серой заливки: пока сеть не подключена,
   в нём стоит наша врезка, и выглядеть она обязана как содержимое сайта, а
   не как дыра, которую забыли закрыть. Пунктир и слово ADVERTISEMENT над
   пустотой — это 312 объявлений о том, что сайт недоделан. */
/* МЕСТО — это только габарит; рамку и фон несёт то, что внутри. Иначе
   врезка в 76 точек висит посреди пустой рамки 300x600, и получается та же
   пустая коробка, из-за которой всё и затевалось, только без подписи.
   Так же сделано у обоих соседних сайтов: место растягивает содержимое. */
.bx-ad{display:flex;align-items:stretch;margin:calc(var(--u)*5) auto;
  overflow:hidden;font:var(--t-micro)/1.4 var(--mono);color:var(--ink-2);
  text-align:left}
.bx-ad-cap{font-weight:700;color:var(--ink-2);letter-spacing:.12em;
  text-transform:uppercase}
.bx-house{display:flex;flex-direction:column;justify-content:center;
  gap:calc(var(--u)*.75);width:100%;padding:calc(var(--u)*2);
  border:var(--w2) solid var(--line-1);background:var(--panel);
  text-decoration:none;color:inherit}
.bx-house:hover .bx-house-h{text-decoration:underline}
.bx-house-h{font:700 var(--t-small)/1.25 var(--sans);color:var(--ink);
  text-transform:none;letter-spacing:0}
.bx-house-s{font-size:var(--t-micro);letter-spacing:.02em;
  text-transform:none;line-height:1.4}
.bx-ad-flow{width:336px;height:280px}
.bx-ad-tower{width:300px;height:600px}
@media (max-width:368px){.bx-ad-flow{width:300px;height:250px}}
@media (max-width:332px){.bx-ad-flow{width:250px;height:250px}}
@media (max-width:1008px){.bx-ad-tower{width:300px;height:250px}}
@media (max-width:332px){.bx-ad-tower{width:250px;height:250px}}
@media (min-width:1109px){.bx-ad-flow{width:728px;height:90px}}
@media (min-width:1351px){.bx-ad-flow{width:970px;height:250px}}

"""
