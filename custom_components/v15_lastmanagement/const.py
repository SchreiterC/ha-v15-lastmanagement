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

# Optional Home Connect cloud-backed program pause/resume (experimental).
CONF_HC_PAUSE = "home_connect_pause_buttons"
CONF_HC_POWERS = "home_connect_load_watts"

# Experimental, separately armed dishwasher PV scheduling (never default-on).
CONF_PV_ENABLED = "pv_start_configured"
CONF_PV_SELECTED = "pv_selected_program"
CONF_PV_ARM = "pv_start_arm"
CONF_PV_FORECAST = "pv_forecast_sensor"
CONF_PV_EARLIEST = "pv_earliest"
CONF_PV_DEADLINE = "pv_deadline"
CONF_PV_DURATION = "pv_duration_minutes"
CONF_PV_MIN_WH = "pv_minimum_wh"
CONF_PV_WATTS = "pv_estimated_watts"
CONF_PV_MARGIN = "pv_margin_watts"
CONF_PV_STABLE = "pv_stable_seconds"

# Restore previous live switch states after reload/restart (explicit opt-in).
# Only the enable switches are restored; load ownership and PV one-shot consent
# are never persisted.
CONF_RESTART_LIVE = "restore_live_control_on_restart"
CONF_RESTART_PV = "restore_pv_start_on_restart"

# Opt-in illustrative Austrian grid-capacity charges (not a bill).
CONF_COST_CONFIGURED = "network_costs_configured"
CONF_COST_MODE = "network_costs_mode"
CONF_COST_REGION = "network_costs_region"
CONF_COST_FIRST = "network_costs_first_cents"
CONF_COST_HIGHER = "network_costs_higher_cents"
CONF_COST_MINIMUM = "network_costs_minimum_kw"
