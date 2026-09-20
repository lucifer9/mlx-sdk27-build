"""Validate packaging and NAX build evidence without claiming M5 correctness."""

import email
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    wheels = sorted(Path("wheelhouse").glob("*.whl"))
    if len(wheels) != 2:
        raise RuntimeError(f"Expected exactly two wheels, got {wheels}")
    records = []
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            metadata_files = [n for n in names if n.endswith(".dist-info/METADATA")]
            if len(metadata_files) != 1:
                raise RuntimeError(f"Unexpected metadata layout: {wheel}")
            metadata = email.message_from_bytes(archive.read(metadata_files[0]))
            name = metadata["Name"]
            if "arm64" not in wheel.name or "macosx" not in wheel.name:
                raise RuntimeError(f"Not an ARM64 macOS wheel: {wheel}")
            if name == "mlx-metal":
                if not any(n.endswith("mlx.metallib") for n in names):
                    raise RuntimeError("Metal backend missing mlx.metallib")
                if not any(n.endswith("libmlx.dylib") for n in names):
                    raise RuntimeError("Metal backend missing libmlx.dylib")
            elif name == "mlx":
                if not any(n.endswith(".so") and "/core" in n for n in names):
                    raise RuntimeError("Frontend missing Python extension")
            else:
                raise RuntimeError(f"Unexpected distribution {name}")
            records.append(
                {
                    "file": wheel.name,
                    "distribution": name,
                    "version": metadata["Version"],
                    "sha256": sha256(wheel),
                    "size_bytes": wheel.stat().st_size,
                    "members": names,
                }
            )
    if {r["distribution"] for r in records} != {"mlx", "mlx-metal"}:
        raise RuntimeError("Missing frontend/backend pair")
    if len({r["version"] for r in records}) != 1:
        raise RuntimeError("Frontend/backend versions differ")
    if sum(r["size_bytes"] for r in records) > 400 * 1024**2:
        raise RuntimeError("Wheel pair exceeds experiment's 400 MiB upload cap")
    build = Path("source/build")
    nax_objects = list(build.rglob("gated_delta_update_nax.air"))
    if not nax_objects or not all(p.stat().st_size > 0 for p in nax_objects):
        raise RuntimeError("No compiled GDN NAX object found")
    flags = list(build.rglob("flags.make"))
    if not flags:
        raise RuntimeError("Missing generated compiler flags")
    if any("MLX_METAL_NO_NAX" in p.read_text() for p in flags):
        raise RuntimeError("NAX was disabled")
    cache = Path("evidence/cmake-cache.txt").read_text()
    for expected in ("MLX_METAL_JIT:BOOL=OFF", "MLX_BUILD_METAL:BOOL=ON"):
        if expected not in cache:
            raise RuntimeError(f"Missing build setting: {expected}")
    binaries = [p for p in build.rglob("libmlx.dylib") if p.is_file()]
    if not binaries:
        raise RuntimeError("Cannot inspect backend architecture")
    for binary in binaries:
        arches = subprocess.check_output(
            ["lipo", "-archs", str(binary)], text=True
        ).strip()
        if arches != "arm64":
            raise RuntimeError(f"Unexpected backend architecture: {arches}")
    manifest = {
        "source_sha": os.environ["MLX_SOURCE_SHA"],
        "experiment_sha": Path("evidence/experiment-sha.txt").read_text().strip(),
        "patch_sha256": sha256(Path("patches/mlx-sdk27-gdn-addrspace.patch")),
        "xcode_build": os.environ["EXPECTED_XCODE_BUILD"],
        "deployment_target": os.environ["MACOSX_DEPLOYMENT_TARGET"],
        "cmake_args": os.environ["CMAKE_ARGS"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "wheels": records,
        "m5_runtime_verified": False,
    }
    text = json.dumps(manifest, indent=2) + "\n"
    Path("evidence/manifest.json").write_text(text)
    Path("wheelhouse/manifest.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
