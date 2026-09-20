"""Exercise toolchain setup when xcrun finds a nonfunctional Metal shim."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ToolchainTests(unittest.TestCase):
    def test_installs_component_when_metal_path_exists_but_toolchain_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("bin", "developer", "evidence", "patches"):
                (root / name).mkdir()
            shutil.copy(
                ROOT / "patches/mlx-sdk27-gdn-addrspace.patch", root / "patches"
            )
            commands = {
                "git": 'printf "%s\\n" "$MLX_SOURCE_SHA"',
                "uname": "echo arm64",
                "sw_vers": "echo macOS-test",
                "sysctl": "echo hardware-test",
                "uv": "echo uv-test",
                "xcodebuild": """
if [[ "$1" == -version ]]; then
  printf 'Xcode 27.0\\nBuild version 27A266a\\n'
elif [[ "$1" == -downloadComponent && "$2" == MetalToolchain ]]; then
  touch "$TEST_ROOT/component-installed"
else
  exit 99
fi
""",
                "xcrun": """
case "$*" in
  '--sdk macosx --show-sdk-version') echo 27.0 ;;
  '--sdk macosx --find metal') echo /shim/metal ;;
  '--sdk macosx --show-sdk-path') echo /SDK ;;
  'clang --version') echo clang ;;
  '--sdk macosx metal --version')
    if [[ -f "$TEST_ROOT/component-installed" ]]; then
      echo Metal-compiler
    else
      echo "error: cannot execute tool 'metal' due to missing Metal Toolchain" >&2
      exit 1
    fi ;;
  *) exit 98 ;;
esac
""",
            }
            for name, body in commands.items():
                executable = root / "bin" / name
                executable.write_text("#!/bin/bash\nset -eu\n" + body + "\n")
                executable.chmod(0o755)
            env = {
                **os.environ,
                "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
                "TEST_ROOT": str(root),
                "MLX_SOURCE_SHA": "fixture-sha",
                "DEVELOPER_DIR": str(root / "developer"),
                "EXPECTED_XCODE_BUILD": "27A266a",
                "MACOSX_DEPLOYMENT_TARGET": "26.2",
                "CMAKE_ARGS": "fixture",
            }
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/toolchain.sh")],
                cwd=root,
                env=env,
                capture_output=True,
                check=False,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / "component-installed").exists())
            self.assertIn("Metal-compiler", result.stdout)


if __name__ == "__main__":
    unittest.main()
