import subprocess

subproc= subprocess.run(["echo", "arguments"], capture_output=True)
print(subproc.stdout)