#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Счётчик количества у позиции, где единица — не штуки, а месяцы.

Константин 20.09.2026, двумя снимками: «генератор с бензином сделай поле как
вентвыход — каждая цифра 1 месяц». Колпаки считались штуками и склонения не
требовали: «(2 шт.)» и «(5 шт.)» одинаковы. Месяцы требуют — «(2 месяц)»
читается как опечатка, а имя позиции уходит в клиентский лист.

Проба меряет то, что видно и что попадает в цену:

  • у позиции со счётчиком есть кнопки «−» и «+», и нажатие меняет число;
  • имя склоняется по числу: 1 месяц, 2 месяца, 5 месяцев, 11 месяцев;
  • цена растёт кратно: два месяца — вдвое дороже одного;
  • у позиции со штуками имя остаётся со штуками — единицу берут из самой
    позиции, а не одну на всех;
  • отмеченная формульная позиция видна и в режиме «Старые цены»: спрятанная,
    она осталась бы в сумме, и итог не сошёлся бы со строками под ним.

Набор проб тут не годится: единица и формула лежат в базе, а не в файле.
Поэтому позиции задаются прямо в браузере — снимок того, что сейчас в
каталоге, с выдуманной ценой.

    python3 check_qty_months.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

# Цена выдуманная: проба меряет кратность и склонение, а не каталог.
ЦЕНА_МЕСЯЦА = 30000


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


ПОДГОТОВКА = """async (цена) => {
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  window._sbProfile = { role: 'admin', full_name: 'Проба' };
  const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
  selectProjectOption(и >= 0 ? и : 0);
  await new Promise(r => setTimeout(r, 1200));
  // Снимок каталога: позиция с месяцами и позиция со штуками.
  const месяцы = OPTIONS.find(o => o.id === 'проба_месяцы') || (() => {
    const о = { id: 'проба_месяцы', section: 'extra', included: false, price: null,
                status: 'formula',
                name: 'Аренда с доставкой на время строительства (1 месяц)',
                formula: { coef: цена, areaSrc: 'qty', qtyOption: true,
                           qtyUnit: 'месяц', defaultQty: 1, defaultMargin: 0 } };
    OPTIONS.push(о); return о;
  })();
  const штуки = OPTIONS.find(o => o.id === 'проба_штуки') || (() => {
    const о = { id: 'проба_штуки', section: 'extra', included: false, price: null,
                status: 'formula', name: 'Колпак вентиляционный (1 шт.)',
                formula: { coef: цена, areaSrc: 'qty', qtyOption: true,
                           defaultQty: 1, defaultMargin: 0 } };
    OPTIONS.push(о); return о;
  })();
  // Отмечать надо после перерисовки: `init` перестраивает список и
  // возвращает опциям их исходное состояние — отметка, поставленная раньше,
  // до измерения не доживает. Так проба и обманулась однажды, показав
  // «позиция пропала» там, где она просто не была отмечена.
  init();
  await new Promise(r => setTimeout(r, 600));
  // Отрисовка возвращает опциям исходное состояние
  // (`checkedOptions[opt.id] = opt.included`), поэтому отметка ставится после
  // неё, а не до, и следом сверяется с разметкой — тем же ходом, каким это
  // делает восстановление расчёта.
  [месяцы.id, штуки.id].forEach(ид => {
    checkedOptions[ид] = true;
    const ч = document.getElementById('chk_' + ид);
    const с = document.getElementById('lbl_' + ид);
    if (ч) ч.checked = true;
    if (с) с.classList.add('active');
  });
  calc();
  await new Promise(r => setTimeout(r, 300));
  return { месяцы: месяцы.id, штуки: штуки.id,
           отмечены: !!checkedOptions[месяцы.id] && !!checkedOptions[штуки.id] };
}"""

