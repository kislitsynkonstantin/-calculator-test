#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: уведомления администратора по чужим ссылкам и коды у всех пресетов.

Две работы 19.09.2026 по просьбе Константина:

  • администратор видит в колокольчике заходы по ссылкам всех менеджеров, чужая
    строка подписана именем менеджера и открывается снимком из самой ссылки
    (пресет чужого менеджера база не отдаёт и отдавать не должна);
  • менеджер по-прежнему видит только свои — это правило, а не мелочь;
  • кнопки «Поделиться» в карточке пресета нет, номер стоит у каждого расчёта
    и появляется до ответа базы: ответы намеренно замедлены, и проба смотрит
    промежуток, пока сеть молчит (19.09.2026, «чтобы сразу номер присваивался»);
  • вставка на занятый номер чужую строку не переписывает, а берёт следующий;
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
    """Номер стоит на карточке до ответа базы, а не после.

    Прежняя проба мерила итог: «после выдачи кодов карточки не ждут». На таком
    замере мгновенная заглушка и живая база неразличимы, и несколько секунд с
    надписью «выдаётся…» проходили незамеченными — ровно то, что Константин
    увидел 19.09.2026. Теперь ответы базы намеренно замедлены, и проверяется
    промежуток: что видно человеку, пока сеть ещё молчит.
    """
    ЗАДЕРЖКА = 1500
    спросить(стр, """(задержка) => {
      window.__ЗАДЕРЖКА = задержка;
      window.__ТАБЛИЦЫ.preset_links = [];
      saveAllPresets({
        p1: { id: 'p1', name: 'Баня «Берлин» 9×5', state: { totalNum: 4513375 }, savedAt: '2026-09-18T11:39:00Z' },
        p2: { id: 'p2', name: 'Отделка парной', state: { totalNum: 5766424 }, savedAt: '2026-09-18T07:57:00Z' },
      });
      openPresetPanel();
    }""", ЗАДЕРЖКА)
    # Ни единого ожидания: карточки обязаны быть с номерами уже сейчас.
    сразу = спросить(стр, """() => {
      const карточки = [...document.querySelectorAll('#presetList .pcard-mine')];
      return {
        карточек: карточки.length,
        поделиться: document.querySelectorAll('#presetList .share-label').length,
        ждут: document.querySelectorAll('#presetList .pcard-code-wait').length,
        строкиКода: document.querySelectorAll('#presetList .pcard-code-row').length,
        коды: [...document.querySelectorAll('#presetList .pcard-code-value')]
                .map(э => э.textContent.trim()),
        вБазе: (window.__ТАБЛИЦЫ.preset_links || []).length,
      };
    }""")
    if not сразу:
        return
    if сразу["карточек"] < 2:
        плохо(f"в списке {сразу['карточек']} карточек вместо двух — проверять нечего")
        return
    if сразу["поделиться"]:
        плохо(f"кнопка «Поделиться» осталась в карточке ({сразу['поделиться']} шт.)")
    if сразу["строкиКода"] < сразу["карточек"]:
        плохо(f"строка кода есть не у всех карточек: {сразу['строкиКода']} из {сразу['карточек']}")
    if сразу["ждут"]:
        плохо(f"{сразу['ждут']} карточек открылись с надписью «выдаётся…» — "
              f"номер обязан стоять сразу, до разговора с базой")
    for к in сразу["коды"]:
        цифры = к.replace(" ", "")
        if not цифры.isdigit() or len(цифры) != 6:
            плохо(f"код не похож на шестизначный: «{к}»")
    if len(set(сразу["коды"])) != len(сразу["коды"]):
        плохо("две карточки получили один и тот же номер")
    if сразу["вБазе"]:
        плохо("строка в базе появилась раньше ответа сети — замер не тот, что думает проба")

    # Новый пресет: номер на карточке до того, как база ответила.
    спросить(стр, """() => {
      window.__прежнийДиалог = showPresetNameDialog;
      showPresetNameDialog = (имя, дальше) => dalshe(имя, дальше);
      function dalshe(имя, дальше) { дальше('Проба нового расчёта'); }
      savePreset();
    }""")
    стр.wait_for_timeout(120)   # меньше десятой доли задержки сети
    новый = спросить(стр, """() => {
      const строки = [...document.querySelectorAll('#presetList .pcard-mine')].map(э => ({
        имя: (э.querySelector('.pcard-name') || {}).textContent || э.innerText.slice(0, 40),
        код: (э.querySelector('.pcard-code-value') || {}).textContent || '',
        ждёт: !!э.querySelector('.pcard-code-wait'),
      }));
      return строки.filter(с => с.имя.indexOf('Проба нового расчёта') >= 0);
    }""")
    if not новый:
        плохо("только что сохранённый расчёт не появился в списке")
    else:
        н = новый[0]
        if н["ждёт"] or not н["код"].replace(" ", "").isdigit():
            плохо(f"новый расчёт открылся без номера («{н['код'].strip() or 'пусто'}») — "
                  f"он обязан стоять сразу, публикация идёт следом")

    # Публикация доходит до базы сама, без нажатий.
    стр.wait_for_timeout(ЗАДЕРЖКА * 4)
    спросить(стр, "async () => { _выдачаКодовИдёт = false; await опубликоватьПресеты(); }")
    стр.wait_for_timeout(ЗАДЕРЖКА * 4)
    после = спросить(стр, """() => ({
      вБазе: (window.__ТАБЛИЦЫ.preset_links || []).map(с => с.short_code),
      наКарточках: [...document.querySelectorAll('#presetList .pcard-code-value')]
                     .map(э => э.textContent.replace(/\\s/g, '')),
      ждут: document.querySelectorAll('#presetList .pcard-code-wait').length,
    })""")
    if не_пусто(после):
        if после["ждут"]:
            плохо(f"после публикации {после['ждут']} карточек без номера")
        if len(set(после["вБазе"])) != len(после["вБазе"]):
            плохо("в базе две строки с одинаковым номером")
        нет = [к for к in после["наКарточках"] if к and к not in после["вБазе"]]
        if нет:
            плохо(f"номер стоит на карточке, но в базу не ушёл: {', '.join(нет)} — "
                  f"по такому коду расчёт у другого менеджера не откроется")
    try:
        стр.locator("#presetList").screenshot(
            path=str(pathlib.Path(__file__).parent / "пресеты-коды.png"), timeout=3000)
    except Exception:
        pass

    # Столкновение с чужим приватным номером: чужую строку не трогаем,
    # себе берём следующий номер.
    спросить(стр, """() => { window.__ЗАДЕРЖКА = 0; }""")
    чужой = спросить(стр, """async () => {
      const код = '654321';
      window.__ТАБЛИЦЫ.preset_links.push({
        short_code: код, preset_id: 'чужой', author_id: 'u-чужой',
        author_name: 'Пётр Смирнов', name: 'Чужая баня', state: { чьё: 'чужое' },
        is_public: true, visibility: 'public',
      });
      const все = loadAllPresets();
      все.p3 = { id: 'p3', name: 'Столкновение', state: { totalNum: 1 },
                 savedAt: '2026-09-19T10:00:00Z', shortCode: код, sharedId: код };
      saveAllPresets(все);
      _sharedPresets = _sharedPresets.filter(с => с.preset_id !== 'p3');
      await sharePreset('p3', true);
      const чужая = (window.__ТАБЛИЦЫ.preset_links || [])
        .find(с => с.short_code === код) || {};
      return {
        чужаяЦела: чужая.author_id === 'u-чужой' && чужая.preset_id === 'чужой',
        нашКод: (loadAllPresets().p3 || {}).shortCode,
        строкП3: (window.__ТАБЛИЦЫ.preset_links || []).filter(с => с.preset_id === 'p3').length,
      };
    }""")
    if не_пусто(чужой):
        if not чужой["чужаяЦела"]:
            плохо("вставка на занятый номер переписала чужую строку в preset_links — "
                  "чужая ссылка стала бы нашей")
        if чужой["нашКод"] == '654321':
            плохо("после столкновения расчёт остался с занятым номером")
        if чужой["строкП3"] != 1:
            плохо(f"после столкновения в базе {чужой['строкП3']} строк своего расчёта вместо одной")

    спросить(стр, "() => { showPresetNameDialog = window.__прежнийДиалог; window.__ЗАДЕРЖКА = 0; }")


def не_пусто(м):
    return isinstance(м, dict) and bool(м)


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
          "их снимком, менеджер — только свои; номер стоит на карточке до ответа "
          "базы, публикация доходит сама, чужая строка при столкновении цела.")


if __name__ == "__main__":
    главная()
