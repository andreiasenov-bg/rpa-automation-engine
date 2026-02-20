
import re

with open('/repo/scripts/deployer.py', 'r') as f:
    lines = f.readlines()

# Find the last "Unknown path" in do_GET (line ~356)
# We need to find it between do_GET and do_OPTIONS
in_do_get = False
target_line = -1
for i, line in enumerate(lines):
    if 'def do_GET(self):' in line:
        in_do_get = True
    elif in_do_get and line.strip().startswith('def '):
        break
    elif in_do_get and '"Unknown path:' in line:
        target_line = i

if target_line > 0:
    # Replace the else block (target_line-1 is "else:", target_line is the json_response)
    indent = '        '
    new_code = [
        indent + 'else:\n',
        indent + '    # Proxy /api/ to backend\n',
        indent + '    if path.startswith("/api/") or path == "/api":\n',
        indent + '        self._proxy_to_backend()\n',
        indent + '        return\n',
        indent + '    # Serve frontend for all other paths\n',
        indent + '    if os.path.isdir(FRONTEND_DIR):\n',
        indent + '        self._serve_frontend()\n',
        indent + '        return\n',
        indent + '    self._json_response(404, {"error": f"Not found: {path}"})\n',
    ]
    # Replace the two lines (else: + json_response)
    lines[target_line-1:target_line+1] = new_code
    
    with open('/repo/scripts/deployer.py', 'w') as f:
        f.writelines(lines)
    print(f"Fixed do_GET fallback at line {target_line}")
    print(f"Total lines: {len(lines) + len(new_code) - 2}")
else:
    print("ERROR: Could not find target line")
