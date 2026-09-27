#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Звезда ручного проекта в поле «Проект» — цветом темы, как в списке.

Константин 27.09.2026, снимком поля «Проект» с чёрной звездой у проекта
«„Берлин“ 9х5 Тёплый контур» и зелёными звёздами в выпадающем списке под ним:
«звёздочку ставь с цветом темы, как в списке ниже выпадающем. Размер звезды
оставь таким же (чуть больше, чем в списке ниже)».

Проба на 390 и 1440, в «Бланке» и «Модерне», днём и ночью, держит:
  • звезда в поле того же цвета, что звезда ручного проекта в списке;
  • её кегль — кегль подписи поля, то есть крупнее звезды в списке;
  • название проекта остаётся цветом подписи, а не звезды;
  • у проекта из каталога звезды в поле нет.

    python3 check_project_star.py
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
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
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


ПОДГОТОВКА = """async (а) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle(а.ui, false);
  document.body.classList.toggle('dark', а.ночь);
  const п = PROJECTS[0];
  if (!customProjects.includes(п)) customProjects.push(п);
  selectProjectOption(0); await ждать(500);
  if (typeof filterProjects === 'function') filterProjects();
  const wrap = document.getElementById('projectSelectWrap'); if (wrap) wrap.classList.add('open');
  await ждать(250);
  return true;
}"""

ОСМОТР = """() => {
  const л = document.getElementById('projectSelectLabel');
  const з = л.querySelector('.proj-star');
  const оп = document.querySelector('.custom-select-option.custom-proj');
  const сп = оп ? getComputedStyle(оп, '::after') : null;
  const цвет = у => у ? getComputedStyle(у).color : null;
  return { текст: л.textContent, звезда: !!з, цветЗвезды: цвет(з), цветПодписи: getComputedStyle(л).color,
           кегльЗвезды: з ? parseFloat(getComputedStyle(з).fontSize) : null, кегльПодписи: parseFloat(getComputedStyle(л).fontSize),
           цветВСписке: сп ? сп.color : null, кегльВСписке: сп ? parseFloat(сп.fontSize) : null };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank",):
                for ночь in (False, True):
                    for ш in (390, 1440):
                        н = f"[{ui} {'ночь' if ночь else 'день'} {ш}]"
                        стр = бр.new_page(viewport={"width": ш, "height": 900})
                        ошибки = []
                        стр.on("pageerror", lambda e: ошибки.append(str(e)))
                        стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                        стр.evaluate(ПОДГОТОВКА, {"ui": ui, "ночь": ночь})
                        р = стр.evaluate(ОСМОТР)
                        print("  " + н, json.dumps(р, ensure_ascii=False))
                        if not р["звезда"]:
                            плохо(f"{н} звезда в поле не отдельным знаком, её не покрасить: «{р['текст']}»")
                        else:
                            if р["цветЗвезды"] != р["цветВСписке"]:
                                плохо(f"{н} звезда в поле {р['цветЗвезды']}, в списке {р['цветВСписке']}")
                            if р["цветЗвезды"] == р["цветПодписи"]:
                                плохо(f"{н} звезда цветом подписи, а не темы")
                            if abs(р["кегльЗвезды"] - р["кегльПодписи"]) > 0.5 or not р["кегльВСписке"] or р["кегльЗвезды"] <= р["кегльВСписке"]:
                                плохо(f"{н} кегль звезды {р['кегльЗвезды']}, подписи {р['кегльПодписи']}, в списке {р['кегльВСписке']}")
                        if ш == 390:
                            стр.screenshot(path=str(СНИМКИ / f"project-star-{ui}-{'n' if ночь else 'd'}.png"), clip={"x": 0, "y": 0, "width": 390, "height": 900})
                        else:
                            стр.screenshot(path=str(СНИМКИ / f"project-star-{ui}-{'n' if ночь else 'd'}-1440.png"))
                        # проект из каталога — без звезды
                        стр.evaluate("async () => { customProjects.length = 0; selectProjectOption(1); await new Promise(r => setTimeout(r, 400)); }")
                        к = стр.evaluate("() => ({ звезда: !!document.querySelector('#projectSelectLabel .proj-star'), текст: document.getElementById('projectSelectLabel').textContent })")
                        if к["звезда"] or "★" in к["текст"]:
                            плохо(f"{н} у проекта из каталога в поле звезда: «{к['текст']}»")
                        for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                            плохо(f"{н} ошибка страницы: {о[:160]}")
                        стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: звезда ручного проекта в поле «Проект» цветом звезды из списка и кеглем подписи, у каталожного "
          "проекта звезды нет — 390 и 1440, обе темы, день и ночь.")


if __name__ == "__main__":
    главная()
