#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Напоминание «Пресет не сохранён» — по содержимому и по центру на любом экране.

Константин 25.09.2026, снимками телефона стоя и лёжа: «полоска на
горизонтальном нормально, а на вертикальном почему так растягивается». До
560 px полоска вставала во всю ширину (left:10px; right:10px), крестик уезжал
к правому краю, а посередине висела пустота. Проба на 390×844, 844×390, 768 и
1440 px, в «Модерне» и «Бланке»:

  • полоска не шире своего содержимого: между кнопкой и крестиком нет
    растяжки — зазор такой же, как между остальными частями;
  • стоит по центру окна (разница полей не больше 1 px) и не выходит за окно;
  • поля нажатия кнопки «Сохранить» и крестика не пересекаются;
  • подпись не обрезана отточием, если места хватает.

    python3 check_save_strip.py
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
СНИМКИ = os.environ.get("BM_SHOTS")


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
  const п = document.getElementById('saveReminder');
  if (!п || !п.getClientRects().length) return null;
  const r = п.getBoundingClientRect();
  const дети = [...п.children].filter(е => е.getClientRects().length).map(е => е.getBoundingClientRect());
  const зазоры = дети.slice(1).map((д, i) => +(д.left - дети[i].right).toFixed(1));
  const поле = (е) => { const b = е.getBoundingClientRect(), st = getComputedStyle(е, '::before');
    const l = parseFloat(st.left) || 0, rr = parseFloat(st.right) || 0;
    return st.content !== 'none' && st.position === 'absolute' ? [b.left + l, b.right - rr] : [b.left, b.right]; };
  const go = п.querySelector('.sv-go'), x = п.querySelector('.sv-x');
  const [, goR] = поле(go), [xL] = поле(x);
  const т = п.querySelector('.sv-txt');
  return { ширина: r.width, левое: r.left, правое: innerWidth - r.right, зазоры,
           наложение: goR - xL, обрезана: т.scrollWidth > т.clientWidth + 1 };
}"""


def проверить(бр, порт, ш, в, бланк):
    где = f"{'Бланк' if бланк else 'Модерн'} · {ш}×{в}"
    к = бр.new_context(viewport={"width": ш, "height": в}, has_touch=ш < 900, is_mobile=ш < 900)
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""(бланк) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      selectProjectOption(0);
      обновитьНапоминаниеСохранить();
    }""", бланк)
    стр.wait_for_timeout(600)
    з = стр.evaluate(ЗАМЕР)
    if СНИМКИ:
        стр.screenshot(path=f"{СНИМКИ}/напоминание-{'бланк' if бланк else 'модерн'}-{ш}x{в}.png")
    к.close()
    if not з:
        плохо(где, "напоминание не показалось"); return
    if max(з["зазоры"]) > min(з["зазоры"]) + 4:
        плохо(где, f"полоска растянута: зазоры между частями {з['зазоры']}")
    if abs(з["левое"] - з["правое"]) > 1:
        плохо(где, f"не по центру: слева {з['левое']:.1f}, справа {з['правое']:.1f}")
    if з["левое"] < 0 or з["правое"] < 0:
        плохо(где, "полоска выходит за окно")
    if з["наложение"] > 0:
        плохо(где, f"поля нажатия «Сохранить» и крестика пересекаются на {з['наложение']:.1f} px")
    if з["обрезана"]:
        плохо(где, "подпись обрезана отточием")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    print(f"  {где}: ширина {з['ширина']:.0f}, поля {з['левое']:.0f}/{з['правое']:.0f}, зазоры {з['зазоры']}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ш, в in ((390, 844), (844, 390), (768, 1024), (1440, 900)):
                    try:
                        проверить(бр, порт, ш, в, бланк)
                    except Exception as e:
                        плохо(f"{бланк}/{ш}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: напоминание «Пресет не сохранён» по содержимому и по центру на любом экране, "
          "поля нажатия не пересекаются, подпись целиком.")


if __name__ == "__main__":
    главная()
