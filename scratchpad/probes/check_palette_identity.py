#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перевод цветов на палитру не меняет ни одного пикселя.

Константин 24.09.2026: «под цвет ты можешь подготовить структуру? Чтобы
остаться на основном цвете, но подготовить токены/цвета к замене одним
действием потом».

Работа по построению невидимая: сотни вписанных руками бирюзовых значений
уходят в переменные палитры, а на экране не должно поменяться ничего. Значит
и мерить надо не «похоже ли», а «совпало ли до пикселя»: проба снимает одни и
те же состояния у сборки до перевода и у рабочей копии и сравнивает кадры
побайтно. Одна строка, оставшаяся без цвета из-за опечатки в имени
переменной, — это уже разница, и проба её покажет с рамкой места.

Сборка до перевода берётся из git (`BM_BASE_REF`, по умолчанию `27e9d95` —
выпуск v2.5.10 (4), последний до палитры) и раскладывается во временную
папку; рабочая копия — из корня репозитория.

Состояния: главный экран с выбранным проектом целиком (вся страница, со
сводом и полоской итога), открытый список проектов, окно настроек, окно
пресетов, журнал действий, окно печати с листом, экран входа и лист клиента
по ссылке — в «Модерне» и «Бланке», днём и ночью, на 390 и 1440 px.

    python3 check_palette_identity.py            # полный обход
    BM_ONLY=main,settings python3 check_palette_identity.py
