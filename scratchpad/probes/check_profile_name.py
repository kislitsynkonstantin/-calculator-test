#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фамилия менеджера из аккаунта и мини-окно «Профиль».

Константин 30.09.2026, по макету mockups/manager-name-v1.html: «Фамилию Имя
менеджера подставляй из аккаунта. Если фамилия не заполнена, отдельным
мини-окном предлагай заполнить…», затем: «так отлично. Чужой пресет коллеги
сохраняет фамилию того, кто автор. Берёт оттуда. Если менеджер не заполнил
Фамилия Имя, почта не подставляется в поле Менеджер».

Проба на 390 и 1440, днём и ночью, с настоящими шрифтами (база подменена):
  • фамилии в профиле нет, проект не выбран — в углу мини-окно «Профиль»
    открылось само: фамилия пустая, имя из аккаунта; поле «Менеджер» пустое,
    почты в нём нет; окно в пределах экрана, кнопки не меньше 36 px;
  • пустая фамилия и «Сохранить» — поле подсвечено, в базу ничего не ушло;
  • фамилия, Enter, Enter — в профиле аккаунта фамилия и имя, в поле
    «Менеджер» «Фамилия Имя», окно и значок ушли;
  • «Позже» сворачивает окно в значок «Профиль»; выбран проект — угол
    занимает «Не сохранён», значок профиля один не стоит рядом;
  • фамилия есть — после «Сбросить всё» поле заполняется само; вписанное
    руками не затирается;
  • свой пресет с пустым полем — при открытии своя фамилия, и она
    сохраняется в пресете; вписанная руками при открытии не меняется;
  • пресет коллеги с пустым полем — в поле фамилия автора, а не своя.

    python3 check_profile_name.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from check_pdf_pick import СоШрифтами
from playwright.sync_api import sync_playwright

НАХОДКИ = []
ПОЧТА = "proba@example.ru"


