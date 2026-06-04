import time
import traceback
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


DEFAULT_EDIT_URL = "https://ygosu.com/board/soop/1609701/?mode=modify&backurl=https%3A%2F%2Fygosu.com%2Fboard%2Fsoop%2F1609701"
EDIT_URL_FILE = Path(__file__).resolve().parent / "beobbang_edit_url.txt"
EDIT_URL = EDIT_URL_FILE.read_text(encoding="utf-8-sig").strip() if EDIT_URL_FILE.exists() else DEFAULT_EDIT_URL

BASE_DIR = Path(__file__).resolve().parent
TXT_PATTERNS = ["ygosu_paste_*.txt", "ygosu_paste.txt"]
AUTO_PROFILE_DIR = BASE_DIR / "chrome_profile_ygosu_auto"

DRY_RUN = False


def find_latest_txt():
    files = []
    for pattern in TXT_PATTERNS:
        files.extend(BASE_DIR.glob(pattern))
    files = [p for p in files if p.is_file()]
    if not files:
        raise Exception(f"파일 없음: {BASE_DIR} / {TXT_PATTERNS}")
    return max(files, key=lambda p: p.stat().st_mtime)


def js_set(driver, element, value):
    driver.execute_script(
        """
        const el = arguments[0];
        const value = arguments[1];

        if ('value' in el) {
            el.value = value;
        } else {
            el.innerHTML = value;
        }

        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true}));
        """,
        element,
        value,
    )


def set_title(driver):
    for selector in ["input[name='subject']", "input[name='title']", "input[type='text']"]:
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if el.is_displayed() and el.is_enabled():
                    now = time.strftime("%y/%m/%d %H:%M")
                    js_set(driver, el, f"버빵동 현황판 ({now} 집계)")
                    print("제목 입력 완료")
                    return True
            except:
                pass

    print("제목 입력창 못 찾음")
    print("현재 주소:", driver.current_url)
    return False


