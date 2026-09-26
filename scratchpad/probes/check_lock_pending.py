#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замок на карточке общего пресета, пока база молчит.

26.09.2026 Константин: «вот отсюда не могу открыть/закрыть замок на своих
пресетах». Журнал базы показал: связь с телефона молчала полторы минуты,
нажатия копились без всякого отклика и ушли разом — четыре запроса за одну
сотую секунды. Замок при этом работал, но выглядел сломанным.

Проба держит на 390 и 1440, в «Бланке» и «Модерне»:
  • пока ответа нет, кнопка стоит «в пути» (класс wait, aria-busy) и значок
    приглушён или дышит — отклик на нажатие виден сразу;
  • четыре нажатия подряд дают один запрос, а не четыре;
  • через шесть секунд молчания об этом сказано словами;
  • поздний ответ применяется: замок закрылся, «в пути» снято;
  • отказ сети тоже снимает «в пути» и говорит об ошибке;
  • то же для кнопки замка в полоске открытого пресета.

    python3 check_lock_pending.py
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
  const вызовы = []; let отпустить = null, уронить = null;
  const былRpc = _sb.rpc.bind(_sb);
  _sb.rpc = (имя, а) => {
    if (имя !== 'set_preset_lock') return былRpc(имя, а);
    вызовы.push([а.p_code, а.p_locked]);
    return new Promise((ok, нет) => { отпустить = () => ok({ data: true, error: null }); уронить = () => нет(new Error('сеть')); });
  };
  const тосты = []; const былТост = window.showToast; window.showToast = т => { тосты.push(String(т)); };
  const я = _sbUser && _sbUser.id;
  const с = (код, имя, замок) => ({ short_code: код, id: код, name: имя, author_name: 'Проба', author_id: я, is_public: true,
    visibility: 'public', locked: замок, preset_id: 'P' + код, created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Проба дом 8×8' }, thickness: 1, totalNum: 7044020, tech: 'frame' } });
  openPresetPanel();
  _sharedPresets.length = 0;
  _sharedPresets.push(с('321910', 'Свой открытый', false), с('235788', 'Свой под замком', true));
  try { _общиеЗагружены = true; } catch (e) {}
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  setSharedFilter('mine'); await ждать(200);
  const кнопка = () => document.querySelector('.shared-pcard[data-scode="321910"] .btn-shared-lock');
  const вид = к => { if (!к) return null; const св = к.querySelector('svg'); const cs = св ? getComputedStyle(св) : null;
    return { ждёт: к.classList.contains('wait'), занят: к.getAttribute('aria-busy'), закрыт: к.classList.contains('on'),
      анимация: cs ? cs.animationName : '', прозрачность: cs ? cs.opacity : '' }; };
  const покой = вид(кнопка());
  for (let i = 0; i < 4; i++) { кнопка()?.click(); await ждать(30); }
  await ждать(100);
  const впути = вид(кнопка());
  const запросов = вызовы.length;
  await ждать(6200);
  const тостМолчания = тосты.some(т => /не отвечает/.test(т));
  отпустить && отпустить(); await ждать(200);
  const после = вид(кнопка());
  // Отказ сети.
  вызовы.length = 0; тосты.length = 0;
  кнопка()?.click(); await ждать(100);
  const впути2 = вид(кнопка());
  уронить && уронить(); await ждать(200);
  const послеОтказа = вид(кнопка());
  const тостОтказа = тосты[тосты.length - 1] || '';
  // Полоска открытого пресета.
  вызовы.length = 0;
  _activeSharedCode = '235788'; updateSharedModeIndicator(); await ждать(100);
  const lb = () => document.getElementById('presetLockBtn');
  const есть = !!lb();
  for (let i = 0; i < 3; i++) { lb()?.click(); await ждать(30); }
  const полоска = { есть, запросов: вызовы.length, ждёт: !!lb()?.classList.contains('wait') };
  отпустить && отпустить(); await ждать(200);
  полоска.послеЖдёт = !!lb()?.classList.contains('wait');
  _activeSharedCode = null; updateSharedModeIndicator();
  window.showToast = былТост; _sb.rpc = былRpc;
  closePresetPanel();
  return { покой, впути, запросов, тостМолчания, после, впути2, послеОтказа, тостОтказа, полоска };
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
                    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
                    стр.evaluate(f"() => applyUiStyle('{тема}', false)")
                    р = стр.evaluate(СЦЕНАРИЙ)
                    н = f"{ш} {тема}"
                    if ш == 390 and тема == "blank":
                        print("  " + json.dumps(р, ensure_ascii=False)[:1500])
                    п, в = р["покой"] or {}, р["впути"] or {}
                    if not в.get("ждёт") or в.get("занят") != "true":
                        плохо(н + ": после нажатия кнопка не показывает, что запрос в пути")
                    if в.get("анимация") in ("", "none") and в.get("прозрачность") == п.get("прозрачность"):
                        плохо(н + ": значок «в пути» выглядит так же, как в покое")
                    if р["запросов"] != 1:
                        плохо(н + f": четыре нажатия подряд дали {р['запросов']} запрос(а) вместо одного")
                    if not р["тостМолчания"]:
                        плохо(н + ": шесть секунд молчания базы прошли без слова")
                    а = р["после"] or {}
                    if а.get("ждёт") or not а.get("закрыт"):
                        плохо(н + f": поздний ответ не применён ({а})")
                    if not (р["впути2"] or {}).get("ждёт"):
                        плохо(н + ": второе нажатие не встало «в пути»")
                    if (р["послеОтказа"] or {}).get("ждёт"):
                        плохо(н + ": после отказа сети кнопка осталась «в пути»")
                    if "Ошибка" not in р["тостОтказа"]:
                        плохо(н + f": отказ сети без сообщения ({р['тостОтказа']!r})")
                    пл = р["полоска"]
                    if not пл["есть"]:
                        плохо(н + ": в полоске открытого пресета нет кнопки замка")
                    elif пл["запросов"] != 1 or not пл["ждёт"] or пл["послеЖдёт"]:
                        плохо(н + f": кнопка замка в полоске без защиты от повторов ({пл})")
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
    print("Чисто: пока база молчит, замок стоит «в пути» и повторов не принимает — одно нажатие, один запрос; "
          "через шесть секунд молчания об этом сказано; поздний ответ применяется, отказ снимает «в пути» — "
          "на карточке и в полоске, на 390 и 1440, в обеих темах.")


if __name__ == "__main__":
    главная()
