import subprocess

# Test with Windows cmd.exe quoting - use single quotes inside
cmd = 'python -c "import sys; print(\'hello\'); sys.exit(1)"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)