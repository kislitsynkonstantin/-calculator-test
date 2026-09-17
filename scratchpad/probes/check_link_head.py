#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба строки «Ссылка клиенту» в панели печати и окна уведомлений.

Держит то, что задано 16.09.2026:
  • «Скопировать ссылку» и «Обновить» стоят в строке заголовка полосы;
  • напоминание «расчёт изменился» появляется, когда снимок разошёлся с тем,
    что лежит по ссылке, и молчит, когда они совпадают, — в том числе когда
    ключи переставлены: снимок возвращается из базы полем jsonb, а оно
    переупорядочивает их, и наивное сравнение ругалось бы всегда;
  • строка заголовка разворачивается только птичкой — промах по кнопке
    копирования блок не открывает;
  • «Печать / PDF» стоит в левой группе верхней строки и ни при какой
    ширине не остаётся одна во втором ряду;
  • подпись о заходах написана без слова «клиент»;
  • в окне уведомлений нет подписи «позже здесь появятся…», и каждое
    открытие ссылки — своя строка.

И то, что задано раньше и легко теряется при перестановке:
  • поле нажатия 44 px при маленькой коробке;
  • зазор до линейки и до соседей — ни склейки, ни повисания в пустоте;
  • никакого горизонтального переполнения.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent.parent
def хром():
    """Путь к браузеру. Номер сборки в нём меняется при обновлении образа,
    поэтому вписанный в пробу он однажды перестал бы совпадать. Значение
    кладёт хук запуска сессии; нет его — находим сами."""
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


ХРОМ = хром()
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")


def стили_печатного_листа():
    """Таблица стилей печатного документа лежит внутри index.html отдельным
    куском — тем, что уходит в собранный лист. На самой странице она не
    действует, поэтому для проверки её правил кусок достаётся текстом."""
    исходник = (КОРЕНЬ / "index.html").read_text(encoding="utf-8")
    метка = исходник.index(".bl-doc{--s:#fff")
    начало = исходник.rindex("<style>", 0, метка) + len("<style>")
    конец = исходник.index("</style>", начало)
    return исходник[начало:конец]


СТИЛИ_ЛИСТА = None

ОКНА = [("телефон", 390, 844), ("телефон лёжа", 844, 390),
        ("планшет", 768, 1024), ("стол", 1440, 900)]

НАХОДКИ = []


def плохо(окно, текст):
    НАХОДКИ.append(f"[{окно}] {текст}")


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ПОДГОТОВКА = """() => {
  _sbUser = { id: 'u-проба' };
  _ссылкаКлиента = {
    code: 'adkv8q5j', revoked: false,
    created_at: '2026-09-10T09:00:00Z', snapshot_at: '2026-09-16T10:00:00Z',
    snapshot: {},
  };
  _заходыКлиента = [
    { seen_at: '2026-09-16T14:22:00Z', version_at: '2026-09-16T10:00:00Z' },
    { seen_at: '2026-09-15T18:03:00Z', version_at: '2026-09-16T10:00:00Z' },
    { seen_at: '2026-09-15T11:40:00Z', version_at: '2026-09-12T08:00:00Z' },
  ];
  // Каталог цен живёт в базе, до неё пробе не дойти — экран ошибки поверх
  // страницы перехватывал бы нажатия.
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  document.getElementById('printOverlay').style.display = 'block';
  переключитьПолосуСсылки(false);
  нарисоватьПолосуСсылки();
}"""

КОЛОКОЛЬЧИК = """async () => {
  await собратьУведомления();
  поставитьОкноУведомлений();
  document.getElementById('bellMenu').style.display = 'block';
  нарисоватьУведомления();
}"""

