#!/bin/bash
# Test backup with active database operations (file locks)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Starting backup test with active database operations..."

# Start background database operations
(
    while true; do
        docker exec test_postgres psql -U postgres -d testdb -c "
            INSERT INTO test_data (name, email, age, salary, data_json, random_text)
            VALUES ('Test_' || random(), 'test' || random() || '@test.com', 
                    (random() * 80 + 18)::INTEGER, 
                    (random() * 100000 + 30000)::DECIMAL(10,2),
                    jsonb_build_object('test', true),
                    md5(random()::text));
        " > /dev/null 2>&1
        
        docker exec test_postgres psql -U postgres -d testdb -c "
            UPDATE test_data SET age = (random() * 80 + 18)::INTEGER 
            WHERE id = (random() * 500000 + 1)::INTEGER;
        " > /dev/null 2>&1
        
        docker exec test_postgres psql -U postgres -d testdb -c "
            DELETE FROM test_data WHERE id = (SELECT MAX(id) FROM test_data);
        " > /dev/null 2>&1
        
        sleep 0.5
    done
) &
DB_OPS_PID=$!

cleanup_db_ops() {
    kill "$DB_OPS_PID" 2>/dev/null || true
    wait "$DB_OPS_PID" 2>/dev/null || true
}
trap cleanup_db_ops EXIT

echo "Database operations running in background (PID: $DB_OPS_PID)"

# Run backup
echo "Starting backup..."
cd "$REPO_ROOT" || exit 1
./bbackup.py backup --containers test_postgres --no-interactive
BACKUP_STATUS=$?

if [ "$BACKUP_STATUS" -ne 0 ]; then
    exit "$BACKUP_STATUS"
fi

echo "Backup test complete!"
