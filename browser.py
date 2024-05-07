import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import google.generativeai as genai
import logging
import traceback
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

 
class LinkedInBot:
    """
    A class representing a bot for interacting with LinkedIn, capable of liking posts,
    commenting based on sentiment analysis and content relevance, and navigating LinkedIn's interface.

    Attributes:
        driver (webdriver.Chrome): The Selenium driver to interact with a web browser.
        posts_data (list): A list of dictionaries containing data for each post.
    """

    def __init__(self):
        self.driver = self.setup_driver()
        self.login()
        
        self.posts_data = []

    def setup_driver(self):
        """Sets up the Chrome WebDriver with necessary options."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def login(self):
        """Logs into LinkedIn using credentials from environment variables."""
        self.driver.get("https://www.linkedin.com/login")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(os.getenv('LINKEDLN_USERNAME'))
        self.driver.find_element(By.ID, "password").send_keys(os.getenv('LINKEDLN_PASSWORD'))
        self.driver.find_element(By.ID, "password").send_keys(Keys.RETURN)
        time.sleep(5)  
        logging.info("Logged in and session started.")
        self.refresh_page()
        
    def refresh_page(self):
        logging.info("Refreshing the current page.")
        self.driver.refresh()

    def fetch_and_store_content(self):
        logging.info("Fetching and storing content from LinkedIn posts.")
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-id]")
            for post in posts:
                post_id = post.get_attribute('data-id')
                post_html = post.get_attribute('outerHTML')
                self.posts_data.append({'id': post_id, 'html': post_html})
            logging.info(f"Content fetched for {len(self.posts_data)} posts.")
        except Exception as e:
            logging.error("Failed to fetch and store content.", exc_info=True)
            
    def remove_markdown(self, text):
        """
        Removes markdown syntax from a given text string.

        Args:
            text: The text string potentially containing markdown syntax.

        Returns:
            The text string with markdown syntax removed.
        """

        patterns = [
            r"(\*{1,2})(.*?)\1",  # Bold and italics
            r"\[(.*?)\]\((.*?)\)",  # Links
            r"`(.*?)`",  # Inline code
            r"(\n\s*)- (.*)",  # Unordered lists (with `-`)
            r"(\n\s*)\* (.*)",  # Unordered lists (with `*`)
            r"(\n\s*)[0-9]+\. (.*)",  # Ordered lists
            r"(#+)(.*)",  # Headings
            r"(>+)(.*)",  # Blockquotes
            r"(---|\*\*\*)",  # Horizontal rules
            r"!\[(.*?)\]\((.*?)\)",  # Images
        ]

        # Replace markdown elements with an empty string
        for pattern in patterns:
            text = re.sub(pattern, r" ", text)  # Extracts the inner content (group 2) if available

        return text.strip()

    def comment_on_post(self, post, comment_text):
        logging.info(f"Attempting to comment on post {post['id']}.")
        try:
            comment_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@data-id='{post['id']}']//button[contains(@aria-label, 'Comment')]"))
            )
            ActionChains(self.driver).move_to_element(comment_button).perform()  # Ensures the button is in view
            comment_button.click()
            comment_input = WebDriverWait(self.driver, 22).until(
                EC.visibility_of_element_located((By.XPATH, f"//div[@data-id='{post['id']}']//div[@role='textbox']"))
            )
            self.driver.execute_script("arguments[0].innerText = arguments[1];", comment_input, comment_text.strip('"'))
            post_comment_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@data-id='{post['id']}']//button[contains(@class, 'comments-comment-box__submit-button') and .//span[text()='Post']]"))
            )
            post_comment_button.click()
            logging.info(f"Comment posted successfully on post {post['id']}.")
        except Exception as e:
            logging.error(f"Failed to comment on post {post['id']}: {str(e)}", exc_info=True)
            
    def like_post(self, post):
        logging.info(f"Attempting to like post {post['id']}.")
        try:
            like_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@data-id='{post['id']}']//button[contains(@aria-label, 'Like')]"))
            )

            # Scroll to the "Like" button to ensure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", like_button)

            # Click the button via JavaScript if interception is detected
            if like_button.get_attribute('aria-pressed') == 'false':
                try:
                    like_button.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", like_button)

                logging.info(f"Post {post['id']} liked successfully!")
                time.sleep(5)  # Pause to simulate user behavior and avoid rapid-fire actions
        except TimeoutException:
            logging.error(f"Failed to find or click the Like button for post {post['id']} within the timeout period.")
        except Exception as e:
            logging.error(f"Failed to like post {post['id']}: {str(e)}", exc_info=True)
            

    def generate_comment_based_on_content(self, post_text):
        logging.info("Generating comment based on content analysis.")
        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            client = genai.GenerativeModel('gemini-pro')
            messages = [{'role': 'user', 'parts': [f"Please generate your professional and insightful thought about the following LinkedIn post in such a way that one cannot tell it was generated by an AI: {post_text}"]}]
            comment_response = client.generate_content(messages)
            return comment_response.text if comment_response.text else "Speechless right now"
        except Exception as e:
            logging.error("Failed to generate a comment.", exc_info=True)
            return None
    
    def analyze_and_interact(self):
        """Analyzes the fetched content and decides on interactions based on its sentiment and relevance."""
        for post in self.posts_data:
            post_text = BeautifulSoup(post['html'], 'html.parser').text.strip()
            if len(post_text) > 220:
                ai_content = self.generate_comment_based_on_content(post_text).strip('"')
                comment_text = self.remove_markdown(ai_content)
                print(f"\n\n Comment Text: {comment_text} \n\n")
                if comment_text:
                    self.comment_on_post(post, comment_text)
                else:
                    print("Failed to generate a comment.")
                    pass
            self.like_post(post)

    def function_to_make_a_post(self):
        # Wait for the "Start a post" button to be clickable and click it
        start_post_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ember2222"))
        )
        start_post_button.click()

        # Wait a moment for animation or modal dialogs to appear
        time.sleep(2)

        # Assuming the text area for the post becomes visible after clicking the button:
        # Locate the text area where you would enter your post content
        # Note: The actual selector might vary, so you need to inspect the element after clicking 'Start a post'
        post_text_area = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
        )

        # Click the text area to focus and start typing a post
        post_text_area.click()
        post_text_area.send_keys("Excited to share that I'm experimenting with automating LinkedIn posts using Selenium and Python! #automation #python #selenium")

        # Optionally, you can search for the 'Post' button and click it to publish
        post_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'share-actions__primary-action')]"))
        )
        post_button.click()
 

if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        bot.fetch_and_store_content()
        bot.analyze_and_interact()
        time.sleep(5)  
    finally:
        bot.driver.quit()  # Ensure the driver is quit properly
        logging.info("Driver session ended cleanly.")

