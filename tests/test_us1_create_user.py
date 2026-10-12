import subprocess
import os

def test_us1_create_user_vitest_suite():
    """Chạy toàn bộ unit test Vitest của US1 và xác nhận 100% test cases passed."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cmd = "npx vitest run src/features/us1_create_user/userService.test.ts"
    result = subprocess.run(cmd, shell=True, cwd=project_root, capture_output=True, text=True)
    
    assert result.returncode == 0, f"Vitest failed with output:\n{result.stdout}\n{result.stderr}"
    assert "12 passed (12)" in result.stdout or "passed" in result.stdout
