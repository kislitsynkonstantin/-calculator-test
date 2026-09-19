#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: чужой расчёт по коду открывается только на просмотр.

Константин 19.09.2026: «Открывать для просмотра». Повод — его же вопрос
днём раньше: «если я открываю по коду расчёт менеджера и случайно там
что-то сделаю, у него тоже изменится?» Изменялось. Своя строка пресета
чужому недоступна, а вот опубликованный расчёт правился всяким, у кого
роль администратора, редактора или специалиста, — молча, в ту же строку,
и автор узнавал об этом по изменившимся цифрам.

Мерка не во флагах, а в поведении: галочка на чужом расчёте не встаёт,
строка в базе после попытки правки не меняется. Флаг, по которому нельзя
нажать, проверять бессмысленно — он бывает верным при работающей правке.

Своё при этом не задето: собственный опубликованный расчёт правится и
пишется, как писался.

Отдельно держится выход: сохранение из чужого расчёта делает свой, и
общий режим при этом гаснет — иначе новый расчёт остаётся под чужим
замком и правится не больше, чем тот, с которого списан.

    python3 check_shared_readonly.py
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

Я = "u-я"
ЧУЖОЙ = "u-чужой"
МОЙ_КОД = "111111"
ЧУЖОЙ_КОД = "222222"

# Пустой проект не годится: без опций нечего нажимать, и проба молчала бы
# о правке, которой не пробовала. Один раздел, восемь позиций.
ПРОЕКТ = "Проба 6×4"
_ОПЦИИ, _МАТРИЦА = [], []
for _н in range(1, 9):
    _oid = "o%d" % _н
    _ОПЦИИ.append({"option_id": _oid, "name": "Позиция номер %d" % _н,
                   "section": "1", "included": _н <= 2, "price": None,
                   "formula": None, "status": "active", "sort": _н})
    _МАТРИЦА.append({"project_slug": ПРОЕКТ, "option_id": _oid, "price": 30000 + _н * 1234})


def ссылка(код, автор, имя):
    return {"short_code": код, "preset_id": "p-" + код, "author_id": автор,
            "author_name": имя, "name": имя, "is_public": True, "locked": False,
            "state": {"savedAt": "2026-09-18T10:00:00Z"},
            "spec_state": {}, "requisites": {}, "discount": {}, "payment_plan": {},
            "created_at": "2026-09-18T10:00:00Z", "updated_at": "2026-09-18T10:00:00Z"}


ТАБЛИЦЫ = {
    "pricing_projects": [{
        "product": "frame", "sort": 1, "slug": ПРОЕКТ, "name": ПРОЕКТ,
        "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
        "floors": 1, "roof_type": "двускатная", "warm": True,
        "open_area": 10, "closed_area": 20, "facade_area": 60,
        "paint_area": 60, "roof_area": 40,
    }],
    "pricing_matrix": _МАТРИЦА,
    "pricing_options": _ОПЦИИ,
    "pricing_sections": [{"section_key": "1", "pct": None, "fixed": None}],
    "project_kits": [], "project_kit_locks": [],
    "presets": [], "client_links": [], "client_link_visits": [],
    "preset_links": [ссылка(МОЙ_КОД, Я, "Мой расчёт"),
                     ссылка(ЧУЖОЙ_КОД, ЧУЖОЙ, "Расчёт Петрова")],
    "profiles": [{"id": Я, "role": "admin", "full_name": "Проба"},
                 {"id": ЧУЖОЙ, "role": "manager", "full_name": "Петров"}],
}


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


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


ОТКРЫТЬ = """(код) => {
  _sbUser = { id: '%s' };
  window._sbProfile = { id: '%s', role: 'admin', full_name: 'Проба' };
  _sharedPresets = (window.__ТАБЛИЦЫ.preset_links || [])
    .map(р => Object.assign({}, р, { id: р.short_code }));
  openSharedPreset(код);
  return true;
}""" % (Я, Я)

СНЯТЬ = """() => {
  const полоска = document.getElementById('sharedModeIndicator');
  return {
    правка: canEditPublic(),
    заперто: замокПресетаЗакрыт(),
    замокДоступен: canToggleLock(),
    полоска: (полоска ? (полоска.innerText || '') : '').replace(/\\s+/g, ' ').trim(),
    замокВидно: !!(полоска && полоска.querySelector('svg path[d*="a5 5 0 0 1 10 0"]')),
  };
}"""


def строка(стр, код):
    return спросить(стр, """(код) => {
      const р = (window.__ТАБЛИЦЫ.preset_links || []).find(с => с.short_code === код);
      return р ? JSON.stringify({ spec: р.spec_state, когда: р.updated_at }) : null;
    }""", код)


