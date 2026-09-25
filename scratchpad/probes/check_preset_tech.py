#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Метка технологии на пресете и фильтр по ней.

Константин 20.09.2026 утвердил макетом: на телефоне метка справа от суммы
(вариант Г), на широком экране слева от неё (вариант Д) — «рядом с суммой»
значит разное, потому что на широком экране сумма уже прижата к правому краю.
Плюс фильтр с одиночным выбором и «Все», плюс нажатие по метке на карточке.

Проба меряет то, что видно, и на обеих ширинах:

  • метка стоит у каждого расчёта и называет его технологию — ту же, что
    лежит в снимке, а не ту, что открыта сейчас;
  • на 1440 метка слева от суммы, на 390 — справа, и обе на одной строке;
  • метка не приклеена к соседям, не висит в пустоте, поле нажатия 44 px и
    не отбирает нажатие у «Загрузить»;
  • чип заменяет собой прежний выбор, а не набирается к нему; повторное
    нажатие и «Все» снимают фильтр; счёт у чипа не меняется от собственного
    нажатия;
  • нажатие по метке оставляет одну технологию, повторное — возвращает все;
  • выбрана технология без расчётов — список не «ничего не найдено», а
    отфильтрован, и сказано, чем его вернуть.

    python3 check_preset_tech.py
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
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

ТАБЛИЦЫ_JS = (
    "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};"
    "window.__ТАБЛИЦЫ.pricing_projects = [1,2].map(и => ({"
    "  product: 'frame', sort: и, slug: 'Проба ' + и, name: 'Проба ' + и,"
    "  price_100: 1000000, price_150: 1200000, price_200: 1400000,"
    "  floors: 1, roof_type: 'двускатная', warm: true,"
    "  open_area: 10, closed_area: 20, facade_area: 60,"
    "  paint_area: 60, roof_area: 40 }));")

# Три расчёта: два каркасных, один брусовый и один без поля технологии —
# сохранённый до разделения технологий, он обязан читаться каркасным.
ПРЕСЕТЫ_JS = """() => {
  const мк = (ид, имя, тех, сумма) => ({
    id: ид, name: имя, savedAt: '2026-09-1' + ид + 'T10:00:00Z',
    shortCode: '40820' + ид, starred: ид === '1',
    state: Object.assign({ version: 1, totalNum: сумма,
      project: { name: 'Проба 1' }, thickness: 1 }, тех ? { tech: тех } : {}),
  });
  const все = {
    '1': мк('1', 'Каркасный расчёт', 'frame', 5909654),
    '2': мк('2', 'Брусовый расчёт', 'glulam', 7214800),
    '3': мк('3', 'Древний расчёт без поля', null, 4513375),
  };
  saveAllPresets(все);
  return Object.keys(все).length;
}"""

