"""uv-network-test.py — diagnose macOS Local Network permission for the
running Python interpreter.

On macOS 15+ ("Local Network" privacy gate) the kernel can silently deny
local-LAN socket connects from a binary that hasn't been granted permission.
The failure surfaces as `OSError: [Errno 65] No route to host` even when
`curl`/`ping` from the same shell work fine. uv-managed standalone Pythons
(from python-build-standalone) are particularly affected because they lack
a proper .app bundle so the system never prompts; it just denies.

This script:
  1. Reports which Python is running and whether it looks like a uv build.
  2. Picks a target on the local LAN (arg, or auto-detected default gateway).
  3. Attempts a raw TCP connect from this Python.
  4. Re-runs the same connect from any other Pythons on PATH for comparison.
  5. Interprets the result and prints concrete remediation steps.

Usage:
    python uv-network-test.py                 # auto-pick default gateway:80
    python uv-network-test.py 192.168.1.42    # custom host, default port 80
    python uv-network-test.py 192.168.1.42:443
"""

from __future__ import annotations

import errno
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def underlying_executable() -> str:
    """Return the real interpreter path, following the venv shim if any.

    Inside a venv, sys.executable is the .venv/bin/python symlink; the actual
    binary being loaded is at sys._base_executable.
    """
    return getattr(sys, "_base_executable", sys.executable) or sys.executable


def classify_python(real_path: str) -> str:
    """Heuristic label for the interpreter source."""
    if "/uv/python/" in real_path or "python-build-standalone" in real_path:
        return "uv-managed standalone"
    if real_path.startswith("/opt/homebrew/") or real_path.startswith("/usr/local/Cellar/"):
        return "Homebrew"
    if real_path.startswith("/Library/Frameworks/Python.framework/"):
        return "python.org installer"
    if real_path.startswith("/usr/bin/") or "/CommandLineTools/" in real_path:
        return "Apple system Python"
    return "unknown / third-party"


def default_gateway() -> str | None:
    """Read the IPv4 default gateway from `route -n get default`."""
    try:
        out = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    for line in out.splitlines():
        if "gateway:" in line:
            return line.split(":", 1)[1].strip()
    return None


def parse_target(arg: str | None) -> tuple[str, int]:
    if arg is None:
        host = default_gateway()
        if not host:
            print("ERROR: no default gateway found; pass an explicit host[:port].")
            sys.exit(2)
        return host, 80
    if ":" in arg:
        host, port_s = arg.rsplit(":", 1)
        return host, int(port_s)
    return arg, 80


def tcp_probe(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str, str]:
    """Return (success, summary, raw_error_repr)."""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        local = s.getsockname()
        s.close()
        return True, f"connected (local {local[0]}:{local[1]})", ""
    except socket.timeout:
        return False, "timeout (firewall drop or wrong subnet)", "timeout"
    except OSError as e:
        name = errno.errorcode.get(e.errno, str(e.errno))
        return False, f"{name}: {e.strerror or e}", repr(e)


def find_other_pythons() -> list[Path]:
    """Find Pythons that are NOT the one currently running."""
    candidates = [
        "/usr/bin/python3",
        "/opt/homebrew/bin/python3",
        "/opt/homebrew/bin/python3.13",
        "/opt/homebrew/bin/python3.12",
        "/opt/homebrew/bin/python3.11",
        "/usr/local/bin/python3",
    ]
    me = Path(sys.executable).resolve()
    found = []
    seen = {me}
    for c in candidates:
        p = Path(c)
        if p.exists():
            rp = p.resolve()
            if rp not in seen:
                found.append(p)
                seen.add(rp)
    return found


