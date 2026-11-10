#!/usr/bin/env python3
"""Point a Pi OS card at the goodtft 3.5 inch panel.

The working deck (Pi 3B, Pi OS Lite 64-bit Trixie) boots with:

  config.txt    KMS commented out, SPI on,
                dtoverlay=disable-fwfb
                dtoverlay=tft35a:rotate=90
  cmdline.txt   initcall_blacklist=simplefb_driver_init

That combination makes the ILI9486 panel /dev/fb0. HDMI-only cards
should not run this. scripts/setup_pi.sh asks first.

root=PARTUUID=... and every other cmdline token are left as they are.
config.txt and cmdline.txt are copied to <name>.doomsday-pre-tft the
first time they actually change, and to a timestamped .doomsday-bak
as well.

  python3 scripts/apply_tft_boot.py /boot/firmware
  python3 scripts/apply_tft_boot.py --self-test
"""

import io
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import redirect_stderr
from pathlib import Path

SIMPLEFB = "simplefb_driver_init"
KMS = re.compile(r"^(\s*)dtoverlay\s*=\s*vc4-kms-v3d\b(.*)$", re.IGNORECASE)
SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
ACTIVE = {
    "spi": re.compile(r"^dtparam\s*=\s*spi\s*=\s*on\b", re.IGNORECASE),
    "fwfb": re.compile(r"^dtoverlay\s*=\s*disable-fwfb\b", re.IGNORECASE),
    "tft": re.compile(r"^dtoverlay\s*=\s*tft35a\b", re.IGNORECASE),
}
BLOCK_LINES = {
    "spi": "dtparam=spi=on",
    "fwfb": "dtoverlay=disable-fwfb",
    "tft": "dtoverlay=tft35a:rotate=90",
}


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def active_keys(text):
    found = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for key, pattern in ACTIVE.items():
            if pattern.match(stripped):
                found.add(key)
    return found


def comment_kms(text):
    changed = []
    for line in text.splitlines(keepends=True):
        bare = line[:-1] if line.endswith("\n") else line
        ending = "\n" if line.endswith("\n") else ""
        if bare.lstrip().startswith("#"):
            changed.append(line)
            continue
        match = KMS.match(bare)
        if match:
            changed.append(f"{match.group(1)}#dtoverlay=vc4-kms-v3d{match.group(2)}{ending}")
        else:
            changed.append(line)
    return "".join(changed)


def _section_name(line):
    match = SECTION.match(line.strip())
    if not match:
        return None
    return match.group(1).strip().lower()


def insert_in_all(text, chunk):
    """Insert chunk at the end of the [all] section, or append [all]."""
    if not chunk.endswith("\n"):
        chunk += "\n"
    lines = text.splitlines(keepends=True)
    all_at = None
    for index, line in enumerate(lines):
        if _section_name(line) == "all":
            all_at = index
            break
    if all_at is None:
        body = text
        if body and not body.endswith("\n"):
            body += "\n"
        if body and not body.endswith("\n\n"):
            body += "\n"
        return body + "[all]\n" + chunk
    end = len(lines)
    for index in range(all_at + 1, len(lines)):
        if _section_name(lines[index]) is not None:
            end = index
            break
    return "".join(lines[:end] + [chunk] + lines[end:])


def ensure_overlays(text):
    missing = [key for key in ("spi", "fwfb", "tft") if key not in active_keys(text)]
    if not missing:
        return text
    body = [
        "# BEGIN DOOMSDAY TFT",
        "# 3.5 inch SPI touchscreen (goodtft / Waveshare-style ILI9486).",
    ]
    body.extend(BLOCK_LINES[key] for key in missing)
    body.append("# END DOOMSDAY TFT")
    return insert_in_all(text, "\n".join(body) + "\n")


def blacklist_has_symbol(text):
    for token in text.split():
        if not token.startswith("initcall_blacklist="):
            continue
        items = token.split("=", 1)[1].split(",")
        if SIMPLEFB in items:
            return True
    return False


