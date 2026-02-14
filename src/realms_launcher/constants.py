"""Project-wide constants and configuration flags."""

# If True, the updater will run elevated (UAC prompt) to write into protected locations.
USE_ELEVATED_UPDATER = True

# Remote metadata
MOD_INFO_URL = "https://realmsinexile.s3.us-east-005.backblazeb2.com/version.json"  # Use version_beta.json for tests
# NOTE: The launcher fetches news from the repo (HTML snippet).
# The canonical file currently lives under dev fixtures.
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/main/dev/fixtures/news.html"

# Mod versions / packages
BASE_MOD_VERSION = "0.8.6"
BASE_MOD_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms.zip"
UPDATE_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_update.zip"
FULL_MOD_ZIP_URL = (
    "https://f005.backblazeb2.com/file/RealmsInExile/realms_full.zip"
)

# Launcher self-update
LAUNCHER_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_launcher.zip"  # beta: realms_launcher_beta.zip
LAUNCHER_VERSION = "1.1.0"

# Settings storage
REG_PATH = r"SOFTWARE\REALMS_Launcher"

