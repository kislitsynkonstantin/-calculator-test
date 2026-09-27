#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Скрыть прошлые / Показать прошлые» в окне уведомлений.

Константин 27.09.2026: «здесь добавь кнопку „Скрыть/Показать“ прошлые
уведомления. Когда скрываешь, показывает только новые в списке, открываешь —
показывает новые и старые».

Проба держит на 390 и 1440, в «Бланке» и «Модерне»:
  • есть прошлые — в шапке окна кнопка «Скрыть прошлые»; нажатие оставляет
    только новые, окно не закрывается, кнопка говорит «Показать прошлые · N»;
    повторное нажатие возвращает все;
  • выбор помнится: окно закрыли и открыли — прошлые по-прежнему скрыты; все
    уже прочитаны — вместо списка «Новых уведомлений нет. Прошлые скрыты.»;
  • прошлых нет — кнопки нет;
  • кнопка в строке шапки справа, не наезжает на заголовок, поле нажатия 44 px.

    python3 check_bell_old.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


# Уведомления подставляем сами: три после рубежа прочтения, четыре до него.
ПОДГОТОВКА = """(рубеж) => {
  try { localStorage.removeItem('banya_nt_hide_old'); } catch (e) {}
  if (typeof _прошлыеСкрыты !== 'undefined') _прошлыеСкрыты = false;
  const у = (д, т) => ({ когда: д, текст: 'Открыта спецификация <b>' + т + '</b>', пресет: null });
  window.__уведомления = [у('2026-09-25T10:00:00Z', 'Новая 1'), у('2026-09-24T10:00:00Z', 'Новая 2'), у('2026-09-23T10:00:00Z', 'Новая 3'),
    у('2026-09-18T10:00:00Z', 'Старая 1'), у('2026-09-17T10:00:00Z', 'Старая 2'), у('2026-09-16T10:00:00Z', 'Старая 3'), у('2026-09-15T10:00:00Z', 'Старая 4')];
  собратьУведомления = async () => { _уведомления = window.__уведомления.slice(); return _уведомления; };
  appSettings.notifReadAt = рубеж;
}"""

ВИД = """() => {
  const м = document.getElementById('bellMenu');
  const открыто = !!м && getComputedStyle(м).display !== 'none';
  const к = м ? м.querySelector('.nt-tg') : null, з = м ? м.querySelector('.nt-h .t') : null, ш = м ? м.querySelector('.nt-h') : null;
  let поле = 0, наезд = false, внутри = true;
  if (к) { const б = к.getBoundingClientRect(), с = getComputedStyle(к, '::before');
    поле = Math.round(б.height - 2 * (parseFloat(с.top) || 0));
    const бз = з.getBoundingClientRect(), бш = ш.getBoundingClientRect();
    наезд = б.left < бз.right + 6; внутри = б.right <= бш.right - 8 && б.top >= бш.top; }
  return { открыто, строк: м ? м.querySelectorAll('.nt-i').length : 0, новых: м ? м.querySelectorAll('.nt-i.new').length : 0,
           кнопка: к ? к.textContent.trim() : null, пусто: м && м.querySelector('.nt-empty') ? м.querySelector('.nt-empty').textContent.trim() : '',
           поле, наезд, внутри };
}"""


def прогон(бр, порт, ш, ui):
    н = f"[{ш} {ui}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("(ui) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle(ui, false); window.scrollTo(0, 0); }", ui)
    стр.evaluate(ПОДГОТОВКА, "2026-09-20T00:00:00Z")
    стр.evaluate("async () => { await переключитьУведомления(); }"); стр.wait_for_timeout(300)
    в = стр.evaluate(ВИД)
    if в["строк"] != 7 or в["кнопка"] != "Скрыть прошлые":
        НАХОДКИ.append(f"{н} при открытом окне ждали 7 строк и «Скрыть прошлые»: {в}")
    if в["кнопка"] and (в["поле"] < 44 or в["наезд"] or not в["внутри"]):
        НАХОДКИ.append(f"{н} кнопка в шапке: поле {в['поле']} px, наезд на заголовок {в['наезд']}, в пределах шапки {в['внутри']}")
    стр.screenshot(path=str(СНИМКИ / f"bell-old-{ш}-{ui}-all.png"))
    if not в["кнопка"]:
        стр.close(); return
    стр.locator("#bellMenu .nt-tg").click(); стр.wait_for_timeout(250)
    в = стр.evaluate(ВИД)
    if not в["открыто"] or в["строк"] != 3 or в["новых"] != 3 or в["кнопка"] != "Показать прошлые · 4":
        НАХОДКИ.append(f"{н} «Скрыть прошлые»: ждали окно открытым, 3 новые строки и «Показать прошлые · 4»: {в}")
    стр.screenshot(path=str(СНИМКИ / f"bell-old-{ш}-{ui}-new.png"))
    стр.locator("#bellMenu .nt-tg").click(); стр.wait_for_timeout(250)
    в = стр.evaluate(ВИД)
    if в["строк"] != 7 or в["кнопка"] != "Скрыть прошлые":
        НАХОДКИ.append(f"{н} «Показать прошлые» не вернуло все 7: {в}")
    # скрыли, закрыли, открыли снова: всё уже прочитано — только сообщение и счёт
    стр.locator("#bellMenu .nt-tg").click(); стр.wait_for_timeout(200)
    стр.evaluate("async () => { закрытьОкноУведомлений(); await переключитьУведомления(); }"); стр.wait_for_timeout(300)
    в = стр.evaluate(ВИД)
    if в["строк"] != 0 or "Новых уведомлений нет" not in в["пусто"] or в["кнопка"] != "Показать прошлые · 7":
        НАХОДКИ.append(f"{н} выбор не запомнился или пустой список без пояснения: {в}")
    # прошлых нет — кнопки нет
    стр.evaluate("async () => { закрытьОкноУведомлений(); appSettings.notifReadAt = ''; await переключитьУведомления(); }"); стр.wait_for_timeout(300)
    в = стр.evaluate(ВИД)
    if в["кнопка"] is not None or в["строк"] != 7:
        НАХОДКИ.append(f"{н} без прошлых кнопка не нужна и видны все: {в}")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for ui in ("blank",):
                    прогон(бр, порт, ш, ui)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Скрыть прошлые» оставляет только новые и не закрывает окно, «Показать прошлые · N» возвращает все, "
          "выбор помнится, пустой список объяснён, без прошлых кнопки нет — на 390 и 1440, в «Бланке» и «Модерне».")


if __name__ == "__main__":
    главная()
