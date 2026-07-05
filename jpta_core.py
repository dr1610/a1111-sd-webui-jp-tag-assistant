import csv
import gzip
from pathlib import Path


DANBOORU_TAGS_FILE = "danbooru_tags.csv"
DANBOORU_COOCCURRENCE_FILE = "danbooru_tags_cooccurrence.csv"
DANBOORU_COOCCURRENCE_GZ_FILE = f"{DANBOORU_COOCCURRENCE_FILE}.gz"


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


def tag_boundary_match(query: str, tag: str):
    if query == tag:
        return True
    return query in tag.split("_")


class JPTAIndex:
    def __init__(self, tags_path: Path, use_machine_labels=True, related_general_only=True, relation_limit=500):
        self.tags_path = Path(tags_path)
        self.use_machine_labels = bool(use_machine_labels)
        self.related_general_only = bool(related_general_only)
        self.relation_limit = int(relation_limit)
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

    def filter_related_items(self, items):
        if not self.related_general_only:
            return items
        categories = self.load_tag_categories()
        return [item for item in items if categories.get(item["tag"]) == 0]

    def related(self, tag, limit=24):
        key = normalize_tag(tag)
        if not key:
            return []
        if self._relations is None:
            items = self.load_related_for_tag(key)
        else:
            items = self.load_relations().get(key, [])
        items = self.filter_related_items(items)
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
