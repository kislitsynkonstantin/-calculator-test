#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: уведомления администратора по чужим ссылкам и коды у всех пресетов.

Две работы 19.09.2026 по просьбе Константина:

  • администратор видит в колокольчике заходы по ссылкам всех менеджеров, чужая
    строка подписана именем менеджера и открывается снимком из самой ссылки
    (пресет чужого менеджера база не отдаёт и отдавать не должна);
  • менеджер по-прежнему видит только свои — это правило, а не мелочь;
  • кнопки «Поделиться» в карточке пресета нет, код стоит у каждого пресета,
    и пока он не выдан — строка честно говорит «выдаётся…»;
  • уникальность кода проверяется функцией базы, а не выборкой: политика
    `preset_links` чужие приватные коды не показывает, и столкновение прошло бы
    незамеченным.

    python3 check_notify_presets.py
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
ЧУЖОЙ_МЕНЕДЖЕР = "Пётр Смирнов"
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(найденные[-1])


ХРОМ = хром()

ТАБЛИЦЫ = {
    "client_links": [
        {"code": "svoya001", "revoked": False, "author_id": "u-проба",
         "author_name": "Проба", "preset_id": "p1",
         "project_name": "Своя баня 6×4", "client_name": "",
         "created_at": "2026-09-18T09:00:00Z", "snapshot_at": "2026-09-18T09:00:00Z",
         "snapshot": {"версия": "своя"}},
        {"code": "chuzh001", "revoked": False, "author_id": "u-чужой",
         "author_name": ЧУЖОЙ_МЕНЕДЖЕР, "preset_id": "p9",
         "project_name": "Чужая баня 9×5", "client_name": "",
         "created_at": "2026-09-18T08:00:00Z", "snapshot_at": "2026-09-18T08:00:00Z",
         "snapshot": {"версия": "чужая"}},
    ],
    "client_link_visits": [
        {"code": "svoya001", "seen_at": "2026-09-18T10:00:00Z", "version_at": "2026-09-18T09:00:00Z"},
        {"code": "chuzh001", "seen_at": "2026-09-18T11:00:00Z", "version_at": "2026-09-18T08:00:00Z"},
    ],
    "preset_links": [],
    "presets": [],
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


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:130])
        return None


