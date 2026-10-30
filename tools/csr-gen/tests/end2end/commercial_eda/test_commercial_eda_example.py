import subprocess
from pathlib import Path


def test_commercial_eda_script() -> None:
    script = Path(__file__).with_name("test.sh")

    result = subprocess.run(
        [str(script)],
        check=False,
        cwd=script.parent,
    )

    assert result.returncode == 0