def sync_all_editors(driver, html):
    driver.switch_to.default_content()

    # 스마트에디터 강제 동기화
    driver.execute_script(
        """
        const html = arguments[0];

        try {
            if (typeof oEditors !== 'undefined' && oEditors.getById) {
                for (let k in oEditors.getById) {
                    try {
                        oEditors.getById[k].exec('SET_IR', [html]);
                        oEditors.getById[k].exec('UPDATE_CONTENTS_FIELD', []);
                    } catch(e) {}
                }
            }
        } catch(e) {}

        try {
            if (window.oEditors && window.oEditors.getById) {
                for (let k in window.oEditors.getById) {
                    try {
                        window.oEditors.getById[k].exec('SET_IR', [html]);
                        window.oEditors.getById[k].exec('UPDATE_CONTENTS_FIELD', []);
                    } catch(e) {}
                }
            }
        } catch(e) {}
        """,
        html,
    )

    # iframe 에디터
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"iframe 개수: {len(frames)}")

    for idx, frame in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            driver.execute_script(
                """
                const html = arguments[0];
                if (document.body) {
                    document.body.focus();
                    document.body.innerHTML = html;
                    document.body.dispatchEvent(new Event('input', {bubbles:true}));
                    document.body.dispatchEvent(new Event('change', {bubbles:true}));
                    document.body.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true}));
                }
                """,
                html,
            )
            print(f"iframe #{idx} 동기화 완료")
        except:
            pass
        finally:
            driver.switch_to.default_content()

    # contenteditable
    for idx, el in enumerate(driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")):
        try:
            driver.execute_script(
                """
                const el = arguments[0];
                const html = arguments[1];
                el.focus();
                el.innerHTML = html;
                el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true}));
                """,
                el,
                html,
            )
            print(f"contenteditable #{idx} 동기화 완료")
        except:
            pass

    # 모든 textarea
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    print(f"textarea 개수: {len(textareas)}")

    for idx, ta in enumerate(textareas):
        try:
            js_set(driver, ta, html)
            print(f"textarea #{idx} 동기화 완료")
        except:
            pass

    driver.switch_to.default_content()


def handle_alerts(driver):
    handled = False
    for _ in range(5):
        try:
            alert = WebDriverWait(driver, 2).until(lambda d: d.switch_to.alert)
            print("알림창:", alert.text)
            alert.accept()
            handled = True
            time.sleep(1)
        except TimeoutException:
            break
        except:
            break
    return handled



def force_open_edit_page(driver):
    """
    현재 탭이 광고/외부 사이트여도 무조건 와이고수 수정 URL로 이동.
    기존 복구 탭 때문에 엉뚱한 페이지가 잡히는 문제 방지.
    """
    driver.switch_to.default_content()

    urls = [
        EDIT_URL,
        EDIT_URL.replace("https://ygosu.com", "https://www.ygosu.com"),
    ]

    # 새 탭을 하나 열고 그 탭에서만 작업
    try:
        driver.execute_script("window.open('about:blank', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(0.5)
    except Exception as e:
        print("새 탭 열기 실패, 현재 탭 사용:", e)

    last_url = ""
    for url in urls:
        print("수정 페이지 접속:", url)
        try:
            driver.get(url)
            time.sleep(5)
            handle_alerts(driver)

            last_url = driver.current_url
            print("현재 주소:", last_url)

            low = last_url.lower()
            if ("ygosu.com" in low) and ("mode=modify" in low or "modify" in low):
                print("와이고수 수정 페이지 접속 확인")
                return True

            # 자동 실행용: 로그인 페이지로 이동하면 엔터 대기하지 않고 즉시 실패 처리
            if "login" in low or "member" in low:
                print("로그인이 필요합니다. 자동 실행에서는 대기하지 않고 종료합니다.")
                return False

        except Exception as e:
            print("수정 페이지 접속 실패:", e)

    print("[ERROR] 와이고수 수정 페이지로 이동 실패")
    print("마지막 주소:", last_url)
    return False


def ensure_edit_page_or_stop(driver):
    current = driver.current_url
    low = current.lower()
    if ("ygosu.com" not in low) or ("mode=modify" not in low and "modify" not in low):
        print("[ERROR] 현재 페이지가 와이고수 수정 페이지가 아닙니다.")
        print("현재 주소:", current)
        print("Adobe/광고/다른 탭이 잡힌 상태일 가능성이 큽니다.")
        return False
    return True


def print_clickable_debug(driver):
    driver.switch_to.default_content()

    print("")
    print("=== 클릭 가능한 요소 목록 일부 ===")

    items = driver.find_elements(By.CSS_SELECTOR, "a, button, input")
    for i, el in enumerate(items[:120]):
        try:
            txt = (
                (el.text or "")
                + " | value=" + (el.get_attribute("value") or "")
                + " | type=" + (el.get_attribute("type") or "")
                + " | class=" + (el.get_attribute("class") or "")
                + " | id=" + (el.get_attribute("id") or "")
                + " | onclick=" + (el.get_attribute("onclick") or "")
            )
            txt = " ".join(txt.split())
            if txt.strip():
                print(f"{i}: {txt[:220]}")
        except:
            pass

    print("=== 목록 끝 ===")
    print("")


def click_by_xpath_text(driver):
    driver.switch_to.default_content()

    xpaths = [
        "//*[self::button or self::a or self::input][contains(normalize-space(.), '수정')]",
        "//*[self::button or self::a or self::input][contains(normalize-space(.), '등록')]",
        "//*[self::button or self::a or self::input][contains(normalize-space(.), '확인')]",
        "//*[self::button or self::a or self::input][contains(normalize-space(.), '저장')]",
        "//input[contains(@value, '수정')]",
        "//input[contains(@value, '등록')]",
        "//input[contains(@value, '확인')]",
        "//input[contains(@value, '저장')]",
        "//*[contains(@onclick, 'write')]",
        "//*[contains(@onclick, 'modify')]",
        "//*[contains(@onclick, 'submit')]",
        "//*[contains(@class, 'write')]",
        "//*[contains(@class, 'submit')]",
        "//*[contains(@id, 'write')]",
        "//*[contains(@id, 'submit')]",
    ]

    for xp in xpaths:
        els = driver.find_elements(By.XPATH, xp)
        if not els:
            continue

        print(f"XPath 후보 {xp} : {len(els)}개")

        # 보이는 요소 우선, 아래쪽 요소 우선
        scored = []
        for el in els:
            try:
                rect = el.rect
                visible = el.is_displayed()
                scored.append((visible, rect.get("y", 0), el))
            except:
                scored.append((False, 0, el))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

        for visible, y, el in scored:
            try:
                label = (
                    (el.text or "")
                    + " " + (el.get_attribute("value") or "")
                    + " " + (el.get_attribute("onclick") or "")
                    + " " + (el.get_attribute("class") or "")
                    + " " + (el.get_attribute("id") or "")
                )
                print("클릭 시도:", " ".join(label.split())[:200])

                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.5)

                try:
                    el.click()
                except:
                    driver.execute_script("arguments[0].click();", el)

                handle_alerts(driver)
                time.sleep(3)
                return True

            except Exception as e:
                print("클릭 실패:", e)

    return False


def call_known_submit_functions(driver):
    driver.switch_to.default_content()

    print("submit 관련 JS 함수 직접 호출 시도")

    result = driver.execute_script(
        """
        const logs = [];

        function tryCall(name) {
            try {
                if (typeof window[name] === 'function') {
                    logs.push('call ' + name);
                    window[name]();
                    return true;
                }
            } catch(e) {
                logs.push(name + ' error ' + e.message);
            }
            return false;
        }

        const names = [
            'checkSubmit',
            'submitContents',
            'writeSubmit',
            'board_write',
            'boardWrite',
            'submitForm',
            'goWrite',
            'goSubmit',
            'chkWrite',
            'frmSubmit'
        ];

        let ok = false;
        for (const n of names) {
            if (tryCall(n)) {
                ok = true;
                break;
            }
        }

        return {ok, logs};
        """
    )

    print("JS 함수 호출 결과:", result)
    handle_alerts(driver)
    time.sleep(2)
    return bool(result and result.get("ok"))


def direct_form_submit(driver):
    driver.switch_to.default_content()

    forms = driver.find_elements(By.TAG_NAME, "form")
    print(f"form 개수: {len(forms)}")

    # 뒤쪽 form부터 시도: 글쓰기 폼이 보통 본문 아래/뒤쪽
    for idx in range(len(forms) - 1, -1, -1):
        form = forms[idx]
        try:
            action = form.get_attribute("action") or ""
            method = form.get_attribute("method") or ""
            print(f"form #{idx} submit 시도: method={method}, action={action[:150]}")

            driver.execute_script(
                """
                const form = arguments[0];

                try {
                    form.dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
                } catch(e) {}

                try {
                    HTMLFormElement.prototype.submit.call(form);
                } catch(e) {
                    form.submit();
                }
                """,
                form,
            )

            handle_alerts(driver)
            time.sleep(3)
            return True

        except Exception as e:
            print(f"form #{idx} submit 실패:", e)

    return False


def final_submit(driver, html):
    print("저장 직전 에디터 재동기화")
    sync_all_editors(driver, html)
    time.sleep(1)

    print_clickable_debug(driver)

    if click_by_xpath_text(driver):
        print("XPath 텍스트 버튼 클릭 완료")
        return True

    if call_known_submit_functions(driver):
        print("JS submit 함수 호출 완료")
        return True

    if direct_form_submit(driver):
        print("form 직접 submit 완료")
        return True

    return False


try:
    print("=== 와이고수 자동 수정 시작 ===")

    txt_file = find_latest_txt()
    print(f"사용 TXT 파일: {txt_file.name}")

    html = txt_file.read_text(encoding="utf-8")

    AUTO_PROFILE_DIR.mkdir(exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={AUTO_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--remote-debugging-port=9223")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument("--disable-features=InfiniteSessionRestore")

    driver = webdriver.Chrome(options=options)

    if not force_open_edit_page(driver):
        print("수정 페이지를 열지 못해서 중단합니다.")
        driver.quit()
        sys.exit(1)

    if not ensure_edit_page_or_stop(driver):
        driver.quit()
        sys.exit(1)

    if not set_title(driver):
        if not ensure_edit_page_or_stop(driver):
            driver.quit()
            sys.exit(1)
        print("제목 입력창을 못 찾았지만 본문 입력은 계속 시도합니다.")

    print("본문 입력/동기화")
    sync_all_editors(driver, html)

    if DRY_RUN:
        print("DRY_RUN=True 상태 - 저장하지 않음")
        driver.quit()
        sys.exit(0)

    ok = final_submit(driver, html)

    if ok:
        print("자동 등록/수정 시도 완료")
        print("현재 주소:", driver.current_url)
        time.sleep(3)
    else:
        print("자동 클릭 실패")
        print("자동 실행용이라 대기하지 않고 브라우저를 닫습니다.")

    driver.quit()
    sys.exit(0 if ok else 1)

except Exception as e:
    print("")
    print("에러 발생")
    print(e)
    traceback.print_exc()
    try:
        driver.quit()
    except Exception:
        pass
    sys.exit(1)
