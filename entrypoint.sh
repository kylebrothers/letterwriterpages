#!/bin/bash
set -e

# Ensure NAS subdirectories exist
mkdir -p /mnt/appdata/logs
mkdir -p /mnt/appdata/server_files
mkdir -p /mnt/appdata/templates
mkdir -p /mnt/appdata/static

# Remove any existing dirs/symlinks in /app and replace with symlinks to NFS
for dir in logs server_files templates static; do
    rm -rf /app/${dir}
    ln -sf /mnt/appdata/${dir} /app/${dir}
    echo "Symlinked /app/${dir} -> /mnt/appdata/${dir}"
done

exec python app.py
