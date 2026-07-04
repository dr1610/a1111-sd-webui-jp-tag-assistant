import csv
import gzip
import shutil
from pathlib import Path

import gradio as gr
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from modules import script_callbacks, shared


JPTA_SECTION = ("jp-tag-assistant", "JP Tag Assistant")
EXT_PATH = Path(__file__).resolve().parents[1]
TAGS_PATH = EXT_PATH.joinpath("tags")
DANBOORU_TAGS_FILE = "danbooru_tags.csv"
DANBOORU_COOCCURRENCE_FILE = "danbooru_tags_cooccurrence.csv"
DANBOORU_COOCCURRENCE_GZ_FILE = f"{DANBOORU_COOCCURRENCE_FILE}.gz"

TAG_COUNT_CACHE = {"mtime": None, "data": {}}
TRANSLATION_CACHE = {"mtime": None, "data": {}}
DICTIONARY_CACHE = {"mtime": None, "data": []}
RELATION_CACHE = {"mtime": None, "data": {}}


def valid_file(path: Path):
    return path.exists() and path.is_file() and path.stat().st_size > 0


def normalize_tag(tag: str):
    return (tag or "").strip().strip('"').replace(" ", "_").lower()


def normalize_ja(text: str):
    return (text or "").strip().lower().replace("　", " ")


def visible_tag(tag: str):
    return tag.replace("_", " ")


def split_aliases(text: str):
    return [part.strip() for part in (text or "").replace("；", "|").replace("、", "|").split("|") if part.strip()]


