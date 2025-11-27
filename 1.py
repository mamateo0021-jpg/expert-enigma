import nest_asyncio
import asyncio
from playwright.async_api import async_playwright
import datetime
import random

nest_asyncio.apply()

# ==== CẤU HÌNH CỦA THẰNG ĂN CẮP TÀI NGUYÊN ====
# Khuyên mày nên dùng GitHub Secrets để giấu pass, nhưng mày ngu thì cứ điền thẳng vào đây
EMAIL            = "kerch.cabo@cit.edu"
PASSWORD         = "YA20HuyAc63Q4xSK"
LOGIN_URL        = "https://www.kaggle.com/account/login?phase=emailSignIn&returnUrl=%2F"
NOTEBOOK_NAME    = "notebookb6603a8407" # Tên notebook phải chuẩn nhé thằng đần
HEADLESS_MODE    = True # GitHub Actions bắt buộc phải Headless

def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")

# ==== Hàm bấm nút Run All ====
async def click_run_all_if_visible(page):
    # 1. Tìm nút Cancel để bấm trước (nếu đang chạy dở)
    try:
        cancel_btn = page.locator('button:has-text("Cancel")').first
        if await cancel_btn.is_visible():
            await cancel_btn.click()
            log("🛑 Đã bấm Cancel session cũ.")
            await page.wait_for_timeout(2000)
    except:
        pass

    # 2. Tìm nút Run All
    selectors = [
        'button:has-text("Run All")',
        'button[aria-label="Run all"]',
        'div[role="button"]:has-text("Run All")'
    ]
    
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                log("🚀 ĐỊT MẸ BẤM RUN ALL RỒI NHÉ!")
                return True
        except:
            continue
    
    log("⚠️ Đéo thấy nút Run All đâu cả.")
    return False

# ==== Main Logic ====
async def run():
    log("💀 Khởi động Bot Kaggle cho GitHub Actions...")
    
    async with async_playwright() as p:
        # Cấu hình browser tàng hình
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", 
                "--disable-setuid-sandbox"
            ]
        )
        
        # Fake User Agent để Kaggle đỡ nghi ngờ
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()

        # Script xóa dấu vết bot
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        # --- ĐĂNG NHẬP ---
        log("🔐 Đang vào trang login...")
        try:
            await page.goto(LOGIN_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)
            
            # Bấm nút Sign In
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Check xem vào được chưa
            if "login" not in page.url:
                log("✅ Login ngon lành cành đào.")
            else:
                log("❌ Login thất bại. Kiểm tra lại pass đi thằng ngu.")
                # Chụp ảnh lỗi lưu lại artifact (nếu cần)
                # await page.screenshot(path="login_error.png")
                return

        except Exception as e:
            log(f"❌ Lỗi login: {e}")
            return

        # --- MỞ NOTEBOOK ---
        log(f"📂 Đang tìm notebook: {NOTEBOOK_NAME}...")
        try:
            # Search hoặc vào thẳng link notebook của mày
            # Cách an toàn nhất là vào thẳng URL nếu mày biết, nhưng ở đây tao làm theo cách search text
            # Mày nên thay dòng này bằng: await page.goto("URL_CUA_NOTEBOOK") cho nhanh
            await page.goto(f"https://www.kaggle.com/code/{NOTEBOOK_NAME}", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(5000)
            
            title = await page.title()
            log(f"-> Đã vào trang: {title}")

        except Exception as e:
            log(f"❌ Không vào được notebook: {e}")
            return

        # --- KÍCH HOẠT CHẠY ---
        await click_run_all_if_visible(page)
        
        # --- VÒNG LẶP DUY TRÌ (KEEP ALIVE) ---
        log("⏳ Bắt đầu chế độ AFK giữ session...")
        start_time = asyncio.get_event_loop().time()
        last_click = start_time
        
        while True:
            now = asyncio.get_event_loop().time()
            elapsed = int(now - start_time)
            
            # GitHub Actions thường giới hạn 6 tiếng (21600s), tao để 5.5 tiếng tự ngắt
            if elapsed > 19800: 
                log("🛑 Sắp hết giờ GitHub Actions. Tự hủy.")
                break
            
            # Cứ 2.5 tiếng (9000s) bấm lại Run All một lần để Kaggle không kill session
            if now - last_click > 9000:
                log("🔄 Đã 2.5 tiếng, bấm lại Run All để refresh...")
                await page.reload() # F5 lại trang cho chắc
                await page.wait_for_timeout(10000)
                await click_run_all_if_visible(page)
                last_click = now
            
            # In log mỗi 5 phút để GitHub không tưởng script bị treo
            if elapsed % 300 == 0:
                log(f"💤 Vẫn đang chạy... (Uptime: {elapsed}s)")
            
            await asyncio.sleep(10)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
