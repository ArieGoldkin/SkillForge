#!/bin/bash
# Langfuse PostgreSQL Database Backup Script
# This backs up ALL Langfuse config: score_configs, prompts, llm_api_keys, eval_templates, etc.
#
# Usage:
#   ./scripts/backup_langfuse_db.sh backup   # Create backup
#   ./scripts/backup_langfuse_db.sh restore  # Restore from latest backup
#   ./scripts/backup_langfuse_db.sh list     # List available backups

set -e

BACKUP_DIR="/Users/yonatangross/coding/SkillForge/backend/data/langfuse_db_backups"
CONTAINER_NAME="skillforge-langfuse-db"
DB_USER="langfuse"
DB_NAME="langfuse"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

case "$1" in
    backup)
        BACKUP_FILE="$BACKUP_DIR/langfuse_backup_${TIMESTAMP}.sql"
        echo "Creating Langfuse database backup..."
        echo "  Container: $CONTAINER_NAME"
        echo "  Database: $DB_NAME"
        echo "  Output: $BACKUP_FILE"

        docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

        # Also create a symlink to latest
        ln -sf "$(basename "$BACKUP_FILE")" "$BACKUP_DIR/latest.sql"

        # Show what was backed up
        echo ""
        echo "Backup complete! Contents:"
        grep -c "INSERT INTO" "$BACKUP_FILE" | xargs -I {} echo "  {} INSERT statements"

        # Count key tables
        echo ""
        echo "Key tables backed up:"
        echo "  - score_configs: $(grep -c 'INSERT INTO.*score_configs' "$BACKUP_FILE" 2>/dev/null || echo 0) rows"
        echo "  - prompts: $(grep -c 'INSERT INTO.*prompts' "$BACKUP_FILE" 2>/dev/null || echo 0) rows"
        echo "  - llm_api_keys: $(grep -c 'INSERT INTO.*llm_api_keys' "$BACKUP_FILE" 2>/dev/null || echo 0) rows"
        echo "  - eval_templates: $(grep -c 'INSERT INTO.*eval_templates' "$BACKUP_FILE" 2>/dev/null || echo 0) rows"
        echo "  - datasets: $(grep -c 'INSERT INTO.*\"datasets\"' "$BACKUP_FILE" 2>/dev/null || echo 0) rows"

        echo ""
        echo "Backup saved to: $BACKUP_FILE"
        ;;

    restore)
        BACKUP_FILE="${2:-$BACKUP_DIR/latest.sql}"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "Error: Backup file not found: $BACKUP_FILE"
            echo "Available backups:"
            ls -la "$BACKUP_DIR"/*.sql 2>/dev/null || echo "  No backups found"
            exit 1
        fi

        echo "WARNING: This will REPLACE the current Langfuse database!"
        echo "  Backup file: $BACKUP_FILE"
        read -p "Are you sure? (yes/no): " confirm

        if [ "$confirm" != "yes" ]; then
            echo "Restore cancelled."
            exit 0
        fi

        echo "Restoring Langfuse database..."

        # Drop and recreate database
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME}_old;"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "ALTER DATABASE $DB_NAME RENAME TO ${DB_NAME}_old;"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

        # Restore
        cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"

        echo "Restore complete! Restart langfuse-web to apply changes:"
        echo "  docker compose restart langfuse-web"
        ;;

    list)
        echo "Available Langfuse backups:"
        ls -lh "$BACKUP_DIR"/*.sql 2>/dev/null || echo "  No backups found"
        ;;

    *)
        echo "Langfuse Database Backup Script"
        echo ""
        echo "Usage:"
        echo "  $0 backup              Create a new backup"
        echo "  $0 restore [file]      Restore from backup (default: latest)"
        echo "  $0 list                List available backups"
        echo ""
        echo "Backup location: $BACKUP_DIR"
        ;;
esac
