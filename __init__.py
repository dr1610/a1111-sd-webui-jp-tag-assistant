from pathlib import Path
import sys

try:
    from .jpta_core import JPTAIndex, visible_tag
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from jpta_core import JPTAIndex, visible_tag


INDEX_CACHE = {}
TAGS_PATH = Path(__file__).resolve().parent.joinpath("tags")


def get_index(use_machine_labels=True, related_general_only=True):
    key = (bool(use_machine_labels), bool(related_general_only))
    index = INDEX_CACHE.get(key)
    if index is None:
        index = JPTAIndex(
            TAGS_PATH,
            use_machine_labels=use_machine_labels,
            related_general_only=related_general_only,
        )
        INDEX_CACHE[key] = index
    return index


def format_item(item, insert_spaces=False):
    tag = visible_tag(item["tag"]) if insert_spaces else item["tag"]
    label = item.get("labelJa") or ""
    count = item.get("count") or 0
    if label:
        return f"{tag} | {label} | {count}"
    return f"{tag} | {count}"


class JPTagAssistantSearch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query": ("STRING", {"default": "", "multiline": False}),
                "limit": ("INT", {"default": 12, "min": 1, "max": 100, "step": 1}),
                "related_limit": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "related_for": ("STRING", {"default": "", "multiline": False}),
                "use_machine_labels": ("BOOLEAN", {"default": True}),
                "related_general_only": ("BOOLEAN", {"default": True}),
                "insert_spaces": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("tags", "candidates", "related_tags", "related")
    FUNCTION = "search"
    CATEGORY = "JP Tag Assistant"

    def search(
        self,
        query,
        limit,
        related_limit,
        related_for,
        use_machine_labels,
        related_general_only,
        insert_spaces,
    ):
        index = get_index(use_machine_labels, related_general_only)
        candidates = index.search(query, limit)
        tags = [visible_tag(item["tag"]) if insert_spaces else item["tag"] for item in candidates]

        related_key = related_for.strip() or (candidates[0]["tag"] if candidates else "")
        related = index.related(related_key, related_limit) if related_key and related_limit else []
        related_tags = [visible_tag(item["tag"]) if insert_spaces else item["tag"] for item in related]

        return (
            ", ".join(tags),
            "\n".join(format_item(item, insert_spaces) for item in candidates),
            ", ".join(related_tags),
            "\n".join(format_item(item, insert_spaces) for item in related),
        )


NODE_CLASS_MAPPINGS = {
    "JPTagAssistantSearch": JPTagAssistantSearch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JPTagAssistantSearch": "JP Tag Assistant Search",
}
