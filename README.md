# WideCanvas

中文超宽画幅生成工作台。通过规划重叠画幅、分段生成和羽化加权融合，在不要求单次图像 API 超过自身比例限制的前提下输出 6:1、8:1 等宽幅 PNG。包含离线演示模式，可不配置密钥检查完整交互与拼接流程。

## 运行

需要 Python 3.10+。Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，填写 IMAGE_API_KEY 和服务参数
python server.py
```

打开 <http://127.0.0.1:8000>。本地预览无需 API Key：页面保持「离线演示模式」开启并生成。演示图带有 `OFFLINE PREVIEW / NOT AI GENERATED` 标记，不能作为实际 AI 效果案例。真实生成需关闭演示模式，并配置兼容 OpenAI Images API 的服务。只需 `IMAGE_API_KEY`；API Base、模型和输出尺寸可通过 `.env` 调整。密钥只存于本地服务端，不经浏览器发送或纳入仓库。

## 方案

1. 根据用户目标尺寸按约 1.5:1 比例规划分段，使用约 24% 重叠窗口。目标画布被等宽切分，最后一段位置回算以保证完整覆盖。
2. 对每段追加位置、风格、光照、地平线、自然边缘延展等约束，逐段调用配置的图像生成服务。面板按序生成，为后续接入参考图扩展留出接口。
3. 将每段适配到目标窗口，重叠处按边缘距离加权融合，得到用户指定像素尺寸的 PNG。

当前 API 接口采用 `POST /v1/images/generations`，支持返回 `b64_json` 或可访问图片 URL 的 OpenAI-compatible 服务。不同供应商的请求格式或模型命名可能不同，需要调整 `server.py` 的 `call_image_api`。标准 Images API 不一定接受参考图；当前实现通过提示词和顺序约束一致性，未声称具备图像参考条件。若服务端支持图像编辑/参考图，传递前一段作为 reference 可改善跨段连贯性。

## 限制

羽化只能减轻亮度/纹理断层，无法修复不同生成片段中的主体跳变；不支持语义级接缝修复、主体定位或多轮局部重绘。严格一致性受底层模型影响。高分辨率生成涉及多次 API 调用，耗时和费用大致随分段数增加。演示模式只是离线合成的流程预览，不是生成案例。

## 项目结构

- `server.py`：标准库 HTTP 服务、图像 API 客户端、任务状态、拼接融合。
- `static/index.html`：中文操作 UI，支持提示词、像素尺寸、6:1 / 8:1 / 自定义比例、进度与 PNG 下载。
- `.env.example`：图像 API 配置示例。
- `requirements.txt`：Pillow 与 NumPy。

## API

- `POST /api/generate` JSON `{ "prompt": "...", "width": 3072, "height": 512, "demo": true }`，返回 `task_id`。
- `GET /api/tasks/{task_id}` 查询进度与产物地址。
- `GET /outputs/{task_id}.png` 获取生成图片。

## 实际案例

题目指定的图像 API 凭证未随题目文档提供，本仓库不伪造 AI 生成案例。配置服务端密钥后，可用 UI 分别选择 6:1 与 8:1 生成真实案例；生成图片保存在本地 `outputs/`（已加入 `.gitignore`，确认授权后可手动挑选公开）。
