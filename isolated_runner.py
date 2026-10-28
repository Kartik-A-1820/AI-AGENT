"""Opt-in, fail-closed Docker execution. No host Python fallback."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import uuid
from workspace_paths import confined_path

OUTPUT_LIMIT = 64 * 1024

def bounded_run(command, timeout):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    chunks, total = [], 0
    overflow = threading.Event()
    def read():
        nonlocal total
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            remaining = max(0, OUTPUT_LIMIT - total)
            chunks.append(chunk[:remaining])
            total += len(chunk)
            if total > OUTPUT_LIMIT:
                overflow.set()
                process.kill()
                break
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise TimeoutError('Code execution timed out')
    finally:
        reader.join(timeout=2)
        process.stdout.close()
    if overflow.is_set():
        raise RuntimeError('Code output exceeded 64 KiB')
    return process.returncode, b''.join(chunks).decode('utf-8', errors='replace')

def docker_command(docker, image, job, filename, name):
    uid = os.getuid() if hasattr(os, 'getuid') and os.getuid() != 0 else 65534
    gid = os.getgid() if hasattr(os, 'getgid') and os.getgid() != 0 else 65534
    return [docker, 'run', '--name', name, '--rm', '--pull', 'never', '--network', 'none',
        '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--user', f'{uid}:{gid}', '--pids-limit', '64', '--memory', '512m', '--memory-swap', '512m',
        '--cpus', '1', '--ulimit', 'fsize=20971520:20971520', '--log-driver', 'none',
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m', '--mount', f'type=bind,src={job},dst=/workspace',
        '--workdir', '/workspace', '--entrypoint', 'python', image, '-I', filename]

def run_python(code, filename, timeout, workspace, input_files=()):
    if os.environ.get('AI_AGENT_ENABLE_CODE', '').lower() != 'true':
        raise RuntimeError('Code execution disabled. Owner must configure AI_AGENT_ENABLE_CODE and a trusted Docker image.')
    image = os.environ.get('AI_AGENT_DOCKER_IMAGE', '')
    if not image or image.startswith('-') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./_:@-]*', image):
        raise ValueError('Configure AI_AGENT_DOCKER_IMAGE with a trusted local image, preferably pinned by digest')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.py', filename):
        raise ValueError('Script filename must be a simple .py basename')
    docker = shutil.which('docker')
    if docker is None:
        raise RuntimeError('Docker unavailable; host execution is never used')
    subprocess.run([docker, 'image', 'inspect', image], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    workspace = Path(workspace).resolve()
    job = confined_path(workspace, '_jobs/' + uuid.uuid4().hex)
    job.mkdir(parents=True)
    # Host root uses an unprivileged container UID; this directory contains only
    # explicitly selected inputs and outputs, never credentials or assistant state.
    job.chmod(0o777)
    if len(input_files) > 10:
        raise ValueError('At most 10 input files are allowed')
    names = {filename}
    for item in input_files:
        source = confined_path(workspace, item)
        if not source.is_file() or source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError('Inputs must be files no larger than 20 MiB')
        if source.name in names:
            raise ValueError('Input basenames must be unique and differ from the script name')
        names.add(source.name)
        shutil.copyfile(source, job / source.name)
        (job / source.name).chmod(0o644)
    script = job / filename
    script.write_text(code, encoding='utf-8')
    script.chmod(0o644)
    name = 'ai-agent-' + uuid.uuid4().hex
    try:
        status, output = bounded_run(docker_command(docker, image, job, filename, name), max(1, min(timeout, 900)))
        if status in (125, 126, 127):
            raise RuntimeError('Container startup failed; no host fallback. Check the Docker image and daemon.')
        return f'exit_code={status}\noutput_directory={job}\n{output[-12000:]}'
    finally:
        # Killing the Docker client alone does not stop a running container.
        subprocess.run([docker, 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
