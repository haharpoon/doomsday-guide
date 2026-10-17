# Guide sheets

These files are the field guide. Edit them here. You do not need to change Python to add a sheet, fix a sentence, or reorder the home menu.

The keyboard guide (`field`) and the touch guide (`field_touch`) both read this folder. On the Pi the installer copies it to `/usr/local/share/doomsday/content`.

## File name

One topic per file: `content/<topic>.md`. The file name is the topic id (`shelter.md`, `knots_main.md`). `README.md` is not a topic.

## Layout

A file starts with optional front matter, then one card per `##` heading. Card text is plain paragraphs. Leave a blank line between paragraphs.

```markdown
---
title: Shelter
order: 1
intro: Build small, get off the ground, stay out of the wind.
---

## Choose a site

Look up before you look down.

Do not camp in a dry wash.
```

Front matter keys:

| Key | Meaning |
| --- | --- |
| `title` | Name on the menu. The touch and keyboard guides show this. |
| `order` | Sort key. Lower numbers come first. Home-menu files need an `order`. |
| `intro` | One line under the section title. Use `intro: \|` when you need several lines. |
| `book` | Kiwix archive book name. When set, the section can search that archive. |
| `hint` | Line shown above the search keyboard. Optional. |
| `parent` | Slug of the section this file belongs under, instead of the home menu. |
| `merge` | `cards` folds this file's cards into the parent, in `order`, before the parent's own cards. |
| `tint` | `true` (default) draws pictures in green. `false` shows the file's own colors. |

`archive` is accepted as another name for `book`.

Archive book names on this Pi:

- Medicine: `wikipedia_en_medicine_nopic_2026-04`
- Places: `wikivoyage_en_all_nopic_2026-09`

A `book` value with nothing after the colon searches both archives.

## What each shape does

- **Several cards** open as a menu. Each `##` heading is one button.
- **One card** opens straight onto that sheet. The sheet title is the file's `title`.
- **No cards, with `book` set** opens search. That is how Medicine works today. One card opens as a sheet and still offers search, the way Food does. Several cards are listed, and Search stays on that menu.
- **`parent`** nests the file under another topic. `signaling.md` and `clothing.md` sit under `more.md`. `knots_more.md` sits under Knots.
- **`merge: cards`** is for a card that lives in its own file but should appear inside the parent. `knot_which.md` is the first Knots card ("Which knot").

`more.md` is the More button. The program adds Places, Search all archives, and (on the keyboard) Cave Mapper after the sheets you list under it. Those three are the library and the scanner, not sheets.

A file with `order` and no `parent` is a home-menu button. The home menu is that list, sorted by `order`. Numbers in the keyboard menu follow that order.

## Length

The screen is 480×320. A card should be about 8–12 short lines so it fits on one page. Longer cards still work: Prev, Next, and a vertical swipe turn pages. Write short sentences. Use a blank line between steps.

## Pictures

Put PNGs in `content/img/`. Refer to them from a card like this, on their own line:

```markdown
![debris hut ridge](img/hut.png)
```

The path is relative to `content/`, so `img/hut.png` means `content/img/hut.png`.

Draw the picture at **480×284 pixels**, PNG, high contrast. Light lines on a black background read best. The touch guide scales it to the area under the title and above the buttons, and tints it green unless the file says `tint: false`.

The keyboard guide has no pictures. It prints:

```text
[diagram: debris hut ridge]
```

The words in brackets are the alt text, so write alt text that still helps if the picture is missing.

## If the folder is missing

The guides still open. They say the sheets were not found and leave Medicine search and archive search available.
