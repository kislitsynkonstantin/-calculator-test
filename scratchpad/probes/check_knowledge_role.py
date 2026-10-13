#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Роль «База знаний»: калькулятор по ней не открывается.

Константин 13.10.2026: «Не нужна роль РОП. Сделай роль «База знаний», чтобы
только к базе был доступ по ней. В калькулятор не войти по этой роли».

Данные калькулятора для роли закрыла сама база (запрещающие правила на
таблицах, проверено подстановкой сессий). Проба держит страницу:

  • сохранённый вход с ролью «База знаний» — выход, экран входа, спокойная
    плашка «открывает только базу знаний» со ссылкой на
    https://knowledge.baniamsk.ru новой вкладкой и rel="noopener";
    цены и пресеты не грузятся, профиль и пользователь сброшены;
  • вход через форму — то же; кнопка снова «Войти», устройство такой вход
    не запоминает (строки «повторного входа» с этим именем потом нет);
  • на тестовом адресе — та же плашка, а не «тестовая версия только для
    администраторов»: человеку говорится, куда идти;
  • другая сторона: менеджер входит как прежде — экран входа уходит, вход
    запомнен, плашки нет;
  • роль подписана в списке сотрудников и есть в выборе роли;
  • плашка не вылезает за лист на 390 и 1440 px днём и ночью, ссылку палец
    ловит в 12 px над и под серединой, а нарисована она строкой текста.

    python3 check_knowledge_role.py
