# Point FIELD_TOUCH_FB at the 3.5in ILI9486 panel.
# The kernel numbers framebuffers as they probe, so the panel is not
# always /dev/fb0 once HDMI is enabled. Match the sysfs name instead.
# DOOMSDAY_FB_SYSFS and DOOMSDAY_FB_DEVDIR exist so this can be tested
# against ordinary directories. Leave them unset on the Pi.
_doomsday_fb_root=${DOOMSDAY_FB_SYSFS:-/sys/class/graphics}
_doomsday_fb_dev=${DOOMSDAY_FB_DEVDIR:-/dev}
if [ -z "${FIELD_TOUCH_FB:-}" ] && [ -d "$_doomsday_fb_root" ]; then
  for _doomsday_node in "$_doomsday_fb_root"/fb*; do
    [ -r "$_doomsday_node/name" ] || continue
    _doomsday_name=$(tr -d '[:space:]' < "$_doomsday_node/name" 2>/dev/null || true)
    if [ "$_doomsday_name" = "fb_ili9486" ]; then
      _doomsday_dev="$_doomsday_fb_dev/$(basename "$_doomsday_node")"
      if [ -e "$_doomsday_dev" ]; then
        export FIELD_TOUCH_FB="$_doomsday_dev"
      fi
      break
    fi
  done
fi
unset _doomsday_fb_root _doomsday_fb_dev _doomsday_node _doomsday_name _doomsday_dev