# Правка пробуется на толщине утепления, а не на галочке позиции, и это
# отдельный урок. Сперва проба нажимала галочку — и молчала на любой сборке:
# позиция без цены не отмечается и на здоровом расчёте («сначала сумма, потом
# галочка»), поэтому «до» и «после» выходили одинаковыми всегда. Толщина —
# три кнопки внутри `.two-col`, то есть внутри запертой зоны, и переключается
# без всяких условий.
ТОЛЩИНА = """() => {
  const к = [...document.querySelectorAll('.thickness-tabs .thick-btn')];
  const и = к.findIndex(б => б.classList.contains('active'));
  return { сколько: к.length, выбрана: и };
}"""


def попробовать_править(стр):
    """Настоящая попытка правки: нажатие по невыбранной кнопке толщины."""
    было = спросить(стр, ТОЛЩИНА) or {}
    if было.get("сколько", 0) < 2:
        return было, было, False
    другая = 0 if было.get("выбрана") != 0 else 1
    try:
        узел = стр.query_selector_all(".thickness-tabs .thick-btn")[другая]
        узел.scroll_into_view_if_needed(timeout=2000)
        узел.click(timeout=2000)
    except Exception:
        pass
    стр.wait_for_timeout(400)
    return было, спросить(стр, ТОЛЩИНА) or {}, True


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            спросить(стр, """() => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
            }""")

            # ── Чужой расчёт ──
            спросить(стр, ОТКРЫТЬ, ЧУЖОЙ_КОД)
            стр.wait_for_timeout(600)
            ч = спросить(стр, СНЯТЬ) or {}
            до = строка(стр, ЧУЖОЙ_КОД)
            было, стало, нажималось = попробовать_править(стр)
            # Запись идёт с задержкой в полторы секунды — ждём дольше.
            спросить(стр, "() => { try { collabSectionChanged('spec'); } catch(e) {} }")
            стр.wait_for_timeout(2200)
            после = строка(стр, ЧУЖОЙ_КОД)

            if ч.get("правка"):
                плохо("чужой расчёт открылся с правом правки — canEditPublic() говорит «да»")
            if not ч.get("заперто"):
                плохо("чужой расчёт открылся незапертым — правящие места отвечают на нажатия")
            if ч.get("замокДоступен"):
                плохо("на чужом расчёте предлагается снять замок — нажатие уйдёт в чужую строку")
            if "только просмотр" not in ч.get("полоска", "").lower():
                плохо("полоска чужого расчёта не говорит «только просмотр»: «%s»"
                      % ч.get("полоска", "")[:80])
            if not ч.get("замокВидно"):
                плохо("на полоске чужого расчёта нет закрытого замка — состояние без причины")
            if not нажималось:
                плохо("кнопок толщины на странице меньше двух — нажимать не на что, "
                      "проба мерила вхолостую")
            elif было.get("выбрана") != стало.get("выбрана"):
                плохо("толщина на чужом расчёте переключилась нажатием — правка не заперта")
            if до != после:
                плохо("строка чужого расчёта в базе изменилась после попытки правки")

            # ── Свой расчёт: правка осталась ──
            спросить(стр, ОТКРЫТЬ, МОЙ_КОД)
            стр.wait_for_timeout(600)
            м = спросить(стр, СНЯТЬ) or {}
            if not м.get("правка"):
                плохо("свой опубликованный расчёт перестал правиться — правило задело своё")
            if м.get("заперто"):
                плохо("свой опубликованный расчёт заперт — правило задело своё")
            if not м.get("замокДоступен"):
                плохо("на своём расчёте пропала кнопка замка")

            # ── Выход: сохранение из чужого делает свой ──
            спросить(стр, ОТКРЫТЬ, ЧУЖОЙ_КОД)
            стр.wait_for_timeout(400)
            # Зовём настоящий savePreset, а не свою копию его внутренностей:
            # иначе проба мерила бы саму себя. Окно с именем отвечает за
            # человека — это единственное, что подменяется.
            спросить(стр, """() => {
              window.__былоПресетов = Object.keys(loadAllPresets()).length;
              window.showPresetNameDialog = (авто, дальше) => дальше('Списано');
            }""")
            спросить(стр, "() => { savePreset(); }")
            стр.wait_for_timeout(1500)
            вышло = спросить(стр, """() => ({
              общийРежим: !!_activeSharedCode,
              прибавилось: Object.keys(loadAllPresets()).length - window.__былоПресетов,
            })""") or {}
            if вышло.get("общийРежим"):
                плохо("после сохранения своего расчёта общий режим не погас — "
                      "новый расчёт остался под чужим замком")
            if вышло.get("прибавилось") != 1:
                плохо("сохранение из чужого расчёта не дало своего пресета")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:200])

            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: чужой расчёт открывается только на просмотр — толщина не "
          "переключается, строка в базе не меняется; своё правится как прежде.")


if __name__ == "__main__":
    главная()
