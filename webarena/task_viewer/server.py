import json
import os
from functools import lru_cache
from pathlib import Path
import urllib.parse as up

from flask import Flask, render_template_string, send_from_directory, request, jsonify

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
TASK_FILES_DIR = os.environ.get('TASK_FILES_DIR', 'taskfiles')  # Directory containing task JSON files
TRACES_DIR = os.environ.get('TRACES_DIR', '../trajs')  # Default to sibling trajs directory

app = Flask(__name__)

# HTML template for the task viewer
TEMPLATE = Path('template.html').read_text()

def get_available_task_files():
    """Get list of available task JSON files in the taskfiles directory"""
    task_files_dir = Path(TASK_FILES_DIR)
    if not task_files_dir.exists():
        return []
    
    json_files = list(task_files_dir.glob('*.json'))
    return [f.name for f in json_files]

def get_task_file_path(filename):
    """Get full path to a task file"""
    return Path(TASK_FILES_DIR) / filename

@lru_cache(maxsize=10)  # Cache multiple task files
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

def load_reviewed(task_file_name):
    """Load reviewed state and notes from disk (task_id -> {reviewed, notes})"""
    # Create reviewed file name based on task file name
    reviewed_file = f"reviewed_{task_file_name}"
    reviewed_path = Path(reviewed_file)
    
    if not reviewed_path.exists():
        return {}
    with open(reviewed_path, 'r') as f:
        return json.load(f)

def save_reviewed(reviewed, task_file_name):
    """Save reviewed state and notes to disk"""
    reviewed_file = f"reviewed_{task_file_name}"
    with open(reviewed_file, 'w') as f:
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

@app.route('/api/task-files')
def get_task_files():
    """API endpoint to get available task files"""
    files = get_available_task_files()
    return jsonify({'files': files})

@app.route('/reviewed/<int:task_id>', methods=['POST'])
def set_reviewed(task_id):
    # Get task file from request data
    data = request.get_json(force=True)
    task_file = data.get('task_file', '')
    
    if not task_file:
        return {'success': False, 'error': 'No task file specified'}, 400
    
    reviewed = load_reviewed(task_file)
    entry = reviewed.get(str(task_id), {})
    entry['reviewed'] = bool(data.get('reviewed', False))
    entry['notes'] = entry.get('notes', '')
    reviewed[str(task_id)] = entry
    save_reviewed(reviewed, task_file)
    return {'success': True, 'task_id': task_id, 'reviewed': entry['reviewed']}

@app.route('/notes/<int:task_id>', methods=['GET', 'POST'])
def notes(task_id):
    # Get task file from query parameter or request data
    if request.method == 'POST':
        data = request.get_json(force=True)
        task_file = data.get('task_file', '')
    else:
        task_file = request.args.get('task_file', '')
    
    if not task_file:
        return {'success': False, 'error': 'No task file specified'}, 400
    
    reviewed = load_reviewed(task_file)
    key = str(task_id)
    if request.method == 'POST':
        entry = reviewed.get(key, {})
        entry['notes'] = data.get('notes', '')
        entry['reviewed'] = entry.get('reviewed', False)
        reviewed[key] = entry
        save_reviewed(reviewed, task_file)
        return {'success': True, 'task_id': task_id, 'notes': entry['notes']}
    else:
        entry = reviewed.get(key, {})
        return {'success': True, 'task_id': task_id, 'notes': entry.get('notes', '')}

@app.route('/')
def index():
    # Get selected task file from query parameter or use first available
    selected_file = request.args.get('task_file', '')
    available_files = get_available_task_files()
    
    if not available_files:
        return "No task files found in taskfiles directory", 404
    
    # If no file selected or selected file doesn't exist, use the first available
    if not selected_file or selected_file not in available_files:
        selected_file = available_files[0]
    
    # Load tasks from selected file
    task_file_path = get_task_file_path(selected_file)
    tasks = load_tasks(str(task_file_path))
    trace_ids = load_trace_ids(TRACES_DIR)
    reviewed = load_reviewed(selected_file)

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
        available_files=available_files,
        selected_file=selected_file,
        get_task_url=get_task_url,
        get_trace_url=get_trace_url
    )

@app.route('/task/<int:task_id>')
def task_detail(task_id):
    """Show detailed view of a single task"""
    # Get selected task file from query parameter or use first available
    selected_file = request.args.get('task_file', '')
    available_files = get_available_task_files()
    
    if not available_files:
        return "No task files found", 404
    
    if not selected_file or selected_file not in available_files:
        selected_file = available_files[0]
    
    task_file_path = get_task_file_path(selected_file)
    tasks = load_tasks(str(task_file_path))
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
    print(f"\nTask files directory: {Path(TASK_FILES_DIR).resolve()}")
    print(f"Traces directory: {Path(TRACES_DIR).resolve()}")
    
    # Check available task files
    available_files = get_available_task_files()
    if available_files:
        print(f"Found {len(available_files)} task files:")
        for file in available_files:
            print(f"  - {file}")
            # Check if reviewed file exists for this task file
            reviewed_file = f"reviewed_{file}"
            if Path(reviewed_file).exists():
                print(f"    (has reviewed data: {reviewed_file})")
    else:
        print("WARNING: No task files found in taskfiles directory!")
    
    # Check if traces directory exists
    traces_path = Path(TRACES_DIR)
    if traces_path.exists():
        trace_count = len(list(traces_path.glob("*.trace.zip")))
        print(f"Found {trace_count} trace files")
    else:
        print("WARNING: Traces directory not found!")
    
    print()
    
    app.run(host='0.0.0.0', port=TASK_VIEWER_PORT, debug=True)