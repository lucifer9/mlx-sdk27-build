"""Package acceptance checks use synthetic wheels; no Metal runtime required."""

import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "verify", Path(__file__).resolve().parents[1] / "scripts/verify.py"
)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, previous)
        for name in ("wheelhouse", "evidence", "patches", "source/build"):
            Path(name).mkdir(parents=True)
        Path("evidence/experiment-sha.txt").write_text("experiment")
        Path("patches/mlx-sdk27-gdn-addrspace.patch").write_text("patch")
        Path("evidence/cmake-cache.txt").write_text(
            "MLX_METAL_JIT:BOOL=OFF\nMLX_BUILD_METAL:BOOL=ON\n"
        )
        Path("source/build/gated_delta_update_nax.air").write_bytes(b"compiled")
        Path("source/build/flags.make").write_text("CXX_FLAGS = -O3")
        Path("source/build/libmlx.dylib").write_bytes(b"backend")
        env = dict.fromkeys(
            (
                "MLX_SOURCE_SHA",
                "EXPECTED_XCODE_BUILD",
                "MACOSX_DEPLOYMENT_TARGET",
                "CMAKE_ARGS",
                "GITHUB_RUN_ID",
                "GITHUB_RUN_ATTEMPT",
            ),
            "test",
        )
        self.enterContext(patch.dict(os.environ, env))
        self.enterContext(
            patch.object(verify.subprocess, "check_output", return_value="arm64\n")
        )
        self.enterContext(patch("builtins.print"))
        self.wheel("mlx", "1.0", ["mlx/core.cpython-312-darwin.so"])
        self.wheel("mlx-metal", "1.0", ["mlx/lib/libmlx.dylib", "mlx/lib/mlx.metallib"])

    def wheel(self, name, version, members):
        filename = name.replace("-", "_") + "-1.0-cp312-cp312-macosx_26_2_arm64.whl"
        with zipfile.ZipFile(Path("wheelhouse") / filename, "w") as archive:
            archive.writestr(
                "package.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n"
            )
            for member in members:
                archive.writestr(member, b"fixture")

    def test_pair_records_hashes_without_claiming_runtime_validation(self):
        verify.main()
        manifest = json.loads(Path("wheelhouse/manifest.json").read_text())
        self.assertFalse(manifest["m5_runtime_verified"])
        self.assertEqual(len(manifest["wheels"]), 2)
        for record in manifest["wheels"]:
            self.assertEqual(
                record["sha256"], verify.sha256(Path("wheelhouse") / record["file"])
            )

    def test_missing_metallib_rejected(self):
        self.wheel("mlx-metal", "1.0", ["mlx/lib/libmlx.dylib"])
        with self.assertRaisesRegex(RuntimeError, "missing mlx.metallib"):
            verify.main()

    def test_version_mismatch_rejected(self):
        self.wheel("mlx", "2.0", ["mlx/core.cpython-312-darwin.so"])
        with self.assertRaisesRegex(RuntimeError, "versions differ"):
            verify.main()

    def test_disabled_nax_rejected(self):
        Path("source/build/flags.make").write_text("-DMLX_METAL_NO_NAX")
        with self.assertRaisesRegex(RuntimeError, "NAX was disabled"):
            verify.main()

    def test_wrong_binary_architecture_rejected(self):
        with (
            patch.object(verify.subprocess, "check_output", return_value="x86_64\n"),
            self.assertRaisesRegex(RuntimeError, "Unexpected backend architecture"),
        ):
            verify.main()


if __name__ == "__main__":
    unittest.main()