def страница(бр, порт, роль):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
        "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
        # Выданный код проверяется через функцию базы: заглушка отвечает так же.
        "window.__RPC = window.__RPC || {};\n"
        "window.__спрошено = [];\n"
        "window.__RPC['preset_short_code_free'] = function (арг) {\n"
        "  window.__спрошено.push(арг && арг.p_code);\n"
        "  var занят = (window.__ТАБЛИЦЫ.preset_links || [])\n"
        "    .some(function (с) { return с.short_code === (арг && арг.p_code); });\n"
        "  return !занят;\n"
        "};\n"
        "window.addEventListener('DOMContentLoaded', function () {\n"
        "  window._sbProfile = { role: " + json.dumps(роль) + ", full_name: 'Проба' };\n"
        "});")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""() => {
      const б = document.getElementById('pricingErrorScreen');
      if (б) б.style.display = 'none';
    }""")
    return стр


def проверить_уведомления(стр, роль):
    спросить(стр, "async () => { await собратьУведомления(); нарисоватьУведомления(); }")
    стр.wait_for_timeout(300)
    м = спросить(стр, """() => {
      const строки = [...document.querySelectorAll('#bellMenu .nt-i')].map(э => ({
        текст: э.innerText.replace(/\\s+/g, ' ').trim(),
        подпись: (э.querySelector('.nt-who') || {}).textContent || '',
        нажимается: э.classList.contains('go'),
        вызов: э.getAttribute('onclick') || '',
      }));
      return { строки, всего: _уведомления.length };
    }""")
    if not м:
        return
    свои = [с for с in м["строки"] if "Своя баня" in с["текст"]]
    чужие = [с for с in м["строки"] if "Чужая баня" in с["текст"]]
    if роль == "manager":
        if чужие:
            плохо("менеджеру показали заход по чужой ссылке — он видит только свои")
        if not свои:
            плохо("менеджер не увидел захода по собственной ссылке")
        return
    if not чужие:
        плохо("администратор не увидел захода по ссылке другого менеджера")
        return
    ч = чужие[0]
    if ЧУЖОЙ_МЕНЕДЖЕР not in ч["подпись"]:
        плохо(f"чужая строка не подписана именем менеджера: «{ч['подпись']}»")
    if not ч["нажимается"] or "открытьЧужойРасчёт" not in ч["вызов"]:
        плохо("чужая строка не ведёт в расчёт по ссылке")
    if свои and "открытьПоУведомлению" not in свои[0]["вызов"]:
        плохо("своя строка перестала открывать собственный пресет")
    стр.evaluate("""() => {
      const м = document.getElementById('bellMenu');
      if (м) { м.style.display = 'flex'; м.style.position = 'static'; }
    }""")
    try:
        стр.locator("#bellMenu").screenshot(
            path=str(pathlib.Path(__file__).parent / "уведомления-админ.png"), timeout=3000)
    except Exception:
        pass

    # Переход: снимок берётся из самой ссылки, свой пресет закрывается.
    спросить(стр, """() => {
      window.__снимок = null;
      window.__прежний = restoreState;
      restoreState = (с) => { window.__снимок = с; };
      setActivePreset('p1');
    }""")
    спросить(стр, "() => открытьЧужойРасчёт('chuzh001')")
    стр.wait_for_timeout(600)
    итог = спросить(стр, """() => ({
      снимок: window.__снимок, активный: (typeof activePresetId !== 'undefined') ? activePresetId : 'нет'
    })""")
    if not итог or not итог.get("снимок"):
        плохо("переход по чужой ссылке не разложил снимок расчёта")
    elif итог["снимок"].get("версия") != "чужая":
        плохо("по чужой ссылке открылся не тот снимок")
    if итог and итог.get("активный"):
        плохо("после открытия чужого расчёта свой пресет остался активным — "
              "автосохранение записало бы чужое поверх своего")
    спросить(стр, "() => { restoreState = window.__прежний; }")


def проверить_пресеты(стр):
    # Окно само выдаёт коды фоном — на время замера «до» придерживаем выдачу
    # тем же признаком, которым она защищена от двух заходов сразу.
    спросить(стр, """() => {
      _выдачаКодовИдёт = true;
      openPresetPanel();
      saveAllPresets({
        p1: { id: 'p1', name: 'Баня «Берлин» 9×5', state: { totalNum: 4513375 }, savedAt: '2026-09-18T11:39:00Z' },
        p2: { id: 'p2', name: 'Отделка парной', state: { totalNum: 5766424 }, savedAt: '2026-09-18T07:57:00Z' },
      });
      renderPresetList();
    }""")
    стр.wait_for_timeout(300)
    до = спросить(стр, """() => {
      const карточки = [...document.querySelectorAll('#presetList .pcard-mine')];
      return {
        карточек: карточки.length,
        поделиться: document.querySelectorAll('#presetList .share-label').length,
        ждут: document.querySelectorAll('#presetList .pcard-code-wait').length,
        строкиКода: document.querySelectorAll('#presetList .pcard-code-row').length,
      };
    }""")
    if not до:
        return
    if до["карточек"] < 2:
        плохо(f"в списке {до['карточек']} карточек вместо двух — проверять нечего")
        return
    if до["поделиться"]:
        плохо(f"кнопка «Поделиться» осталась в карточке ({до['поделиться']} шт.)")
    if до["строкиКода"] < до["карточек"]:
        плохо(f"строка кода есть не у всех карточек: {до['строкиКода']} из {до['карточек']}")
    if до["ждут"] != до["карточек"]:
        плохо(f"без выданного кода карточка обязана говорить «выдаётся…»: "
              f"{до['ждут']} из {до['карточек']}")

    спросить(стр, "async () => { _выдачаКодовИдёт = false; await выдатьКодыПресетам(); }")
    стр.wait_for_timeout(900)
    после = спросить(стр, """() => {
      const коды = [...document.querySelectorAll('#presetList .pcard-code-value')]
        .map(э => э.textContent.trim());
      return {
        коды, ждут: document.querySelectorAll('#presetList .pcard-code-wait').length,
        вБазе: (window.__ТАБЛИЦЫ.preset_links || []).map(с => с.short_code),
        спрошено: window.__спрошено.slice(),
      };
    }""")
    if not после:
        return
    if после["ждут"]:
        плохо(f"после выдачи {после['ждут']} карточек всё ещё без кода")
    if len(после["вБазе"]) != до["карточек"]:
        плохо(f"в базе {len(после['вБазе'])} кодов на {до['карточек']} пресета")
    if len(set(после["вБазе"])) != len(после["вБазе"]):
        плохо("выданы одинаковые коды")
    if not после["спрошено"]:
        плохо("код выдан без вопроса к базе — чужой приватный код так не увидеть, "
              "и столкновение пройдёт незамеченным")
    for к in после["коды"]:
        цифры = к.replace(" ", "")
        if not цифры.isdigit() or len(цифры) != 6:
            плохо(f"код не похож на шестизначный: «{к}»")
    try:
        стр.locator("#presetList").screenshot(
            path=str(pathlib.Path(__file__).parent / "пресеты-коды.png"), timeout=3000)
    except Exception:
        pass

    # Столкновение: занятый код берётся из базы, и выдаётся другой.
    if not после["вБазе"]:
        return
    занятый = после["вБазе"][0]
    новый = спросить(стр, """async (занятый) => {
      const исх = Math.random;
      let раз = 0;
      Math.random = () => {
        raz_плюс();
        // Первый вызов выдаёт занятый код, дальше — обычная случайность.
        if (раз === 1) return (Number(занятый) - 100000) / 900000;
        return исх();
      };
      function raz_плюс() { раз++; }
      const код = await generateUniqueShortCode();
      Math.random = исх;
      return код;
    }""", занятый)
    if новый == занятый:
        плохо("выдан код, который уже занят в базе")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
            стр = страница(бр, порт, "admin")
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            проверить_уведомления(стр, "admin")
            проверить_пресеты(стр)
            стр.close()

            стр2 = страница(бр, порт, "manager")
            стр2.evaluate("() => { window._sbProfile = { role: 'manager', full_name: 'Менеджер' }; }")
            проверить_уведомления(стр2, "manager")
            стр2.close()

            важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
            for о in важные[:3]:
                плохо("ошибка страницы: " + о[:150])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: администратор видит чужие ссылки с подписью менеджера и открывает "
          "их снимком, менеджер — только свои; код есть у каждого пресета, "
          "«Поделиться» убрана, уникальность спрашивается у базы.")


if __name__ == "__main__":
    главная()
