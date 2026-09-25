#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Строка порядка в списке проектов стоит на месте при прокрутке списка.

Константин 25.09.2026, снимком открытого списка: «вот эту панель сделай
закреп, когда проматываешь список проектов» — строку «Снять выбор» со
значками порядка. Проба на 390 и 1440 px, в «Модерне» и «Бланке», днём и
ночью:

  • список открыт и прокручен до середины — строка порядка прижата к верху
    списка, над ней нет щели, сквозь которую видно проекты;
  • строка непрозрачна: в её середине и у каждого значка сверху лежит она
    сама, а не проект под ней; значки нажимаются;
  • список открыт на проекте из конца — выбранный проект виден целиком и не
    уходит под строку порядка.

    python3 check_project_list_sticky.py
"""
import functools, http.server, json, os, pathlib, socketserver, sys, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


def плохо(где, т):
    НАХОДКИ.append(f"{где}: {т}")


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ЗАМЕР = r"""() => {
  const л = document.getElementById('projectSelectDropdown');
  const стр = л.querySelector('.cs-sortrow');
  const Л = л.getBoundingClientRect(), С = стр.getBoundingClientRect();
  const верх = Л.top + parseFloat(getComputedStyle(л).borderTopWidth);
  const свой = (x, y) => { const е = document.elementFromPoint(x, y); return !!(е && стр.contains(е)); };
  const значки = [...стр.querySelectorAll('.cs-sbtn')].map(б => { const r = б.getBoundingClientRect(); return свой(r.left + r.width / 2, r.top + r.height / 2); });
  const щель = document.elementFromPoint(С.left + 40, верх + 1);
  return { прокрутка: л.scrollTop, из: л.scrollHeight - л.clientHeight, отступ: +(С.top - верх).toFixed(1),
           середина: свой(С.left + С.width / 2, С.top + С.height / 2), значки,
           щельПроект: !!(щель && щель.closest('.custom-select-option') && !стр.contains(щель)) };
}"""


def проверить(бр, порт, ш, в, бланк, ночь):
    где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    всего = стр.evaluate("""([бланк, ночь]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
      // В наборе для проб два проекта — список не прокручивается. Дописываем
      // копии первого под другими именами, как длинный каталог в бою.
      const образец = PROJECTS[0];
      for (let i = 1; i <= 18; i++) { const к = образец.slice(); к[0] = 'Проба проект ' + i + ' 6×' + (4 + i); PROJECTS.push(к); }
      populateProjectSelect('');
      selectProjectOption(0);
      return document.querySelectorAll('#projectSelectDropdown .custom-select-option:not(.custom-select-deselect)').length;
    }""", [бланк, ночь])
    стр.wait_for_timeout(400)
    стр.evaluate("() => document.getElementById('projectSelectTrigger').scrollIntoView({block:'start'})")
    стр.evaluate("() => scrollBy(0, -120)")
    стр.evaluate("() => toggleProjectDropdown()")
    стр.wait_for_timeout(300)
    стр.evaluate("() => { const л = document.getElementById('projectSelectDropdown'); л.scrollTop = (л.scrollHeight - л.clientHeight) / 2; }")
    стр.wait_for_timeout(200)
    з = стр.evaluate(ЗАМЕР)
    if з["из"] < 40:
        плохо(где, f"список не прокручивается ({всего} проектов) — проба ничего не проверила")
    if abs(з["отступ"]) > 1:
        плохо(где, f"строка порядка не у верха списка при прокрутке {з['прокрутка']:.0f}: отступ {з['отступ']} px")
    if not з["середина"] or not all(з["значки"]):
        плохо(где, f"строку порядка перекрывают проекты: середина {з['середина']}, значки {з['значки']}")
    if з["щельПроект"]:
        плохо(где, "над строкой порядка щель, в ней виден проект")
    # Выбранный проект из конца списка — не под строкой.
    стр.evaluate("() => { toggleProjectDropdown(); const н = document.querySelectorAll('#projectSelectDropdown .custom-select-option:not(.custom-select-deselect)').length; selectProjectOption(н - 1); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => toggleProjectDropdown()")
    стр.wait_for_timeout(400)
    п = стр.evaluate("""() => { const л = document.getElementById('projectSelectDropdown');
      const с = л.querySelector('.custom-select-option.selected'), р = л.querySelector('.cs-sortrow');
      if (!с) return null; const a = с.getBoundingClientRect(), b = р.getBoundingClientRect(), Л = л.getBoundingClientRect();
      return { под: +(b.bottom - a.top).toFixed(1), низ: +(a.bottom - Л.bottom).toFixed(1) }; }""")
    if not п:
        плохо(где, "выбранный проект в списке не отмечен")
    elif п["под"] > 0.5 or п["низ"] > 0.5:
        плохо(где, f"выбранный проект виден не целиком: под строкой {п['под']} px, ниже списка {п['низ']} px")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()
    print(f"  {где}: проектов {всего}, прокрутка {з['прокрутка']:.0f}/{з['из']}, отступ строки {з['отступ']}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 844), (1440, 900)):
                        try:
                            проверить(бр, порт, ш, в, бланк, ночь)
                        except Exception as e:
                            плохо(f"{бланк}/{ночь}/{ш}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: строка порядка прижата к верху прокрученного списка, непрозрачна и нажимается; "
          "выбранный проект при открытии виден целиком.")


if __name__ == "__main__":
    главная()
