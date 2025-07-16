#!/bin/bash

# Resolve symlinks to get the real script directory, even if called via symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
WEBARENA_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
SESSION_NAME="serve"

# Parse command line arguments
RESTART=false
if [[ "$1" == "--restart" ]]; then
    RESTART=true
fi

# Check if tmux session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null
SESSION_EXISTS=$?

if [ $SESSION_EXISTS -eq 0 ] && [ "$RESTART" = true ]; then
    echo "Killing existing session..."
    tmux kill-session -t $SESSION_NAME
    sleep 2
    SESSION_EXISTS=1
fi

if [ $SESSION_EXISTS != 0 ]; then
    echo "Creating new tmux session: $SESSION_NAME"
    
    # Create new session with first window for homepage
    tmux new-session -d -s $SESSION_NAME -n homepage
    tmux send-keys -t $SESSION_NAME:homepage "cd $WEBARENA_DIR && sudo bash 06_serve_homepage.sh" C-m
    
    # Create window for reset server (optional)
    tmux new-window -t $SESSION_NAME -n reset
    tmux send-keys -t $SESSION_NAME:reset "cd $WEBARENA_DIR && sudo bash 07_serve_reset.sh" C-m
    
    # Create window for setup
    tmux new-window -t $SESSION_NAME -n setup
    
    # Chain all setup commands together with && to ensure sequential execution
    tmux send-keys -t $SESSION_NAME:setup "cd $WEBARENA_DIR && \
        sudo bash 02_docker_remove_containers.sh && \
        sudo bash 03_docker_create_containers.sh && \
        sudo bash 04_docker_start_containers.sh && \
        sudo bash 05_docker_patch_containers.sh && \
        echo 'Setup complete!'" C-m
    
    echo "WebArena services starting up..."
    echo "To view status: tmux attach -t $SESSION_NAME"
    echo "To switch windows: Ctrl-b + window number (0=homepage, 1=reset, 2=setup)"
else
    echo "Session $SESSION_NAME already exists!"
    echo "To attach: tmux attach -t $SESSION_NAME"
    echo "To restart: $0 --restart"
fi

# Show current status
echo ""
echo "Current tmux sessions:"
tmux ls
