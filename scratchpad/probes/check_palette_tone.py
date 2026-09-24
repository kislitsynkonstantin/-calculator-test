#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цвет оформления: бирюзовый по умолчанию, синий — выбором в настройках.

Константин 24.09.2026: «переключатель конечно в настройках, по умолчанию
также стоит бирюза». Проба меряет отрисованное, а не разметку, в обеих темах
оформления, днём и ночью, на 390 и 1440 px:

  • без выбора — бирюза: признака тона нет, акцент бирюзовый, логотип в шапке
    и на экране входа — основной, значки — основные;
  • в настройках строка «Цвет оформления» с двумя кнопками, отмечена
    «Бирюзовый»; кнопки не вылезают за строку;
  • «Синий» — акцент синий в самой странице, логотип в шапке и на входе —
    синий (картинка тона, а не основная), значок вкладки и приложения —
    синие; выбор ушёл в профиль аккаунта (app_settings.tone);
  • документ, собранный отдельно (печать, договор, справка — через
    сПалитрой), тоже синий и с синим логотипом; лист печати в самой
    странице — с синим логотипом;
  • снимок для ссылки клиенту несёт тон, а лист клиента по такому снимку
    встаёт синим, и его синий логотип-файл действительно грузится;
  • «Бирюзовый» возвращает всё байт в байт: адреса значков, логотипы, цвет.

    python3 check_palette_tone.py
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
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              # Строка профиля, куда ложится сохранённая настройка аккаунта.
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []
КОД = "abcd2345"


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(где, т):
    НАХОДКИ.append(f"[{где}] {т}")


def синий(rgb):
    """Синий — канал B заметно больше G; бирюза — G и B почти равны."""
    import re
    ч = [int(x) for x in re.findall(r"\d+", rgb)[:3]]
    return len(ч) == 3 and ч[2] - ч[1] > 25


ЗАМЕР = """() => {
  const к = document.createElement('i'); к.style.color = 'var(--br-38)'; document.body.appendChild(к);
  const акцент = getComputedStyle(к).color; к.remove();
  const шапка = document.getElementById('headerLogo'), вход = document.getElementById('loginLogo');
  const основы = [_LOGO_DARK, _LOGO_LIGHT];
  return {
    признак: document.documentElement.dataset.tone || '',
    акцент,
    шапкаОснова: основы.includes(шапка.getAttribute('src')),
    входОснова: основы.includes(вход.getAttribute('src')),
    значок: document.querySelector('link[rel="icon"]').getAttribute('href'),
    прил: document.querySelector('link[rel="apple-touch-icon"]').getAttribute('href'),
    профиль: ((window.__ТАБЛИЦЫ.profiles || []).find(p => p.id === 'u-проба') || {}).app_settings || null,
  };
}"""

ДОКУМЕНТ = """async () => {
  // Отдельный документ — как печать и договор: через сПалитрой, в кадре.
  const ф = document.createElement('iframe'); document.body.appendChild(ф);
  ф.srcdoc = сПалитрой('<!doctype html><html><head></head><body><i id="к" style="color:var(--br-38)">к</i>'
    + '<img id="л" src="' + _LOGO_DARK + '"></body></html>');
  await new Promise(r => ф.onload = r);
  const д = ф.contentDocument;
  const итог = { акцент: getComputedStyle(д.getElementById('к')).color,
                 логотипОснова: д.getElementById('л').getAttribute('src') === _LOGO_DARK };
  ф.remove();
  // Лист печати в самой странице.
  try { buildPrintDoc(); } catch (e) {}
  const лп = [...document.querySelectorAll('img[alt="Баня-МСК"]')].map(и => и.getAttribute('src'));
  итог.печатьОснова = лп.some(с => с === _LOGO_DARK);
  итог.печатьЕсть = лп.length;
  итог.снимокТон = (window._снимокКлиента || {}).тон || '';
  итог.снимок = window._снимокКлиента || null;
  return итог;
}"""


