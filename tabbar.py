"""Shared 36px tab bar for the 480x320 field guide and Cave Mapper.

GUIDE | SCAN | RADIO, three equal widths. Active is filled #1AFF80 with
black text. Inactive is a #0A5C2E outline and dim text. A caller can turn a
tab off; none of them is forced off. Both programs import this so the bar
stays the same.

    import tabbar

    hits = tabbar.draw_tabbar(surface, font_16, active="GUIDE", pressed=None,
                              enabled={"GUIDE": True, "SCAN": True})
    name = tabbar.tab_at(hits, x, y)
"""

import pygame

WIDTH = 480
TAB_H = 36
TABS = ("GUIDE", "SCAN", "RADIO")
GREEN = (0x1A, 0xFF, 0x80)
DIM = (0x0A, 0x5C, 0x2E)
BLACK = (0, 0, 0)


def tab_rects(width=WIDTH, y=0, height=TAB_H):
    """Equal hit rectangles across `width`. The last tab absorbs the remainder."""
    count = len(TABS)
    base = width // count
    rects = []
    x = 0
    for index, name in enumerate(TABS):
        span = base if index < count - 1 else width - x
        rects.append((name, pygame.Rect(x, y, span, height)))
        x += span
    return rects


def draw_tabbar(surface, font, active, pressed=None, enabled=None, y=0):
    """Draw the bar and return hit records: name, rect, enabled.

    `pressed` is the tab name drawn inverted (finger down, or the brief flash).
    `enabled` defaults every tab on. Pass False to dim one.
    """
    flags = {}
    if enabled:
        flags.update(enabled)
    for name in TABS:
        flags.setdefault(name, True)
    hits = []
    for name, rect in tab_rects(surface.get_width(), y, TAB_H):
        is_enabled = bool(flags.get(name))
        _draw_tab(
            surface,
            font,
            name,
            rect,
            active=name == active,
            pressed=name == pressed,
            enabled=is_enabled,
        )
        hits.append({"name": name, "rect": rect, "enabled": is_enabled})
    return hits


def tab_at(hits, x, y):
    """Return the tab name under a point, including a disabled tab."""
    for hit in hits:
        if hit["rect"].collidepoint(x, y):
            return hit["name"]
    return None


def _draw_tab(surface, font, name, rect, active, pressed, enabled):
    if pressed:
        # Invert: a filled tab flashes to an outline, an outline tab flashes filled.
        if active:
            pygame.draw.rect(surface, BLACK, rect)
            pygame.draw.rect(surface, GREEN, rect, 2)
            color = GREEN
        else:
            pygame.draw.rect(surface, DIM, rect)
            color = BLACK
    elif active and enabled:
        pygame.draw.rect(surface, GREEN, rect)
        color = BLACK
    else:
        pygame.draw.rect(surface, BLACK, rect)
        # A live tab has a heavier outline than the disabled placeholder.
        pygame.draw.rect(surface, DIM, rect, 2 if enabled else 1)
        color = DIM
    image = font.render(name, True, color)
    surface.blit(
        image,
        (
            rect.x + (rect.width - image.get_width()) // 2,
            rect.y + (rect.height - image.get_height()) // 2,
        ),
    )
