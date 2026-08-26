import subprocess

result = subprocess.run(['cmd', '/c', 'python', '-c', 'import sys; print("About to exit with 1"); sys.exit(1)'], capture_output=True, text=True, timeout=10)
print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)