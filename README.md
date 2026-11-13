# WideCanvas · 超宽画幅生成工作台

面向超宽横幅（Banner、文化墙背景、网页横幅、全景视觉素材）的图片生成方案。通过**规划重叠画幅 → 分段生成 → 羽化加权融合**，在不要求单次图像 API 超过其自身比例限制的前提下，输出 6:1、8:1 等宽幅图片，且画面内容连贯，不是拉伸、裁切或留白。

## 效果

<!-- cases:start -->
尚未生成实际案例。配置 `IMAGE_API_KEY` 后运行 `python make_cases.py`，本节会自动写入 6:1 与 8:1 的真实生成结果；提示词与参数记录在 [`cases/cases.json`](cases/cases.json)。
<!-- cases:end -->

## 快速开始

需要 Python 3.10+。PowerShell（无需激活虚拟环境）：

```powershell
cd E:\photo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
Copy-Item .env.example .env
# 编辑 .env，填写 IMAGE_API_KEY 及服务参数
.\.venv\Scripts\python.exe server.py
```

打开 <http://127.0.0.1:8000> 即可使用。

- **离线演示模式**：页面默认开启，无需 API Key，可检查交互、进度与拼接流程。演示图带有 `OFFLINE PREVIEW / NOT AI GENERATED` 标记，不是 AI 生成结果。
- **真实生成**：关闭演示模式，服务端需配置 `IMAGE_API_KEY`。密钥只保存在服务端 `.env`，不经浏览器传递，也不会提交到仓库。

## 生成实际案例

```powershell
.\.venv\Scripts\python.exe make_cases.py
```

脚本按 `cases` 配置生成 6:1 与 8:1 两张图，输出到 `cases/case-6-1.png`、`cases/case-8-1.png`，并把提示词、尺寸、模型写入 `cases/cases.json`。`--demo` 参数可生成离线预览（写入 `cases/preview/`，不入库）。

## 方案实现

1. **画幅规划**：按目标像素尺寸将画面等宽切分为若干约 1.5:1 的画幅，相邻画幅保留约 24% 重叠；末段位置回算，保证完整覆盖目标宽度。
2. **分段生成**：逐段调用图像生成服务，提示词追加该段位置（左/中/右）、风格一致性、边缘自然延展等约束，避免拼贴感。
3. **羽化融合**：每段缩放适配到目标窗口，按到边缘的距离生成权重，重叠区按权重加权求和，得到目标尺寸 PNG。

## 模型与第三方服务

- 图像生成：任何兼容 OpenAI Images API 的服务（`POST /v1/images/generations`，返回 `b64_json` 或图片 URL），通过 `.env` 的 `IMAGE_API_BASE`、`IMAGE_MODEL`、`IMAGE_SIZE` 切换。
- 若服务商接口格式不同，只需调整 `server.py` 中的 `call_image_api`。
- 运行环境：Python 标准库 + Pillow + NumPy，无 Web 框架依赖。

## 在线部署

仓库已包含 `render.yaml`、`Procfile`、`Dockerfile`、`runtime.txt`，可直接部署。

**方式一：Render（免费，最省事）**

1. 在 [render.com](https://render.com) 用 GitHub 账号登录并创建 New → Web Service，选中本仓库。
2. 平台会读取 `render.yaml` 自动配置构建与启动命令；或在界面手动填写：Build Command `pip install -r requirements.txt`，Start Command `python server.py`。
3. 在 Environment 变量中填入 `IMAGE_API_KEY`（以及需要时覆盖 `IMAGE_API_BASE`、`IMAGE_MODEL`、`IMAGE_SIZE`），不要写进代码或提交到仓库。
4. 部署完成后得到 `https://widecanvas.onrender.com` 之类的地址，直接打开即可操作，无需本地运行 Python。

**方式二：Docker（任意云主机）**

```bash
docker build -t widecanvas .
docker run -d -p 8000:8000 -e IMAGE_API_KEY=你的密钥 widecanvas
```

**其他平台**：Railway、Fly.io、Hugging Face Spaces 均可使用 `Procfile` 或 `Dockerfile`。所有平台都需要在控制台设置 `IMAGE_API_KEY` 环境变量。

## API

- `POST /api/generate`：`{ "prompt": "...", "width": 3072, "height": 512, "demo": false }`，返回 `task_id`。
- `GET /api/tasks/{task_id}`：查询进度、尺寸、比例、分段数与产物地址。
- `GET /outputs/{task_id}.png`：获取生成图片。
- `GET /api/health`：健康检查，返回服务状态与是否已配置密钥。

## 已知限制

- 羽化融合只能减轻亮度与纹理断层，无法修复不同生成片段之间的主体跳变；跨段一致性取决于底层模型能力与提示词质量。
- 暂不支持语义级接缝修复、主体定位锁定、多轮局部重绘。
- 宽幅图需要多次 API 调用，耗时与费用随分段数增长。
- 部分服务商不支持参考图输入，当前实现通过提示词与分段顺序约束一致性；若服务商支持图像编辑接口，可将上一段作为参考图传入以进一步提升连贯性。

## 项目结构

- `server.py`：HTTP 服务、图像 API 客户端、任务状态、拼接融合。
- `make_cases.py`：批量生成 6:1 / 8:1 实际案例。
- `static/index.html`：中文操作界面（提示词、尺寸、比例、进度、PNG 下载）。
- `cases/`：实际生成案例与参数记录。
- `.env.example`：图像服务配置示例（真实 `.env` 已被 `.gitignore` 排除）。
- `requirements.txt`、`render.yaml`、`Procfile`、`Dockerfile`：依赖与部署配置。

