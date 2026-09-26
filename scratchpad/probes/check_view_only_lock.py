#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет «только просмотр»: ничего не меняется — ни скидка, ни план, ни сброс.

Константин 26.09.2026, снимком итога чужого пресета, открытого по коду: «могу
менять галочку „за наличные“, тип скидки (% или сумма). Проверь: не должно
быть возможности менять ничего в таком пресете, чтобы случайно что-то не
изменить». Замок держал проект, спецификацию и полотно, а скидка в итоге,
платёжный план, данные для договора, пункты «Сбросить» и строки поиска опций
стояли вне его.

Проба на 390 и 1440 открывает чужой неопубликованный пресет по коду и
настоящими нажатиями и набором держит:
  • «за наличные» не переключается, подписи «Спец. цена» / «Скидка» не
    меняют главное поле, процент не меняется ни набором, ни стрелкой мышью,
    ни клавишами ↑↓, сумма скидки не набирается, срок не получает фокус;
  • в платёжном плане доля этапа не набирается, «Добавить этап» не
    добавляет;
  • в «Данных для договора» поле не набирается, крестик окно закрывает;
  • «Сбросить → Отметки опций» не снимает отметки;
  • в поиске опций ни нажатие по строке, ни Enter опцию не включают;
  • и обратная сторона: в своём открытом общем пресете и в расчёте без
    пресета «за наличные» переключается, процент набирается.

    python3 check_view_only_lock.py
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


# вид: 'чужой' — чужой неопубликованный по коду; 'свой' — свой открытый общий;
# 'без' — расчёт без пресета.
ОТКРЫТЬ = """async (вид) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  selectProjectOption(0); await ждать(700);
  // Отмечаем пару опций, чтобы было что сбрасывать.
  const оп = OPTIONS.filter(о => !checkedOptions[о.id]).slice(0, 40);
  for (const о of оп) { try { toggleOpt(о.id); } catch (e) {} if (Object.values(checkedOptions).filter(Boolean).length >= 3) break; }
  const снимок = collectState(); снимок.tech = 'frame';
  document.getElementById('discountPctInput').value = '3';
  if (снимок.discount != null) снимок.discount = 3;
  window.showToast = () => {};
  if (вид === 'без') return true;
  const строка = { short_code: '365484', id: '365484', preset_id: 'preset_x',
    author_id: вид === 'свой' ? _sbUser.id : 'u-другой', author_name: вид === 'свой' ? 'Проба' : 'Максим Григорьев',
    name: 'Пресет пробы', state: снимок, is_public: вид === 'свой', visibility: 'public',
    created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false };
  _sharedPresets.push(строка);
  openSharedPreset('365484'); await ждать(900);
  return { правка: canEditPublic(), активный: _activeSharedCode };
}"""

СНИМОК = """() => ({
  нал: document.getElementById('cashDiscountCheck').checked,
  режим: typeof _режимСкидки !== 'undefined' ? _режимСкидки : null,
  проц: document.getElementById('discountPctInput').value,
  сумма: document.getElementById('discountSavedInput').value,
  отмечено: Object.values(checkedOptions).filter(Boolean).length,
})"""


