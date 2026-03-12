#!/bin/bash
# Reset all dev data: PostgreSQL, Neo4j, Redis, local file storage.
# Run from the project root: ./scripts/reset-dev-data.sh
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  This will delete ALL data from PostgreSQL, Neo4j, Redis, and local storage.${NC}"
read -p "Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# ---------------------------------------------------------------------------
# PostgreSQL — truncate all tables (preserves schema and migrations)
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}→ Clearing PostgreSQL...${NC}"
docker exec docker-postgres-1 psql -U osint -d osint -c "
  TRUNCATE TABLE document_chunks, documents, investigations RESTART IDENTITY CASCADE;
" && echo -e "${GREEN}✓ PostgreSQL cleared${NC}"

# ---------------------------------------------------------------------------
# Neo4j — delete all nodes and relationships
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}→ Clearing Neo4j...${NC}"
docker exec docker-neo4j-1 cypher-shell -u neo4j -p osint_dev \
  "MATCH (n) DETACH DELETE n;" \
  && echo -e "${GREEN}✓ Neo4j cleared${NC}"

# ---------------------------------------------------------------------------
# Redis — flush all keys (clears Celery queues and results)
# ---------------------------------------------------------------------------
echo -e "\n${YELLOW}→ Clearing Redis...${NC}"
docker exec docker-redis-1 redis-cli FLUSHALL \
  && echo -e "${GREEN}✓ Redis cleared${NC}"

# ---------------------------------------------------------------------------
# Local file storage — delete uploaded PDFs
# ---------------------------------------------------------------------------
STORAGE_DIR="$(dirname "$0")/../storage"
if [ -d "$STORAGE_DIR" ]; then
    echo -e "\n${YELLOW}→ Clearing local file storage ($STORAGE_DIR)...${NC}"
    rm -rf "${STORAGE_DIR:?}"/*
    echo -e "${GREEN}✓ Local storage cleared${NC}"
else
    echo -e "\n${GREEN}✓ Local storage directory not found — nothing to clear${NC}"
fi

echo -e "\n${GREEN}✅ All dev data reset.${NC}"
