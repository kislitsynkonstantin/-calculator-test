import functools, http.server, socketserver, threading, pathlib, sys
from playwright.sync_api import sync_playwright
ВЫХ = pathlib.Path(sys.argv[1])
class Т(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а): pass
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Т, directory='/home/user/-calculator-test/mockups'))
threading.Thread(target=с.serve_forever, daemon=True).start()
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for ш, в in ((1440, 900), (390, 844)):
        стр = бр.new_page(viewport={"width": ш, "height": в}, device_scale_factor=1)
        ош = []; стр.on("pageerror", lambda e: ош.append(str(e))); стр.on("requestfailed", lambda r: ош.append('сеть: ' + r.url[:80]))
        стр.goto(f"http://127.0.0.1:{с.server_address[1]}/steam-page-v1.html", wait_until="load"); стр.wait_for_timeout(800)
        т = lambda: стр.evaluate("() => [document.getElementById('totalDisplay').textContent, document.getElementById('sec_total_st').textContent, document.getElementById('optprice_premium').textContent, document.getElementById('why_premium').textContent, document.getElementById('why_yalta').textContent, document.documentElement.scrollWidth - document.documentElement.clientWidth]")
        print(ш, 'старт', т(), 'ошибки', ош[:3])
        стр.screenshot(path=str(ВЫХ / f'стр-{ш}.png'), full_page=True)
        if ш == 1440:
            стр.locator('#lbl_okno .opt-name').click(); print('без окна', т())
            стр.locator('#lbl_okno .opt-name').click()
            и = стр.locator('.dim-in[data-dim="L"]'); и.fill('3,6'); стр.keyboard.press('Tab'); print('L=3,6', т())
            стр.locator('#lbl_optima .opt-name').click(); print('Оптима', т(), стр.evaluate("() => [lbl_yalta.classList.contains('active'), lbl_optima.classList.contains('active'), why_optima.textContent]"))
            стр.locator('#qtyval_podsv').locator('xpath=following-sibling::button').click(); print('3 уровня', т())
            стр.locator('#projectSelectTrigger').click(); стр.locator('[data-room="frame"]').click(); print('каркасный дом', т(), стр.evaluate("() => [lbl_karkas.classList.contains('active'), why_karkas.textContent]"))
            стр.evaluate("() => scrollTo(0, 3000)"); стр.wait_for_timeout(300); print('полоска', стр.evaluate("() => [totalStrip.classList.contains('on'), tsVal.textContent]"))
            стр.screenshot(path=str(ВЫХ / 'стр-после.png'))
        print(ш, 'ошибки', ош[:3])
        стр.close()
    бр.close()
с.shutdown()
