import os
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import google.generativeai as genai
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class LinkedInBot:
    def __init__(self):
        self.driver = self.setup_driver()
        self.login()

    def setup_driver(self):
        """Sets up the Chrome WebDriver with necessary options."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def random_delay(self, min_delay=1, max_delay=3):
        """Introduce a random delay to mimic human behavior."""
        time.sleep(random.uniform(min_delay, max_delay))

    def login(self):
        """Logs into LinkedIn using credentials from environment variables."""
        self.driver.get("https://www.linkedin.com/login")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")

        # Mimic human typing by sending keys with delays
        for char in os.getenv("LINKEDIN_USERNAME"):
            username_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        for char in os.getenv("LINKEDIN_PASSWORD"):
            password_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        password_field.send_keys(Keys.RETURN)
        self.random_delay(5, 7)

        # Check for verification code input form
        try:
            verification_form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email-pin-challenge"))
            )
            logging.info("Verification code required. Prompting user for input.")
            verification_code = input("Enter the verification code sent to your email: ")

            # Enter the verification code
            code_input = self.driver.find_element(By.ID, "input__email_verification_pin")
            code_input.send_keys(verification_code)

            # Submit the verification form
            submit_button = self.driver.find_element(By.ID, "email-pin-submit-button")
            submit_button.click()

            # Wait for the process to complete and navigate to the feed section
            self.random_delay(10, 12)
            self.driver.get("https://www.linkedin.com/feed/")
            logging.info("Logged in and navigated to the feed section.")
        except Exception as e:
            logging.info("Verification code not required or error occurred.")
            pass

    def remove_markdown(self, text, ignore_hashtags=False):
        """Removes markdown syntax from a given text string."""
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

        # If ignoring hashtags, remove the heading pattern
        if ignore_hashtags:
            patterns.remove(r"(#+)(.*)")

        # Replace markdown elements with an empty string
        for pattern in patterns:
            text = re.sub(
                pattern, r" ", text
            )  

        return text.strip()

    def generate_post_content(self, topic):
        """Generates post content using Gemini AI based on the given topic."""
        logging.info(f"Generating post content for topic: {topic}")
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            client = genai.GenerativeModel("gemini-pro")

            messages = [
                {
                    "role": "user",
                    "parts": [
                        f"Generate a LinkedIn post with a minimum amount of 1000 characters about the following topic and do not forget to add suitable hastags: {topic}. Start with a captivating introduction that grabs the reader's attention. Develop a compelling thesis statement that clearly articulates the main argument of the post and support it with strong evidence and logical reasoning. Ensure the post is engaging, relatable, and structured with clear sections or headings. Include experts experiences, emotions, and specific scenarios or examples that support the topic. Provide detailed case studies or examples showing the impact of this topic in various contexts or industries. Delve into relevant technical aspects or processes if applicable. Support the claims with statistics or data points. Conclude with a call to action that encourages readers to learn more or take specific steps related to the topic. The post should read like it was written by a human and resonate with the readers."
                    ],
                }
            ]

            post_response = client.generate_content(messages)

            if post_response.text:
                post_text = self.remove_markdown(
                    post_response.text, ignore_hashtags=True
                )
            else:
                post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"
        except Exception as e:
            logging.error("Failed to generate post content.", exc_info=True)
            post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"

        return post_text

    def close_overlapping_elements(self):
        try:
            # Close chat overlay
            chat_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'msg-overlay-bubble-header__control--close')]")
            chat_overlay_close_button.click()
            self.random_delay()
        except Exception as e:
            logging.info("No chat overlay to close.")

        try:
            # Close any other notification or modal
            notification_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]")
            notification_overlay_close_button.click()
            self.random_delay()
        except Exception as e:
            logging.info("No notification or modal overlay to close.")


    def post_to_linkedin(self, post_text):
        """Posts the generated content to LinkedIn."""
        logging.info("Posting to LinkedIn.")
        try:
            # Close overlapping elements
            self.close_overlapping_elements()

            # Wait for the "Start a post" button to be clickable and click it using JavaScript
            start_post_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start a post')]"))
            )

            self.driver.execute_script("arguments[0].click();", start_post_button)

            # Wait a moment for animation or modal dialogs to appear
            time.sleep(2)

            # Assuming the text area for the post becomes visible after clicking the button:
            post_text_area = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
            )

            # Click the text area to focus and start typing a post
            post_text_area.click()
            self.driver.execute_script(
                "arguments[0].innerText = arguments[1];", post_text_area, post_text
            )

            # Optionally, you can search for the 'Post' button and click it to publish
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'share-actions__primary-action')]",
                    )
                )
            )
            self.driver.execute_script("arguments[0].click();", post_button)

            logging.info("Post successful.")
            return True
        except Exception as e:
            logging.error("Failed to post to LinkedIn.", exc_info=True)
            return False

    def process_topics(self):
        """Processes the first topic from Topics.txt, posts it to LinkedIn, and updates the files accordingly."""
        try:
            with open("Topics.txt", "r") as file:
                topics = file.readlines()

            if not topics:
                logging.info("No topics to process.")
                return

            # Get the first topic
            topic = topics[0].strip()
            if not topic:
                logging.info("The first topic is empty.")
                return

            post_text = self.generate_post_content(topic)
            if self.post_to_linkedin(post_text):
                with open("Topics_done.txt", "a") as done_file:
                    done_file.write(topic + "\n")
                logging.info(f"Topic posted and saved to Topics_done.txt: {topic}")

                # Remove the posted topic from Topics.txt
                with open("Topics.txt", "w") as file:
                    file.writelines(topics[1:])
                logging.info("First topic removed from Topics.txt.")
            else:
                logging.info(f"Failed to post topic: {topic}")
            self.random_delay(5, 10)

        except Exception as e:
            logging.error("An error occurred while processing topics.", exc_info=True)

if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        bot.process_topics()
        time.sleep(5)
    finally:
        bot.driver.quit()
        logging.info("Driver session ended cleanly.")

# import os
# import re
# import time
# import random
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from dotenv import load_dotenv
# import google.generativeai as genai
# import logging

# load_dotenv()

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )


# class LinkedInBot:
#     """
#     A class representing a bot for interacting with LinkedIn, capable of liking posts,
#     commenting based on sentiment analysis and content relevance, and navigating LinkedIn's interface.
#     """

