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
    # Проектов два нарочно. С одним калькулятор выбирает его сам («Auto-select
    # if exactly one result»), и «пустой расчёт» в пробе оказывался начатым —
    # проверка того, что настройка срабатывает на пустом, мерила бы вхолостую.
    "pricing_projects": [{
        "product": "frame", "sort": и, "slug": "Проба %d×4" % (5 + и),
        "name": "Проба %d×4" % (5 + и),
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    } for и in (1, 2)],
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
              if (typeof выбратьТехнологиюПоУмолчанию !== 'function')
                return { нетВыбора: true };
              // Расчёт начат: выбор в настройках не должен его стереть.
              const и = PROJECTS.findIndex(p => p && p[0]);
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 700));
              const былаТех = currentTech;
              выбратьТехнологиюПоУмолчанию('glulam');
              await new Promise(r => setTimeout(r, 900));
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
                # Третья кнопка — заглушка «Камень», её состав проверяется ниже
                # отдельно; здесь важны только готовые технологии.
                if имена[:2] != ["Каркас", "Клеёный брус"]:
                    НАХОДКИ.append(f"готовые технологии в ряду не те: {имена}")
                if sum(1 for к in тех["кнопки"] if к["активна"]) != 1:
                    НАХОДКИ.append("отмечена не ровно одна технология")
                if тех["вНастройках"] != "glulam":
                    НАХОДКИ.append(f"выбор не лёг в настройки: {тех['вНастройках']}")
                if тех["техПослеВыбора"] != тех["былаТех"]:
                    НАХОДКИ.append("выбор в настройках переключил технологию поверх "
                                   "начатого расчёта — работа человека стёрлась бы "
                                   "прямо из окна настроек")
                # Ищется смысл, а не слово. «Настройка аккаунта» — наш жаргон;
                # менеджеру то же самое говорят «на любом вашем устройстве»,
                # и проба не должна держать формулировку, когда та стала лучше.
                if "устройств" not in тех["подпись"].lower():
                    НАХОДКИ.append("в подписи не сказано, что выбор едет за человеком "
                                   f"на другие устройства: «{тех['подпись'][:90]}»")

            # Снимок верха окна — тройка «Тема», «Стиль интерфейса»,
            # «Технология по умолчанию» читается вместе, а не по отдельности.
            стр.evaluate("""() => {
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              renderSettingsBody();
              const т = document.getElementById('settingsBody');
              if (т) т.scrollTop = 0;
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

            # ── «Камень»: место занято, выбрать нельзя ──
            # Константин 20.09.2026: «тут иконку дома убери, добавь ещё
            # технологию „Камень" и поставь заглушку на ней (в калькуляторе
            # и настройках)».
            камень = стр.evaluate("""async () => {
              const р = [...document.querySelectorAll('#settingsBody .st-row')]
                .find(э => /Технология по умолчанию/.test(э.innerText));
              if (!р) return { нет: true };
              const кн = [...р.querySelectorAll('.st-theme-btn')].map(б => ({
                имя: б.textContent.trim(), скоро: б.classList.contains('soon') }));
              const список = [...document.querySelectorAll('#techSelectDropdown .custom-select-option')]
                .map(э => ({ текст: (э.innerText || '').replace(/\\s+/g, ' ').trim(),
                             скоро: э.classList.contains('soon') }));
              // Нажатие пробуем из бруса, а не из каркаса: без заглушки
              // `selectTech` сводит всё незнакомое к каркасу, и проба,
              // нажимающая «Камень» стоя в каркасе, молчала бы при
              // полностью сломанном поведении — каркас в каркас.
              await switchTech('glulam');
              await new Promise(r => setTimeout(r, 900));
              const было = currentTech;
              selectTech('Камень');
              await new Promise(r => setTimeout(r, 900));
              return { значок: !!р.querySelector('svg'), кнопки: кн, список,
                       было, стало: currentTech };
            }""") or {}
            if камень.get("нет"):
                НАХОДКИ.append("строки технологии нет — «Камень» проверять негде")
            else:
                if камень["значок"]:
                    НАХОДКИ.append("в строке технологии остался значок — его просили убрать")
                имена = [к["имя"] for к in камень["кнопки"]]
                if имена != ["Каркас", "Клеёный брус", "Камень"]:
                    НАХОДКИ.append(f"кнопки технологии не те: {имена}")
                elif not камень["кнопки"][2]["скоро"]:
                    НАХОДКИ.append("«Камень» в настройках нарисован как обычная кнопка — "
                          "по виду не отличить готовую технологию от заглушки")
                тексты = [с["текст"] for с in камень["список"]]
                if len(тексты) != 3 or not тексты[2].startswith("Камень"):
                    НАХОДКИ.append(f"в списке технологий в шапке нет «Камня»: {тексты}")
                elif not камень["список"][2]["скоро"]:
                    НАХОДКИ.append("«Камень» в списке технологий не помечен заглушкой")
                if камень["стало"] != камень["было"]:
                    НАХОДКИ.append(f"нажатие «Камня» переключило технологию: "
                          f"{камень['было']} → {камень['стало']} — расчёт ушёл бы "
                          "в другую технологию молча")

            # ── место строки в окне ──
            # Константин 19.09.2026: «строку с переключением Каркас / КБ
            # поставь под темой». Значит она стоит в верхнем блоке, третьей
            # после «Темы» и «Стиля интерфейса», а не внизу, в «Калькуляторе».
            место = стр.evaluate("""() => {
              const ряды = [...document.querySelectorAll('#settingsBody .st-row')];
              const первый = р => (р.innerText || '').split('\\n')[0].trim();
              return {
                порядок: ряды.slice(0, 4).map(первый),
                тех: ряды.findIndex(р => /Технология по умолчанию/.test(р.innerText)),
                стиль: ряды.findIndex(р => /Стиль интерфейса/.test(р.innerText)),
                цвет: ряды.findIndex(р => /Цвет оформления/.test(р.innerText)),
              };
            }""")
            if not место or место["тех"] < 0:
                НАХОДКИ.append("строки технологии в окне не нашлось")
            # С v2.5.10 между стилем и технологией встал «Цвет оформления»:
            # технология идёт следом за последней строкой вида.
            elif место["тех"] != max(место["стиль"], место["цвет"]) + 1:
                НАХОДКИ.append("строка технологии стоит не под строками вида, "
                               f"а {место['тех'] + 1}-й: {место['порядок']}")

            стр.close()

            # ── на телефоне подпись не сжимается в столбик ──
            # Пояснение рядом с двумя кнопками ужималось до полутора сотен
            # пикселей и рвалось на четыре строки. Правило переноса было
            # написано только для «Бланка» и только ниже 375 px, то есть на
            # телефоне Константина (390 px) не работало вовсе.
            for тема in ("бланк", "модерн"):
                тел = бр.new_page(viewport={"width": 390, "height": 820})
                тел.add_init_script(ЗАГЛУШКА)
                тел.add_init_script(
                    "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                    "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
                тел.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                тел.wait_for_timeout(2500)
                узк = тел.evaluate("""async (тема) => {
                  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                  document.body.classList.toggle('ui-blank', тема === 'бланк');
                  window._sbProfile = { role: 'admin', full_name: 'Проба' };
                  openSettings();
                  await new Promise(r => setTimeout(r, 700));
                  renderSettingsBody();
                  await new Promise(r => setTimeout(r, 300));
                  const р = [...document.querySelectorAll('#settingsBody .st-row')]
                    .find(э => /Технология по умолчанию/.test(э.innerText));
                  if (!р) return { нет: true };
                  const п = р.querySelector('.st-sub');
                  const я = р.querySelector('.st-label');
                  return {
                    подпись: p_ш(п), метка: p_ш(я), строка: p_ш(р),
                    строк: п ? Math.round(п.getBoundingClientRect().height /
                                          parseFloat(getComputedStyle(п).lineHeight || 16)) : 0,
                  };
                  function p_ш(э) { return э ? Math.round(э.getBoundingClientRect().width) : 0; }
                }""", тема)
                if not узк or узк.get("нет"):
                    НАХОДКИ.append(f"[{тема}] строки технологии на телефоне нет")
                else:
                    if узк["подпись"] < 200:
                        НАХОДКИ.append(f"[{тема}] пояснение сжато до {узк['подпись']} px "
                                       f"при строке {узк['строка']} px — рвётся в столбик")
                    if узк["строк"] > 3:
                        НАХОДКИ.append(f"[{тема}] пояснение занимает {узк['строк']} строк — "
                                       "кнопки держат ширину, текст ушёл в столбик")
                тел.close()

            стр = страница(бр, порт)

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

            # ── пустой расчёт переключается сразу ──
            # Константин 19.09.2026: «тут поставил КБ, но после того, как
            # подключилась синхронизация, остался Каркас». Обещание «со
            # следующего открытия» на пустом расчёте — обещание впустую:
            # терять нечего, и выбор должен вступать в силу тут же.
            стр3 = страница(бр, порт)
            срз = стр3.evaluate("""async () => {
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              const былаТех = currentTech;
              выбратьТехнологиюПоУмолчанию('glulam');
              await new Promise(r => setTimeout(r, 1500));
              return { былаТех, стала: currentTech, вНастройках: appSettings.defaultTech };
            }""")
            if not срз:
                НАХОДКИ.append("переключение на пустом расчёте проверить не удалось")
            else:
                if срз["былаТех"] != "frame":
                    НАХОДКИ.append("проба начала не с каркаса — переключать было нечего, "
                                   "мерило вхолостую")
                elif срз["стала"] != "glulam":
                    НАХОДКИ.append("на пустом расчёте выбор технологии не сработал сразу: "
                                   f"осталось «{срз['стала']}» — человек видит, что ничего "
                                   "не изменилось")

            # ── профиль не отменяет то, что выбрано руками ──
            # Запрос к базе уходит при загрузке, ответ приходит через секунду
            # с лишним. Кто успел за это время выбрать — терял выбор: в ответе
            # лежало прежнее значение, и оно накрывало настройки целиком.
            гонка = стр3.evaluate("""async () => {
              window.__ТАБЛИЦЫ.profiles = [{
                id: 'u-проба', role: 'admin', first_name: 'Проба', last_name: '',
                app_settings: { defaultTech: 'frame', defaultDiscount: 7 },
              }];
              _sbUser = { id: 'u-проба' };
              appSettings.defaultTech = 'glulam';   // выбрано руками только что
              await loadSbProfile();
              await new Promise(r => setTimeout(r, 900));
              const строка = [...document.querySelectorAll('#settingsBody .st-row')]
                .find(р => /Технология по умолчанию/.test(р.innerText));
              const кнопка = строка && [...строка.querySelectorAll('.st-theme-btn')]
                .find(б => б.classList.contains('active'));
              return {
                вНастройках: appSettings.defaultTech,
                вОблаке: (window.__ТАБЛИЦЫ.profiles[0].app_settings || {}).defaultTech,
                скидка: appSettings.defaultDiscount,
                отмечена: кнопка ? кнопка.textContent.trim() : null,
              };
            }""")
            if not гонка:
                НАХОДКИ.append("проверку прихода профиля выполнить не удалось")
            else:
                if гонка["вНастройках"] != "glulam":
                    НАХОДКИ.append("профиль отменил выбор, сделанный руками: в настройках "
                                   f"«{гонка['вНастройках']}» вместо «glulam»")
                if гонка["вОблаке"] != "glulam":
                    НАХОДКИ.append("выбор не догнал облако: в профиле осталось "
                                   f"«{гонка['вОблаке']}» — на другом устройстве будет прежнее")
                if гонка["скидка"] != 7:
                    НАХОДКИ.append("нетронутая настройка из профиля не приехала — слияние "
                                   f"выкинуло чужое вместе со своим (скидка {гонка['скидка']})")
                if гонка["отмечена"] not in (None, "Клеёный брус"):
                    НАХОДКИ.append(f"в окне настроек отмечено «{гонка['отмечена']}», "
                                   "а в силе другое — окно врёт о состоянии")
            стр3.close()

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
    print("Чисто: салатового в подсветке нет и выбранный переведён; технология "
          "стоит третьей строкой под «Стилем интерфейса» и на телефоне не сжимается, "
          "на пустом расчёте переключает сразу, поверх начатого молчит, приход "
          "профиля её не отменяет и заслон бруса не обходит.")


if __name__ == "__main__":
    главная()
