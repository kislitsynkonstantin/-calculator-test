#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окна не уходят под открытую боковую панель.

Константин 21.09.2026, снимком широкого экрана: «сделай на десктопе это окно
чуть уже, чтобы боковую панель справа не перекрывало». Окно пресетов
центрировалось во всём экране, панель висит справа поверх всего — и правый край
карточек, кнопки «Загрузить» и «Публ.», оказывался под ней. Проверка кадра
целиком нашла второе такое же окно: лист справки шириной 1000 px уходил под
панель вместе с крестиком «Закрыть», который прижат к его правому краю.

Путь до дефекта важен не меньше самого дефекта. Открытие окна саму панель
закрывает (`openPresetPanel` зовёт `closeSideNav`), поэтому проба, открывающая
панель первой, ничего бы не поймала. Панель приходит после окна: мышь, задевшая
правый край экрана, открывает её поверх всего — этот путь проба и повторяет,
двигая указатель, а не вызывая `openSideNav` напрямую.

Проба меряет то, что видно, в обеих темах и на двух ширинах:

  • окно кончается левее панели, и между ними есть зазор;
  • сама панель при этом открыта — иначе мерить нечего;
  • панель закрыта — поджатие снято: оно не должно застревать;
  • на узком экране панель и так лежит поверх листа, и окно не жмётся зря.

    python3 check_sidenav_overlap.py
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
ЗАЗОР = 8          # меньше — окно и панель читаются слипшимися

# Окно: как его зовут, чем открывают, где лежит сам лист и где его подложка.
ОКНА = [
    ("окно пресетов", "openPresetPanel()", "#presetBox", "#presetPanel",
     "правый край карточек с кнопками «Загрузить» и «Публ.»"),
    ("справка", "openManual()", "#manualPanel", "#manualOverlay",
     "крестик «Закрыть», прижатый к правому краю листа"),
]


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


ВИД = """([лист, подложка]) => {
  const окно = document.querySelector(лист);
  const низ = document.querySelector(подложка);
  const панель = document.querySelector('.side-nav');
  const тело = панель ? панель.querySelector('.side-nav-panel') : null;
  const к = окно ? окно.getBoundingClientRect() : null;
  const п = тело ? тело.getBoundingClientRect() : null;
  return {
    окноВидно: !!(к && к.width > 1),
    окноПраво: к ? Math.round(к.right) : null,
    окноШирина: к ? Math.round(к.width) : null,
    панельОткрыта: !!(панель && панель.classList.contains('open') && п && п.width > 1),
    панельЛево: п ? Math.round(п.left) : null,
    поле: низ ? Math.round(parseFloat(getComputedStyle(низ).paddingRight) || 0) : 0,
  };
}"""


def подготовить(стр, порт, бланк, вызов):
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                        + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2400)
    стр.evaluate("""async ([бланк, вызов]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      window._sbProfile = { role: 'admin', full_name: 'Проба' };
      document.body.classList.toggle('ui-blank', бланк);
      const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
      selectProjectOption(и >= 0 ? и : 0);
      await new Promise(r => setTimeout(r, 1000));
      eval(вызов);
      await new Promise(r => setTimeout(r, 700));
    }""", [бланк, вызов])


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for имя, вызов, лист, подложка, что in ОКНА:
                print(f"{имя}:")
                for тема in ("Модерн", "Бланк"):
                    for ширина in (1280, 1440):
                        где = f"{имя} · {тема} {ширина}px"
                        стр = бр.new_page(viewport={"width": ширина, "height": 950})
                        ошибки = []
                        стр.on("pageerror", lambda e: ошибки.append(str(e)))
                        подготовить(стр, порт, тема == "Бланк", вызов)

                        # Панель открывает не вызов из кода, а мышь у правого
                        # края — тем же путём она приходит поверх открытого
                        # окна у человека.
                        стр.mouse.move(ширина // 2, 500)
                        стр.mouse.move(ширина - 4, 500)
                        стр.wait_for_timeout(500)

                        в = стр.evaluate(ВИД, [лист, подложка])
                        if not в["окноВидно"]:
                            плохо(f"[{где}] окно не открылось — мерить нечего")
                        elif not в["панельОткрыта"]:
                            плохо(f"[{где}] мышь у правого края не открыла боковую "
                                  "панель — перекрывать нечему, проверка прошла бы "
                                  "вхолостую")
                        else:
                            зазор = в["панельЛево"] - в["окноПраво"]
                            print(f"  {тема} {ширина}px: окно {в['окноШирина']} px, "
                                  f"правый край {в['окноПраво']}, панель с "
                                  f"{в['панельЛево']} · зазор {зазор}")
                            if зазор < ЗАЗОР:
                                плохо(f"[{где}] окно заходит под боковую панель: "
                                      f"зазор {зазор} px — под ней {что}")

                        # ── Панель закрыта — поджатие снято ────────────────
                        стр.evaluate("() => { closeSideNav(); }")
                        стр.wait_for_timeout(400)
                        после = стр.evaluate(ВИД, [лист, подложка])
                        if после["поле"] > 40:
                            плохо(f"[{где}] панель закрыта, а окно осталось поджатым "
                                  f"на {после['поле']} px — поджатие застряло")

                        if ошибки:
                            плохо(f"[{где}] ошибки страницы: " + "; ".join(ошибки)[:200])
                        стр.close()

                # ── Узкий экран: панель лежит поверх листа, жать окно незачем ─
                стр = бр.new_page(viewport={"width": 900, "height": 900})
                подготовить(стр, порт, False, вызов)
                стр.evaluate("() => { try { openSideNav(); } catch (e) {} }")
                стр.wait_for_timeout(400)
                у = стр.evaluate(ВИД, [лист, подложка])
                if у["поле"] > 40:
                    плохо(f"[{имя} · 900px] окно поджато на {у['поле']} px, хотя на "
                          "этой ширине панель и так лежит поверх листа — место "
                          "отнято у содержимого ни за что")
                стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: окно пресетов и справка кончаются левее открытой боковой панели "
          "в обеих темах, закрытая панель снимает поджатие, а на узком экране его "
          "нет вовсе.")


if __name__ == "__main__":
    главная()
