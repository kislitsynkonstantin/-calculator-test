#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: код расчёта стоит в строке журнала событий.

Константин 19.09.2026: «так как у каждого пресета теперь есть номер, где-то тут
в журнале событий аккуратно пиши этот код. Можно будет подглядывать за
расчётами менеджеров».

Держатся три вещи:
  • строка события с кодом показывает его в серой подписи, группами по три
    знака — так его переписывают и диктуют;
  • набран он как всё вокруг: тем же шрифтом, цветом, кеглем и весом, что
    строка с названием пресета. Выделять его не просили — просили обратное:
    «в целом, подумал: не надо выделять» (19.09.2026);
  • двойное нажатие мышью и два касания пальцем кладут в буфер одни цифры,
    без слова «код» и без пробела: их вставляют в поиск пресетов. Одиночное
    нажатие не копирует;
  • строка без кода остаётся как была: у старых записей его нет вовсе, и
    пустого «код» в журнале быть не должно;
  • само событие уносит код в базу — и у своего пресета, и у расчёта,
    открытого по коду: иначе в журнале ему взяться неоткуда.

Отдельно проверяется отказ базы при правке чужого расчёта. Он уходил в консоль
браузера и человеку не показывался: правка видна на экране, а в базу не
принята — и это выглядит как сохранённая. Теперь об отказе говорят словами.

    python3 check_log_code.py
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
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

СОБЫТИЯ = [
    {"id": 1, "user_id": "u-проба", "event_type": "preset_saved",
     "project_name": "Фахверковая баня «Берлин» 9×5", "total_price": 6386520,
     "options_count": 12, "thickness": 150, "discount": 3, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-19T12:28:00Z",
     "details": {"obj": "Антон · Фахверковая баня «Берлин» 8×6 · 18.09.26",
                 "preset": "Антон · Фахверковая баня «Берлин» 8×6 · 18.09.26",
                 "presetCode": "386520", "rows": []}},
    {"id": 2, "user_id": "u-проба", "event_type": "print",
     "project_name": "Фахверковая баня «Магдебург» 6×6", "total_price": 4241082,
     "options_count": 8, "thickness": 150, "discount": 0, "cash_discount": False,
     "checked_options": {}, "created_at": "2026-09-19T12:37:00Z",
     "details": {"obj": "Фахверковая баня «Магдебург» 6×6", "rows": []}},
]

