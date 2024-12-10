import os
import shutil

# Create workflows directory
workflows_dir = os.path.join(os.path.dirname(__file__), 'workflows')
os.makedirs(workflows_dir, exist_ok=True)

# Move the workflow file
src = os.path.join(os.path.dirname(__file__), 'Simple Flux Workflow.json')
dst = os.path.join(workflows_dir, 'Simple Flux Workflow.json')
if os.path.exists(src):
    shutil.move(src, dst)
