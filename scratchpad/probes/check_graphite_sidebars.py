#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Зелёный-графит»: боковое меню справки и базы знаний — графит.

Константин 25.09.2026, снимками справки и базы знаний: «в базе и
руководстве вот это сделай графит в теме „Зелёный-графит“». Цвет меню —
решение тона, а не поворот цвета, поэтому оно держится за признак тона:

  • справка: калькулятор собирает её через сПалитрой(); при «Зелёном-
    графите» у корня документа стоит data-tone="bmsk", и меню .sb — #24271f;
    при бирюзе признака нет и меню прежнее, при «Синем» — не графит;
  • на графите зелёным — заголовки групп и выбранный пункт (вариант 03
    макета sidebar-green-v1: «вот так давай»), в других тонах — нет;
  • база знаний: сообщение тона несёт имя; при bmsk меню графитовое, при
    другом имени и при старом сообщении без имени — нет;
  • калькулятор шлёт имя тона в обоих местах, где отправляет тон базе.

Оболочку справки берёт из рабочей области (BM_MANUAL), базу — из её
репозитория (BM_KB); если их нет рядом, соответствующая часть пропускается
со словами.

    python3 check_graphite_sidebars.py
"""
import functools, http.server, json, os, pathlib, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
СПРАВКА = pathlib.Path(os.environ.get("BM_MANUAL") or "/home/user/vscode-workspace/docs/справка/manual--shell.html")
БАЗА = pathlib.Path(os.environ.get("BM_KB") or "/home/user/knowledge-baniamsk")
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
ГРАФИТ = "rgb(36, 39, 31)"
# Вариант 03 макета sidebar-green-v1: заголовки групп #8bc34a, выбранный пункт #a6d474.
ЗЕЛ, ЗЕЛ2 = "rgb(139, 195, 74)", "rgb(166, 212, 116)"
НАХОДКИ = []


def плохо(где, т):
    НАХОДКИ.append(f"{где}: {т}")


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер(папка):
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(папка)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def справка(бр, порт):
    if not СПРАВКА.exists():
        print("  справка: оболочки рядом нет — часть пропущена"); return
    оболочка = СПРАВКА.read_text(encoding="utf-8")
    к = бр.new_context(viewport={"width": 1440, "height": 900})
    стр = к.new_page()
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    for тон, ждём in (("bmsk", True), ("teal", False), ("sky", False)):
        з = стр.evaluate("""async ([тон, html]) => {
          applyTone(тон, false);
          const собрано = сПалитрой(html);
          const ф = document.createElement('iframe'); ф.style.cssText = 'width:1000px;height:600px';
          document.body.appendChild(ф);
          await new Promise(r => { ф.onload = r; ф.srcdoc = собрано; });
          const sb = ф.contentDocument.querySelector('.sb');
          const гр = ф.contentDocument.querySelector('.sb-group');
          const пн = ф.contentDocument.querySelector('.sb-a'); пн.classList.add('on');
          await new Promise(r => setTimeout(r, 300));  // у пункта цвет меняется с переходом 0,1 с
          const итог = { признак: ф.contentDocument.documentElement.getAttribute('data-tone') || '',
                         фон: sb ? getComputedStyle(sb).backgroundColor : '',
                         группа: getComputedStyle(гр).color, выбран: getComputedStyle(пн).color };
          ф.remove(); return итог;
        }""", [тон, оболочка])
        где = f"справка · {тон}"
        if (з["фон"] == ГРАФИТ) != ждём:
            плохо(где, f"меню {з['фон']}, графит ждали: {ждём}")
        if ждём and (з["группа"] != ЗЕЛ or з["выбран"] != ЗЕЛ2):
            плохо(где, f"зелёные акценты: группа {з['группа']}, выбранный {з['выбран']}")
        if not ждём and ЗЕЛ in (з["группа"], з["выбран"]):
            плохо(где, "зелёные акценты графита протекли в другой тон")
        if ждём and з["признак"] != "bmsk":
            плохо(где, f"признак тона у корня {з['признак']!r}")
        if тон == "teal" and з["признак"]:
            плохо(где, f"у бирюзы появился признак тона {з['признак']!r}")
        print(f"  {где}: признак {з['признак'] or '—'}, меню {з['фон']}")
    исходник = (КОРЕНЬ / "index.html").read_text(encoding="utf-8")
    отправки = re.findall(r"postMessage\(\{ type: 'tone'[^}]*\}", исходник)
    if len(отправки) < 2 or not all("name:" in о for о in отправки):
        плохо("калькулятор", f"не во всех сообщениях тона базе есть имя: {len(отправки)} отправок")
    к.close()


def база(бр):
    if not (БАЗА / "index.html").exists():
        print("  база знаний: репозитория рядом нет — часть пропущена"); return
    с, порт = сервер(БАЗА)
    try:
        к = бр.new_context(viewport={"width": 1440, "height": 900})
        стр = к.new_page()
        # Библиотека Supabase в контейнере не грузится; без неё сценарий базы
        # обрывается раньше, чем подписывается на сообщения. Та же заглушка,
        # что у калькулятора.
        стр.add_init_script(ЗАГЛУШКА)
        # Два блока и три урока — чтобы в меню были заголовки блоков и пункты:
        # без них проверять зелёные акценты не на чем.
        стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps({
            "kb_blocks": [{"id": "b1", "num": 1, "ord": 1, "name_ru": "Компания", "name_en": "Company", "sub_ru": "", "sub_en": ""},
                          {"id": "b3", "num": 3, "ord": 3, "name_ru": "Продажи", "name_en": "Sales", "sub_ru": "", "sub_en": ""}],
            "kb_lessons": [{"id": f"lesson-{к}", "block": int(к[0]), "ord": int(к[2:]), "status": "ready", "title_ru": н, "title_en": н,
                            "nav_ru": н, "nav_en": н, "sub_ru": "", "sub_en": "", "body_html": f'<div class="lesson" id="lesson-{к}"></div>'}
                           for к, н in (("1-1", "Кто такая Баня-МСК"), ("1-3", "Что мы строим"), ("3-1", "Как устроены продажи"))]},
            ensure_ascii=False) + ");")
        стр.goto(f"http://127.0.0.1:{порт}/index.html?embed=1", wait_until="load")
        стр.wait_for_timeout(1500)
        for имя, ждём in (("bmsk", True), ("sky", False), (None, False), ("bmsk", True), ("", False)):
            стр.evaluate("""(имя) => {
              const d = { type: 'tone', shift: 0, sat: 1 }; if (имя !== null) d.name = имя;
              window.dispatchEvent(new MessageEvent('message', { data: d, origin: 'https://test.calculator.baniamsk.ru' }));
            }""", имя)
            стр.wait_for_timeout(150)
            фон = стр.evaluate("() => getComputedStyle(document.getElementById('sidebar')).backgroundColor")
            стр.wait_for_timeout(250)
            гр = стр.evaluate("() => { const g = document.querySelector('#sidebar .sb-group'); return g ? getComputedStyle(g).color : ''; }")
            if not гр:
                плохо(f"база знаний · имя {имя!r}", "в меню нет заголовков блоков — зелёные акценты не проверены")
            где = f"база знаний · имя {имя!r}"
            if (фон == ГРАФИТ) != ждём:
                плохо(где, f"меню {фон}, графит ждали: {ждём}")
            if гр and (гр == ЗЕЛ) != ждём:
                плохо(где, f"заголовок блока {гр}, зелёный ждали: {ждём}")
            print(f"  {где}: меню {фон}")
        # Чужой источник сообщения не красит.
        стр.evaluate("""() => window.dispatchEvent(new MessageEvent('message',
          { data: { type: 'tone', shift: 0, sat: 1, name: 'bmsk' }, origin: 'https://evil.example' }))""")
        стр.wait_for_timeout(150)
        if стр.evaluate("() => getComputedStyle(document.getElementById('sidebar')).backgroundColor") == ГРАФИТ:
            плохо("база знаний", "сообщение с чужого источника перекрасило меню")
        к.close()
    finally:
        с.shutdown()


def главная():
    с, порт = сервер(КОРЕНЬ)
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for часть in (lambda: справка(бр, порт), lambda: база(бр)):
                try:
                    часть()
                except Exception as e:
                    плохо("проба", f"оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: при «Зелёном-графите» боковое меню справки и базы знаний графитовое, "
          "в остальных тонах прежнее; имя тона уходит базе в обоих местах.")


if __name__ == "__main__":
    главная()
