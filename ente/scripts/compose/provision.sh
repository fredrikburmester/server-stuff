#!/bin/sh

# MinIO provisioning script for Ente
# Runs once on first startup to create required buckets

MINIO_USER="${MINIO_ROOT_USER:-admin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-changeme}"

# Wait for MinIO to be ready
while ! mc alias set h0 http://minio:3200 "$MINIO_USER" "$MINIO_PASS"
do
   echo "waiting for MinIO..."
   sleep 0.5
done

echo "[OK] MinIO is ready!"

# Check for existing buckets
echo "[INFO] Checking for existing buckets..."
BUCKETS=$(mc ls h0)

# Create bucket if it doesn't exist
if echo "$BUCKETS" | grep -q "b2-eu-cen"; then
    echo "[OK] Bucket 'b2-eu-cen' already exists"
else
    echo "[INFO] Creating bucket 'b2-eu-cen'..."
    mc mb -p h0/b2-eu-cen
fi

echo "[OK] MinIO provisioning completed!"


