#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цвет оформления ставится до первого кадра — без бирюзовой вспышки.

Константин 24.09.2026: «когда калькулятор только грузится — сразу мелькает
бирюзовая тема, потом ставится та, что стоит в настройках. Делай проверку и
сразу грузи нужную. Так раньше было с темой». Тон ставил loadSettings() из
общего скрипта в конце документа, а браузер к этому времени уже рисовал
страницу бирюзовой.

Проба смотрит на страницу в тот миг, когда разборщик дошёл до шапки, — общий
скрипт ещё не выполнен, loadSettings() ещё не существует:

  • сохранённый синий уже стоит на корне, и фирменная переменная уже синяя;
  • логотип в этот миг скрыт, а не бирюзовый; после загрузки — виден и
    перекрашен;
  • бирюза по умолчанию ничего не скрывает и признака на корне не ставит;
  • снятый цвет (бордо) ранний шаг не признаёт — как и текущийТон();
  • тёмная тема и «Бланк» по-прежнему стоят с первого кадра.

    python3 check_tone_flash.py
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
    к.log_message = lambda *а, **кк: None
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


# Снимок в миг, когда в документе появилась шапка с логотипом: это заведомо
# раньше общего скрипта, где живут loadSettings() и applyTone().
НАБЛЮДАТЕЛЬ = """(() => {
  window.__ранний = null;
  const н = new MutationObserver(() => {
    const лого = document.getElementById('headerLogo');
    if (!лого || window.__ранний) return;
    const кс = getComputedStyle(document.documentElement);
    window.__ранний = {
      тон: document.documentElement.dataset.tone || '',
      бренд: кс.getPropertyValue('--br-28').trim(),
      видно: getComputedStyle(лого).visibility,
      тёмная: document.body.classList.contains('dark'),
      бланк: document.body.classList.contains('ui-blank'),
      общийСкрипт: typeof loadSettings === 'function',
    };
    н.disconnect();
  });
  н.observe(document, { childList: true, subtree: true });
})();"""

ПОСЛЕ = """() => {
  const лого = document.getElementById('headerLogo');
  return {
    тон: document.documentElement.dataset.tone || '',
    готово: document.documentElement.dataset.toneReady || '',
    видно: getComputedStyle(лого).visibility,
    перекрашен: лого.src !== _LOGO_DARK && лого.src !== _LOGO_LIGHT,
    бренд: getComputedStyle(document.documentElement).getPropertyValue('--br-28').trim(),
  };
}"""


def прогон(бр, порт, настройки):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script("try { localStorage.setItem('appSettings_v1', "
                        + json.dumps(json.dumps(настройки, ensure_ascii=False), ensure_ascii=False)
                        + "); } catch (e) {}")
    стр.add_init_script(НАБЛЮДАТЕЛЬ)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    ранний = стр.evaluate("() => window.__ранний") or {}
    после = стр.evaluate(ПОСЛЕ)
    стр.close()
    return ранний, после


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            # Бирюза для сравнения: какой фирменный цвет у неё.
            р0, п0 = прогон(бр, порт, {"uiStyle": "blank", "themeMode": "light"})
            бирюза = п0.get("бренд")
            if р0.get("общийСкрипт"):
                плохо("снимок сделан слишком поздно — общий скрипт уже выполнен, проба ничего не меряет")
            if р0.get("тон") or р0.get("видно") != "visible":
                плохо(f"бирюза по умолчанию: на корне «{р0.get('тон')}», логотип {р0.get('видно')} — ничего скрывать не надо")

            р, п = прогон(бр, порт, {"uiStyle": "blank", "themeMode": "dark", "tone": "blue"})
            if р.get("тон") != "blue":
                плохо(f"первый кадр без выбранного цвета: на корне «{р.get('тон')}» вместо «blue»")
            if р.get("бренд") == бирюза or not р.get("бренд"):
                плохо(f"первый кадр бирюзовый: фирменная переменная {р.get('бренд')} (у бирюзы {бирюза})")
            if р.get("видно") != "hidden":
                плохо("логотип в первом кадре виден — он ещё бирюзовый")
            if not (р.get("тёмная") and р.get("бланк")):
                плохо("тёмная тема или «Бланк» больше не стоят с первого кадра")
            if п.get("видно") != "visible" or not п.get("готово"):
                плохо(f"после загрузки логотип {п.get('видно')}, признак готовности «{п.get('готово')}»")
            if not п.get("перекрашен"):
                плохо("после загрузки логотип остался бирюзовым")
            if п.get("бренд") != р.get("бренд"):
                плохо(f"цвет в первом кадре ({р.get('бренд')}) и после загрузки ({п.get('бренд')}) разошёлся")

            р2, п2 = прогон(бр, порт, {"uiStyle": "blank", "themeMode": "light", "tone": "wine"})
            if р2.get("тон") or р2.get("видно") != "visible":
                плохо(f"снятый цвет признан ранним шагом: на корне «{р2.get('тон')}», логотип {р2.get('видно')}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: сохранённый цвет стоит с первого кадра, логотип до перекраски скрыт, а потом виден "
          "в тоне; бирюза ничего не скрывает, снятый цвет не признаётся, тема и «Бланк» на месте.")


if __name__ == "__main__":
    главная()
