#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимки макета: каждый вариант в «Бланке» и «Модерне», телефон и компьютер.

    python3 shots.py макет.html папка
"""
import os, pathlib, sys
from playwright.sync_api import sync_playwright
макет, папка = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]); папка.mkdir(parents=True, exist_ok=True)
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1100})
    ошибки = []; стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(макет.as_uri()); стр.wait_for_timeout(2500)
    for т in ("blank", "light"):
        стр.click(f'#theme button[data-t="{т}"]')
        for в in "0123":
            стр.click(f'#vars button[data-v="{в}"]'); стр.wait_for_timeout(300)
            стр.locator(".frames").screenshot(path=str(папка / f"{т}-v{в}.png"))
    стр.set_viewport_size({"width": 390, "height": 900}); стр.wait_for_timeout(400)
    стр.screenshot(path=str(папка / "page-390.png"), full_page=True)
    print("ошибки:", ошибки[:3], "ширина:", стр.evaluate("document.documentElement.scrollWidth"))
    бр.close()

# ── мерки: зазор до края карточки и до соседа, переполнение ──
МЕРА = r"""() => {
  const out = [];
  document.querySelectorAll('#codePresetList .shared-pcard').forEach((к, i) => {
    const кр = к.getBoundingClientRect();
    к.querySelectorAll('.mk-v0, .mk-v1, .mk-v2, .mk-v3').forEach(э => {
      if (!э.offsetWidth) return;
      const r = э.getBoundingClientRect();
      const бр = [...э.parentElement.children].filter(x => x !== э && x.offsetWidth && getComputedStyle(x).position !== 'absolute').map(x => x.getBoundingClientRect());
      const сосед = Math.min(...бр.filter(b => b.bottom > r.top && b.top < r.bottom).map(b => Math.max(r.left - b.right, b.left - r.right)), 999);
      out.push({ карт: i, класс: э.className.baseVal || э.className, доПрава: Math.round(кр.right - r.right), доВерха: Math.round(r.top - кр.top), сосед: Math.round(сосед), h: Math.round(r.height), w: Math.round(r.width) });
    });
  });
  return { out, шире: document.documentElement.scrollWidth > innerWidth + 1 };
}"""
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1100})
    стр.goto(макет.as_uri()); стр.wait_for_timeout(2500)
    for т in ("blank", "light"):
        стр.click(f'#theme button[data-t="{т}"]')
        for в in "0123":
            стр.click(f'#vars button[data-v="{в}"]'); стр.wait_for_timeout(250)
            for i, ф in enumerate(стр.frames[1:]):
                м = ф.evaluate(МЕРА)
                print(т, "v" + в, ["390", "1280"][i], "шире" if м["шире"] else "", [(x["карт"], x["доПрава"], x["сосед"], x["h"]) for x in м["out"]])
    бр.close()
