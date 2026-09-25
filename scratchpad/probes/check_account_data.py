#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Личные данные менеджера живут в аккаунте, а не в браузере.

Константин 25.09.2026: «база не видит пресеты на компьютерах менеджеров…
надо все переносить в базу». Пресеты уехали в базу в (32)–(33); здесь —
остаток, который жил только в браузере: звёзды на чужих общих расчётах,
история поиска по опциям, рубеж прочитанных уведомлений, частота
синхронизации. Всё это теперь в `appSettings` и уезжает в
`profiles.app_settings`.

Проба держит:
  • старое из браузера переезжает в аккаунт один раз, и ключи в браузере
    удаляются;
  • звезда на общем расчёте, запрос в поиске, открытие уведомлений и смена
    частоты доходят до профиля в базе и не пишут своих ключей в браузер;
  • «другое устройство» — пустой браузер — получает всё это из профиля.

    python3 check_account_data.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
НАХОДКИ = []
СТАРЫЕ_КЛЮЧИ = ["optSearchHistory_v1", "bm_уведомления_прочитано", "sb_sync_interval", "shared_stars_u-проба"]


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


def страница(бр, порт, в_браузере, профиль):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(
        "window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");"
        "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: "
        + json.dumps(профиль, ensure_ascii=False) + " }];")
    стр.add_init_script("try { if (!sessionStorage.getItem('засеяно')) { localStorage.clear(); "
                        + "".join(f"localStorage.setItem({json.dumps(к, ensure_ascii=False)}, {json.dumps(з, ensure_ascii=False)});"
                                  for к, з in в_браузере.items())
                        + " sessionStorage.setItem('засеяно', '1'); } } catch (e) {}")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    return стр, ошибки


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])

            # 1. Старое из браузера переезжает в аккаунт.
            стр, ошибки = страница(бр, порт, {
                "optSearchHistory_v1": json.dumps(["полок", "печь"], ensure_ascii=False),
                "bm_уведомления_прочитано": "2026-09-20T10:00:00.000Z",
                "sb_sync_interval": "10",
                "shared_stars_u-проба": json.dumps(["111111"]),
            }, {})
            р = стр.evaluate("""async () => {
              звёздыОбщих();
              await new Promise(r => setTimeout(r, 300));
              const проф = window.__ТАБЛИЦЫ.profiles[0].app_settings || {};
              return { ключи: %s.filter(к => localStorage.getItem(к) !== null),
                       настройки: { история: appSettings.optSearchHistory, прочитано: appSettings.notifReadAt,
                                    частота: appSettings.syncIntervalMin, звёзды: appSettings.sharedStars },
                       профиль: { история: проф.optSearchHistory, прочитано: проф.notifReadAt,
                                  частота: проф.syncIntervalMin, звёзды: проф.sharedStars } }; }""" % json.dumps(СТАРЫЕ_КЛЮЧИ, ensure_ascii=False))
            if р["ключи"]:
                плохо(f"после переезда в браузере остались ключи: {р['ключи']}")
            н = р["настройки"]
            if н["история"] != ["полок", "печь"] or н["прочитано"] != "2026-09-20T10:00:00.000Z" \
                    or н["частота"] != 10 or н["звёзды"] != ["111111"]:
                плохо(f"старое из браузера не переехало в аккаунт: {н}")
            if р["профиль"] != н:
                плохо(f"переехавшее не дошло до профиля в базе: {р['профиль']}")
            print(f"  переезд: в аккаунте {н}, ключей в браузере {len(р['ключи'])}")

            # 2. Новые действия пишут в профиль, а не в браузер.
            р = стр.evaluate("""async () => {
              const записи = []; const был = Storage.prototype.setItem;
              Storage.prototype.setItem = function (к, в) { записи.push(к); return был.call(this, к, в); };
              toggleSharedStar('222222');
              addOptSearchHistory('веник');
              пометитьПрочитанными();
              setSyncInterval(30);
              await new Promise(r => setTimeout(r, 300));
              Storage.prototype.setItem = был;
              const проф = window.__ТАБЛИЦЫ.profiles[0].app_settings || {};
              return { записи: [...new Set(записи)], звёзды: проф.sharedStars, история: проф.optSearchHistory,
                       прочитано: проф.notifReadAt, частота: проф.syncIntervalMin, таймер: _syncIntervalMin }; }""")
            чужие = [к for к in р["записи"] if к != "appSettings_v1"]
            if чужие:
                плохо(f"действия пишут свои ключи в браузер: {чужие}")
            if "222222" not in (р["звёзды"] or []):
                плохо("звезда на общем расчёте не дошла до профиля")
            if not р["история"] or р["история"][0] != "веник":
                плохо("запрос поиска не дошёл до профиля")
            if not р["прочитано"] or р["прочитано"] <= "2026-09-20":
                плохо("открытие уведомлений не сдвинуло рубеж в профиле")
            if р["частота"] != 30 or р["таймер"] != 30:
                плохо(f"частота синхронизации не дошла до профиля: {р['частота']}, таймер {р['таймер']}")
            print(f"  действия: в браузер писался только {р['записи']}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            стр.close()

            # 3. Другое устройство: пустой браузер, всё приезжает с профилем.
            стр, ошибки = страница(бр, порт, {}, {
                "sharedStars": ["333333"], "optSearchHistory": ["баня"],
                "notifReadAt": "2026-09-24T10:00:00.000Z", "syncIntervalMin": 1})
            р = стр.evaluate("""async () => {
              await new Promise(r => setTimeout(r, 500));
              return { звёзды: [..._sharedStars], история: getOptSearchHistory(), прочитано: прочитаноДо(),
                       частота: _syncIntervalMin }; }""")
            if р != {"звёзды": ["333333"], "история": ["баня"], "прочитано": "2026-09-24T10:00:00.000Z", "частота": 1}:
                плохо(f"на другом устройстве из профиля приехало не всё: {р}")
            print(f"  другое устройство: {р}")
            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: звёзды на общих расчётах, история поиска, прочитанные уведомления и частота синхронизации "
          "живут в аккаунте; старое из браузера переехало один раз, другое устройство получает всё из профиля.")


if __name__ == "__main__":
    главная()
