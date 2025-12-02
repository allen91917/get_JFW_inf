import os
import sys
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

# ============================
# 取得執行檔所在目錄（支援 PyInstaller 打包）
# ============================
def get_base_dir():
    """
    取得程式執行的基礎目錄
    如果是 PyInstaller 打包的 exe，會返回 exe 所在目錄
    如果是 Python 腳本，會返回腳本所在目錄
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包後的 exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是 Python 腳本
        return os.path.dirname(os.path.abspath(__file__))

# ============================
# 設定參數（可獨立管理）
# ============================
LOGIN_URL = "https://ad.jfw-win.com/#/agent-login"
PERSONAL_URL = "https://ad.jfw-win.com/#/agent/report-manage/agentReport"

# ============================
# 報表功能 XPath 常數
# ============================
XPATH_REPORT = "//div[@class='link-item' and .//div[text()='報表']]"
XPATH_LEDGER = "//div[@class='pk-radio-label-normal' and text()='總帳損益']"
XPATH_LAST_WEEK = "//div[@class='pk-radio-label-mini' and text()='上週']"
XPATH_SEARCH = "/html/body/div/div[2]/div/section/main/div[4]/div[3]/button"

# ============================s
# 取得 Chrome 主版本（Mac / Windows）
# ============================
def get_chrome_version() -> str:
    """取得 Chrome 主版號（例如 131）。"""
    try:
        system = platform.system()

        if system == "Darwin":  # macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            cmd = [chrome_path, "--version"]
        elif system == "Windows":
            cmd = ["reg", "query", r"HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon", "/v", "version"]
        else:
            raise Exception("不支援的系統")

        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8")

        if system == "Windows":
            version = output.split()[-1]
        else:
            version = output.replace("Google Chrome", "").strip()

        return version.split(".")[0]  # 主版號
    except Exception as e:
        print("❌ 無法取得 Chrome 版本：", e)
        return None


# ============================
# 建立 Selenium Driver
# ============================
def create_driver():
    """使用 webdriver-manager 自動管理 ChromeDriver"""
    print("🌐 正在初始化 Chrome Driver...")
    
    # Chrome Options
    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # 使用 webdriver-manager 自動下載和管理 chromedriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    print("✅ Chrome Driver 初始化完成")
    return driver


# ============================
# 讀取用戶帳密 TXT
# ============================
def read_all_user_info():
    """
    讀取用戶資訊.txt 中的所有帳號密碼
    每一行格式： account,password
    回傳 List[Tuple[str, str]]
    """
    base_dir = get_base_dir()  # 使用新的函數取得正確路徑
    txt_path = os.path.join(base_dir, "用戶資訊.txt")

    if not os.path.exists(txt_path):
        print(f"❌ 找不到 用戶資訊.txt")
        print(f"📁 當前查找路徑: {txt_path}")
        print(f"📂 exe 所在目錄: {base_dir}")
        raise FileNotFoundError(f"❌ 找不到 用戶資訊.txt，請確保檔案與 exe 在同一資料夾")

    user_list = []
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "," not in line:
            print(f"⚠ 格式錯誤略過：{line}")
            continue

        account, password = line.split(",", 1)
        user_list.append((account.strip(), password.strip()))

    return user_list


def input_account_password(driver, account, password):
    """輸入指定帳密"""
    wait = WebDriverWait(driver, 10)

    acc_input = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@placeholder='請輸入帳號']")
    ))
    acc_input.clear()
    acc_input.send_keys(account)

    pwd_input = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@placeholder='請輸入密碼']")
    ))
    pwd_input.clear()
    pwd_input.send_keys(password)

    print(f"✔ 已輸入帳密：{account} / {password}")



def click_login_button(driver):
    """
    自動點擊登入按鈕
    """
    wait = WebDriverWait(driver, 10)
    login_btn = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "/html/body/div/div/div/form/div[2]/button"
    )))
    login_btn.click()
    print("✔ 已點擊登入按鈕")

def click_radio_by_value(driver, value, timeout=10):
    """
    透過 radio 的 value 自動點擊 ElementUI 的 radio。
    
    :param driver: Selenium WebDriver
    :param value: <input value="xxx"> 的值，例如 "lastweek"
    :param timeout: 等待秒數
    """

    wait = WebDriverWait(driver, timeout)

    # 1. 找到 input[value=目標]
    input_el = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"input.el-radio__original[value='{value}']")
        )
    )

    # 2. 找到上層 label（ElementUI radio 結構固定）
    label_el = input_el.find_element(By.XPATH, "./ancestor::label")

    # 3. 如果已打勾，就不用點
    if "is-checked" in label_el.get_attribute("class"):
        print(f"✔ Radio 已經被打勾：{value}")
        return

    # 4. 點擊 label（ElementUI 必須點 label 才會變 checked）
    driver.execute_script("arguments[0].click();", label_el)
    print(f"👉 已幫你打勾：{value}")

def click_search_button(driver, timeout=10):
    """
    使用你提供的 XPath 點擊 <div class='reser'>立即查詢</div>
    """

    xpath = "//div[@class='reser' and text()='立即查詢']"

    wait = WebDriverWait(driver, timeout)

    # 等到元素可點擊
    btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

    # 使用 JS click 確保能點擊成功
    driver.execute_script("arguments[0].click();", btn)

    print("👉  XPath 已成功點擊:立即查詢")

def parse_agent_report(driver):
    """
    解析代理報表資料
    """
    # 等待頁面載入完成
    time.sleep(3)
    
    # 取得頁面 HTML
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # 找到所有的 strip-item
    strip_items = soup.find_all('div', {'class': 'strip-item', 'data-v-95d7a5b4': ''})
    
    results = []
    
    for item in strip_items:
        try:
            # 提取基本資訊
            data = {}
            
            # 帳號
            account_elem = item.find('div', {'class': 'cratedate'}, string=lambda x: x and '帳號' in x)
            if account_elem:
                data['帳號'] = account_elem.text.replace('帳號：', '').replace('帳號:', '').strip()
            
            # 名稱
            name_elem = item.find('div', {'class': 'cratedate'}, string=lambda x: x and '名稱' in x)
            if name_elem:
                data['名稱'] = name_elem.text.replace('名稱：', '').replace('名稱:', '').strip()
            
            # 狀態
            tag_elem = item.find('div', {'class': 'tag'})
            if tag_elem:
                txt_elem = tag_elem.find('div', {'class': 'txt'})
                if txt_elem:
                    data['狀態'] = txt_elem.text.strip()
            
            # 提取所有數據面板
            panels = item.find_all('div', {'class': 'panelBox'})
            
            for panel in panels:
                # 取得標題
                title_elem = panel.find('div', {'class': lambda x: x and 'item-data-feild-title' in x})
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                # 取得數值
                value_elem = panel.find('div', {'class': 'item-data-des'})
                if value_elem:
                    # 處理數值,包含整數和小數部分
                    value_span = value_elem.find('span', recursive=False)
                    if value_span:
                        # 找到所有直接子 span
                        inner_spans = value_span.find_all('span', recursive=False)
                        if len(inner_spans) >= 2:
                            # 有整數和小數部分
                            integer_part = inner_spans[0].text.strip()
                            decimal_part = inner_spans[1].text.strip()
                            # 移除逗號
                            integer_part = integer_part.replace(',', '')
                            # 組合完整數值
                            value = integer_part + decimal_part
                        else:
                            # 只有一個值
                            value = value_span.text.strip().replace(',', '')
                    else:
                        # 沒有 span 標籤,直接取文字
                        value = value_elem.text.strip().replace(',', '')
                    
                    data[title] = value
            
            if data:
                results.append(data)
                
        except Exception as e:
            print(f"⚠ 解析項目時發生錯誤: {e}")
            continue
    
    return results

def save_results_to_csv(all_results):
    """
    將所有結果儲存到單一 CSV 檔案並放在桌面
    """
    # 取得桌面路徑
    desktop_path = Path.home() / "Desktop"
    
    # 產生檔案名稱
    filename = "代理管理.csv"
    filepath = desktop_path / filename
    
    # 將結果轉換為 DataFrame
    df = pd.DataFrame(all_results)
    
    # 調整欄位順序(如果欄位存在)
    column_order = [
        '帳號', '名稱', '狀態',
        '注單筆數', '下注金額', '有效投注',
        '玩家輸贏', '玩家退水', '玩家盈虧',
        '應收下線'
    ]
    
    # 只保留存在的欄位
    existing_columns = [col for col in column_order if col in df.columns]
    
    df = df[existing_columns]
    
    # 儲存為 CSV (使用 UTF-8 BOM 編碼,確保 Excel 正確顯示中文)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    print(f"✅ CSV 已儲存至桌面: {filepath}")
    return str(filepath)

# ============================
# 主程式
# ============================
def main():
    user_list = read_all_user_info()
    all_results = []  # 儲存所有帳號的結果

    for index, (acc, pwd) in enumerate(user_list, start=1):
        print("\n============================")
        print(f"▶ 處理第 {index} 組帳號：{acc}")
        print("============================")

        driver = create_driver()
        driver.get(LOGIN_URL)

        input_account_password(driver, acc, pwd)
        time.sleep(1)
        click_login_button(driver)
        time.sleep(5)

        driver.get(PERSONAL_URL)
        time.sleep(5)

        click_radio_by_value(driver, "lastweek")
        time.sleep(2)
        click_search_button(driver)
        
        # 等待查詢結果載入
        print("⏳ 等待查詢結果載入...")
        time.sleep(5)
        
        # 解析報表資料
        print("📊 開始解析報表資料...")
        results = parse_agent_report(driver)
        
        if results:
            print(f"✅ 成功解析 {len(results)} 筆資料")
            
            # 將結果加入總列表
            all_results.extend(results)
            
            # 顯示摘要
            print("\n📋 資料摘要:")
            for idx, data in enumerate(results[:3], 1):  # 只顯示前3筆
                print(f"  {idx}. {data.get('帳號', 'N/A')} - {data.get('名稱', 'N/A')}")
                if '玩家輸贏' in data:
                    print(f"     玩家輸贏: {data['玩家輸贏']}")
            
            if len(results) > 3:
                print(f"  ... 還有 {len(results) - 3} 筆資料")
        else:
            print("⚠ 未找到任何資料")
        
        driver.quit()
        print(f"✅ 帳號 {acc} 處理完成")

    # 所有帳號處理完成後,統一儲存到一個 CSV
    if all_results:
        print("\n💾 正在儲存所有資料...")
        save_results_to_csv(all_results)
        print(f"📊 總共儲存 {len(all_results)} 筆資料")
    else:
        print("\n⚠ 沒有任何資料可儲存")

    print("\n🎉 所有帳號流程已完成！")

if __name__ == "__main__":
    main()
