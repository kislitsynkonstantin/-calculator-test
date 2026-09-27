#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Мои»: у опубликованного пресета вместо корзины — замок.

Константин 27.09.2026, снимком карточки в «Моих»: «когда пресет публикую,
кнопку „Удалить“ меняй на „Замок“. Когда отзываю (снимаю с публикации),
меняем обратно. Идея в том, что опубликованный пресет нельзя удалить, не
сняв с публикации».

Проба на 390 и 1440, в «Бланке» и «Модерне», держит:
  • у опубликованного корзины нет, на её месте замок в ряду значковых кнопок,
    той же высоты, что соседние; у неопубликованного — корзина и нет замка;
  • замок нажимается: уходит один запрос, и замок встаёт закрытым;
  • удаление опубликованного, позванное не с карточки, отказывает словами;
  • снятая публикация возвращает корзину;
  • карточка не вылезает за край окна.

    python3 check_my_lock_bin.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
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


ПОДГОТОВКА = """async (ui) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle(ui, false);
  selectProjectOption(0); await ждать(600);
  const снимок = collectState();
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  window.__замок = 0;
  window.__RPC = window.__RPC || {};
  window.__RPC.set_preset_lock = () => { window.__замок++; return true; };
  saveAllPresets({
    p1: { id: 'p1', name: 'Опубликованный пресет пробы', state: снимок, savedAt: new Date().toISOString(), shortCode: '111111', sharedId: '111111', publishedAs: 'public' },
    p2: { id: 'p2', name: 'Неопубликованный пресет пробы', state: снимок, savedAt: new Date().toISOString(), shortCode: '222222', sharedId: '222222' },
  });
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '111111', id: '111111', preset_id: 'p1', author_id: _sbUser.id, is_public: true, visibility: 'public', locked: false, created_at: new Date().toISOString() },
                      { short_code: '222222', id: '222222', preset_id: 'p2', author_id: _sbUser.id, is_public: false, visibility: 'public', locked: false, created_at: new Date().toISOString() });
  openPresetPanel(); await ждать(300); switchPresetTab('my'); await ждать(400);
  return true;
}"""

КАРТОЧКИ = """() => {
  const о = ид => { const к = document.querySelector('#presetList .pcard[data-pid="' + ид + '"]'); if (!к) return null;
    const замок = к.querySelector('.pcard-act.btn-shared-lock'), корз = к.querySelector('.pcard-act.danger');
    const сосед = к.querySelector('.pcard-act:not(.btn-shared-lock):not(.danger)');
    const r = к.getBoundingClientRect();
    return { замок: !!замок, закрыт: замок ? замок.classList.contains('on') : null, корзина: !!корз,
             hЗамка: замок ? Math.round(замок.getBoundingClientRect().height) : null, hСоседа: сосед ? Math.round(сосед.getBoundingClientRect().height) : null,
             заКрай: r.right > innerWidth + 0.5 || r.left < -0.5 }; };
  return { p1: о('p1'), p2: о('p2') };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ui in ("blank", "light"):
                for ш in (390, 1440):
                    н = f"[{ui} {ш}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                    стр.evaluate(ПОДГОТОВКА, ui)
                    к = стр.evaluate(КАРТОЧКИ)
                    print("  " + н, json.dumps(к, ensure_ascii=False))
                    p1, p2 = к["p1"], к["p2"]
                    if not p1 or not p2:
                        плохо(f"{н} карточек нет: {к}"); стр.close(); continue
                    if p1["корзина"] or not p1["замок"]:
                        плохо(f"{н} у опубликованного: корзина {p1['корзина']}, замок {p1['замок']} — ждали замок без корзины")
                    if not p2["корзина"] or p2["замок"]:
                        плохо(f"{н} у неопубликованного: корзина {p2['корзина']}, замок {p2['замок']} — ждали корзину без замка")
                    if p1["hЗамка"] and p1["hСоседа"] and abs(p1["hЗамка"] - p1["hСоседа"]) > 1:
                        плохо(f"{н} замок выше или ниже соседних кнопок: {p1['hЗамка']} против {p1['hСоседа']}")
                    if p1["заКрай"] or p2["заКрай"]:
                        плохо(f"{н} карточка за краем окна")
                    стр.screenshot(path=str(СНИМКИ / f"my-lock-{ui}-{ш}.png"))
                    # нажатие по замку
                    зам = стр.locator('#presetList .pcard[data-pid="p1"] .pcard-act.btn-shared-lock')
                    if not зам.count():
                        стр.close(); continue
                    зам.click()
                    стр.wait_for_timeout(600)
                    после = стр.evaluate(КАРТОЧКИ)["p1"]
                    запросов = стр.evaluate("() => window.__замок")
                    if запросов != 1 or not после["закрыт"]:
                        плохо(f"{н} замок: запросов {запросов}, закрыт {после['закрыт']}")
                    # удаление опубликованного в обход карточки
                    стр.evaluate("() => deletePreset('p1')"); стр.wait_for_timeout(300)
                    есть = стр.evaluate("() => !!loadAllPresets().p1 && !document.querySelector('.confirm-overlay[style*=\"flex\"], #confirmDialog[style*=\"flex\"]')")
                    тосты = стр.evaluate("() => window.__тосты")
                    if not есть or not any("отзовите" in т for т in тосты):
                        плохо(f"{н} удаление опубликованного не отказало: пресет {есть}, сообщения {тосты[-2:]}")
                    # снятая публикация — корзина снова
                    стр.evaluate("() => { const в = loadAllPresets(); delete в.p1.publishedAs; saveAllPresets(в); _sharedPresets[0].is_public = false; renderPresetList(); }")
                    стр.wait_for_timeout(300)
                    сн = стр.evaluate(КАРТОЧКИ)["p1"]
                    if not сн["корзина"] or сн["замок"]:
                        плохо(f"{н} после снятия публикации: корзина {сн['корзина']}, замок {сн['замок']}")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"{н} ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в «Моих» у опубликованного вместо корзины замок той же высоты, он нажимается; удаление "
          "опубликованного отказывает словами; снятая публикация возвращает корзину — на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
