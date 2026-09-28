#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба: «Отозвать» в окне «Пресеты» сначала спрашивает.

Константин 29.09.2026: снятие с публикации — как в карточке пресета, с
подтверждением. Снятый пресет пропадает из «Общих» и у коллег, у которых он
открыт, а ссылка клиента перестаёт открываться.

Держит:
  • обе кнопки «Отозвать» (карточки «Моих» и «Общих») ведут в retractPreset;
  • retractPreset открывает окно подтверждения поверх окна «Пресеты», с
    кнопкой «Отозвать», а базу не трогает;
  • «Отмена» закрывает окно, и функция базы retract_preset не вызывается;
  • «Отозвать» вызывает её ровно один раз;
  • над «Отозвать» не корзина (пресет не удаляется), а окно удаления после
    этого снова предлагает «Удалить» с корзиной.
На 390 и 1440 px, днём и ночью. Двусторонняя: на (5) падает.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

КОРЕНЬ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
НАХОДКИ = []


def main():
    исходник = open(os.path.join(КОРЕНЬ, 'index.html'), encoding='utf-8').read()
    кнопки = re.findall(r'<button class="(?:pcard-retract|btn-retract)"[^>]*onclick="([^"]*)"', исходник)
    if len(кнопки) < 3 or not all('retractPreset(' in к for к in кнопки):
        НАХОДКИ.append(f"кнопки «Отозвать» ведут не в retractPreset: {кнопки}")
    с, порт = м.сервер()
    with sync_playwright() as pw:
        бр = pw.chromium.launch(executable_path=м.хром(), args=['--no-sandbox'])
        for ш, в in ((390, 844), (1440, 900)):
            for ночь in (False, True):
                н = f"[{ш}{' ночь' if ночь else ''}]"
                стр = бр.new_page(viewport={'width': ш, 'height': в})
                ош = []
                стр.on('pageerror', lambda e: ош.append(str(e)))
                стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
                стр.add_init_script("window.__ОТОЗВАНО = 0; window.__RPC = window.__RPC || {};"
                                    "window.__RPC.retract_preset = function () { window.__ОТОЗВАНО++; return true; };")
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until='load'); стр.wait_for_timeout(2500)
                стр.evaluate("(н) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';"
                             " document.body.classList.toggle('dark', н); openPresetPanel(); }", ночь)
                стр.wait_for_timeout(300)
                стр.evaluate("() => retractPreset('123456')"); стр.wait_for_timeout(200)
                р = стр.evaluate("""() => { const д = document.getElementById('confirmDialog'), ок = document.getElementById('confirmDialogOk');
                  const r = ок.getBoundingClientRect(), наверху = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  return { видно: д.classList.contains('show') && getComputedStyle(д).display !== 'none', кнопка: ок.textContent.trim(),
                           заголовок: document.getElementById('confirmDialogTitle').textContent, поверх: наверху === ок || ок.contains(наверху),
                           вызвано: window.__ОТОЗВАНО, корзина: !!document.querySelector('#confirmDialogIcon polyline') }; }""")
                print(н, р)
                if not р['видно']: НАХОДКИ.append(f"{н} «Отозвать» не спросил подтверждения")
                if р['кнопка'] != 'Отозвать': НАХОДКИ.append(f"{н} на кнопке подтверждения «{р['кнопка']}», ждали «Отозвать»")
                if not р['поверх']: НАХОДКИ.append(f"{н} окно подтверждения под окном «Пресеты» — кнопку не нажать")
                if р['вызвано']: НАХОДКИ.append(f"{н} база вызвана до подтверждения")
                if р.get('корзина'): НАХОДКИ.append(f"{н} над «Отозвать» корзина — пресет же не удаляется")
                if ш == 1440 and not ночь:
                    стр.screenshot(path='/tmp/retract_confirm_1440.png')
                if ш == 390 and ночь:
                    стр.screenshot(path='/tmp/retract_confirm_390_night.png')
                if not р['видно']:
                    стр.close(); continue
                стр.click('#confirmDialogCancel'); стр.wait_for_timeout(200)
                if стр.evaluate("() => document.getElementById('confirmDialog').classList.contains('show') || window.__ОТОЗВАНО"):
                    НАХОДКИ.append(f"{н} «Отмена» не закрыла окно или всё же отозвала")
                стр.evaluate("() => retractPreset('123456')"); стр.wait_for_timeout(150)
                стр.click('#confirmDialogOk'); стр.wait_for_timeout(500)
                раз = стр.evaluate("() => window.__ОТОЗВАНО")
                if раз != 1: НАХОДКИ.append(f"{н} «Отозвать» вызвал базу {раз} раз, ждали 1")
                стр.evaluate("() => showConfirmDialog('Удалить пресет?', 'проба', () => {})")
                if стр.evaluate("() => document.getElementById('confirmDialogOk').textContent.trim()") != 'Удалить' \
                        or not стр.evaluate("() => !!document.querySelector('#confirmDialogIcon polyline')"):
                    НАХОДКИ.append(f"{н} окно удаления осталось с чужой надписью или значком")
                if ош: НАХОДКИ.append(f"{н} ошибки скрипта: {ош}")
                стр.close()
        бр.close()
    с.shutdown()
    if НАХОДКИ:
        print("\nНАХОДКИ:")
        for н in НАХОДКИ: print("  ✗", н)
        sys.exit(1)
    print("\nЧисто: «Отозвать» спрашивает поверх окна «Пресеты», «Отмена» ничего не меняет, "
          "подтверждение отзывает один раз, окно удаления — по-прежнему «Удалить»; на 390 и 1440, днём и ночью.")


if __name__ == '__main__':
    main()
