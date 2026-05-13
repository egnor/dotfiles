#!/usr/bin/env python3
# Helper for batch-signing zones up at Hurricane Electric DNS as secondaries.
# Not run by pyinfra — controller-side helper invoked by hand:
#
#   dns/he_signup.py urls              # print clickable add-slave URLs
#   dns/he_signup.py txt <zone> <key>  # add the dnshenet-key.<zone> TXT
#                                      # record HE.net wants as proof, then
#                                      # reload the zone in Knot (Knot-mastered
#                                      # zones only; for ofb-mastered zones it
#                                      # prints what to do on the ofb side)
#   dns/he_signup.py untxt <zone>      # remove the TXT after HE.net accepts
#   dns/he_signup.py check <zone>      # dig @ns1.he.net to confirm HE serves it
#
# HE.net's add-slave form has two paths to accept a zone: the parent TLD
# already delegates to ns{1..5}.he.net, OR you publish a per-zone TXT proof
# at `dnshenet-key.<zone>`. Since we don't flip registrar NS records until
# HE.net is serving correctly, the TXT path is what we use.

import os
import subprocess
import sys
from urllib.parse import quote

# List 1: ofb-mastered. HE.net AXFR pulls from ns1.ofb.net.
OFB_MASTER = "104.197.242.163"
OFB_ZONES = [
    "corrersinlimites.com",
    "dynamic.ofb.net",
    "enjoys.beer",
    "escapegamedirectory.org",
    "escapegamelist.org",
    "escaperoom.directory",
    "escaperoomdirectory.com",
    "escaperoomdirectory.info",
    "escaperoomdirectory.net",
    "escaperoomdirectory.org",
    "escaperoomlist.com",
    "escaperoomlist.org",
    "escaperoomsubmitter.com",
    "escaperoomsubmitter.org",
    "exitgame.directory",
    "exitgamedirectory.com",
    "exitgamedirectory.org",
    "exitgamelist.com",
    "exitgamelist.org",
    "exitroom.directory",
    "exitroomdirectory.com",
    "exitroomdirectory.org",
    "exitroomlist.com",
    "exitroomlist.org",
    "gale.seattle.wa.us",
    "miskatonic.nu",
    "roomescape.directory",
    "roomescapedirectory.org",
    "roomescapelist.com",
    "roomescapelist.org",
    "te.vg",
    "theburninators.org",
]

# List 2: Knot-mastered here. HE.net AXFR pulls from us via the eacs.io
# hostname (apex A 104.200.25.248 + AAAA, set explicitly in eacs.io.zone).
LOCAL_MASTER = "eacs.io"
LOCAL_ZONES = [
    "amiobsoleteyet.com",
    "amiobsoleteyet.net",
    "amiobsoleteyet.org",
    "cara.vision",
    "competent.services",
    "dan.egnor.name",
    "eacs.io",
    "egnor.io",
    "egnor.me",
    "egnor.services",
    "escaperooms.fun",
    "gorey.games",
    "isthereapuzzlehuntthisweekend.com",
    "isthereapuzzlehunttoday.com",
    "isthereapuzzlehunttomorrow.com",
    "nutrimatic.org",
    "plague.wtf",
    "prexcytgo.com",
    "puzzlehuntcalendar.com",
    "puzzlehuntcalendar.org",
    "puzzlehunts.org",
    "teamleftout.org",
]

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_ZONES = os.path.join(HERE, "files", "zones")
LIVE_ZONES = "/etc/knot/zones"


def _current_public_ns(zone: str) -> list[str]:
    """Where does public DNS say the zone is currently authoritative? Used
    to decide whether to edit the local Knot zone file (we're already
    delegated) or just print instructions for adding the TXT at whatever
    nameserver the parent TLD still points at."""
    out = subprocess.run(
        ["dig", "+short", "+tries=2", "+time=3", "@1.1.1.1", zone, "NS"],
        capture_output=True, text=True,
    )
    return [ns.strip().rstrip(".") for ns in out.stdout.split() if ns.strip()]


def _is_delegated_here(ns_list: list[str]) -> bool:
    """True if the parent already points at our Knot (eacs.io) or HE.net."""
    return any("eacs.io" in ns or "he.net" in ns for ns in ns_list)


def _sync_to_live(zone: str) -> None:
    """Copy the repo zone file to /etc/knot/zones/ (root:knot 644) and
    trigger a Knot zone reload. Without this, edits to the repo file
    don't reach Knot until the next `pyinfra ... deploy.py`."""
    repo = os.path.join(REPO_ZONES, f"{zone}.zone")
    live = os.path.join(LIVE_ZONES, f"{zone}.zone")
    subprocess.run(
        ["sudo", "install", "-o", "root", "-g", "knot", "-m", "644", repo, live],
        check=True,
    )
    subprocess.run(["sudo", "knotc", "zone-reload", zone], check=True)


