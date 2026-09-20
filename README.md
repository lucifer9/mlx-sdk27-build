# MLX SDK 27 构建实验

在公开仓库的标准 `xcode-27` ARM64 runner 上，用 Xcode 27 / SDK 27 构建 MLX，再下载到 M5 Pro 本机验证。支持手动触发；仅 `main` 上构建 workflow 文件的更新会自动触发，用于初始化和验证 workflow。不使用收费 larger runner，不发布 PyPI，不包含模型、凭据或本机数据。

## 固定输入

- MLX：`59d600b5e64c238427d0f8d897ab7c682ef4d3d2`
- Xcode：27.0 RC，build `27A266a`；路径和 build 不符合时明确失败。
- Python：3.12.14；uv：0.12.16；构建依赖固定在 `build-requirements.txt`。
- Release/AOT：`MLX_METAL_JIT=OFF`，deployment target 26.2，ARM64，并行编译 2 个任务。
- 第三方 Actions 固定提交；runner 镜像本身不可按摘要固定，会记录实际版本。

## 编译与验收

1. 验证 SDK、编译器和源码；需要时下载 Apple 官方 Metal Toolchain。
2. 原版 GDN NAX 单文件分别按编译器默认目标和 26.2 目标编译，保存退出码及完整日志。原版成功会如实记录；非预期错误会停止。
3. 应用 `patches/mlx-sdk27-gdn-addrspace.patch`，同样选项编译补丁版，必须全部成功。
4. 沿用 MLX 官方 frontend/backend 分阶段打包，构建匹配的 `mlx` 和 `mlx-metal` wheels。
5. 检查版本、ARM64、动态库、metallib、GDN NAX 编译对象及禁用标志；保存来源与 SHA256。

补丁针对 [MLX #4533](https://github.com/ml-explore/mlx/issues/4533)，仅在三处 cooperative tensor 模板调用中剥离操作数的地址空间限定符。本机最小 runtime/JIT 用例已通过；完整 AOT 和模型验证以实际实验结果为准。

## 资源边界

单 job 最多 180 分钟，无自动重试，无 Actions cache。标准 runner 在公开仓库的构建分钟免费。Artifact 保留 1 天，wheels 总量超过 400 MiB 会阻止上传；账户已有 artifact/Packages 存储仍需单独关注，不能以此保证总存储免费。失败也上传诊断日志，日志不包含凭据或模型。

## 下载和本机验证

在 Actions 页面手动触发 `SDK27 build experiment`。完成后下载 `sdk27-evidence-<run>-<attempt>` 和 `sdk27-wheels-<run>-<attempt>`，先按 manifest 校验 SHA256，再用独立 uv 环境安装两个 wheel。不要覆盖现有推理环境。

构建成功不等于 M5 正确性或性能通过。后续需验证 GPU、完整 GDN 输出及 recurrent state，再在内存看门狗保护下进行模型速度和长上下文对照。新 GDN API 还需要适配 mlx-vlm；不要直接绕过原实验的 Q6 版本检查。

## 上游参考

- [官方打包 action](https://github.com/ml-explore/mlx/blob/59d600b5e64c238427d0f8d897ab7c682ef4d3d2/.github/actions/build-wheel/action.yml)
- [Xcode 27 preview runner](https://github.com/actions/runner-images/issues/14404)
- [GitHub Actions 计费规则](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

MLX 补丁涉及 MIT 授权源码，原许可见 `LICENSE-MLX`。
