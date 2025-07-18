#!/bin/bash

# Resolve symlinks to get the real script directory, even if called via symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
WEBARENA_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

# Source the variables
if [ -f "$WEBARENA_DIR/00_vars.sh" ]; then
    source "$WEBARENA_DIR/00_vars.sh"
else
    echo "Error: Could not find $WEBARENA_DIR/00_vars.sh"
    exit 1
fi

echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== WebArena Services ==="
echo "Checking services on $PUBLIC_HOSTNAME..."

# Function to check service status
check_service() {
    local name=$1
    local url=$2
    local code=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5)
    if [ "$code" == "000" ]; then
        echo "$name: TIMEOUT/UNREACHABLE"
    else
        echo "$name: $code"
    fi
}

check_service "Homepage" "http://localhost:${HOMEPAGE_PORT}"
check_service "Shopping" "http://localhost:${SHOPPING_PORT}"
check_service "Shopping Admin" "http://localhost:${SHOPPING_ADMIN_PORT}/admin"
check_service "Reddit" "http://localhost:${REDDIT_PORT}"
check_service "GitLab" "http://localhost:${GITLAB_PORT}"
check_service "Wikipedia" "http://localhost:${WIKIPEDIA_PORT}"
check_service "Map" "http://localhost:${MAP_PORT}"
check_service "Reset Server" "http://localhost:${RESET_PORT}/status"
check_service "Task Viewer" "http://localhost:${TASK_VIEWER_PORT}"

echo -e "\n=== External URLs ==="
echo "Homepage: http://${PUBLIC_HOSTNAME}:${HOMEPAGE_PORT}"
echo "Shopping: ${SHOPPING_URL}"
echo "Shopping Admin: ${SHOPPING_ADMIN_URL}"
echo "Reddit: ${REDDIT_URL}"
echo "GitLab: ${GITLAB_URL}"
echo "Wikipedia: ${WIKIPEDIA_URL}"
echo "Map: ${MAP_URL}"
echo "Reset: http://${PUBLIC_HOSTNAME}:${RESET_PORT}/reset"
echo "Task Viewer: ${TASK_VIEWER_URL}"

echo -e "\n=== Tmux Sessions ==="
tmux ls 2>/dev/null || echo "No tmux sessions"
