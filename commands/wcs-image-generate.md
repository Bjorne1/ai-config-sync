---
description: 通过当前项目 API 主动生图（自动检测并启动服务，默认保存到 D:\wcs_project\wcs-image\image）
argument-hint: "必填: --prompt \"提示词\"；可选: --reference-image 路径(可重复) --aspect-ratio 9:16 --image-size 2K --count 1 --timeout 300"
---

你是一个执行型命令。接到本命令后，直接调用本地脚本完成生图，不要再去调用任何 skill。

## 命令目标

- 使用当前项目对外接口 `POST /api/generate` 生成图片
- 先检测 API 服务可用性，不可用则自动启动 `api_main.py`
- 将图片保存到 `D:\wcs_project\wcs-image\image`
- 默认超时 300 秒

## 执行规则

1. 直接把用户传入参数透传给脚本。
2. 如果用户未提供 `--prompt`，立刻提示用户补充，不做猜测。
3. 执行后将脚本 JSON 输出原样返回给用户，并附上保存路径。

## 执行命令

```bash
python "C:\Users\Administrator\.claude\commands\scripts\generate_via_wcs_api.py" $ARGUMENTS
```

## 用法示例

```bash
/wcs-image-generate --prompt "一只在雨夜霓虹街道奔跑的银色机械狼，电影感，高细节"
```

```bash
/wcs-image-generate --prompt "将人物转换为赛博朋克风，保留面部结构" --reference-image "D:\素材\ref1.png" --aspect-ratio "9:16" --image-size "2K" --count 2
```
