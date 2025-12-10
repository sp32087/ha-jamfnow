
DOMAIN = "jamfnow"
PLATFORMS: list[str] = ["sensor", "select"]
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_BASE_URL = "base_url"

DEFAULT_BASE_URL = "https://services-api.services.jamfnow.com"
UPDATE_INTERVAL_SECONDS = 300

SERVICE_SET_BLUEPRINT = "set_blueprint"
SERVICE_ENABLE_LOST_MODE = "enable_lost_mode"
SERVICE_DISABLE_LOST_MODE = "disable_lost_mode"
SERVICE_RESTART_DEVICE = "restart_device"
SERVICE_SHUTDOWN_DEVICE = "shutdown_device"
SERVICE_SYNC_INVENTORY = "sync_inventory"
