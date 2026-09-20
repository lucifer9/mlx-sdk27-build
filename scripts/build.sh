#!/usr/bin/env bash
set -euo pipefail
root="$PWD"
uv venv --python 3.12.14 .build-venv
uv pip sync --require-hashes --python .build-venv/bin/python build-requirements.txt
uv pip freeze --python .build-venv/bin/python > evidence/build-packages.txt
export PATH="$root/.build-venv/bin:$PATH"
cd source
python setup.py clean --all
MLX_BUILD_FRONTEND_PACKAGE=1 python -m build --no-isolation --wheel
mv dist/mlx-*.whl "$root/wheelhouse/"
python setup.py clean --all
MLX_BUILD_BACKEND_PACKAGE=1 python -m build --no-isolation --wheel
mv dist/mlx_metal-*.whl "$root/wheelhouse/"
# Keep the final build cache/flags, not gigabytes of intermediate objects.
while IFS= read -r cache; do
  printf '\n### %s\n' "$cache" >> "$root/evidence/cmake-cache.txt"
  cat "$cache" >> "$root/evidence/cmake-cache.txt"
done < <(find build -name CMakeCache.txt -type f)
