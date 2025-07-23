
import argparse
import random
import time
from selenium.webdriver.common.by import By

from browser_automation import BrowserManager, Node
from utils import Utility

PROJECT_URL = "chrome-extension://andhndehpcjpmneneealacgnmealilal"

class Setup:
    def __init__(self, node: Node, profile) -> None:
        self.node = node
        self.profile = profile
        
    def _run(self):
        self.node.new_tab(f'{PROJECT_URL}/home.html', method="get")
        Utility.wait_time(10)

class Auto:
    def __init__(self, node: Node, profile: dict) -> None:
        self.driver = node._driver
        self.node = node
        self.profile_name = profile.get('profile_name')
        self.pin = profile.get('pin')
        self.wallet = profile.get('wallet')
        self.recieve_addresses = profile.get('recieve_addresses')

    def unlock(self):
        btns = self.node.find_all(By.TAG_NAME, 'button')
        for btn in btns:
            if 'I HAVE AN ACCOUNT'.lower() in btn.text.lower():
                self.node.log(f'Cần import Haha wallet')
                return
            
            elif 'Unlock'.lower() in btn.text.lower():
                self.node.log(f'Cần unlock wallet')
                self.node.find_and_input(By.TAG_NAME, 'input', self.pin)
                self.node.find_and_click(By.XPATH, '//button[contains(text(), "Unlock")]')
                p_els = self.node.find_all(By.TAG_NAME, 'p')
                for p in p_els:
                    if 'Incorrect Pin Code'.lower() in p.text.lower():
                        self.node.log(f'Sai mã pin')
                        return
                return self.unlock()

            elif '0x' in btn.text.lower():
                self.node.log(f'Đã đăng nhập')
                return True

    def check_in(self):
        div_els = self.node.find_all(By.TAG_NAME, 'div')
        check_in = None
        for div in div_els:
            if 'Click here to claim your daily karma'.lower() in div.text.lower():
                check_in = div
                self.node.go_to(f'{PROJECT_URL}/home.html#quests', 'get')
                break

        if check_in:
            btns = self.node.find_all(By.TAG_NAME, 'button')
            for btn in btns:
                if 'Claim'.lower() in btn.text.lower():
                    claim = btn
                    self.node.click(claim)
                    break
            
            div_els = self.node.find_all(By.TAG_NAME, 'div')
            for div in div_els:
                if 'Come back tomorrow after midnight UTC for more karma'.lower() in div.text.lower():
                    return True
            
        return False

    def change_chain(self):
        chain = self.node.find(By.CSS_SELECTOR, '[class="text-nowrap mr-2"]')

        if chain and chain.text.lower() == 'Sepolia'.lower():
            self.node.log(f'Đang chain Sepolia')
            return True
        else:
            self.node.click(chain)
            btns = self.node.find_all(By.TAG_NAME, 'button')
            for btn in btns:
                if 'Sepolia (ETH)'.lower() in btn.text.lower():
                    if self.node.click(btn):
                        return self.change_chain()

        return False

    def send_eth(self):
        for attempt in range(2):
            self.node.go_to(f'{PROJECT_URL}/home.html', 'get')
            self.node.find(By.XPATH,'//html[contains(@class, "haha-loaded")]')

            if not self.change_chain():
                return False
            
            self.node.find_and_click(By.XPATH, '//p[contains(text(), "Legacy Wallet")]')
            self.node.find_and_click(By.XPATH, '//button[p[contains(text(), "Send")]]')
            btn_eth = self.node.find(By.XPATH, '//button[.//p[text()="ETH"]]')
            if not btn_eth:
                return False

            value_eth = self.node.get_text(By.XPATH, './div[last()]', btn_eth)
            if value_eth:
                try:
                    value_eth = float(value_eth)
                except Exception as e:
                    value_eth = None
            if value_eth and value_eth < 0.005:
                self.node.snapshot(f'Không đủ Eth để thực hiện tx (min 0.005)', False)
                return False

            self.node.click(btn_eth)
            
            select_address = random.choice(self.recieve_addresses)
            if select_address:
                self.node.find_and_input(By.TAG_NAME, 'input', select_address, delay=0)
                self.node.find_and_click(By.XPATH, '//button[not(@disabled) and contains(text(), "Continue")]')
            else:
                btns = self.node.find_all(By.TAG_NAME, 'button')
                for btn in btns:
                    if '(Legacy Wallet)'.lower() in btn.text.lower():
                        self.node.click(btn)
                        break
            value = round(random.uniform(0.0001, 0.0010), 5)
            value_str = f"{value:.5f}"
            self.node.find_and_input(By.TAG_NAME, 'input', value_str)
            if not self.node.find_and_click(By.XPATH, '//button[not(@disabled) and contains(text(), "Next")]'):
                if self.node.find(By.XPATH, '//p[contains(text(),"Insufficient funds")]'):
                    self.node.snapshot(f'Không đủ Insufficient funds', False)
                return False

            if self.node.find_and_click(By.XPATH, '//button[not(@disabled) and contains(text(), "Confirm")]'):
                return True
            else:
                self.node.log(f'Thử lại lần 2')

    def _run(self):
        completed = []
        self.node.new_tab(f'{PROJECT_URL}/home.html', method="get")
        self.node.find(By.TAG_NAME, 'title')
        if not self.unlock():
            self.node.snapshot(f'Unlock wallet không thành công')

        if self.check_in():
            completed.append('checked-in')

        times = 0
        while times < 10:
            if self.send_eth():
                times += 1
            else:
                break
        completed.append(f'Send_ETH: {times}')

        self.node.snapshot(f'Hoàn thành: {completed} ')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true', help="Chạy ở chế độ tự động")
    parser.add_argument('--headless', action='store_true', help="Chạy trình duyệt ẩn")
    parser.add_argument('--disable-gpu', action='store_true', help="Tắt GPU")
    args = parser.parse_args()

    profiles = Utility.read_data('profile_name', 'pin', 'wallet')
    for profile in profiles:
        profile['recieve_addresses'] = [p['wallet'] for p in profiles]
    if not profiles:
        print("Không có dữ liệu để chạy")
        exit()

    browser_manager = BrowserManager(AutoHandlerClass=Auto, SetupHandlerClass=Setup)
    browser_manager.config_extension('HaHa-Wallet-Chrome-Web-Store.crx')
    browser_manager.run_terminal(
        profiles=profiles,
        max_concurrent_profiles=4,
        block_media=True,
        auto=args.auto,
        headless=args.headless,
        disable_gpu=args.disable_gpu,
    )