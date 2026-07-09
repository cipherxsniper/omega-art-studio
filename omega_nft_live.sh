#!/bin/bash
# Live NFT minting viewer — copies each image to gallery as it's produced
IMAGES="/data/data/com.termux/files/home/echoes_of_eternity/images"
GALLERY="/sdcard/Pictures/EchoesOfEternity"
mkdir -p "$GALLERY"

echo "Watching for new NFTs..."
SEEN=""
while true; do
    for f in "$IMAGES"/*.png; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        if [[ "$SEEN" != *"$name"* ]]; then
            cp "$f" "$GALLERY/$name"
            echo "NEW: $name → Gallery"
            SEEN="$SEEN $name"
        fi
    done
    sleep 4
done