def make_url(zone: str, master: str) -> str:
    # Hand-build to preserve the literal `!` in `Add+Slave!` and the literal
    # `+` (space) — urllib.parse.urlencode would percent-escape both.
    return (
        "https://dns.he.net/index.cgi?action=add_slave&retmail=0"
        f"&add_slave={quote(zone, safe='')}"
        f"&master1={quote(master, safe='')}"
        "&submit=Add+Slave!"
    )


def cmd_urls() -> None:
    print(f"## List 2 — {len(LOCAL_ZONES)} zones, Knot-mastered (HE pulls from {LOCAL_MASTER})")
    for z in LOCAL_ZONES:
        print(f"  {z:<36} {make_url(z, LOCAL_MASTER)}")
    print()
    print(f"## List 1 — {len(OFB_ZONES)} zones, ofb-mastered (HE pulls from {OFB_MASTER})")
    for z in OFB_ZONES:
        print(f"  {z:<36} {make_url(z, OFB_MASTER)}")
    print()
    print(f"Total: {len(LOCAL_ZONES) + len(OFB_ZONES)} zones "
          "(HE.net free-tier cap is 50).")


def cmd_txt(zone: str, key: str) -> None:
    # HE.net's UI shows the FQDN (e.g. `dnshenet-key.amiobsoleteyet.com`);
    # accept either that or the bare zone name.
    if zone.startswith("dnshenet-key."):
        zone = zone[len("dnshenet-key."):]
    if zone in OFB_ZONES:
        print(f"{zone} is ofb-mastered. On the ofb host, add this record to "
              "its zone file (under /ofb/config/bind/) and `rndc reload`:")
        print(f"  dnshenet-key.{zone}.   300   IN   TXT   \"{key}\"")
        return

    if zone not in LOCAL_ZONES:
        sys.exit(f"unknown zone: {zone}")

    # Knot here is *intended* primary, but until the registrar's NS records
    # have been flipped, the public-DNS chain still resolves the zone via the
    # old provider. HE.net's verification follows the public chain, so the
    # TXT has to live wherever the parent currently delegates.
    ns = _current_public_ns(zone)
    if _is_delegated_here(ns):
        path = os.path.join(REPO_ZONES, f"{zone}.zone")
        # Idempotent: replace any prior `dnshenet-key` line(s) rather than
        # appending — handy if HE.net regenerated the key mid-flow.
        with open(path) as f:
            kept = [ln for ln in f if "dnshenet-key" not in ln]
        if kept and not kept[-1].endswith("\n"):
            kept[-1] += "\n"
        kept.append(
            f'dnshenet-key 1h TXT "{key}"   ; HE.net signup proof (remove after accept)\n'
        )
        with open(path, "w") as f:
            f.writelines(kept)
        print(f"Set dnshenet-key TXT in {path}.")
        _sync_to_live(zone)
        print(f"Synced + reloaded {zone}. Now click 'verify' at HE.net.")
    else:
        print(f"{zone} is not yet delegated to us. The parent still points at:")
        for n in ns:
            print(f"  {n}")
        print("HE.net verifies via public DNS, so add this record at whoever "
              "currently runs the zone (Porkbun / Squarespace / ofb / etc.):")
        print(f"  dnshenet-key.{zone}.   IN   TXT   \"{key}\"")
        print("Then wait for that provider's TTL and click 'verify' at HE.net.")


def cmd_untxt(zone: str) -> None:
    if zone.startswith("dnshenet-key."):
        zone = zone[len("dnshenet-key."):]
    if zone in LOCAL_ZONES:
        path = os.path.join(REPO_ZONES, f"{zone}.zone")
        with open(path) as f:
            kept = [ln for ln in f if "dnshenet-key" not in ln]
        with open(path, "w") as f:
            f.writelines(kept)
        _sync_to_live(zone)
        print(f"Removed dnshenet-key from {zone}.")
    elif zone in OFB_ZONES:
        print(f"On the ofb host, remove the dnshenet-key.{zone} TXT record "
              "and `rndc reload`.")
    else:
        sys.exit(f"unknown zone: {zone}")


def cmd_check(zone: str) -> None:
    out = subprocess.run(
        ["dig", "+short", "@ns1.he.net", zone, "SOA"],
        capture_output=True, text=True,
    )
    soa = out.stdout.strip()
    if soa:
        print(f"OK: {zone} is served at ns1.he.net")
        print(f"   {soa}")
    else:
        sys.exit(f"FAIL: ns1.he.net returned no SOA for {zone}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "urls"
    if cmd == "urls":
        cmd_urls()
    elif cmd == "txt" and len(sys.argv) == 4:
        cmd_txt(sys.argv[2], sys.argv[3])
    elif cmd == "untxt" and len(sys.argv) == 3:
        cmd_untxt(sys.argv[2])
    elif cmd == "check" and len(sys.argv) == 3:
        cmd_check(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