МЕРА = """() => {
  const кор = э => { const r = э.getBoundingClientRect();
    return { л: r.left, п: r.right, в: r.top, н: r.bottom, ш: r.width, вы: r.height }; };
  const полоса = document.getElementById('clientLinkBar');
  const голова = полоса.querySelector('.cl-head');
  const копия  = полоса.querySelector('.cl-copy');
  const птичка = полоса.querySelector('.cl-arrow');
  const поле = э => {
    const с = getComputedStyle(э, '::before');
    const чис = з => parseFloat(з) || 0;
    const r = э.getBoundingClientRect();
    if (с.content === 'none') return { ш: r.width, вы: r.height };
    return { ш: r.width - чис(с.left) - чис(с.right), вы: r.height - чис(с.top) - чис(с.bottom) };
  };
  const панель = document.getElementById('printToolbar');
  const верх = панель.firstElementChild;
  const печать = document.getElementById('printDocBtn');
  const строки = {};
  [...верх.children].filter(э => э.getClientRects().length).forEach(э => {
    const r = э.getBoundingClientRect();
    const к = Math.round(r.top / 4) * 4;
    (строки[к] = строки[к] || []).push(э.id || э.className || э.tagName);
  });
  const пр = печать.getBoundingClientRect();
  const мойРяд = Object.entries(строки)
    .find(([к]) => Math.abs(+к - Math.round(пр.top / 4) * 4) < 1);
  // Промежутки внутри каждого ряда верхней строки. Ровный ряд — это когда они
  // все одинаковые; дыра посреди ряда видна именно здесь, а не в переполнении
  // и не в расстоянии до ближайшего соседа (у соседа-то зазор нормальный).
  const ряды = {};
  [...верх.children].filter(э => э.getClientRects().length).forEach(э => {
    const r = э.getBoundingClientRect();
    if (getComputedStyle(э).position === 'absolute') return;   // крестик вне потока
    const к = Math.round(r.top / 4) * 4;
    (ряды[к] = ряды[к] || []).push({ кто: э.id || э.className || э.tagName, л: r.left, п: r.right });
  });
  // Ряд из одной кнопки — находка только тогда, когда она поместилась бы
  // строкой выше. Если не поместилась, это честный перенос, а не «болтается».
  const доступно = верх.clientWidth - parseFloat(getComputedStyle(верх).paddingRight);
  const зазорРяда = parseFloat(getComputedStyle(верх).columnGap) || 0;
  const порядок = Object.keys(ряды).map(Number).sort((a, b) => a - b);
  const одиночки = [];
  порядок.forEach((к, и) => {
    const ряд = ряды[к];
    if (ряд.length !== 1 || и === 0) return;
    const выше = ряды[порядок[и - 1]];
    const занято = выше.reduce((с, э) => с + (э.п - э.л), 0) + (выше.length - 1) * зазорРяда;
    const свободно = доступно - занято;
    const нужно = ряд[0].п - ряд[0].л + зазорРяда;
    одиночки.push({ кто: ряд[0].кто, свободно, нужно });
  });
  const промежутки = Object.values(ряды).map(ряд => {
    ряд.sort((a, b) => a.л - b.л);
    const щели = [];
    for (let и = 1; и < ряд.length; и++) щели.push({ между: ряд[и - 1].кто + '↔' + ряд[и].кто,
                                                     сколько: ряд[и].л - ряд[и - 1].п });
    return щели;
  }).filter(щ => щ.length);
  return {
    естьСтараяКнопка: !!document.getElementById('clientLinkBtn'),
    естьПодписьНизаУведомлений: !!document.querySelector('#bellMenu .nt-f'),
    подпись: полоса.querySelector('.cl-sub').textContent,
    заголовок: полоса.querySelector('.cl-t').textContent.trim(),
    текстКопии: копия ? копия.textContent.trim() : null,
    голова: кор(голова), копия: кор(копия), птичка: кор(птичка),
    полеКопии: поле(копия), полеПтички: поле(птичка),
    рульГоловы: голова.getBoundingClientRect().bottom,
    панельШ: панель.getBoundingClientRect().width,
    печатьРяд: мойРяд ? мойРяд[1] : [],
    печатьКор: кор(печать),
    промежутки, одиночки,
    строкиВерха: Object.keys(строки).length,
    переполнение: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    ошибкиРазметки: [...полоса.querySelectorAll('.cl-head > *')].map(э => ({
      кто: э.className || э.tagName, авто: getComputedStyle(э).marginLeft === 'auto',
    })),
    соседи: (() => {
      const дети = [...голова.children].filter(э => э.getClientRects().length);
      const к = голова.getBoundingClientRect();
      return дети.map(э => {
        const r = э.getBoundingClientRect();
        const свои = дети.filter(д => д !== э && Math.abs(д.getBoundingClientRect().top - r.top) < 6);
        const слева = свои.filter(д => д.getBoundingClientRect().right <= r.left + 1)
          .map(д => r.left - д.getBoundingClientRect().right);
        const справа = свои.filter(д => д.getBoundingClientRect().left >= r.right - 1)
          .map(д => д.getBoundingClientRect().left - r.right);
        const все = [...слева, ...справа, r.left - к.left, к.right - r.right];
        return { кто: э.className || э.tagName, ближайший: Math.min(...все) };
      });
    })(),
  };
}"""


