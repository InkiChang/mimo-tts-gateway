# Legado (阅读) 接入 mimo-tts-gateway

## 方式一：直接手动添加（推荐）

在阅读 App 中：

1. 打开任意一本书，进入阅读界面
2. 点击屏幕中间 → 点击右下角 **设置**
3. 点击 **朗读** → 点击右上角 **TTS 配置**
4. 点击右上角 `+` 添加朗读引擎
5. 填入以下信息：

| 字段 | 值 |
|------|-----|
| 名称 | `MiMo TTS (冰糖)` |
| 朗读引擎 URL | `http://192.168.3.172:8000/tts?token=dev-token-001&preset=default&text={{`{{}}`speakText{{`}}`}}` |
| 内容类型 | `audio/mpeg` |

> **注意**：填入 URL 时，`speakText` 必须用双花括号 `{{speakText}}`。

6. 点击右上角 **保存**

## 方式二：快速导入

在浏览器中打开以下链接（手机浏览器）：

```
legado://import/httpTTS?src=https://raw.githubusercontent.com/<YOUR_REPO>/main/docs/legado-mimo-tts.json
```

或直接在阅读 App 中：
1. 我的 → 书源管理 → 右上角 `⋮` → 本地导入
2. 粘贴以下 JSON：

```json
[{
  "name": "MiMo TTS (冰糖)",
  "url": "http://192.168.3.172:8000/tts?token=dev-token-001&preset=default&text={{speakText}}",
  "contentType": "audio/mpeg"
}]
```

## 如何使用

1. 打开任意书籍
2. 进入阅读界面 → 点击右下角 **朗读**
3. 在朗读引擎列表中选择 `MiMo TTS (冰糖)`
4. 点击播放按钮开始听书

## 多预设配置

可以在网关 WebUI（`http://192.168.3.172:8000/admin/setup`）中创建多个 Preset，然后为阅读 App 添加多个朗读引擎：

| 引擎名称 | URL |
|----------|-----|
| MiMo 默认 | `http://192.168.3.172:8000/tts?token=dev-token-001&preset=default&text={{`{{}}`speakText{{`}}`}}` |
| MiMo 睡前 | `http://192.168.3.172:8000/tts?token=dev-token-001&preset=sleep&text={{`{{}}`speakText{{`}}`}}` |
| MiMo 快速 | `http://192.168.3.172:8000/tts?token=dev-token-001&preset=fast&text={{`{{}}`speakText{{`}}`}}` |

> **说明**：Legado 会自动对 `{{speakText}}` 进行 URL 编码，不需要手动编码。语音速度可以通过 Legado 自带的语速滑块调节（不影响网关）。

## 常见问题

### 无法朗读
- 确认网关服务正在运行
- 确认手机和服务器在同一局域网
- 检查 `GATEWAY_TOKEN` 是否正确

### 朗读中断
- 检查网关 Logs 页面查看上游错误
- 可能是上游 API 超时，可在 Provider 配置中增加超时时间

### 音频格式
- 当前中转 API 返回 MP3 格式，可直接使用
- 如需 WAV 格式，请在 WebUI 中修改 Provider 的 `output_format`
