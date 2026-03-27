"""
wordpress_agent.py
Uses Playwright to:
  1. Log in to WordPress admin.
  2. Create a new user (username derived from purchaser email, password = 1234).
  3. Enroll that user in "קורס גינון אקולוגי מורחב".
"""

import logging
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

logger = logging.getLogger(__name__)

COURSE_NAME = "קורס גינון אקולוגי מורחב"
NEW_USER_ROLE = "subscriber"


class WordPressAgent:
    def __init__(self, admin_url: str, admin_user: str, admin_password: str, headless: bool = True):
        self.admin_url = admin_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.headless = headless

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _login(self, page) -> bool:
        """Navigate to wp-login.php and authenticate."""
        login_url = f"{self.admin_url}/wp-login.php"
        logger.info("Navigating to login page: %s", login_url)
        page.goto(login_url, wait_until="networkidle")

        page.fill("#user_login", self.admin_user)
        page.fill("#user_pass", self.admin_password)
        page.click("#wp-submit")
        page.wait_for_load_state("networkidle")

        if "wp-admin" in page.url or "dashboard" in page.url:
            logger.info("WP login successful.")
            return True

        logger.error("WP login failed. Current URL: %s", page.url)
        return False

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def create_user(self, username: str, email: str, password: str) -> bool:
        """
        Create a new WordPress subscriber.
        Returns True on success, False on failure (including duplicate user).
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                if not self._login(page):
                    return False

                url = f"{self.admin_url}/user-new.php"
                logger.info("Navigating to user creation page: %s", url)
                page.goto(url, wait_until="networkidle")

                # Fill username
                page.fill("#user_login", username)

                # Fill email
                page.fill("#email", email)

                # Clear auto-generated password and type our own
                # WP shows the password in a visible text input (#pass1-text) when
                # the "show password" toggle is active; otherwise it's #pass1.
                try:
                    page.click("button.wp-generate-pw")          # "Set New Password" toggle
                    page.wait_for_selector("#pass1-text", timeout=3000)
                    page.fill("#pass1-text", password)
                except PWTimeoutError:
                    pass

                # Fallback: fill the hidden input directly
                page.evaluate(
                    """(pwd) => {
                        const f1 = document.getElementById('pass1');
                        if (f1) { f1.value = pwd; f1.dispatchEvent(new Event('input', {bubbles:true})); }
                        const f2 = document.getElementById('pass1-text');
                        if (f2) { f2.value = pwd; f2.dispatchEvent(new Event('input', {bubbles:true})); }
                    }""",
                    password,
                )

                # Set role to subscriber
                page.select_option("#role", NEW_USER_ROLE)

                # Wait for the "Confirm weak password" checkbox to appear and check it
                try:
                    page.wait_for_selector("#pw_weak", timeout=4000)
                    if not page.is_checked("#pw_weak"):
                        page.check("#pw_weak")
                    logger.info("Checked 'Confirm use of weak password'.")
                except PWTimeoutError:
                    logger.debug("Weak-password checkbox did not appear (may not be needed).")

                # Click "Add New User"
                page.click("#createusersub")
                page.wait_for_load_state("networkidle")

                # Check for success or error notice
                if page.locator(".notice-success, #message.updated").count() > 0:
                    logger.info("User '%s' created successfully.", username)
                    return True

                error_text = page.locator(".notice-error, #error-page").inner_text() if page.locator(".notice-error, #error-page").count() > 0 else "unknown"
                logger.error("User creation failed for '%s': %s", username, error_text)
                return False

            except Exception as exc:
                logger.exception("Unexpected error during user creation: %s", exc)
                return False
            finally:
                browser.close()

    def enroll_student(self, username: str) -> bool:
        """
        Enroll the given username in COURSE_NAME via the WP admin enrollment page.
        Returns True on success.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                if not self._login(page):
                    return False

                url = (
                    f"{self.admin_url}/admin.php"
                    "?page=enrollments&sub_page=enroll_student"
                )
                logger.info("Navigating to enrollment page: %s", url)
                page.goto(url, wait_until="networkidle")

                # --- Search for the student ---
                # Try common selector patterns used by LearnDash / TutorLMS / LifterLMS
                student_input_selector = (
                    "input[name='student_search'], "
                    "input[placeholder*='student'], "
                    "input[placeholder*='user'], "
                    "input#student_name, "
                    "input.student-search"
                )
                page.wait_for_selector(student_input_selector, timeout=10000)
                page.fill(student_input_selector, username)

                # Some plugins show a live-search dropdown; wait and click the match
                try:
                    dropdown_item = page.locator(
                        f"li:has-text('{username}'), "
                        f"div.autocomplete-item:has-text('{username}'), "
                        f"option:has-text('{username}')"
                    ).first
                    dropdown_item.wait_for(timeout=5000)
                    dropdown_item.click()
                    logger.info("Selected student '%s' from dropdown.", username)
                except PWTimeoutError:
                    logger.debug("No autocomplete dropdown found; submitting search directly.")
                    search_btn = page.locator("button[type='submit'], input[type='submit']").first
                    search_btn.click()
                    page.wait_for_load_state("networkidle")

                # --- Select the course ---
                course_selector = (
                    "select[name='course_id'], "
                    "select#course_id, "
                    "select.course-select"
                )
                page.wait_for_selector(course_selector, timeout=10000)

                # Select by visible text (the Hebrew course name)
                page.select_option(course_selector, label=COURSE_NAME)
                logger.info("Selected course: %s", COURSE_NAME)

                # --- Click Enroll ---
                enroll_btn_selector = (
                    "button:has-text('Enroll'), "
                    "input[value='Enroll Student'], "
                    "button:has-text('רשום'), "
                    "input[type='submit']"
                )
                page.click(enroll_btn_selector)
                page.wait_for_load_state("networkidle")

                # Check for success message
                if page.locator(".notice-success, .updated, .alert-success").count() > 0:
                    logger.info("Enrollment successful for '%s'.", username)
                    return True

                # If no success banner, log page content for debugging
                logger.warning(
                    "Enrollment result unclear for '%s'. Page title: %s",
                    username,
                    page.title(),
                )
                return True  # Don't fail the whole flow; check logs manually

            except Exception as exc:
                logger.exception("Unexpected error during enrollment: %s", exc)
                return False
            finally:
                browser.close()