def проверить(страница, окно, ш, в):
    страница.set_viewport_size({"width": ш, "height": в})
    страница.evaluate(ПОДГОТОВКА)
    страница.wait_for_timeout(500)
    д = страница.evaluate(МЕРА)

    if д["естьСтараяКнопка"]:
        плохо(окно, "прежняя кнопка «Ссылка клиенту» осталась на панели")
    if д["заголовок"] != "Ссылка":
        плохо(окно, f"заголовок полоски — {д['заголовок']!r}, а должен быть «Ссылка»")
    if д["текстКопии"] != "Скопировать ссылку":
        плохо(окно, f"кнопка в строке заголовка названа {д['текстКопии']!r}, а не «Скопировать ссылку»")
    if "клиент" in д["подпись"].lower():
        плохо(окно, f"в подписи о заходах осталось слово «клиент»: {д['подпись']!r}")
    if "открыли" not in д["подпись"]:
        плохо(окно, f"подпись о заходах не говорит, что ссылку открывали: {д['подпись']!r}")
    if "3 раза" not in д["подпись"]:
        плохо(окно, f"подпись не показывает общее число заходов: {д['подпись']!r}")

    # Поле нажатия — 44 px, коробка при этом лёгкая.
    if д["полеКопии"]["вы"] < 43.5:
        плохо(окно, f"поле нажатия «Скопировать ссылку» {д['полеКопии']['вы']:.0f} px по высоте, нужно 44")
    if д["копия"]["вы"] > 34:
        плохо(окно, f"кнопка копирования нарисована {д['копия']['вы']:.0f} px — вес оплачен размером")
    if д["полеПтички"]["вы"] < 43.5 or д["полеПтички"]["ш"] < 43.5:
        плохо(окно, f"поле нажатия птички {д['полеПтички']['ш']:.0f}×{д['полеПтички']['вы']:.0f}, нужно 44×44")

    # Зазор до линейки под строкой заголовка.
    зазор = д["рульГоловы"] - д["копия"]["н"]
    if зазор < 6:
        плохо(окно, f"кнопка копирования в {зазор:.0f} px от линейки под заголовком — склеилась с ней")

    # «Элемент стоит рядом с чем-то»: ни один в строке не повисает в пустоте.
    for э in д["соседи"]:
        if э["ближайший"] > 26:
            плохо(окно, f"{э['кто']} в строке заголовка стоит в {э['ближайший']:.0f} px от всего — повис в пустоте")

    # Два margin-left:auto в одной строке — тот самый код-признак.
    авто = [э["кто"] for э in д["ошибкиРазметки"] if э["авто"]]
    if len(авто) > 1:
        плохо(окно, f"в строке заголовка два margin-left:auto: {авто}")

    # Ряд ровный: промежутки между кнопками одинаковые.
    for щели in д["промежутки"]:
        размеры = [щ["сколько"] for щ in щели]
        самая = max(щели, key=lambda щ: щ["сколько"])
        if самая["сколько"] > 30 and самая["сколько"] > min(размеры) * 2.5:
            плохо(окно, f"дыра в ряду кнопок: {самая['сколько']:.0f} px между "
                        f"{самая['между']} при обычных {min(размеры):.0f} px — ряд кривой")

    # ── напоминание «расчёт изменился» ──────────────────────────────────
    ДАНО = {"проект": "Баня 6×4", "итог": 100, "разделы": [{"имя": "Каркас", "сумма": 7}]}
    ПЕРЕСТАВЛЕНО = {"разделы": [{"сумма": 7, "имя": "Каркас"}], "итог": 100, "проект": "Баня 6×4"}
    ИНОЕ = {"проект": "Баня 6×4", "итог": 111, "разделы": [{"имя": "Каркас", "сумма": 7}]}

    def напоминание(снимок, лежит):
        return страница.evaluate("""([снимок, лежит]) => {
          window._снимокКлиента = снимок;
          _ссылкаКлиента.snapshot = лежит;
          нарисоватьПолосуСсылки();
          const полоса = document.getElementById('clientLinkBar');
          return {
            подпись: полоса.querySelector('.cl-sub').textContent,
            зовёт: !!полоса.querySelector('.cl-upd.звать'),
            есть: !!полоса.querySelector('.cl-upd'),
          };
        }""", [снимок, лежит])

    совпало = напоминание(ДАНО, ДАНО)
    if not совпало["есть"]:
        плохо(окно, "«Обновить» пропала из строки заголовка")
    if совпало["зовёт"] or "расчёт изменился" in совпало["подпись"]:
        плохо(окно, "напоминание стоит там, где расчёт не менялся")

    переставлено = напоминание(ПЕРЕСТАВЛЕНО, ДАНО)
    if переставлено["зовёт"] or "расчёт изменился" in переставлено["подпись"]:
        плохо(окно, "напоминание сработало на переставленных ключах — снимок из базы "
                    "приходит именно таким, и оно горело бы всегда")

    иное = напоминание(ИНОЕ, ДАНО)
    if not иное["зовёт"]:
        плохо(окно, "расчёт изменился, а «Обновить» не зовёт")
    if "расчёт изменился" not in иное["подпись"]:
        плохо(окно, f"в подписи нет напоминания: {иное['подпись'][:80]!r}")

    # Кнопки строки заголовка — ростом в одно, и меряется это в зовущем
    # состоянии: залитая кнопка кажется крупнее незалитой при равной высоте,
    # и разницу глаз замечает первой. «А почему по высоте разные» —
    # Константин, 17.09.2026, на равных по высоте кнопках.
    ПУСТО = ("rgba(0, 0, 0, 0)", "transparent")
    было_бланком = страница.evaluate("() => document.body.classList.contains('ui-blank')")
    for бланк in (False, True):
        страница.evaluate("(б) => document.body.classList.toggle('ui-blank', !!б)", бланк)
        страница.wait_for_timeout(60)
        рост = страница.evaluate("""() => {
          const м = с => { const э = document.querySelector(с); if (!э) return null;
            const r = э.getBoundingClientRect();
            return { в: +r.height.toFixed(1), верх: +r.top.toFixed(1), низ: +r.bottom.toFixed(1),
                     залито: getComputedStyle(э).backgroundColor }; };
          return { копия: м('#clientLinkBar .cl-copy'), обновить: м('#clientLinkBar .cl-upd') };
        }""")
        где = окно + (", бланк" if бланк else "")
        к, о = рост["копия"], рост["обновить"]
        if not (к and о):
            плохо(где, "в строке заголовка нет одной из кнопок")
            continue
        if abs(к["в"] - о["в"]) > 0.6:
            плохо(где, f"«Скопировать ссылку» {к['в']:.0f} px, «Обновить» {о['в']:.0f} px — "
                       "кнопки одной строки разной высоты")
        if abs(к["верх"] - о["верх"]) > 0.6 or abs(к["низ"] - о["низ"]) > 0.6:
            плохо(где, "кнопки строки заголовка стоят не по одной линии")
        # Залитая кнопка кажется крупнее незалитой при равной высоте, и глаз
        # читает это как разную высоту. Сравнение в обе стороны: залита может
        # оказаться любая из двух.
        if (о["залито"] in ПУСТО) != (к["залито"] in ПУСТО):
            плохо(где, f"одна кнопка залита, другая нет: копия {к['залито']}, "
                       f"обновить {о['залито']} — при равной высоте выглядят разными")
    страница.evaluate("(б) => document.body.classList.toggle('ui-blank', !!б)", было_бланком)

    # ── «Параметры» → «Ссылка»: полоску можно убрать совсем ─────────────
    # Галочка лежит в настройках аккаунта, а не устройства: settings уезжают
    # в профиль, поэтому проверяется и то, что переключатель их трогает.
    страница.evaluate("() => { window._снимокКлиента = null; нарисоватьПолосуСсылки(); }")
    пункт = страница.evaluate("""() => {
      const п = document.getElementById('printParamsLinkItem');
      if (!п) return null;
      const г = document.getElementById('printParamsLinkCheck');
      return { текст: п.textContent.replace(/[✓\\s]+/g, ' ').trim(),
               галочка: г ? getComputedStyle(г).opacity : null,
               виден: !!п.getClientRects().length };
    }""")
    if not пункт:
        плохо(окно, "в «Параметрах» нет пункта «Ссылка»")
    else:
        if пункт["текст"] != "Ссылка":
            плохо(окно, f"пункт назван {пункт['текст']!r}, а не «Ссылка»")
        if пункт["галочка"] != "1":
            плохо(окно, "галочка «Ссылка» снята при настройке по умолчанию")

        # Пункт добавлен третьим — значит, меню стало длиннее, и его нижний
        # край мог уйти под обрез окна печати. Мерить высоту мало: важно,
        # что по пункту попадает нажатие.
        достаём = страница.evaluate("""() => {
          togglePrintParamsDrop();
          const п = document.getElementById('printParamsLinkItem');
          const r = п.getBoundingClientRect();
          const под = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          const итог = { высота: +r.height.toFixed(1), низ: +r.bottom.toFixed(1),
                         окно: innerHeight, свой: !!(под && п.contains(под)) };
          togglePrintParamsDrop();
          return итог;
        }""")
        if not достаём["свой"]:
            плохо(окно, "по пункту «Ссылка» не попадает нажатие — меню выросло "
                        "и нижний пункт ушёл под обрез")
        if достаём["низ"] > достаём["окно"]:
            плохо(окно, f"пункт «Ссылка» на {достаём['низ'] - достаём['окно']:.0f} px "
                        "ниже края экрана")

        убрали = страница.evaluate("""() => {
          togglePrintClientLink();
          const п = document.getElementById('clientLinkBar');
          const л = document.getElementById('clientLinkRule');
          let вНастройках = null;
          try { вНастройках = JSON.parse(localStorage.getItem('appSettings_v1') || '{}').showClientLink; }
          catch (e) {}
          return {
            полоса: getComputedStyle(п).display, линейка: getComputedStyle(л).display,
            внутри: п.innerHTML.trim().length, развёрнута: п.classList.contains('open'),
            галочка: getComputedStyle(document.getElementById('printParamsLinkCheck')).opacity,
            вПамяти: appSettings.showClientLink, вНастройках: вНастройках,
          };
        }""")
        if убрали["полоса"] != "none":
            плохо(окно, "снятая галочка «Ссылка» не убрала полоску")
        if убрали["линейка"] != "none":
            плохо(окно, "полоска убрана, а линейка под ней осталась — в панели висит пустая черта")
        if убрали["внутри"]:
            плохо(окно, "убранная полоска осталась в разметке с содержимым")
        if убрали["развёрнута"]:
            плохо(окно, "убранная полоска осталась развёрнутой — вернётся раскрытой")
        if убрали["галочка"] != "0":
            плохо(окно, "полоску убрали, а галочка в меню осталась стоять")
        if убрали["вПамяти"] is not False or убрали["вНастройках"] is not False:
            плохо(окно, f"настройка не записалась: в памяти {убрали['вПамяти']}, "
                        f"в настройках {убрали['вНастройках']} — на другом устройстве "
                        "полоска вернётся")

        # Убранная полоска не стоит запроса к базе при открытии панели.
        ходили = страница.evaluate("""async () => {
          let ходов = 0;
          const был = window.загрузитьСсылкуКлиента;
          window.загрузитьСсылкуКлиента = async () => { ходов++; };
          await подтянутьСсылкуВПанель();
          window.загрузитьСсылкуКлиента = был;
          return ходов;
        }""")
        if ходили:
            плохо(окно, "панель ходит за ссылкой, хотя полоска убрана")

        вернули = страница.evaluate("""async () => {
          await togglePrintClientLink();
          const п = document.getElementById('clientLinkBar');
          return { полоса: getComputedStyle(п).display,
                   есть: !!п.querySelector('.cl-copy'),
                   галочка: getComputedStyle(document.getElementById('printParamsLinkCheck')).opacity,
                   вПамяти: appSettings.showClientLink };
        }""")
        if вернули["полоса"] == "none" or not вернули["есть"]:
            плохо(окно, "галочку вернули, а полоска не появилась")
        if вернули["галочка"] != "1" or вернули["вПамяти"] is not True:
            плохо(окно, "галочку вернули, а настройка осталась снятой")


    # От 768 px все пять кнопок стоят одной строкой. Держится это тремя
    # пикселями запаса, поэтому пусть держит проба, а не надежда: подпись
    # кнопки станет длиннее — узнаем здесь, а не на снимке от Константина.
    if ш >= 768 and д["строкиВерха"] > 1:
        плохо(окно, f"кнопки панели встали в {д['строкиВерха']} ряда — от 768 px они "
                    "обязаны помещаться в один")

    # Кнопка одна в ряду — только если строкой выше ей не хватило места.
    for о in д["одиночки"]:
        if о["свободно"] >= о["нужно"]:
            плохо(окно, f"{о['кто']} стоит в ряду одна, хотя строкой выше свободно "
                        f"{о['свободно']:.0f} px при нужных {о['нужно']:.0f} — перенос лишний")

    if д["переполнение"] > 1:
        плохо(окно, f"горизонтальное переполнение страницы {д['переполнение']} px")

    # Списки кнопок панели открываются на экране целиком. Привязка меню к краю
    # кнопки рассчитывалась на прежний порядок, где «Бланк» стоял у правого
    # края; распорки больше нет, и проверять это надо мерой, а не памятью.
    ЗАМЕР = """([к, м]) => {
      const кн = document.getElementById(к), мн = document.getElementById(м);
      if (!кн || !мн) return null;
      кн.click();
      const r = мн.getBoundingClientRect();
      кн.click();
      return { л: r.left, п: r.right, ш: r.width };
    }"""
    for кнопка, меню in (("previewEntityBtn", "previewEntityMenu"),
                         ("printStyleDropBtn", "printStyleDropMenu"),
                         ("printSectionBtn", "printSectionMenu"),
                         ("printParamsBtn", "printParamsDropMenu")):
        вышло = страница.evaluate(ЗАМЕР, [кнопка, меню])
        страница.wait_for_timeout(60)
        if not вышло or not вышло["ш"]:
            continue
        if вышло["л"] < -1:
            плохо(окно, f"список «{меню}» уходит за левый край на {-вышло['л']:.0f} px")
        if вышло["п"] > ш + 1:
            плохо(окно, f"список «{меню}» уходит за правый край на {вышло['п'] - ш:.0f} px")

    # Лист менеджера: со скрытыми параметрами в сетку реквизитов уходит пустая
    # клетка-распорка. Своей линейки она рисовать не должна — это была бы та же
    # полоска без названия, что у клиента. Проверяется правилом таблицы стилей,
    # а не отрисовкой документа: каталог цен пробе недоступен.
    линейка = страница.evaluate("""(стили) => {
      const лист = document.createElement('style');
      лист.textContent = стили;
      document.head.appendChild(лист);
      // Цвета линеек заданы переменными на .bl-doc — без обёртки var(--rule)
      // не разрешается, и линейки нет ни у кого. Это уже ловилось.
      const док = document.createElement('div');
      док.className = 'bl-doc';
      док.innerHTML = '<div class="bl-req">' +
        '<div><span>Менеджер</span><b>Ефремов</b></div><div></div></div>';
      document.body.appendChild(док);
      const сетка = док.firstElementChild;
      const итог = {
        пустая: parseFloat(getComputedStyle(сетка.children[1]).borderBottomWidth) || 0,
        полная: parseFloat(getComputedStyle(сетка.children[0]).borderBottomWidth) || 0,
      };
      док.remove();
      лист.remove();
      return итог;
    }""", СТИЛИ_ЛИСТА)
    if линейка["пустая"]:
        плохо(окно, f"пустая клетка реквизитов рисует линейку {линейка['пустая']:.0f} px — "
                    "полоска без названия на листе менеджера")
    if not линейка["полная"]:
        плохо(окно, "заполненная строка реквизитов осталась без линейки — "
                    "правило сняло лишнего")

    # Разворот — только птичкой.
    страница.evaluate("() => переключитьПолосуСсылки(false)")
    страница.evaluate("""() => {
      const г = document.querySelector('#clientLinkBar .cl-head');
      const r = г.getBoundingClientRect();
      г.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + 4, clientY: r.top + 4 }));
    }""")
    страница.wait_for_timeout(120)
    if страница.evaluate("() => document.getElementById('clientLinkBar').classList.contains('open')"):
        плохо(окно, "нажатие по строке заголовка развернуло блок — должна только птичка")
    страница.click("#clientLinkBar .cl-arrow")
    страница.wait_for_timeout(400)
    if not страница.evaluate("() => document.getElementById('clientLinkBar').classList.contains('open')"):
        плохо(окно, "птичка не развернула блок")

    # Точка на колокольчике загорается сама, без нажатия. До 17.09.2026
    # собрать уведомления было некому, кроме самого открытия окна: страница
    # стоит открытой весь день, клиент открывал ссылку — колокольчик молчал.
    точка = страница.evaluate("""async () => {
      const т = document.getElementById('bellDot');
      // Начинаем с чистого листа: всё прочитано, точки нет.
      пометитьПрочитанными();
      _уведомления = [];
      обновитьТочкуКолокольчика();
      const доЗахода = getComputedStyle(т).display;
      // Клиент открывает ссылку, пока страница просто стоит открытой.
      window.__ТАБЛИЦЫ.client_link_visits.push({
        code: 'adkv8q5j', seen_at: new Date(Date.now() + 1000).toISOString(),
        version_at: '2026-09-16T10:00:00Z',
      });
      const самоПоСебе = getComputedStyle(т).display;
      // Вернулись к вкладке — список обязан перечитаться сам, без нажатий.
      _уведомленияСобраны = 0;
      document.dispatchEvent(new Event('visibilitychange'));
      await new Promise(р => setTimeout(р, 500));
      const итог = {
        доЗахода, самоПоСебе,
        послеВозврата: getComputedStyle(т).display,
        окноНеОткрывали: document.getElementById('bellMenu').style.display !== 'block',
      };
      // Убираем за собой: окон четыре, и подложенный заход иначе копился бы
      // от окна к окну, а проверка числа строк ниже считала бы чужое.
      window.__ТАБЛИЦЫ.client_link_visits.pop();
      пометитьПрочитанными();
      return итог;
    }""")
    if точка["доЗахода"] != "none":
        плохо(окно, "точка горит, когда всё прочитано")
    if точка["самоПоСебе"] != "none":
        плохо(окно, "точка загорелась до того, как список перечитали — проба меряет не то")
    if точка["послеВозврата"] == "none":
        плохо(окно, "вернулись к вкладке, а точка не загорелась — о заходе узнаешь, "
                    "только нажав на колокольчик")
    if not точка["окноНеОткрывали"]:
        плохо(окно, "проба открыла окно уведомлений — так загорелась бы и прежняя точка")

    # Окно уведомлений: подписи под списком нет, каждое открытие своей строкой.
    страница.evaluate("() => { document.getElementById('printOverlay').style.display='none'; }")
    страница.evaluate(КОЛОКОЛЬЧИК)
    страница.wait_for_timeout(200)
    у = страница.evaluate("""() => ({
      подпись: !!document.querySelector('#bellMenu .nt-f'),
      строк: document.querySelectorAll('#bellMenu .nt-i').length,
      строки: [...document.querySelectorAll('#bellMenu .nt-i')].map(э => ({
        текст: э.querySelector('.t').textContent,
        зовёт: э.getAttribute('role') === 'button' && !!э.getAttribute('onclick'),
        шеврон: !!э.querySelector('.nt-go'),
        палец: getComputedStyle(э).cursor === 'pointer',
      })),
      текст: document.getElementById('bellMenu').textContent,
      низ: (() => { const с=[...document.querySelectorAll('#bellMenu .nt-i')].pop();
        if(!с) return null; const м=document.getElementById('bellMenu').getBoundingClientRect();
        return { рамка: getComputedStyle(с).borderBottomWidth,
                 доНиза: м.bottom - с.getBoundingClientRect().bottom }; })(),
    })""")
    if у["подпись"]:
        плохо(окно, "в окне уведомлений осталась подпись «позже здесь появятся…»")
    if у["строк"] != 4:
        плохо(окно, f"в окне уведомлений {у['строк']} строк на четыре открытия — открытия склеены")
    # Имя заказчика — справка в конце строки, а не подлежащее: по ссылке мог
    # открыть кто угодно, кому её переслали, и «Иванов открыл» — утверждение,
    # которого мы не знаем (Константин, 16.09.2026).
    ИМЯ = "Иванов Иван Сергеевич"
    ПРОЕКТ = "Фахверковая баня «Берлин» 9×5"
    for р in у.get("строки") or []:
        строка = р["текст"]
        if not строка.startswith("Открыта спецификация"):
            плохо(окно, f"уведомление начинается не с события: {строка[:70]!r}")
        if re.search(r"\bоткрыл[аи]?\b", строка):
            плохо(окно, f"уведомление утверждает, кто открыл: {строка[:70]!r}")
        if ПРОЕКТ in строка:
            if ИМЯ not in строка:
                плохо(окно, f"в уведомлении нет имени заказчика: {строка[:70]!r}")
            elif строка.index(ИМЯ) < строка.index(ПРОЕКТ):
                плохо(окно, f"имя заказчика стоит впереди спецификации: {строка[:70]!r}")
        # Нажимается та строка, за которой стоит расчёт, и только она.
        сПресетом = ПРОЕКТ in строка
        if сПресетом and not (р["зовёт"] and р["шеврон"] and р["палец"]):
            плохо(окно, f"строка с расчётом не открывает его: зов={р['зовёт']}, "
                        f"шеврон={р['шеврон']}, палец={р['палец']}")
        if not сПресетом and (р["зовёт"] or р["шеврон"] or р["палец"]):
            плохо(окно, "строка по ссылке без пресета притворяется нажимаемой")

    # Нажатие уводит в тот пресет, по которому выдана ссылка, и гасит окно.
    # Пресета в этом браузере нет — проверяется длинный путь: достать строку
    # из облака, положить к себе и открыть.
    страница.evaluate("""() => {
      window.__куда = null;
      window.__былLoadPreset = window.loadPreset;
      window.loadPreset = ид => { window.__куда = ид; };
      document.querySelector('#bellMenu .nt-i.go').click();
    }""")
    страница.wait_for_timeout(600)
    ушли = страница.evaluate("""() => {
      const итог = { куда: window.__куда,
                     окно: document.getElementById('bellMenu').style.display,
                     улёгся: !!(JSON.parse(localStorage.getItem('banya_msk_presets_v1') || '{}')['7']) };
      window.loadPreset = window.__былLoadPreset;
      return итог;
    }""")
    if ушли["куда"] != "7":
        плохо(окно, f"нажатие увело в пресет {ушли['куда']!r}, а ссылка выдана по «7»")
    if ушли["окно"] != "none":
        плохо(окно, "после перехода окно уведомлений осталось открытым")
    if у["низ"] and у["низ"]["рамка"] not in ("0px", ""):
        плохо(окно, "последняя строка уведомлений отчёркнута линейкой в край окна")
    страница.evaluate("() => { document.getElementById('bellMenu').style.display='none'; }")

    снимок = pathlib.Path(__file__).parent / f"снимок-{окно.replace(' ', '-')}.png"
    страница.evaluate("() => { document.getElementById('printOverlay').style.display='block'; }")
    страница.wait_for_timeout(150)
    страница.locator("#printToolbar").screenshot(path=str(снимок))


def главная():
    global СТИЛИ_ЛИСТА
    СТИЛИ_ЛИСТА = стили_печатного_листа()
    с, порт = сервер()
    ошибки = []
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
        стр = бр.new_page()
        стр.add_init_script(ЗАГЛУШКА)
        стр.on("console", lambda с: ошибки.append(с.text) if с.type == "error" else None)
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
        стр.wait_for_timeout(1500)
        for имя, ш, в in ОКНА:
            проверить(стр, имя, ш, в)
        бр.close()
    с.shutdown()

    важные = [о for о in ошибки if "favicon" not in о and "jsdelivr" not in о]
    if важные:
        print("Ошибки в консоли (первые пять):")
        for о in важные[:5]:
            print("   ", о[:200])
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("\nЧисто: строка заголовка, «Печать / PDF», подпись и уведомления — все четыре окна.")


if __name__ == "__main__":
    главная()
