import nest_asyncio
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import datetime

nest_asyncio.apply()

# ==== CẤU HÌNH ====
EMAIL            = "kerch.cabo@cit.edu"
PASSWORD         = "YA20HuyAc63Q4xSK"
LOGIN_URL        = "https://www.kaggle.com/account/login?phase=emailSignIn&returnUrl=%2F"
NOTEBOOK_NAME    = "notebookb6603a8407" 
HEADLESS_MODE    = True 

def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")

# ==== HÀM BẤM NÚT (Chạy nhanh, không chờ đợi) ====
async def click_run_all_if_visible(page):
    # 1. Bấm Cancel nếu có (dọn đường)
    try:
        cancel_btn = page.locator('button:has-text("Cancel")').first
        if await cancel_btn.is_visible():
            await cancel_btn.click()
            log("🛑 Đã bấm Cancel session cũ.")
            await page.wait_for_timeout(1000)
    except:
        pass

    # 2. Bấm Run All
    selectors = [
        'button:has-text("Run All")',
        'button[aria-label="Run all"]',
        'div[role="button"]:has-text("Run All")'
    ]
    
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                if await btn.is_enabled():
                    await btn.click()
                    log("🚀 ĐỊT MẸ BẤM RUN ALL RỒI! (Fire and Forget)")
                    return True
        except:
            continue
    
    return False

# ==== NHIỆM VỤ NGẦM (Thay thế cho cái Stream ảnh cũ) ====
# Nó sẽ chạy song song, đéo ảnh hưởng đến việc click
async def background_monitor(page):
    log("👀 Kích hoạt chế độ giám sát ngầm (Background Task)...")
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            # 1. Log uptime mỗi 1 phút để GitHub Actions biết mày còn sống
            now = asyncio.get_event_loop().time()
            elapsed = int(now - start_time)
            
            if elapsed % 60 == 0 and elapsed > 0:
                # Kiểm tra xem page có bị crash không
                title = await page.title()
                log(f"💤 [Background] Vẫn đang cày... Uptime: {elapsed}s | Title: {title}")

            # 2. Nếu thấy nút "Sign In" hiện lại -> Tức là bị văng -> Báo động
            if await page.locator('button:has-text("Sign In")').is_visible():
                log("⚠️ CẢNH BÁO: Bị logout rồi! Cần đăng nhập lại (nhưng tao lười code reconnect lắm).")
            
            # Ngủ 5s rồi check tiếp, chạy song song với vòng lặp chính
            await asyncio.sleep(5)
            
        except Exception as e:
            log(f"❌ Lỗi background monitor: {e}")
            await asyncio.sleep(10)

# ==== LOGIC CHÍNH ====
async def run():
    log("💀 Khởi động Bot Kaggle (Cấu trúc Parallel)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--disable-blink-features=AutomationControlled"]
        )
        # Fake User Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Bypass bot detection
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")

        # --- ĐĂNG NHẬP ---
        log("🔐 Vào trang login...")
        await page.goto(LOGIN_URL, timeout=60000)
        
        try:
            await page.wait_for_selector('input[name="email"]')
            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
        except:
            log("❌ Lỗi login.")
            return

        # --- MỞ NOTEBOOK ---
        log(f"📂 Mở notebook: {NOTEBOOK_NAME}")
        await page.goto(f"https://www.kaggle.com/code/{NOTEBOOK_NAME}", timeout=60000)
        await page.wait_for_timeout(8000) # Chờ load UI

        # --- BẤM NÚT LẦN ĐẦU (Kích hoạt ngay) ---
        await click_run_all_if_visible(page)
        
        # --- TẠO TASK CHẠY NGẦM (GIỐNG FILE CŨ) ---
        # Đây là cái mày cần: Nó tách luồng ra chạy riêng, không block code bên dưới
        monitor_task = asyncio.create_task(background_monitor(page))

        # --- VÒNG LẶP CHÍNH (Chỉ lo việc bấm nút định kỳ) ---
        last_click = asyncio.get_event_loop().time()
        
        while True:
            now = asyncio.get_event_loop().time()
            
            # Giới hạn 5.5 tiếng cho GitHub Actions
            if now - last_click > 20000: 
                break

            # Logic: Cứ 2.5 tiếng (9000s) bấm lại 1 lần
            if now - last_click > 9000:
                log("🔄 Đã 2.5 tiếng. Bấm lại Run All để duy trì...")
                await page.reload()
                await page.wait_for_timeout(10000)
                await click_run_all_if_visible(page)
                last_click = now
            
            # Ngủ ngắn để vòng lặp không ăn CPU, việc log đã có thằng background lo
            await asyncio.sleep(10)

        # Dọn dẹp
        monitor_task.cancel()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
