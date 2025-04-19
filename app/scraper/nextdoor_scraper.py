import os
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

from app.config.settings import BROWSER_HEADLESS, NEXTDOOR_EMAIL, NEXTDOOR_PASSWORD, NEXTDOOR_COOKIES

# Configure logger
logger = logging.getLogger(__name__)

class NextdoorScraper:
    """
    Scraper for Nextdoor neighborhoods to extract posts and check for keywords
    """
    
    def __init__(self, headless=BROWSER_HEADLESS):
        """Initialize the Nextdoor scraper with browser options"""
        self.headless = headless
        self.driver = None
        self.cookies_file = os.path.join(os.path.dirname(__file__), '..', '..', 'nextdoor_cookies.json')
        
    def _setup_driver(self):
        """Set up and configure the Selenium WebDriver"""
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
        
    def _load_cookies(self):
        """Load Nextdoor cookies from file if available"""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                # Add cookies to browser
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                
                logger.info("Loaded Nextdoor cookies from file")
                return True
            except Exception as e:
                logger.error(f"Error loading cookies: {str(e)}")
        
        return False
    
    def _save_cookies(self):
        """Save Nextdoor cookies to file for future use"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info("Saved Nextdoor cookies to file")
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")
    
    def login(self):
        """Log in to Nextdoor using credentials or cookies"""
        if not self.driver:
            self._setup_driver()
        
        self.driver.get('https://nextdoor.com/login')
        
        # Try to use cookies first
        if NEXTDOOR_COOKIES:
            try:
                cookies = json.loads(NEXTDOOR_COOKIES)
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
        if NEXTDOOR_EMAIL and NEXTDOOR_PASSWORD:
            try:
                # Find email field and enter email
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "id_email"))
                )
                email_field.send_keys(NEXTDOOR_EMAIL)
                
                # Click continue button
                continue_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_button.click()
                
                # Wait for password field to appear
                password_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "id_password"))
                )
                password_field.send_keys(NEXTDOOR_PASSWORD)
                
                # Click login button
                login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
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
                    return False
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                return False
        else:
            logger.error("No login credentials provided")
            return False
    
    def _is_logged_in(self):
        """Check if the user is logged in to Nextdoor"""
        try:
            # Look for elements that are only visible when logged in
            self.driver.find_element(By.XPATH, "//div[contains(@class, 'user-profile')]//img | //button[contains(@aria-label, 'User menu')]")
            return True
        except NoSuchElementException:
            return False
    
    def scrape_neighborhood(self, neighborhood_url, keywords, max_posts=20):
        """
        Scrape a Nextdoor neighborhood for posts containing specified keywords
        
        Args:
            neighborhood_url (str): URL of the Nextdoor neighborhood
            keywords (list): List of keywords to search for
            max_posts (int): Maximum number of posts to scrape
            
        Returns:
            list: List of dictionaries containing matched posts
        """
        if not self.driver:
            self._setup_driver()
            
        if not self._is_logged_in():
            if not self.login():
                logger.error("Failed to log in to Nextdoor")
                return []
        
        # Navigate to the neighborhood
        self.driver.get(neighborhood_url)
        logger.info(f"Navigating to Nextdoor neighborhood: {neighborhood_url}")
        
        # Wait for posts to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'post-list-item')]"))
            )
        except TimeoutException:
            logger.error(f"Timeout waiting for posts to load in neighborhood: {neighborhood_url}")
            return []
        
        # Scroll to load more posts
        self._scroll_to_load_posts(max_posts)
        
        # Extract posts
        posts = self._extract_posts()
        
        # Match posts against keywords
        matched_posts = []
        for post in posts[:max_posts]:
            for keyword in keywords:
                if self._match_keyword(post['text'], keyword):
                    post['matched_keyword'] = keyword
                    matched_posts.append(post)
                    break  # Stop checking keywords once a match is found
        
        logger.info(f"Found {len(matched_posts)} posts matching keywords in neighborhood: {neighborhood_url}")
        return matched_posts
    
    def _scroll_to_load_posts(self, max_posts):
        """Scroll down to load more posts"""
        posts_found = 0
        max_scrolls = 10  # Limit scrolling to prevent infinite loops
        
        for _ in range(max_scrolls):
            # Count current posts
            posts = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'post-list-item')]")
            posts_found = len(posts)
            
            if posts_found >= max_posts:
                break
                
            # Scroll down
            self.driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)  # Wait for new content to load
    
    def _extract_posts(self):
        """Extract post data from the current page"""
        posts = []
        post_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'post-list-item')]")
        
        for post_element in post_elements:
            try:
                # Extract post ID from data attributes or URL
                post_id = ""
                try:
                    post_link = post_element.find_element(By.XPATH, ".//a[contains(@href, '/post/')]")
                    href = post_link.get_attribute("href")
                    post_id_match = re.search(r'/post/(\d+)', href)
                    if post_id_match:
                        post_id = post_id_match.group(1)
                except NoSuchElementException:
                    pass
                
                # Extract post URL
                post_url = ""
                try:
                    post_link = post_element.find_element(By.XPATH, ".//a[contains(@href, '/post/')]")
                    post_url = post_link.get_attribute("href")
                except NoSuchElementException:
                    pass
                
                # Extract post text
                post_text = ""
                try:
                    content_elements = post_element.find_elements(By.XPATH, ".//div[contains(@class, 'post-content')]")
                    
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
                    author_element = post_element.find_element(By.XPATH, ".//div[contains(@class, 'post-byline')]//a")
                    author_name = author_element.text.strip()
                except NoSuchElementException:
                    pass
                
                # Extract post date
                post_date = None
                try:
                    date_element = post_element.find_element(By.XPATH, ".//div[contains(@class, 'post-byline')]//time")
                    date_text = date_element.get_attribute("datetime") or date_element.text
                    if date_text:
                        # Try to parse the date text
                        try:
                            post_date = datetime.strptime(date_text, "%Y-%m-%dT%H:%M:%S.%fZ")
                        except ValueError:
                            # Handle relative dates like "2 hours ago"
                            pass
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
                        'source_type': 'nextdoor'
                    })
            except Exception as e:
                logger.error(f"Error extracting post data: {str(e)}")
        
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
            self.driver.quit()
            self.driver = None