def probe_via(python_path: Path, host: str, port: int) -> str:
    """Run the same connect from a different Python; return one-line summary."""
    code = (
        "import socket,sys,errno\n"
        "s=socket.socket(); s.settimeout(4)\n"
        "try:\n"
        f"    s.connect(({host!r},{port}))\n"
        "    print('OK', s.getsockname()[0])\n"
        "except OSError as e:\n"
        "    name=errno.errorcode.get(e.errno,str(e.errno))\n"
        "    print('FAIL', name, e.strerror)\n"
    )
    try:
        r = subprocess.run([str(python_path), "-c", code],
                           capture_output=True, text=True, timeout=10)
        return (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "(no output)"
    except Exception as e:
        return f"(failed to invoke: {e})"


def main(argv: list[str]) -> int:
    host, port = parse_target(argv[1] if len(argv) > 1 else None)

    real = underlying_executable()
    print("=" * 72)
    print("Python under test")
    print("-" * 72)
    print(f"  sys.executable : {sys.executable}")
    if real != sys.executable:
        print(f"  real binary    : {real}  (venv shim resolved)")
    print(f"  sys.version    : {sys.version.split()[0]}")
    print(f"  classified as  : {classify_python(real)}")
    print(f"  platform       : {platform.platform()}")

    print()
    print(f"Target: {host}:{port}")
    print("-" * 72)

    # Sanity: can we even resolve / route via the shell?
    ping = shutil.which("ping")
    if ping:
        r = subprocess.run([ping, "-c", "1", "-W", "1000", host],
                           capture_output=True, text=True)
        print(f"  ping (ICMP)    : {'OK' if r.returncode == 0 else 'fail'}")

    curl = shutil.which("curl")
    if curl:
        r = subprocess.run(
            [curl, "-sS", "-m", "3", "-o", "/dev/null",
             "-w", "HTTP %{http_code}", f"http://{host}:{port}/"],
            capture_output=True, text=True,
        )
        print(f"  curl HTTP      : {r.stdout.strip() or 'no output'} (rc={r.returncode})")

    print()
    print("Raw TCP connect from THIS Python")
    print("-" * 72)
    ok, summary, _raw = tcp_probe(host, port)
    print(f"  result: {'OK' if ok else 'FAIL'} — {summary}")

    others = find_other_pythons()
    if others:
        print()
        print("Same connect from OTHER Pythons on this machine")
        print("-" * 72)
        for p in others:
            print(f"  {p}")
            print(f"    -> {probe_via(p, host, port)}")

    print()
    print("Diagnosis")
    print("-" * 72)
    if ok:
        print("  This Python can reach the LAN. No permission issue.")
        return 0

    # Heuristic: if curl/ping work but Python doesn't with EHOSTUNREACH/ENETUNREACH,
    # it's almost certainly the macOS Local Network privacy gate.
    if "EHOSTUNREACH" in summary or "ENETUNREACH" in summary:
        if platform.system() == "Darwin":
            print("  Symptom matches macOS Local Network privacy denial.")
            print("  curl/ping work (Apple-signed system binaries are implicitly")
            print("  trusted) but this Python binary has been silently denied LAN")
            print("  access. ALL third-party Pythons (uv-managed, Homebrew,")
            print("  python.org, pyenv) are subject to this gate — only Apple's")
            print("  /usr/bin/python3 is exempt.")
            print()
            print("  Remediation, in order of likely-to-work:")
            print()
            print("  1. System Settings → Privacy & Security → Local Network.")
            print("     Look for an entry matching this binary and toggle it ON:")
            print(f"       {real}")
            print("     Note: macOS may display only the parent shell (Terminal,")
            print("     iTerm, your IDE) — try toggling that too.")
            print()
            print("  2. If no relevant entry exists, force a fresh permission prompt:")
            print("       tccutil reset LocalNetwork")
            print("     Then re-run this script. macOS should prompt to allow the")
            print("     binary the next time it touches a LAN address.")
            print()
            print("  3. Standalone Pythons (uv, sometimes Homebrew) lack an .app")
            print("     bundle / Info.plist, so the prompt sometimes never fires.")
            print("     Last-resort workarounds:")
            print("     - Run via /usr/bin/python3 if the project supports 3.9.")
            print("     - Run from an IDE / Terminal that already has Local Network")
            print("       permission and execute the Python binary as a child.")
            print("     - Sign the binary with a custom entitlement (advanced).")
        else:
            print("  EHOSTUNREACH on non-macOS — check routing / interface config.")
    elif "ECONNREFUSED" in summary:
        print("  TCP reached the host but nothing is listening on that port.")
        print("  LAN permission is fine; the target service is just down.")
    elif "timeout" in summary:
        print("  Connect timed out. Either the host isn't on this LAN, or a")
        print("  firewall is silently dropping SYNs. Verify with `ping` / `arp -n`.")
    else:
        print(f"  Unrecognized failure: {summary}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
