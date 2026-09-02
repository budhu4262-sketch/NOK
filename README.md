# 13-Agent Automated YouTube Video Pipeline
> Production-grade automated pipeline to generate, process, voice-transform, subtitle, and schedule high-retention YouTube videos in the **Data Visualization & Global Statistics** niche using Google NotebookLM's Cinematic Video Overview engine as the visual core.

---

## Architecture Overview

```
project_root/
├── config/
│   └── settings.py          # API keys, CDP port, paths, models config
├── workspace/               # Ephemeral storage for the current run
│   ├── 01_topic.json
│   ├── 02_source.txt
│   ├── 03_verified_source.txt
│   ├── 04_notebook_prompts.json
│   ├── 06_raw_video.mp4
│   ├── 07_transcript.json
│   ├── 07_outro.json
│   ├── 08_voiced_video.mp4
│   ├── 09_final_video.mp4
│   ├── 10_metadata.json
│   ├── 11_thumbnail.png
│   └── 12_manifest.json
├── assets/                  # Target voice sample, fallback charts, fonts
│   └── target_voice.wav
├── runs/                    # Immutable historical archives (<timestamp>_<topic_slug>/)
├── agents/
│   ├── agent1_trend_scout.py          # Viral concept scout (Claude Opus)
│   ├── agent2_source_writer.py        # 1,500-word structured source (Claude Opus)
│   ├── agent3_fact_verifier.py        # Structural & ingestion audit (Claude Opus)
│   ├── agent4_prompt_synthesizer.py    # Locked visual & steering prompts
│   ├── agent5_notebook_feeder.py      # Playwright CDP NotebookLM ingestion
│   ├── agent6_asset_harvester.py      # CDP generation poller & MP4 downloader
│   ├── agent7_transcriber_outro.py    # faster-whisper & 15s outro generator
│   ├── agent8_voice_transformer.py    # Seed-VC/RVC STS & Edge-TTS outro splicer
│   ├── agent9_subtitle_editor.py      # ASS word-by-word karaoke highlight burner
│   ├── agent10_seo_packager.py        # 3 High-CTR titles, chapters, 15 tags
│   ├── agent11_thumbnail_generator.py # 1280x720 neon infographic thumbnail
│   ├── agent12_asset_bundler.py       # Manifest verification & run archive
│   └── agent13_youtube_publisher.py   # YouTube Data API v3 OAuth publisher
├── utils/
│   ├── tabi_client.py                 # Centralized Claude Opus API wrapper
│   └── cdp_driver.py                  # Reusable Playwright CDP session manager
├── requirements.txt
├── .env.example
└── orchestrator.py                    # Master CLI runner with stage-based resume
```

---

## Tech Stack & Engine Mapping

| Agent | Module | Engine / Provider | Functionality |
|---|---|---|---|
| **1** | Trend Scout | TabiAI (`claude-opus-5`) | 5 viral counter-intuitive data shifts with hooks |
| **2** | Source Writer | TabiAI (`claude-opus-5`) | 1,500-word structured dossier with milestones & tables |
| **3** | Fact Verifier | TabiAI (`claude-opus-5`) | Audits logical flow, headers, and bullet points |
| **4** | Prompt Synthesizer | TabiAI (`claude-opus-5`) | Locked 2D data-viz visual prompt + dynamic steering |
| **5** | NotebookLM Feeder | Playwright over CDP | Uploads source & prompts into NotebookLM Cinematic engine |
| **6** | Asset Harvester | Playwright over CDP | Monitors render queue and downloads raw MP4 |
| **7** | Transcriber & Outro | `faster-whisper` + Claude | Word-level timestamps and 15s retention cliffhanger outro |
| **8** | Voice Transformer | FFmpeg + Seed-VC/RVC + `edge-tts` | Zero-shot STS conversion + outro speech merge |
| **9** | Subtitle Editor | FFmpeg + `libass` | Burns modern yellow/cyan word-by-word highlighted captions |
| **10** | SEO Packager | TabiAI (`claude-opus-5`) | High-CTR titles, chapter markers, description, 15 tags |
| **11** | Thumbnail Engine | Pillow + Matplotlib | 1280x720 high-contrast data chart thumbnail (<4 words) |
| **12** | Asset Bundler | Python `hashlib` & `shutil` | Integrity checksums, manifest generation, runs archiving |
| **13** | YouTube Publisher | `google-api-python-client` | OAuth 2.0 video upload, thumbnail set, and scheduling |

---

## Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.14)
- **FFmpeg with `libass`** (verify via `ffmpeg -version`)
- **Google Chrome** with active Google session logged into [NotebookLM](https://notebooklm.google.com/)

### 2. Launch Chrome with Remote Debugging (Port 9222)
Close existing Chrome windows, then run:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\dell\AppData\Local\Google\Chrome\User Data"
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Key variables:
- `TABI_API_KEY`: Your TabiAI / Tabitoken API key.
- `CDP_URL`: `http://localhost:9222` (default).
- `HARVESTER_INITIAL_WAIT_SEC`: Initial silent wait in seconds (default `1200` = 20 mins).
- `TARGET_VOICE_NAME`: Edge-TTS profile (e.g. `en-US-ChristopherNeural`).

---

## CLI Master Orchestrator

```bash
# Run complete end-to-end pipeline (Agents 1 through 13)
python orchestrator.py --full

# Resume from a specific agent stage (e.g., resume from Agent 5 onwards)
python orchestrator.py --stage 5

# Skip NotebookLM web automation and run post-processing on existing 06_raw_video.mp4 (Agents 7-13)
python orchestrator.py --skip-notebooklm

# Inspect current workspace state and generated files
python orchestrator.py --status

# Dry-run mode for pipeline verification without calling live CDP/YouTube upload
python orchestrator.py --full --dry-run
```

---

## Fallback & Fault-Tolerance Modes
- **LLM Rate-Limiting**: Centralized `TabiClient` performs retries with exponential backoff and markdown JSON extraction.
- **Voice Transformation**: If Seed-VC / RVC CLI binaries are not locally installed, Agent 8 applies a broadcast-grade audio filter and normalization pass-through, ensuring the pipeline completes without crashing.
- **YouTube Publishing**: If OAuth credentials (`client_secrets.json`) are absent, Agent 13 outputs the complete upload manifest and simulated identifiers.
- **Fail-Safe Checkpoints**: If an agent fails, the pipeline halts cleanly, saves the error stack trace to `workspace/pipeline.log`, and allows instantaneous resumption using `--stage <N>`.