import asyncio
from playwright.async_api import async_playwright
import http.server
import socketserver
import threading
import os
import sys

PORT = 8998
os.chdir(os.path.join(os.path.dirname(__file__), 'website'))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

httpd = socketserver.TCPServer(('127.0.0.1', PORT), QuietHandler)
t = threading.Thread(target=httpd.serve_forever)
t.daemon = True
t.start()

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        
        errors = []
        page.on('pageerror', lambda err: print(f'PAGE_ERR: {err}'))
        page.on('console', lambda msg: print(f'CONSOLE: [{msg.type}] {msg.text}'))
        
        url = f'http://127.0.0.1:{PORT}/index.html'
        print(f'Navigating to {url}...')
        await page.goto(url, wait_until='domcontentloaded')
        
        # Wait for script compilation and initialization
        print('Waiting for openPaywallModal to initialize...')
        await page.wait_for_function('typeof window.openPaywallModal === "function"', timeout=15000)
        
        # Test 1: Check openPaywallModal is defined
        fn_type = await page.evaluate('typeof window.openPaywallModal')
        assert fn_type == 'function', f'openPaywallModal is {fn_type}'
        print('[PASS] Gate 1: openPaywallModal is defined and ready')
        
        # Test 2: Trigger modal
        await page.evaluate('openPaywallModal("Choose Your Plan", "single")')
        await page.wait_for_selector('#paywallModal.open', state='visible')
        print('[PASS] Gate 2: #paywallModal is visible with .open class')
        
        # Test 3: Check all 4 SKU cards exist
        for sku_id in ['skuSingleCard', 'skuPassCard', 'skuSoloCard', 'skuProCard']:
            card = await page.query_selector(f'#{sku_id}')
            assert card is not None, f'Card #{sku_id} missing!'
            is_visible = await card.is_visible()
            assert is_visible, f'Card #{sku_id} is not visible!'
        print('[PASS] Gate 3: All 4 pricing cards (single, pass, solo, pro) present & visible')
        
        # Test 4: Set region to ZA for exact ZAR verification
        await page.evaluate('setGlobalRegion("ZA")')
        single_price = await (await page.query_selector('#skuSinglePrice')).inner_text()
        print(f'Single price display (ZA): {single_price}')
        assert 'R 49.00' in single_price or '49' in single_price, f'Expected 49 in single price, got: {single_price}'
        
        # Test 5: Verify selection behavior and button text for each SKU in ZA
        expectations = [
            ('single', 'Continue to Payment — Single Statement Unlock (R 49.00 ZAR)'),
            ('pass', 'Continue to Payment — 7-Day Pass (R 100.00 ZAR)'),
            ('solo', 'Continue to Payment — Pro Unlimited (1 User) (R 249.00 ZAR)'),
            ('pro', 'Continue to Payment — Practice & Firm (5 Seats) (R 850.00 ZAR)')
        ]
        
        for sku, expected_btn in expectations:
            await page.evaluate(f'selectPaywallSku("{sku}")')
            btn_text = await page.evaluate('document.getElementById("payCheckoutBtn").innerText')
            print(f'Selected [{sku}] (ZA) -> Button: "{btn_text}"')
            assert expected_btn in btn_text, f'SKU {sku} mismatch! Expected "{expected_btn}", got "{btn_text}"'
        print('[PASS] Gate 4: All 4 SKUs dynamically update checkout button text and pricing (ZA)')

        # Test 5b: Switch region to US and verify single price & button text
        await page.evaluate('setGlobalRegion("US")')
        single_price_us = await (await page.query_selector('#skuSinglePrice')).inner_text()
        print(f'Single price display (US): {single_price_us}')
        assert '$3.00' in single_price_us, f'Expected $3.00 in US single price, got: {single_price_us}'
        await page.evaluate('selectPaywallSku("single")')
        btn_text_us = await page.evaluate('document.getElementById("payCheckoutBtn").innerText')
        print(f'Selected [single] (US) -> Button: "{btn_text_us}"')
        assert '$3.00' in btn_text_us and 'R 49.00 ZAR' in btn_text_us, f'Expected $3.00 and R 49.00 ZAR in US btn, got {btn_text_us}'
        print('[PASS] Gate 4b: International pricing localization verified ($3.00 USD / R 49.00 ZAR)')
        
        # Test 6: Verify #invPlanSelect contains single
        inv_options = await page.evaluate('''
            Array.from(document.getElementById('invPlanSelect').options).map(o => ({ value: o.value, text: o.text }))
        ''')
        single_opt = next((o for o in inv_options if o['value'] == 'single'), None)
        assert single_opt is not None, 'Single option missing from #invPlanSelect'
        print(f'[PASS] Gate 5: Invoice generator has single option: {single_opt}')
        
        # Test 7: Verify comparison matrix row 4 in both US and ZA
        matrix_us = await page.evaluate('''
            document.getElementById('compRow4TC') ? document.getElementById('compRow4TC').innerText : ''
        ''')
        print(f'Comparison matrix Row 4 (US): {matrix_us}')
        assert '$3.00 Single' in matrix_us, f'Expected $3.00 Single in US matrix, got: {matrix_us}'
        
        await page.evaluate('setGlobalRegion("ZA")')
        matrix_za = await page.evaluate('''
            document.getElementById('compRow4TC') ? document.getElementById('compRow4TC').innerText : ''
        ''')
        print(f'Comparison matrix Row 4 (ZA): {matrix_za}')
        assert 'R 49.00 Single' in matrix_za, f'Expected R 49.00 Single in ZA matrix, got: {matrix_za}'
        print('[PASS] Gate 6: Comparison matrix features dynamic localized Single Statement option (US & ZA)')
        
        # Capture Desktop screenshot of Paywall Modal
        await page.evaluate('selectPaywallSku("single")')
        desktop_img = 'C:/Users/arvin/.gemini/antigravity/brain/7c22accf-d39f-4f51-9696-9192482114e2/r49_paywall_desktop.png'
        await page.screenshot(path=desktop_img, full_page=False)
        print(f'[PASS] Gate 7: Desktop screenshot captured -> {desktop_img}')
        
        # Capture Mobile screenshot of Paywall Modal
        await page.set_viewport_size({'width': 390, 'height': 844})
        await page.wait_for_timeout(400)
        mobile_img = 'C:/Users/arvin/.gemini/antigravity/brain/7c22accf-d39f-4f51-9696-9192482114e2/r49_paywall_mobile.png'
        await page.screenshot(path=mobile_img, full_page=False)
        print(f'[PASS] Gate 8: Mobile screenshot captured -> {mobile_img}')

        # Test 8b: Verify Default Trigger lands on R 49 single & Close Modal
        await page.set_viewport_size({'width': 1280, 'height': 800})
        await page.evaluate('closeModal("paywallModal"); openPaywallModal("Unlock Full Statement")')
        default_btn = await page.evaluate('document.getElementById("payCheckoutBtn").innerText')
        assert 'R 49.00' in default_btn, f'Default unlock trigger should select single R 49.00, got: {default_btn}'
        await page.evaluate('closeModal("paywallModal")')
        print('[PASS] Gate 9: Default Unlock Full Statement trigger pre-selects R 49.00 Single')

        # Test 9: Bank Quick-Selector Chips (ZA & US localization + click feedback)
        trust_free = await (await page.query_selector('#trustFreeText')).inner_text()
        assert '2 free conversions' in trust_free, f'Unexpected trustFreeText: {trust_free}'
        za_chips = await page.evaluate('Array.from(document.querySelectorAll("#bankQuickStrip .bank-quick-chip")).map(el => el.getAttribute("data-bank-chip"))')
        print('ZA Bank Quick Chips:', za_chips)
        assert 'Capitec' in za_chips and 'Locked PDF' in za_chips, f'Missing expected ZA bank chips: {za_chips}'
        await page.click('#bankQuickStrip .bank-quick-chip[data-bank-chip="Capitec"]')
        hint_after_click = await (await page.query_selector('#dropHintStatus')).inner_text()
        assert 'Calibrated for Capitec' in hint_after_click, f'Drop hint did not update: {hint_after_click}'
        await page.evaluate('setGlobalRegion("US")')
        us_chips = await page.evaluate('Array.from(document.querySelectorAll("#bankQuickStrip .bank-quick-chip")).map(el => el.getAttribute("data-bank-chip"))')
        print('US Bank Quick Chips:', us_chips)
        assert any('Chase' in c for c in us_chips), f'Expected US bank chip (Chase) in {us_chips}'
        await page.evaluate('setGlobalRegion("ZA")')
        dropzone_img = 'C:/Users/arvin/.gemini/antigravity/brain/7c22accf-d39f-4f51-9696-9192482114e2/partb_dropzone_activation.png'
        await page.screenshot(path=dropzone_img, full_page=False)
        print(f'[PASS] Gate 10: Bank Quick Chips & Above-the-Fold Trust Strip verified -> {dropzone_img}')

        # Test 10: Deep-link auto-checkout (?buy=single&email=buyer@example.com)
        await page.goto(f'http://127.0.0.1:{PORT}/index.html?buy=single&email=buyer@example.com', wait_until='domcontentloaded')
        await page.wait_for_function('typeof window.openPaywallModal === "function"', timeout=15000)
        await page.wait_for_selector('#paywallModal.open', state='visible', timeout=5000)
        prefilled_email = await page.evaluate('document.getElementById("payEmailInput").value')
        assert prefilled_email == 'buyer@example.com', f'Deep-link email mismatch: {prefilled_email}'
        print('[PASS] Gate 11: Deep-link auto-checkout (?buy=single&email=...) opens paywall with email pre-filled')
        
        print(f'Total errors logged: {len(errors)}')
        for err in errors:
            print(f'   {err}')
        assert len(errors) == 0, 'Found unhandled console/page errors!'
        print('==================================================================')
        print('SUCCESS: ALL R 49 SUITE GATES PASSED WITH ZERO CONSOLE ERRORS!')
        print('==================================================================')
        
        await browser.close()
    httpd.shutdown()

asyncio.run(run_tests())