def начать(бр, порт, ш, в, ночь, фамилия):
    стр = СоШрифтами(бр).new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.add_init_script(f"""window.__ТАБЛИЦЫ.profiles = [
      {{ id: 'u-проба', role: 'manager', first_name: 'Сергей', last_name: '{фамилия}', email: '{ПОЧТА}', app_settings: {{}} }},
      {{ id: 'u-другой', role: 'manager', first_name: 'Павел', last_name: 'Волков', app_settings: {{}} }}];""")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""(ночь) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); document.body.classList.toggle('dark', ночь);
      window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); }; }""", ночь)
    стр.evaluate("async () => { await loadSbProfile(); }")
    # Профиль приносит свою тему — ночь ставится после него.
    стр.evaluate("(ночь) => { applyThemeMode(ночь ? 'dark' : 'light', false); document.body.classList.toggle('dark', ночь); }", ночь)
    стр.wait_for_timeout(900)
    return стр, ошибки


СОСТ = """() => { const з = document.getElementById('presetChip'), к = document.getElementById('presetChipCard');
  const р = к ? к.getBoundingClientRect() : null;
  const кн = к ? [...к.querySelectorAll('.pc-row button')].map(б => Math.round(б.getBoundingClientRect().height)) : [];
  return { режим: _значокРежим, значок: з ? з.className : '', надпись: з ? з.innerText.trim() : '', окно: !!к && к.classList.contains('show'),
    фам: (к && к.querySelector('#pcLast') || {}).value, имя: (к && к.querySelector('#pcFirst') || {}).value,
    плохо: !!(к && к.querySelector('#pcLast.bad')), поле: document.getElementById('managerName').value,
    коробка: р && { l: р.left, t: р.top, r: р.right, b: р.bottom }, кнопки: кн, ш: innerWidth, в: innerHeight,
    профиль: (window.__ТАБЛИЦЫ.profiles || [])[0], тосты: (window.__тосты || []).join(' | ') }; }"""


def прогон(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    # 1. Фамилии нет.
    стр, ошибки = начать(бр, порт, ш, в, ночь, "")
    с = стр.evaluate(СОСТ)
    if с["режим"] != "profile" or not с["окно"] or с["фам"] != "" or с["имя"] != "Сергей":
        НАХОДКИ.append(f"{н} фамилии нет — мини-окно «Профиль» не открылось само с пустой фамилией и именем из аккаунта: {с}")
    if с["поле"]:
        НАХОДКИ.append(f"{н} фамилии нет, а в поле «Менеджер» стоит «{с['поле']}» (почта не должна подставляться)")
    к_ = с["коробка"]
    if к_ and (к_["l"] < 0 or к_["t"] < 0 or к_["r"] > с["ш"] + .5 or к_["b"] > с["в"] + .5):
        НАХОДКИ.append(f"{н} мини-окно «Профиль» за краем экрана: {к_}")
    if any(h < 36 for h in с["кнопки"]):
        НАХОДКИ.append(f"{н} кнопки мини-окна ниже 36 px: {с['кнопки']}")
    стр.screenshot(path=str(м.СНИМКИ / f"profile-{ш}{'-ночь' if ночь else ''}.png"))
    if not с["окно"]:
        стр.close(); return
    # 2. Пустая фамилия — не сохраняется.
    стр.locator("#presetChipCard [data-act='prof-save']").click(); стр.wait_for_timeout(300)
    с = стр.evaluate(СОСТ)
    if not с["плохо"] or с["профиль"].get("last_name"):
        НАХОДКИ.append(f"{н} пустая фамилия: поле не подсвечено или в профиль что-то ушло: {с['профиль']}")
    # 3. Фамилия, Enter, Enter.
    стр.locator("#pcLast").fill("Иванов"); стр.locator("#pcLast").press("Enter")
    if стр.evaluate("() => document.activeElement && document.activeElement.id") != "pcFirst":
        НАХОДКИ.append(f"{н} Enter в фамилии не перевёл к имени")
    стр.locator("#pcFirst").press("Enter"); стр.wait_for_timeout(900)
    с = стр.evaluate(СОСТ)
    if с["профиль"].get("last_name") != "Иванов" or с["профиль"].get("first_name") != "Сергей":
        НАХОДКИ.append(f"{н} фамилия и имя не ушли в профиль аккаунта: {с['профиль']}")
    if с["поле"] != "Иванов Сергей":
        НАХОДКИ.append(f"{н} после сохранения в поле «Менеджер» «{с['поле']}», ждали «Иванов Сергей»")
    if с["окно"] or "pc-hide" not in с["значок"]:
        НАХОДКИ.append(f"{н} после сохранения мини-окно или значок профиля остались: {с['значок']}")
    # 4. Вписанное руками не затирается; «Сбросить всё» заполняет снова.
    стр.evaluate("() => { document.getElementById('managerName').value = 'Иванов Сергей Петрович'; подставитьМенеджера(); }"); стр.wait_for_timeout(200)
    if стр.evaluate("() => document.getElementById('managerName').value") != "Иванов Сергей Петрович":
        НАХОДКИ.append(f"{н} вписанное руками затёрто")
    стр.evaluate("() => { document.getElementById('managerName').value = ''; setTimeout(подставитьМенеджера, 0); }"); стр.wait_for_timeout(300)
    if стр.evaluate("() => document.getElementById('managerName').value") != "Иванов Сергей":
        НАХОДКИ.append(f"{н} пустое поле при заполненном профиле не заполнилось")
    # 4б. Свой пресет с пустым полем: при открытии — своя фамилия, и она
    # сохраняется в самом пресете; заполненное руками при открытии не меняется.
    стр.evaluate("""async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 700));
      const пр = loadAllPresets(); const ст = collectState();
      пр['проба-пустое'] = { id: 'проба-пустое', name: 'Проба пустое', state: Object.assign({}, ст, { manager: '' }), savedAt: new Date().toISOString() };
      пр['проба-руками'] = { id: 'проба-руками', name: 'Проба руками', state: Object.assign({}, ст, { manager: 'Петров Пётр' }), savedAt: new Date().toISOString() };
      saveAllPresets(пр); }""")
    стр.evaluate("() => loadPreset('проба-пустое')"); стр.wait_for_timeout(600)
    п = стр.evaluate("() => document.getElementById('managerName').value")
    if п != "Иванов Сергей":
        НАХОДКИ.append(f"{н} свой пресет с пустым полем: при открытии в поле «{п}», ждали «Иванов Сергей»")
    стр.wait_for_timeout(9000)
    сохр = стр.evaluate("() => (loadAllPresets()['проба-пустое'] || { state: {} }).state.manager")
    if сохр != "Иванов Сергей":
        НАХОДКИ.append(f"{н} подставленная фамилия не сохранилась в пресете: в нём «{сохр}»")
    стр.evaluate("() => loadPreset('проба-руками')"); стр.wait_for_timeout(600)
    п = стр.evaluate("() => document.getElementById('managerName').value")
    if п != "Петров Пётр":
        НАХОДКИ.append(f"{н} пресет с фамилией, вписанной руками: при открытии в поле «{п}», ждали «Петров Пётр»")
    # 5. Пресет коллеги с пустым полем — фамилия автора.
    стр.evaluate("""() => { _sharedPresets.push({ short_code: '111222', id: '111222', name: 'Баня «Лейпциг» 5×7', author_name: 'Павел Волков',
      author_id: 'u-другой', is_public: true, visibility: 'public', locked: true, created_at: '2026-09-22T13:05:00Z', updated_at: '2026-09-22T13:05:00Z',
      state: { version: 1, manager: '', client: '' } }); openSharedPreset('111222'); }""")
    стр.wait_for_timeout(1500)
    п = стр.evaluate("() => document.getElementById('managerName').value")
    if п != "Волков Павел":
        НАХОДКИ.append(f"{н} пресет коллеги с пустым полем: в поле «{п}», ждали фамилию автора «Волков Павел»")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()
    # 6. «Позже» и проект.
    стр, ошибки = начать(бр, порт, ш, в, ночь, "")
    стр.locator("#presetChipCard [data-act='prof-later']").first.click(); стр.wait_for_timeout(400)
    с = стр.evaluate(СОСТ)
    q = стр.evaluate("() => { const р = document.getElementById('presetChip').getBoundingClientRect(); return { x: р.x - 14, y: р.y - 14, w: р.width + 28, h: р.height + 28 }; }")
    if q["w"] > 30:
        стр.screenshot(path=str(м.СНИМКИ / f"profile-chip-{ш}{'-ночь' if ночь else ''}.png"), clip={"x": max(0, q["x"]), "y": max(0, q["y"]), "width": q["w"], "height": q["h"]})
    if с["окно"] or с["режим"] != "profile" or "Профиль" not in с["надпись"]:
        НАХОДКИ.append(f"{н} «Позже» не свернуло окно в значок «Профиль»: {с}")
    стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
    с = стр.evaluate(СОСТ)
    if с["режим"] == "profile" or "Профиль" in с["надпись"] or стр.evaluate("() => document.querySelectorAll('.pchip').length") != 1:
        НАХОДКИ.append(f"{н} выбран проект, а значок профиля остался или значков в углу несколько: {с['режим']} «{с['надпись']}»")
    if с["поле"]:
        НАХОДКИ.append(f"{н} фамилии нет, а после выбора проекта в поле «Менеджер» «{с['поле']}»")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            for ш, в in ((390, 844), (1440, 900)):
                for ночь in (False, True):
                    прогон(бр, порт, ш, в, ночь)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: без фамилии в профиле мини-окно «Профиль» открывается само, почта в поле не встаёт; пустая фамилия "
          "не сохраняется; сохранённые фамилия и имя уходят в аккаунт и в поле «Менеджер»; вписанное руками не затирается; "
          "«Позже» сворачивает в значок, проект забирает угол; в пресете коллеги — фамилия автора — на 390 и 1440, днём и ночью.")


if __name__ == "__main__":
    главная()
