"""Constants for V15 Lastmanagement."""
DOMAIN = "v15_lastmanagement"
CONF_GRID = "grid_sensor"
CONF_LIMIT = "limit_kw"
CONF_RESERVE = "reserve_kw"
CONF_REVERSED = "reverse_sign"
CONF_LOADS = "load_switches"
CONF_STALE = "stale_seconds"
DEFAULT_LIMIT = 5.0
DEFAULT_RESERVE = 0.5
DEFAULT_STALE = 120

# Restoration is opt-in, disabled for existing entries until configured.
CONF_RESTORE = "auto_restore"
CONF_RESTORE_POWERS = "restore_load_watts"
CONF_RESTORE_STABLE = "restore_stable_seconds"
CONF_RESTORE_MIN_OFF = "restore_min_off_seconds"
CONF_RESTORE_MARGIN = "restore_margin_watts"
DEFAULT_RESTORE = False
DEFAULT_RESTORE_STABLE = 90
DEFAULT_RESTORE_MIN_OFF = 180
DEFAULT_RESTORE_MARGIN = 200