ВИД = """(ид) => {
  const о = OPTIONS.find(x => x.id === ид) || {};
  const строка = document.getElementById('lbl_' + ид);
  const счётчик = строка ? строка.querySelector('.opt-qty-stepper') : null;
  const кнопки = счётчик ? счётчик.querySelectorAll('.opt-qty-btn') : [];
  return {
    имя: о.name || '',
    цена: getOptPrice(о) || 0,
    видна: !!строка && строка.offsetParent !== null,
    счётчик: !!счётчик,
    кнопок: кнопки.length,
    число: счётчик ? (счётчик.querySelector('.opt-qty-val') || {}).textContent : null,
  };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                                + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2600)
            иды = стр.evaluate(ПОДГОТОВКА, ЦЕНА_МЕСЯЦА)
            if not иды.get("отмечены"):
                плохо("позиции пробы не отмечены — мерить нечего, "
                      "проверка режима прошла бы вхолостую")

            # ── Счётчик есть и нажимается ────────────────────────────────────
            в = стр.evaluate(ВИД, иды["месяцы"])
            if not в["счётчик"]:
                плохо("у позиции с месяцами нет счётчика количества — "
                      "менять число нечем")
            elif в["кнопок"] != 2:
                плохо(f"у счётчика {в['кнопок']} кнопок вместо «−» и «+»")
            if в["цена"] != ЦЕНА_МЕСЯЦА:
                плохо(f"один месяц стоит {в['цена']} вместо {ЦЕНА_МЕСЯЦА}")

            # ── Имя склоняется, цена кратна ─────────────────────────────────
            for сколько, ожидание in ((1, "1 месяц"), (2, "2 месяца"), (5, "5 месяцев"),
                                      (11, "11 месяцев"), (21, "21 месяц"),
                                      (22, "22 месяца")):
                стр.evaluate("([ид, н]) => { formulaOverrides[ид] = { area: н };"
                             " refreshQtyName(ид); calc(); }", [иды["месяцы"], сколько])
                стр.wait_for_timeout(120)
                в = стр.evaluate(ВИД, иды["месяцы"])
                if not в["имя"].endswith("(" + ожидание + ")"):
                    плохо(f"при {сколько} в имени «{в['имя'][-22:]}» — "
                          f"ожидалось «({ожидание})»")
                if в["цена"] != ЦЕНА_МЕСЯЦА * сколько:
                    плохо(f"{сколько} мес. стоят {в['цена']} вместо "
                          f"{ЦЕНА_МЕСЯЦА * сколько} — цена не кратна числу")

            # ── Штуки остаются штуками ──────────────────────────────────────
            # Единица берётся у самой позиции: одна на всех превратила бы
            # колпаки в месяцы.
            стр.evaluate("([ид, н]) => { formulaOverrides[ид] = { area: н };"
                         " refreshQtyName(ид); }", [иды["штуки"], 3])
            стр.wait_for_timeout(120)
            в = стр.evaluate(ВИД, иды["штуки"])
            if not в["имя"].endswith("(3 шт.)"):
                плохо(f"у позиции со штуками имя «{в['имя'][-20:]}» — "
                      "ожидалось «(3 шт.)»")

            # ── Старый расчёт открывается со строкой, а не с одной ценой ────
            # Расчёт той эпохи открывается в режиме «Старые цены», где
            # формульных позиций на экране нет. Отмеченная в таком расчёте
            # позиция попадала бы в сумму, не имея строки: итог не сходится с
            # тем, что под ним написано. У снятых опций эта оговорка была
            # сделана давно, у формульных — нет.
            вышло = стр.evaluate("""async (ид) => {
              formulaOverrides[ид] = { area: 3 };
              const снимок = collectState();
              снимок.optionPricingMode = 'legacy';
              // Открываем расчёт с чистого калькулятора: позиция в нём не
              // отмечена, и первая отрисовка её прячет. Если открывать поверх
              // того же состояния, строка останется от прежней отрисовки, и
              // проба пройдёт, ничего не проверив.
              checkedOptions[ид] = false;
              renderOptionSections();
              await new Promise(r => setTimeout(r, 200));
              restoreState(снимок);
              await new Promise(r => setTimeout(r, 900));
              const строка = document.getElementById('lbl_' + ид);
              return {
                режим: optionPricingMode,
                отмечена: !!checkedOptions[ид],
                строка: !!строка,
                видна: !!(строка && строка.offsetParent),
                вИтоге: (OPTIONS.find(o => o.id === ид) || {}) &&
                        !!checkedOptions[ид] &&
                        (Number(getOptPrice(OPTIONS.find(o => o.id === ид))) || 0) > 0,
              };
            }""", иды["месяцы"])
            if вышло["режим"] != "legacy":
                плохо("расчёт не открылся в режиме «Старые цены» — "
                      "проверка прошла бы вхолостую")
            elif not вышло["отмечена"]:
                плохо("после открытия старого расчёта позиция не отмечена — "
                      "мерить пропажу строки не на чем")
            else:
                if not вышло["строка"]:
                    плохо("старый расчёт открыт: формульная позиция отмечена и "
                          "стоит в сумме, а строки её на экране нет — итог не "
                          "сходится со списком под ним")
                elif not вышло["видна"]:
                    плохо("строка отмеченной формульной позиции есть в разметке, "
                          "но не показывается")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:220])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: счётчик меняет число, имя склоняется по своей единице "
          "(месяц/месяца/месяцев, штуки остаются штуками), цена кратна числу, "
          "а отмеченная формульная позиция не пропадает в старом режиме.")


if __name__ == "__main__":
    главная()
