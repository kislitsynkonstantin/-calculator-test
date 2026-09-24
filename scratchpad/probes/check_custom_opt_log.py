#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: правка своей опции говорит, что и у чего поменялось.

Константин 24.09.2026, снимком строки «Своя опция изменена», под птичкой у
которой стоял один «Раздел»: «непонятно как». Журнал отбрасывает пары без
перемены, поэтому сохранение без правок оставляло пустое событие, а правка
одной цены не называла опцию.

Там же вскрылось второе: «Свои опции добавлены списком» резали список
двенадцатью именами при записи — тот же дефект, что 23.09 был у набора
опций, — и раскрыть хвост было нечем.

Берега:

  • сохранили без правок — события нет;
  • поменяли цену — в событии название опции и цена «было → стало»;
  • переименовали — «Название» было → стало;
  • вставили списком 15 позиций — в событии все 15 имён, а в журнале видна
    дюжина и кнопка «и ещё 3», раскрывающая остаток.

    python3 check_custom_opt_log.py
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
              + json.dumps(dict(ДАННЫЕ, events=[], profiles=[{"id": "u-проба", "role": "admin",
                                                               "first_name": "Проба", "last_name": ""}]),
                           ensure_ascii=False) + ");")
НАХОДКИ = []


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


ШАГИ = """async () => {
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  window._sbProfile = { role: 'admin', full_name: 'Проба' };
  selectProjectOption(0);
  await new Promise(r => setTimeout(r, 800));
  const ключ = SECTIONS.find(с => document.getElementById('addName_' + с.key)).key;
  const пауза = () => new Promise(r => setTimeout(r, 250));
  const правки = () => (window.__ТАБЛИЦЫ.events || []).filter(с => с.event_type === 'custom_opt_edited');

  document.getElementById('addName_' + ключ).value = 'Проба опция';
  document.getElementById('addPrice_' + ключ).value = '100000';
  confirmAddOpt(ключ);
  await пауза();
  const co = getCustomOpts(ключ).find(c => c.name === 'Проба опция');

  const вышло = {};
  // 1. сохранить без правок
  startEditCustomOpt(ключ, co.id); saveEditCustomOpt(ключ, co.id); await пауза();
  вышло.безПравок = правки().length;
  // 2. только цена
  startEditCustomOpt(ключ, co.id);
  document.getElementById('editOptPrice_' + co.id).value = '120 000';
  saveEditCustomOpt(ключ, co.id); await пауза();
  вышло.цена = (правки().slice(-1)[0] || {}).details;
  // 3. новое название
  startEditCustomOpt(ключ, co.id);
  document.getElementById('editOptName_' + co.id).value = 'Проба опция новая';
  saveEditCustomOpt(ключ, co.id); await пауза();
  вышло.имя = (правки().slice(-1)[0] || {}).details;
  // 4. вставка списком, 15 позиций
  document.getElementById('addPaste_' + ключ).value =
    Array.from({ length: 15 }, (_, и) => 'Позиция вставки ' + (и + 1) + ' — 1000').join('\\n');
  разобратьВставку(ключ); подтвердитьВставку(ключ); await пауза();
  const вст = (window.__ТАБЛИЦЫ.events || []).filter(с => с.event_type === 'custom_opts_pasted').slice(-1)[0];
  const стр = вст ? (вст.details.rows || []).find(р => р.k === 'Список') : null;
  вышло.вставкаИмён = стр ? String(стр.b).split('\\n').filter(Boolean).length : null;
  вышло.вставкаХвост = стр ? /и ещё \\d+/.test(стр.b) : null;

  // журнал: строки раскрываем и смотрим список вставки
  // Заглушка, в отличие от базы, не ставит время записи — без него журнал
  // отсекает строки фильтром периода.
  (window.__ТАБЛИЦЫ.events || []).forEach(с => { if (!с.created_at) с.created_at = new Date().toISOString(); });
  // Правки своих опций — события второго уровня: видны в режиме «Подробно».
  openActionLog(); _alПодробно = true; await loadActionLog(true); await new Promise(r => setTimeout(r, 500));
  alРисовать();
  document.querySelectorAll('#alFeed .al-row').forEach(с => с.classList.add('open'));
  const сп = [...document.querySelectorAll('#alFeed .al-dlist')].find(у => у.textContent.includes('Позиция вставки'));
  вышло.журналВидно = сп ? [...сп.querySelectorAll('li')].filter(л => !л.classList.contains('al-dmore') && л.getBoundingClientRect().height > 0).length : null;
  вышло.журналКнопка = сп ? ((сп.querySelector('.al-dmore-btn') || {}).textContent || '') : null;
  const правкаЦены = [...document.querySelectorAll('#alFeed .al-row')].find(с => с.textContent.includes('Своя опция изменена') && с.textContent.replace(/\u00a0/g, ' ').includes('120 000'));
  вышло.журналИмяУЦены = правкаЦены ? правкаЦены.querySelector('.al-more').textContent.includes('Проба опция') : null;
  return вышло;
}"""


def строки(д):
    н = lambda с: str(с or "").replace("\xa0", " ")
    return {р["k"]: (н(р.get("a")), н(р.get("b"))) for р in ((д or {}).get("rows") or [])}


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            try:
                в = стр.evaluate(ШАГИ)
            except Exception as e:
                плохо(f"проба оборвалась: {e!s:.300}")
                в = None
            if в:
                if в["безПравок"] != 0:
                    плохо(f"сохранение без правок записало событие ({в['безПравок']})")
                ц = строки(в["цена"])
                if ц.get("Опция", ("", ""))[1] != "Проба опция":
                    плохо(f"правка цены не называет опцию: {ц}")
                if ц.get("Цена") != ("100 000 ₽", "120 000 ₽"):
                    плохо(f"правка цены без «было → стало»: {ц.get('Цена')}")
                и = строки(в["имя"])
                if и.get("Название") != ("Проба опция", "Проба опция новая"):
                    плохо(f"переименование без «было → стало»: {и}")
                if в["вставкаИмён"] != 15 or в["вставкаХвост"]:
                    плохо(f"вставка списком записала {в['вставкаИмён']} имён из 15"
                          + (" и хвост «и ещё N» в значении" if в["вставкаХвост"] else ""))
                if в["журналВидно"] != 12 or (в["журналКнопка"] or "").strip() != "и ещё 3":
                    плохо(f"в журнале у вставки видно {в['журналВидно']} имён, кнопка "
                          f"«{в['журналКнопка']}» — ждали 12 и «и ещё 3»")
                if not в["журналИмяУЦены"]:
                    плохо("в журнале под правкой цены нет названия опции")
                print(f"  без правок: {в['безПравок']} событий; цена: {ц}; вставка: "
                      f"{в['вставкаИмён']} имён, в журнале {в['журналВидно']} + «{в['журналКнопка']}»")
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
    print("Чисто: сохранение без правок в журнал не идёт, правка своей опции называет её "
          "и показывает «было → стало», а вставка списком хранит все имена и раскрывает хвост.")


if __name__ == "__main__":
    главная()
