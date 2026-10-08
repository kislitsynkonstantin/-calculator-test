#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Реквизиты: в полях «Менеджер» и «Заказчик» цифры не пишутся.

Константин 26.09.2026, снимком реквизитов с телефоном после фамилии менеджера:
«в полях Менеджер и Заказчик запрети писать цифры».

Проба на 390, настоящим набором с клавиатуры, держит:
  • набранные цифры в оба поля не попадают, буквы и дефис остаются;
  • цифра, набранная в середине, не сбивает курсор: следующая буква встаёт
    туда же, куда встала бы без неё;
  • вставленный телефон снимается целиком, дефис в фамилии остаётся;
  • сообщение одно на серию нажатий, а не на каждую цифру;
  • номер договора цифры принимает, как и прежде;
  • расчёт, сохранённый до запрета с телефоном в «Менеджере», открывается без
    телефона: тот уходил в шапку печати (Константин, 08.10.2026).

    python3 check_names_no_digits.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []


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
            стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              selectProjectOption(0); await new Promise(r => setTimeout(r, 700));
              window.__тосты = []; const с = window.showToast; window.showToast = т => { window.__тосты.push(String(т)); }; }""")
            for ид in ("managerName", "clientName"):
                п = стр.locator("#" + ид)
                п.scroll_into_view_if_needed()
                п.fill("")
                стр.evaluate("() => { window.__тосты = []; }")
                п.click()
                стр.keyboard.type("Петров Пётр 8-900-000-00-00", delay=5)
                з = п.input_value()
                if any(ц.isdigit() for ц in з):
                    плохо(f"[{ид}] набранные цифры остались: «{з}»")
                if not з.startswith("Петров Пётр"):
                    плохо(f"[{ид}] буквы пострадали: «{з}»")
                тостов = стр.evaluate("() => window.__тосты.filter(т => /цифры/.test(т)).length")
                if тостов != 1:
                    плохо(f"[{ид}] сообщений о цифрах {тостов} — ждали одно на серию")
                # цифра в середине не сбивает курсор
                п.fill("Иванов Пётр")
                стр.evaluate(f"() => {{ const п = document.getElementById('{ид}'); п.focus(); п.setSelectionRange(6, 6); }}")
                стр.keyboard.type("7а", delay=5)
                з2 = п.input_value()
                if з2 != "Иванова Пётр":
                    плохо(f"[{ид}] после цифры в середине курсор сбился: «{з2}» — ждали «Иванова Пётр»")
                # вставка
                п.fill("")
                п.click()
                стр.evaluate(f"""() => {{ const п = document.getElementById('{ид}');
                  п.setRangeText('Сидоров +7 (999) 123', п.selectionStart, п.selectionEnd, 'end');
                  п.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertFromPaste' }})); }}""")
                з3 = п.input_value()
                if з3.strip() != "Сидоров":
                    плохо(f"[{ид}] вставка оставила от телефона «{з3}» — ждали «Сидоров»")
                п.fill("")
                п.click()
                стр.keyboard.type("Салтыков-Щедрин", delay=5)
                if п.input_value() != "Салтыков-Щедрин":
                    плохо(f"[{ид}] дефис в фамилии не устоял: «{п.input_value()}»")
                print(f"  [{ид}] набор «{з}», середина «{з2}», вставка «{з3}», сообщений {тостов}")
            # Запись до запрета: телефон в «Менеджере» лежит в снимке расчёта.
            # Открытие снимает его, имя остаётся; «Заказчик» не трогается.
            о = стр.evaluate("""async () => {
              const с = collectState(); с.manager = 'Петров Пётр 8-900-000-00-00'; с.client = 'Сидоров Иван';
              restoreState(с); await new Promise(r => setTimeout(r, 300));
              return { м: document.getElementById('managerName').value, з: document.getElementById('clientName').value }; }""")
            if о["м"] != "Петров Пётр":
                плохо(f"открытый расчёт с телефоном в «Менеджере» держит «{о['м']}» — ждали «Петров Пётр»")
            if о["з"] != "Сидоров Иван":
                плохо(f"открытие расчёта задело «Заказчика»: «{о['з']}»")
            print(f"  [открытие] менеджер «{о['м']}», заказчик «{о['з']}»")
            н = стр.locator("#contractNumber")
            if н.count():
                н.scroll_into_view_if_needed(); н.fill(""); н.click(); стр.keyboard.type("12345", delay=5)
                if н.input_value() != "12345":
                    плохо(f"номер договора не принял цифры: «{н.input_value()}»")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо(f"ошибка страницы: {о[:160]}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в «Менеджере» и «Заказчике» цифры не пишутся ни набором, ни вставкой, курсор на месте, "
          "сообщение одно на серию; номер договора цифры принимает; открытый расчёт с телефоном в «Менеджере» "
          "его теряет.")


if __name__ == "__main__":
    главная()