#     def __init__(self):
#         self.driver = self.setup_driver()
#         self.login()

#     def setup_driver(self):
#         """Sets up the Chrome WebDriver with necessary options."""
#         chrome_options = Options()
#         chrome_options.add_argument("--no-sandbox")
#         chrome_options.add_argument("--disable-dev-shm-usage")
#         chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#         # chrome_options.add_argument("--headless") 
#         chrome_options.add_argument("start-maximized")
#         chrome_options.add_argument("disable-infobars")
#         chrome_options.add_argument("--disable-extensions")
#         chrome_options.add_argument(
#             "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
#         )
#         service = Service(ChromeDriverManager().install())
#         driver = webdriver.Chrome(service=service, options=chrome_options)
#         driver.execute_script(
#             "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
#         )
#         return driver

#     def random_delay(self, min_delay=1, max_delay=3):
#         """Introduce a random delay to mimic human behavior."""
#         time.sleep(random.uniform(min_delay, max_delay))

#     def login(self):
#         """Logs into LinkedIn using credentials from environment variables."""
#         self.driver.get("https://www.linkedin.com/login")
#         WebDriverWait(self.driver, 10).until(
#             EC.presence_of_element_located((By.ID, "username"))
#         )

#         username_field = self.driver.find_element(By.ID, "username")
#         password_field = self.driver.find_element(By.ID, "password")

#         # Mimic human typing by sending keys with delays
#         for char in os.getenv("LINKEDIN_USERNAME"):
#             username_field.send_keys(char)
#             self.random_delay(0.1, 0.3)
#         self.random_delay()

#         for char in os.getenv("LINKEDIN_PASSWORD"):
#             password_field.send_keys(char)
#             self.random_delay(0.1, 0.3)
#         self.random_delay()

#         password_field.send_keys(Keys.RETURN)
#         self.random_delay(5, 7)


#     def remove_markdown(self, text, ignore_hashtags=False):
#         """
#         Removes markdown syntax from a given text string.

#         Args:
#             text: The text string potentially containing markdown syntax.
#             ignore_hashtags: Boolean flag to ignore hashtags while removing markdown.

#         Returns:
#             The text string with markdown syntax removed.
#         """

#         patterns = [
#             r"(\*{1,2})(.*?)\1",  # Bold and italics
#             r"\[(.*?)\]\((.*?)\)",  # Links
#             r"`(.*?)`",  # Inline code
#             r"(\n\s*)- (.*)",  # Unordered lists (with `-`)
#             r"(\n\s*)\* (.*)",  # Unordered lists (with `*`)
#             r"(\n\s*)[0-9]+\. (.*)",  # Ordered lists
#             r"(#+)(.*)",  # Headings
#             r"(>+)(.*)",  # Blockquotes
#             r"(---|\*\*\*)",  # Horizontal rules
#             r"!\[(.*?)\]\((.*?)\)",  # Images
#         ]