def ensure_blacklist(text):
    """Add simplefb_driver_init. Return the original string if it is already there."""
    if text.strip() == "":
        raise ValueError("cmdline.txt is empty; refusing to replace it")
    if "root=" not in text.split():
        # Still edit, but the caller prints a warning. A Pi cmdline always
        # has root=. Leaving it missing would be a bug in the source file.
        pass
    if blacklist_has_symbol(text):
        return text
    newline = text.endswith("\n")
    tokens = []
    seen = False
    for token in text.split():
        if token.startswith("initcall_blacklist="):
            items = [item for item in token.split("=", 1)[1].split(",") if item]
            if SIMPLEFB not in items:
                items.append(SIMPLEFB)
            tokens.append("initcall_blacklist=" + ",".join(items))
            seen = True
        else:
            tokens.append(token)
    if not seen:
        tokens.append("initcall_blacklist=" + SIMPLEFB)
    rendered = " ".join(tokens)
    if newline:
        rendered += "\n"
    return rendered


def backup(path):
    pre = Path(str(path) + ".doomsday-pre-tft")
    if not pre.exists():
        shutil.copy2(path, pre)
        print(f"Backed up {path} to {pre}")
    stamp = time.strftime("%Y%m%d%H%M%S")
    dest = Path(f"{path}.doomsday-bak-{stamp}")
    suffix = 0
    while dest.exists():
        suffix += 1
        dest = Path(f"{path}.doomsday-bak-{stamp}-{suffix}")
    shutil.copy2(path, dest)
    print(f"Backed up {path} to {dest}")
    return dest


