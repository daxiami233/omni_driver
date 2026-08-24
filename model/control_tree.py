import json
import re
import xml.etree.ElementTree as ET

from ..errors import HierarchyError


BOOLEAN_ATTRIBUTES = {
    "clickable",
    "longClickable",
    "selected",
    "checkable",
    "checked",
    "enabled",
    "focused",
}


class ControlTree:
    def __init__(self, root=None):
        # Root element of the unified control tree.
        self.root = root

    def __str__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __call__(self, **kwargs):
        # Delegate attribute-based lookup to the root element.
        if self.root is None:
            return []
        return self.root.find(**kwargs)

    def count(self):
        # Count all elements in the tree recursively.
        def walk(element):
            total = 1
            for child in element.children:
                total += walk(child)
            return total

        return 0 if self.root is None else walk(self.root)

    def to_dict(self):
        return self.root.to_dict() if self.root is not None else None

    @classmethod
    def from_dict(cls, source):
        if source is None:
            return cls()
        return cls(Element.from_dict(source))


class Element:
    def __init__(self, attributes=None, children=None):
        # Store normalized control attributes and child elements.
        self.attributes = attributes or {}
        self.children = children or []

    def __str__(self):
        # Return attributes for quick inspection.
        return str(self.attributes)

    def __len__(self):
        # Allow len(element) to mean number of direct children.
        return len(self.children)

    def __getitem__(self, index):
        # Provide indexed child access.
        return self.children[index]

    @property
    def attribute(self):
        # Keep compatibility with existing attribute-style access.
        return self.attributes

    def append(self, element):
        # Add a child node and enforce the unified node type.
        if not isinstance(element, Element):
            raise TypeError(f"expected Element, got {type(element).__name__}")
        self.children.append(element)

    def find(self, **kwargs):
        # Recursively collect all elements whose attributes match kwargs.
        result = []
        if self._match(**kwargs):
            result.append(self)
        for child in self.children:
            result.extend(child.find(**kwargs))
        return result

    def to_dict(self):
        return {
            "attributes": dict(self.attributes),
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, source):
        if not isinstance(source, dict):
            raise HierarchyError("element data must be a dictionary")
        attributes = source.get("attributes", {})
        children = source.get("children", [])
        if not isinstance(attributes, dict) or not isinstance(children, list):
            raise HierarchyError("element data has invalid attributes or children")
        element = cls(attributes=_normalize_attributes(attributes))
        for child in children:
            element.append(cls.from_dict(child))
        return element

    def _match(self, **kwargs):
        for key, value in kwargs.items():
            if key in BOOLEAN_ATTRIBUTES:
                value = _to_bool(value)
            if self.attributes.get(key) != value:
                return False
        return True


