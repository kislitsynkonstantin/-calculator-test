#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""База знаний идёт за цветом оформления калькулятора.

Константин 24.09.2026, снимком базы знаний при синем калькуляторе: «в базе
знаний» цвет не поменялся. База — отдельный сайт (knowledge-baniamsk) в кадре
калькулятора; тон приходит сообщением `{type: 'tone', shift}` и перекрашивает
страницу той же функцией, что аналитику.

Проба открывает страницу базы из соседнего репозитория, днём и ночью, на 390 и
1440 px, и меряет отрисовку:

  • обработчик сообщения «tone» на месте и зовёт перекраску;
  • сдвиг 31° (синий) — на отрисовке не остаётся ни одного бирюзового цвета
    (цвет, фон, рамка, заливка, обводка), включая то, что страница дорисует
    после перекраски;
  • сдвиг 0 — таблицы стилей и атрибуты возвращаются байт в байт.

    python3 check_kb_tone.py
"""
import functools
import http.server
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

БАЗА = pathlib.Path(os.environ.get("BM_KB_ROOT", "/home/user/knowledge-baniamsk"))
НАХОДКИ = []

СЧЁТ = """() => {
  const бирюза = (с) => {
    const ч = (с.match(/\\d+(\\.\\d+)?/g) || []).map(Number);
    if (ч.length < 3 || (ч.length > 3 && ч[3] === 0)) return false;
    const [r, g, b] = ч, M = Math.max(r, g, b), m = Math.min(r, g, b);
    if (M - m < 6) return false;
    let h = M === r ? ((g - b) / (M - m)) % 6 : M === g ? (b - r) / (M - m) + 2 : (r - g) / (M - m) + 4;
    h = (h * 60 + 360) % 360;
    return h >= 175 && h <= 195;
  };
  let всего = 0, бир = 0; const примеры = [];
  document.querySelectorAll('*').forEach(э => {
    const с = getComputedStyle(э);
    ['color', 'backgroundColor', 'borderTopColor', 'borderLeftColor', 'fill', 'stroke'].forEach(к => {
      const в = с[к]; if (!в || в === 'none') return;
      всего += 1;
      if (бирюза(в)) { бир += 1; if (примеры.length < 3) примеры.push((э.className || э.tagName) + ' ' + к + ' ' + в); }
    });
  });
  return { всего: всего, бир: бир, примеры: примеры };
}"""

СЛЕПОК = """() => JSON.stringify({
  стили: [...document.querySelectorAll('style')].map(с => с.textContent),
  атр: [...document.querySelectorAll('[style],[fill],[stroke]')].map(э =>
    ['style', 'fill', 'stroke'].map(а => э.getAttribute(а)).join('|')),
})"""


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(БАЗА))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def главная():
    текст = (БАЗА / "index.html").read_text(encoding="utf-8")
    if "e.data.type === 'tone'" not in текст or "перекраситьПоТону(document" not in текст:
        НАХОДКИ.append("в базе знаний нет обработчика сообщения «tone»")
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ночь in (False, True):
                for ш, в in ((390, 844), (1440, 900)):
                    где = f"{'ночь' if ночь else 'день'} · {ш}px"
                    к = бр.new_context(viewport={"width": ш, "height": в}, color_scheme="dark" if ночь else "light")
                    стр = к.new_page()
                    ошибки = []
                    стр.on("pageerror", lambda e, о=ошибки: о.append(str(e)))
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(1500)
                    стр.evaluate("(н) => { document.body.classList.remove('dark','light'); document.body.classList.add(н ? 'dark' : 'light'); }", ночь)
                    до = стр.evaluate(СЧЁТ)
                    слепок = стр.evaluate(СЛЕПОК)
                    if not до["бир"]:
                        НАХОДКИ.append(f"[{где}] бирюзы нет и до перекраски — проверять нечего")
                    try:
                        стр.evaluate("() => перекраситьПоТону(document, 31)")
                    except Exception as e:
                        НАХОДКИ.append(f"[{где}] перекраски в базе нет: {e!s:.120}")
                        к.close()
                        continue
                    стр.wait_for_timeout(200)
                    после = стр.evaluate(СЧЁТ)
                    if после["бир"]:
                        НАХОДКИ.append(f"[{где}] при синем осталось {после['бир']} бирюзовых цветов: {после['примеры']}")
                    # дорисованное позже
                    стр.evaluate("""() => { const д = document.createElement('div'); д.id = 'проба-тона';
                      д.style.cssText = 'background:#1e6c72;color:#3db0ba;width:20px;height:20px';
                      document.body.appendChild(д); }""")
                    стр.wait_for_timeout(200)
                    поздний = стр.evaluate("() => getComputedStyle(document.getElementById('проба-тона')).backgroundColor")
                    if поздний == "rgb(30, 108, 114)":
                        НАХОДКИ.append(f"[{где}] дорисованное после перекраски осталось бирюзовым")
                    стр.evaluate("() => document.getElementById('проба-тона').remove()")
                    стр.evaluate("() => перекраситьПоТону(document, 0)")
                    стр.wait_for_timeout(200)
                    if стр.evaluate(СЛЕПОК) != слепок:
                        НАХОДКИ.append(f"[{где}] сдвиг 0 не вернул стили байт в байт")
                    # Библиотека базы данных грузится с CDN, закрытого в контейнере:
                    # эта ошибка — среда, а не страница.
                    ошибки = [о for о in ошибки if "supabase is not defined" not in о]
                    if ошибки:
                        НАХОДКИ.append(f"[{где}] ошибки страницы: " + "; ".join(ошибки)[:200])
                    print(f"  {где}: бирюзовых до {до['бир']}, при синем {после['бир']}")
                    к.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: база знаний по сообщению тона перекрашивается целиком, дорисованное тоже, "
          "а сдвиг 0 возвращает стили байт в байт.")


if __name__ == "__main__":
    главная()
