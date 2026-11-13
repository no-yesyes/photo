# 实际生成案例

本目录存放由真实图像 API 生成的 6:1 与 8:1 案例，以及生成时的提示词和参数记录（`cases.json`）。

生成方式：

```powershell
python make_cases.py
```

脚本会读取 `.env` 中的图像服务配置，逐段生成并融合，输出 `case-6-1.png`（3072×512）与 `case-8-1.png`（4096×512）。
