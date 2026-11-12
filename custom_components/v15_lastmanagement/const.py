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

# Optional evcc integration through existing Home Assistant evcc entities.
CONF_EVCC_CONFIGURED = "evcc_configured"
CONF_EVCC_CURRENT = "evcc_current_entity"
CONF_EVCC_MODE = "evcc_mode_entity"
CONF_EVCC_POWER = "evcc_charge_power_entity"
CONF_EVCC_PHASES = "evcc_phases_entity"
CONF_EVCC_FIXED_PHASES = "evcc_fixed_phases"
CONF_EVCC_MIN_A = "evcc_min_current_a"
CONF_EVCC_MAX_A = "evcc_max_current_a"
CONF_EVCC_VOLTAGE = "evcc_voltage"
CONF_EVCC_MARGIN_W = "evcc_margin_w"
CONF_EVCC_STABLE_S = "evcc_stable_seconds"
CONF_EVCC_STEP_S = "evcc_step_seconds"
CONF_EVCC_ALLOW_PAUSE = "evcc_allow_pause"
DEFAULT_EVCC_PHASES = 3
DEFAULT_EVCC_MIN_A = 6
DEFAULT_EVCC_MAX_A = 16
DEFAULT_EVCC_VOLTAGE = 230
DEFAULT_EVCC_MARGIN_W = 300
DEFAULT_EVCC_STABLE_S = 90
DEFAULT_EVCC_STEP_S = 30
