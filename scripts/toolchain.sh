#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -m)" == arm64 ]]
[[ "$(git -C source rev-parse HEAD)" == "$MLX_SOURCE_SHA" ]]
[[ -d "$DEVELOPER_DIR" ]]
xcodebuild -version
[[ "$(xcodebuild -version | awk '/Build version/{print $3}')" == "$EXPECTED_XCODE_BUILD" ]]
[[ "$(xcrun --sdk macosx --show-sdk-version)" == 27.0 ]]
# Xcode ships a metal shim even when the downloadable component is absent.
if xcrun --sdk macosx metal --version > evidence/metal-before.log 2>&1; then
  cat evidence/metal-before.log
elif grep -q 'missing Metal Toolchain' evidence/metal-before.log; then
  cat evidence/metal-before.log
  echo 'Metal Toolchain missing; downloading the official Xcode component.'
  xcodebuild -downloadComponent MetalToolchain
else
  cat evidence/metal-before.log
  echo 'Unexpected Metal compiler failure; refusing an unrelated retry.' >&2
  exit 1
fi
xcrun --sdk macosx --find metal
xcrun --sdk macosx metal --version
xcrun --sdk macosx --show-sdk-path
xcrun clang --version
sw_vers
uname -m
sysctl hw.memsize hw.ncpu
printf 'ImageOS=%s\nImageVersion=%s\n' "${ImageOS:-unset}" "${ImageVersion:-unset}"
printf 'Deployment target=%s\nCMAKE_ARGS=%s\n' "$MACOSX_DEPLOYMENT_TARGET" "$CMAKE_ARGS"
uv --version
shasum -a 256 patches/mlx-sdk27-gdn-addrspace.patch
[[ "$(shasum -a 256 patches/mlx-sdk27-gdn-addrspace.patch | awk '{print $1}')" == 48faeded5196d915efc08b509afc6f04849d2f6842d389123e9577e6705021b6 ]]
git rev-parse HEAD > evidence/experiment-sha.txt
git -C source rev-parse HEAD > evidence/source-sha.txt
