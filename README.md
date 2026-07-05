# a1111-sd-webui-jp-tag-assistant

Japanese-to-Danbooru tag search and suggestion extension for ReForge / Forge / AUTOMATIC1111 WebUI.

`JP Tag Assistant` adds a compact collapsible search panel under the txt2img/img2img negative prompt area. Type Japanese words such as `腕`, `腕組み`, `赤面`, or `長髪`, then click candidate tags to insert them into the prompt.

## Features

- Japanese keyword search for Danbooru tags
- English tag and alias search, e.g. `x-ray`, `xray`, and `x ray`
- Candidate chips with English tag, Japanese label, and tag count
- Ambiguous-word expansion, e.g. `腕` shows `arms`, `bare arms`, `arms up`, `crossed arms`
- Related tag suggestions from Danbooru cooccurrence data
- Optional related-tag filtering to keep only general Danbooru tags
- Click to insert/remove the tag in prompt
- Shift+click to insert/remove the tag in negative prompt
- User dictionary support

## Data Files

The extension reads data from the `tags` folder.

- `jp_tag_dictionary.csv`: built-in Japanese search dictionary
- `jp_tag_user.csv`: optional user dictionary
- `danbooru-jp.csv`: manual Japanese labels
- `danbooru-machine-jp.csv`: machine-filled Japanese labels
- `danbooru.csv` or `danbooru_tags.csv`: tag count data
- `danbooru_tags_cooccurrence.csv` or `.gz`: related tag data

`danbooru_tags_cooccurrence.csv.gz` is unpacked automatically on startup when the raw CSV is missing.

## User Dictionary

Create `tags/jp_tag_user.csv` to add or override search phrases.

```csv
ja,tag,aliases
腕組み,crossed_arms,腕を組む|両腕を組む
素腕,bare_arms,腕出し|腕が出ている
```

## Usage

The WebUI panel intentionally keeps helper text minimal. This README is the main place for usage notes.

This extension is meant to complement tag completion extensions. Use JP Tag Assistant for Japanese concept search such as `膝立ち`, `四つんばい`, `下から`, or `横顔`; use a tag completion extension for broad English Danbooru tag-name completion.

### ReForge / Forge / AUTOMATIC1111

1. Install this folder into `extensions/a1111-sd-webui-jp-tag-assistant`.
2. Restart WebUI.
3. Open txt2img or img2img.
4. Type Japanese in the `JP Tag Assistant` panel.
5. Click a candidate to insert it into the prompt.
6. Shift+click to insert it into the negative prompt.

### ComfyUI

This repository can also be installed as a ComfyUI custom node.

1. Install this folder into `ComfyUI/custom_nodes/a1111-sd-webui-jp-tag-assistant`.
2. Restart ComfyUI.
3. Add `JP Tag Assistant Search` from the `JP Tag Assistant` node category.
4. Enter Japanese text in `query`.
5. Use the `tags` output as a comma-separated prompt fragment, or inspect `candidates` and `related`.

The ComfyUI node does not edit prompt fields directly. It returns strings so it can be connected to prompt-building workflows.
`related_limit` defaults to `0` because related-tag lookup may need to scan the cooccurrence file on first use. Increase it only when you want related tags in the workflow.

Keyboard shortcuts inside the assistant input:

- `ArrowUp` / `ArrowDown`: move through candidates
- `Enter` / `Tab`: insert the active candidate into the prompt
- `Shift+Enter` / `Shift+Tab`: insert the active candidate into the negative prompt
- `Esc`: collapse the assistant panel

## Settings

Settings are available under `JP Tag Assistant`.

- `Enable JP Tag Assistant`
- `Maximum search results`
- `Maximum related tags`
- `Show only general related tags`
- `Use machine-translated Japanese labels`
- `Maximum cached relations per tag`

`Show only general related tags` is enabled by default. It removes artist, copyright, character, and meta tags from the Related section while leaving direct search candidates unchanged.
