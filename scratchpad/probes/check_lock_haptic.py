#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замок общего пресета: лёгкий отклик под пальцем.

Константин 26.09.2026: «на открытие/закрытие замка пресета на телефоне добавь
вибрацию одинарную лёгкую».

Вибрацию проба почувствовать не может, поэтому меряет вызовы:
  • сенсорный экран с вибрацией (Android): одно нажатие замка — один вызов
    navigator.vibrate не длиннее 20 мс; четыре быстрых нажатия, пока база не
    ответила, — всё равно один вызов;
  • сенсорный экран без вибрации (iPhone): переключается спрятанный системный
    переключатель — ровно раз на нажатие, и он не виден и не ловит нажатий;
  • мышь (1440): ни вибрации, ни переключателя;
  • на карточке и в полоске открытого пресета одинаково.

    python3 check_lock_haptic.py
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




СЦЕНАРИЙ = """async (безВибрации) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const вибр = [];
  if (безВибрации) { try { Object.defineProperty(navigator, 'vibrate', { value: undefined, configurable: true }); } catch (e) {} }
  else { try { Object.defineProperty(navigator, 'vibrate', { value: (м) => { вибр.push(м); return true; }, configurable: true }); } catch (e) {} }
  let отпустить = null;
  const былRpc = _sb.rpc.bind(_sb);
  _sb.rpc = (имя, а) => имя !== 'set_preset_lock' ? былRpc(имя, а)
    : new Promise(ok => { отпустить = () => ok({ data: true, error: null }); });
  window.showToast = () => {};
  const я = _sbUser && _sbUser.id;
  const с = (код, замок) => ({ short_code: код, id: код, name: 'Пресет ' + код, author_name: 'Проба', author_id: я, is_public: true,
    visibility: 'public', locked: замок, created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 7044020, tech: 'frame' } });
  openPresetPanel();
  _sharedPresets.length = 0; _sharedPresets.push(с('321910', false), с('235788', true));
  try { _общиеЗагружены = true; } catch (e) {}
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  setSharedFilter('mine'); await ждать(200);
  const щелчки = [];
  document.addEventListener('change', e => { if (e.target && e.target.closest && e.target.closest('#bmHaptic')) щелчки.push(1); }, true);
  const кнопка = () => document.querySelector('.shared-pcard[data-scode="321910"] .btn-shared-lock');
  for (let i = 0; i < 4; i++) { кнопка()?.click(); await ждать(30); }
  const карточка = { вибр: вибр.slice(), щелчков: щелчки.length };
  отпустить && отпустить(); await ждать(200);
  вибр.length = 0; щелчки.length = 0;
  closePresetPanel();
  _activeSharedCode = '235788'; updateSharedModeIndicator(); await ждать(100);
  document.getElementById('presetLockBtn')?.click();
  const полоска = { вибр: вибр.slice(), щелчков: щелчки.length };
  отпустить && отпустить(); await ждать(200);
  const п = document.getElementById('bmHaptic');
  const скрыт = п ? (() => { const r = п.getBoundingClientRect(); return (r.right <= 0 || r.left >= innerWidth || getComputedStyle(п).opacity === '0') && getComputedStyle(п).pointerEvents === 'none'; })() : null;
  _activeSharedCode = null; updateSharedModeIndicator(); _sb.rpc = былRpc;
  return { карточка, полоска, переключатель: !!п, скрыт };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for имя, ш, касание, безВибрации in (("Android", 390, True, False), ("iPhone", 390, True, True), ("мышь", 1440, False, False)):
                кон = бр.new_context(viewport={"width": ш, "height": 900}, has_touch=касание, is_mobile=касание)
                стр = кон.new_page()
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА)
                стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; applyUiStyle('blank', false); }")
                р = стр.evaluate(СЦЕНАРИЙ, безВибрации)
                print(f"  [{имя}]", json.dumps(р, ensure_ascii=False))
                н = f"[{имя}]"
                for где in ("карточка", "полоска"):
                    x = р[где]
                    if имя == "Android":
                        if len(x["вибр"]) != 1 or not (0 < (x["вибр"][0] if isinstance(x["вибр"][0], (int, float)) else 999) <= 20):
                            плохо(н + f" {где}: вибрация {x['вибр']} — нужен один короткий вызов")
                        if x["щелчков"]:
                            плохо(н + f" {где}: при работающей вибрации щёлкнул ещё и переключатель")
                    elif имя == "iPhone":
                        if x["щелчков"] != 1:
                            плохо(н + f" {где}: переключатель щёлкнул {x['щелчков']} раз вместо одного")
                    else:
                        if x["вибр"] or x["щелчков"]:
                            плохо(н + f" {где}: мышью отклика быть не должно ({x})")
                if имя == "iPhone" and not р["скрыт"]:
                    плохо(н + " переключатель виден или ловит нажатия")
                if имя == "мышь" and р["переключатель"]:
                    плохо(н + " при мыши на странице появился переключатель")
                for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                    плохо(f"{н} ошибка страницы: {о[:160]}")
                кон.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: замок откликается одним лёгким щелчком на нажатие — вибрацией, где она есть, и системным "
          "переключателем на iPhone; быстрые повторы не множат отклик, мышью отклика нет — на карточке и в полоске.")


if __name__ == "__main__":
    главная()
