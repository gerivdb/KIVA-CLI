import subprocess
import os

# Test simple command
result = subprocess.run('python -c "import sys; print(\"hello\"); sys.exit(1)"', shell=True, capture_output=True, text=True, timeout=10)
print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)