#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимки принадлежат своему расчёту и не переходят в соседний.

Константин 20.09.2026, двумя снимками экрана: «фото загружены в пресет Берлин.
Когда меняю пресет, они переходят в другой пресет. Фото должны быть только в
том пресете, в котором они загружены».

Так и было: раскладка снимков ставилась только тогда, когда в расчёте они есть,
а пустой список считался «делать нечего» — и холст оставался с картинками
прежнего расчёта. Беда тихая: на экране всё выглядит целым, чужие фотографии
стоят на своих местах, и уходят они в печать под чужой сметой.

Проба открывает расчёты по очереди и считает снимки на холсте:

  • расчёт со снимками открыт — снимки его;
  • следом открыт расчёт без снимков — холст пуст;
  • вернулись к первому — снимки вернулись;
  • открытие расчёта снимками не считается правкой: пресет не помечен
    грязным, иначе автосохранение переписало бы его раскладкой соседа;
  • выбран другой проект — холст пуст; снят выбор проекта — тоже пуст.
    Вторая ветка своя: «снять выбор» идёт мимо onProjectChange, где стоит
    очистка, и снимки снятого расчёта оставались на экране;
  • сменилась технология — холст пуст, а расчёт другой технологии всё равно
    открывается со своими снимками: восстановление само меняет технологию,
    и очистка, поставленная без оглядки, стёрла бы уже разложенное;
  • «Сбросить всё» снимки уносит, а выключенный в настройках пункт
    «Визуализация и планировка» их оставляет — это обещано в справке.

    python3 check_preset_photos.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []

# Однопиксельный png — снимку в пробе важно быть картинкой, а не фотографией.
ТОЧКА = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
         "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


def не_один(н):
    return н != 1


