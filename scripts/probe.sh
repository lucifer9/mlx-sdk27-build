#!/usr/bin/env bash
set -euo pipefail
root="$PWD"
cd source
kernel=mlx/backend/metal/kernels/gated_delta_update_nax.metal
flags=(-x metal -Wall -Wextra -fno-fast-math -Wno-c++17-extensions -Wno-c++20-extensions -Wmetal-addr-spaces)
# Test the compiler default and the actual release deployment target separately.
for variant in default target26.2; do
  extra=()
  if [[ "$variant" == target26.2 ]]; then
    extra=(-mmacosx-version-min=26.2)
  fi
  status=0
  env -u MACOSX_DEPLOYMENT_TARGET xcrun -sdk macosx metal "${flags[@]}" ${extra[@]+"${extra[@]}"} \
    -c "$kernel" -I . -o "$RUNNER_TEMP/gdn-stock-$variant.air" \
    > "$root/evidence/stock-$variant.log" 2>&1 || status=$?
  printf '%s stock exit=%s\n' "$variant" "$status" | tee -a "$root/evidence/probe-status.txt"
  if [[ "$status" != 0 ]]; then
    if ! grep -q get_destination_cooperative_tensor "$root/evidence/stock-$variant.log"; then
      cat "$root/evidence/stock-$variant.log"
      echo 'Unexpected baseline compile failure; stop before applying patch.' >&2
      exit 1
    fi
  else
    echo "Baseline $variant compiled: address-space failure was not reproduced with these options."
  fi
done
git apply --check "$root/patches/mlx-sdk27-gdn-addrspace.patch"
git apply "$root/patches/mlx-sdk27-gdn-addrspace.patch"
git diff --check
git diff > "$root/evidence/applied.patch"
for variant in default target26.2; do
  extra=()
  if [[ "$variant" == target26.2 ]]; then
    extra=(-mmacosx-version-min=26.2)
  fi
  env -u MACOSX_DEPLOYMENT_TARGET xcrun -sdk macosx metal "${flags[@]}" ${extra[@]+"${extra[@]}"} \
    -c "$kernel" -I . -o "$RUNNER_TEMP/gdn-patched-$variant.air" \
    > "$root/evidence/patched-$variant.log" 2>&1
  printf '%s patched exit=0\n' "$variant" | tee -a "$root/evidence/probe-status.txt"
done
