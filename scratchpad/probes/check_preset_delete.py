#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба удаления пресета: удаление обязано пережить синхронизацию.

17.09.2026 Константин удалил почти все пресеты на тестовом домене, открыл
боевой — и они вернулись все до одного. Дело не в удалении, а в сложении:
синхронизация заливает в облако всё местное, чего в облаке нет. Удаление
стирало строку, другой браузер держал пресет у себя и заливал его обратно.
В базе это видно: из 74 пресетов 73 имели время правки в пределах суток.

Проба держит три правила:
  • удаление не стирает строку, а ставит метку `deleted_at` — иначе другому
    устройству нечем узнать, что пресет удалён;
  • синхронизация убирает помеченный пресет из местной памяти;
  • и не заливает его обратно, даже когда он лежит у неё, а в облаке его
    «нет» (то есть он помечен).

Заглушка облака здесь не декорация: живой базы из контейнера не достать, а
проверять надо именно сложение множеств в `sbSyncPresets`.
"""
import os
import pathlib
import sys
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

# Обычно проверяется рабочий файл теста. Боевую копию проба тоже умеет:
# тихая правка уезжает в бой без выпуска, и сверять её надо тем же способом,
# а не глазами по диффу — BM_ROOT=/путь/к/боевому. Имя латиницей:
# кириллическое имя переменной оболочка не принимает.
КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium не найден — запусти .claude/hooks/session-start.sh")
    return str(найденные[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


# Облако и местная память под пробу: один пресет живой, один помеченный
# удалённым, и оба лежат в браузере — как у того самого второго устройства.
ПОДГОТОВКА = """() => {
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  const вход = document.getElementById('loginScreen');
  if (вход) вход.style.display = 'none';
  _sbUser = { id: 'u-проба' };
  window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};
  window.__ТАБЛИЦЫ.presets = [
    { id: 'живой', user_id: 'u-проба', name: 'Живой', state: { savedAt: '2026-09-17T10:00:00Z' },
      updated_at: '2026-09-17T10:00:00Z', deleted_at: null },
    { id: 'удалённый', user_id: 'u-проба', name: 'Удалённый', state: { savedAt: '2026-09-17T10:00:00Z' },
      updated_at: '2026-09-17T12:00:00Z', deleted_at: '2026-09-17T12:00:00Z' },
  ];
  window.__ТАБЛИЦЫ.preset_links = [];
  // В браузере лежат оба — и ещё один, которого в облаке нет вовсе: такой
  // обязан уехать наверх, иначе новое устройство потеряет свою работу.
  localStorage.setItem('banya_msk_presets_v1', JSON.stringify({
    'живой':     { id: 'живой',     name: 'Живой',     state: { savedAt: '2026-09-17T09:00:00Z' } },
    'удалённый': { id: 'удалённый', name: 'Удалённый', state: { savedAt: '2026-09-17T09:00:00Z' } },
    'местный':   { id: 'местный',   name: 'Местный',   state: { savedAt: '2026-09-17T09:00:00Z' } },
  }));
  window.__залито = [];
  window.__былоСохранение = window.sbSavePreset;
  window.sbSavePreset = async (п) => { window.__залито.push(п.id); };
  return true;
}"""


def главная():
    с, порт = сервер()
    ошибки = []
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
        стр = бр.new_page()
        стр.add_init_script(ЗАГЛУШКА)
        стр.on("pageerror", lambda e: ошибки.append(str(e)[:160]))
        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
        стр.wait_for_timeout(1500)
        стр.evaluate(ПОДГОТОВКА)

        # ── удаление ставит метку, а не стирает строку ──────────────────────
        удаление = стр.evaluate("""async () => {
          await sbDeletePreset('живой');
          const р = window.__ТАБЛИЦЫ.presets.find(п => п.id === 'живой');
          return { строкаНаМесте: !!р, метка: р ? р.deleted_at : null };
        }""")
        if not удаление["строкаНаМесте"]:
            НАХОДКИ.append("удаление стёрло строку в облаке — другому устройству нечем "
                           "узнать, что пресет удалён, и оно зальёт его обратно")
        elif not удаление["метка"]:
            НАХОДКИ.append("строка осталась, а метки удаления на ней нет")

        # Возвращаем исходное состояние облака для второй половины пробы.
        стр.evaluate(ПОДГОТОВКА)

        # ── синхронизация чтит метку ────────────────────────────────────────
        итог = стр.evaluate("""async () => {
          await sbSyncPresets(true);
          const местные = JSON.parse(localStorage.getItem('banya_msk_presets_v1') || '{}');
          const итог = { ключи: Object.keys(местные).sort(), залито: window.__залито.slice() };
          window.sbSavePreset = window.__былоСохранение;
          return итог;
        }""")
        if "удалённый" in итог["ключи"]:
            НАХОДКИ.append("после синхронизации удалённый пресет остался в браузере — "
                           "удаление не доходит до второго устройства")
        if "удалённый" in итог["залито"]:
            НАХОДКИ.append("синхронизация залила удалённый пресет обратно в облако — "
                           "ровно то воскрешение, из-за которого правка и делалась")
        if "живой" not in итог["ключи"]:
            НАХОДКИ.append("живой пресет пропал из браузера — удаление задело не то")
        if "местный" not in итог["залито"]:
            НАХОДКИ.append("пресет, которого нет в облаке, не уехал наверх — работа "
                           "нового устройства потеряется")

        # ── удалённый расчёт не открывается по своему номеру ────────────────
        # Номер теперь есть у каждого расчёта, а не только у опубликованного.
        # Прежнее условие убирало строку в `preset_links` только у
        # опубликованного — у остальных она оставалась вместе с расчётом
        # целиком, и удалённая смета продолжала открываться по номеру.
        ссылки = стр.evaluate("""async () => {
          window.__ТАБЛИЦЫ.preset_links = [
            { short_code: '111111', preset_id: 'сномером', author_id: 'u-проба',
              author_name: 'Проба', name: 'С номером', state: {}, is_public: false,
              visibility: 'public' },
            { short_code: '222222', preset_id: 'чужой', author_id: 'u-чужой',
              author_name: 'Другой', name: 'Чужой', state: {}, is_public: true,
              visibility: 'public' },
          ];
          localStorage.setItem('banya_msk_presets_v1', JSON.stringify({
            'сномером': { id: 'сномером', name: 'С номером', state: {},
                          shortCode: '111111', sharedId: '111111' },
          }));
          window.__прежнийВопрос = showConfirmDialog;
          showConfirmDialog = (з, т, да) => да();
          deletePreset('сномером');
          await new Promise(р => setTimeout(р, 400));
          showConfirmDialog = window.__прежнийВопрос;
          return (window.__ТАБЛИЦЫ.preset_links || []).map(с => с.short_code);
        }""")
        if '111111' in ссылки:
            НАХОДКИ.append("после удаления расчёта его строка в preset_links осталась — "
                           "удалённая смета продолжает открываться по своему номеру")
        if '222222' not in ссылки:
            НАХОДКИ.append("удаление своего расчёта снесло чужую ссылку")

        бр.close()
    с.shutdown()

    важные = [о for о in ошибки if "favicon" not in о]
    if важные:
        НАХОДКИ.append("ошибки страницы: " + "; ".join(важные[:2]))
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: удаление ставит метку, синхронизация её чтит и обратно пресет не заливает, "
          "а строка ссылки уходит вместе с расчётом — по номеру он больше не открывается.")


if __name__ == "__main__":
    главная()
