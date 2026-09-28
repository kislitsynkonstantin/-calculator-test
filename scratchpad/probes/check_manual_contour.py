#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба справки: в бою нет ничего, что написано про тест.

Справка одна на тест и бой. 27.09.2026 менеджеры видели в журнале боевого
калькулятора карточку v2.5.13 «на тесте» (Константин: «на боевом не должно
быть справки журнала и справки теста»). Оболочка справки с тех пор сама узнаёт
контур по адресу калькулятора и в бою удаляет карточку «на тесте» и блоки
data-contour="test", а на тесте — блоки data-contour="prod".

Проба открывает справку так, как её открывает калькулятор, — кадром srcdoc
внутри страницы с настоящим адресом, боевым и тестовым: запросы к этим адресам
перехватываются и в сеть не уходят. В справку подкладываются проверочная
карточка «на тесте» и два абзаца с метками контура. Мерится поведение, а не
разметка: что осталось в документе, что находит поиск, сколько правок в
счёте, какая карточка раскрыта первой.

Двусторонняя: с вырезанным фильтром проба обязана упасть (--без-фильтра).
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import справка  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(найденные[-1])


ТЕСТ_СЛОВО = "Проверочноесловотестовогоконтура"
БОЙ_СЛОВО = "Проверочноесловобоевогоконтура"
КАРТОЧКА = (
    '<div class="upd" id="проба-карточка">\n'
    '  <div class="upd-head"><span class="upd-ver">v9.9.9</span>'
    '<span class="upd-date">01.01.2099</span><span class="upd-state">на тесте</span></div>\n'
    '  <div class="upd-list"><div class="upd-item"><strong>Проверочная правка.</strong> '
    'Только для теста.</div></div>\n'
    '</div>\n')
АБЗАЦЫ = (f'<p class="lead" data-contour="test">{ТЕСТ_СЛОВО} — абзац только для теста.</p>'
          f'<p class="lead" data-contour="prod">{БОЙ_СЛОВО} — абзац только для боя.</p>')

НАХОДКИ = []


def находка(т):
    НАХОДКИ.append(т)


def собрать(без_фильтра):
    м = справка.достать()
    if без_фильтра:
        м2 = re.sub(r"// ── В бою — только то, что в бою есть ──.*?(?=// ── Тема: только от калькулятора ──)",
                    "var справкаНаТесте = true;\n", м, count=1, flags=re.S)
        if м2 == м:
            raise SystemExit("фильтр в оболочке не найден — проба устарела")
        м = м2
    i = м.find('<div class="upd">')
    if i < 0:
        raise SystemExit("в журнале нет карточек")
    м = м[:i] + КАРТОЧКА + м[i:]
    г = re.search(r'id="ch-overview"[^>]*>', м)
    if not г:
        raise SystemExit("нет главы «Обзор»")
    м = м[:г.end()] + АБЗАЦЫ + м[г.end():]
    return м


def родитель(справка_html):
    import json
    return ("<!doctype html><meta charset=utf-8><body style='margin:0'>"
            "<iframe id=f style='width:1200px;height:900px;border:0'></iframe><script>"
            "document.getElementById('f').srcdoc="
            # «</script>» внутри текста справки закрыл бы этот скрипт раньше времени.
            + json.dumps(справка_html).replace("</", "<\\/") + ";</script>")


def осмотр(стр, адрес, html_родителя):
    стр.route(адрес, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8",
                                                       body=html_родителя))
    стр.goto(адрес, wait_until="load")
    # Кадр сперва стоит пустым (about:blank), srcdoc приходит следом: ждём,
    # пока в нём заработает скрипт справки, а не событие загрузки.
    стр.wait_for_function("() => { const f = document.getElementById('f');"
                          " return f && f.contentWindow && typeof f.contentWindow.doSearch === 'function'; }")
    fr = стр.frames[1]
    return fr.evaluate(f"""() => {{
      const карточки = [...document.querySelectorAll('#ch-updates .upd')];
      const тестовые = карточки.filter(к => (к.querySelector('.upd-state')||{{}}).textContent?.trim().toLowerCase() === 'на тесте');
      const первая = карточки[0];
      doSearch({ТЕСТ_СЛОВО!r});
      const найдено_тест = document.querySelectorAll('#srchResults .srch-item').length;
      closeSearch && closeSearch();
      doSearch({БОЙ_СЛОВО!r});
      const найдено_бой = document.querySelectorAll('#srchResults .srch-item').length;
      return {{
        контур: document.documentElement.getAttribute('data-contour'),
        карточек: карточки.length,
        тестовых: тестовые.length,
        первая: первая ? первая.querySelector('.upd-ver').textContent.trim() : '',
        первая_открыта: первая ? первая.classList.contains('open') : false,
        первая_счёт: первая ? (первая.querySelector('.upd-count')||{{}}).textContent : '',
        абзац_тест: document.body.innerText.includes({ТЕСТ_СЛОВО!r}),
        абзац_бой: document.body.innerText.includes({БОЙ_СЛОВО!r}),
        найдено_тест, найдено_бой,
      }};
    }}""")


def main():
    без_фильтра = "--без-фильтра" in sys.argv
    м = собрать(без_фильтра)
    чистая = справка.достать()
    всего_в_базе = len(re.findall(r'<div class="upd"[ >]', чистая))
    тестовых_в_базе = len(re.findall(r'<span class="upd-state">\s*на тесте\s*</span>', чистая))
    with sync_playwright() as p:
        б = p.chromium.launch(executable_path=хром())
        for адрес, бой in (("https://calculator.baniamsk.ru/", True),
                           ("https://test.calculator.baniamsk.ru/", False)):
            стр = б.new_page()
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            р = осмотр(стр, адрес, родитель(м))
            имя = "бой" if бой else "тест"
            print(f"{имя}: {р}")
            if ошибки:
                находка(f"{имя}: ошибки скрипта {ошибки}")
            if р["контур"] != ("prod" if бой else "test"):
                находка(f"{имя}: контур определён как {р['контур']}")
            if бой:
                if р["тестовых"]:
                    находка(f"бой: в журнале {р['тестовых']} карточек «на тесте»")
                if р["первая"] == "v9.9.9":
                    находка("бой: первой стоит проверочная карточка теста")
                if р["абзац_тест"] or р["найдено_тест"]:
                    находка("бой: виден или находится поиском абзац только для теста")
                if not р["абзац_бой"]:
                    находка("бой: пропал абзац для боя")
                if р["карточек"] != всего_в_базе - тестовых_в_базе:
                    находка(f"бой: карточек {р['карточек']}, ждали {всего_в_базе - тестовых_в_базе}")
            else:
                if р["первая"] != "v9.9.9" or not р["первая_открыта"]:
                    находка("тест: проверочная карточка не первая или не раскрыта")
                if not р["абзац_тест"] or not р["найдено_тест"]:
                    находка("тест: не виден или не находится абзац только для теста")
                if р["абзац_бой"] or р["найдено_бой"]:
                    находка("тест: виден абзац, который только для боя")
            if not р["первая_открыта"]:
                находка(f"{имя}: первая карточка журнала свёрнута")
            if not re.match(r"\d+ прав", р["первая_счёт"] or ""):
                находка(f"{имя}: у первой карточки нет счёта правок")
            стр.close()
        б.close()
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ:
            print(" •", н)
        sys.exit(1)
    print("\nЧисто: в бою нет ни карточки «на тесте», ни абзацев теста; на тесте всё на месте.")


if __name__ == "__main__":
    main()
