#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Публикация ставит пресет под замок — сразу, без мелькания открытого.

Константин 27.09.2026: «Когда нажимаешь опубликовать пресет, замок по
умолчанию закрывай. Чтобы можно было из Моих дальше также редактировать», и
следом: «появляется замок с открытой душкой и потом закрывается. Сделай,
чтобы сразу появлялся закрытый».

Следом — снимок «new row violates row-level security policy for table
"preset_links"»: (69) писала строку сразу запертой, а правило доступа это
запрещает. Прежняя проба правила не знала и пропустила отказ.

Проба держит, на заглушке с правилом доступа как в базе (обновить можно
только открытую строку, и новая строка обязана остаться открытой) и с эхом
подписки, приходящим после конца публикации:
  • новый пресет, пресет с кодом (строка есть, не опубликована) и отозванный
    под замком — все три публикуются и встают под замок, в базе и в памяти;
  • ни одна перерисовка карточки, в том числе между эхом записи и эхом замка,
    не показала открытый замок; сообщение говорит «под замком»;
  • замок не встал — сообщение так и говорит, страница пресет не запирает;
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


ПОДГОТОВКА = """async (режим) => {
  const отказ = режим === 'отказ', безЗамка = режим === 'замок';
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false);
  selectProjectOption(0); await ждать(600);
  const снимок = collectState();
  window.__тосты = []; window.showToast = т => window.__тосты.push(String(т));
  window.__замок = [];
  const строка = к => (window.__ТАБЛИЦЫ.preset_links || []).find(r => r.short_code === к);
  // Эхо подписки: база рассылает строку такой, какой она легла, с задержкой —
  // и эхо может прийти уже после того, как публикация закончилась.
  const эхо = (вид, было, стало, мс) => { const н = JSON.parse(JSON.stringify(стало)), с = было ? JSON.parse(JSON.stringify(было)) : null;
    setTimeout(() => приходОбщего({ eventType: вид, new: н, old: с }), мс); };
  window.__RPC.set_preset_lock = а => { window.__замок.push(а.p_locked);
    if (безЗамка && а.p_locked) return false;
    const с = строка(а.p_code); if (с) { const было = { ...с }; с.locked = а.p_locked; эхо('UPDATE', было, с, 260); } return true; };
  window.__RPC.preset_short_code_free = () => true;
  window.__записи = [];
  const былFrom = _sb.from.bind(_sb);
  _sb.from = т => { const з = былFrom(т); if (т !== 'preset_links') return з;
    const u = з.upsert; з.upsert = (зн, н) => { window.__записи.push(JSON.parse(JSON.stringify(зн)));
      if (отказ) return Promise.resolve({ data: null, error: { message: 'отказ пробы' } });
      // Правило доступа базы, как оно есть: обновить можно только открытую
      // строку, и новая строка обязана остаться открытой (у правила обновления
      // нет отдельной проверки — условие USING проверяет и новую строку).
      const было = строка(зн.short_code);
      if (было && (было.locked === true || зн.locked === true))
        return Promise.resolve({ data: null, error: { code: '42501', message: 'new row violates row-level security policy for table "preset_links"' } });
      const копия = было ? { ...было } : null;
      return u.call(з, зн, н).then(р => { const с = строка(зн.short_code);
        if (с && с.locked === undefined) с.locked = false;
        if (с) эхо(копия ? 'UPDATE' : 'INSERT', копия, с, 160); return р; }); }; return з; };
  window.__ТАБЛИЦЫ.preset_links = [];
  const т0 = new Date().toISOString();
  saveAllPresets({ p1: { id: 'p1', name: 'Новый пресет', state: снимок, savedAt: т0 },
                   p2: { id: 'p2', name: 'Отозванный', state: снимок, savedAt: т0, shortCode: '222222', sharedId: '222222' },
                   p3: { id: 'p3', name: 'С кодом', state: снимок, savedAt: т0, shortCode: '333333', sharedId: '333333' } });
  _sharedPresets.length = 0;
  const свой = (к, ид, имя, зап) => ({ short_code: к, id: к, preset_id: ид, author_id: _sbUser.id, author_name: 'Проба', name: имя,
    state: снимок, is_public: false, visibility: 'public', locked: зап, created_at: '2026-09-20T10:00:00Z' });
  // p2 — отозванный под замком; p3 — пресет с кодом, строка которого есть, но не
  // опубликована (как «Виго» на снимке Константина).
  [свой('222222', 'p2', 'Отозванный', true), свой('333333', 'p3', 'С кодом', false)].forEach(р => {
    _sharedPresets.push(Object.assign({}, р)); window.__ТАБЛИЦЫ.preset_links.push(Object.assign({}, р)); });
  try { _общиеЗагружены = true; } catch (e) {}
  openPresetPanel(); await ждать(300); switchPresetTab('my');
  const итог = {};
  for (const [ид, к] of [['p1', null], ['p2', '222222'], ['p3', '333333']]) {
    window.__виды = []; window.__тосты.length = 0; window.__записи.length = 0; window.__замок.length = 0;
    const набл = new MutationObserver(() => { const з = document.querySelector('#presetList .pcard[data-pid="' + ид + '"] .btn-shared-lock');
      if (з) window.__виды.push(з.classList.contains('on') ? 'закрыт' : 'открыт'); });
    набл.observe(document.getElementById('presetList'), { childList: true, subtree: true, attributes: true });
    // Между эхом записи (160 мс) и эхом замка (260 мс) список перерисовывается —
    // как от любой другой строки подписки или переключения вкладки.
    const перерисовка = setTimeout(() => renderPresetList(), 210);
    await publishPreset(ид, 'public'); await ждать(700); clearTimeout(перерисовка);
    набл.disconnect();
    const код = к || loadAllPresets()[ид].shortCode;
    итог[ид] = { код, виды: [...new Set(window.__виды)], вызовы: window.__замок.slice(),
      вБазе: (строка(код) || {}).locked, опубл: (строка(код) || {}).is_public,
      вПамяти: (_sharedPresets.find(r => r.short_code === код) || {}).locked, тосты: window.__тосты.slice() };
  }
  _sb.from = былFrom;
  return итог;
}"""

