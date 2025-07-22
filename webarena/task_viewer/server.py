import json
import os
from functools import lru_cache
from pathlib import Path
import urllib.parse as up

from flask import Flask, render_template_string, send_from_directory, request

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
TRACES_DIR = os.environ.get('TRACES_DIR', '../trajs')  # Default to sibling trajs directory

app = Flask(__name__)

# HTML template for the task viewer
TEMPLATE = Path('template.html').read_text()

@lru_cache(maxsize=1)
def load_tasks(filepath):
    """Load tasks from JSON file"""
    with open(filepath, 'r') as f:
        tasks = json.load(f)
    print(f"Loaded {len(tasks)} tasks from {filepath}")
    return tasks

@lru_cache(maxsize=1)
def load_trace_ids(trace_dir) -> set[str]:
    """Load the set of trace ids from the trace dir

    - trace files are named {trace_dir}/{task_id}.trace.zip
    """


    trace_ids = {int(f.stem.split('.')[0]) for f in Path(trace_dir).glob('*.trace.zip')}
    print(f"Loaded {len(trace_ids)} trace ids from {trace_dir}")
    return trace_ids

def get_task_url(task):
    """Generate URL for the task based on the site"""
    site = task['sites'][0]
    return TASK_URLS.get(site, task.get('start_url', '#'))

def get_trace_url(task_id):
    """Generate URL for viewing the trace (served from local laptop)"""
    # Always point to localhost:54321 for trace files
    # trace_file_url = f"http://[::]:54321/{task_id}.trace.zip"
    # 5432 has a flask app running serving the trace files
    trace_file_url = f"http://localhost:5432/traces/{task_id}.trace.zip"
    encoded_url = up.quote(trace_file_url, safe='')
    return f"https://trace.playwright.dev/?trace={encoded_url}"

@app.route('/')
def index():
    # Load tasks from your JSON file
    tasks = load_tasks(TASK_JSON_PATH)
    trace_ids = load_trace_ids(TRACES_DIR)

    # Add trace availability info to each task
    for task in tasks:
        task['has_trace'] = task['task_id'] in trace_ids
    
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
        get_task_url=get_task_url,
        get_trace_url=get_trace_url
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

@app.route('/traces/<path:filename>')
def serve_trace(filename):
    """Serve trace files with CORS headers"""
    traces_path = Path(TRACES_DIR).resolve()
    print(f"Serving trace file: {filename} from {traces_path}")
    response = send_from_directory(traces_path, filename, mimetype='application/zip')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response

if __name__ == '__main__':
    print("WebArena Task Viewer Server Starting...")
    print(f"Server will run on port: {TASK_VIEWER_PORT}")
    print("\nTask URLs:")
    for site, url in TASK_URLS.items():
        print(f"  {site}: {url}")
    print(f"\nTask JSON path: {TASK_JSON_PATH}")
    print(f"Traces directory: {Path(TRACES_DIR).resolve()}")
    
    # Check if traces directory exists
    traces_path = Path(TRACES_DIR)
    if traces_path.exists():
        trace_count = len(list(traces_path.glob("*.trace.zip")))
        print(f"Found {trace_count} trace files")
    else:
        print("WARNING: Traces directory not found!")
    
    print()
    
    app.run(host='0.0.0.0', port=TASK_VIEWER_PORT, debug=True)