class ControlTreeParser:
    @classmethod
    def dump(cls, tree, file, indent=2):
        if not isinstance(tree, ControlTree):
            raise TypeError("tree must be a ControlTree")
        with open(file, "w", encoding="utf-8") as write_file:
            json.dump(tree.to_dict(), write_file, indent=indent, ensure_ascii=False)

    @classmethod
    def load(cls, file):
        try:
            with open(file, encoding="utf-8") as read_file:
                return ControlTree.from_dict(json.load(read_file))
        except (OSError, json.JSONDecodeError, HierarchyError) as exc:
            raise HierarchyError(f"failed to load control tree: {exc}") from exc

    @classmethod
    def parse_hdc_json(cls, source):
        try:
            return ControlTree(cls._parse_hdc_node(source))
        except HierarchyError:
            raise
        except Exception as exc:
            raise HierarchyError(f"invalid Harmony hierarchy: {exc}") from exc

    @classmethod
    def parse_adb_xml(cls, source):
        if not isinstance(source, (str, bytes)) or not source:
            raise HierarchyError("Android hierarchy must be non-empty XML")
        try:
            return ControlTree(cls._parse_adb_node(ET.fromstring(source)))
        except ET.ParseError as exc:
            raise HierarchyError(f"invalid Android hierarchy XML: {exc}") from exc

    @classmethod
    def _parse_hdc_node(cls, source):
        if not isinstance(source, dict):
            raise HierarchyError("Harmony hierarchy node must be a dictionary")
        if "attributes" not in source:
            raise HierarchyError("Harmony hierarchy node is missing attributes")

        extra = source["attributes"]
        if not isinstance(extra, dict):
            raise HierarchyError("Harmony hierarchy attributes must be a dictionary")
        x1, y1, x2, y2 = cls._parse_bounds(extra.get("bounds", ""))
        attributes = _normalize_attributes({
            "bundle": extra.get("bundleName", ""),
            "page": extra.get("pagePath", ""),
            "bounds": [[x1, y1], [x2, y2]],
            "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
            "clickable": extra.get("clickable", ""),
            "longClickable": extra.get("longClickable", ""),
            "selected": extra.get("selected", ""),
            "checkable": extra.get("checkable", ""),
            "checked": extra.get("checked", ""),
            "type": extra.get("type", ""),
            "id": extra.get("id", ""),
            "text": extra.get("text", ""),
            "enabled": extra.get("enabled", ""),
            "focused": extra.get("focused", ""),
        })
        element = Element(attributes=attributes)
        children = source.get("children", [])
        if not isinstance(children, list):
            raise HierarchyError("Harmony hierarchy children must be a list")
        for child in children:
            element.append(cls._parse_hdc_node(child))
        return element

    @classmethod
    def _parse_adb_node(cls, source):
        # Convert one Android XML node and its descendants into Element objects.
        if source.tag == "hierarchy":
            attributes = _normalize_attributes({
                "bundle": "",
                "page": "",
                "bounds": [[0, 0], [0, 0]],
                "center": [0, 0],
                "clickable": False,
                "longClickable": False,
                "selected": False,
                "checkable": False,
                "checked": False,
                "type": "",
                "id": "",
                "text": "",
                "enabled": False,
                "focused": False,
            })
        else:
            extra = source.attrib
            x1, y1, x2, y2 = cls._parse_bounds(extra.get("bounds", ""), allow_fallback=True)
            attributes = _normalize_attributes({
                "bundle": extra.get("package", ""),
                "page": "",
                "bounds": [[x1, y1], [x2, y2]],
                "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                "clickable": extra.get("clickable", ""),
                "longClickable": extra.get("long-clickable", ""),
                "selected": extra.get("selected", ""),
                "checkable": extra.get("checkable", ""),
                "checked": extra.get("checked", ""),
                "type": extra.get("class", ""),
                "id": extra.get("resource-id", ""),
                "text": extra.get("text", ""),
                "enabled": extra.get("enabled", ""),
                "focused": extra.get("focused", ""),
            })

        element = Element(attributes=attributes)
        for child in source:
            element.append(cls._parse_adb_node(child))
        return element

    @staticmethod
    def _parse_bounds(raw_bounds, allow_fallback=False):
        if (
            isinstance(raw_bounds, (list, tuple))
            and len(raw_bounds) == 2
            and all(isinstance(point, (list, tuple)) and len(point) == 2 for point in raw_bounds)
        ):
            try:
                return tuple(int(value) for point in raw_bounds for value in point)
            except (TypeError, ValueError):
                pass
        match = re.fullmatch(
            r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]",
            str(raw_bounds or "").strip(),
        )
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            if (x1, y1, x2, y2) == (2147483647, 2147483647, -2147483648, -2147483648):
                return 0, 0, 100, 100
            return x1, y1, x2, y2
        if allow_fallback:
            return 0, 0, 100, 100
        raise HierarchyError(f"invalid bounds: {raw_bounds}")


def _normalize_attributes(attributes):
    normalized = dict(attributes)
    for key in BOOLEAN_ATTRIBUTES:
        normalized[key] = _to_bool(normalized.get(key))

    bounds = normalized.get("bounds", [[0, 0], [0, 0]])
    x1, y1, x2, y2 = ControlTreeParser._parse_bounds(bounds, allow_fallback=True)
    normalized["bounds"] = [[x1, y1], [x2, y2]]

    center = normalized.get("center")
    if isinstance(center, (list, tuple)) and len(center) == 2:
        try:
            normalized["center"] = [int(center[0]), int(center[1])]
        except (TypeError, ValueError):
            normalized["center"] = [int((x1 + x2) / 2), int((y1 + y2) / 2)]
    else:
        normalized["center"] = [int((x1 + x2) / 2), int((y1 + y2) / 2)]
    return normalized


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