"""
import functools
import json
import http.server
import mimetypes
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
ШРИФТЫ = (ЗДЕСЬ / "шрифты_google.css").read_text(encoding="utf-8")
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
        + (ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8") + ");")
НАХОДКИ, ОТЧЁТ = [], []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    класс = functools.partial(Тихий, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def факт(ок, где, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(f"[{где}] {т}")


# Роль, путь входа и счёт: сколько раз страница выходила и какие таблицы
# спрашивала. Путь «форма» — сессии нет, вход нажатием; как и в supabase-js,
# signInWithPassword дожидается обработчика SIGNED_IN и только потом отвечает:
# поэтому запись «кто входил» из loginSubmit идёт уже после калитки.
ОБВЯЗКА = """(([роль, путь]) => {
  window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, {
    profiles: [{ id: 'u-проба', email: 'probe@baniamsk.ru', role: роль, first_name: 'Ирина', last_name: 'Проба', app_settings: {} }] });
  window.__выходов = 0; window.__спрошено = [];
  const создать = window.supabase.createClient;
  window.supabase.createClient = function () {
    const к = создать.apply(this, arguments);
    const из = к.from;
    к.from = function (т) { window.__спрошено.push(т); return из.apply(this, arguments); };
    const выйти = к.auth.signOut;
    к.auth.signOut = function () { window.__выходов++; return выйти.apply(this, arguments); };
    if (путь === 'форма') {
      const сессия = { user: { id: 'u-проба', email: 'probe@baniamsk.ru' }, access_token: 'проба' };
      let слушатель = null;
      к.auth.getSession = () => Promise.resolve({ data: { session: null }, error: null });
      к.auth.onAuthStateChange = (ф) => { слушатель = ф; return { data: { subscription: { unsubscribe() {} } } }; };
      к.auth.signInWithPassword = async () => {
        if (слушатель) await слушатель('SIGNED_IN', сессия);
        return { data: { session: сессия, user: сессия.user }, error: null };
      };
    }
    return к;
  };
})"""

СОСТОЯНИЕ = """() => {
  const экран = document.getElementById('loginScreen'), н = document.getElementById('loginNote');
  const о = document.getElementById('loginError'), кн = document.getElementById('loginBtn');
  const виден = э => !!э && getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().height > 0;
  const а = н && н.querySelector('a');
  return {
    экран: виден(экран), плашка: виден(н) ? н.textContent : '', ошибка: виден(о) ? о.textContent : '',
    ссылка: а ? { href: а.getAttribute('href'), target: а.target, rel: а.rel } : null,
    кнопка: кн.textContent.trim(), ждёт: кн.classList.contains('wait'),
    повтор: экран.classList.contains('repeat'), память: localStorage.getItem('bm_last_login'),
    профиль: window._sbProfile ? window._sbProfile.role : null, пользователь: !!window._sbUser,
    выходов: window.__выходов, спрошено: window.__спрошено.slice(),
  };
}"""

ГЕОМ = """() => {
  const л = document.querySelector('#loginScreen .lg-paper').getBoundingClientRect();
  const н = document.getElementById('loginNote'), р = н.getBoundingClientRect();
  const а = н.querySelector('a');
  if (!а || getComputedStyle(н).display === 'none') return null;
  const б = а.getBoundingClientRect();
  const x = б.left + б.width / 2, y = б.top + б.height / 2;
  const ловит = [y - 12, y + 12].every(ty => { const э = document.elementFromPoint(x, ty); return э === а || а.contains(э); });
  return { внутри: р.left >= л.left - 0.5 && р.right <= л.right + 0.5, ссылкаВнутри: б.right <= р.right + 0.5 && б.left >= р.left - 0.5,
           высота: Math.round(б.height), ловит, вширь: document.documentElement.scrollWidth - document.documentElement.clientWidth };
}"""


def открыть(бр, адрес, роль, путь, ш=1440, в=900, ночь=False, память=None):
    к = бр.new_context(viewport={"width": ш, "height": в}, device_scale_factor=2 if ш == 1440 else 1,
                       color_scheme="dark" if ночь else "light")
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    if адрес.startswith("https://test."):
        def отдать(r):
            путь_ф = r.request.url.split("baniamsk.ru/", 1)[1].split("?")[0].split("#")[0] or "index.html"
            ф = КОРЕНЬ / путь_ф
            if not ф.is_file():
                return r.fulfill(status=404, body="")
            r.fulfill(status=200, body=ф.read_bytes(),
                      content_type=mimetypes.guess_type(str(ф))[0] or "application/octet-stream")
        стр.route("https://test.calculator.baniamsk.ru/**", отдать)
    if память:
        # Только в самой странице: сценарии запуска идут и во вложенных окнах, и
        # запись из них вернула бы память уже после калитки.
        стр.add_init_script(f"if (window === window.top) try {{ localStorage.setItem('bm_last_login', {json.dumps(память)}); }} catch (e) {{}}")
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.add_init_script(f"({ОБВЯЗКА})({json.dumps([роль, путь])})")
    стр.goto(адрес, wait_until="load")
    стр.wait_for_timeout(1800)
    return к, стр, ошибки


def ценовые(спрошено):
    return sorted({т for т in спрошено if т.startswith("pricing_") or т in ("presets", "preset_links", "shared_presets", "custom_projects", "products")})


def главная():
    с, порт = сервер()
    местный = f"http://127.0.0.1:{порт}/index.html"
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

        # ── сохранённый вход, роль «База знаний» ──
        где = "сессия · База знаний"
        к, стр, ош = открыть(бр, местный, "knowledge", "сессия",
                             память='{"email":"probe@baniamsk.ru","имя":"Ирина Проба"}')
        с_ = стр.evaluate(СОСТОЯНИЕ)
        факт(с_["экран"], где, f"экран входа стоит: {с_['экран']}")
        факт("только базу знаний" in с_["плашка"], где, f"плашка о базе знаний: «{с_['плашка'][:80]}»")
        факт(с_["ссылка"] == {"href": "https://knowledge.baniamsk.ru", "target": "_blank", "rel": "noopener"},
             где, f"ссылка на базу знаний новой вкладкой: {с_['ссылка']}")
        факт(с_["выходов"] >= 1 and not с_["пользователь"] and с_["профиль"] is None, где,
             f"вышел, пользователь и профиль сброшены: выходов {с_['выходов']}, пользователь {с_['пользователь']}, профиль {с_['профиль']}")
        факт(not ценовые(с_["спрошено"]), где, f"цены и пресеты не спрашивались: {ценовые(с_['спрошено'])}")
        факт(not с_["память"] and not с_["повтор"], где, f"устройство забыло вход: память {с_['память']!r}, повтор {с_['повтор']}")
        факт(not с_["ошибка"], где, f"красной ошибки нет: «{с_['ошибка']}»")
        факт(not ош, где, f"ошибок страницы нет: {ош[:2]}")
        к.close()

        # ── вход через форму, роль «База знаний» ──
        где = "форма · База знаний"
        к, стр, ош = открыть(бр, местный, "knowledge", "форма")
        стр.fill("#loginEmail", "probe@baniamsk.ru"); стр.fill("#loginPassword", "проба-пароль")
        стр.click("#loginBtn"); стр.wait_for_timeout(900)
        с_ = стр.evaluate(СОСТОЯНИЕ)
        факт(с_["экран"] and "только базу знаний" in с_["плашка"], где, f"экран входа и плашка: {с_['экран']}, «{с_['плашка'][:60]}»")
        факт(с_["кнопка"].lower() == "войти" and not с_["ждёт"], где, f"кнопка снова «Войти»: «{с_['кнопка']}», ждёт {с_['ждёт']}")
        факт(not с_["память"], где, f"вход не запомнен: {с_['память']!r}")
        факт(с_["выходов"] >= 1 and not ценовые(с_["спрошено"]), где, f"вышел, цен не спрашивал: {с_['выходов']}, {ценовые(с_['спрошено'])}")
        факт(not ош, где, f"ошибок страницы нет: {ош[:2]}")
        к.close()

        # ── тестовый адрес ──
        где = "тест · База знаний"
        к, стр, ош = открыть(бр, "https://test.calculator.baniamsk.ru/", "knowledge", "сессия")
        с_ = стр.evaluate(СОСТОЯНИЕ)
        контур = стр.evaluate("() => window.IS_TEST_DOMAIN")
        факт(контур, где, f"страница считает себя тестом: {контур}")
        факт("только базу знаний" in с_["плашка"] and "Тестовая версия" not in (с_["ошибка"] + с_["плашка"]), где,
             f"сказано про базу знаний, а не про тест: плашка «{с_['плашка'][:50]}», ошибка «{с_['ошибка'][:50]}»")
        факт(not ош, где, f"ошибок страницы нет: {ош[:2]}")
        к.close()

        # ── другая сторона: менеджер ──
        for путь in ("сессия", "форма"):
            где = f"{путь} · Менеджер"
            к, стр, ош = открыть(бр, местный, "manager", путь)
            if путь == "форма":
                стр.fill("#loginEmail", "probe@baniamsk.ru"); стр.fill("#loginPassword", "проба-пароль")
                стр.click("#loginBtn"); стр.wait_for_timeout(1500)
            с_ = стр.evaluate(СОСТОЯНИЕ)
            факт(not с_["экран"] and not с_["плашка"] and с_["выходов"] == 0, где,
                 f"калькулятор открылся: экран входа {с_['экран']}, плашка «{с_['плашка'][:40]}», выходов {с_['выходов']}")
            факт(с_["профиль"] == "manager" and "pricing_options" in с_["спрошено"], где,
                 f"профиль менеджера, цены спрошены: {с_['профиль']}, {'pricing_options' in с_['спрошено']}")
            факт(bool(с_["память"]) and "probe@baniamsk.ru" in с_["память"], где, f"вход запомнен: {с_['память']!r}")
            if путь == "сессия":
                роли = стр.evaluate("""() => {
                  const сп = document.createElement('div'); сп.id = 'employeesList'; document.body.appendChild(сп);
                  renderEmployees([{ id: 'x1', email: 'kb@baniamsk.ru', role: 'knowledge', first_name: 'Ирина', last_name: '' }]);
                  const з = сп.querySelector('[data-role="knowledge"]'), в = сп.querySelector('#rolesel_x1');
                  const код = [...document.scripts].map(с => с.textContent).join('\\n');
                  const р = { значок: з ? з.textContent.trim() : '', выбрано: в ? в.value : '',
                              приглашение: код.includes('<option value="knowledge">База знаний</option>') };
                  сп.remove(); return р; }""")
                факт(роли == {"значок": "База знаний", "выбрано": "knowledge", "приглашение": True}, где,
                     f"роль подписана в списке сотрудников и есть в приглашении: {роли}")
            факт(not ош, где, f"ошибок страницы нет: {ош[:2]}")
            к.close()

        # ── вид плашки ──
        for ш, в in ((390, 844), (1440, 900)):
            for ночь in (False, True):
                где = f"вид · {ш}px · {'ночь' if ночь else 'день'}"
                к, стр, ош = открыть(бр, местный, "knowledge", "сессия", ш, в, ночь)
                г = стр.evaluate(ГЕОМ)
                if г is None:
                    факт(False, где, "плашки со ссылкой на экране нет — мерить нечего")
                    к.close()
                    continue
                факт(г["внутри"] and г["ссылкаВнутри"] and г["вширь"] <= 0, где,
                     f"плашка и ссылка в пределах листа, вширь {г['вширь']}: {г['внутри']}, {г['ссылкаВнутри']}")
                факт(г["ловит"] and г["высота"] <= 22, где, f"ссылку ловит палец ±12 px, нарисована строкой {г['высота']} px: {г['ловит']}")
                стр.screenshot(path=str(ЗДЕСЬ / f"knowledge-role-{ш}-{'night' if ночь else 'day'}.png"))
                к.close()
        бр.close()
    с.shutdown()
    print("\n".join("    ок  " + т for т in ОТЧЁТ))
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print("  ✗", т)
        sys.exit(1)
    print("Чисто: роль «База знаний» выходит из калькулятора с плашкой и ссылкой на базу знаний, "
          "вход не запоминается, цены не грузятся; менеджер входит как прежде.")


if __name__ == "__main__":
    главная()
