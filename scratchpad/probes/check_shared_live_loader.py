#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно «Пресеты», «Общие»: цена не пропадает, загрузка — полоской.

Константин 26.09.2026: «пропадает цена у моих общих пресетов» и «сделай экран
загрузки как в Справке в пресетах, они часто грузятся».

Проба держит на 390 и 1440, в «Бланке» и «Модерне», днём и ночью:
  • строка из живой подписки без снимка расчёта (так приходит правка, которая
    его не тронула, — например, замок) не стирает у карточки проект и цену;
  • правка, которая снимок принесла, его обновляет;
  • пока список ни разу не загружен, в нём полоска загрузки справки: 180×3,
    по центру списка, с подписью, и в поле зрения окна;
  • уже загруженный список при повторном заходе на вкладку показывается сразу,
    без полоски, пока обновление идёт в фоне.

    python3 check_shared_live_loader.py
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
  const я = _sbUser && _sbUser.id;
  const с = (код, имя, сумма) => ({ short_code: код, id: код, name: имя, author_name: 'Проба', author_id: я, is_public: true,
    visibility: 'public', locked: false, created_at: '2026-09-02T10:05:00Z', updated_at: '2026-09-02T10:05:00Z',
    state: { project: { name: 'Хай-тек баня «Виго»' }, thickness: 1, totalNum: сумма, tech: 'frame' },
    spec_state: { totalNum: сумма } });
  openPresetPanel();
  _presetTab = 'shared';
  ['my','shared','search'].forEach(t => { document.getElementById('ptab-' + t)?.classList.toggle('ptab-active', t === 'shared');
    const c = document.getElementById('ptab-content-' + t); if (c) c.style.display = t === 'shared' ? 'flex' : 'none'; });
  // 1. Загрузка с пустого: запрос к базе не отвечает.
  const былоFrom = _sb.from;
  const висит = () => ({ select: () => ({ order: () => new Promise(() => {}) }) });
  _sb.from = t => t === 'preset_links' ? висит() : былоFrom.call(_sb, t);
  _кодыПресетовИзБазы = false; _sharedPresets = [];
  loadSharedPresets(); await ждать(150);
  const спис = document.getElementById('sharedPresetList');
  const пол = спис.querySelector('.bm-load');
  const окно = document.getElementById('presetScroll') || спис;
  const загрузка = пол ? (() => { const r = пол.getBoundingClientRect(), L = спис.getBoundingClientRect(), W = окно.getBoundingClientRect();
    const полоса = пол.querySelector('i'); const анимация = полоса ? getComputedStyle(полоса).animationName : '';
    return { ш: Math.round(r.width), в: Math.round(r.height), центрX: Math.round((r.left + r.right) / 2 - (L.left + L.right) / 2),
      видна: r.top >= W.top && r.bottom <= Math.min(W.bottom, innerHeight), подпись: (спис.textContent || '').trim(),
      цвет: getComputedStyle(полоса).backgroundColor, анимация }; })() : null;
  // 2. Список загружен: повторный заход не показывает полоску.
  _sharedPresets = [с('235788', 'D1_Хай-тек баня «Виго»', 5761901), с('321910', 'Хай-тек баня «Виго» 25.09', 7044020)];
  _кодыПресетовИзБазы = true;
  renderSharedList(); await ждать(100);
  loadSharedPresets(); await ждать(150);
  const повторно = { полоска: !!спис.querySelector('.bm-load'), карточек: спис.querySelectorAll('.shared-pcard').length };
  _sb.from = былоFrom;
  // 3. Живая подписка: замок без снимка расчёта. Обработчик берётся тем же
  // путём, каким его получает сама подписка, — через канал.
  let обработчик = null;
  const былКанал = _sb.channel, былоУдалить = _sb.removeChannel;
  const канал = { on: (e, ф, fn) => { обработчик = fn; return канал; }, subscribe: () => канал, unsubscribe: () => Promise.resolve('ok') };
  _sb.channel = () => канал; _sb.removeChannel = () => Promise.resolve('ok');
  subscribeSharedRealtime();
  _sb.channel = былКанал; _sb.removeChannel = былоУдалить;
  const приходОбщего = обработчик;
  const карточка = код => { const к = спис.querySelector('.shared-pcard[data-scode="' + код + '"]');
    return к ? { цена: ((к.querySelector('.shared-pcard-price') || {}).textContent || '').trim(),
                 проект: ((к.querySelector('.shared-pcard-project') || {}).textContent || '').trim() } : null; };
  renderSharedList(); await ждать(100);
  const до = карточка('321910');
  const строка = Object.assign({}, _sharedPresets[1]); delete строка.state; delete строка.spec_state; строка.locked = true;
  приходОбщего({ eventType: 'UPDATE', new: строка, old: { short_code: '321910' } }); await ждать(100);
  const послеЗамка = карточка('321910');
  const строка2 = Object.assign({}, _sharedPresets[1], { spec_state: { totalNum: 7100000 }, state: Object.assign({}, _sharedPresets[1].state, { totalNum: 7100000 }), locked: true });
  приходОбщего({ eventType: 'UPDATE', new: строка2, old: { short_code: '321910' } }); await ждать(100);
  const послеПравки = карточка('321910');
  const строка3 = Object.assign({}, _sharedPresets[0], { state: null, spec_state: null });
  приходОбщего({ eventType: 'UPDATE', new: строка3, old: { short_code: '235788' } }); await ждать(100);
  const послеNull = карточка('235788');
  closePresetPanel();
  return { загрузка, повторно, до, послеЗамка, послеПравки, послеNull };
}"""


def главная():
    с, порт = сервер()
    снимки = pathlib.Path(os.environ["BM_SHOTS"]) if os.environ.get("BM_SHOTS") else None
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
                        try:
                            р = стр.evaluate(СЦЕНАРИЙ)
                        except Exception as e:
                            плохо(f"{ш} {тема}: сценарий упал: {str(e)[:160]}"); стр.close(); continue
                        н = f"{ш} {тема} {'ночь' if ночь else 'день'}"
                        if ш == 390 and тема == "blank" and not ночь:
                            print("  " + json.dumps(р, ensure_ascii=False))
                        з = р["загрузка"]
                        if not з: плохо(н + ": пока список грузится, полоски загрузки нет")
                        else:
                            if (з["ш"], з["в"]) != (180, 3): плохо(н + f": полоска {з['ш']}×{з['в']}, у справки 180×3")
                            if abs(з["центрX"]) > 2: плохо(н + f": полоска не по центру списка ({з['центрX']})")
                            if not з["видна"]: плохо(н + ": полоска вне поля зрения окна")
                            if "загружаются" not in з["подпись"]: плохо(н + ": у полоски нет подписи")
                            if з["анимация"] != "bmLoad": плохо(н + ": полоска не движется")
                        if р["повторно"]["полоска"] or р["повторно"]["карточек"] != 2:
                            плохо(н + f": загруженный список при повторном заходе спрятан за полоской ({р['повторно']})")
                        if not р["до"] or not р["до"]["цена"]: плохо(н + ": у карточки нет цены ещё до правки — проба не мерит")
                        elif р["послеЗамка"] != р["до"]: плохо(н + f": после замка из подписки карточка изменилась: {р['до']} → {р['послеЗамка']}")
                        if not р["послеПравки"] or "7 100 000" not in р["послеПравки"]["цена"].replace("\u00a0", " ").replace("\u202f", " "):
                            плохо(н + f": правка с новым снимком не обновила цену ({р['послеПравки']})")
                        if not р["послеNull"] or not р["послеNull"]["цена"]: плохо(н + ": пустые поля снимка из подписки стёрли цену")
                        if снимки and not ночь:
                            pass
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
    print("Чисто: строка подписки без снимка расчёта не стирает проект и цену, новый снимок их обновляет; "
          "пока список не загружен — полоска справки по центру с подписью, загруженный показывается сразу — "
          "на 390 и 1440, в обеих темах, днём и ночью.")


if __name__ == "__main__":
    главная()