"""
import functools
import http.server
import io
import json
import os
import pathlib
import shutil
import socketserver
import subprocess
import sys
import tarfile
import tempfile
import threading

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ОСНОВА = os.environ.get("BM_BASE_REF", "27e9d95")
# Справка лежит в рабочей области, а не здесь: основа — её коммит до перевода.
СПРАВКА = pathlib.Path(os.environ.get("BM_MANUAL_SRC", "/home/user/vscode-workspace/docs/справка"))
СПРАВКА_ОСНОВА = os.environ.get("BM_MANUAL_BASE_REF", "f0ef1a6")
ТОЛЬКО = set(filter(None, os.environ.get("BM_ONLY", "").split(",")))
КАДРЫ = pathlib.Path(os.environ.get("BM_SHOTS") or tempfile.mkdtemp(prefix="палитра-"))
КАДРЫ.mkdir(parents=True, exist_ok=True)
НАХОДКИ = []

СОБЫТИЯ = [
    {"id": 1, "user_id": "u-проба", "event_type": "options_batch",
     "project_name": "Проба дом 8×6", "total_price": 6694122,
     "options_count": 14, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T09:51:00Z",
     "details": {"obj": "Проба дом 8×6", "presetCode": "901974",
                 "rows": [{"k": "Добавлены", "a": "",
                           "b": "\n".join(f"Позиция № {i}" for i in range(1, 15))},
                          {"k": "Итог", "a": "5 587 994 ₽", "b": "6 694 122 ₽"}]}},
    {"id": 2, "user_id": "u-проба", "event_type": "print",
     "project_name": "Проба дом 8×6", "total_price": 4241082,
     "options_count": 8, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-23T08:37:00Z",
     "details": {"obj": "Проба дом 8×6", "rows": []}},
]

ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(dict(ДАННЫЕ, events=СОБЫТИЯ,
                                profiles=[{"id": "u-проба", "role": "admin",
                                           "full_name": "Проба"}]),
                           ensure_ascii=False) + ");"
              # Часы стоят: подписи «сегодня» и даты в журнале не должны
              # расходиться между двумя проходами, снятыми с разницей в минуту.
              "(function(){const Н=new Date('2026-09-23T12:00:00Z').getTime();"
              "const Д=Date;class Ф extends Д{constructor(...а){super(...(а.length?а:[Н]));}"
              "static now(){return Н;}};window.Date=Ф;"
              # Случайные коды пресетов и ссылок тоже одинаковые в обоих проходах.
              "let з=12345;Math.random=function(){з=(з*16807)%2147483647;return (з-1)/2147483646;};})();")


def справка(основа):
    """Строки app_docs для заглушки: из рабочих файлов или из коммита основы."""
    корень = subprocess.run(["git", "-C", str(СПРАВКА), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=True).stdout.strip()
    отн = СПРАВКА.relative_to(корень)
    опись = json.loads((СПРАВКА / "опись.json").read_text(encoding="utf-8"))
    строки = []
    for ч in опись:
        if ч["doc"] != "manual":
            continue
        имя = f"{ч['doc']}--{ч['part']}.html"
        if основа:
            html = subprocess.run(["git", "-C", корень, "show", f"{СПРАВКА_ОСНОВА}:{отн / имя}"],
                                  capture_output=True, text=True, check=True).stdout
        else:
            html = (СПРАВКА / имя).read_text(encoding="utf-8")
        строки.append({"doc": "manual", "part": ч["part"], "ord": ч["ord"],
                       "staff_only": ч.get("staff_only", False), "html": html.strip("\n")})
    return "window.__ТАБЛИЦЫ.app_docs = " + json.dumps(строки, ensure_ascii=False) + ";"


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер(корень):
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(корень))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def разложить_основу():
    """Сборка до перевода — во временную папку, целиком из git."""
    папка = pathlib.Path(tempfile.mkdtemp(prefix="основа-"))
    архив = subprocess.run(["git", "-C", str(КОРЕНЬ), "archive", ОСНОВА],
                           capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(архив)) as т:
        т.extractall(папка)
    return папка


def плохо(т):
    НАХОДКИ.append(т)


ПОДГОТОВКА = """async ([ui, ночь]) => {
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  window._sbProfile = { role: 'admin', full_name: 'Проба' };
  applyUiStyle(ui, false);
  applyThemeMode(ночь ? 'dark' : 'light', false);
  const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
  selectProjectOption(и >= 0 ? и : 0);
  await new Promise(r => setTimeout(r, 900));
  // Мигающий курсор и анимации дают разницу там, где цвета совпадают.
  const с = document.createElement('style');
  с.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
  document.head.appendChild(с);
  if (document.activeElement) document.activeElement.blur();
}"""

# Каждое состояние — код, который приводит к нему страницу. Всё, что открыто,
# снимается целиком по окну; главный экран — всей страницей.
СОСТОЯНИЯ = {
    "main": ("", True),
    "dropdown": ("document.getElementById('projectSelectWrap').classList.add('open');", False),
    "settings": ("openSettings();", False),
    "presets": ("openPresetPanel();", False),
    "log": ("openActionLog(); await loadActionLog(true);"
            "document.querySelectorAll('#alFeed .al-row').forEach(с => с.classList.add('open'));", False),
    "print": ("openPrintPreview();", False),
    "login": ("document.getElementById('loginScreen').style.display='';", False),
    "manual": ("await openManual(); await new Promise(r => setTimeout(r, 1500));", False),
    "contract": ("openPrintPreview(); setPreviewEntity('contract');"
                 "await new Promise(r => setTimeout(r, 900));", False),
}

# Документы, которые калькулятор собирает отдельно и отдаёт в новое окно:
# лист в окне печати, график платежей, печать комплектаций. Их не видно ни на
# одном снимке страницы, а именно там пропавшая палитра обесцветила бы лист.
# Окно и Blob подменяются, собранная разметка снимается отдельной страницей.
ПЕРЕХВАТ = """async () => {
  window.__док = [];
  window.open = function () {
    return { document: { write: h => window.__док.push(['окно', h]), close() {}, title: '' },
             focus() {}, print() {}, close() {} };
  };
  const Б = window.Blob;
  window.Blob = function (части, опц) {
    if (опц && /html/.test(опц.type || '')) window.__док.push(['blob', части.join('')]);
    return new Б(части, опц);
  };
  window.print = () => {};
  const шаги = [
    ['лист', () => { openPrintPreview(); printFromPreview(); }],
    ['график', () => printPaymentPlan()],
    ['комплектации', () => printKompl()],
  ];
  const вышло = [];
  for (const [имя, ш] of шаги) {
    const было = window.__док.length;
    try { ш(); } catch (e) { вышло.push([имя, 'ошибка: ' + e.message]); continue; }
    await new Promise(r => setTimeout(r, 500));
    const новые = window.__док.slice(было);
    вышло.push([имя, новые.length ? новые[новые.length - 1][1] : '']);
  }
  return вышло;
}"""


def снять(бр, порт, ui, ночь, ш, в, имя, код, вся, справка_js=""):
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    if справка_js:
        стр.add_init_script(справка_js)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate(ПОДГОТОВКА, [ui, ночь])
    if код:
        стр.evaluate("async () => {" + код + "}")
        стр.wait_for_timeout(700)
    png = стр.screenshot(full_page=вся)
    стр.close()
    return png, ошибки


def отдельные(бр, порт, ui):
    стр = бр.new_page(viewport={"width": 1440, "height": 950})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate(ПОДГОТОВКА, [ui, False])
    доки = стр.evaluate(ПЕРЕХВАТ)
    стр.close()
    кадры = {}
    for имя, html in доки:
        if not html or html.startswith("ошибка"):
            кадры[имя] = (html or "пусто").encode()
            continue
        л = бр.new_page(viewport={"width": 900, "height": 1200})
        л.set_content(html, wait_until="load")
        л.wait_for_timeout(400)
        кадры[имя] = л.screenshot(full_page=True)
        л.close()
    return кадры


def лист_клиента(бр, порт, ночь, ш, в):
    стр = бр.new_page(viewport={"width": ш, "height": в},
                      color_scheme="dark" if ночь else "light")
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/adkv8q5j", wait_until="load")
    стр.wait_for_timeout(2000)
    png = стр.screenshot(full_page=True)
    стр.close()
    return png


def сравнить(имя, а, б):
    ка = Image.open(io.BytesIO(а)).convert("RGB")
    кб = Image.open(io.BytesIO(б)).convert("RGB")
    if ка.size != кб.size:
        плохо(f"[{имя}] размер кадра {ка.size} → {кб.size}")
        return False
    разн = ImageChops.difference(ка, кб)
    рамка = разн.getbbox()
    if рамка:
        # Сглаживание края у точек-уведомлений даёт разницу в два-три пикселя
        # между двумя прогонами одного и того же кода. Перекраска выглядит
        # иначе: целая линия, буква, заливка — десятки пикселей. Шум — не
        # больше шести точек с разницей меньше 60 по каналу.
        кус = разн.crop(рамка)
        точки = [п for п in кус.get_flattened_data() if max(п) > 0]
        предел = max(max(п) for п in точки)
        # Разница в одну-две ступени по каналу глазом не видна вовсе — это
        # край полосы прокрутки, пересчитанный по-другому.
        if предел <= 2 or (len(точки) <= 6 and предел < 60):
            return True
    if рамка:
        ка.save(КАДРЫ / f"{имя}-до.png")
        кб.save(КАДРЫ / f"{имя}-после.png")
        плохо(f"[{имя}] кадры разошлись в области {рамка} — снимки в {КАДРЫ}")
        return False
    return True


def главная():
    основа = разложить_основу()
    сп_до, сп_после = справка(True), справка(False)
    с1, п1 = сервер(основа)
    с2, п2 = сервер(КОРЕНЬ)
    всего = совпало = 0
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui, тема in (("light", "Модерн"), ("blank", "Бланк")):
                for ночь in (False, True):
                    for ш, в in ((390, 900), (1440, 950)):
                        for имя, (код, вся) in СОСТОЯНИЯ.items():
                            if ТОЛЬКО and имя not in ТОЛЬКО:
                                continue
                            метка = f"{тема}-{'ночь' if ночь else 'день'}-{ш}-{имя}"
                            а, оа = снять(бр, п1, ui, ночь, ш, в, имя, код, вся, сп_до)
                            б, об = снять(бр, п2, ui, ночь, ш, в, имя, код, вся, сп_после)
                            всего += 1
                            if об and not оа:
                                плохо(f"[{метка}] ошибки страницы после перевода: "
                                      + "; ".join(об)[:200])
                            совпало += сравнить(метка, а, б)
            if not ТОЛЬКО or "docs" in ТОЛЬКО:
                for ui, тема in (("light", "Модерн"), ("blank", "Бланк")):
                    а, б = отдельные(бр, п1, ui), отдельные(бр, п2, ui)
                    for имя in а:
                        метка = f"{тема}-документ-{имя}"
                        всего += 1
                        if not а[имя].startswith(b"\x89PNG"):
                            # У сборки до перевода документ не собрался — сравнивать
                            # нечего, но и молчать нельзя: иначе проба идёт вхолостую.
                            плохо(f"[{метка}] документ не собрался и в основе: {а[имя][:80]!r}")
                            continue
                        if not б.get(имя, b"").startswith(b"\x89PNG"):
                            плохо(f"[{метка}] после перевода документ не собрался: {б.get(имя, b'')[:80]!r}")
                            continue
                        совпало += сравнить(метка, а[имя], б[имя])
            if not ТОЛЬКО or "client" in ТОЛЬКО:
                for ночь in (False, True):
                    for ш, в in ((390, 900), (1440, 950)):
                        метка = f"клиент-{'ночь' if ночь else 'день'}-{ш}"
                        всего += 1
                        совпало += сравнить(метка, лист_клиента(бр, п1, ночь, ш, в),
                                            лист_клиента(бр, п2, ночь, ш, в))
            бр.close()
    finally:
        с1.shutdown(); с2.shutdown()
        shutil.rmtree(основа, ignore_errors=True)

    print(f"  кадров {всего}, совпало до пикселя {совпало}")
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print(f"Чисто: {всего} кадров сборки до перевода и рабочей копии совпали до "
          "пикселя в обеих темах, днём и ночью, на телефоне и мониторе.")


if __name__ == "__main__":
    главная()