ТАБЛИЦЫ = {
    "events": СОБЫТИЯ,
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
    "preset_links": [], "presets": [],
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
}


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 390, "height": 900})
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' }; });")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)

            # ── строка журнала ──
            м = стр.evaluate("""async () => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              _sbProfile = { role: 'admin', full_name: 'Проба' };
              await loadActionLog(true);
              await new Promise(r => setTimeout(r, 500));
              const строки = [...document.querySelectorAll('#alFeed .al-i, #alFeed .al-item, #alFeed > div')]
                .filter(э => э.querySelector('.al-ctx') || э.querySelector('.al-code'));
              const коды = [...document.querySelectorAll('#alFeed .al-code')].map(э => ({
                текст: э.textContent.trim(),
                вПодписи: !!э.closest('.al-ctx'),
                цвет: getComputedStyle(э).color,
              }));
              return { коды, лента: document.getElementById('alFeed').innerText };
            }""")
            if м is None:
                плохо("журнал не открылся")
            else:
                if len(м["коды"]) != 1:
                    плохо(f"кодов в журнале {len(м['коды'])}, а событие с кодом одно — "
                          "у записи без кода его быть не должно")
                if м["коды"]:
                    к = м["коды"][0]
                    if к["текст"] != "код 386 520":
                        плохо(f"код в журнале подписан не так: «{к['текст']}» — "
                              "ждали «код 386 520»: без слова шесть цифр с пробелом "
                              "читаются второй суммой рядом с итогом")
                    if not к["вПодписи"]:
                        плохо("код вынесен из серой подписи события — он там последним и тише соседей")
                if "код 386 520" not in (м["лента"] or ""):
                    плохо("кода не видно в тексте журнала")

            for тема in ('модерн', 'бланк'):
                стр.evaluate("(т) => document.body.classList.toggle('ui-blank', т === 'бланк')", тема)
                стр.wait_for_timeout(250)
                try:
                    стр.evaluate("""() => {
                      const о = document.getElementById('actionLogOverlay')
                            || document.getElementById('alOverlay');
                      if (о) { о.style.display = 'block'; }
                      const л = document.getElementById('alFeed');
                      if (л) л.scrollTop = 0;
                    }""")
                    стр.wait_for_timeout(300)
                    стр.locator('#alFeed').screenshot(
                        path=str(pathlib.Path(__file__).parent / f"журнал-код-{тема}.png"), timeout=6000)
                except Exception as e:
                    print('снимок', тема, 'не вышел:', str(e).split(chr(10))[0][:90])

            # ── код набран как соседи по строке, а не выделен ──
            вид = стр.evaluate("""() => {
              const к = document.querySelector('#alFeed .al-code');
              if (!к) return { нет: true };
              const сосед = к.closest('.al-ctx');
              const ск = getComputedStyle(к), сс = getComputedStyle(сосед);
              return {
                шрифт: ск.fontFamily, шрифтСоседа: сс.fontFamily,
                цвет: ск.color, цветСоседа: сс.color,
                кегль: ск.fontSize, кегльСоседа: сс.fontSize,
                вес: ск.fontWeight, весСоседа: сс.fontWeight,
                цифры: к.getAttribute('data-code') || '',
                видно: к.textContent.trim(),
              };
            }""")
            if not вид or вид.get("нет"):
                плохо("кода в журнале нет — проверять нечего")
            else:
                for что, а, б in (("шрифтом", вид["шрифт"], вид["шрифтСоседа"]),
                                  ("цветом", вид["цвет"], вид["цветСоседа"]),
                                  ("кеглем", вид["кегль"], вид["кегльСоседа"]),
                                  ("весом", вид["вес"], вид["весСоседа"])):
                    if а != б:
                        плохо(f"код набран другим {что}, чем строка вокруг: "
                              f"«{а}» против «{б}» — выделять его не просили")
                if вид["цифры"] != "386520":
                    плохо(f"в data-code не одни цифры кода: «{вид['цифры']}»")
                if "код" not in вид["видно"]:
                    плохо("слово «код» пропало из строки")

            # ── двойное нажатие кладёт в буфер одни цифры ──
            коп = стр.evaluate("""async () => {
              window.__буфер = null;
              const прежний = navigator.clipboard && navigator.clipboard.writeText;
              try {
                Object.defineProperty(navigator, 'clipboard', {
                  configurable: true,
                  value: { writeText: (т) => { window.__буфер = т; return Promise.resolve(); } },
                });
              } catch (e) { return { нетПодмены: String(e) }; }
              const к = document.querySelector('#alFeed .al-code');
              if (!к) return { нет: true };
              // Мышью: двойное нажатие.
              к.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
              await new Promise(r => setTimeout(r, 150));
              const мышью = window.__буфер;
              // Пальцем: два касания подряд по одному коду.
              window.__буфер = null;
              const касание = () => к.dispatchEvent(new TouchEvent('touchend',
                { bubbles: true, cancelable: true }));
              касание();
              await new Promise(r => setTimeout(r, 60));
              касание();
              await new Promise(r => setTimeout(r, 150));
              const пальцем = window.__буфер;
              // Одиночное нажатие копировать не должно.
              window.__буфер = null;
              к.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              await new Promise(r => setTimeout(r, 150));
              const одним = window.__буфер;
              return { мышью, пальцем, одним };
            }""")
            if not коп or коп.get("нет") or коп.get("нетПодмены"):
                плохо("двойное нажатие по коду проверить не удалось")
            else:
                if коп["мышью"] != "386520":
                    плохо(f"двойное нажатие мышью положило в буфер «{коп['мышью']}» "
                          f"вместо одних цифр")
                if коп["пальцем"] != "386520":
                    плохо(f"два касания пальцем положили в буфер «{коп['пальцем']}» "
                          f"вместо одних цифр — на телефоне `dblclick` бывает не всегда")
                if коп["одним"]:
                    плохо(f"одиночное нажатие уже копирует («{коп['одним']}») — "
                          "просили двойное")

            # ── событие уносит код в базу ──
            п = стр.evaluate("""async () => {
              window.__ТАБЛИЦЫ.events = [];
              _sbUser = { id: 'u-проба' };
              // Свой пресет с кодом.
              saveAllPresets({ p1: { id: 'p1', name: 'Свой расчёт', state: {},
                                     shortCode: '112233', sharedId: '112233' } });
              setActivePreset('p1');
              await logEvent('preset_saved', null);
              const своё = (window.__ТАБЛИЦЫ.events.slice(-1)[0] || {}).details;
              // Чужой расчёт, открытый по коду.
              setActivePreset(null);
              _activeSharedCode = '445566';
              await logEvent('print', null);
              const чужое = (window.__ТАБЛИЦЫ.events.slice(-1)[0] || {}).details;
              _activeSharedCode = null;
              return { своё, чужое };
            }""")
            if not п:
                плохо("событие не удалось записать")
            else:
                if (п["своё"] or {}).get("presetCode") != "112233":
                    плохо(f"у события в своём пресете код не записан: {п['своё']}")
                if (п["чужое"] or {}).get("presetCode") != "445566":
                    плохо(f"у события в чужом расчёте код не записан: {п['чужое']}")

            # ── отказ базы виден словами ──
            о = стр.evaluate("""async () => {
              const исх = _sb.from.bind(_sb);
              _sb.from = (табл) => {
                const о = исх(табл);
                if (табл !== 'preset_links') return о;
                о.update = () => ({ eq: () => Promise.resolve({
                  data: null, error: { code: '42501', message: 'new row violates row-level security policy' } }) });
                return о;
              };
              window.__тосты = [];
              const прежний = window.showToast;
              window.showToast = (т) => { window.__тосты.push(String(t_или(т))); };
              function t_или(т) { return т; }
              _activeSharedCode = '778899';
              // Расчёт свой: с 19.09.2026 чужой открывается только на просмотр,
              // записи в базу на нём не бывает вовсе, и отказ базы проверять
              // там нечем. Мерим то, ради чего проба написана: отказ в записи
              // виден словами, а не молча.
              _sharedPresets = [{ short_code: '778899', author_id: 'u-проба',
                                  is_public: true, locked: false, name: 'Свой общий' }];
              _sbProfile = { role: 'admin', full_name: 'Проба' };
              _collabLastState = {};
              await collabWriteSection('disc');
              await new Promise(r => setTimeout(r, 200));
              window.showToast = прежний;
              _sb.from = исх;
              _activeSharedCode = null;
              return window.__тосты;
            }""")
            if о is None:
                плохо("правку чужого расчёта проверить не удалось")
            elif not any("не сохранена" in т for т in о):
                плохо("база отказала в записи, а человеку об этом не сказали — "
                      f"правка выглядит сохранённой (тосты: {о})")

            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: код расчёта стоит в подписи события группами по три, у записи "
          "без кода его нет, событие уносит код и своего пресета, и чужого "
          "расчёта, а отказ базы в записи виден словами.")


if __name__ == "__main__":
    главная()
