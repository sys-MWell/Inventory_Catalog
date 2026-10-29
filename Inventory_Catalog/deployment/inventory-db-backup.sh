#!/usr/bin/env bash
set -euo pipefail

DATABASE="${INVENTORY_DATABASE:-/var/lib/inventory-catalog/inventory.db}"
BACKUP_DIR="${INVENTORY_BACKUP_DIR:-/var/lib/inventory-catalog/backups}"
RETENTION_SECONDS=$((2 * 24 * 60 * 60))

if [[ ! -f "$DATABASE" ]]; then
	printf 'Database does not exist: %s\n' "$DATABASE" >&2
	exit 1
fi

install -d -m 0700 "$BACKUP_DIR"
timestamp=$(date -u +%Y%m%d-%H%M%S)
target="$BACKUP_DIR/inventory-$timestamp.db"
temporary="$target.tmp"

cleanup() {
	rm -f "$temporary"
}
trap cleanup EXIT

sqlite3 "$DATABASE" ".backup '$temporary'"
chmod 0600 "$temporary"
mv --no-clobber "$temporary" "$target"

find "$BACKUP_DIR" -type f -name 'inventory-*.db' -mmin +$((RETENTION_SECONDS / 60)) -delete