def открыть(бр, порт, ш, в, бланк, ночь):
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""([бланк, ночь]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
      selectProjectOption(0);
    }""", [бланк, ночь])
    стр.wait_for_timeout(600)
    return к, стр, ошибки


def лист_клиента(бр, порт, снимок, ночь):
    с404 = (КОРЕНЬ / "404.html").read_text(encoding="utf-8")
    ответ = {"status": "ok", "snapshot_at": "2026-09-24T09:00:00+00:00", "price_until": None, "snapshot": снимок}
    к = бр.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark" if ночь else "light")
    к.route(f"http://127.0.0.1:{порт}/{КОД}*",
            lambda м: м.fulfill(status=200, content_type="text/html; charset=utf-8", body=с404))
    к.route("**/rest/v1/rpc/**",
            lambda м: м.fulfill(status=200, content_type="application/json",
                                body=json.dumps(ответ if м.request.url.endswith("client_link_get") else {"status": "ok"})))
    стр = к.new_page()
    стр.goto(f"http://127.0.0.1:{порт}/{КОД}", wait_until="load")
    стр.wait_for_timeout(1500)
    итог = стр.evaluate("""() => {
      const к = document.createElement('i'); к.style.color = 'var(--br-38)'; document.body.appendChild(к);
      const акцент = getComputedStyle(к).color; к.remove();
      const лого = [...document.querySelectorAll('img.cl-logo, img.bl-logo-doc')];
      return { признак: document.documentElement.getAttribute('data-tone') || '', акцент,
               адреса: лого.map(и => и.getAttribute('src')),
               загружены: лого.filter(и => getComputedStyle(и).display !== 'none').every(и => и.complete && и.naturalWidth > 0) };
    }""")
    к.close()
    return итог


def проверить(бр, порт, ш, в, бланк, ночь):
    где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь)
    до = стр.evaluate(ЗАМЕР)
    if до["признак"] or синий(до["акцент"]) or not до["шапкаОснова"] or not до["входОснова"]:
        плохо(где, f"без выбора не бирюза: {до['признак']!r}, акцент {до['акцент']}, "
                   f"шапка основная {до['шапкаОснова']}, вход основной {до['входОснова']}")
    # ── строка в настройках ──
    стр.evaluate("() => { openSettings && openSettings(); }")
    стр.wait_for_timeout(400)
    строка = стр.evaluate("""() => {
      const кн = [...document.querySelectorAll('.st-tone-btn')];
      if (!кн.length) return null;
      const ряд = кн[0].closest('.st-row').getBoundingClientRect();
      return { подписи: кн.map(к => к.textContent.trim()), отмечена: кн.filter(к => к.classList.contains('active')).map(к => к.textContent.trim()),
               внутри: кн.every(к => { const б = к.getBoundingClientRect(); return б.left >= ряд.left - 0.5 && б.right <= ряд.right + 0.5; }) };
    }""")
    if not строка:
        плохо(где, "в настройках нет строки «Цвет оформления»")
    else:
        if строка["подписи"] != ["Бирюзовый", "Синий"] or строка["отмечена"] != ["Бирюзовый"]:
            плохо(где, f"кнопки цвета: {строка}")
        if not строка["внутри"]:
            плохо(где, "кнопки цвета вылезают за строку настроек")
        стр.click(".st-tone-btn[data-tone='blue']")
        стр.wait_for_timeout(400)
    после = стр.evaluate(ЗАМЕР)
    if после["признак"] != "blue" or not синий(после["акцент"]):
        плохо(где, f"«Синий» не перекрасил страницу: признак {после['признак']!r}, акцент {после['акцент']}")
    if после["шапкаОснова"] or после["входОснова"]:
        плохо(где, "при синем логотип в шапке или на входе остался бирюзовым")
    if после["значок"] == до["значок"] or после["прил"] == до["прил"]:
        плохо(где, "при синем значок вкладки или приложения остался бирюзовым")
    if not после["профиль"] or после["профиль"].get("tone") != "blue":
        плохо(где, f"выбор не ушёл в профиль аккаунта: {после['профиль'] and после['профиль'].get('tone')!r}")
    д = стр.evaluate(ДОКУМЕНТ)
    if not синий(д["акцент"]) or д["логотипОснова"]:
        плохо(где, f"отдельный документ не синий: акцент {д['акцент']}, логотип основной {д['логотипОснова']}")
    if д["печатьОснова"]:
        плохо(где, "лист печати в странице — с бирюзовым логотипом")
    if д["снимокТон"] != "blue":
        плохо(где, f"снимок для ссылки не несёт тон: {д['снимокТон']!r}")
    if ш == 390 and д["снимок"]:
        кл = лист_клиента(бр, порт, д["снимок"], ночь)
        if кл["признак"] != "blue" or not синий(кл["акцент"]):
            плохо(где, f"лист клиента по синему снимку не синий: {кл}")
        if not all("-blue.png" in а for а in кл["адреса"]) or not кл["загружены"]:
            плохо(где, f"логотип на листе клиента не синий или не загрузился: {кл['адреса']}, загружены {кл['загружены']}")
    # ── обратно ──
    стр.evaluate("() => applyTone('teal')")
    стр.wait_for_timeout(300)
    назад = стр.evaluate(ЗАМЕР)
    for ключ in ("признак", "акцент", "шапкаОснова", "входОснова", "значок", "прил"):
        if назад[ключ] != до[ключ]:
            плохо(где, f"«Бирюзовый» не вернул {ключ}: было {str(до[ключ])[:60]}, стало {str(назад[ключ])[:60]}")
    д2 = стр.evaluate(ДОКУМЕНТ)
    if синий(д2["акцент"]) or not д2["логотипОснова"] or д2["снимокТон"]:
        плохо(где, "после возврата к бирюзе документ или снимок остались синими")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()
    print(f"  {где}: бирюза {до['акцент']} → синий {после['акцент']}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 844), (1440, 900)):
                        try:
                            проверить(бр, порт, ш, в, бланк, ночь)
                        except Exception as e:
                            плохо(f"{бланк}/{ночь}/{ш}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: по умолчанию бирюза; «Синий» в настройках перекрашивает страницу, логотипы, "
          "значки, отдельные документы и лист клиента и уходит в аккаунт; «Бирюзовый» "
          "возвращает всё как было.")


if __name__ == "__main__":
    главная()
