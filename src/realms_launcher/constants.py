"""Project-wide constants and configuration flags."""

# If True, the updater will run elevated (UAC prompt) to write into protected locations.
USE_ELEVATED_UPDATER = True

# Remote metadata
MOD_INFO_URL = "https://realmsinexile.s3.us-east-005.backblazeb2.com/version.json"  # Use version_beta.json for tests
NEWS_URL = "https://raw.githubusercontent.com/hansnery/Realms-Launcher/refs/heads/main/news.html"

# Mod versions / packages
BASE_MOD_VERSION = "0.8.0"
BASE_MOD_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms.zip"
UPDATE_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_update.zip"
AOTR_RAR_URL = "https://f005.backblazeb2.com/file/RealmsInExile/aotr.rar"

# Launcher self-update
LAUNCHER_ZIP_URL = "https://f005.backblazeb2.com/file/RealmsInExile/realms_launcher.zip"  # beta: realms_launcher_beta.zip
LAUNCHER_VERSION = "1.0.7"

# Settings storage
REG_PATH = r"SOFTWARE\REALMS_Launcher"

