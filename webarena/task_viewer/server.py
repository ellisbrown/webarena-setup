import json
import os
from functools import lru_cache

from flask import Flask, render_template_string
from pathlib import Path

# Task URL constants from environment variables
TASK_URLS = {
    'shopping_admin': os.environ.get('SHOPPING_ADMIN_URL', 'http://localhost:7780/admin'),
    'map': os.environ.get('MAP_URL', 'http://localhost:3000'),
    'reddit': os.environ.get('REDDIT_URL', 'http://localhost:9999/forums/all'),
    'gitlab': os.environ.get('GITLAB_URL', 'http://localhost:8023/explore'),
    'wikipedia': os.environ.get('WIKIPEDIA_URL', 'http://localhost:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing')
}
TASK_VIEWER_PORT = int(os.environ.get('TASK_VIEWER_PORT', 5000))
TASK_JSON_PATH = os.environ.get('TASK_JSON_PATH', 'webarena_tasks.json')


app = Flask(__name__)

# HTML template for the task viewer
TEMPLATE = Path('template.html').read_text()

@lru_cache(maxsize=1)
def load_tasks(filepath):
    """Load tasks from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_task_url(task):
    """Generate URL for the task based on the site"""
    site = task['sites'][0]
    return TASK_URLS.get(site, task.get('start_url', '#'))

@app.route('/')
def index():
    # Load tasks from your JSON file
    # Update this path to where your tasks JSON file is located
    tasks = load_tasks(TASK_JSON_PATH)
    
    # Get unique sites and counts
    sites = list(set(task['sites'][0] for task in tasks))
    site_counts = {}
    for site in sites:
        site_counts[site] = sum(1 for task in tasks if task['sites'][0] == site)
    
    return render_template_string(
        TEMPLATE, 
        tasks=tasks, 
        sites=sorted(sites),
        site_counts=site_counts,
        get_task_url=get_task_url
    )

@app.route('/task/<int:task_id>')
def task_detail(task_id):
    """Show detailed view of a single task"""
    tasks = load_tasks(TASK_JSON_PATH)
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    
    if task:
        return f"<pre>{json.dumps(task, indent=2)}</pre>"
    else:
        return "Task not found", 404

if __name__ == '__main__':
    
    print("WebArena Task Viewer Server Starting...")
    print(f"Server will run on port: {TASK_VIEWER_PORT}")
    print("\nTask URLs:")
    for site, url in TASK_URLS.items():
        print(f"  {site}: {url}")
    print(f"\nTask JSON path: {TASK_JSON_PATH}")
    print()

    
    app.run(host='0.0.0.0', port=TASK_VIEWER_PORT, debug=True)
