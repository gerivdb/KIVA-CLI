import os
import subprocess

os.environ['OUTPUT_DIR'] = 'D:/DO/WEB/TOOLS/reports/test-env'
result = subprocess.run(['python', '-c', 'import os; print(os.environ.get("OUTPUT_DIR"))'], capture_output=True, text=True, env={**os.environ})
print('stdout:', result.stdout)
print('stderr:', result.stderr)