ВИД = """() => {
  const карточки = [...document.querySelectorAll('#presetList .pcard')];
  const чипы = [...document.querySelectorAll('#presetList .tfilter-chip')].map(ч => ({
    текст: (ч.textContent || '').trim(),
    выбран: ч.classList.contains('on'),
    пунктир: ч.classList.contains('soon'),
    высота: (() => { const к = ч.getBoundingClientRect();
      const с = getComputedStyle(ч, '::before');
      return Math.round(к.height - 2 * (parseFloat(с.top) || 0)); })(),
  }));
  return {
    чипы,
    карточки: карточки.map(к => {
      const м = к.querySelector('.tech-chip');
      const ц = к.querySelector('.pcard-price');
      const имя = к.querySelector('.pcard-name');
      const кн = к.querySelector('.pcard-use');
      if (!м || !ц) return { имя: имя ? имя.textContent.trim() : '', метки: false };
      const мк = м.getBoundingClientRect(), цк = ц.getBoundingClientRect();
      const с = getComputedStyle(м, '::before');
      const вб = parseFloat(с.top) || 0, вв = parseFloat(с.left) || 0;
      const ряд = м.parentElement.getBoundingClientRect();
      const карт = к.getBoundingClientRect();
      const снизу = кн ? кн.getBoundingClientRect() : null;
      return {
        имя: имя ? имя.textContent.trim() : '',
        метки: true,
        текст: (м.textContent || '').trim(),
        выбрана: м.classList.contains('on'),
        залита: (() => { const ф = getComputedStyle(м).backgroundColor;
          const ч = (ф.match(/[\d.]+/g) || []).map(Number);
          return !(ч.length >= 4 && ч[3] === 0) && ф !== 'transparent'; })(),
        // Вид отмеченной метки — то, чем она отличается от неотмеченной.
        вид: [getComputedStyle(м).borderTopColor, getComputedStyle(м).color,
              getComputedStyle(м).fontWeight].join('|'),
        слеваОтСуммы: мк.right <= цк.left + 1,
        справаОтСуммы: мк.left >= цк.right - 1,
        однаСтрока: Math.abs((мк.top + мк.bottom) / 2 - (цк.top + цк.bottom) / 2) < 14,
        доСуммы: мк.left >= цк.right ? mкОтступ(мк, цк) : цк.left - мк.right,
        доКрая: Math.min(мк.left - карт.left, карт.right - мк.right),
        поле: { ш: Math.round(мк.width - 2 * вв), в: Math.round(мк.height - 2 * вб) },
        задеваетКнопку: snизу(мк, вб, снизу),
        цвет: (() => { const т = м.querySelector('.tech-dot');
          return т ? getComputedStyle(т).backgroundColor : null; })(),
      };
    }),
    пусто: (document.querySelector('#presetList .preset-empty') || {}).textContent || '',
    панельВидна: (() => { const п = document.getElementById('presetPanel');
      return !!п && п.getBoundingClientRect().width > 100; })(),
  };
  function mкОтступ(мк, цк) { return мк.left - цк.right; }
  function snизу(мк, вб, кн) {
    if (!кн) return false;
    return (мк.bottom - вб) > кн.top + 1;
  }
}"""


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


ОТКРЫТЬ = """async (пресеты) => {
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  window._sbProfile = { role: 'admin', full_name: 'Проба' };
  document.body.classList.add('ui-blank');
  if (window.__ночь) document.body.classList.add('dark');
  selectProjectOption(0);
  await new Promise(r => setTimeout(r, 900));
  // Панель надо открыть: у закрытой нет размеров, и всякая мерка в ней даёт
  // нули. Проба, меряющая нули, зеленеет на чём угодно.
  openPresetPanel();
  await new Promise(r => setTimeout(r, 500));
  renderPresetList();
  await new Promise(r => setTimeout(r, 400));
}"""


