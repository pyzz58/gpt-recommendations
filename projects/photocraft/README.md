# PhotoCraft

## 原项目

- 项目名称：PhotoCraft
- GitHub 原始地址：<https://github.com/storytold/photocraft>
- 作者：ArtCraft（GitHub 组织 storytold）
- 许可证：Apache-2.0（README 标注 MIT / Apache-2.0）
- 最新版本：v0.6.0（2026-10-10）

## 项目简介

图像编辑软件，是 Adobe Photoshop 的 clean-room（干净室）重实现，使用纯 Rust 编写。支持图层、蒙版、调整图层、图层样式、文字、矢量与笔刷，并可直接读写真实的 PSD 文件。原生支持 macOS / Windows / Linux / FreeBSD，也提供浏览器 WebAssembly 版本与 CLI 工具。

## 为什么推荐

整个 Adobe 全家桶被同一个团队用 Rust 逐个重写，PhotoCraft 是这个家族里最火的一个：2026-09-30 建仓，11 天后 star 达到 41,444，fork 6,160，仓库每天都有提交。它是「不订阅 Photoshop 到底行不行」这个问题最值得实测的答案。

## 我能怎么用

安装 macOS 原生版直接处理图片；用浏览器版免安装快速体验；需要自动化时用配套 CLI 做批量处理。

## 后续研究

- 实测 PSD 兼容度（图层、蒙版、调整图层是否正确还原）。
- 评估 early alpha 状态下的稳定性与崩溃情况。
- 研究 CLI 能力，判断能否接入自动化与 Agent 流程。

## 状态

待研究（2026-10-11 收录，本机已下载 macOS 安装包 78.7 MB，未安装）
