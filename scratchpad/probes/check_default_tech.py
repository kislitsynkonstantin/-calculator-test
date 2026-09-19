#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба двух настроек: цвета примечаний и технологии по умолчанию.

Константин 19.09.2026: «салатовый убери из цветов подсветки примечаний» и
«добавь в настройки „Технология по умолчанию" (Каркас/Клеёный брус). Хранится
пусть в аккаунте, между устройствами».

Цвет:
  • салатового (#f0f4ee) среди кружков нет;
  • у кого он был выбран — переводится на мятный, иначе подпись показывала бы
    «—», ни один кружок не был бы отмечен, а примечания красились цветом,
    которого в списке уже нет.

Технология:
  • строка есть, кнопки две, выбранная отмечена;
  • выбор ложится в `appSettings` — а этот объект целиком уезжает в
    `profiles.app_settings`, поэтому настройка и есть аккаунтная;
  • выбор в настройках технологию сейчас же не переключает: человек пришёл в
    настройки, а не считать, и переключение стёрло бы его расчёт;
  • при старте настройка применяется, но только если расчёт ещё не начат —
    профиль приезжает с задержкой, и переключение поверх начатой работы её бы
    стёрло;
  • брус не открыт — строки нет вовсе и настройка из аккаунта заслон не обходит.

    python3 check_default_tech.py
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
САЛАТОВЫЙ = "#f0f4ee"

ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
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


def страница(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
    }""")
    return стр


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = страница(бр, порт)

            # ── цвет примечаний ──
            цв = стр.evaluate("""async (салатовый) => {
              appSettings.noteHighlightColor = салатовый;
              openSettings();
              await new Promise(r => setTimeout(r, 500));
              const тело = document.getElementById('settingsBody');
              const кружки = [...тело.querySelectorAll('.st-swatch')]
                .map(э => (э.getAttribute('style') || '').match(/background:\\s*([^;]+)/));
              return {
                цвета: кружки.map(м => м ? м[1].trim() : ''),
                текущий: appSettings.noteHighlightColor,
                отмечено: тело.querySelectorAll('.st-swatch.on').length,
              };
            }""", САЛАТОВЫЙ)
            if not цв:
                НАХОДКИ.append("настройки не открылись")
            else:
                if any(САЛАТОВЫЙ in ц for ц in цв["цвета"]):
                    НАХОДКИ.append("салатовый остался среди кружков подсветки")
                if цв["текущий"].lower() == САЛАТОВЫЙ:
                    НАХОДКИ.append("выбранный салатовый не переведён на другой цвет — "
                                   "подпись покажет «—», и ни один кружок не отмечен")
                if цв["отмечено"] != 1:
                    НАХОДКИ.append(f"отмеченных кружков {цв['отмечено']}, а должен быть один")

            # ── технология по умолчанию ──
            тех = стр.evaluate("""async () => {
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              renderSettingsBody();
              await new Promise(r => setTimeout(r, 300));
              const тело = document.getElementById('settingsBody');
              const строка = [...тело.querySelectorAll('.st-row')]
                .find(р => /Технология по умолчанию/.test(р.innerText));
              if (!строка) return { нет: true };
              const кнопки = [...строка.querySelectorAll('.st-theme-btn')]
                .map(б => ({ имя: б.textContent.trim(), активна: б.classList.contains('active') }));
              const былаТех = currentTech;
              if (typeof выбратьТехнологиюПоУмолчанию !== 'function')
                return { нетВыбора: true };
              выбратьТехнологиюПоУмолчанию('glulam');
              await new Promise(r => setTimeout(r, 300));
              return {
                кнопки, вНастройках: appSettings.defaultTech,
                техПослеВыбора: currentTech, былаТех,
                подпись: строка.innerText.replace(/\\s+/g, ' '),
              };
            }""")
            if тех and тех.get("нетВыбора"):
                НАХОДКИ.append("выбора технологии по умолчанию нет вовсе — "
                               "функции `выбратьТехнологиюПоУмолчанию` в файле нет")
            elif not тех or тех.get("нет"):
                НАХОДКИ.append("строки «Технология по умолчанию» нет в настройках")
            else:
                имена = [к["имя"] for к in тех["кнопки"]]
                if имена != ["Каркас", "Клеёный брус"]:
                    НАХОДКИ.append(f"кнопки технологии не те: {имена}")
                if sum(1 for к in тех["кнопки"] if к["активна"]) != 1:
                    НАХОДКИ.append("отмечена не ровно одна технология")
                if тех["вНастройках"] != "glulam":
                    НАХОДКИ.append(f"выбор не лёг в настройки: {тех['вНастройках']}")
                if тех["техПослеВыбора"] != тех["былаТех"]:
                    НАХОДКИ.append("выбор в настройках сейчас же переключил технологию — "
                                   "расчёт человека стёрся бы прямо из окна настроек")
                if "аккаунт" not in тех["подпись"].lower():
                    НАХОДКИ.append("в подписи не сказано, что настройка аккаунтная")

            # Снимок раздела «Калькулятор» — его и читает человек.
            стр.evaluate("""() => {
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              renderSettingsBody();
              const т = [...document.querySelectorAll('#settingsBody .st-section-title')]
                .find(э => /Калькулятор/i.test(э.textContent));
              if (т) т.scrollIntoView({ block: 'start' });
            }""")
            стр.wait_for_timeout(400)
            for тема in ('модерн', 'бланк'):
                стр.evaluate("(т) => document.body.classList.toggle('ui-blank', т === 'бланк')", тема)
                стр.wait_for_timeout(250)
                try:
                    стр.locator('#settingsBody').screenshot(
                        path=str(pathlib.Path(__file__).parent / f"настройки-тех-{тема}.png"), timeout=5000)
                except Exception as e:
                    print('снимок', тема, 'не вышел:', str(e).split(chr(10))[0][:80])

            # ── при старте применяется, но не поверх начатого ──
            прим = стр.evaluate("""async () => {
              if (typeof применитьТехнологиюПоУмолчанию !== 'function')
                return { нетПрименения: true };
              // Расчёт начат: переключать нельзя.
              appSettings.defaultTech = 'glulam';
              const и = PROJECTS.findIndex(p => p && p[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 700));
              await применитьТехнологиюПоУмолчанию();
              await new Promise(r => setTimeout(r, 400));
              const приЗанятом = currentTech;
              // Чистый старт: переключить обязан.
              selectedProject = null; checkedOptions = {};
              try { setActivePreset(null); } catch (e) {}
              _activeSharedCode = null;
              await применитьТехнологиюПоУмолчанию();
              await new Promise(r => setTimeout(r, 900));
              return { приЗанятом, начисто: currentTech };
            }""")
            if прим and прим.get("нетПрименения"):
                НАХОДКИ.append("настройка нигде не применяется — функции "
                               "`применитьТехнологиюПоУмолчанию` в файле нет")
            elif not прим:
                НАХОДКИ.append("применение настройки проверить не удалось")
            else:
                if прим["приЗанятом"] != "frame":
                    НАХОДКИ.append("настройка переключила технологию поверх начатого расчёта — "
                                   "выбранный проект и отмеченные опции стёрлись бы")
                if прим["начисто"] != "glulam":
                    НАХОДКИ.append(f"на чистом старте настройка не сработала: {прим['начисто']}")

            стр.close()

            # ── брус не открыт: строки нет вовсе ──
            стр2 = страница(бр, порт)
            зак = стр2.evaluate("""async () => {
              window.IS_TEST_DOMAIN = false;
              window.GLULAM_ROLES = ['admin', 'editor'];
              window._sbProfile = { role: 'manager', full_name: 'Менеджер' };
              openSettings();
              await new Promise(r => setTimeout(r, 500));
              const тело = document.getElementById('settingsBody');
              appSettings.defaultTech = 'glulam';
              const былаТех = currentTech;
              if (typeof применитьТехнологиюПоУмолчанию === 'function')
                await применитьТехнологиюПоУмолчанию();
              await new Promise(r => setTimeout(r, 400));
              return { есть: /Технология по умолчанию/.test(тело.innerText),
                       тех: currentTech, былаТех };
            }""")
            if зак is None:
                НАХОДКИ.append("проверку закрытого бруса выполнить не удалось")
            else:
                if зак["есть"]:
                    НАХОДКИ.append("строка технологии показана там, где брус не открыт — "
                                   "выбирать не из чего")
                if зак["тех"] != зак["былаТех"]:
                    НАХОДКИ.append("настройка из аккаунта обошла заслон и включила брус")
            стр2.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: салатового в подсветке нет и выбранный переведён, технология по "
          "умолчанию лежит в настройках аккаунта, сразу не переключает, при старте "
          "срабатывает только на чистом расчёте и заслон бруса не обходит.")


if __name__ == "__main__":
    главная()
