import nest_asyncio
import asyncio
from playwright.async_api import async_playwright
import datetime

nest_asyncio.apply()

# ==== CẤU HÌNH ====
EMAIL            = "kerch.cabo@cit.edu"
PASSWORD         = "YA20HuyAc63Q4xSK"
# Dùng link gốc, đéo dùng link tham số nữa cho đỡ bị redirect lung tung
LOGIN_URL        = "https://www.kaggle.com/account/login"
NOTEBOOK_NAME    = "notebookb6603a8407" 
HEADLESS_MODE    = True 

def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")

async def click_run_all_if_visible(page):
    try:
        # Bấm Cancel trước
        await page.locator('button:has-text("Cancel")').first.click(timeout=2000)
    except:
        pass

    # Bấm Run All
    selectors = ['button:has-text("Run All")', 'div[role="button"]:has-text("Run All")']
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                log("🚀 BẤM RUN ALL THÀNH CÔNG!")
                return True
        except:
            continue
    return False

async def background_monitor(page):
    log("👀 Background Monitor đang chạy...")
    start_time = asyncio.get_event_loop().time()
    while True:
        await asyncio.sleep(60)
        elapsed = int(asyncio.get_event_loop().time() - start_time)
        try:
            title = await page.title()
            log(f"💤 [BG] Uptime: {elapsed}s | Title: {title}")
        except:
            log("❌ Page crash hoặc đóng rồi.")
            break

async def run():
    log("💀 Bot Kaggle V2 - Fix Login Timeout...")
    
    async with async_playwright() as p:
        # Cấu hình Chrome chống phát hiện bot
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Tiêm script tàng hình
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")

        # --- ĐĂNG NHẬP (SỬA LẠI LOGIC) ---
        log("🔐 Vào trang login...")
        try:
            await page.goto(LOGIN_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # 1. Kiểm tra xem có nút "Sign in with Email" không thì bấm
            try:
                email_option_btn = page.locator('button:has-text("Sign in with Email")').first
                if await email_option_btn.is_visible():
                    log("ℹ️ Thấy nút chọn Email, đang bấm...")
                    await email_option_btn.click()
                    await page.wait_for_timeout(2000)
            except:
                pass

            # 2. Điền Email
            log("✍️ Điền Email...")
            # Dùng selector gắt hơn để tìm input
            await page.wait_for_selector('input[name="email"]', state="visible", timeout=30000)
            await page.fill('input[name="email"]', EMAIL)
            
            # 3. Điền Password
            log("✍️ Điền Password...")
            await page.fill('input[name="password"]', PASSWORD)
            
            # 4. Bấm Submit
            log("🖱️ Bấm Sign In...")
            await page.click('button[type="submit"]')
            
            # Chờ chuyển trang
            await page.wait_for_timeout(5000)
            
            # Debug: In title xem đang ở đâu
            log(f"-> Title hiện tại: {await page.title()}")

            if "login" in page.url:
                log("❌ Vẫn ở trang login. Chụp ảnh lỗi...")
                await page.screenshot(path="login_error.png")
                # In ra HTML để debug nếu cần
                # print(await page.content())
                return

        except Exception as e:
            log(f"❌ LỖI LOGIN: {e}")
            await page.screenshot(path="exception_error.png")
            return

        # --- VÀO NOTEBOOK ---
        log(f"📂 Vào notebook: {NOTEBOOK_NAME}")
        await page.goto(f"https://www.kaggle.com/code/{NOTEBOOK_NAME}", timeout=60000)
        
        # Chờ editor load (lâu vãi lồn đấy)
        try:
            await page.wait_for_selector('button:has-text("Run All")', timeout=30000)
        except:
            log("⚠️ Chưa thấy nút Run All, nhưng cứ thử bấm...")

        # --- CHẠY ---
        await click_run_all_if_visible(page)
        
        # Chạy nền giám sát
        asyncio.create_task(background_monitor(page))

        # --- LOOP ---
        last_click = asyncio.get_event_loop().time()
        while True:
            now = asyncio.get_event_loop().time()
            if now - last_click > 20000: # 5.5 tiếng
                break
            
            if now - last_click > 9000:
                log("🔄 Refresh & Run All...")
                await page.reload()
                await page.wait_for_timeout(15000) # Chờ load lại lâu hơn tí
                await click_run_all_if_visible(page)
                last_click = now
            
            await asyncio.sleep(10)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
