import os
import subprocess
import sys
import pytest
import isolated_runner as runner
from workspace_paths import confined_path

def test_path_traversal_and_symlink_escape(tmp_path):
    root = tmp_path/'workspace'
    root.mkdir()
    outside = tmp_path/'outside'
    outside.mkdir()
    assert confined_path(root, 'nested/file.txt') == root/'nested/file.txt'
    with pytest.raises(ValueError):
        confined_path(root, '../outside/file')
    try:
        (root/'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Symlinks unavailable')
    with pytest.raises(ValueError):
        confined_path(root, 'link/file')

def test_execution_disabled_without_owner_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv('AI_AGENT_ENABLE_CODE', raising=False)
    with pytest.raises(RuntimeError, match='disabled'):
        runner.run_python('print(1)', 'task.py', 1, tmp_path)

def test_no_host_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_AGENT_ENABLE_CODE', 'true')
    monkeypatch.setenv('AI_AGENT_DOCKER_IMAGE', 'trusted:local')
    monkeypatch.setattr(runner.shutil, 'which', lambda _: None)
    with pytest.raises(RuntimeError, match='never used'):
        runner.run_python('print(1)', 'task.py', 1, tmp_path)

def test_container_contract_does_not_mount_workspace_or_forward_tokens(tmp_path):
    command = runner.docker_command('docker', 'trusted:local', tmp_path/'job', 'task.py', 'job')
    for option, value in [('--network','none'),('--pull','never'),('--cap-drop','ALL'),('--memory','512m')]:
        assert command[command.index(option)+1] == value
    assert '--read-only' in command
    assert '--privileged' not in command and '--env' not in command and '--env-file' not in command
    assert command.count('--mount') == 1
    assert 'dst=/workspace' in command[command.index('--mount')+1]
    assert command[-3:] == ['trusted:local','-I','task.py']

def test_bounded_output_and_timeout():
    assert runner.bounded_run([sys.executable, '-c', 'print("ok")'], 5) == (0, 'ok\n')
    with pytest.raises(RuntimeError, match='64 KiB'):
        runner.bounded_run([sys.executable, '-c', 'print("x"*100000)'], 5)
    with pytest.raises(TimeoutError):
        runner.bounded_run([sys.executable, '-c', 'import time; time.sleep(10)'], .05)

def test_container_cleanup_after_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_AGENT_ENABLE_CODE', 'true')
    monkeypatch.setenv('AI_AGENT_DOCKER_IMAGE', 'trusted:local')
    monkeypatch.setattr(runner.shutil, 'which', lambda _: '/bin/docker')
    calls=[]
    monkeypatch.setattr(runner.subprocess, 'run', lambda cmd, **kw: calls.append(cmd))
    def fail(*args):
        raise TimeoutError('timed out')
    monkeypatch.setattr(runner, 'bounded_run', fail)
    with pytest.raises(TimeoutError):
        runner.run_python('print(1)', 'task.py', 1, tmp_path)
    assert calls[-1][1:3] == ['rm','-f']
