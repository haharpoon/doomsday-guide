---
title: Offline library
order: 6
parent: more
intro: Bigger books for the Pi: Wikipedia, medicine, repair and how-to, read with Kiwix.
---

## What Kiwix is

Kiwix reads ZIM files. A ZIM is a whole website packed into one file: Wikipedia, a medical encyclopedia, a repair site. Once it is on the card, it works with no internet.

This guide already uses two ZIMs: Medicine search and Places. The bigger library adds more, from the same Kiwix catalogue at library.kiwix.org.

On the Pi, kiwix-serve shares the files as web pages. Search all archives (in More) searches every ZIM it knows about. On another phone or laptop on the same Wi-Fi, open the Pi's address in a browser on port 8080. The login screen shows it, for example http://192.168.1.20:8080.

## What to get

The recommended set fits a 128 GB card with room to spare. Sizes as of October 2026:

- Wikipedia, English, no pictures: 52.7 GB. All articles, text only.
- WikiMed (medical Wikipedia, with pictures): 1.9 GB
- Wikivoyage (travel and places): 1.1 GB
- Wikibooks (textbooks and how-tos): 6.2 GB
- iFixit (repair guides): 3.6 GB
- Appropedia (appropriate technology): 0.6 GB
- Post-disaster resources collection: 0.6 GB
- Project Gutenberg, medicine (R): 2.0 GB
- Project Gutenberg, agriculture (S): 4.5 GB
- Project Gutenberg, technology (T): 13.2 GB
- Stack Exchange DIY: 2.1 GB
- Stack Exchange Cooking: 0.2 GB
- Stack Exchange Outdoors: 0.1 GB

ZIM total: about 88.7 GB. PDFs below: about 50 MB.

Wikipedia with pictures (maxi) is 127 GB and does not fit a 128 GB card. A 256 GB card, or a USB drive, would hold it.

## PDF manuals

Free manuals, saved as PDF in library/pdf:

- ATP 3-50.21 Survival (US Army, 2018). Water, food, fire, shelter, navigation, knots.
- TC 4-02.1 First Aid (US Army, 2016 with changes to 2018). Replaced FM 4-25.11.
- FM 4-25.11 First Aid (2002). Older, kept for its clear pictures.
- FM 3-25.26 Map Reading and Land Navigation. Now TC 3-25.26.
- Where There Is No Doctor (Hesperian, 2025). Village health care: illness, injury, childbirth, and the Green Pages on medicine doses.

US Army manuals are public domain and approved for public release.

Hesperian lets you copy it for non-commercial use with credit, but asks permission before passing on digital copies. Download it for yourself from Hesperian. Do not hand out cards with it on.

Open PDFs on the Pi with the desktop's PDF viewer, or from another device over Wi-Fi.

## Download

On a computer or Pi with internet, from the guide folder:

sh scripts/fetch_library.sh /media/usb/library

It prints the size first and asks before starting. Downloads resume: if the connection drops, run it again and it carries on with wget -c. The big Wikipedia file takes many hours.

Kiwix renames files when it publishes a new month. If a link fails, find the new name at library.kiwix.org and edit the date in the script.

Check the card has room: about 89 GB for the full set.

## Add to the Pi

Copy the zim folder to wherever kiwix-serve keeps its archives on your Pi (the Kiwix files live under /var/lib/kiwix on this build). Use a fast USB drive if the SD card is full.

Add each file to the Kiwix library list that kiwix-serve reads:

kiwix-manage library.xml add zim/*.zim

Restart kiwix-serve, or reboot the Pi. The new books show in Search all archives.

To make one ZIM a section's search, set book in that topic's front matter to the ZIM's book name (the file name without .zim). See content/README.md.

## Use it well

Search with plain words: "burn", "water filter", "bicycle chain".

Wikipedia has more breadth. WikiMed has more depth on health. Where There Is No Doctor is written for people with no clinic nearby: start there for illness.

iFixit and Stack Exchange DIY are for fixing things. Wikibooks and Appropedia cover making and growing things. Gutenberg has old farming, building and craft books: check old advice against newer sources, especially on medicine.

The Pi is slow on big searches. Give it a few seconds. Turn it off when not reading to save power.

## Library sources

Kiwix catalogue: library.kiwix.org (sizes read from the catalogue and download.kiwix.org on 17 October 2026)

US Army Publishing Directorate: armypubs.army.mil

Hesperian Health Guides and Open Copyright Policy: hesperian.org, languages.hesperian.org/pages/en/pdf.html

Internet Archive and Wikimedia Commons copies of public-domain Army manuals: archive.org, commons.wikimedia.org

WikiHow and Practical Action are not in the Kiwix catalogue at the moment. Appropedia and the post-disaster collection cover similar ground.
