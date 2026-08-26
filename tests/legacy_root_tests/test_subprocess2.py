import subprocess

result = subprocess.run([
    'python', 'test_subprocess.py'
], capture_output=True, text=True, shell=False, timeout=30)

print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)