СЧЁТ = """() => ({
  снимков: document.querySelectorAll('.canvas-img-item').length,
  грязный: typeof _presetDirty !== 'undefined' ? !!_presetDirty : null,
  активный: (typeof activePresetId !== 'undefined') ? activePresetId : null,
})"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 950})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                                + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2600)

            # ── Два расчёта: один со снимками, другой без ────────────────────
            готово = стр.evaluate("""async (точка) => {
              const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
              window._sbProfile = { role: 'admin', full_name: 'Проба' };
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 1200));

              const все = loadAllPresets();
              // Сначала расчёт БЕЗ снимков: холст пуст.
              canvasClearAll();
              все['без'] = { id: 'без', name: 'Расчёт без снимков',
                             savedAt: new Date().toISOString(), state: collectState() };
              // Теперь со снимками — два, чтобы счёт отличался и от единицы.
              canvasAddImage(точка);
              canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 300));
              все['со'] = { id: 'со', name: 'Расчёт со снимками',
                            savedAt: new Date().toISOString(), state: collectState() };
              localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(все));
              canvasClearAll();
              return {
                вЗаписи: (все['со'].state.canvasImages || []).length,
                вПустом: (все['без'].state.canvasImages || []).length,
              };
            }""", ТОЧКА)
            if готово["вЗаписи"] != 2:
                плохо(f"в сохранённом расчёте {готово['вЗаписи']} снимков вместо двух — "
                      "мерить переход нечем")
            if готово["вПустом"]:
                плохо(f"в расчёт без снимков попало {готово['вПустом']} — "
                      "он должен быть пустым")

            def открыть(ид):
                стр.evaluate("(и) => loadPreset(и)", ид)
                стр.wait_for_timeout(1300)
                return стр.evaluate(СЧЁТ)

            # ── Расчёт со снимками — снимки его ──────────────────────────────
            в = открыть("со")
            if в["снимков"] != 2:
                плохо(f"открыт расчёт со снимками, а на холсте их {в['снимков']} "
                      "вместо двух — снимки не вернулись из записи")

            # ── Следом расчёт без снимков — холст пуст ───────────────────────
            в = открыть("без")
            if в["снимков"]:
                плохо(f"открыт расчёт без снимков, а на холсте {в['снимков']} — "
                      "это фотографии соседнего расчёта, и они уйдут в его печать")
            if в["грязный"]:
                плохо("открытие расчёта помечено правкой — автосохранение "
                      "переписало бы его раскладкой соседа")

            # ── Вернулись к первому — снимки вернулись ───────────────────────
            в = открыть("со")
            if в["снимков"] != 2:
                плохо(f"вернулись к расчёту со снимками, а их {в['снимков']} — "
                      "очистка холста забрала и свои")
            if в["грязный"]:
                плохо("возврат к расчёту со снимками помечен правкой")

            # ── Смена проекта уносит снимки ──────────────────────────────────
            # Снимки принадлежат расчёту, а расчёт начинается с проекта: на
            # новом проекте прежние фотографии — чужие, и уехали бы в печать
            # новой спецификации.
            стр.evaluate("""async () => {
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 6'));
              selectProjectOption(и >= 0 ? и : 1);
              await new Promise(r => setTimeout(r, 1200));
            }""")
            в = стр.evaluate(СЧЁТ)
            if в["снимков"]:
                плохо(f"выбран другой проект, а на холсте {в['снимков']} снимков — "
                      "фотографии прежнего расчёта уедут в новую спецификацию")

            # ── Снятие выбора проекта — тоже ─────────────────────────────────
            # Отдельная ветка: «снять выбор» идёт мимо onProjectChange, и
            # очистка, стоящая там, сюда не достаёт. Расчёта без проекта нет,
            # значит и снимкам держаться не на чем.
            стр.evaluate("""async (точка) => {
              canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 300));
              selectProjectOption(-1);
              await new Promise(r => setTimeout(r, 800));
            }""", ТОЧКА)
            в = стр.evaluate(СЧЁТ)
            if в["снимков"]:
                плохо(f"выбор проекта снят, а на холсте {в['снимков']} снимков — "
                      "расчёта нет, а фотографии от него остались")

            # ── Смена технологии уносит снимки ───────────────────────────────
            # Технология меняет всё: проект, позиции, цены, дописанное руками.
            # Расчёт начинается заново — и снимки прежнего в нём такие же
            # чужие, как чужой проект. В наборе проб для этого есть брусовые
            # строки: выдуманные, как и каркасные.
            стр.evaluate("""async (точка) => {
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 300));
            }""", ТОЧКА)
            если = стр.evaluate(СЧЁТ)
            if не_один(если["снимков"]):
                плохо(f"перед сменой технологии на холсте {если['снимков']} снимков "
                      "вместо одного — мерить переход нечем")
            вышло = стр.evaluate("""async () => {
              await switchTech('glulam');
              await new Promise(r => setTimeout(r, 900));
              return { тех: currentTech,
                       снимков: document.querySelectorAll('.canvas-img-item').length };
            }""")
            if вышло["тех"] != "glulam":
                плохо("технология не переключилась на брус — "
                      f"осталась «{вышло['тех']}», переход мерить нечем")
            elif вышло["снимков"]:
                плохо(f"сменилась технология, а на холсте {вышло['снимков']} снимков — "
                      "фотографии каркасного расчёта остались в брусовом")

            # ── Расчёт чужой технологии открывается со своими снимками ───────
            # Оборотная сторона очистки: восстановление расчёта само меняет
            # технологию, и очистка, поставленная в `switchTech` без оглядки,
            # стёрла бы уже разложенные снимки — расчёт открывался бы пустым.
            # Поэтому мерим не только «чужие ушли», но и «свои пришли».
            вышло = стр.evaluate("""async (точка) => {
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Брусовая проба'));
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              canvasAddImage(точка); canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 300));
              const все = loadAllPresets();
              все['брус'] = { id: 'брус', name: 'Брусовый расчёт со снимками',
                              savedAt: new Date().toISOString(), state: collectState() };
              localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(все));
              await switchTech('frame');
              await new Promise(r => setTimeout(r, 900));
              const послеСмены = document.querySelectorAll('.canvas-img-item').length;
              loadPreset('брус');
              await new Promise(r => setTimeout(r, 3000));
              return {
                послеСмены,
                тех: currentTech,
                снимков: document.querySelectorAll('.canvas-img-item').length,
                грязный: typeof _presetDirty !== 'undefined' ? !!_presetDirty : null,
              };
            }""", ТОЧКА)
            if вышло["послеСмены"]:
                плохо(f"возврат к каркасу оставил {вышло['послеСмены']} снимков "
                      "брусового расчёта")
            if вышло["тех"] != "glulam":
                плохо("открыт брусовый расчёт, а технология осталась "
                      f"«{вышло['тех']}» — мерить снимки не на чем")
            elif вышло["снимков"] != 2:
                плохо(f"брусовый расчёт открыт, а снимков в нём {вышло['снимков']} "
                      "вместо двух — очистка при смене технологии стёрла свои же")
            if вышло["грязный"]:
                плохо("открытие расчёта другой технологии помечено правкой")

            # ── «Сбросить всё» уносит снимки, а выключенный пункт оставляет ──
            # У сброса свой список: каждый пункт можно выключить в настройках,
            # и «Визуализация и планировка» — один из них. Значит, мерить надо
            # обе стороны. Сторона «оставляет» важнее: она и есть обещание,
            # данное в справке, и сломать её легко — достаточно поставить
            # очистку мимо `cfg.images`, и выключенный пункт замолчит.
            сброс = стр.evaluate("""async (точка) => {
              const и = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
              selectProjectOption(и >= 0 ? и : 0);
              await new Promise(r => setTimeout(r, 900));
              canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 250));
              const до = document.querySelectorAll('.canvas-img-item').length;
              resetEverything();
              await new Promise(r => setTimeout(r, 700));
              const после = document.querySelectorAll('.canvas-img-item').length;

              // Пункт выключен — снимки обязаны пережить сброс.
              appSettings.resetAllConfig = appSettings.resetAllConfig || {};
              appSettings.resetAllConfig.images = false;
              const и2 = PROJECTS.findIndex(p => p && String(p[0]).includes('Проба дом 8'));
              selectProjectOption(и2 >= 0 ? и2 : 0);
              await new Promise(r => setTimeout(r, 900));
              canvasAddImage(точка);
              await new Promise(r => setTimeout(r, 250));
              resetEverything();
              await new Promise(r => setTimeout(r, 700));
              const приВыключенном = document.querySelectorAll('.canvas-img-item').length;
              delete appSettings.resetAllConfig.images;
              return { до, после, приВыключенном,
                       вСписке: сколькоСбрасывается() };
            }""", ТОЧКА)
            if не_один(сброс["до"]):
                плохо(f"перед сбросом на холсте {сброс['до']} снимков вместо одного — "
                      "мерить сброс нечем")
            elif сброс["после"]:
                плохо(f"нажато «Сбросить всё», а на холсте {сброс['после']} снимков — "
                      "расчёт начат заново, а фотографии прежнего остались")
            if сброс["приВыключенном"] != 1:
                плохо("пункт «Визуализация и планировка» в списке сброса выключен, "
                      f"а снимков после сброса {сброс['приВыключенном']} вместо одного — "
                      "выключатель ничего не решает, и справка обещает несбыточное")
            if "из 14" not in сброс["вСписке"]:
                плохо(f"в списке сброса {сброс['вСписке']} — пунктов стало другое "
                      "число, проверить строку счётчика")

            if ошибки:
                плохо("ошибки страницы: " + "; ".join(ошибки)[:220])
            стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: снимки приходят вместе со своим расчётом и уходят вместе с ним — "
          "при смене расчёта, проекта, технологии, при снятии выбора и при сбросе; "
          "выключенный пункт сброса их оставляет, а открытие расчёта правкой "
          "не считается.")


if __name__ == "__main__":
    главная()
