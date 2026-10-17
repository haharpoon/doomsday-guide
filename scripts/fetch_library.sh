#!/bin/sh
# Download the offline library: Kiwix ZIM archives and public-domain PDFs.
#
#   sh scripts/fetch_library.sh [library-dir]
#
# Default folder: ./library. Downloads resume (wget -c), so run it again
# after a dropped connection. Sizes are from HTTP HEAD on 2026-10-17.
# Kiwix replaces old dated files; if a URL 404s, look up the newer name at
# https://library.kiwix.org and change the date below.
set -eu

DEST=${1:-./library}
K=https://download.kiwix.org/zim

# bytes  url
ZIMS="
52690706555 $K/wikipedia/wikipedia_en_all_nopic_2026-06.zim
1864210320 $K/wikipedia/wikipedia_en_medicine_maxi_2026-10.zim
1071168673 $K/wikivoyage/wikivoyage_en_all_maxi_2026-09.zim
3570695757 $K/ifixit/ifixit_en_all_2025-12.zim
6177865115 $K/wikibooks/wikibooks_en_all_maxi_2026-04.zim
581641351 $K/other/appropedia_en_all_maxi_2026-02.zim
644665513 $K/other/zimgit-post-disaster_en_2024-05.zim
2019297662 $K/gutenberg/gutenberg_en_lcc-r_2026-03.zim
4532683039 $K/gutenberg/gutenberg_en_lcc-s_2026-03.zim
13154803470 $K/gutenberg/gutenberg_en_lcc-t_2026-03.zim
141407927 $K/stack_exchange/outdoors.stackexchange.com_en_all_2026-08.zim
2062547155 $K/stack_exchange/diy.stackexchange.com_en_all_2026-08.zim
237005541 $K/stack_exchange/cooking.stackexchange.com_en_all_2026-07.zim
"

# US Army manuals (public domain, approved for public release).
# armypubs.army.mil serves ATP 3-50.21 directly. TC 4-02.1 is no longer on
# armypubs and TC 3-25.26 there needs a CAC login, so those come from
# Wikimedia Commons and the Internet Archive.
PDFS="
23772309 ATP_3-50.21_Survival.pdf https://armypubs.army.mil/epubs/DR_pubs/DR_a/pdf/web/ARN12086_ATP%203-50x21%20FINAL%20WEB%202.pdf
1627734 TC_4-02.1_First_Aid.pdf https://upload.wikimedia.org/wikipedia/commons/0/09/TC_4-02.1_First_Aid_%28Change_2%2C_ARN14135-TC_4-02.1-002-WEB-3%29.pdf
2600639 FM_4-25.11_First_Aid.pdf https://archive.org/download/FM4-25x11/FM4-25x11.pdf
8167056 FM_3-25.26_Map_Reading.pdf https://archive.org/download/FM3-25x26/FM3-25x26.pdf
"

# Where There Is No Doctor (Hesperian, 2025). Free for personal,
# non-commercial use under Hesperian's Open Copyright Policy. Hesperian asks
# for permission before it is passed on in digital form, so this script
# fetches it from Hesperian for you; do not bundle the PDFs into an image
# you hand out. About 14 MB in 32 chapter files.
WTND_BYTES=14030592
WTND_BASE=https://hesperian.org/wp-content/uploads/pdf/en_wtnd_2025
WTND_PARTS="fm toc int 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 gp info gloss resc indx bm"

total=$(printf '%s\n%s\n' "$ZIMS" "$PDFS" | awk -v w="$WTND_BYTES" 'NF {s += $1} END {printf "%.0f", s + w}')
gb=$(awk -v b="$total" 'BEGIN {printf "%.1f", b / 1e9}')
echo "Offline library: about $gb GB into $DEST"
printf '%s\n' "$ZIMS" | awk 'NF {n = split($2, p, "/"); printf "  %7.2f GB  %s\n", $1 / 1e9, p[n]}'
printf '%s\n' "$PDFS" | awk 'NF {printf "  %7.2f MB  %s\n", $1 / 1e6, $2}'
printf '  %7.2f MB  Where There Is No Doctor (32 PDFs)\n' "$(awk -v b="$WTND_BYTES" 'BEGIN {print b / 1e6}')"

mkdir -p "$DEST/zim" "$DEST/pdf/where-there-is-no-doctor"
free=$(df -Pk "$DEST" | awk 'NR == 2 {print $4 * 1024}')
have=$(du -sk "$DEST" | awk '{print $1 * 1024}')
if [ "$(awk -v f="$free" -v h="$have" -v t="$total" 'BEGIN {print (f + h < t) ? 1 : 0}')" = 1 ]; then
    echo "Not enough free space: need about $gb GB, have $(awk -v f="$free" 'BEGIN {printf "%.1f", f / 1e9}') GB free." >&2
    exit 1
fi

if [ "${YES:-}" != 1 ]; then
    printf 'Start downloading? [y/N] '
    read -r answer
    case "$answer" in y|Y|yes) ;; *) echo "Stopped."; exit 0 ;; esac
fi

WGET="wget -c --tries=20 --waitretry=10 --timeout=60 --progress=dot:giga"

printf '%s\n' "$ZIMS" | while read -r _bytes url; do
    [ -n "$url" ] || continue
    $WGET -P "$DEST/zim" "$url"
done

printf '%s\n' "$PDFS" | while read -r _bytes name url; do
    [ -n "$url" ] || continue
    [ -f "$DEST/pdf/$name" ] && continue
    $WGET -O "$DEST/pdf/$name.part" "$url" && mv "$DEST/pdf/$name.part" "$DEST/pdf/$name"
done

for part in $WTND_PARTS; do
    $WGET -P "$DEST/pdf/where-there-is-no-doctor" "$WTND_BASE/en_wtnd_2025_$part.pdf"
done

echo "Done. Add the ZIMs to Kiwix with:"
echo "  kiwix-manage $DEST/library.xml add $DEST/zim/*.zim"
