#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -m)" == arm64 ]]
[[ "$(git -C source rev-parse HEAD)" == "$MLX_SOURCE_SHA" ]]
[[ -d "$DEVELOPER_DIR" ]]
xcodebuild -version
[[ "$(xcodebuild -version | awk '/Build version/{print $3}')" == "$EXPECTED_XCODE_BUILD" ]]
[[ "$(xcrun --sdk macosx --show-sdk-version)" == 27.0 ]]
if ! xcrun --sdk macosx --find metal; then
  echo 'Metal Toolchain missing; downloading the official Xcode component.'
  xcodebuild -downloadComponent MetalToolchain
fi
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
