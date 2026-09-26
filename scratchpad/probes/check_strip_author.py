#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полоска открытого общего пресета называет автора.

Константин 26.09.2026, снимком полоски внизу экрана: «в этой полоске допиши
чей пресет — автора».

Проба держит на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • у чужого пресета в строке состояния стоит автор — полностью на широком
    экране, «Имя Ф.» на телефоне; у своего — «ваш»;
  • строка состояния не обрезана: «заблокирован» и значок замка видны целиком,
    текст не уходит за край строки (scrollWidth не больше clientWidth);
  • автор стоит между «Общий пресет» и состоянием, а не отдельной строкой:
    строк в полоске на телефоне по-прежнему две.

    python3 check_strip_author.py
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



СЦЕНАРИЙ = """async ([свой, имяАвтора]) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const я = _sbUser && _sbUser.id;
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '235788', name: 'D1_Хай-тек баня «Виго» 7,7x8,2 · 24.09.26', author_name: имяАвтора,
    author_id: свой ? я : 'u-другой', is_public: true, visibility: 'public', locked: true,
    created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 4600000, tech: 'frame' } });
  _activeSharedCode = '235788';
  updateSharedModeIndicator(); await ждать(250);
  const п = document.getElementById('sharedModeIndicator');
  if (!п) return { нет: true };
  const с = п.querySelector('.si-status');
  const видимый = (el) => el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().width > 0;
  const видно = [...с.querySelectorAll('span')].filter(видимый).map(x => x.textContent).join('|');
  const замок = с.querySelector('svg'); const зк = замок ? замок.getBoundingClientRect() : null, ск = с.getBoundingClientRect();
  const И = п.querySelector('.si-name').getBoundingClientRect();
  const строк = Math.abs((И.top + И.bottom) / 2 - (ск.top + ск.bottom) / 2) > 6 ? 2 : 1;
  const r = { текст: (с.innerText || '').replace(/\\s+/g, ' ').trim(), обрезана: с.scrollWidth > с.clientWidth + 1,
    замокВиден: !!(зк && зк.right <= ск.right + 1 && зк.width > 0), строк, высота: Math.round(п.getBoundingClientRect().height) };
  _activeSharedCode = null; updateSharedModeIndicator();
  return r;
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
                        н = f"[{ш} {тема} {'ночь' if ночь else 'день'}]"
                        for свой, имя in ((False, "Константин Константинопольский"), (True, "Проба")):
                            р = стр.evaluate(СЦЕНАРИЙ, [свой, имя])
                            if ш == 390 and тема == "blank" and not ночь:
                                print("  " + н, "свой" if свой else "чужой", json.dumps(р, ensure_ascii=False))
                            if р.get("нет"):
                                плохо(н + " полоски нет"); continue
                            надо = "ваш" if свой else (имя if ш >= 900 else "Константин К.")
                            if надо not in р["текст"]:
                                плохо(н + f" {'свой' if свой else 'чужой'}: в полоске нет «{надо}» ({р['текст']!r})")
                            if "заблокирован" not in р["текст"] or р["обрезана"] or not р["замокВиден"]:
                                плохо(н + f" строка состояния обрезана ({р})")
                            if ш < 900 and р["строк"] != 2:
                                плохо(н + f" на телефоне строк {р['строк']}, а не две")
                        for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                            плохо(f"{н} ошибка страницы: {о[:160]}")
                        стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: полоска называет автора — полностью на широком экране, «Имя Ф.» на телефоне, «ваш» у своего; "
          "строка состояния не обрезана, строк на телефоне две — на 390 и 1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