def write_if_changed(path, new_text):
    old = read_text(path)
    if old == new_text:
        return False
    backup(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(new_text)
    return True


def apply(boot_dir):
    boot_dir = Path(boot_dir)
    config_path = boot_dir / "config.txt"
    cmdline_path = boot_dir / "cmdline.txt"
    missing = [str(path) for path in (config_path, cmdline_path) if not path.is_file()]
    if missing:
        sys.stderr.write("apply_tft_boot: missing " + " and ".join(missing) + "\n")
        return 1
    config = read_text(config_path)
    cmdline = read_text(cmdline_path)
    if not any(token.startswith("root=") for token in cmdline.split()):
        sys.stderr.write(
            "apply_tft_boot: cmdline.txt has no root= token. "
            "The rest of the line is kept, but check the file before rebooting.\n"
        )
    try:
        new_cmdline = ensure_blacklist(cmdline)
    except ValueError as error:
        sys.stderr.write(f"apply_tft_boot: {error}\n")
        return 1
    new_config = ensure_overlays(comment_kms(config))
    changed = False
    if write_if_changed(config_path, new_config):
        print(f"Updated {config_path}")
        changed = True
    if write_if_changed(cmdline_path, new_cmdline):
        print(f"Updated {cmdline_path}")
        changed = True
    if changed:
        print("Screen boot files now request the 3.5 inch panel as /dev/fb0.")
        print("Reboot to apply this. HDMI stays off until: sudo doomsday-hdmi on")
    else:
        print("Screen boot files already request the 3.5 inch panel.")
    return 0


def _fail(message):
    sys.stderr.write(message + "\n")
    return 1


def self_test():
    repo = Path(__file__).resolve().parents[1]
    example = repo / "system" / "boot" / "config.txt.example"
    if not example.is_file():
        return _fail(f"missing {example}")
    example_text = read_text(example)
    failures = []

    def check(cond, message):
        if not cond:
            failures.append(message)

    # The captured Pi config is already the panel setup. Applying it again
    # must not add a second overlay or touch the KMS comment.
    with tempfile.TemporaryDirectory() as tmp:
        boot = Path(tmp)
        config = boot / "config.txt"
        cmdline = boot / "cmdline.txt"
        config.write_text(example_text, encoding="utf-8")
        original_cmd = (
            "console=serial0,115200 console=tty1 root=PARTUUID=aaaaaaaa-02 "
            "rootfstype=ext4 fsck.repair=yes rootwait cfg80211.ieee80211_regdom=XX "
            "initcall_blacklist=simplefb_driver_init\n"
        )
        cmdline.write_text(original_cmd, encoding="utf-8")
        err = io.StringIO()
        with redirect_stderr(err):
            result = apply(boot)
        check(result == 0, "apply on the captured config returns 0")
        check("no root=" not in err.getvalue(), "a root=PARTUUID token is recognised")
        check(config.read_text(encoding="utf-8") == example_text, "captured config.txt is unchanged")
        check(cmdline.read_text(encoding="utf-8") == original_cmd, "cmdline with the token is unchanged")
        check(not list(boot.glob("*.doomsday-pre-tft")), "unchanged files are not backed up")

    stock_config = (
        "dtparam=audio=on\n"
        "\n"
        "# Enable DRM VC4 V3D driver\n"
        "dtoverlay=vc4-kms-v3d\n"
        "max_framebuffers=2\n"
        "\n"
        "[all]\n"
    )
    stock_cmd = "console=tty1 root=PARTUUID=aaaaaaaa-02 rootwait cfg80211.ieee80211_regdom=XX\n"
    with tempfile.TemporaryDirectory() as tmp:
        boot = Path(tmp)
        config = boot / "config.txt"
        cmdline = boot / "cmdline.txt"
        config.write_text(stock_config, encoding="utf-8")
        cmdline.write_text(stock_cmd, encoding="utf-8")
        check(apply(boot) == 0, "apply on a stock config returns 0")
        text = config.read_text(encoding="utf-8")
        cmd = cmdline.read_text(encoding="utf-8")
        check("#dtoverlay=vc4-kms-v3d" in text, "KMS line is commented")
        check(not re.search(r"(?m)^dtoverlay=vc4-kms-v3d\b", text), "KMS line is not left active")
        check("dtparam=spi=on" in text, "SPI is on")
        check("dtoverlay=disable-fwfb" in text, "disable-fwfb is present")
        check("dtoverlay=tft35a:rotate=90" in text, "tft35a rotate=90 is present")
        check(text.count("dtoverlay=disable-fwfb") == 1, "disable-fwfb appears once")
        check(text.count("dtoverlay=tft35a:rotate=90") == 1, "tft35a appears once")
        check("root=PARTUUID=aaaaaaaa-02" in cmd, "PARTUUID is preserved")
        check("cfg80211.ieee80211_regdom=XX" in cmd, "regdom token is preserved")
        check("initcall_blacklist=simplefb_driver_init" in cmd, "simplefb blacklist is added")
        check((boot / "config.txt.doomsday-pre-tft").is_file(), "config.txt was backed up first")
        check((boot / "cmdline.txt.doomsday-pre-tft").is_file(), "cmdline.txt was backed up first")
        check(
            (boot / "config.txt.doomsday-pre-tft").read_text(encoding="utf-8") == stock_config,
            "the backup is the original config",
        )
        first = text
        first_cmd = cmd
        check(apply(boot) == 0, "second apply returns 0")
        check(config.read_text(encoding="utf-8") == first, "second apply does not change config")
        check(cmdline.read_text(encoding="utf-8") == first_cmd, "second apply does not change cmdline")

    merged = ensure_blacklist(
        "root=PARTUUID=aaaaaaaa-02 initcall_blacklist=other_driver_init\n"
    )
    check(
        merged == "root=PARTUUID=aaaaaaaa-02 initcall_blacklist=other_driver_init,simplefb_driver_init\n",
        f"existing blacklist is extended ({merged!r})",
    )
    try:
        ensure_blacklist("\n")
        check(False, "empty cmdline should be refused")
    except ValueError:
        pass

    dtbo = repo / "system" / "boot" / "overlays" / "disable-fwfb.dtbo"
    dts = repo / "system" / "boot" / "overlays" / "disable-fwfb-overlay.dts"
    check(dtbo.is_file() and dtbo.stat().st_size == 214, "disable-fwfb.dtbo is the 214-byte overlay")
    check(dts.is_file(), "overlay source is present")
    compiler = shutil.which("dtc")
    if compiler:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "disable-fwfb.dtbo"
            result = os.spawnv(
                os.P_WAIT,
                compiler,
                [compiler, "-I", "dts", "-O", "dtb", "-o", str(out), str(dts)],
            )
            check(result == 0 and out.is_file(), "dtc compiles the overlay source")
            if out.is_file():
                check(out.read_bytes() == dtbo.read_bytes(), "recompiled overlay matches the Pi blob")
    else:
        print("dtc not installed; skipping overlay round-trip")

    if failures:
        for message in failures:
            sys.stderr.write(message + "\n")
        return 1
    print("apply_tft_boot self-test ok")
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) != 2:
        sys.stderr.write("usage: apply_tft_boot.py BOOTDIR | --self-test\n")
        return 2
    try:
        return apply(argv[1])
    except OSError as error:
        sys.stderr.write(f"apply_tft_boot: {error}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