def прогон(стр, ш, вид):
    н = f"[{ш} {вид}]"
    р = стр.evaluate(ОТКРЫТЬ, вид)
    if вид == "чужой" and (not isinstance(р, dict) or р.get("правка") or р.get("активный") != "365484"):
        плохо(f"{н} пресет не открылся на просмотр: {р}")
        return
    до = стр.evaluate(СНИМОК)

    # за наличные
    стр.locator("#cashDiscountLabel").scroll_into_view_if_needed()
    стр.locator("#cashDiscountLabel").click()
    стр.wait_for_timeout(150)
    нал = стр.evaluate("() => document.getElementById('cashDiscountCheck').checked")
    # процент набором
    п = стр.locator("#discountPctInput")
    п.click(); стр.keyboard.press("End"); стр.keyboard.type("5", delay=5); стр.wait_for_timeout(100)
    проц_набор = п.input_value()
    стр.evaluate("() => document.activeElement && document.activeElement.blur()")
    if вид != "без" and вид != "свой":
        # стрелка мышью у правого края и клавиши
        бк = п.bounding_box()
        стр.mouse.click(бк["x"] + бк["width"] - 6, бк["y"] + бк["height"] * 0.3)
        стр.wait_for_timeout(100)
        стр.evaluate("() => document.getElementById('discountPctInput').focus()")
        стр.keyboard.press("ArrowUp"); стр.wait_for_timeout(100)
        проц_стрелки = п.input_value()
        # подпись главного поля
        стр.locator("#discSumLab").click(); стр.wait_for_timeout(100)
        режим = стр.evaluate("() => _режимСкидки")
        # сумма
        с = стр.locator("#discountSavedInput")
        было_с = с.input_value()
        с.click(); стр.keyboard.type("99", delay=5); стр.wait_for_timeout(100)
        сумма = с.input_value()
        # срок
        стр.locator("#discountUntilDate").click(); стр.wait_for_timeout(100)
        фокус_срок = стр.evaluate("() => document.activeElement && document.activeElement.id")
        if нал != до["нал"]:
            плохо(f"{н} «за наличные» переключилась")
        if проц_набор != до["проц"] or проц_стрелки != до["проц"]:
            плохо(f"{н} процент изменился: набором «{проц_набор}», стрелками «{проц_стрелки}», был «{до['проц']}»")
        if режим != до["режим"]:
            плохо(f"{н} подпись «Скидка» сменила главное поле: {до['режим']} → {режим}")
        if сумма != было_с:
            плохо(f"{н} сумма скидки набралась: «{было_с}» → «{сумма}»")
        if фокус_срок == "discountUntilDate":
            плохо(f"{н} срок спец. цены получил фокус")

        # платёжный план
        стр.evaluate("() => openPaymentPlan()"); стр.wait_for_timeout(500)
        пп = стр.evaluate("""() => { const в = document.querySelector('#paymentPlanBody input[type="text"], #paymentPlanBody input:not([type])');
          return { поле: !!в, этапов: document.querySelectorAll('#paymentPlanBody .pp-trash, #paymentPlanBody [class*="stage"]').length }; }""")
        if пп["поле"]:
            в = стр.locator('#paymentPlanBody input[type="text"], #paymentPlanBody input:not([type])').first
            было = в.input_value()
            в.click(); стр.keyboard.type("7", delay=5); стр.wait_for_timeout(100)
            if в.input_value() != было:
                плохо(f"{н} в платёжном плане доля набралась: «{было}» → «{в.input_value()}»")
        доб = стр.locator('#paymentPlanBody [onclick^="ppAddStage"]')
        if доб.count():
            этапов_до = стр.evaluate("() => JSON.stringify(ppState)")
            доб.first.click(); стр.wait_for_timeout(200)
            if стр.evaluate("() => JSON.stringify(ppState)") != этапов_до:
                плохо(f"{н} «Добавить этап» добавил этап")
        else:
            плохо(f"{н} в платёжном плане нет «Добавить этап» — проверить нечем")
        стр.evaluate("() => closePaymentPlan()"); стр.wait_for_timeout(200)

        # данные для договора
        стр.evaluate("() => openContractDataModal()"); стр.wait_for_timeout(300)
        т = стр.locator("#cdPhone")
        было = т.input_value()
        т.click(); стр.keyboard.type("123", delay=5); стр.wait_for_timeout(100)
        if т.input_value() != было:
            плохо(f"{н} «Данные для договора» набираются: «{было}» → «{т.input_value()}»")
        стр.locator("#contractDataOverlay .ovl-x").click(); стр.wait_for_timeout(200)
        if стр.evaluate("() => document.getElementById('contractDataOverlay').style.display") != "none":
            плохо(f"{н} крестик «Данных для договора» окно не закрыл")

        # «Сбросить»: первый живой пункт, кроме звёзд опций
        сброс = стр.evaluate("""async () => { const слепок = () => { const с = collectState(); delete с.savedAt; return JSON.stringify(с); };
          toggleResetDropdown(); await new Promise(r => setTimeout(r, 200));
          const к = [...document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')]
            .find(х => !х.disabled && х.id !== 'rdStars' && !х.classList.contains('reset-all-item'));
          // С (50) пункты под замком серые — замок держит их и без нажатия.
          const выкл = [...document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')]
            .filter(х => х.id !== 'rdStars' && !х.classList.contains('reset-all-item')).every(х => х.disabled);
          if (!к) { try { closeResetDropdown(); } catch (e) {} return { пункт: null, выкл }; }
          const до = слепок(); к.click(); await new Promise(r => setTimeout(r, 400));
          try { closeResetDropdown(); } catch (e) {}
          return { пункт: к.id, изменилось: слепок() !== до }; }""")
        if not сброс["пункт"]:
            if not сброс.get("выкл"):
                плохо(f"{н} в «Сбросить» нет живых пунктов, но и выключены не все")
        elif сброс["изменилось"]:
            плохо(f"{н} «Сбросить → {сброс['пункт']}» изменила расчёт")

        # поиск опций: нажатие по строке и Enter
        стр.evaluate("() => openOptSearch()"); стр.wait_for_timeout(300)
        пс = стр.evaluate("""async () => { const слепок = () => { const с = collectState(); delete с.savedAt; return JSON.stringify(с); };
          const п = document.getElementById('optSearchInput') || document.querySelector('#optSearchOverlay input');
          if (!п) return { поле: false };
          for (const о of OPTIONS) {
            const слово = String(о.name || '').split(/\s+/).find(с => с.length > 4);
            if (!слово) continue;
            п.value = слово; п.dispatchEvent(new Event('input', { bubbles: true }));
            await new Promise(r => setTimeout(r, 120));
            if (document.querySelector('#optSearchResults .ops-row:not(.blocked)')) break;
          }
          const строка = document.querySelector('#optSearchResults .ops-row:not(.blocked) .ops-name');
          if (!строка) return { поле: true, строка: false };
          const до = слепок();
          строка.click(); await new Promise(r => setTimeout(r, 200));
          const послеНажатия = слепок() !== до;
          п.focus(); п.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
          await new Promise(r => setTimeout(r, 200));
          return { поле: true, строка: true, нажатие: послеНажатия, enter: слепок() !== до }; }""")
        if not пс.get("строка"):
            плохо(f"{н} поиск опций не дал строки — проверить нечем ({пс})")
        elif пс["нажатие"] or пс["enter"]:
            плохо(f"{н} поиск опций изменил расчёт: нажатием {пс['нажатие']}, Enter {пс['enter']}")
        стр.evaluate("() => { try { closeOptSearch(); } catch (e) {} }")
        print(f"  {н} чисто по своим пунктам" if not [х for х in НАХОДКИ if х.startswith(н)] else f"  {н} есть находки")
    else:
        # обратная сторона: правка идёт
        if нал == до["нал"]:
            плохо(f"{н} «за наличные» не переключилась — замок держит лишнее")
        if проц_набор == до["проц"]:
            плохо(f"{н} процент не набирается — замок держит лишнее")
        print(f"  {н} правка идёт: наличные {до['нал']} → {нал}, процент «{до['проц']}» → «{проц_набор}»")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for вид in ("чужой", "свой", "без"):
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    try:
                        прогон(стр, ш, вид)
                    except Exception as e:
                        плохо(f"[{ш} {вид}] проба оборвалась: {e!s:.300}")
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"[{ш} {вид}] ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в пресете «только просмотр» не меняются ни скидка, ни платёжный план, ни данные для договора, "
          "ни отметки через «Сбросить» и поиск опций; в своём открытом пресете и без пресета правка идёт.")


if __name__ == "__main__":
    главная()
