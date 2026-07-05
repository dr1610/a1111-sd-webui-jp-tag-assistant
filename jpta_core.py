import csv
import gzip
from pathlib import Path


DANBOORU_TAGS_FILE = "danbooru_tags.csv"
DANBOORU_COOCCURRENCE_FILE = "danbooru_tags_cooccurrence.csv"
DANBOORU_COOCCURRENCE_GZ_FILE = f"{DANBOORU_COOCCURRENCE_FILE}.gz"
RELATED_MODES = [
    "Auto",
    "Prompt Builder",
    "Pose / Body",
    "Camera / Composition",
    "Clothing / Appearance",
    "Location / Scene",
    "NSFW",
    "All General",
    "All",
    "Off",
]

POSE_EXACT = {
    "standing", "sitting", "kneeling", "on_one_knee", "squatting", "lying", "on_back",
    "on_stomach", "all_fours", "seiza", "spread_legs", "crossed_legs", "arms_up",
    "arm_up", "crossed_arms", "outstretched_arms", "arms_behind_back",
    "arms_behind_head", "hands_up", "hand_on_hip", "interlocked_fingers",
    "hugging_own_legs",
}
POSE_WORDS = {
    "pose", "standing", "sitting", "kneeling", "squatting", "lying", "crouching",
    "walking", "running", "jumping", "arms", "arm", "hands", "hand", "legs",
    "leg", "feet", "foot", "knees", "knee", "fingers",
}
CAMERA_EXACT = {
    "from_below", "from_above", "from_side", "from_behind", "profile", "full_body",
    "upper_body", "cowboy_shot", "portrait", "close-up", "looking_at_viewer",
}
CAMERA_WORDS = {
    "view", "from", "angle", "perspective", "shot", "focus", "closeup", "close-up",
    "profile", "portrait", "body", "looking",
}
APPEARANCE_EXACT = {
    "school_uniform", "serafuku", "shirt", "white_shirt", "skirt", "miniskirt",
    "dress", "white_dress", "swimsuit", "bikini", "underwear", "panties",
    "thighhighs", "socks", "gloves", "boots", "shoes", "hat", "ribbon",
    "hair_ornament", "collar", "choker", "long_hair", "short_hair", "smile",
    "blush", "open_mouth", "closed_mouth", "one_eye_closed",
}
APPEARANCE_WORDS = {
    "hair", "eyes", "eye", "smile", "blush", "mouth", "tears", "sweat", "shirt",
    "skirt", "dress", "uniform", "serafuku", "swimsuit", "bikini", "underwear",
    "panties", "thighhighs", "socks", "gloves", "boots", "shoes", "hat", "ribbon",
    "collar", "choker", "breasts", "ass", "navel", "stomach",
}
LOCATION_EXACT = {
    "outdoors", "indoors", "sky", "blue_sky", "ocean", "water", "night", "day",
    "simple_background", "white_background", "black_background", "transparent_background",
}
LOCATION_WORDS = {
    "background", "outdoors", "indoors", "sky", "ocean", "water", "night", "day",
    "room", "street", "forest", "beach", "bedroom", "school", "city", "outside",
    "inside",
}
NSFW_EXACT = {
    "nude", "completely_nude", "topless", "nipples", "sex", "missionary",
    "cum", "pussy", "penis", "vaginal", "oral", "fellatio", "paizuri",
}
NSFW_WORDS = {
    "nude", "naked", "sex", "nsfw", "nipples", "pussy", "penis", "cum", "vaginal",
    "oral", "fellatio", "breast_grab", "ass_grab", "missionary",
}
SUBJECT_EXACT = {
    "1girl", "1boy", "solo", "multiple_girls", "multiple_boys", "2girls", "2boys",
    "girl", "boy",
}
MODE_CLASS = {
    "Pose / Body": "pose",
    "Camera / Composition": "camera",
    "Clothing / Appearance": "appearance",
    "Location / Scene": "location",
    "NSFW": "nsfw",
}


