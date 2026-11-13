"""Pure local go-e API v2 validation, independent of Home Assistant."""
import ipaddress
import math
from types import SimpleNamespace

_RFC1918 = tuple(ipaddress.ip_network(n) for n in
                 ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def validated_local_ipv4(host):
    """Reject remote hosts, URLs, credentials and unexpected ports.

    The go-e HTTP API v2 is plaintext on the local network. This preliminary
    backend therefore supports RFC1918 IPv4 only, without authentication.
    """
    try:
        addr = ipaddress.ip_address(str(host).strip())
    except ValueError as exc:
        raise ValueError("go-e requires a local IPv4 address, not a URL") from exc
    if not isinstance(addr, ipaddress.IPv4Address) or not any(
        addr in subnet for subnet in _RFC1918
    ):
        raise ValueError("go-e address must be in a private RFC1918 IPv4 network")
    return str(addr)


def parse_goe_status(raw, configured_phases):
    """Parse documented API v2 keys; reject incomplete and unsafe readings.

    nrg: U(L1,L2,L3,N), I(L1,L2,L3), P(L1,L2,L3,N,total), pf(...).
    The total charging power is nrg[11], in watts.
    """
    if not isinstance(raw, dict):
        return None
    amp = raw.get("amp")
    frc = raw.get("frc")
    nrg = raw.get("nrg")
    pnp = raw.get("pnp")
    if (type(amp) is not int or not 6 <= amp <= 32 or
            type(frc) is not int or frc not in (0, 1, 2) or
            not isinstance(nrg, list) or len(nrg) < 12):
        return None
    try:
        power = float(nrg[11])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(power) or not 0 <= power <= 30000:
        return None
    if configured_phases not in (1, 3):
        return None
    if pnp is not None and (type(pnp) is not int or pnp not in (0, 1, 3)):
        return None
    # 3 phases are always assumed for a three-phase-capable installation;
    # this cannot underestimate the required charging power.
    if configured_phases == 1 and pnp == 3:
        return None
    phases = max(configured_phases, pnp or configured_phases)
    name = {0: "smart", 1: "off", 2: "now"}[frc]
    return {
        "current_a": amp, "charge_w": power, "phases": phases,
        "mode_name": name,
        "mode": SimpleNamespace(attributes={"options": ["smart", "off", "now"]}),
    }


