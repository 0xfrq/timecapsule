import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json
import time
import os
import random
import requests

class GrokImageGenerator:
    def __init__(self, cookies_file="grok_cookies.json"):
        self.cookies_file = cookies_file
        self.driver = None
        
    def setup_driver(self, user_data_dir=None):
        print("Initializing undetected Chrome driver...")
        
        options = uc.ChromeOptions()
        
        prefs = {
            "download.default_directory": os.path.abspath("."),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        options.add_argument(f'--window-size={width},{height}')
        
        try:
            self.driver = uc.Chrome(options=options)
        except Exception as e:
            print(f"Error: {e}")
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except:
            pass
        
        time.sleep(random.uniform(2, 4))
        print("Driver initialized")
        
    def human_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))
        
    def slow_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
    
    def save_cookies(self):
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"Cookies saved to {self.cookies_file}")
            print(f"Saved {len(cookies)} cookies")
        except Exception as e:
            print(f"Error saving cookies: {e}")
        
    def load_cookies(self):
        if not os.path.exists(self.cookies_file):
            print("No cookie file found")
            return False
        
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            if not cookies:
                print("Cookie file is empty")
                return False
            
            print(f"Loading {len(cookies)} cookies...")
            
            self.driver.get("https://grok.com")
            self.human_delay(2, 3)
            
            added_count = 0
            for cookie in cookies:
                try:
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    if 'sameSite' in cookie:
                        if cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                            cookie['sameSite'] = 'Lax'
                    
                    self.driver.add_cookie(cookie)
                    added_count += 1
                except Exception as e:
                    pass
            
            print(f"Added {added_count}/{len(cookies)} cookies")
            
            self.driver.refresh()
            self.human_delay(2, 3)
            return True
            
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return False
    
    def manual_login_with_steps(self):
        print("\n" + "="*60)
        print("MANUAL LOGIN")
        print("="*60)
        print("\nSTEPS:")
        print("1. Browser will open to grok.com")
        print("2. Click 'Sign in' and log in with X/Twitter")
        print("3. After login, navigate to: https://grok.com/imagine")
        print("4. Wait until you see the image generation interface")
        print("5. Come back here and press ENTER")
        print("="*60 + "\n")
        
        self.driver.get("https://grok.com")
        self.human_delay(3, 5)
        
        input("Press ENTER after you're logged in and on the Imagine page...")
        
        print("Saving login session...")
        self.save_cookies()
        
        current_url = self.driver.current_url
        if 'imagine' not in current_url:
            print("Navigating to Imagine page...")
            self.driver.get("https://grok.com/imagine")
            self.human_delay(2, 3)
        
        print("Login successful!")
        return True
    
    def select_image_mode(self):
        try:
            print("Selecting image mode...")
            
            mode_selectors = [
                'button[aria-label*="image"]',
                'button[aria-label*="Image"]',
                'div[role="tab"][aria-label*="image"]',
                'button:has(svg)',
            ]
            
            for selector in mode_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.get_attribute('aria-label') or elem.text
                        if 'image' in text.lower():
                            elem.click()
                            print("Image mode selected")
                            self.human_delay(1, 2)
                            return True
                except:
                    continue
            
            print("Could not find image mode selector, continuing anyway...")
            return True
        except Exception as e:
            print(f"Error selecting image mode: {e}")
            return True
    
    def generate_images(self, prompt, output_dir="generated_images", num_images=5, wait_time=60):
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            print("\nNavigating to Grok Imagine...")
            self.driver.get("https://grok.com/imagine")
            self.human_delay(5, 8)
            
            self.select_image_mode()
            
            print("Looking for prompt input...")
            input_selectors = [
                'div[contenteditable="true"][data-placeholder*="imagine"]',
                'div.tiptap[contenteditable="true"]',
                'div[contenteditable="true"]',
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        input_field = elements[0]
                        print("Found input field")
                        break
                except:
                    continue
            
            if not input_field:
                print("Could not find input field")
                self.driver.save_screenshot("no_input_found.png")
                return False
            
            print(f"Entering prompt: {prompt}")
            input_field.click()
            self.human_delay(0.5, 1)
            
            input_field.send_keys(Keys.CONTROL + "a")
            input_field.send_keys(Keys.BACKSPACE)
            self.human_delay(0.3, 0.5)
            
            self.slow_type(input_field, prompt)
            self.human_delay(1, 2)
            
            print("Submitting prompt...")
            submit_selectors = [
                'button[type="submit"][aria-label="Submit"]',
                'button[aria-label="Submit"]',
                'button[type="submit"]'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if not btn.get_attribute('disabled'):
                            btn.click()
                            print("Submitted!")
                            submitted = True
                            break
                    if submitted:
                        break
                except:
                    continue
            
            if not submitted:
                input_field.send_keys(Keys.RETURN)
                print("Submitted via Enter key")
            
            print(f"\nWaiting {wait_time} seconds for images to generate...")
            for i in range(0, wait_time, 10):
                time.sleep(10)
                print(f"{i+10}/{wait_time} seconds")
            
            print("\nScrolling to view all images...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.human_delay(2, 3)
            
            print(f"Looking for generated images (getting top {num_images})...")
            
            image_containers = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[role="listitem"] img[alt*="Generated"]'
            )
            
            if not image_containers:
                image_containers = self.driver.find_elements(By.CSS_SELECTOR, 'img[alt*="Generated"]')
            
            if not image_containers:
                print("No images found!")
                self.driver.save_screenshot("no_images_found.png")
                return False
            
            print(f"Found {len(image_containers)} generated images")
            
            images_to_download = image_containers[:num_images]
            downloaded_files = []
            
            main_window = self.driver.current_window_handle
            
            for idx, img_element in enumerate(images_to_download, 1):
                try:
                    print(f"\nProcessing image {idx}/{len(images_to_download)}...")
                    
                    self.driver.switch_to.window(main_window)
                    self.human_delay(1, 2)
                    
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_element)
                        self.human_delay(1, 2)
                    except:
                        print(f"Re-finding image {idx}...")
                        image_containers = self.driver.find_elements(
                            By.CSS_SELECTOR, 
                            'div[role="listitem"] img[alt*="Generated"]'
                        )
                        if idx <= len(image_containers):
                            img_element = image_containers[idx-1]
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_element)
                            self.human_delay(1, 2)
                        else:
                            print(f"Could not find image {idx}")
                            continue
                    
                    print(f"Clicking image {idx}...")
                    img_element.click()
                    self.human_delay(2, 3)
                    
                    print(f"Looking for download button...")
                    download_button = None
                    
                    download_selectors = [
                        'button[aria-label="Download"]',
                        'button:has(svg.lucide-download)',
                        'svg.lucide-download',
                    ]
                    
                    for selector in download_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                try:
                                    if elem.is_displayed():
                                        download_button = elem
                                        if 'svg' in selector:
                                            download_button = elem.find_element(By.XPATH, '..')
                                        break
                                except:
                                    continue
                            if download_button:
                                break
                        except:
                            continue
                    
                    if not download_button:
                        print(f"No download button found, trying to get image URL...")
                        
                        main_images = self.driver.find_elements(By.CSS_SELECTOR, 'img[src*="http"]')
                        for main_img in main_images:
                            try:
                                if main_img.size['width'] > 300:
                                    img_url = main_img.get_attribute('src')
                                    if img_url and ('grok' in img_url or 'twimg' in img_url):
                                        print(f"Found image URL, downloading...")
                                        response = requests.get(img_url, headers={
                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                        })
                                        ext = 'jpg' if 'jpg' in img_url or 'jpeg' in img_url else 'png'
                                        new_filename = f"{output_dir}/image_{idx}.{ext}"
                                        with open(new_filename, 'wb') as f:
                                            f.write(response.content)
                                        print(f"Downloaded: {new_filename}")
                                        downloaded_files.append(new_filename)
                                        break
                            except:
                                continue
                        
                        try:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            self.human_delay(1, 2)
                        except:
                            pass
                        continue
                    
                    windows_before = len(self.driver.window_handles)
                    
                    print(f"Clicking download button...")
                    download_button.click()
                    self.human_delay(2, 3)
                    
                    windows_after = len(self.driver.window_handles)
                    
                    if windows_after > windows_before:
                        print(f"New tab opened, switching to download tab...")
                        new_window = [w for w in self.driver.window_handles if w != main_window][0]
                        self.driver.switch_to.window(new_window)
                        self.human_delay(2, 3)
                        
                        current_url = self.driver.current_url
                        print(f"Download URL: {current_url[:80]}...")
                        
                        try:
                            response = requests.get(current_url, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            })
                            
                            ext = 'jpg'
                            if '.png' in current_url:
                                ext = 'png'
                            elif '.webp' in current_url:
                                ext = 'webp'
                            elif 'content-type' in response.headers:
                                content_type = response.headers['content-type']
                                if 'png' in content_type:
                                    ext = 'png'
                                elif 'webp' in content_type:
                                    ext = 'webp'
                            
                            new_filename = f"{output_dir}/image_{idx}.{ext}"
                            with open(new_filename, 'wb') as f:
                                f.write(response.content)
                            
                            print(f"Downloaded: {new_filename}")
                            downloaded_files.append(new_filename)
                        except Exception as e:
                            print(f"Failed to download from URL: {e}")
                        
                        print(f"Closing download tab...")
                        self.driver.close()
                        
                        self.driver.switch_to.window(main_window)
                        print(f"Back to main window")
                        self.human_delay(1, 2)
                    else:
                        print(f"Checking for downloaded file...")
                        time.sleep(3)
                        
                        files = [f for f in os.listdir('.') if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                        if files:
                            latest_file = max(files, key=lambda x: os.path.getctime(x))
                            if os.path.getctime(latest_file) > time.time() - 10:
                                ext = latest_file.split('.')[-1]
                                new_filename = f"{output_dir}/image_{idx}.{ext}"
                                os.rename(latest_file, new_filename)
                                print(f"Downloaded: {new_filename}")
                                downloaded_files.append(new_filename)
                    
                    try:
                        self.driver.switch_to.window(main_window)
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        self.human_delay(1, 2)
                    except:
                        pass
                    
                except Exception as e:
                    print(f"Error with image {idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    try:
                        self.driver.switch_to.window(main_window)
                    except:
                        pass
                    continue
            
            print(f"\nSuccessfully processed {len(downloaded_files)} images!")
            print(f"Saved in: {output_dir}/")
            for f in downloaded_files:
                print(f"- {f}")
            
            return len(downloaded_files) > 0
            
        except Exception as e:
            print(f"Error generating images: {e}")
            self.driver.save_screenshot("error_screenshot.png")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    print("\nGROK IMAGE GENERATOR - BATCH DOWNLOAD\n")
    
    generator = GrokImageGenerator()
    
    try:
        generator.setup_driver()
        
        cookies_loaded = generator.load_cookies()
        
        if not cookies_loaded:
            print("\nNo saved session found - login required")
            generator.manual_login_with_steps()
        else:
            print("Verifying saved session...")
            generator.driver.get("https://grok.com/imagine")
            generator.human_delay(3, 5)
            
            if "signin" in generator.driver.current_url.lower() or "login" in generator.driver.current_url.lower():
                print("Session expired - login required")
                generator.manual_login_with_steps()
            else:
                print("Logged in with saved session!")
        
        print("\n" + "="*60)
        prompt = input("Enter your image prompt: ").strip()
        if not prompt:
            prompt = "A futuristic cyberpunk city at sunset with flying cars"
            print(f"Using default prompt: {prompt}")
        
        num_images = input("How many images to download? (default: 5): ").strip()
        num_images = int(num_images) if num_images.isdigit() else 5
        
        output_dir = input("Output directory (default: generated_images): ").strip()
        if not output_dir:
            output_dir = "generated_images"
        
        print("\n" + "="*60)
        success = generator.generate_images(
            prompt, 
            output_dir=output_dir,
            num_images=num_images,
            wait_time=50
        )
        
        if success:
            print("\nSUCCESS! Images downloaded!")
        else:
            print("\nFailed to download images. Check screenshots.")
        
        input("\nPress ENTER to close browser...")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.close()
        print("\nBrowser closed. Goodbye!")


if __name__ == "__main__":
    main()