def valid_file(path: Path):
    return path.exists() and path.is_file() and path.stat().st_size > 0


def normalize_tag(tag: str):
    return (tag or "").strip().strip('"').replace(" ", "_").lower()


def normalize_ja(text: str):
    return (text or "").strip().lower().replace("\u3000", " ")


def visible_tag(tag: str):
    return tag.replace("_", " ")


def split_aliases(text: str):
    return [part.strip() for part in (text or "").replace("；", "|").replace("、", "|").split("|") if part.strip()]


def split_tag_aliases(text: str):
    return [
        normalize_tag(part)
        for part in (text or "").replace("|", ",").split(",")
        if normalize_tag(part)
    ]


def compact_key(text: str):
    return "".join(char for char in normalize_tag(text) if char.isalnum())


def tag_words(tag: str):
    return set(normalize_tag(tag).replace("-", "_").split("_"))


def tag_has_any(tag: str, exact, words):
    key = normalize_tag(tag)
    return key in exact or bool(tag_words(key) & words)


def related_tag_class(tag: str):
    key = normalize_tag(tag)
    if tag_has_any(key, NSFW_EXACT, NSFW_WORDS):
        return "nsfw"
    if key in LOCATION_EXACT:
        return "location"
    if tag_has_any(key, POSE_EXACT, POSE_WORDS):
        return "pose"
    if tag_has_any(key, CAMERA_EXACT, CAMERA_WORDS):
        return "camera"
    if tag_has_any(key, APPEARANCE_EXACT, APPEARANCE_WORDS):
        return "appearance"
    if tag_has_any(key, set(), LOCATION_WORDS):
        return "location"
    if key in SUBJECT_EXACT:
        return "subject"
    return "general"


def normalize_related_mode(mode):
    mode = (mode or "Auto").strip()
    return mode if mode in RELATED_MODES else "Auto"


def infer_related_mode(tag: str):
    tag_class = related_tag_class(tag)
    if tag_class == "nsfw":
        return "NSFW"
    if tag_class == "location":
        return "Location / Scene"
    if tag_class == "pose":
        return "Pose / Body"
    if tag_class == "camera":
        return "Camera / Composition"
    if tag_class == "appearance":
        return "Clothing / Appearance"
    return "Prompt Builder"


def tag_boundary_match(query: str, tag: str):
    if query == tag:
        return True
    return query in tag.split("_")


