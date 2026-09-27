#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Публикация ставит пресет под замок — сразу, без мелькания открытого.

Константин 27.09.2026: «Когда нажимаешь опубликовать пресет, замок по
умолчанию закрывай. Чтобы можно было из Моих дальше также редактировать», и
следом: «появляется замок с открытой душкой и потом закрывается. Сделай,
чтобы сразу появлялся закрытый».

Проба держит:
  • первая публикация — строка уходит в базу уже запертой (locked в самой
    записи), а не запирается следом: иначе открытый замок мелькал бы и на
    карточке, и у всех по подписке; ни одна перерисовка карточки не показала
    открытый замок; строка в базе и в памяти страницы заперта; «Загрузить» в
    «Моих» рабочая; сообщение говорит «под замком»;
  • повторная публикация отозванного пресета с открытым замком тоже запирает;
  • запись не легла, а замок перед ней снимали, — замок возвращается.

    python3 check_publish_locked.py
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


ПОДГОТОВКА = """async (отказ) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false);
  selectProjectOption(0); await ждать(600);
  const снимок = collectState();
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  window.__замок = [];
  window.__RPC.set_preset_lock = а => { window.__замок.push(а.p_locked);
    const с = (window.__ТАБЛИЦЫ.preset_links || []).find(r => r.short_code === а.p_code); if (с) с.locked = а.p_locked; return true; };
  window.__RPC.preset_short_code_free = () => true;
  // Что уходит в запись строки, и — по заказу пробы — отказ базы в ней.
  window.__записи = [];
  const былFrom = _sb.from.bind(_sb);
  _sb.from = т => { const з = былFrom(т); if (т !== 'preset_links') return з;
    const u = з.upsert; з.upsert = (зн, н) => { window.__записи.push(JSON.parse(JSON.stringify(зн)));
      if (отказ) return Promise.resolve({ data: null, error: { message: 'отказ пробы' } }); return u.call(з, зн, н); }; return з; };
  window.__ТАБЛИЦЫ.preset_links = [];
  saveAllPresets({ p1: { id: 'p1', name: 'Новый пресет', state: снимок, savedAt: new Date().toISOString() },
                   p2: { id: 'p2', name: 'Отозванный', state: снимок, savedAt: new Date().toISOString(), shortCode: '222222', sharedId: '222222' } });
  _sharedPresets.length = 0;
  const отозван = { short_code: '222222', id: '222222', preset_id: 'p2', author_id: _sbUser.id, author_name: 'Проба', name: 'Отозванный',
    state: снимок, is_public: false, visibility: 'public', locked: отказ, created_at: '2026-09-20T10:00:00Z' };
  _sharedPresets.push(Object.assign({}, отозван)); window.__ТАБЛИЦЫ.preset_links.push(Object.assign({}, отозван));
  try { _общиеЗагружены = true; } catch (e) {}
  openPresetPanel(); await ждать(300); switchPresetTab('my');
  window.__виды = [];
  const набл = new MutationObserver(() => { const з = document.querySelector('#presetList .pcard[data-pid="p1"] .btn-shared-lock');
    if (з) window.__виды.push(з.classList.contains('on') ? 'закрыт' : 'открыт'); });
  набл.observe(document.getElementById('presetList'), { childList: true, subtree: true, attributes: true });
  await publishPreset('p1', 'public'); await ждать(300);
  набл.disconnect();
  const код1 = loadAllPresets().p1.shortCode;
  const р1 = { код: код1, запись: (window.__записи[0] || {}).locked, виды: [...new Set(window.__виды)],
    вБазе: (window.__ТАБЛИЦЫ.preset_links.find(r => r.short_code === код1) || {}).locked,
    вПамяти: (_sharedPresets.find(r => r.short_code === код1) || {}).locked, тосты: window.__тосты.slice(),
    приглушена: (document.querySelector('#presetList .pcard[data-pid="p1"] .pcard-use') || {}).getAttribute?.('aria-disabled') === 'true' };
  window.__замок.length = 0; window.__тосты.length = 0; window.__записи.length = 0;
  await publishPreset('p2', 'public'); await ждать(300);
  const р2 = { запись: (window.__записи[0] || {}).locked, вызовы: window.__замок.slice(),
    вБазе: (window.__ТАБЛИЦЫ.preset_links.find(r => r.short_code === '222222') || {}).locked,
    вПамяти: (_sharedPresets.find(r => r.short_code === '222222') || {}).locked, тосты: window.__тосты.slice() };
  _sb.from = былFrom;
  return { р1, р2 };
}"""

def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for отказ in (False, True):
                н = "[база отказала]" if отказ else "[обычно]"
                стр = бр.new_page(viewport={"width": 1440, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                р = стр.evaluate(ПОДГОТОВКА, отказ)
                print("  " + н, json.dumps(р, ensure_ascii=False)[:600])
                р1, р2 = р["р1"], р["р2"]
                if not отказ:
                    if р1["запись"] is not True:
                        плохо(f"{н} строка уходит в базу открытой и запирается следом — замок мелькнёт открытым: {р1}")
                    if "открыт" in р1["виды"]:
                        плохо(f"{н} во время публикации на карточке мелькнул открытый замок: {р1['виды']}")
                    if not р1["вБазе"] or not р1["вПамяти"]:
                        плохо(f"{н} первая публикация не заперла пресет: {р1}")
                    if р1["приглушена"]:
                        плохо(f"{н} после публикации «Загрузить» в «Моих» приглушена — замок должен быть закрыт")
                    if not any("под замком" in т for т in р1["тосты"]):
                        плохо(f"{н} сообщение о публикации не говорит про замок: {р1['тосты']}")
                    if р2["запись"] is not True or not р2["вБазе"] or not р2["вПамяти"]:
                        плохо(f"{н} повторная публикация с открытым замком не заперла пресет: {р2}")
                else:
                    if not р2["вызовы"] or р2["вызовы"][-1] is not True:
                        плохо(f"{н} запись отказала, а снятый перед ней замок не вернулся: {р2}")
                    if any("под замком" in т for т in р1["тосты"] + р2["тосты"]):
                        плохо(f"{н} при отказе базы сказано «под замком»: {р1['тосты'] + р2['тосты']}")
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
    print("Чисто: публикация пишет строку уже запертой — открытый замок не мелькает; и первая, и повторная ставят "
          "пресет под замок, «Загрузить» в «Моих» рабочая; при отказе записи снятый замок возвращается.")


if __name__ == "__main__":
    главная()
