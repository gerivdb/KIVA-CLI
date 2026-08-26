import os
import subprocess

result = subprocess.run([
    'python', 'test_registry_full.py'
], capture_output=True, text=True, timeout=30, shell=True, env={**os.environ})

print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)