"""
main.py
Entry point for the Chitim course-enrollment automation agent.

Flow:
  1. Poll IMAP inbox for purchase-confirmation emails from support@grow.security.
  2. For each matching email:
       a. Create a WordPress user (username = part before @ in purchaser's email).
       b. Enroll the user in the course.
       c. Save a draft reply with the credentials.
  3. Sleep and repeat.
"""

import logging
import os
import time

from dotenv import load_dotenv

from email_monitor import fetch_new_purchase_emails, create_draft
from wordpress_agent import WordPressAgent

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "mail.zahav.net.il")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

WP_ADMIN_URL = os.getenv("WP_ADMIN_URL", "https://meshek.chitim.co.il/wp-admin")
WP_ADMIN_USER = os.getenv("WP_ADMIN_USER", "")
WP_ADMIN_PASSWORD = os.getenv("WP_ADMIN_PASSWORD", "")

NEW_USER_PASSWORD = os.getenv("NEW_USER_PASSWORD", "1234")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _check_config() -> bool:
    required = {
        "EMAIL_ADDRESS": EMAIL_ADDRESS,
        "EMAIL_PASSWORD": EMAIL_PASSWORD,
        "WP_ADMIN_USER": WP_ADMIN_USER,
        "WP_ADMIN_PASSWORD": WP_ADMIN_PASSWORD,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return False
    return True


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------
def process_email(record: dict, agent: WordPressAgent) -> None:
    username = record["username"]
    purchaser_email = record["purchaser_email"]

    logger.info("=== Processing purchase for %s ===", purchaser_email)

    # Step 1: Create WordPress user
    logger.info("Step 1/3 – Creating WP user '%s' …", username)
    user_created = agent.create_user(
        username=username,
        email=purchaser_email,
        password=NEW_USER_PASSWORD,
    )
    if not user_created:
        logger.error("User creation failed for '%s'. Skipping enrollment.", username)
        return

    # Step 2: Enroll in course
    logger.info("Step 2/3 – Enrolling '%s' in course …", username)
    enrolled = agent.enroll_student(username=username)
    if not enrolled:
        logger.error("Enrollment failed for '%s'.", username)
        # Still attempt to send credentials even if enrollment failed
    else:
        logger.info("Enrollment successful for '%s'.", username)

    # Step 3: Create draft email with credentials
    logger.info("Step 3/3 – Creating draft email for %s …", purchaser_email)
    draft_ok = create_draft(
        imap_host=IMAP_HOST,
        imap_port=IMAP_PORT,
        email_address=EMAIL_ADDRESS,
        email_password=EMAIL_PASSWORD,
        to_address=purchaser_email,
        username=username,
        password=NEW_USER_PASSWORD,
    )
    if draft_ok:
        logger.info("Draft email saved for %s.", purchaser_email)
    else:
        logger.warning("Draft email could not be saved for %s.", purchaser_email)

    logger.info("=== Done with %s ===", purchaser_email)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run() -> None:
    if not _check_config():
        raise SystemExit(1)

    agent = WordPressAgent(
        admin_url=WP_ADMIN_URL,
        admin_user=WP_ADMIN_USER,
        admin_password=WP_ADMIN_PASSWORD,
        headless=True,
    )

    logger.info(
        "Agent started. Checking email every %d seconds. Press Ctrl+C to stop.",
        CHECK_INTERVAL,
    )

    while True:
        try:
            logger.info("Checking inbox …")
            records = fetch_new_purchase_emails(
                imap_host=IMAP_HOST,
                imap_port=IMAP_PORT,
                email_address=EMAIL_ADDRESS,
                email_password=EMAIL_PASSWORD,
            )

            if not records:
                logger.info("No new purchase emails found.")
            else:
                for record in records:
                    try:
                        process_email(record, agent)
                    except Exception as exc:
                        logger.exception(
                            "Unhandled error processing email UID %s: %s",
                            record.get("uid"),
                            exc,
                        )

        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception as exc:
            logger.exception("Unexpected error in main loop: %s", exc)

        logger.info("Sleeping %d seconds …", CHECK_INTERVAL)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
