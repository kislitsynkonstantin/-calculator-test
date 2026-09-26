#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: загрузка — полоской справки.

Константин 26.09.2026: «журнал действий тоже сделай страницу загрузки».

Проба держит на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • пока журнал читается из базы, в ленте полоска загрузки справки: 180×3,
    движется, по центру ленты, в поле зрения, с подписью;
  • надписи «Загружаем…» нет ни в ленте, ни в строке сводки над фильтрами.

    python3 check_actionlog_loader.py
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


СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const былоFrom = _sb.from;
  const висит = () => { const з = { select: () => з, in: () => з, gte: () => з, lt: () => з, eq: () => з, order: () => з,
    limit: () => new Promise(() => {}), then: (ф, о) => new Promise(() => {}) }; return з; };
  _sb.from = t => t === 'events' ? висит() : былоFrom.call(_sb, t);
  try { _alСобытия = []; } catch (e) {}
  openActionLog(); await ждать(400);
  const лента = document.getElementById('alFeed');
  const пол = лента && лента.querySelector('.bm-load');
  const окно = document.getElementById('actionLogOverlay');
  let з = null;
  if (пол) { const r = пол.getBoundingClientRect(), L = лента.getBoundingClientRect(), полоса = пол.querySelector('i');
    з = { ш: Math.round(r.width), в: Math.round(r.height), центрX: Math.round((r.left + r.right) / 2 - (L.left + L.right) / 2),
      видна: r.top >= 0 && r.bottom <= innerHeight, анимация: getComputedStyle(полоса).animationName }; }
  const текст = (окно.textContent || '');
  const итог = { загрузка: з, подпись: (лента.textContent || '').trim(), сводка: document.getElementById('alSub').textContent.trim(),
    осталось: /Загружаем/i.test(текст) };
  _sb.from = былоFrom;
  try { closeActionLog(); } catch (e) {}
  return итог;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тема in ("blank", "light"):
                    for ночь in (False, True):
                        стр = бр.new_page(viewport={"width": ш, "height": 900})
                        ошибки = []
                        стр.on("pageerror", lambda e: ошибки.append(str(e)))
                        стр.add_init_script(ЗАГЛУШКА)
                        стр.add_init_script(ТАБЛИЦЫ_JS)
                        стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                        стр.wait_for_timeout(2500)
                        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                        стр.evaluate(f"() => {{ applyUiStyle('{тема}', false); document.body.classList.toggle('dark', {str(ночь).lower()}); }}")
                        н = f"{ш} {тема} {'ночь' if ночь else 'день'}"
                        try:
                            р = стр.evaluate(СЦЕНАРИЙ)
                        except Exception as e:
                            плохо(f"{н}: сценарий упал: {str(e)[:160]}"); стр.close(); continue
                        if ш == 390 and тема == "blank" and not ночь:
                            print("  " + json.dumps(р, ensure_ascii=False))
                        з = р["загрузка"]
                        if not з: плохо(н + ": пока журнал грузится, полоски загрузки нет")
                        else:
                            if (з["ш"], з["в"]) != (180, 3): плохо(н + f": полоска {з['ш']}×{з['в']}, у справки 180×3")
                            if abs(з["центрX"]) > 2: плохо(н + f": полоска не по центру ленты ({з['центрX']})")
                            if not з["видна"]: плохо(н + ": полоска вне экрана")
                            if з["анимация"] != "bmLoad": плохо(н + ": полоска не движется")
                        if "загружается" not in р["подпись"]: плохо(н + ": у полоски нет подписи")
                        if р["осталось"]: плохо(н + f": в окне осталась надпись «Загружаем…» (сводка: «{р['сводка']}»)")
                        for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                            плохо(f"{н}: ошибка страницы: {о[:160]}")
                        стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: пока журнал действий грузится, в ленте полоска справки по центру с подписью, «Загружаем…» нигде нет — "
          "на 390 и 1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
