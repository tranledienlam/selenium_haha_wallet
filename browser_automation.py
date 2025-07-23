import sys
import glob
import time
import shutil
import re
from pathlib import Path
from math import ceil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import cast

from screeninfo import get_monitors
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.window import WindowTypes
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException, ElementNotVisibleException, NoSuchWindowException, WebDriverException

from utils import Utility, Chromium, TeleHelper, AIHelper

DIR_PATH = Path(__file__).parent

class Node:
    def __init__(self, driver: webdriver.Chrome, profile_name: str, tele_bot: TeleHelper|None = None, ai_bot: AIHelper|None = None) -> None:
        '''
        Khởi tạo một đối tượng Node để quản lý và thực hiện các tác vụ tự động hóa trình duyệt.

        Args:
            driver (webdriver.Chrome): WebDriver điều khiển trình duyệt Chrome.
            profile_name (str): Tên profile được sử dụng để khởi chạy trình duyệt
        '''
        self._driver = driver
        self.profile_name = profile_name
        self.tele_bot = tele_bot
        self.ai_bot = ai_bot
        # Khoảng thời gian đợi mặc định giữa các hành động (giây)
        self.wait = 3
        self.timeout = 30  # Thời gian chờ mặc định (giây) cho các thao tác
    
    def _get_wait(self, wait: float|None = None):
        if wait is None:
            wait = self.wait
        return wait
    
    def _get_timeout(self, timeout: float|None = None):
        if timeout is None:
            timeout = self.timeout
        return timeout
    
    def _save_screenshot(self) -> str|None:
        snapshot_dir = DIR_PATH / 'snapshot'
        screenshot_png = self.take_screenshot()
        
        if screenshot_png is None:
            return None
        
        if not snapshot_dir.exists():
            self.log(f'Không tin thấy thư mục {snapshot_dir}. Đang tạo...')
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self.log(f'Tạo thư mục Snapshot thành công')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = str(snapshot_dir/f'{self.profile_name}_{timestamp}.png')
        try:
            with open(file_path, 'wb') as f:
                f.write(screenshot_png)

        except Exception as e:
            self.log(f'❌ Không thể ghi file ảnh: {e}')
            return None
        
        self.log(f'✅ Ảnh đã được lưu tại Snapshot')
        return file_path

    def _send_screenshot_to_telegram(self, message: str):
        screenshot_png = self.take_screenshot()
        
        if screenshot_png is None:
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        message = f'[{timestamp}][{self.profile_name}] - {message}'
        if self.tele_bot and self.tele_bot.send_photo(screenshot_png, message):
            self.log(message=f"✅ Ảnh đã được gửi đến Telegram bot.")

    def _execute_node(self, node_action, *args):
        """
        Thực hiện một hành động node bất kỳ.
        Đây là function hỗ trợ thực thi node cho execute_chain

        Args:
            node_action: tên node
            *args: arg được truyền vào node
        """

        if not node_action(*args):
            return False
        return True

    def execute_chain(self, actions: list[tuple], message_error: str = 'Dừng thực thi chuỗi hành động'):
        """
        Thực hiện chuỗi các node hành động. 
        Dừng lại nếu một node thất bại.

        Args:
            actions (list[tuple]): Danh sách các tuple đại diện cho các hành động.
                Mỗi tuple có cấu trúc: 
                    (hàm_thực_thi, *tham_số_cho_hàm)
                Trong đó:
                    - `hàm_thực_thi` là một hàm được định nghĩa trong class, chịu trách nhiệm thực hiện hành động.
                    - `*tham_số_cho_hàm` là danh sách các tham số sẽ được truyền vào `hàm_thực_thi`.
                    - `stop_on_failure` (bool): Nếu False, không dừng chuỗi hành động dù hành động hiện tại thất bại. Mặc định là True

            message_error (str): Thông báo lỗi khi xảy ra thất bại trong chuỗi hành động. Nên là tên actions cụ thể của nó

        Returns:
            bool: 
                - `True` nếu tất cả các hành động đều được thực thi thành công.
                - `False` nếu có bất kỳ hành động nào thất bại.    

        Ví dụ: 
            actions = [
                (find, By.ID, 'onboarding__terms-checkbox', False), # Nếu lỗi vẫn tiếp tục
                (find_and_input, By.CSS_SELECTOR, 'button[data-testid="onboarding-import-wallet"]', False),
                (find_and_click, By.ID, 'metametrics-opt-in'),
                (find_and_click, By.CSS_SELECTOR, 'button[data-testid="metametrics-i-agree"]')
            ]

            self.execute_chain(actions, message_error="Lỗi trong quá trình thực hiện chuỗi hành động.")
        """
        for action in actions:
            stop_on_failure = True

            if isinstance(action, tuple):
                *action_args, stop_on_failure = action if isinstance(
                    action[-1], bool) else (*action, True)

                func = action_args[0]
                args = action_args[1:]

                if not callable(func):
                    self.log(f'Lỗi {func} phải là 1 function')
                    return False

            elif callable(action):
                func = action
                args = []

            else:
                self.log(
                    f"Lỗi - {action} phải là một function hoặc tuple chứa function.")
                return False

            if not self._execute_node(func, *args):
                self.log(
                    f'Lỗi {["skip "] if not stop_on_failure else ""}- {message_error}')
                if stop_on_failure:
                    return False

        return True

    def log(self, message: str = 'message chưa có mô tả', show_log: bool = True):
        '''
        Ghi và hiển thị thông báo nhật ký (log)

        Cấu trúc log hiển thị:
            [profile_name][func_thuc_thi]: {message}

        Args:
            message (str, optional): Nội dung thông báo log. Mặc định là 'message chưa có mô tả'.
            show_log (bool, optional): cho phép hiển thị nhật ký hay không. Mặc định: True (cho phép).

        Mô tả:
            - Phương thức sử dụng tiện ích `Utility.logger` để ghi lại thông tin nhật ký kèm theo tên hồ sơ (`profile_name`) của phiên làm việc hiện tại.
        '''
        Utility.logger(profile_name=self.profile_name,
                       message=message, show_log=show_log)
    
    def take_screenshot(self) -> bytes|None:
        """
        Chụp ảnh màn hình hiện tại của trình duyệt.

        Returns:
            bytes | None: Ảnh chụp màn hình ở dạng bytes PNG nếu thành công,
                        None nếu xảy ra lỗi.
        """
        try:
            return self._driver.get_screenshot_as_png()
        except Exception as e:
            self.log(f'❌ Không thể chụp ảnh màn hình: {e}')
            return None

    def snapshot(self, message: str = 'Mô tả lý do snapshot', stop: bool = True):
        '''
        Ghi lại trạng thái trình duyệt bằng hình ảnh và dừng thực thi chương trình.

        Args:
            message (str, optional): Thông điệp mô tả lý do dừng thực thi. Mặc định là 'Dừng thực thi.'. Nên gồm tên function chứa nó.
            stop (bool, optional): Nếu `True`, phương thức sẽ ném ra một ngoại lệ `ValueError`, dừng chương trình ngay lập tức.

        Mô tả:
            Phương thức này sẽ ghi lại thông điệp vào log và chụp ảnh màn hình trình duyệt.
            Nếu `stop=True`, phương thức sẽ quăng lỗi `ValueError`, dừng quá trình thực thi.
            Nếu `data_tele` tồn tại, ảnh chụp sẽ được gửi lên Telegram. Nếu không, ảnh sẽ được lưu cục bộ.
        '''
        self.log(message)
        if self.tele_bot and self.tele_bot.valid:
            self._send_screenshot_to_telegram(message)
        else:
            self._save_screenshot()

        if stop:
            raise ValueError(f'{message}')

    def new_tab(self, url: str|None = None, method: str = 'script', wait: float|None = None, timeout: float|None = None):
        '''
        Mở một tab mới trong trình duyệt và (tuỳ chọn) điều hướng đến URL cụ thể.

        Args:
            url (str, optional): URL đích cần điều hướng đến sau khi mở tab mới. Mặc định là `None`.
            method (str, optional): - Phương thức điều hướng URL. Mặc định: `script`
                - `'script'` → sử dụng JavaScript để thay đổi location.
                - `'get'` → sử dụng `driver.get(url)`.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác (tính bằng giây). Mặc định là giá trị của `self.wait`.
            timeout (float, optional): Thời gian chờ tối đa để trang tải hoàn tất (tính bằng giây). Mặc định là giá trị của `self.timeout = 20`.

        Returns:
            bool:
                - `True`: Nếu tab mới được mở và (nếu có URL) trang đã tải thành công.
                - `None`: Nếu chỉ mở tab mới mà không điều hướng đến URL.

        Raises:
            Exception: Nếu xảy ra lỗi trong quá trình mở tab mới hoặc điều hướng trang.

        Example:
            # Chỉ mở tab mới
            self.new_tab()

            # Mở tab mới và điều hướng đến Google
            self.new_tab(url="https://www.google.com")
        '''

        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        Utility.wait_time(wait)

        try:
            self._driver.switch_to.new_window(WindowTypes.TAB)

            if url:
                return self.go_to(url=url, method=method, wait=1, timeout=timeout)

        except Exception as e:
            self.log(f'Lỗi khi tải trang {url}: {e}')

        return False

    def go_to(self, url: str, method: str = 'script', wait: float|None = None, timeout: float|None = None):
        '''
        Điều hướng trình duyệt đến một URL cụ thể và chờ trang tải hoàn tất.

        Args:
            url (str): URL đích cần điều hướng đến.
            method (str, optional): - Phương thức điều hướng URL. Mặc định: `script`
                - `'script'` → sử dụng JavaScript để thay đổi location.
                - `'get'` → sử dụng `driver.get(url)`.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian chờ tải trang, mặc định là giá trị của `self.timeout = 20`.

        Returns:
            bool:
                - `True`: nếu trang tải thành công.
                - `False`: nếu có lỗi xảy ra trong quá trình tải trang.
        '''
        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        methods = ['script', 'get']
        Utility.wait_time(wait)
        if method not in methods:
            self.log(f'Gọi url sai phương thức. Chỉ gồm [{methods}]')
            return False
        try:
            if method == 'get':
                self._driver.get(url)
            elif method == 'script':
                self._driver.execute_script(f"window.location.href = '{url}';")

            WebDriverWait(self._driver, timeout).until(
                lambda driver: driver.execute_script(
                    "return document.readyState") == 'complete'
            )
            self.log(f'Trang {url} đã tải thành công.')
            return True

        except Exception as e:
            self.log(f'Lỗi - Khi tải trang "{url}": {e}')

            return False

    def wait_for_disappear(
        self,
        by: str,
        value: str,
        parent_element: WebElement|None = None,
        wait: float|None = None,
        timeout: float|None = None,
        show_log: bool = True
    ) -> bool:
        """
        Chờ cho đến khi phần tử (thường là loading spinner hoặc overlay) biến mất.

        Args:
            by (str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.
            show_log (bool, optional): Có log ra hay không.

        Returns:
            bool: 
                - True nếu phần tử biến mất (tức là hoàn tất loading).
                - False nếu hết timeout mà phần tử vẫn còn (coi như lỗi).
        """
        wait = self._get_wait(wait)
        timeout = timeout if timeout is not None else self.timeout

        Utility.wait_time(wait)
        search_context = parent_element if parent_element else self._driver

        start_time = time.time()
        wait_log = True
        try:
            while time.time() - start_time < timeout:
                try:
                    element = search_context.find_element(by, value)
                    if not element.is_displayed():
                        if show_log:
                            self.log(f"✅ Phần tử ({by}, {value}) đã biến mất.")
                        return True
                    else:
                        if show_log and wait_log:
                            wait_log = False
                            self.log(f'⏳ Đang chờ ({by}, {value}) biến mất.')
                except (StaleElementReferenceException, NoSuchElementException):
                    # Element không còn tồn tại trong DOM → coi là đã biến mất
                    if show_log:
                        self.log(f"✅ Phần tử ({by}, {value}) không còn trong DOM.")
                    return True

                Utility.wait_time(0.5)

            if show_log:
                self.log(f"⏰ Timeout - Phần tử ({by}, {value}) vẫn còn sau {timeout}s.")
            return False

        except Exception as e:
            self.log(f"❌ Lỗi khi chờ phần tử biến mất ({by}, {value}): {e}")
            return False
        
    def get_url(self, wait: float|None = None):
        '''
        Phương thức lấy url hiện tại

        Args:
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.

        Returns:
            Chuỗi str URL hiện tại
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait, True)
        return self._driver.current_url

    def find(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None, show_log: bool = True):
        '''
        Phương thức tìm một phần tử trên trang web trong khoảng thời gian chờ cụ thể.

        Args:
            by (By|str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa chờ phần tử xuất hiện (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            WebElement | bool:
                - WebElement: nếu tìm thấy phần tử.
                - `None`: nếu không tìm thấy hoặc xảy ra lỗi.
        '''
        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        Utility.wait_time(wait)
        try:
            search_context = parent_element if parent_element else self._driver
            element = WebDriverWait(search_context, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            self.log(message=f'Tìm thấy phần tử ({by}, {value})', show_log=show_log)
            return element

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - không xác định khi tìm phần tử ({by}, {value}) {e}')

        return None
    
    def find_all(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None, show_log: bool = True):
        '''
        Phương thức tìm tất cả các phần tử trên trang web trong khoảng thời gian chờ cụ thể.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa chờ phần tử xuất hiện (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            list[WebElement]: Danh sách các phần tử tìm thấy.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        try:
            search_context = parent_element if parent_element else self._driver
            elements = WebDriverWait(search_context, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )   
            self.log(message=f'Tìm thấy {len(elements)} phần tử ({by}, {value})', show_log=show_log)
            return elements

        except TimeoutException:
            self.log(f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:  
            self.log(f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(f'Lỗi - không xác định khi tìm phần tử ({by}, {value}) {e}')

        return []   
    
    def find_in_shadow(self, selectors: list[tuple[str, str]], wait: float|None = None, timeout: float|None = None):
        '''
        Tìm phần tử trong nhiều lớp shadow-root.

        Args:
            selectors (list[tuple[str, str]]): Danh sách selectors để truy cập shadow-root.
            wait (float, optional): Thời gian chờ giữa các bước.
            timeout (float, optional): Thời gian chờ tối đa khi tìm phần tử.

        Returns:
            WebElement | None: Trả về phần tử cuối cùng nếu tìm thấy, ngược lại trả về None.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        if not isinstance(selectors, list) or len(selectors) < 2:
            self.log("Lỗi - Selectors không hợp lệ (phải có ít nhất 2 phần tử).")
            return None

        try:
            if not isinstance(selectors[0], tuple) and len(selectors[0]) != 2:
                self.log(
                    f"Lỗi - Selector {selectors[0]} phải có ít nhất 2 phần tử (pt1,pt2)).")
                return None

            element = WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located(selectors[0])
            )

            for i in range(1, len(selectors)):
                if not isinstance(selectors[i], tuple) and len(selectors[i]) != 2:
                    self.log(
                        f"Lỗi - Selector {selectors[i]} phải có ít nhất 2 phần tử (pt1,pt2)).")
                    return None
                try:
                    shadow_root = self._driver.execute_script(
                        "return arguments[0].shadowRoot", element)
                    if not shadow_root:
                        self.log(
                            f"⚠️ Không tìm thấy shadowRoot của {selectors[i-1]}")
                        return None

                    element = cast(
                        WebElement, shadow_root.find_element(*selectors[i]))

                except NoSuchElementException:
                    self.log(f"Lỗi - Không tìm thấy phần tử: {selectors[i]}")
                    return None
                except Exception as e:
                    self.log(
                        f'Lỗi - không xác định khi tìm phần tử {selectors[1]} {e}')
                    return None

            self.log(f'Tìm thấy phần tử {selectors[-1]}')
            return element

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử {selectors[0]} trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử {selectors[0]} đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - không xác định khi tìm phần tử {selectors[0]} {e}')

        return None

    def see_by_text(self, text: str,  by: str = By.XPATH, parent_element: WebElement | None = None, wait: float | None = None, timeout: float | None = None, show_log: bool = True) -> list[WebElement]:
        '''
        Tìm tất cả phần tử chứa đoạn text cho trước, bất kể thẻ nào (div, p, span,...).

        Args:
            text (str): Nội dung cần tìm (sẽ tìm theo contains, không phân biệt tag).
            by (str): Kiểu định vị phần tử, mặc định là By.XPATH.
            parent_element (WebElement, optional): Nếu có, tìm trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi tìm.
            timeout (float, optional): Thời gian chờ tối đa để tìm phần tử.
            show_log (bool): Có hiển thị log hay không.

        Returns:
            list[WebElement]: Danh sách phần tử chứa đoạn text.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        # XPath để tìm phần tử chứa đoạn text
        value = f'.//*[contains(normalize-space(.), "{text}")]' if parent_element else f'//*[contains(normalize-space(.), "{text}")]'

        try:
            search_context = parent_element if parent_element else self._driver
            elements = WebDriverWait(search_context, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            self.log(message=f'🔍 Tìm thấy {len(elements)} phần tử chứa "{text}"', show_log=show_log)
            return elements

        except TimeoutException:
            self.log(f'❌ Không tìm thấy phần tử chứa "{text}" trong {timeout}s', show_log=show_log)
        except StaleElementReferenceException:
            self.log(f'⚠️ Phần tử chứa "{text}" đã bị thay đổi trong DOM', show_log=show_log)
        except Exception as e:
            self.log(f'❗ Lỗi khi tìm phần tử chứa "{text}": {e}', show_log=show_log)

        return []

    def click(self, element: WebElement|None = None, wait: float|None = None) -> bool:
        '''
            Nhấp vào một phần tử trên trang web.

    Args:
        value (WebElement): Phần tử cần nhấp.
        wait (float, optional): Thời gian chờ (giây) trước khi nhấp. Mặc định là `self.wait`.

    Returns:
        bool: 
            - `True`: nếu nhấp thành công.
            - `False`: nếu gặp lỗi.

    Ghi chú:
        - Gọi `.click()` trên phần tử sau khi chờ thời gian ngắn (nếu được chỉ định).
        - Ghi log kết quả thao tác hoặc lỗi gặp phải.
    '''
        wait = self._get_wait(wait)
        Utility.wait_time(wait)
        
        try:
            if element is None:
                self.log('❌ Không có phần tử để click (element is None)')
                return False
            element.click()
            self.log(f'Click phần tử thành công')
            return True

        except ElementClickInterceptedException:
                self.log('❌ Lỗi - Element bị chặn hoặc bị che, không thể nhấp được.')

        except ElementNotInteractableException:
            self.log('❌ Lỗi - Element không tương tác được (ẩn hoặc bị disable).')

        except StaleElementReferenceException:
            self.log('❌ Lỗi - Element không còn tồn tại hoặc DOM đã thay đổi.')

        except WebDriverException as e:
            self.log(f'❌ WebDriver lỗi khi click phần tử: {str(e)}')

        except Exception as e:
            self.log(f'❌ Lỗi không xác định khi click: {str(e)}')
    
        return False
    
    def find_and_click(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None) -> bool:
        '''
        Phương thức tìm và nhấp vào một phần tử trên trang web.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác nhấp. Mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử có thể nhấp được. Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            bool: 
                `True`: nếu nhấp vào phần tử thành công.
                `False`: nếu gặp lỗi.

        Mô tả:
            - Phương thức sẽ tìm phần tử theo phương thức `by` và `value`.
            - Sau khi tìm thấy phần tử, phương thức sẽ đợi cho đến khi phần tử có thể nhấp được (nếu cần).
            - Sau khi phần tử có thể nhấp, sẽ tiến hành nhấp vào phần tử đó.
            - Nếu gặp lỗi, sẽ ghi lại thông báo lỗi cụ thể.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout). until(
                EC.element_to_be_clickable((by, value))
            )

            Utility.wait_time(wait)
            element.click()
            self.log(f'Click phần tử ({by}, {value}) thành công')
            return True

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã thay đổi hoặc không còn hợp lệ')
        except ElementClickInterceptedException:
            self.log(
                f'Lỗi - Không thể nhấp vào phần tử phần tử ({by}, {value}) vì bị che khuất hoặc ngăn chặn')
        except ElementNotInteractableException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) không thể tương tác, có thể bị vô hiệu hóa hoặc ẩn')
        except Exception as e:
            # Thử phương pháp click khác khi bị lỗi từ Javascript
            if 'LavaMoat' in str(e):
                try:
                    element = WebDriverWait(search_context, timeout).until(
                        EC.presence_of_element_located((by, value))
                    )
                    Utility.wait_time(wait)
                    element.click()
                    self.log(f'Click phần tử ({by}, {value}) thành công (PT2)')
                    return True
                except ElementClickInterceptedException as e:
                    error_msg = e.msg.split("\n")[0] if e.msg else str(e)
                    self.log(
                        f'Lỗi - Không thể nhấp vào phần tử phần tử ({by}, {value}) vì bị che khuất hoặc ngăn chặn: {error_msg}')
                except Exception as e:
                    self.log(f'Lỗi - Không xác định ({by}, {value}) (PT2) {e}')
            else:
                self.log(f'Lỗi - Không xác định ({by}, {value}) {e}')

        return False

    def find_and_input(self, by: str, value: str, text: str, parent_element: WebElement|None = None, delay: float = 0.2, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức tìm và điền văn bản vào một phần tử trên trang web.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            text (str): Nội dung văn bản cần nhập vào phần tử.
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            delay (float): Thời gian trễ giữa mỗi ký tự khi nhập văn bản. Mặc định là 0.2 giây.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác nhấp. Mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử có thể nhấp được. Mặc định sử dụng giá trị self.timeout = 20.

        Returns:
            bool: 
                `True`: nếu nhập văn bản vào phần tử thành công.
                `False`: nếu gặp lỗi trong quá trình tìm hoặc nhập văn bản.

        Mô tả:
            - Phương thức sẽ tìm phần tử theo phương thức `by` và `value`.
            - Sau khi tìm thấy phần tử và đảm bảo phần tử có thể tương tác, phương thức sẽ thực hiện nhập văn bản `text` vào phần tử đó.
            - Văn bản sẽ được nhập từng ký tự một, với thời gian trễ giữa mỗi ký tự được xác định bởi tham số `delay`.
            - Nếu gặp lỗi, sẽ ghi lại thông báo lỗi cụ thể.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        if not text:
            self.log(f'Không có text để nhập vào input')
            return False
        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout).until(
                EC.visibility_of_element_located((by, value))
            )

            Utility.wait_time(wait)

            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            
            for char in text:
                Utility.wait_time(delay)
                element.send_keys(char)
            self.log(f'Nhập văn bản phần tử ({by}, {value}) thành công')
            return True

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except ElementNotVisibleException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) có trong DOM nhưng không nhìn thấy. ví dụ display: none hoặc visibility: hidden')
        except Exception as e:
            # Thử phương pháp click khác khi bị lỗi từ Javascript
            if 'LavaMoat' in str(e):
                element = WebDriverWait(search_context, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                Utility.wait_time(wait)

                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(Keys.DELETE)
                
                for char in text:
                    Utility.wait_time(delay)
                    element.send_keys(char)
                self.log(
                    f'Nhập văn bản phần tử ({by}, {value}) thành công (PT2)')
                return True
            else:
                self.log(f'Lỗi - không xác định ({by}, {value}) {e}')

        return False
    def press_key(self, key: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức nhấn phím trên trang web.

        Args:
            key (str): Phím cần nhấn (ví dụ: 'Enter', 'Tab', 'a', '1', etc.)
            parent_element (WebElement, optional): Phần tử cụ thể để nhấn phím. Mặc định là None (nhấn trên toàn trang).
            wait (float, optional): Thời gian chờ trước khi nhấn phím. Mặc định là self.wait.
            timeout (float, optional): Thời gian chờ tối đa. Mặc định là self.timeout.

        Returns:
            bool: True nếu nhấn phím thành công, False nếu có lỗi.

        Ví dụ:
            # Nhấn Enter trên toàn trang
            node.press_key('Enter')
            
            # Nhấn Tab trong một element cụ thể
            element = node.find(By.ID, 'search')
            node.press_key('Tab', parent_element=element)
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        
        try:
            Utility.wait_time(wait)
            
            # Lấy key từ class Keys nếu có
            key_to_press = getattr(Keys, key.upper(), key)
        
            if parent_element:
                # Nhấn phím trong element cụ thể
                if parent_element.is_displayed():
                    parent_element.send_keys(key_to_press)
                else:
                    self.log(f"⚠️ Element không hiển thị, không thể nhấn phím {key}")
                    return False
            else:
                # Nhấn phím trên toàn trang bằng ActionChains
                ActionChains(self._driver).send_keys(key_to_press).perform()
            
            self.log(f'Nhấn phím {key} thành công')
            return True
            
        except AttributeError:
            self.log(f'Lỗi - Phím {key} không hợp lệ')
        except Exception as e:
            self.log(f'Lỗi - Không thể nhấn phím {key}: {e}')
        
        return False

    def get_text(self, by, value, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức tìm và lấy văn bản từ một phần tử trên trang web.

        Args:
            by (By | str): Phương thức xác định cách tìm phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác lấy văn bản, mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử hiển thị, mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            str: Văn bản của phần tử nếu lấy thành công.
            `None`: Nếu không tìm thấy phần tử hoặc gặp lỗi.

        Mô tả:
            - Phương thức tìm phần tử trên trang web theo `by` và `value`.
            - Sau khi đảm bảo phần tử tồn tại, phương thức sẽ lấy văn bản từ phần tử và loại bỏ khoảng trắng thừa bằng phương thức `strip()`.
            - Nếu phần tử chứa văn bản, phương thức trả về văn bản đó và ghi log thông báo thành công.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            Utility.wait_time(wait)
            text = element.text.strip()

            if text:
                self.log(
                    f'Tìm thấy văn bản "{text}" trong phần tử ({by}, {value})')
                return text
            else:
                self.log(f'Lỗi - Phần tử ({by}, {value}) không chứa văn bản')

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - Không xác định khi tìm văn bản trong phần tử ({by}, {value})')

        return None

    def switch_tab(self, value: str, type: str = 'url', wait: float|None = None, timeout: float|None = None, show_log: bool = True) -> bool:
        '''
        Chuyển đổi tab dựa trên tiêu đề hoặc URL.

        Args:
            value (str): Giá trị cần tìm kiếm (URL hoặc tiêu đề).
            type (str, optional): 'title' hoặc 'url' để xác định cách tìm kiếm tab. Mặc định là 'url'
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.
            timeout (float, optional): Tổng thời gian tối đa để tìm kiếm.
            show_log (bool, optional): Hiển thị nhật ký ra bênngoài. Mặc định là True

        Returns:
            bool: True nếu tìm thấy và chuyển đổi thành công, False nếu không.
        '''
        types = ['title', 'url']
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        found = False

        if type not in types:
            self.log('Lỗi - Tìm không thành công. {type} phải thuộc {types}')
            return found
        Utility.wait_time(wait)
        try:
            current_handle = self._driver.current_window_handle
            current_title = self._driver.title
            current_url = self._driver.current_url
        except Exception as e:
            # Tab hiện tịa đã đóng, chuyển đến tab đầu tiên
            try:
                current_handle = self._driver.window_handles[0]
            except Exception as e:
                self.log(f'Lỗi không xác đinh: current_handle {e}')

        try:
            end_time = time.time() + timeout
            while time.time() < end_time:
                for handle in self._driver.window_handles:
                    self._driver.switch_to.window(handle)

                    if type == 'title':
                        find_window = self._driver.title.lower()
                        match_found = (find_window == value.lower())
                    elif type == 'url':
                        find_window = self._driver.current_url.lower()
                        match_found = find_window.startswith(value.lower())

                    if match_found:
                        found = True
                        self.log(
                            message=f'Đã chuyển sang tab: {self._driver.title} ({self._driver.current_url})',
                            show_log=show_log
                        )
                        return found

                Utility.wait_time(2)

            # Không tìm thấy → Quay lại tab cũ
            self._driver.switch_to.window(current_handle)
            self.log(
                message=f'Lỗi - Không tìm thấy tab có [{type}: {value}] sau {timeout}s.',
                show_log=show_log
            )
        except NoSuchWindowException as e:
            self.log(
                message=f'Tab hiện tại đã đóng: {current_title} ({current_url})',
                show_log=show_log
            )
        except Exception as e:
            self.log(message=f'Lỗi - Không xác định: {e}', show_log=show_log)

        return found

    def reload_tab(self, wait: float|None = None):
        '''
        Làm mới tab hiện tại

        Args:
            wait (float, optional): Thời gian chờ trước khi thực hiện reload, mặc định sử dụng giá trị `self.wait = 3`.
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait)
        try:
            self._driver.refresh()
        except:
            self._driver.execute_script("window.location.reload();")
        
        self.log('Tab đã reload')


    def close_tab(self, value: str|None = None, type: str = 'url', wait: float|None = None, timeout: float|None = None) -> bool:
        '''
        Đóng tab hiện tại hoặc tab cụ thể dựa trên tiêu đề hoặc URL.

        Args:
            value (str, optional): Giá trị cần tìm kiếm (URL hoặc tiêu đề).
            type (str, optional): 'title' hoặc 'url' để xác định cách tìm kiếm tab. Mặc định: 'url'
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.
            timeout (float, optional): Tổng thời gian tối đa để tìm kiếm.

        Returns:
            bool: True nếu đóng tab thành công, False nếu không.
        '''

        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        current_handle = self._driver.current_window_handle
        all_handles = self._driver.window_handles

        Utility.wait_time(wait)
        # Nếu chỉ có 1 tab, không thể đóng
        if len(all_handles) < 2:
            self.log(f'❌ Chỉ có 1 tab duy nhất, không thể đóng')
            return False

        # Nếu không nhập `value`, đóng tab hiện tại & chuyển về tab trước
        if not value:
            Utility.wait_time(wait)

            self.log(
                f'Đóng tab: {self._driver.title} ({self._driver.current_url})')
            self._driver.close()

            previous_index = all_handles.index(current_handle) - 1
            self._driver.switch_to.window(all_handles[previous_index])
            return True

        # Nếu có `value`, tìm tab theo tiêu đề hoặc URL
        if self.switch_tab(value=value, type=type, show_log=False):
            found_handle = self._driver.current_window_handle

            self.log(
                f'Đóng tab: {self._driver.title} ({self._driver.current_url})')
            self._driver.close()

            if current_handle == found_handle:
                previous_index = all_handles.index(current_handle) - 1
                self._driver.switch_to.window(all_handles[previous_index])
            else:
                self._driver.switch_to.window(current_handle)

            return True

        self.log(f"❌ Không tìm thấy tab có {type}: {value}.")
        return False
    
    def scroll_to(self, element: WebElement, wait: float|None = None):
        '''
        Phương thức cuộn đến phần tử cụ thể được chỉ định.

        Args:
            element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.

        Returns:
            bool: True, cuộn thành công. False khi gặp lỗi
            
        Mô tả:
            Phương thức sẽ nhận vào 1 element cụ thể, sau đó dùng driver.execute_script() để thực thi script
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait)
        try:
            self._driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.log(f'Cuộn thành công')
            return True
        
        except NoSuchWindowException:
            self.log(f'Không thể cuộn. Cửa sổ đã đóng')
        except Exception as e:
            self.log(f'Lỗi - không xác định khi cuộn: {e}')
            
        return False
    
    def ask_ai(self, prompt: str, is_image: bool = True, wait: float|None = None) -> str|None:
        '''
        Gửi prompt và hình ảnh (nếu có) đến AI để phân tích và nhận kết quả.

        Args:
            prompt (str): Câu hỏi hoặc yêu cầu gửi đến AI
            is_image (bool, optional):  Nếu True, sẽ chụp ảnh màn hình hiện tại và gửi kèm. 
                                        Nếu False, chỉ gửi prompt không kèm ảnh.
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.

        Returns:
            str: Kết quả phân tích từ AI. Trả về None nếu có lỗi xảy ra.
        '''
        wait = self._get_wait(wait)

        if not self.ai_bot or not self.ai_bot.valid:
            self.log(f'AI bot không hoạt động')
            return None
        
        self.log(f'AI đang suy nghĩ...')
        Utility.wait_time(wait)

        result, error = None, None
        if is_image:
            try:
                img_bytes = self._driver.get_screenshot_as_png()
                result, error = self.ai_bot.ask(prompt, img_bytes)
            except Exception as e:
                error = f'Không thể chụp hình ảnh gửi đến AI bot'
        else:   
            result, error =  self.ai_bot.ask(prompt)
        
        if error:
            self.log(message=f'{error}')
            return None
        
        if result:
            self.log(f'AI đã trả lời: "{result[:10]}{"..." if len(result) > 10 else ''}"')

        return result
        
    def check_window_handles(self):
        Utility.wait_time(5, True)
        original_handle = self._driver.current_window_handle
        window_handles = self._driver.window_handles

        print("Danh sách các cửa sổ/tab đang hoạt động:", window_handles)
        # handle là ID, ví dụ có 2 page ['433E0A85799F602DFA5CE74CA1D00682', '2A6FD93FC931056CCF842DF11782C45B']
        for handle in self._driver.window_handles:
            self._driver.switch_to.window(handle)
            print(f'{self._driver.title} - {self._driver.current_url}')

        self._driver.switch_to.window(original_handle)
        print(f'Hiện đang ở {self._driver.title}')

class BrowserManager:                                                                                                                                                                              # Anh em cứ yên tâm chạy nhé, không có mã độc đâu! :D Chỉ giả vờ đánh lừa người ngoài chút thôi! 🚀
    def __init__(self, AutoHandlerClass=None, SetupHandlerClass=None) -> None:
        '''
        Khởi tạo đối tượng BrowserManager để quản lý trình duyệt.

        Tham số:
        - AutoHandlerClass (class, optional): Lớp xử lý tự động các tác vụ trên trình duyệt.
        - SetupHandlerClass (class, optional): Lớp xử lý thiết lập môi trường trình duyệt.

        Chức năng:
        - Cho phép tùy chỉnh cách quản lý trình duyệt bằng cách truyền vào các lớp xử lý tương ứng.
        - Có thể được sử dụng để tự động hóa thao tác trình duyệt hoặc thiết lập cấu hình khi khởi chạy.

        Ví dụ sử dụng:
        ```python
        browser_manager = BrowserManager(AutoHandlerClass=Auto, SetupHandlerClass=Setup)
        ```
        '''
        self.AutoHandlerClass = AutoHandlerClass
        self.SetupHandlerClass = SetupHandlerClass

        self.headless = False
        self.disable_gpu = False
        self.user_data_dir = self._get_user_data_dir()
        self.path_chromium = Chromium().path
        self.tele_bot = TeleHelper()
        self.ai_bot = AIHelper()
        self.matrix: list[list[str | None]] = [[None]]
        self.extensions = []

        # lấy kích thước màn hình
        monitors = get_monitors()
        if len(monitors) > 1:
            select_monitor = monitors[1]
        else:
            select_monitor = monitors[0]
        self.screen_width = select_monitor.width
        self.screen_height = select_monitor.height
        self.screen_x = select_monitor.x
        self.screen_y = select_monitor.y

    def _log(self, profile_name: str = 'SYS', message: str = 'message chưa có mô tả'):
        '''
        Ghi và hiển thị thông báo nhật ký (log)

        Cấu trúc log hiển thị:
            [profile_name][func_thuc_thi]: {message}

        Args:
            profile_name (str): tên hồ sơ hiện tại
            message (str, optional): Nội dung thông báo log. Mặc định là 'message chưa có mô tả'.

        Mô tả:
            - Phương thức sử dụng tiện ích `Utility.logger` để ghi lại thông tin nhật ký kèm theo tên hồ sơ (`profile_name`) của phiên làm việc hiện tại.
        '''
        Utility.logger(profile_name, message)

    def _get_user_data_dir(self):
        dir_path = Utility.read_config('USER_DATA_DIR')
        if dir_path and Path(dir_path[0]).exists():
            return Path(dir_path[0])/'user_data'
        else:
            return DIR_PATH/'user_data'
            
    def _get_matrix(self, number_profiles: int, max_concurrent_profiles: int):
        """
        Phương thức tạo ma trận vị trí cho các trình duyệt dựa trên số lượng hồ sơ và luồng song song tối đa.

        Args:
            number_profiles (int): Tổng số lượng hồ sơ cần chạy.
            max_concurrent_profiles (int): Số lượng hồ sơ chạy đồng thời tối đa.

        Hoạt động:
            - Nếu chỉ có 1 hồ sơ chạy, tạo ma trận 1x1.
            - Tự động điều chỉnh số hàng và cột dựa trên số lượng hồ sơ thực tế và giới hạn luồng song song.
            - Đảm bảo ma trận không dư thừa hàng/cột khi số lượng hồ sơ nhỏ hơn giới hạn song song.
        """
        # Số lượng hàng dựa trên giới hạn song song
        rows = 1 if (max_concurrent_profiles == 1 or number_profiles == 1) else 2

        # Tính toán số cột cần thiết
        if number_profiles <= max_concurrent_profiles:
            # Dựa trên số lượng hồ sơ thực tế
            cols = ceil(number_profiles / rows)
        else:
            # Dựa trên giới hạn song song
            cols = ceil(max_concurrent_profiles / rows)
        
        # Tạo ma trận với số hàng và cột đã xác định
        self.matrix = [[None for _ in range(cols)] for _ in range(rows)]

    def _arrange_window(self, driver, row, col):
        cols = len(self.matrix[0])
        y = row * self.screen_height

        if cols > 1 and (cols * self.screen_width) > self.screen_width*2:
            x = col * (self.screen_width // (cols-1))
        else:
            x = col * self.screen_width
        driver.set_window_rect(x, y, self.screen_width, self.screen_height)

    def _get_position(self, profile_name: str):
        """
        Gán profile vào một ô trống và trả về tọa độ (x, y).
        """
        for row in range(len(self.matrix)):
            for col in range(len(self.matrix[0])):
                if self.matrix[row][col] is None:
                    self.matrix[row][col] = profile_name
                    return row, col
        return None, None

    def _release_position(self, profile_name: int, row, col):
        """
        Giải phóng ô khi profile kết thúc.
        """
        for row in range(len(self.matrix)):
            for col in range(len(self.matrix[0])):
                if self.matrix[row][col] == profile_name:
                    self.matrix[row][col] = None
                    return True
        return False
        
    def _browser(self, profile_name: str, proxy_info: str|None = None, block_media: bool = False) -> webdriver.Chrome:
        '''
        Phương thức khởi tạo trình duyệt Chrome (browser) với các cấu hình cụ thể, tự động khởi chạy khi gọi `BrowserManager.run_browser()`.

        Args:
            profile_name (str): tên hồ sơ. Được tự động thêm vào khi chạy phương thức `BrowserManager.run_browser()`

        Returns:
            driver (webdriver.Chrome): Đối tượng trình duyệt được khởi tạo.

        Mô tả:
            - Dựa trên thông tin hồ sơ (`profile_data`), hàm sẽ thiết lập và khởi tạo trình duyệt Chrome với các tùy chọn cấu hình sau:
                - Chạy browser với dữ liệu người dùng (`--user-data-dir`).
                - Tùy chọn tỉ lệ hiển thị trình duyệt (`--force-device-scale-factor`)
                - Tắt các thông báo tự động và hạn chế các tính năng tự động hóa của trình duyệt.
                - Vô hiệu hóa dịch tự động của Chrome.
                - Vô hiệu hóa tính năng lưu mật khẩu (chỉ áp dụng khi sử dụng hồ sơ mặc định).
            - Các tiện ích mở rộng (extensions) được thêm vào trình duyệt (Nếu có).       
        '''
        rows = len(self.matrix)
        scale = 1 if (rows == 1) else 0.5

        chrome_options = ChromeOptions()

        if self.path_chromium:
            chrome_options.binary_location = str(self.path_chromium)
        chrome_options.add_argument(
            f'--user-data-dir={self.user_data_dir}/{profile_name}')
        # chrome_options.add_argument(f'--profile-directory={profile_name}') # tắt để sử dụng profile default trong profile_name
        chrome_options.add_argument('--lang=en')
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument(f"--force-device-scale-factor={scale}")
        chrome_options.add_argument(
            '--disable-blink-features=AutomationControlled') # để có thể đăng nhập google
        # Tắt dòng thông báo auto
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # chrome_options.add_experimental_option('enableExtensionTargets', True)
        # Ngăn Chrome tự động khôi phục session
        # chrome_options.add_argument("--disable-features=InfiniteSessionRestore,SessionService,TabDiscarding")
        # chrome_options.add_argument("--disable-session-crashed-bubble") 
        # vô hiệu hóa save mật khẩu
        prefs = {
        #     "profile.default_content_setting_values.notifications": 2,
        #     "credentials_enable_service": False,
        #     "profile.password_manager_enabled": False,
            "profile.managed_default_content_settings.images": 1,
            "profile.managed_default_content_settings.video": 1,
        #     # Tắt gợi ý đăng nhập Chrome
        #     "signin.allowed": False,
        #     "sync_disable": True,
        #     "signout.allowed": True,
        #     "enable_sync": False,
        #     "signin.allowed_on_next_startup": False,
        #     "credentials_enable_autosignin": False
        }
        # block image và video để tăng hiệu suất, nhưng cần tắt khi có cloudflare
        if block_media:
            prefs.update({
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.video": 2
            })
            
        chrome_options.add_experimental_option("prefs", prefs) # chỉ dùng được khi dùng profile default (tắt --profile-directory={profile_name})

        # hiệu suất
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")  # Tránh lỗi memory
        if self.disable_gpu:
            chrome_options.add_argument("--disable-gpu")  # Tắt GPU, dành cho máy không có GPU vật lý
        if self.headless:
            chrome_options.add_argument("--headless=new") # ẩn UI khi đang chạy
        
        # add extensions
        for ext in self.extensions:
            chrome_options.add_extension(ext)

        service = Service(log_path='NUL')
	  
        # # run proxy
        use_proxy = None
        path_lock = self.user_data_dir / f'''{re.sub(r'[^a-zA-Z0-9_\-]', '_', profile_name)}.lock'''
        if proxy_info:
            self._log(profile_name, 'Kiểm tra proxy')
            use_proxy = Utility.is_proxy_working(proxy_info)
        self._log(profile_name, 'Đang mở Chrome...')
        if use_proxy:
            try:
                from seleniumwire import webdriver
                seleniumwire_options = {
                'verify_ssl': True,  # ✅ False Bỏ qua xác thực SSL
                'proxy': {
                    'http': f'http://{proxy_info}',
                    'https': f'https://{proxy_info}'
                }
            }
                # Khóa profile
                Utility.lock_profile(path_lock)
                driver = webdriver.Chrome(service=service, options=chrome_options, seleniumwire_options=seleniumwire_options)
            except Exception as e:
                # Giải phóng profile nếu có lỗi
                Utility.unlock_profile(path_lock)
                self._log(profile_name, f'Lỗi khi sử dụng proxy: {e}')
                exit()
        else:
            try:
                from selenium import webdriver
                Utility.lock_profile(path_lock)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                # Giải phóng profile nếu có lỗi
                Utility.unlock_profile(path_lock)
                self._log(profile_name, f'Lỗi khi không sử dụng proxy: {e}')
                exit()
        return driver

    def config_extension(self, *args: str):
        '''
        Cấu hình trình duyệt với các tiện ích mở rộng (extensions).

        Args:
            *args (str): Danh sách tên tệp các tiện ích mở rộng (ví dụ: 'ext1.crx', 'ext2.crx').

        Mô tả:
            - Phương thức sẽ kiểm tra sự tồn tại của thư mục extensions và từng tệp tiện ích mở rộng được cung cấp trong tham số `args`.
            - Đường dẫn của các tiện ích mở rộng sẽ được xác định dựa trên thư mục `extensions` nằm cùng cấp với tệp hiện tại (`__file__`).
            - Nếu bất kỳ tệp tiện ích mở rộng nào không tồn tại, phương thức sẽ thông báo lỗi và dừng chương trình.
            - Nếu tất cả các tệp tồn tại, chúng sẽ được thêm vào danh sách `self.extensions` để sử dụng trước khi khởi chạy trình duyệt.

        Ví dụ:
            config_extension('ext1.crx', 'ext2.crx')
        '''
        extensions_path = DIR_PATH / 'extensions'
        
        if not extensions_path.exists():
            return

        for arg in args:
            # Nếu có ký tự '*' trong tên, thực hiện tìm kiếm
            ext_path = extensions_path / arg
            if '*' in arg:
                matched_files = glob.glob(str(ext_path))
                if matched_files:
                    ext_path = max(matched_files, key=lambda f: Path(
                        f).stat().st_ctime)  # Chọn file mới nhất
                else:
                    self._log(message=
                        f'Lỗi: {ext_path} không tồn tại. Dừng chương trình')
                    exit()
            else:
                if not ext_path.exists():
                    self._log(
                        f'Lỗi: {ext_path} không tồn tại. Dừng chương trình')
                    exit()

            self.extensions.append(ext_path)

    def _listen_for_enter(self, profile_name: str):
        """Lắng nghe sự kiện Enter để dừng trình duyệt"""
        if sys.stdin.isatty():  # Kiểm tra nếu có stdin hợp lệ
            input(f"[{profile_name}] Nhấn ENTER để đóng trình duyệt...")
        else:
            self._log(
                f"⚠ Không thể sử dụng input() trong môi trường này. Đóng tự động sau 10 giây.")
            Utility.wait_time(10)

    def run_browser(self, profile: dict, row: int = 0, col: int = 0, block_media: bool = False, stop_flag: bool = False):
        '''
        Phương thức khởi chạy trình duyệt (browser).

        Args:
            profile (dict): Thông tin cấu hình hồ sơ trình duyệt
                - profile_name (str): Tên hồ sơ trình duyệt.
            row (int, optional): Vị trí hàng để sắp xếp cửa sổ trình duyệt. Mặc định là 0.
            col (int, optional): Vị trí cột để sắp xếp cửa sổ trình duyệt. Mặc định là 0.
            block_media (bool, optional): True, block image và video để tăng hiệu suất, nhưng cần False khi có cloudflare. Mặc định `False`.
            stop_flag (multiprocessing.Value, optional): Cờ tín hiệu để dừng trình duyệt. 
                - Nếu `stop_flag` là `True`, trình duyệt sẽ duy trì trạng thái trước khi enter.
                - Nếu là `None|False`, trình duyệt sẽ tự động đóng sau khi chạy xong.

        Mô tả:
            - Hàm khởi chạy trình duyệt dựa trên thông tin hồ sơ (`profile`) được cung cấp.
            - Sử dụng phương thức `_browser` để khởi tạo đối tượng trình duyệt (`driver`).
            - Gọi phương thức `_arrange_window` để sắp xếp vị trí cửa sổ trình duyệt theo `row` và `col`.
            - Nếu `AutoHandlerClass` và `SetupHandlerClass` được chỉ định, phương thức `_run` của lớp này sẽ được gọi để xử lý thêm logic.
            - Nêu `stop_flag` được cung cấp, trình duyệt sẽ duy trì hoạt động cho đến khi nhấn enter.
            - Sau cùng, - Đóng trình duyệt và giải phóng vị trí đã chiếm dụng bằng `_release_position`.

        Lưu ý:
            - Phương thức này có thể chạy độc lập hoặc được gọi bên trong `BrowserManager.run_multi()` và `BrowserManager.run_stop()`.
            - Đảm bảo rằng `AutoHandlerClass` (nếu có) được định nghĩa với phương thức `run_browser()`.
        '''
        profile_name = profile['profile_name']
        proxy_info = profile.get('proxy_info')
        path_lock = self.user_data_dir / f'''{re.sub(r'[^a-zA-Z0-9_\-]', '_', profile_name)}.lock'''
        
        # Chờ profile được giải phóng nếu đang bị khóa
        try:
            Utility.wait_until_profile_free(profile_name, path_lock)
        except TimeoutError as e:
            return

        
        driver = self._browser(profile_name, proxy_info, block_media)
        self._arrange_window(driver, row, col)
        node = Node(driver, profile_name, self.tele_bot, self.ai_bot)

        try:
            # Khi chạy chương trình với phương thức run_stop. Duyệt trình sẽ duy trì trạng thái
            if stop_flag:
                # Nếu có SetupHandlerClass thì thực hiện
                if self.SetupHandlerClass:
                    self.SetupHandlerClass(node, profile)._run()
                self._listen_for_enter(profile_name)
            else:
                # Nếu có AutoHandlerClass thì thực hiện
                if self.AutoHandlerClass:
                    self.AutoHandlerClass(node, profile)._run()
                    
        except ValueError as e:
            # Node.snapshot() quăng lỗi ra đây
            pass
        except Exception as e:
            # Lỗi bất kỳ khác
            self._log(profile_name, str(e))

        finally:
            Utility.wait_time(5, True)
            self._log(profile_name, 'Đóng... wait')
            Utility.wait_time(1, True)
            driver.quit()
            # Giải phóng profile
            Utility.unlock_profile(path_lock)
            self._release_position(profile_name, row, col)

    def run_multi(self, profiles: list[dict], max_concurrent_profiles: int = 1, delay_between_profiles: int = 10, block_media: bool = False):
        '''
        Phương thức khởi chạy nhiều hồ sơ đồng thời

        Args:
            profiles (list[dict]): Danh sách các hồ sơ trình duyệt cần khởi chạy.
                Mỗi hồ sơ là một dictionary chứa thông tin, với key 'profile' là bắt buộc, ví dụ: {'profile': 'profile_name',...}.
            max_concurrent_profiles (int, optional): Số lượng tối đa các hồ sơ có thể chạy đồng thời. Mặc định là 1.
            delay_between_profiles (int, optional): Thời gian chờ giữa việc khởi chạy hai hồ sơ liên tiếp (tính bằng giây). Mặc định là 10 giây.
            block_media (bool, optional): True, block image và video để tăng hiệu suất, nhưng cần False khi có cloudflare. Mặc định `False`.
        Hoạt động:
            - Sử dụng `ThreadPoolExecutor` để khởi chạy các hồ sơ trình duyệt theo mô hình đa luồng.
            - Hàng đợi (`queue`) chứa danh sách các hồ sơ cần chạy.
            - Xác định vị trí hiển thị trình duyệt (`row`, `col`) thông qua `_get_position`.
            - Khi có vị trí trống, hồ sơ sẽ được khởi chạy thông qua phương thức `run`.
            - Nếu không có vị trí nào trống, chương trình chờ 10 giây trước khi kiểm tra lại.
        '''
        queue = [profile for profile in profiles]
        self._get_matrix(
            max_concurrent_profiles=max_concurrent_profiles,
            number_profiles=len(queue)
        )

        with ThreadPoolExecutor(max_workers=max_concurrent_profiles) as executor:
            while len(queue) > 0:
                profile = queue[0]
                profile_name = profile['profile_name']
                row, col = self._get_position(profile_name)

                if row is not None and col is not None:
                    queue.pop(0)
                    executor.submit(self.run_browser, profile, row, col, block_media)
                    # Thời gian chờ mở profile kế
                    Utility.wait_time(delay_between_profiles, True)
                else:
                    # Thời gian chờ check lại
                    Utility.wait_time(10, True)

    def run_stop(self, profiles: list[dict], block_media: bool = False):
        '''
        Chạy từng hồ sơ trình duyệt tuần tự, đảm bảo chỉ mở một profile tại một thời điểm.

        Args:
            profiles (list[dict]): Danh sách các hồ sơ trình duyệt cần khởi chạy.
                Mỗi profile là một dictionary chứa thông tin, trong đó key 'profile' là bắt buộc. 
                Ví dụ: {'profile': 'profile_name', ...}
            block_media (bool, optional): True, block image và video để tăng hiệu suất, nhưng cần False khi có cloudflare. Mặc định `False`.
        Hoạt động:
            - Duyệt qua từng profile trong danh sách.
            - Hiển thị thông báo chờ 5 giây trước khi khởi chạy từng hồ sơ.
            - Gọi `run_browser()` để chạy hồ sơ.
            - Chờ cho đến khi hồ sơ hiện tại đóng lại trước khi tiếp tục hồ sơ tiếp theo.
        '''
        self.matrix = [[None]]
        for index, profile in enumerate(profiles):
            self._log(
                profile_name=profile['profile_name'], message=f'[{index+1}/{len(profiles)}]Chờ 5s...')
            Utility.wait_time(5)

            self.run_browser(profile=profile,block_media=block_media, stop_flag=True)

    def run_terminal(self, profiles: list[dict], max_concurrent_profiles: int = 4, auto: bool = False, headless: bool = False, disable_gpu: bool = False, block_media: bool = False):
        '''
        Chạy giao diện dòng lệnh để người dùng chọn chế độ chạy.

        Args:
            profiles (list[dict]): Danh sách các profile trình duyệt có thể khởi chạy.
                Mỗi profile là một dictionary chứa thông tin, trong đó key 'profile' là bắt buộc. 
                Ví dụ: {'profile': 'profile_name', ...}
            max_concurrent_profiles (int, optional): Số lượng tối đa các hồ sơ có thể chạy đồng thời. Mặc định là 4.
            auto (bool, optional): True, bỏ qua lựa chọn terminal và chạy trực tiếp chức năng auto. Mặc định False.
            headless (bool, optional): True, sẽ ẩn duyệt trình khi chạy. Mặc định False.
            disable_gpu (bool, optional): True, tắt GPU, dành cho máy không có GPU vật lý. Mặc định False.
            block_media (bool, optional): True, block image và video để tăng hiệu suất, nhưng cần False khi có cloudflare. Mặc định `False`.
        
        Chức năng:
            - Hiển thị menu cho phép người dùng chọn một trong các chế độ:
                1. Set up: Chọn và mở lần lượt từng profile để cấu hình.
                2. Chạy auto: Tự động chạy các profile đã cấu hình.
                3. Xóa profile: Xóa profile đã tồn tại.
                0. Thoát chương trình.
            - Khi chọn Set up, người dùng có thể chọn chạy tất cả hoặc chỉ một số profile cụ thể.
            - Khi chọn Chạy auto, chương trình sẽ khởi động tự động với số lượng profile tối đa có thể chạy đồng thời.
            - Hỗ trợ quay lại menu chính hoặc thoát chương trình khi cần.

        Hoạt đông:
            - Gọi `run_stop()` nếu người dùng chọn Set up.
            - Gọi `run_multi()` nếu người dùng chọn Chạy auto.

        '''
        self.headless = headless
        self.disable_gpu = disable_gpu
        
        is_run = True

        print("\n"+"=" * 60)
        print(f"⚙️  Tool Automation Airdrop đang sử dụng:")
        if self.tele_bot.valid:
            print(f"   📍 Tele bot:             {self.tele_bot.bot_name}")
        if self.ai_bot.valid:
            print(f"   📍 AI bot Gemini:        {self.ai_bot.model_name}")
        if self.path_chromium:
            print(f"   📍 Đường dẫn Chrome:     {self.path_chromium}")
        else:
            print(f"   📍 Chrome hệ thống")
        print(f"   📍 Đường dẫn Profiles:   {self.user_data_dir}")
        print("=" * 60+"\n")

        while is_run:
            user_data_profiles = []

            if self.user_data_dir.exists() and self.user_data_dir.is_dir():
                raw_user_data_profiles = [folder.name for folder in self.user_data_dir.iterdir() if folder.is_dir()]
                
                # Thêm các profile theo thứ tự trong profiles trước
                for profile in profiles:
                    profile_name = profile['profile_name']
                    if profile_name in raw_user_data_profiles:
                        user_data_profiles.append(profile_name)
                
                # Thêm các profile còn lại không có trong profiles vào cuối
                for profile_name in raw_user_data_profiles:
                    if profile_name not in user_data_profiles:
                        user_data_profiles.append(profile_name)
            
            if not auto:
                print("[A] 📋 Chọn một tùy chọn:")
                print("   1. Set up       - Mở lần lượt từng profile để cấu hình.")
                print("   2. Chạy auto    - Tất cả profiles sau khi đã cấu hình.")
                if user_data_profiles:
                    print("   3. Xóa profile  - Xoá các profile đã tồn tại.") # đoạn này xuất hiện, nếu có tồn tại danh sách user_data_profiles ở trên
                print("   0. Thoát        - Thoát chương trình.")
                choice = input("Nhập lựa chọn: ")
            else:
                choice = '2'
                profile_list = profiles
                is_run = False

            if choice in ('1', '2', '3'):

                if not auto:
                    profile_list = profiles if choice in ('1', '2') else user_data_profiles
                    print("=" * 10)
                    if choice in ('1', '2'):
                        print(
                            f"[B] 📋 Chọn các profile muốn chạy {'Set up' if choice == '1' else 'Auto'}:")
                        print(f"❌ Không tồn tại profile trong file data.txt") if len(profile_list) == 0 else None
                    elif (choice in ('3')):
                        if not user_data_profiles:
                            continue
                        print("[B] 📋 Chọn các profile muốn xóa:")

                    print(f"   0. ALL ({len(profile_list)})") if len(profile_list) > 1 else None
                    for idx, profile in enumerate(profile_list, start=1):
                        print(f"   {idx}. {profile['profile_name'] if choice in ('1', '2') else profile}{' [✓]' if choice in ('1', '2') and profile['profile_name'] in user_data_profiles else ''}")

                    profile_choice = input(
                        "Nhập số và cách nhau bằng dấu cách (nếu chọn nhiều) hoặc bất kì để quay lại: ")
                else:
                    profile_choice = '0'

                selected_profiles = []
                choices = profile_choice.split()
                if "0" in choices:  # Chạy tất cả profiles
                    selected_profiles = profile_list
                else:
                    for ch in choices:
                        if ch.isdigit():
                            index = int(ch) - 1
                            if 0 <= index < len(profile_list):  # Kiểm tra index hợp lệ
                                selected_profiles.append(profile_list[index])
                            else:
                                print(f"⚠ Profile {ch} không hợp lệ, bỏ qua.")

                if not selected_profiles:
                    Utility.print_section('LỖI: Lựa chọn không hợp lệ. Vui lòng thử lại...', "🛑")
                    continue
                
                if choice == '1':
                    Utility.print_section("BẮT ĐẦU CHƯƠNG TRÌNH","🔄")                
                    self.run_stop(selected_profiles, block_media)
                    Utility.print_section("KẾT THÚC CHƯƠNG TRÌNH","✅")                
                
                elif choice == '2':
                    Utility.print_section("BẮT ĐẦU CHƯƠNG TRÌNH","🔄")                
                    self.run_multi(profiles=selected_profiles,
                                   max_concurrent_profiles=max_concurrent_profiles, block_media=block_media)
                    Utility.print_section("KẾT THÚC CHƯƠNG TRÌNH","✅")                

                elif choice == '3':
                    profiles_to_deleted = []
                    for profile_name in selected_profiles:
                        # kiểm tra profile_name là string
                        if not isinstance(profile_name, str):
                            continue
                        profile_path = self.user_data_dir / profile_name
                        try:
                            shutil.rmtree(profile_path)
                            profiles_to_deleted.append(profile_name)
                        except Exception as e:
                            self._log(message=f"❌ Lỗi khi xóa profile {profile_name}: {e}")
                    Utility.print_section(f"Đã xóa profile: {profiles_to_deleted}")
            elif choice == '0':  # Thoát chương trình
                is_run = False
                Utility.print_section("THOÁT CHƯƠNG TRÌNH","❎")

            else:
                Utility.print_section('LỖI: Lựa chọn không hợp lệ. Vui lòng thử lại...', "🛑")


if __name__ == '__main__':
    profiles = Utility.read_data('profile_name')
    if not profiles:
        print("Không có dữ liệu để chạy")
        exit()
    browser_manager = BrowserManager()
    browser_manager.config_extension('meta-wallet-*.crx')
    # browser_manager.run_browser(profiles[0])
    browser_manager.run_terminal(
        profiles=profiles,
        max_concurrent_profiles=4,
        auto=False,
        headless=False,
        disable_gpu=False,
        block_media=False
    )
