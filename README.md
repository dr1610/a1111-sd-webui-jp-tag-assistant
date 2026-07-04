# a1111-sd-webui-jp-tag-assistant

Japanese-to-Danbooru tag search and suggestion extension for ReForge / Forge / AUTOMATIC1111 WebUI.

`JP Tag Assistant` adds a compact collapsible search panel under the txt2img/img2img negative prompt area. Type Japanese words such as `腕`, `腕組み`, `赤面`, or `長髪`, then click candidate tags to insert them into the prompt.

## Features

- Japanese keyword search for Danbooru tags
- Candidate chips with English tag, Japanese label, and tag count
- Ambiguous-word expansion, e.g. `腕` shows `arms`, `bare arms`, `arms up`, `crossed arms`
- Related tag suggestions from Danbooru cooccurrence data
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

1. Install this folder into `extensions/a1111-sd-webui-jp-tag-assistant`.
2. Restart WebUI.
3. Open txt2img or img2img.
4. Type Japanese in the `JP Tag Assistant` panel.
5. Click a candidate to insert it into the prompt.
6. Shift+click to insert it into the negative prompt.

## Settings

Settings are available under `JP Tag Assistant`.

- `Enable JP Tag Assistant`
- `Maximum search results`
- `Maximum related tags`
- `Use machine-translated Japanese labels`
- `Maximum cached relations per tag`
