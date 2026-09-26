#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно «Пресеты»: при прокрутке ряд кнопок уезжает, поиск остаётся.

Константин 26.09.2026: «когда проматываю в окне пресетов, этот блок кнопок
проматывай и оставляй только полоску поиска».

Проба держит на 390 / 768 / 1440, в «Бланке» и «Модерне», днём и ночью:
  • вверху списка ряд кнопок виден целиком;
  • после прокрутки ряд ушёл за верх области прокрутки, а строка поиска
    прилипла к её верху, непрозрачна и сама отвечает на нажатие — карточки
    под ней не просвечивают и не перехватывают палец;
  • шапка с крестиком и вкладки на месте;
  • прокручивается одна область: у самого списка своей прокрутки нет;
  • «Активный» по-прежнему доводит до открытого пресета.

    python3 check_preset_scroll.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


РАЗЛОЖИТЬ = """() => {
  const п = {};
  for (let i = 0; i < 14; i++) {
    const ид = 'p' + i;
    п[ид] = { id: ид, name: 'Пресет ' + (i + 1), savedAt: new Date(Date.now() - i * 3600e3).toISOString(),
      shortCode: String(100000 + i), state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 3000000 + i, tech: 'frame' } };
  }
  window._пресеты = п; setActivePreset('p11');
  openPresetPanel(); switchPresetTab('my'); renderPresetList();
}"""

МЕРА = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const обл = document.getElementById('presetScroll');
  if (!обл) return { нетОбласти: true };
  const тул = document.querySelector('#presetBox .ptoolbar'), пои = document.querySelector('#ptab-content-my .psearch-bar');
  const шапка = document.getElementById('presetHeader'), влк = document.querySelector('#presetBox .ptabs');
  const r = el => el.getBoundingClientRect();
  обл.scrollTop = 0; await ждать(60);
  const о0 = r(обл), т0 = r(тул), ш0 = r(шапка);
  const вначале = { тулВиден: т0.top >= о0.top - 0.5 && т0.bottom <= о0.bottom };
  обл.scrollTop = 600; await ждать(80);
  const о = r(обл), т = r(тул), п = r(пои), ш = r(шапка), в = r(влк);
  const ввод = пои.querySelector('input'), вр = r(ввод);
  const попал = document.elementFromPoint(вр.left + 20, (вр.top + вр.bottom) / 2);
  const фон = getComputedStyle(пои).backgroundColor;
  const спис = document.getElementById('presetList');
  return { вначале, прокручено: обл.scrollTop,
    тулУшёл: т.bottom <= о.top + 0.5, поискСверху: Math.abs(п.top - о.top) <= 1,
    поискОтвечает: !!(попал && пои.contains(попал)), фон,
    шапкаНаМесте: Math.abs(ш.top - ш0.top) < 0.5 && ш.bottom <= о.top + 0.5 && в.bottom <= о.top + 0.5,
    своейПрокрутки: спис.scrollHeight > спис.clientHeight + 1 && getComputedStyle(спис).overflowY !== 'visible',
    гориз: обл.scrollWidth > обл.clientWidth + 1 };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (768, 1024), (1440, 900)):
                стр = бр.new_page(viewport={"width": ш, "height": в})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
                  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none'; }""")
                for тема in ("blank", "light"):
                    for ночь in (False, True):
                        стр.evaluate(f"() => {{ applyUiStyle('{тема}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                        стр.evaluate(РАЗЛОЖИТЬ)
                        стр.wait_for_timeout(200)
                        м = стр.evaluate(МЕРА)
                        н = f"{ш} {тема} {'ночь' if ночь else 'день'}"
                        if м.get("нетОбласти"):
                            плохо(н + ": нет общей области прокрутки"); continue
                        if not м["вначале"]["тулВиден"]: плохо(н + ": вверху списка ряд кнопок виден не целиком")
                        if м["прокручено"] < 100: плохо(н + f": область не прокручивается ({м['прокручено']})")
                        if not м["тулУшёл"]: плохо(н + ": после прокрутки ряд кнопок остался на экране")
                        if not м["поискСверху"]: плохо(н + ": строка поиска не прилипла к верху")
                        if not м["поискОтвечает"]: плохо(н + ": строка поиска не отвечает — сверху лежит карточка")
                        if м["фон"] in ("rgba(0, 0, 0, 0)", "transparent"): плохо(н + ": строка поиска прозрачна, карточки просвечивают")
                        if not м["шапкаНаМесте"]: плохо(н + ": шапка или вкладки сдвинулись")
                        if м["своейПрокрутки"]: плохо(н + ": у списка осталась своя прокрутка")
                        if м["гориз"]: плохо(н + ": прокрутка вбок")
                        if ш == 390 and тема == "blank" and not ночь:
                            print(f"  {н}: {json.dumps(м, ensure_ascii=False)}")
                # «Активный» доводит до открытого пресета, не прячась под поиском.
                стр.evaluate("() => applyUiStyle('blank', false)")
                стр.evaluate(РАЗЛОЖИТЬ)
                р = стр.evaluate("""async () => { if (!document.getElementById('presetScroll')) return { виден: false };
                  document.getElementById('presetScroll').scrollTop = 0;
                  await scrollToActivePreset(); await new Promise(r => setTimeout(r, 900));
                  const к = document.querySelector('.pcard-active').getBoundingClientRect(), о = document.getElementById('presetScroll').getBoundingClientRect(),
                        п = document.querySelector('#ptab-content-my .psearch-bar').getBoundingClientRect();
                  return { виден: к.top >= п.bottom - 1 && к.bottom <= о.bottom + 1 }; }""")
                if not р["виден"]:
                    плохо(f"{ш}: «Активный» не довёл до открытого пресета (карточка под поиском или за краем)")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{ш}: ошибка страницы: {о[:160]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: при прокрутке окна «Пресеты» ряд кнопок уезжает, строка поиска прилипает к верху и отвечает на нажатие; "
          "шапка и вкладки на месте, у списка нет своей прокрутки, «Активный» доводит до пресета — на 390/768/1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
