import json
import os
from functools import lru_cache
from pathlib import Path
import urllib.parse as up

from flask import Flask, render_template_string, send_from_directory, request

# Site URL constants from environment variables
SITE_URLS = {
    '__SHOPPING__': os.environ.get('SHOPPING_URL', 'http://localhost:7770'),
    '__SHOPPING_ADMIN__': os.environ.get('SHOPPING_ADMIN_URL', 'http://localhost:7780/admin'),
    '__MAP__': os.environ.get('MAP_URL', 'http://localhost:3000'),
    '__REDDIT__': os.environ.get('REDDIT_URL', 'http://localhost:9999'),
    '__GITLAB__': os.environ.get('GITLAB_URL', 'http://localhost:8023'),
    '__WIKIPEDIA__': os.environ.get('WIKIPEDIA_URL', 'http://localhost:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing')
}
TASK_VIEWER_PORT = int(os.environ.get('TASK_VIEWER_PORT', 5000))
TASK_JSON_PATH = os.environ.get('TASK_JSON_PATH', 'webarena_tasks.json')
TRACES_DIR = os.environ.get('TRACES_DIR', '../trajs')  # Default to sibling trajs directory
REVIEWED_JSON_PATH = os.environ.get('REVIEWED_JSON_PATH', 'reviewed_tasks.json')

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

def load_reviewed():
    """Load reviewed state and notes from disk (task_id -> {reviewed, notes})"""
    if not Path(REVIEWED_JSON_PATH).exists():
        return {}
    with open(REVIEWED_JSON_PATH, 'r') as f:
        return json.load(f)

def save_reviewed(reviewed):
    with open(REVIEWED_JSON_PATH, 'w') as f:
        json.dump(reviewed, f)

def get_task_url(task):
    """Generate URL for the task based on the site"""
    start_url = task.get('start_url', '#')  # eg "__GITLAB__", "__SHOPPING__/path/to/subpage"
    # replace __SITE__ with the corresponding URL
    for site, url in SITE_URLS.items():
        start_url = start_url.replace(site, url)
    return start_url

def get_trace_url(task_id):
    """Generate URL for viewing the trace (served from local laptop)"""
    # Always point to localhost:54321 for trace files
    # trace_file_url = f"http://[::]:54321/{task_id}.trace.zip"
    # 5432 has a flask app running serving the trace files
    trace_file_url = f"http://localhost:5432/traces/{task_id}.trace.zip"
    encoded_url = up.quote(trace_file_url, safe='')
    return f"https://trace.playwright.dev/?trace={encoded_url}"

@app.route('/reviewed/<int:task_id>', methods=['POST'])
def set_reviewed(task_id):
    reviewed = load_reviewed()
    data = request.get_json(force=True)
    entry = reviewed.get(str(task_id), {})
    entry['reviewed'] = bool(data.get('reviewed', False))
    entry['notes'] = entry.get('notes', '')
    reviewed[str(task_id)] = entry
    save_reviewed(reviewed)
    return {'success': True, 'task_id': task_id, 'reviewed': entry['reviewed']}

@app.route('/notes/<int:task_id>', methods=['GET', 'POST'])
def notes(task_id):
    reviewed = load_reviewed()
    key = str(task_id)
    if request.method == 'POST':
        data = request.get_json(force=True)
        entry = reviewed.get(key, {})
        entry['notes'] = data.get('notes', '')
        entry['reviewed'] = entry.get('reviewed', False)
        reviewed[key] = entry
        save_reviewed(reviewed)
        return {'success': True, 'task_id': task_id, 'notes': entry['notes']}
    else:
        entry = reviewed.get(key, {})
        return {'success': True, 'task_id': task_id, 'notes': entry.get('notes', '')}

@app.route('/')
def index():
    # Load tasks from your JSON file
    tasks = load_tasks(TASK_JSON_PATH)
    trace_ids = load_trace_ids(TRACES_DIR)
    reviewed = load_reviewed()

    # Add trace, reviewed, and notes info to each task
    for task in tasks:
        entry = reviewed.get(str(task['task_id']), {})
        task['has_trace'] = task['task_id'] in trace_ids
        task['reviewed'] = entry.get('reviewed', False)
        task['notes'] = entry.get('notes', '')
    
    # Get unique sites and counts (support multiple sites per task)
    from collections import Counter
    all_sites = []
    for task in tasks:
        all_sites.extend(task['sites'])
    sites = list(set(all_sites))
    site_counts = dict(Counter(all_sites))
    
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
    for site, url in SITE_URLS.items():
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