#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Смена проекта снимает свои опции, а опции каталога оставляет.

Константин 24.09.2026, снимками «Виго» и поиска по опциям с «ручными
позициями»: при смене проекта без «Сбросить» расчёт перестраивался с тем же
набором, и свои опции оставались с ценами прежнего проекта. «Ручные опции с
ценами должны сбрасываться, а постоянные опции из калькулятора могут
оставаться».

Берега:

  • сменили проект в списке — своих опций нет ни в расчёте, ни на экране,
    их звёздочки и подарки не повисли; опция каталога осталась отмеченной;
  • сообщение называет снятое, а запись «Проект изменён» в журнале несёт
    список снятых;
  • выбор того же проекта ничего не снимает;
  • открытый пресет со своими опциями их сохраняет — это не смена проекта.

    python3 check_project_switch_custom.py
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
              + json.dumps(dict(ДАННЫЕ, events=[]), ensure_ascii=False) + ");")
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
  const пауза = (мс = 300) => new Promise(r => setTimeout(r, мс));
  const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
  const выбрать = async имя => {
    const и = filteredProjects.findIndex(p => p[0] === имя);
    selectProjectOption(и); await пауза(700);
  };
  const своих = () => Object.values(customOptions).reduce((s, a) => s + (a || []).length, 0);
  const строк = () => document.querySelectorAll('[data-custom-id]').length;
  const [А, Б] = PROJECTS.slice(0, 2).map(p => p[0]);
  const вышло = { А, Б };
  await выбрать(А);
  // опция каталога с ценой
  const кат = OPTIONS.find(o => !o.included && o.price && document.getElementById('chk_' + o.id));
  toggleOpt(кат.id); await пауза();
  // своя опция
  const ключ = SECTIONS.find(с => document.getElementById('addName_' + с.key)).key;
  document.getElementById('addName_' + ключ).value = 'Своя проба под проект А';
  document.getElementById('addPrice_' + ключ).value = '142500';
  confirmAddOpt(ключ); await пауза();
  const co = getCustomOpts(ключ)[0];
  starredOpts.add('custom_' + co.id); giftedOpts.add('custom_' + co.id);
  вышло.доСмены = своих();
  // тот же проект ещё раз — ничего не снимается
  await выбрать(А);
  вышло.темЖе = своих();
  // пресет со своей опцией
  const снимок = JSON.parse(JSON.stringify(collectState()));
  // смена проекта
  const тост = document.getElementById('toastMsg');
  await выбрать(Б);
  вышло.послеСмены = своих();
  вышло.строкПосле = строк();
  вышло.звездаПовисла = starredOpts.has('custom_' + co.id) || giftedOpts.has('custom_' + co.id);
  вышло.каталог = !!checkedOptions[кат.id];
  вышло.тост = тост ? тост.textContent : '';
  const смена = (window.__ТАБЛИЦЫ.events || []).filter(с => с.event_type === 'project_changed').slice(-1)[0];
  const ряд = смена ? (смена.details.rows || []).find(р => р.k === 'Сняты свои опции') : null;
  вышло.вЖурнале = ряд ? ряд.b : null;
  // открыли сохранённый расчёт — свои опции на месте
  restoreState(снимок); await пауза(800);
  вышло.изПресета = своих();
  return вышло;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 390, "height": 900})
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
                if в["доСмены"] != 1:
                    плохо(f"своя опция не добавилась ({в['доСмены']}) — проверять нечего")
                if в["темЖе"] != 1:
                    плохо("выбор того же проекта снял свои опции")
                if в["послеСмены"] or в["строкПосле"]:
                    плохо(f"после смены проекта свои опции остались: в расчёте {в['послеСмены']}, "
                          f"на экране {в['строкПосле']}")
                if в["звездаПовисла"]:
                    плохо("звёздочка или подарок снятой своей опции остались висеть")
                if not в["каталог"]:
                    плохо("опция каталога снялась вместе со своими — она должна остаться")
                if "Своя проба под проект А" not in (в["тост"] or ""):
                    плохо(f"сообщение не называет снятое: «{в['тост'][:80]}»")
                if not в["вЖурнале"] or "Своя проба под проект А" not in в["вЖурнале"]:
                    плохо(f"в записи «Проект изменён» нет снятых опций: {в['вЖурнале']!r}")
                if в["изПресета"] != 1:
                    плохо(f"открытый пресет потерял свою опцию ({в['изПресета']})")
                print(f"  {в['А']} → {в['Б']}: своих было {в['доСмены']}, стало {в['послеСмены']}; "
                      f"каталог отмечен: {в['каталог']}; из пресета: {в['изПресета']}")
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
    print("Чисто: смена проекта снимает свои опции с их отметками и говорит об этом, "
          "опции каталога остаются, тот же проект ничего не снимает, а пресет свои опции хранит.")


if __name__ == "__main__":
    главная()