#         # If ignoring hashtags, remove the heading pattern
#         if ignore_hashtags:
#             patterns.remove(r"(#+)(.*)")

#         # Replace markdown elements with an empty string
#         for pattern in patterns:
#             text = re.sub(
#                 pattern, r" ", text
#             )  
#             # Extracts the inner content (group 2) if available

#         return text.strip()

#     def generate_post_content(self, topic):
#         """Generates post content using Gemini AI based on the given topic."""
#         logging.info(f"Generating post content for topic: {topic}")
#         try:
#             genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
#             client = genai.GenerativeModel("gemini-pro")

#             messages = [
#                 {
#                     "role": "user",
#                     "parts": [
#                         f"Generate a LinkedIn post with a minimum amount of 1000 characters about the following topic and do not forget to add suitable hastags: {topic}. Start with a captivating introduction that grabs the reader's attention. Develop a compelling thesis statement that clearly articulates the main argument of the post and support it with strong evidence and logical reasoning. Ensure the post is engaging, relatable, and structured with clear sections or headings. Include experts experiences, emotions, and specific scenarios or examples that support the topic. Provide detailed case studies or examples showing the impact of this topic in various contexts or industries. Delve into relevant technical aspects or processes if applicable. Support the claims with statistics or data points. Conclude with a call to action that encourages readers to learn more or take specific steps related to the topic. The post should read like it was written by a human and resonate with the readers."

#                     ],
#                 }
#             ]

#             post_response = client.generate_content(messages)

#             if post_response.text:
#                 post_text = self.remove_markdown(
#                     post_response.text, ignore_hashtags=True
#                 )
#             else:
#                 post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"
#         except Exception as e:
#             logging.error("Failed to generate post content.", exc_info=True)
#             post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"

#         return post_text

#     def post_to_linkedin(self, post_text):
#         """Posts the generated content to LinkedIn."""
#         logging.info("Posting to LinkedIn.")
#         try:
#             # Wait for the "Start a post" button to be clickable and click it
#             start_post_button = WebDriverWait(self.driver, 20).until(
#                 EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start a post')]"))
#             )

#             start_post_button.click()

#             # Wait a moment for animation or modal dialogs to appear
#             time.sleep(2)

#             # Assuming the text area for the post becomes visible after clicking the button:
#             post_text_area = WebDriverWait(self.driver, 10).until(
#                 EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
#             )

#             # Click the text area to focus and start typing a post
#             post_text_area.click()
#             self.driver.execute_script(
#                 "arguments[0].innerText = arguments[1];", post_text_area, post_text
#             )

#             # Optionally, you can search for the 'Post' button and click it to publish
#             post_button = WebDriverWait(self.driver, 10).until(
#                 EC.element_to_be_clickable(
#                     (
#                         By.XPATH,
#                         "//button[contains(@class, 'share-actions__primary-action')]",
#                     )
#                 )
#             )
#             post_button.click()

#             logging.info("Post successful.")
#             return True
#         except Exception as e:
#             logging.error("Failed to post to LinkedIn.", exc_info=True)
#             return False

#     def process_topics(self):
#         """Processes the first topic from Topics.txt, posts it to LinkedIn, and updates the files accordingly."""
#         try:
#             with open("Topics.txt", "r") as file:
#                 topics = file.readlines()

#             if not topics:
#                 logging.info("No topics to process.")
#                 return

#             # Get the first topic
#             topic = topics[0].strip()
#             if not topic:
#                 logging.info("The first topic is empty.")
#                 return

#             post_text = self.generate_post_content(topic)
#             print(post_text)
#             if self.post_to_linkedin(post_text):
#                 with open("Topics_done.txt", "a") as done_file:
#                     done_file.write(topic + "\n")
#                 logging.info(f"Topic posted and saved to Topics_done.txt: {topic}")

#                 # Remove the posted topic from Topics.txt
#                 with open("Topics.txt", "w") as file:
#                     file.writelines(topics[1:])
#                 logging.info("First topic removed from Topics.txt.")
#             else:
#                 logging.info(f"Failed to post topic: {topic}")
#             self.random_delay(5, 10)

#         except Exception as e:
#             logging.error("An error occurred while processing topics.", exc_info=True)


# if __name__ == "__main__":
#     bot = LinkedInBot()
#     try:
#         bot.process_topics()
#         time.sleep(5)
#     finally:
#         time.sleep(50)
#         bot.driver.quit()  # Ensure the driver is quit properly
#         logging.info("Driver session ended cleanly.")
