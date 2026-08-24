"""
Central place for every environment variable / constant the app reads.
Nothing else in the codebase should call os.getenv() directly — import from
here instead, so there's exactly one place to check when adding a new
setting or debugging a missing config value.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LINE Official Account ---
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# --- Gemini ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# --- DeepSeek / OpenRouter (for chat fallback or non-Gemini primary) ---
# For "free-style" usage, many teams use OpenRouter-compatible endpoints.
# Set LLM_PROVIDER=deepseek and fill DEEPSEEK_API_KEY.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://openrouter.ai/api/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "openrouter/free")
DEEPSEEK_SITE_URL = os.getenv("DEEPSEEK_SITE_URL", "")
DEEPSEEK_APP_NAME = os.getenv("DEEPSEEK_APP_NAME", "greenman-line-agent")

# --- dh-task (klive-tasks) ---
KLIVE_API_URL = os.getenv("KLIVE_API_URL", "https://tasks.dohome.technology/api")
KLIVE_TASKS_API_URL = os.getenv("KLIVE_TASKS_API_URL", "https://tasks.dohome.technology/api")
KLIVE_API_TOKEN = os.getenv("KLIVE_API_TOKEN", "")

# --- Self-identity ---
# Resolved to a dh-task user_id whenever the LINE user refers to themselves.
SELF_EMAIL = os.getenv("SELF_EMAIL", "wirun.pin@dohome.co.th")

# --- Access control (admin-approval gate) ---
# The LINE userId of the admin who approves/denies new users. Required for
# the approval flow to have somewhere to send notifications. Get this from
# LINE Official Account Manager > Settings > Messaging API, or by having the
# admin message the bot once and reading event.source.user_id from the logs.
ADMIN_LINE_USER_ID = os.getenv("ADMIN_LINE_USER_ID", "")

# --- LIFF verification page ---
# The LIFF ID for the verification mini-app, created in the LINE Developers
# Console under the channel > LIFF tab. Format: "1234567890-AbCdEfGh".
LIFF_ID = os.getenv("LIFF_ID", "")

# --- Full-screen project dashboard web page (LIFF, Full size) ---
# A second, separate LIFF app (different LIFF ID, registered with size
# "Full") pointed at /liff/project/ — the "ดูเว็บเต็มจอ" button on a project
# card (see flex_builder.build_project_bubble). Kept separate from LIFF_ID
# (the verify-flow LIFF, size "Compact") since they're different pages with
# different sizes; left blank, build_project_bubble simply omits the button.
LIFF_PROJECT_ID = os.getenv("LIFF_PROJECT_ID", "")

# --- Reminders cron ---
# Shared secret required as ?token=... on /cron/check-reminders so random
# internet traffic can't trigger it. Set this, then point a free external
# cron (cron-job.org, UptimeRobot, etc.) at
# https://<your-render-url>/cron/check-reminders?token=<this value>
# every 1-5 minutes. This both fires due reminders on time AND keeps the
# free Render instance from spinning down between real user messages.
# Left blank, the endpoint still works (fails open) but logs a warning.
CRON_SECRET = os.getenv("CRON_SECRET", "")

# --- Public base URL (for assets we host ourselves, e.g. Flex Message logo) ---
# No trailing slash. Defaults to the known Render URL for this service.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://pj-linebot.onrender.com")

# --- Firestore (user registry: LINE userId -> approval status) ---
# Path to the downloaded GCP service account JSON key. On Render this should
# point at a Secret File (e.g. /etc/secrets/firestore-key.json); locally it
# can point at a file inside the project (keep it out of git!).
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID", "")
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "bot_users")
