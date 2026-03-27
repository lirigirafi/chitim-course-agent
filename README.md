# Chitim Course Enrollment Agent

Automated agent that monitors an email inbox, creates a WordPress user, enrolls them in a course, and saves a draft reply — all triggered by a purchase-confirmation email.

---

## What it does

1. **Polls IMAP** (`chitim@zahav.net.il`) for unread emails from `support@grow.security`.
2. **Checks** whether the email body contains the phrase:
   > רכישת כניסה לקורס הגינון האקולוגי מורחב
3. **Extracts** the purchaser's email address from the email body and derives a username (everything before `@`).
4. **Creates a WordPress user** at `meshek.chitim.co.il/wp-admin/user-new.php` with password `1234`.
5. **Enrolls the user** in *קורס גינון אקולוגי מורחב* via the WP admin enrollment page.
6. **Saves a draft email** to the IMAP Drafts folder addressed to the purchaser with their login credentials.

---

## Requirements

- Python 3.11+
- A running Chromium-compatible browser (installed automatically by Playwright)

---

## Installation

```bash
# 1. Clone / navigate to the project folder
cd chitim-course-agent

# 2. Create a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (only needed once)
playwright install chromium
```

---

## Configuration

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `IMAP_HOST` | IMAP server hostname (default: `mail.zahav.net.il`) |
| `IMAP_PORT` | IMAP SSL port (default: `993`) |
| `SMTP_HOST` | SMTP server hostname (default: `smtp.zahav.net.il`) |
| `SMTP_PORT` | SMTP SSL port (default: `465`) |
| `EMAIL_ADDRESS` | Full email address (`chitim@zahav.net.il`) |
| `EMAIL_PASSWORD` | Email account password |
| `WP_ADMIN_URL` | WordPress admin base URL |
| `WP_ADMIN_USER` | WordPress admin username |
| `WP_ADMIN_PASSWORD` | WordPress admin password |
| `NEW_USER_PASSWORD` | Default password for new users (default: `1234`) |
| `CHECK_INTERVAL` | Seconds between inbox checks (default: `300`) |

---

## Running the agent

```bash
python main.py
```

The agent runs in a loop, checking the inbox every `CHECK_INTERVAL` seconds.
Press **Ctrl+C** to stop.

---

## Project structure

```
chitim-course-agent/
├── main.py              # Entry point and main loop
├── email_monitor.py     # IMAP polling, phrase detection, draft creation
├── wordpress_agent.py   # Playwright automation (user creation + enrollment)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| IMAP login fails | Verify `EMAIL_ADDRESS` / `EMAIL_PASSWORD` and that IMAP is enabled for the account |
| WP login fails | Check `WP_ADMIN_USER` / `WP_ADMIN_PASSWORD` and that the admin URL is correct |
| "Confirm weak password" not clicked | This is handled automatically; if it still fails, set a stronger default password in `.env` |
| Enrollment selectors not matching | The enrollment page selectors depend on the installed WP plugin. Open `wordpress_agent.py → enroll_student()` and adjust the CSS selectors to match the actual page HTML |
| Draft not saved | Some IMAP providers use non-standard Drafts folder names. The agent tries `Drafts`, `INBOX.Drafts`, and `[Gmail]/Drafts` automatically |

---

## Logs

All activity is printed to stdout with timestamps. Redirect to a file if needed:

```bash
python main.py >> agent.log 2>&1
```