def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for режим in ("обычно", "замок", "отказ"):
                н = {"обычно": "[обычно]", "замок": "[замок не встал]", "отказ": "[запись отказала]"}[режим]
                стр = бр.new_page(viewport={"width": 1440, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                р = стр.evaluate(ПОДГОТОВКА, режим)
                for ид, р1 in р.items():
                    print("  " + н, ид, json.dumps(р1, ensure_ascii=False)[:400])
                    тосты = " | ".join(р1["тосты"])
                    if режим == "обычно":
                        if "Ошибка" in тосты:
                            плохо(f"{н} {ид}: публикация не прошла: {тосты}")
                        if "открыт" in р1["виды"]:
                            плохо(f"{ид}: во время публикации на карточке мелькнул открытый замок: {р1['виды']}")
                        if not (р1["опубл"] and р1["вБазе"] and р1["вПамяти"]):
                            плохо(f"{ид}: публикация не заперла пресет: {р1}")
                        if "под замком" not in тосты:
                            плохо(f"{ид}: сообщение о публикации не говорит про замок: {тосты}")
                    elif режим == "замок":
                        if "под замком" in тосты or "замок закрыть не удалось" not in тосты:
                            плохо(f"{н} {ид}: база замок не закрыла, а сообщение другое: {тосты}")
                        if р1["вПамяти"] is not False:
                            плохо(f"{н} {ид}: база замок не закрыла, а страница считает пресет запертым: {р1}")
                    else:
                        if "под замком" in тосты:
                            плохо(f"{н} {ид}: при отказе записи сказано «под замком»: {тосты}")
                        if ид == "p2" and (not р1["вызовы"] or р1["вызовы"][-1] is not True):
                            плохо(f"{н} p2: запись отказала, а снятый перед ней замок не вернулся: {р1}")
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
    print("Чисто: публикация проходит правило доступа и для новой строки, и для пресета с кодом, и для отозванного под "
          "замком; все три встают под замок, и открытый замок не мелькает даже от запоздалого эха подписки; не встал "
          "замок — так и сказано; отказала запись — снятый замок возвращается.")


if __name__ == "__main__":
    главная()
