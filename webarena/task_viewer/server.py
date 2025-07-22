import json
import os
from functools import lru_cache
from pathlib import Path
import subprocess
import time
from flask import Flask, render_template_string, send_from_directory, request, jsonify

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

# Track running trace viewers
trace_viewers = {}

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
    """Generate URL for viewing the trace"""
    # Return a URL that will trigger our launch endpoint
    return f"/launch-trace/{task_id}"

def find_free_port(start_port=9000):
    """Find a free port starting from start_port"""
    import socket
    port = start_port
    while port < start_port + 100:  # Try 100 ports
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("No free ports found")

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

@app.route('/launch-trace/<int:task_id>')
def launch_trace(task_id):
    """Launch playwright trace viewer for a specific task"""
    trace_path = Path(TRACES_DIR).absolute() / f"{task_id}.trace.zip"
    
    if not trace_path.exists():
        return "Trace not found", 404
    
    # Check if viewer already running for this task
    if task_id in trace_viewers and trace_viewers[task_id]['process'].poll() is None:
        # Viewer already running, redirect to it
        port = trace_viewers[task_id]['port']
        viewer_url = f"http://{request.host.split(':')[0]}:{port}"
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
            <h2>Trace Viewer Already Running</h2>
            <p>The trace viewer for task #{task_id} is already running on port {port}</p>
            <a href="{viewer_url}" target="_blank" style="display: inline-block; margin: 20px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">Open Trace Viewer</a>
            <br><br>
            <a href="/" style="color: #666;">← Back to Task List</a>
        </body>
        </html>
        """
    
    try:
        # Find a free port
        port = find_free_port()
        
        # Launch playwright trace viewer
        cmd = [
            "playwright", "show-trace",
            str(trace_path.absolute()),
            "--host", "0.0.0.0",
            "--port", str(port)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Store process info
        trace_viewers[task_id] = {
            'process': process,
            'port': port,
            'started_at': time.time()
        }
        
        # Wait a moment for the server to start
        time.sleep(1)
        
        # Generate viewer URL
        viewer_url = f"http://{request.host.split(':')[0]}:{port}"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
            <h2>Trace Viewer Launched</h2>
            <p>Playwright trace viewer for task #{task_id} is now running on port {port}</p>
            <a href="{viewer_url}" target="_blank" style="display: inline-block; margin: 20px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Open Trace Viewer</a>
            <br><br>
            <p style="color: #666;">The viewer will remain open until you close it or stop this server.</p>
            <a href="/" style="color: #666;">← Back to Task List</a>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 40px;">
            <h2>Error Launching Trace Viewer</h2>
            <p style="color: #dc3545;">Failed to launch trace viewer: {str(e)}</p>
            <p>Make sure Playwright is installed: <code>npm install -g playwright</code></p>
            <br>
            <a href="/" style="color: #666;">← Back to Task List</a>
        </body>
        </html>
        """

@app.route('/trace-status')
def trace_status():
    """Get status of running trace viewers"""
    status = {}
    for task_id, info in list(trace_viewers.items()):
        if info['process'].poll() is None:
            status[task_id] = {
                'port': info['port'],
                'running': True,
                'uptime': int(time.time() - info['started_at'])
            }
        else:
            # Process ended, remove from list
            del trace_viewers[task_id]
    
    return jsonify(status)

def cleanup_trace_viewers():
    """Clean up any running trace viewer processes"""
    for task_id, info in trace_viewers.items():
        if info['process'].poll() is None:
            info['process'].terminate()
            print(f"Terminated trace viewer for task {task_id}")

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
    
    # Check if playwright is installed
    try:
        subprocess.run(["playwright", "--version"], capture_output=True, check=True)
        print("\n✓ Playwright CLI is installed")
    except:
        print("\n⚠ WARNING: Playwright CLI not found!")
        print("  Install with: npm install -g playwright")
    
    print("\nTrace viewer mode: Launch local Playwright viewers on-demand")
    print()
    
    try:
        app.run(host='0.0.0.0', port=TASK_VIEWER_PORT, debug=True)
    finally:
        cleanup_trace_viewers()