def проверить(стр, ширина):
    мк = f"{ширина}px"
    в = стр.evaluate(ВИД)

    if not в.get("панельВидна"):
        плохо(f"[{мк}] панель пресетов закрыта — мерить в ней нечего, "
              "и всякая проверка прошла бы вхолостую")
        return

    карточки = в["карточки"]
    if len(карточки) != 3:
        плохо(f"[{мк}] карточек в списке {len(карточки)}, а положено 3 — "
              "мерить не на чем")
        return
    без = [к["имя"] for к in карточки if not к.get("метки")]
    if без:
        плохо(f"[{мк}] у расчётов нет метки технологии: {', '.join(без)}")
        return

    ожидание = {"Каркасный расчёт": "Каркас", "Брусовый расчёт": "Брус",
                "Древний расчёт без поля": "Каркас"}
    for к in карточки:
        надо = ожидание.get(к["имя"])
        if надо and надо not in к["текст"]:
            плохо(f"[{мк}] «{к['имя']}» помечен «{к['текст']}», а должен «{надо}»")

    для_места = карточки[0]
    if ширина >= 900:
        if not для_места["слеваОтСуммы"]:
            плохо(f"[{мк}] метка не слева от суммы — на широком экране просили Д")
    else:
        if not для_места["справаОтСуммы"]:
            плохо(f"[{мк}] метка не справа от суммы — на телефоне просили Г")
    if not для_места["однаСтрока"]:
        плохо(f"[{мк}] метка и сумма на разных строках")

    for к in карточки:
        if к["поле"]["в"] < 44:
            плохо(f"[{мк}] поле нажатия метки {к['поле']['ш']}×{к['поле']['в']} — "
                  "меньше 44 px по высоте")
        if к["задеваетКнопку"]:
            плохо(f"[{мк}] поле нажатия метки залезает на «Загрузить»")
        сосед = min(abs(к["доСуммы"]), к["доКрая"])
        if сосед < 4:
            плохо(f"[{мк}] метка приклеена к соседу: {round(сосед)} px")
        if сосед > 26:
            плохо(f"[{мк}] метка висит в пустоте: ближайший сосед в "
                  f"{round(сосед)} px")

    чипы = в["чипы"]
    подписи = [ч["текст"] for ч in чипы]
    if len(чипы) != 4:
        плохо(f"[{мк}] чипов фильтра {len(чипы)}, а должно быть четыре — "
              f"«Все» и три технологии: {подписи}")
        return
    if not чипы[0]["выбран"]:
        плохо(f"[{мк}] выбор пуст, а «Все» не подсвечен")
    if "Каркас" not in подписи[1] or "2" not in подписи[1]:
        плохо(f"[{мк}] счёт у «Каркаса» не двойка: «{подписи[1]}» — "
              "древний расчёт без поля обязан считаться каркасным")
    if not чипы[3]["пунктир"]:
        плохо(f"[{мк}] «Камень» без расчётов нарисован сплошной рамкой, "
              "а место, которое только готовится, помечается пунктиром")
    мелкие = [ч["текст"] for ч in чипы if ч["высота"] < 44]
    if мелкие:
        плохо(f"[{мк}] поле нажатия чипа меньше 44 px: {', '.join(мелкие)}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ширина in (1440, 390):
                стр = бр.new_page(viewport={"width": ширина, "height": 950})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2200)
                стр.evaluate(ПРЕСЕТЫ_JS)
                стр.evaluate(ОТКРЫТЬ)
                проверить(стр, ширина)

                if ширина == 1440:
                    # ── Нажатие по метке: остаётся одна технология ──
                    стр.evaluate("() => фильтрПоМетке('my','glulam')")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    имена = [к["имя"] for к in в["карточки"]]
                    if имена != ["Брусовый расчёт"]:
                        плохо("нажатие по метке «Брус» оставило в списке "
                              + (", ".join(имена) or "пусто")
                              + " — должен остаться один брусовый")
                    if в["чипы"] and "2" not in в["чипы"][1]["текст"]:
                        плохо("счёт у чипа изменился от собственного нажатия: "
                              f"«{в['чипы'][1]['текст']}» — он должен считать "
                              "весь список, а не остаток")

                    # ── Повторное нажатие возвращает всё ──
                    стр.evaluate("() => фильтрПоМетке('my','glulam')")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    if len(в["карточки"]) != 3:
                        плохо("повторное нажатие по той же метке не вернуло "
                              f"список целиком: осталось {len(в['карточки'])}")

                    # ── Отмеченное видно, и видно обрамлением ──
                    # Обе темы: в «Бланке» ночью акцент светлеет, и признак,
                    # заметный днём, там может пропасть. Проверка одной темы
                    # такую пару пропускает молча. Меряется сама различимость,
                    # а не способ: цвет рамки и надписи вправе смениться,
                    # требование «отмеченное видно» остаётся.
                    for ночь in (False, True):
                        тема = "ночь" if ночь else "день"
                        стр.evaluate("(н) => { window.__ночь = н;"
                                     " document.body.classList.toggle('dark', н);"
                                     " всеТехнологии('my'); }", ночь)
                        стр.wait_for_timeout(300)
                        без = стр.evaluate(ВИД)
                        вид_без = {к_["имя"]: к_.get("вид") for к_ in без["карточки"]}
                        стр.evaluate("() => нажатьЧипТехнологии('my','frame')")
                        стр.wait_for_timeout(300)
                        с_ = стр.evaluate(ВИД)
                        залиты = [к_["имя"] for к_ in с_["карточки"] if к_.get("залита")]
                        if залиты:
                            плохо(f"[{тема}] метка залита: " + ", ".join(залиты)
                                  + " — просили обрамление, а заливка спорит "
                                  "с суммой рядом")
                        одинаковые = [к_["имя"] for к_ in с_["карточки"]
                                      if к_.get("вид") == вид_без.get(к_["имя"])]
                        if одинаковые:
                            плохо(f"[{тема}] фильтр стоит, а метка выглядит как "
                                  "без фильтра: " + ", ".join(одинаковые)
                                  + " — отобранный список неотличим от полного")
                        if not [ч for ч in с_["чипы"] if ч["выбран"]]:
                            плохо(f"[{тема}] чип нажат, а отметки на нём нет")
                    стр.evaluate("() => { window.__ночь = false;"
                                 " document.body.classList.remove('dark');"
                                 " всеТехнологии('my'); }")
                    стр.wait_for_timeout(250)


                    # ── Выбор одиночный ──
                    # Второй чип заменяет первый, а не набирается к нему:
                    # Константин 20.09.2026 — «мультифильтр убери: можно
                    # выбрать только один или все». Мерить надо оба признака:
                    # накопившийся выбор виден и по списку (в нём остались бы
                    # два расчёта), и по ряду чипов (отмеченными стояли бы два).
                    стр.evaluate("() => { нажатьЧипТехнологии('my','frame');"
                                 " нажатьЧипТехнологии('my','glulam'); }")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    имена = [к_["имя"] for к_ in в["карточки"]]
                    if имена != ["Брусовый расчёт"]:
                        плохо("после каркаса нажат брус, а в списке "
                              + (", ".join(имена) or "пусто")
                              + " — выбор должен заменяться, а не набираться")
                    отмечены = [ч["текст"].strip() for ч in в["чипы"] if ч["выбран"]]
                    if len(отмечены) != 1:
                        плохо("отмеченных чипов " + str(len(отмечены))
                              + " (" + ", ".join(отмечены) + ") — "
                              "отмечен должен быть ровно один")

                    # ── Повторное нажатие по чипу возвращает список ──
                    стр.evaluate("() => нажатьЧипТехнологии('my','glulam')")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    if len(в["карточки"]) != 3:
                        плохо("повторное нажатие по выбранному чипу не вернуло "
                              f"список целиком: осталось {len(в['карточки'])}")
                    if not (в["чипы"] and в["чипы"][0]["выбран"]):
                        плохо("фильтр снят повторным нажатием, а отметка на "
                              "«Все» не встала")

                    # ── «Все» снимает выбор ──
                    стр.evaluate("() => всеТехнологии('my')")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    if not (в["чипы"] and в["чипы"][0]["выбран"]):
                        плохо("«Все» нажато, а подсветка на нём не встала")
                    if len(в["карточки"]) != 3:
                        плохо("«Все» нажато, а список не вернулся целиком")

                    # ── Технология без расчётов ──
                    стр.evaluate("() => нажатьЧипТехнологии('my','stone')")
                    стр.wait_for_timeout(300)
                    в = стр.evaluate(ВИД)
                    if в["карточки"]:
                        плохо("выбран «Камень», на котором расчётов нет, "
                              "а карточки в списке остались")
                    if "Все" not in в["пусто"]:
                        плохо("список отфильтрован в пустоту, а чем его вернуть — "
                              f"не сказано: «{в['пусто'].strip()[:70]}»")
                    if not [ч for ч in в["чипы"] if ч["выбран"]]:
                        плохо("список пуст по фильтру, а сам фильтр исчез — "
                              "вернуть список нечем")
                    стр.evaluate("() => всеТехнологии('my')")

                if ошибки:
                    плохо(f"[{ширина}px] ошибки страницы: " + "; ".join(ошибки)[:200])
                стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: метка называет технологию снимка, стоит слева от суммы на "
          "широком экране и справа на телефоне, нажимается пальцем и не "
          "отбирает нажатие у соседей; фильтр выбирается по одной, «Все» "
          "возвращает список, а пустой отбор объясняет себя словами.")


if __name__ == "__main__":
    главная()
