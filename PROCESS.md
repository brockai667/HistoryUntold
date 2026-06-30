# NextByte - tech & AI news (pro video pipeline)

Daily autonomous: generate_topics (tech/AI niche + trend-scan) -> generate_batch -> make_video -> push_to_buffer.

## Shared engine base (same across ALL factories, only the niche differs)
- **B-roll**: pooled multi-query Pexels search in get_broll -> picks best by topic-match (url slug) + resolution.
- **Captions**: POP animated (config caption_renderer=pop) - each word pops in (scale), key words/numbers yellow.
- **Voice**: Kokoro (local, free). **Music**: cinematic (cine_*). **Motion**: hook zoom + Ken Burns. Color grade.
- Per-segment `asset` (local image/video) supported for screenshots / micro-montages / animated logos.

Each factory keeps its own niche (topics + brand colors/hashtags) but the make_video.py engine is identical.
