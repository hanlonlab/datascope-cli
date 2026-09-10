from playwright.async_api import async_playwright
import asyncio

EXCH_MAP = {
    "NasdaqGM": ".O",
    "NasdaqGS": ".O",
    "NasdaqCM": ".O",
    "NYSEArca": "",
    "NYSE": "",
    "Cboe": ".K",
}

async def get_exch(symbol):
    browsers = ['firefox',] #['chromium', 'firefox', 'webkit']
    async with async_playwright() as p:
        for browser_type in browsers:
            browser = await p[browser_type].launch()
            page = await browser.new_page()
            await page.goto(f'https://finance.yahoo.com/quote/{symbol}/')
            # await page.screenshot(path=f'py_{browser_type}.png', full_page=True)
            await page.wait_for_timeout(1000)

            all_results = await page.query_selector_all('span.exchange.yf-wk4yba > span:nth-child(1)')
            data = []
            for product in all_results:
                result = await product.inner_text() if product else None
                data.append(result)
            try:
                exch_symbol = data[0].split()[0]
            except IndexError:
                exch_symbol = "ERROR"

            all_results = await page.query_selector_all('h1.yf-xxbei9')
            data = []
            for product in all_results:
                result = await product.inner_text() if product else None
                data.append(result)
            try:
                name = data[0]
            except IndexError:
                name = "ERROR"
                
            await browser.close()

            return exch_symbol, name

list_path = "/Users/warble/code/hfsl/hfsl-data/tmp/darsh_tick_request.csv"
out_path = "/Users/warble/code/hfsl/hfsl-data/tmp/darsh_rics.csv"
with open(list_path, "r") as rf, open(out_path, "a") as wf:
    wf.write("symbol,date,name,exchange,ric\n")
    rf.readline()
    lines = rf.readlines()[71:]
    for line in lines:
        sym = line.split(",")[0]
        if "-" in sym:
            clean_sym = f"{sym.split("-")[0]}{sym.split("-")[1].lower()}"
        else:
            clean_sym = sym
        exch, name = asyncio.run(get_exch(symbol=sym))
        wf.write(f'{line[:-1]},"{name}",{exch},{clean_sym}{EXCH_MAP.get(exch,f".{exch}")}\n')

# exch = asyncio.run(get_exch(symbol="AAPL"))
# print(exch)