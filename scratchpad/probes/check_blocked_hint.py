#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Закрытая опция: подсказка едет со строкой, рамка продолжает полоску.

Константин 26.09.2026, тремя снимками: «это сообщение появляется, почему
заблокировано возле опции. Когда проматываешь страницу — оно остаётся висеть
на том же месте экрана. Пусть остаётся на той же опции» и «когда выбирают
заблокированную опцию — это обрамление сделай, чтобы левая вертикальная
полоска совпадала с левой полоской выделенной опции… получалась одна прямая».

Проба нажимает «Двойную обвязку» при снятом свайно-винтовом фундаменте и держит
на 390 и 1440, в «Бланке» и «Модерне»:
  • подсказка появилась у строки; страницу прокрутили на 120 px — расстояние
    от подсказки до её строки не изменилось (±1 px), подсказка уехала вместе
    со строкой, а не осталась на месте экрана;
  • в «Бланке» у виновника рамка: левая сторона там же (left), той же толщины и
    того же цвета, что полоска выбранной строки, строки выровнены по левому
    краю — вместе это одна прямая; через полторы секунды рамки нет;
  • в «Модерне» по-прежнему обводка.

    python3 check_blocked_hint.py
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
  selectProjectOption(0); await ждать(900);
  if (checkedOptions.f5) { document.getElementById('lbl_f5').click(); await ждать(300); }
  const f6 = document.getElementById('lbl_f6'), f5 = document.getElementById('lbl_f5');
  if (!f6 || !f5 || f6.dataset.blocked !== '1') return { нетСцены: true };
  f6.scrollIntoView({ block: 'center' }); await ждать(300);
  f6.click(); await ждать(250);
  const tip = document.getElementById('exclTooltip');
  const якорь = f5.getBoundingClientRect().top < 60 || f5.getBoundingClientRect().bottom > innerHeight - 40 ? f5 : f6;
  const зазор = () => { const t = tip.getBoundingClientRect(); const r = якорь.getBoundingClientRect(); return Math.round((t.top - r.top) * 10) / 10; };
  const видна = () => tip.style.display === 'block' && tip.getBoundingClientRect().height > 0;
  const доПрокрутки = { видна: видна(), зазор: зазор(), верх: Math.round(tip.getBoundingClientRect().top) };
  const рамка = (() => {
    const п = getComputedStyle(f5, '::after');
    const выбранная = [...document.querySelectorAll('.opt-item.active')].find(x => x.closest('.opts-list') === f5.closest('.opts-list'))
      || document.querySelector('.opt-item.active');
    const ч = выбранная ? getComputedStyle(выбранная, '::before') : null;
    return { класс: f5.classList.contains('opt-culprit'), обводка: f5.style.outline || '',
      есть: п.content !== 'none' && п.content !== '', left: п.left, толщина: п.borderLeftWidth, цвет: п.borderLeftColor,
      полоска: ч ? { left: ч.left, ширина: ч.width, цвет: ч.backgroundColor } : null,
      краяСтрок: выбранная ? Math.abs(выбранная.getBoundingClientRect().left - f5.getBoundingClientRect().left) : null };
  })();
  window.scrollBy(0, 120); await ждать(200);
  const послеПрокрутки = { видна: видна(), зазор: зазор(), верх: Math.round(tip.getBoundingClientRect().top) };
  await ждать(1300);
  const погасла = { класс: f5.classList.contains('opt-culprit'), обводка: f5.style.outline || '' };
  спрятатьЗапрет();
  return { доПрокрутки, послеПрокрутки, рамка, погасла };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for тема in ("blank", "light"):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate(f"() => {{ const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle('{тема}', false); }}")
                    р = стр.evaluate(СЦЕНАРИЙ)
                    н = f"[{ш} {тема}]"
                    print("  " + н, json.dumps(р, ensure_ascii=False)[:700])
                    if р.get("нетСцены"):
                        плохо(н + " «Двойная обвязка» не закрыта — мерить не на чем"); стр.close(); continue
                    д, п = р["доПрокрутки"], р["послеПрокрутки"]
                    if not д["видна"]:
                        плохо(н + " подсказка не появилась")
                    elif not п["видна"] or abs(д["зазор"] - п["зазор"]) > 1:
                        плохо(н + f" подсказка не поехала со строкой: до {д}, после {п}")
                    рм = р["рамка"]
                    if тема == "blank":
                        пол = рм["полоска"] or {}
                        if not рм["класс"] or not рм["есть"]:
                            плохо(н + f" у виновника нет рамки ({рм})")
                        elif (рм["left"] != пол.get("left") or рм["толщина"] != пол.get("ширина")
                              or рм["цвет"] != пол.get("цвет") or (рм["краяСтрок"] or 0) > 0.5):
                            плохо(н + f" левая сторона рамки не продолжает полоску выбранной строки ({рм})")
                        if рм["обводка"]:
                            плохо(н + " в «Бланке» осталась прежняя обводка поверх рамки")
                    else:
                        if not рм["обводка"]:
                            плохо(н + " в «Модерне» пропала обводка виновника")
                    if р["погасла"]["класс"] or р["погасла"]["обводка"]:
                        плохо(н + f" рамка не погасла ({р['погасла']})")
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
    print("Чисто: подсказка о закрытой опции едет со своей строкой при прокрутке; в «Бланке» рамка виновника "
          "продолжает полоску выбранных строк одной прямой и гаснет — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
