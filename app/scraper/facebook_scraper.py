import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import re

from app.config.settings import BROWSER_HEADLESS, FACEBOOK_EMAIL, FACEBOOK_PASSWORD, FACEBOOK_COOKIES
from app.utils.error_handling import setup_logger, handle_captcha_error, handle_auth_failure, log_scraper_activity

# Configure logger
logger = setup_logger('app.scraper.facebook')

class FacebookScraper:
    """
    Scraper for Facebook Groups to extract posts and check for keywords
    """
    
    def __init__(self, headless=BROWSER_HEADLESS):
        """Initialize the Facebook scraper with browser options"""
        self.headless = headless
        self.driver = None
        self.cookies_file = os.path.join(os.path.dirname(__file__), '..', '..', 'facebook_cookies.json')
        
    def _setup_driver(self):
        """Set up and configure the Selenium WebDriver"""
        try:
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-infobars')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            logger.info("WebDriver set up successfully")
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {str(e)}")
            raise
        
    def _load_cookies(self):
        """Load Facebook cookies from file if available"""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                # Add cookies to browser
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                
                logger.info("Loaded Facebook cookies from file")
                return True
            except Exception as e:
                logger.error(f"Error loading cookies: {str(e)}")
        
        return False
    
    def _save_cookies(self):
        """Save Facebook cookies to file for future use"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info("Saved Facebook cookies to file")
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")
    
    def login(self):
        """Log in to Facebook using credentials or cookies"""
        try:
            if not self.driver:
                self._setup_driver()
            
            self.driver.get('https://www.facebook.com/')
            logger.info("Navigating to Facebook login page")
            
            # Try to use cookies first
            if FACEBOOK_COOKIES:
                try:
                    cookies = json.loads(FACEBOOK_COOKIES)
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                    self.driver.refresh()
                    logger.info("Logged in using provided cookies")
                    return True
                except Exception as e:
                    logger.error(f"Error using provided cookies: {str(e)}")
            
            # Try to load cookies from file
            if self._load_cookies():
                self.driver.refresh()
                # Check if login was successful
                if self._is_logged_in():
                    logger.info("Logged in using saved cookies")
                    return True
            
            # If cookies didn't work, try email/password login
            if FACEBOOK_EMAIL and FACEBOOK_PASSWORD:
                try:
                    # Find email and password fields
                    email_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "email"))
                    )
                    password_field = self.driver.find_element(By.ID, "pass")
                    
                    # Enter credentials
                    email_field.send_keys(FACEBOOK_EMAIL)
                    password_field.send_keys(FACEBOOK_PASSWORD)
                    
                    # Click login button
                    login_button = self.driver.find_element(By.NAME, "login")
                    login_button.click()
                    
                    # Wait for login to complete
                    time.sleep(5)
                    
                    # Check if login was successful
                    if self._is_logged_in():
                        logger.info("Logged in using email and password")
                        self._save_cookies()
                        return True
                    else:
                        logger.error("Login failed - could not verify successful login")
                        # Check for captcha
                        if "captcha" in self.driver.page_source.lower() or "security check" in self.driver.page_source.lower():
                            handle_captcha_error("Facebook", "facebook")
                        else:
                            handle_auth_failure("Facebook", "facebook", "Login verification failed")
                        return False
                except Exception as e:
                    logger.error(f"Login error: {str(e)}")
                    handle_auth_failure("Facebook", "facebook", str(e))
                    return False
            else:
                logger.error("No login credentials provided")
                return False
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return False
    
    def _is_logged_in(self):
        """Check if the user is logged in to Facebook"""
        try:
            # Look for elements that are only visible when logged in
            self.driver.find_element(By.XPATH, "//div[@aria-label='Your profile' or @aria-label='Account' or contains(@aria-label, 'profile')]")
            return True
        except NoSuchElementException:
            return False
    
    def scrape_group(self, group_url, keywords, max_posts=20):
        """
        Scrape a Facebook group for posts containing specified keywords
        
        Args:
            group_url (str): URL of the Facebook group
            keywords (list): List of keywords to search for
            max_posts (int): Maximum number of posts to scrape
            
        Returns:
            list: List of dictionaries containing matched posts
        """
        try:
            if not self.driver:
                self._setup_driver()
                
            if not self._is_logged_in():
                if not self.login():
                    logger.error("Failed to log in to Facebook")
                    return []
            
            # Extract group name from URL for logging
            group_name = group_url.split('/')[-1] if '/' in group_url else group_url
            
            # Navigate to the group
            self.driver.get(group_url)
            logger.info(f"Navigating to Facebook group: {group_url}")
            log_scraper_activity(group_name, "facebook", "navigate", "success")
            
            # Wait for posts to load
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
                )
            except TimeoutException:
                logger.error(f"Timeout waiting for posts to load in group: {group_url}")
                log_scraper_activity(group_name, "facebook", "load_posts", "timeout")
                return []
            
            # Scroll to load more posts
            self._scroll_to_load_posts(max_posts)
            
            # Extract posts
            posts = self._extract_posts()
            log_scraper_activity(group_name, "facebook", "extract_posts", f"found {len(posts)} posts")
            
            # Match posts against keywords
            matched_posts = []
            for post in posts[:max_posts]:
                for keyword in keywords:
                    if self._match_keyword(post['text'], keyword):
                        post['matched_keyword'] = keyword
                        matched_posts.append(post)
                        log_scraper_activity(group_name, "facebook", "match", f"keyword '{keyword}' matched in post {post.get('id', 'unknown')}")
                        break  # Stop checking keywords once a match is found
            
            logger.info(f"Found {len(matched_posts)} posts matching keywords in group: {group_url}")
            return matched_posts
            
        except Exception as e:
            logger.error(f"Error scraping Facebook group {group_url}: {str(e)}")
            log_scraper_activity(group_name if 'group_name' in locals() else "unknown", "facebook", "scrape", f"error: {str(e)}")
            return []
    
    def _scroll_to_load_posts(self, max_posts):
        """Scroll down to load more posts"""
        try:
            posts_found = 0
            max_scrolls = 10  # Limit scrolling to prevent infinite loops
            
            for i in range(max_scrolls):
                # Count current posts
                posts = self.driver.find_elements(By.XPATH, "//div[@role='article']")
                posts_found = len(posts)
                logger.debug(f"Scroll {i+1}/{max_scrolls}: Found {posts_found} posts")
                
                if posts_found >= max_posts:
                    break
                    
                # Scroll down
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)  # Wait for new content to load
        except Exception as e:
            logger.error(f"Error while scrolling: {str(e)}")
    
    def _extract_posts(self):
        """Extract post data from the current page"""
        posts = []
        try:
            post_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']")
            
            for post_element in post_elements:
                try:
                    # Extract post ID from data attributes or URL
                    post_id = ""
                    try:
                        post_link = post_element.find_element(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/permalink/')]")
                        href = post_link.get_attribute("href")
                        post_id_match = re.search(r'/posts/(\d+)|/permalink/(\d+)', href)
                        if post_id_match:
                            post_id = post_id_match.group(1) or post_id_match.group(2)
                    except NoSuchElementException:
                        pass
                    
                    # Extract post URL
                    post_url = ""
                    try:
                        timestamp_element = post_element.find_element(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/permalink/') or contains(@href, '/groups/')]")
                        post_url = timestamp_element.get_attribute("href")
                    except NoSuchElementException:
                        pass
                    
                    # Extract post text
                    post_text = ""
                    try:
                        content_elements = post_element.find_elements(By.XPATH, ".//div[contains(@class, 'userContent') or contains(@data-ad-preview, 'message')]")
                        if not content_elements:
                            content_elements = post_element.find_elements(By.XPATH, ".//div[contains(@dir, 'auto')]")
                        
                        for element in content_elements:
                            element_text = element.text.strip()
                            if element_text and len(element_text) > 10:  # Avoid empty or very short texts
                                post_text = element_text
                                break
                    except Exception:
                        pass
                    
                    # Extract author name
                    author_name = ""
                    try:
                        author_element = post_element.find_element(By.XPATH, ".//h3[contains(@class, 'actor')]//a | .//strong")
                        author_name = author_element.text.strip()
                    except NoSuchElementException:
                        try:
                            author_element = post_element.find_element(By.XPATH, ".//a[@role='link' and contains(@aria-label, '')]")
                            author_name = author_element.text.strip()
                        except NoSuchElementException:
                            pass
                    
                    # Extract post date
                    post_date = None
                    try:
                        date_element = post_element.find_element(By.XPATH, ".//abbr")
                        timestamp = date_element.get_attribute("data-utime")
                        if timestamp:
                            post_date = datetime.fromtimestamp(int(timestamp))
                    except NoSuchElementException:
                        pass
                    
                    # Only add posts with text content
                    if post_text:
                        posts.append({
                            'id': post_id,
                            'url': post_url,
                            'text': post_text,
                            'author': author_name,
                            'date': post_date,
                            'source_type': 'facebook'
                        })
                except Exception as e:
                    logger.error(f"Error extracting post data: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting posts: {str(e)}")
        
        return posts
    
    def _match_keyword(self, text, keyword):
        """Check if text contains the keyword (case insensitive)"""
        if not text or not keyword:
            return False
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Check for exact phrase match
        return keyword_lower in text_lower
    
    def close(self):
        """Close the browser and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
