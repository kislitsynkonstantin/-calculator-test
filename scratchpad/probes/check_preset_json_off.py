#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Опубликованный пресет не скачивается.

Константин 18.10.2026: «после того, как пресет опубликован, сделай неактивной
кнопку для его скачивания (json), чтобы не плодить дубли».

Проба на 390 и 1440 держит:
  • в «Моих» у опубликованного кнопка скачивания неактивна (aria-disabled,
    подсказка говорит почему), нажатие файла не даёт и говорит словами; у
    неопубликованного — скачивает;
  • в «Общих» у опубликованного — так же неактивна;
  • неактивная кнопка — того же размера, что соседние, и бледнее их.

    python3 check_preset_json_off.py
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
  window.__скачано = []; window.triggerDownload = (т, имя) => window.__скачано.push(имя);
  const былоСоздать = URL.createObjectURL; URL.createObjectURL = б_ => { window.__скачано.push('blob'); return былоСоздать.call(URL, б_); };
  const сейчас = new Date().toISOString();
  saveAllPresets({ p1: { id: 'p1', name: 'Опубликованный', state: снимок, savedAt: сейчас, shortCode: '235788', sharedId: '235788', publishedAs: 'public' },
                   p2: { id: 'p2', name: 'Свой черновик', state: снимок, savedAt: сейчас } });
  _sharedPresets.length = 0;
  _sharedPresets.push({ short_code: '235788', id: '235788', preset_id: 'p1', author_id: _sbUser.id, author_name: 'Проба', name: 'Опубликованный',
                        state: снимок, is_public: true, visibility: 'public', locked: false, created_at: сейчас, updated_at: сейчас });
  window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(х => Object.assign({}, х));
  openPresetPanel(); await ждать(300);
  return true;
}"""

КНОПКА = """(сел) => { const к = [...document.querySelectorAll(сел)].find(х => /Скачать/.test(х.getAttribute('aria-label') || х.getAttribute('title') || ''));
  if (!к) return null;
  const р = к.getBoundingClientRect(), сосед = [...к.parentElement.children].find(х => х !== к && х.tagName === 'BUTTON');
  const рс = сосед ? сосед.getBoundingClientRect() : null;
  return { выкл: к.getAttribute('aria-disabled') === 'true', подсказка: к.getAttribute('title'), бледность: +getComputedStyle(к).opacity,
    размер: рс ? [Math.round(р.height - рс.height)] : null }; }"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ошибки = []
                стр.on("pageerror", lambda e: ошибки.append(str(e)))
                стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
                стр.evaluate(ПОДГОТОВКА, "blank")
                стр.evaluate("async () => { switchPresetTab('my'); await new Promise(r => setTimeout(r, 500)); }")
                for пид, надо_выкл in (("p1", True), ("p2", False)):
                    н = f"[{ш} Мои {пид}]"
                    сел = f'#presetList .pcard[data-pid="{пид}"] button'
                    к = стр.evaluate(КНОПКА, сел)
                    if not к:
                        плохо(f"{н} кнопки скачивания нет"); continue
                    стр.evaluate("() => { window.__скачано.length = 0; window.__тосты.length = 0; }")
                    стр.locator(f'#presetList .pcard[data-pid="{пид}"] button[aria-label^="Скачать"], #presetList .pcard[data-pid="{пид}"] button[title^="Скачать"]').first.click(force=True)
                    стр.wait_for_timeout(300)
                    итог = стр.evaluate("() => ({ скачано: window.__скачано.slice(), тосты: window.__тосты.slice() })")
                    if надо_выкл:
                        if not к["выкл"] or "дубли" not in (к["подсказка"] or "") or к["бледность"] > .6 or итог["скачано"] or not any("не скачивается" in т for т in итог["тосты"]):
                            плохо(f"{н} опубликованный: {к}, {итог}")
                    elif к["выкл"] or not итог["скачано"]:
                        плохо(f"{н} неопубликованный не скачивается: {к}, {итог}")
                    if к["размер"] and abs(к["размер"][0]) > 1:
                        плохо(f"{н} кнопка не одной высоты с соседней: {к['размер']}")
                стр.evaluate("async () => { switchPresetTab('shared'); await new Promise(r => setTimeout(r, 500)); }")
                н = f"[{ш} Общие]"
                к = стр.evaluate(КНОПКА, '#sharedPresetList .shared-pcard[data-scode="235788"] button')
                стр.evaluate("() => { window.__скачано.length = 0; }")
                if not к or not к["выкл"]:
                    плохо(f"{н} опубликованный в «Общих»: {к}")
                else:
                    стр.locator('#sharedPresetList .shared-pcard[data-scode="235788"] button[aria-disabled="true"]').first.click(force=True); стр.wait_for_timeout(300)
                    if стр.evaluate("() => window.__скачано.length"):
                        плохо(f"{н} неактивная кнопка всё же скачала")
                стр.screenshot(path=str(СНИМКИ / f"json-off-{ш}.png"))
                if ошибки:
                    плохо(f"[{ш}] ошибки страницы: {ошибки[:3]}")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        raise SystemExit(1)
    print("Чисто: опубликованный пресет не скачивается ни в «Моих», ни в «Общих» — кнопка бледная, с подсказкой, нажатие говорит словами; неопубликованный скачивается; 390 и 1440.")


if __name__ == "__main__":
    главная()