class JPTAIndex:
    def __init__(
        self,
        tags_path: Path,
        use_machine_labels=True,
        related_general_only=True,
        relation_limit=500,
        related_mode="Auto",
    ):
        self.tags_path = Path(tags_path)
        self.use_machine_labels = bool(use_machine_labels)
        self.related_general_only = bool(related_general_only)
        self.relation_limit = int(relation_limit)
        self.related_mode = normalize_related_mode(related_mode)
        self._counts = None
        self._categories = None
        self._aliases = None
        self._translations = None
        self._dictionary = None
        self._relations = None

    def tag_count_path(self):
        for file_name in [DANBOORU_TAGS_FILE, "danbooru.csv"]:
            path = self.tags_path.joinpath(file_name)
            if valid_file(path):
                return path
        return self.tags_path.joinpath(DANBOORU_TAGS_FILE)

    def load_tag_counts(self):
        if self._counts is not None:
            return self._counts
        path = self.tag_count_path()
        counts = {}
        if valid_file(path):
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.reader(handle):
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
        self._counts = counts
        return counts

    def load_tag_categories(self):
        if self._categories is not None:
            return self._categories
        path = self.tag_count_path()
        categories = {}
        if valid_file(path):
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.reader(handle):
                        if len(row) < 2:
                            continue
                        tag = normalize_tag(row[0])
                        if not tag or tag == "tag":
                            continue
                        try:
                            categories[tag] = int(float(row[1]))
                        except ValueError:
                            continue
            except Exception as exc:
                print(f"JP Tag Assistant: failed to read tag categories from {path.name}: {exc}")
        self._categories = categories
        return categories

    def load_tag_aliases(self):
        if self._aliases is not None:
            return self._aliases
        path = self.tag_count_path()
        aliases = {}
        if valid_file(path):
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.reader(handle):
                        if len(row) < 4:
                            continue
                        tag = normalize_tag(row[0])
                        if not tag or tag == "tag":
                            continue
                        tag_aliases = split_tag_aliases(row[3])
                        if tag_aliases:
                            aliases[tag] = tag_aliases
            except Exception as exc:
                print(f"JP Tag Assistant: failed to read aliases from {path.name}: {exc}")
        self._aliases = aliases
        return aliases

    def translation_files(self):
        candidates = ["danbooru_ja_user.csv", "danbooru-jp.csv"]
        if self.use_machine_labels:
            candidates.append("danbooru-machine-jp.csv")
        return [self.tags_path.joinpath(name) for name in candidates if valid_file(self.tags_path.joinpath(name))]

    def load_translations(self):
        if self._translations is not None:
            return self._translations
        labels = {}
        for path in self.translation_files():
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.reader(handle):
                        if len(row) < 2:
                            continue
                        tag = normalize_tag(row[0])
                        label = row[1].strip()
                        if tag and tag not in {"tag", "name"} and label:
                            labels.setdefault(tag, label)
            except Exception as exc:
                print(f"JP Tag Assistant: failed to read {path.name}: {exc}")
        self._translations = labels
        return labels

    def dictionary_files(self):
        candidates = ["jp_tag_user.csv", "jp_tag_dictionary.csv"]
        return [self.tags_path.joinpath(name) for name in candidates if valid_file(self.tags_path.joinpath(name))]

    def load_dictionary(self):
        if self._dictionary is not None:
            return self._dictionary
        entries = []
        for path in self.dictionary_files():
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
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

        for tag, label in self.load_translations().items():
            entries.append({
                "tag": tag,
                "labelJa": label,
                "terms": [label],
                "source": "translation",
            })
        self._dictionary = entries
        return entries

    def relation_files(self):
        patterns = ["*cooccurrence*.csv", "*co-occurrence*.csv", "*related*.csv"]
        found = []
        for pattern in patterns:
            found.extend(self.tags_path.glob(pattern))
        gz_path = self.tags_path.joinpath(DANBOORU_COOCCURRENCE_GZ_FILE)
        if valid_file(gz_path):
            found.append(gz_path)
        return sorted({p for p in found if p.is_file()})

    def open_relation_file(self, path):
        if path.suffix == ".gz":
            return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
        return path.open("r", encoding="utf-8-sig", newline="")

    def load_relations(self):
        if self._relations is not None:
            return self._relations

        counts = self.load_tag_counts()
        relations = {}
        for path in self.relation_files():
            try:
                with self.open_relation_file(path) as handle:
                    for row in csv.reader(handle):
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
            )[: self.relation_limit]

        self._relations = relations
        return relations

    def item_for_tag(self, tag, label=None, source="tag", score=0, matched=None):
        labels = self.load_translations()
        counts = self.load_tag_counts()
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

    def score_entry(self, query, entry):
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

    def score_english_tag_query(self, query: str, tag: str, aliases=None):
        aliases = aliases or []
        q = normalize_tag(query)
        if not q:
            return 0, ""

        visible = visible_tag(tag)
        terms = [tag, visible, *aliases, *(visible_tag(alias) for alias in aliases)]
        compact_query = compact_key(q)
        is_phrase_query = "_" in q
        best_score = 0
        best_term = ""

        for term in terms:
            t = normalize_tag(term)
            if not t:
                continue
            compact_term = compact_key(t)
            if q == t:
                score = 660
            elif compact_query and compact_query == compact_term:
                score = 650
            elif tag_boundary_match(q, t):
                score = 620
            elif t.startswith(q):
                score = 560
            elif compact_query and compact_term.startswith(compact_query):
                score = 540
            elif not is_phrase_query and len(compact_query) >= 4 and q in t:
                score = 500
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_term = term
        return best_score, best_term

    def search(self, query, limit=40):
        q = normalize_ja(query)
        if not q:
            return []

        limit = max(1, min(int(limit), 100))
        counts = self.load_tag_counts()
        aliases = self.load_tag_aliases()
        results = {}

        for entry in self.load_dictionary():
            score, matched = self.score_entry(q, entry)
            if score <= 0:
                continue
            if entry["source"] == "user":
                score += 120
            elif entry["source"] == "dictionary":
                score += 80
            elif entry["source"] == "translation":
                score = max(1, score - 180)
            tag = entry["tag"]
            item = self.item_for_tag(tag, entry["labelJa"], entry["source"], score, matched)
            previous = results.get(tag)
            if previous is None or item["score"] > previous["score"]:
                results[tag] = item

        tag_query = normalize_tag(q)
        if tag_query:
            for tag, count in counts.items():
                score, matched = self.score_english_tag_query(tag_query, tag, aliases.get(tag, []))
                if score:
                    item = self.item_for_tag(tag, source="danbooru", score=score, matched=tag_query)
                    item["count"] = count
                    item["matched"] = matched
                    previous = results.get(tag)
                    if previous is None or item["score"] > previous["score"]:
                        results[tag] = item

        return sorted(
            results.values(),
            key=lambda item: (item["score"], item.get("count", 0)),
            reverse=True,
        )[:limit]

    def attach_labels(self, items):
        labels = self.load_translations()
        counts = self.load_tag_counts()
        for item in items:
            tag = item["tag"]
            item["displayTag"] = visible_tag(tag)
            item["labelJa"] = item.get("labelJa") or labels.get(tag, "")
            item["count"] = item.get("count") or counts.get(tag, 0)
        return items

    def filter_related_items(self, items, selected_tag="", related_mode=None):
        mode = normalize_related_mode(related_mode or self.related_mode)
        if mode == "Auto":
            mode = infer_related_mode(selected_tag)
        if mode == "Off":
            return []
        if mode == "All":
            return items

        categories = self.load_tag_categories()
        general_items = [item for item in items if categories.get(item["tag"]) == 0]
        if mode in {"Prompt Builder", "All General"}:
            return general_items

        target_class = MODE_CLASS.get(mode)
        if not target_class:
            return general_items
        return [item for item in general_items if related_tag_class(item["tag"]) == target_class]

    def related(self, tag, limit=24, related_mode=None):
        key = normalize_tag(tag)
        if not key:
            return []
        if normalize_related_mode(related_mode or self.related_mode) == "Off":
            return []
        if self._relations is None:
            items = self.load_related_for_tag(key)
        else:
            items = self.load_relations().get(key, [])
        items = self.filter_related_items(items, key, related_mode)
        return self.attach_labels(items[: max(0, min(int(limit), 100))])

    def load_related_for_tag(self, key):
        counts = self.load_tag_counts()
        related = {}
        for path in self.relation_files():
            try:
                with self.open_relation_file(path) as handle:
                    for row in csv.reader(handle):
                        if len(row) < 2:
                            continue
                        left = normalize_tag(row[0])
                        right = normalize_tag(row[1])
                        if not left or not right or left in {"tag", "tag_a", "tag1"}:
                            continue
                        if left != key and right != key:
                            continue
                        try:
                            count = int(float(row[2])) if len(row) > 2 and row[2] else 0
                        except ValueError:
                            count = 0
                        other = right if left == key else left
                        previous = related.get(other)
                        if previous is None or count > previous["count"]:
                            related[other] = {"tag": other, "count": count}
            except Exception as exc:
                print(f"JP Tag Assistant: failed to read {path.name}: {exc}")

        count_a = counts.get(key, 0)
        for item in related.values():
            count_b = counts.get(item["tag"], 0)
            union = count_a + count_b - item["count"]
            item["score"] = item["count"] / union if union > 0 else 0
        return sorted(
            related.values(),
            key=lambda item: (item.get("score", 0), item["count"]),
            reverse=True,
        )[: self.relation_limit]
