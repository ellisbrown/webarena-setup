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
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WebArena Task Viewer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .task-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .task-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .task-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .task-id {
            font-size: 14px;
            color: #666;
            font-weight: bold;
        }
        .site-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .site-shopping_admin { background: #e3f2fd; color: #1976d2; }
        .site-map { background: #e8f5e9; color: #388e3c; }
        .site-reddit { background: #fff3e0; color: #f57c00; }
        .site-gitlab { background: #fce4ec; color: #c2185b; }
        .site-wikipedia { background: #f3e5f5; color: #7b1fa2; }
        
        .task-intent {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin: 15px 0;
            line-height: 1.4;
        }
        .task-details {
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 14px;
        }
        .detail-row {
            margin: 8px 0;
            display: flex;
            align-items: flex-start;
        }
        .detail-label {
            font-weight: bold;
            min-width: 120px;
            color: #555;
        }
        .detail-value {
            flex: 1;
            color: #333;
        }
        .expected-answer {
            background: #e8f5e9;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            border-left: 3px solid #4caf50;
        }
        .task-actions {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
            text-align: center;
            transition: background 0.2s;
        }
        .btn-primary {
            background: #007bff;
            color: white;
        }
        .btn-primary:hover {
            background: #0056b3;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #545b62;
        }
        .filter-section {
            margin: 20px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 6px 14px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background: #f8f9fa;
        }
        .filter-btn.active {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        .stats {
            margin: 20px 0;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .stat-card {
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>WebArena Task Viewer</h1>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ tasks|length }}</div>
            <div class="stat-label">Total Tasks</div>
        </div>
        {% for site, count in site_counts.items() %}
        <div class="stat-card">
            <div class="stat-value">{{ count }}</div>
            <div class="stat-label">{{ site|replace('_', ' ')|title }}</div>
        </div>
        {% endfor %}
    </div>
    
    <div class="filter-section">
        <h3>Filter by Site:</h3>
        <div class="filter-buttons">
            <button class="filter-btn active" onclick="filterTasks('all')">All</button>
            {% for site in sites %}
            <button class="filter-btn" onclick="filterTasks('{{ site }}')">{{ site|replace('_', ' ')|title }}</button>
            {% endfor %}
        </div>
    </div>
    
    <div class="task-grid">
        {% for task in tasks %}
        <div class="task-card" data-site="{{ task.sites[0] }}">
            <div class="task-header">
                <span class="task-id">Task #{{ task.task_id }}</span>
                <span class="site-badge site-{{ task.sites[0] }}">{{ task.sites[0]|replace('_', ' ') }}</span>
            </div>
            
            <div class="task-intent">{{ task.intent }}</div>
            
            <div class="task-details">
                <div class="detail-row">
                    <span class="detail-label">Template:</span>
                    <span class="detail-value">{{ task.intent_template }}</span>
                </div>
                
                {% if task.instantiation_dict %}
                <div class="detail-row">
                    <span class="detail-label">Parameters:</span>
                    <span class="detail-value">
                        {% for key, value in task.instantiation_dict.items() %}
                        {{ key }}: {{ value }}{% if not loop.last %}, {% endif %}
                        {% endfor %}
                    </span>
                </div>
                {% endif %}
                
                <div class="expected-answer">
                    <strong>Expected Answer:</strong><br>
                    {% if task.eval.reference_answers.exact_match %}
                        {{ task.eval.reference_answers.exact_match }}
                    {% elif task.eval.reference_answers.fuzzy_match %}
                        {{ task.eval.reference_answers.fuzzy_match[0] }}
                    {% elif task.eval.reference_answers.must_include %}
                        {{ task.eval.reference_answers.must_include|join(', ') }}
                    {% endif %}
                </div>
            </div>
            
            <div class="task-actions">
                <a href="{{ get_task_url(task) }}" target="_blank" class="btn btn-primary">Try Task</a>
                <button class="btn btn-secondary" onclick="showTaskDetails({{ task.task_id }})">View JSON</button>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <script>
        function filterTasks(site) {
            const cards = document.querySelectorAll('.task-card');
            const buttons = document.querySelectorAll('.filter-btn');
            
            // Update button states
            buttons.forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.toLowerCase() === site || 
                    (site === 'all' && btn.textContent === 'All')) {
                    btn.classList.add('active');
                }
            });
            
            // Filter cards
            cards.forEach(card => {
                if (site === 'all' || card.dataset.site === site) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        
        function showTaskDetails(taskId) {
            // In a real implementation, this would show a modal with full JSON
            alert('Task JSON viewer not implemented. Task ID: ' + taskId);
        }
    </script>
</body>
</html>
"""

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