def unpack_bundled_cooccurrence():
    final_path = TAGS_PATH.joinpath(DANBOORU_COOCCURRENCE_FILE)
    gz_path = TAGS_PATH.joinpath(DANBOORU_COOCCURRENCE_GZ_FILE)
    if valid_file(final_path) or not valid_file(gz_path):
        return False

    tmp_path = TAGS_PATH.joinpath(f"{DANBOORU_COOCCURRENCE_FILE}.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    print(f"JP Tag Assistant: unpacking bundled {DANBOORU_COOCCURRENCE_GZ_FILE}")
    with gzip.open(gz_path, "rb") as source:
        with tmp_path.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    shutil.move(tmp_path, final_path)
    return True


def tag_count_path():
    for file_name in [DANBOORU_TAGS_FILE, "danbooru.csv"]:
        path = TAGS_PATH.joinpath(file_name)
        if valid_file(path):
            return path
    return TAGS_PATH.joinpath(DANBOORU_TAGS_FILE)


def load_tag_counts():
    path = tag_count_path()
    if not valid_file(path):
        return {}

    mtime = path.stat().st_mtime
    if TAG_COUNT_CACHE["mtime"] == mtime:
        return TAG_COUNT_CACHE["data"]

    counts = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 3:
                    continue
                tag = normalize_tag(row[0])
                if not tag or tag == "tag":
                    continue
                try:
                    counts[tag] = int(float(row[2]))
                except ValueError:
                    continue
    except Exception as exc:
        print(f"JP Tag Assistant: failed to read {path.name}: {exc}")

    TAG_COUNT_CACHE["mtime"] = mtime
    TAG_COUNT_CACHE["data"] = counts
    print(f"JP Tag Assistant: loaded {len(counts)} tag counts from {path.name}.")
    return counts


def translation_files():
    candidates = ["danbooru_ja_user.csv", "danbooru-jp.csv"]
    if bool(getattr(shared.opts, "jpta_useMachineJapaneseLabels", True)):
        candidates.append("danbooru-machine-jp.csv")
    return [TAGS_PATH.joinpath(name) for name in candidates if valid_file(TAGS_PATH.joinpath(name))]


def load_translations():
    files = translation_files()
    mtime = tuple((path.as_posix(), path.stat().st_mtime) for path in files)
    if TRANSLATION_CACHE["mtime"] == mtime:
        return TRANSLATION_CACHE["data"]

    labels = {}
    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if len(row) < 2:
                        continue
                    tag = normalize_tag(row[0])
                    label = row[1].strip()
                    if tag and tag not in {"tag", "name"} and label:
                        labels.setdefault(tag, label)
        except Exception as exc:
            print(f"JP Tag Assistant: failed to read {path.name}: {exc}")

    TRANSLATION_CACHE["mtime"] = mtime
    TRANSLATION_CACHE["data"] = labels
    print(f"JP Tag Assistant: loaded {len(labels)} Japanese labels.")
    return labels


def dictionary_files():
    candidates = ["jp_tag_user.csv", "jp_tag_dictionary.csv"]
    return [TAGS_PATH.joinpath(name) for name in candidates if valid_file(TAGS_PATH.joinpath(name))]


def load_dictionary():
    files = dictionary_files()
    translation_files_mtime = tuple((path.as_posix(), path.stat().st_mtime) for path in translation_files())
    mtime = (
        tuple((path.as_posix(), path.stat().st_mtime) for path in files),
        translation_files_mtime,
        bool(getattr(shared.opts, "jpta_useMachineJapaneseLabels", True)),
    )
    if DICTIONARY_CACHE["mtime"] == mtime:
        return DICTIONARY_CACHE["data"]

    entries = []
    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    ja = (row.get("ja") or "").strip()
                    tag = normalize_tag(row.get("tag") or "")
                    aliases = split_aliases(row.get("aliases") or "")
                    if not ja or not tag:
                        continue
                    entries.append({
                        "tag": tag,
                        "labelJa": ja,
                        "terms": [ja, *aliases],
                        "source": "user" if path.name == "jp_tag_user.csv" else "dictionary",
                    })
        except Exception as exc:
            print(f"JP Tag Assistant: failed to read {path.name}: {exc}")

    for tag, label in load_translations().items():
        entries.append({
            "tag": tag,
            "labelJa": label,
            "terms": [label],
            "source": "translation",
        })

    DICTIONARY_CACHE["mtime"] = mtime
    DICTIONARY_CACHE["data"] = entries
    print(f"JP Tag Assistant: loaded {len(entries)} dictionary/search entries.")
    return entries


def relation_files():
    unpack_bundled_cooccurrence()
    patterns = ["*cooccurrence*.csv", "*co-occurrence*.csv", "*related*.csv"]
    found = []
    for pattern in patterns:
        found.extend(TAGS_PATH.glob(pattern))
    return sorted({p for p in found if p.is_file()})


def load_relations():
    files = relation_files()
    mtime = tuple((path.as_posix(), path.stat().st_mtime) for path in files)
    if RELATION_CACHE["mtime"] == mtime:
        return RELATION_CACHE["data"]

    limit_per_tag = int(getattr(shared.opts, "jpta_relationCacheLimit", 500))
    counts = load_tag_counts()
    relations = {}

    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if len(row) < 2:
                        continue
                    left = normalize_tag(row[0])
                    right = normalize_tag(row[1])
                    if not left or not right or left in {"tag", "tag_a", "tag1"}:
                        continue
                    try:
                        count = int(float(row[2])) if len(row) > 2 and row[2] else 0
                    except ValueError:
                        count = 0
                    relations.setdefault(left, []).append({"tag": right, "count": count})
                    relations.setdefault(right, []).append({"tag": left, "count": count})
        except Exception as exc:
            print(f"JP Tag Assistant: failed to read {path.name}: {exc}")

    for tag, items in relations.items():
        deduped = {}
        for item in items:
            previous = deduped.get(item["tag"])
            if previous is None or item["count"] > previous["count"]:
                deduped[item["tag"]] = item
        count_a = counts.get(tag, 0)
        for item in deduped.values():
            count_b = counts.get(item["tag"], 0)
            union = count_a + count_b - item["count"]
            item["score"] = item["count"] / union if union > 0 else 0
        relations[tag] = sorted(
            deduped.values(),
            key=lambda item: (item.get("score", 0), item["count"]),
            reverse=True,
        )[:limit_per_tag]

    RELATION_CACHE["mtime"] = mtime
    RELATION_CACHE["data"] = relations
    print(f"JP Tag Assistant: loaded {len(relations)} related-tag entries.")
    return relations


def item_for_tag(tag, label=None, source="tag", score=0, matched=None):
    labels = load_translations()
    counts = load_tag_counts()
    label = label or labels.get(tag, "")
    return {
        "tag": tag,
        "displayTag": visible_tag(tag),
        "labelJa": label,
        "count": counts.get(tag, 0),
        "source": source,
        "score": score,
        "matched": matched or "",
    }


def score_entry(query, entry):
    q = normalize_ja(query)
    if not q:
        return 0, ""

    best_score = 0
    best_term = ""
    for term in entry["terms"]:
        t = normalize_ja(term)
        if not t:
            continue
        if q == t:
            score = 1000
        elif t.startswith(q):
            score = 850
        elif q in t:
            score = 760
        elif t in q:
            score = 700
        else:
            score = 0
        if score > best_score:
            best_score = score
            best_term = term
    return best_score, best_term


def tag_boundary_match(query: str, tag: str):
    if query == tag:
        return True
    return query in tag.split("_")


def search_tags(query, limit=40):
    q = normalize_ja(query)
    if not q:
        return []

    limit = max(1, min(int(limit), 100))
    counts = load_tag_counts()
    results = {}

    for entry in load_dictionary():
        score, matched = score_entry(q, entry)
        if score <= 0:
            continue
        if entry["source"] == "user":
            score += 120
        elif entry["source"] == "dictionary":
            score += 80
        elif entry["source"] == "translation":
            score = max(1, score - 180)
        tag = entry["tag"]
        item = item_for_tag(tag, entry["labelJa"], entry["source"], score, matched)
        previous = results.get(tag)
        if previous is None or item["score"] > previous["score"]:
            results[tag] = item

    tag_query = normalize_tag(q)
    if tag_query:
        for tag, count in counts.items():
            if tag_boundary_match(tag_query, tag):
                score = 640 if tag == tag_query else 520
                item = item_for_tag(tag, source="danbooru", score=score, matched=tag_query)
                item["count"] = count
                previous = results.get(tag)
                if previous is None or item["score"] > previous["score"]:
                    results[tag] = item

    return sorted(
        results.values(),
        key=lambda item: (item["score"], item.get("count", 0)),
        reverse=True,
    )[:limit]


def attach_labels(items):
    labels = load_translations()
    counts = load_tag_counts()
    for item in items:
        tag = item["tag"]
        item["displayTag"] = visible_tag(tag)
        item["labelJa"] = item.get("labelJa") or labels.get(tag, "")
        item["count"] = item.get("count") or counts.get(tag, 0)
    return items


def on_ui_settings():
    shared.opts.add_option(
        "jpta_enable",
        shared.OptionInfo(True, "Enable JP Tag Assistant", section=JPTA_SECTION),
    )
    shared.opts.add_option(
        "jpta_maxResults",
        shared.OptionInfo(32, "Maximum search results", gr.Slider, {"minimum": 8, "maximum": 100, "step": 1}, section=JPTA_SECTION),
    )
    shared.opts.add_option(
        "jpta_relatedMaxResults",
        shared.OptionInfo(24, "Maximum related tags", gr.Slider, {"minimum": 4, "maximum": 80, "step": 1}, section=JPTA_SECTION),
    )
    shared.opts.add_option(
        "jpta_useMachineJapaneseLabels",
        shared.OptionInfo(True, "Use machine-translated Japanese labels", section=JPTA_SECTION),
    )
    shared.opts.add_option(
        "jpta_relationCacheLimit",
        shared.OptionInfo(500, "Maximum cached relations per tag", gr.Slider, {"minimum": 50, "maximum": 2000, "step": 50}, section=JPTA_SECTION),
    )


def api_jp_tag_assistant(_: gr.Blocks, app: FastAPI):
    @app.get("/jptagapi/v1/config")
    async def config():
        return {
            "enable": bool(getattr(shared.opts, "jpta_enable", True)),
            "maxResults": int(getattr(shared.opts, "jpta_maxResults", 32)),
            "relatedMaxResults": int(getattr(shared.opts, "jpta_relatedMaxResults", 24)),
        }

    @app.get("/jptagapi/v1/search")
    async def search(q: str = "", limit: int = 32):
        return {"query": q, "results": search_tags(q, limit)}

    @app.get("/jptagapi/v1/related")
    async def related(tag: str, limit: int = 24):
        key = normalize_tag(tag)
        if not key:
            return {"tag": tag, "results": []}
        relations = load_relations()
        items = relations.get(key, [])[: max(0, min(int(limit), 100))]
        return {"tag": key, "results": attach_labels(items)}

    @app.post("/jptagapi/v1/reload")
    async def reload_data():
        TAG_COUNT_CACHE["mtime"] = None
        TRANSLATION_CACHE["mtime"] = None
        DICTIONARY_CACHE["mtime"] = None
        RELATION_CACHE["mtime"] = None
        return JSONResponse({"ok": True, "entries": len(load_dictionary())})


script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_app_started(api_jp_tag_assistant)
