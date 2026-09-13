# Bundled tag data

Last checked: 2026-09-13.

## English tags, categories, counts and aliases

`danbooru.csv` is the unmodified CSV from [DraconicDragon/dbr-e621-lists-archive](https://github.com/DraconicDragon/dbr-e621-lists-archive), also used as a source by upstream Tag Autocomplete.

- Snapshot: 2026-04-01, 201,269 unique tags, at least 20 posts per tag.
- [Pinned source file](https://github.com/DraconicDragon/dbr-e621-lists-archive/blob/e67f8782c80857e99804d2afd7677cb5837a34ee/tag-lists/danbooru/danbooru_2026-04-01_pt20-ia-dd.csv).
- Source Git blob: `45992801b5c5dd5290b31b101a32438fd70041ad`.
- Source repository license: [Unlicense](https://github.com/DraconicDragon/dbr-e621-lists-archive/blob/e67f8782c80857e99804d2afd7677cb5837a34ee/LICENSE).
- CSV columns: tag, Danbooru category, post count, comma-separated aliases.

This replaces the previous 140,782-tag list: 64,023 names added, 3,536 absent from the new snapshot, and 114,453 existing rows updated. The increase includes the lower post-count cutoff (20 instead of 25), not just newly created tags. Categories remain the standard Danbooru values; copyright/character exclusion still uses categories 3 and 4.

## Japanese labels

The bundled `danbooru-jp.csv` (427 rows) and `danbooru-machine-jp.csv` (99,999 rows) match [boorutan/booru-japanese-tag at cec5f7e](https://github.com/boorutan/booru-japanese-tag/tree/cec5f7eefbe5c3addd8fb9338d11435518ae8ccf), ignoring line endings. No label changes were available when checked. This source uses the [MIT license](https://github.com/boorutan/booru-japanese-tag/blob/cec5f7eefbe5c3addd8fb9338d11435518ae8ccf/LICENSE).

New English tags do not automatically receive Japanese translations. `jp_tag_dictionary.csv` and user dictionary/translation files are maintained separately and were not replaced by this update.

## Related tags

`danbooru_tags_cooccurrence.csv.gz` retains the existing data from [newtextdoc1111/danbooru-tag-csv](https://huggingface.co/datasets/newtextdoc1111/danbooru-tag-csv). The upstream cooccurrence file was last updated on 2025-05-09; no newer version was available when checked. Updating English tags does not add cooccurrence information for new tags.
