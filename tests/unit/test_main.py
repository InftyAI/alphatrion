import subprocess
import sys


def test_main():
    process = subprocess.run(
        [sys.executable, "-m", "alphatrion.main"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0
    assert "Hello, AlphaTrion!" in process.stdout
