#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снятые позиции бруса: укладка плитки и винилового ламината, фиброцементные плиты.

Константин 14.10.2026, двумя снимками правок Анатолия: «Вот эти две правки в
брусе сделай» — во «Внутренней отделке» убрать «Укладка плитки» и «Укладка
винилового ламината», в «Парном отделении» — фиброцементные плиты за печкой,
прямые и угловые. В базе им поставлен статус legacy (сразу и в бою), в файле —
`ОПЦИИ_СНЯТЫ`, чтобы их не показывал и режим «Старые».

Держит, на брусе:
  • в новом расчёте строк нет;
  • в режиме «Старые» строк тоже нет;
  • старый расчёт, где позиция отмечена, открывается с ней: строка видна,
    отмечена, её цена — в сумме раздела.

    python3 check_glulam_removed.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
СНЯТЫЕ = {"kb_i12": ("interior", "Укладка плитки", 44800), "kb_i13": ("interior", "Укладка винилового ламината", 3850),
          "kb_s25": ("steam", "Фиброцементные плиты (фасад за печкой)", 34000),
          "kb_s26": ("steam", "Фиброцементные плиты, угловой вариант (фасад за печкой)", 53500)}
ФИКСТУРА["pricing_options"] += [{"product": "glulam", "option_id": и, "name": н, "section": р, "included": False,
                                 "price": ц, "formula": None, "status": "legacy", "sort": 900 + к}
                                for к, (и, (р, н, ц)) in enumerate(СНЯТЫЕ.items())]
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])
ВИДНЫ = "(ид) => ид.filter(и => { const э = document.getElementById('lbl_' + и); return !!э && э.getClientRects().length > 0; })"

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1000})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }""")
    стр.wait_for_timeout(600)
    ид = list(СНЯТЫЕ)
    факт(стр.evaluate("() => currentTech") == "glulam", "расчёт бруса открыт")
    в = стр.evaluate(ВИДНЫ, ид)
    факт(not в, f"в новом расчёте снятых строк нет: {в}")
    стр.evaluate("() => { setOptionPricingMode('legacy'); }"); стр.wait_for_timeout(500)
    в = стр.evaluate(ВИДНЫ, ид)
    факт(not в, f"в режиме «Старые» снятых строк нет: {в}")
    стр.evaluate("() => { setOptionPricingMode('new'); }"); стр.wait_for_timeout(400)
    # Старый расчёт: плитка и угловые плиты отмечены.
    сост = стр.evaluate("() => { const с = collectState(); с.checkedOptions = Object.assign({}, с.checkedOptions, { kb_i12: true, kb_s26: true }); return с; }")
    стр.evaluate("(с) => { restoreState(с); calc(); }", сост); стр.wait_for_timeout(700)
    р = стр.evaluate("""() => ({ видны: ['kb_i12', 'kb_s26'].filter(и => { const э = document.getElementById('lbl_' + и); return !!э && э.getClientRects().length > 0; }),
      отмечены: ['kb_i12', 'kb_s26'].filter(и => checkedOptions[и] === true),
      прочие: ['kb_i13', 'kb_s25'].filter(и => { const э = document.getElementById('lbl_' + и); return !!э && э.getClientRects().length > 0; }) })""")
    факт(р["видны"] == ["kb_i12", "kb_s26"] and р["отмечены"] == ["kb_i12", "kb_s26"] and not р["прочие"],
         f"старый расчёт открывается с отмеченными снятыми, неотмеченных нет: {р}")
    факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: укладка плитки и винилового ламината и фиброцементные плиты бруса сняты; старые расчёты их сохраняют.")
