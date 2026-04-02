import json
import re
import xml.etree.ElementTree as ET


class ControlTree:
    def __init__(self, root=None):
        # Root element of the unified control tree.
        self.root = root

    def __str__(self):
        # Serialize the tree to a readable string for debugging.
        return str(self.root.to_dict()) if self.root else "{}"

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
        # Convert the element subtree into a JSON-friendly structure.
        return {
            "attributes": self._json_attributes(),
            "children": [child.to_dict() for child in self.children],
        }

    def _match(self, **kwargs):
        # Check whether the current element satisfies all requested attributes.
        for key, value in kwargs.items():
            if self.attributes.get(key) != value:
                return False
        return True

    def _json_attributes(self):
        # Normalize complex fields before serialization.
        attributes = dict(self.attributes)
        bounds = attributes.get("bounds")
        if bounds is not None:
            attributes["bounds"] = "".join(str(part) for part in bounds)
        center = attributes.get("center")
        if center is not None:
            attributes["center"] = str(center)
        return attributes


class ControlTreeParser:
    @classmethod
    def dump(cls, tree, file, indent=2):
        # Write the unified tree structure to disk as JSON.
        with open(file, "w", encoding="utf-8") as write_file:
            json.dump(tree.root.to_dict(), write_file, indent=indent, ensure_ascii=False)

    @classmethod
    def parse_hdc_json(cls, source):
        # Parse a Harmony JSON hierarchy into the unified tree model.
        return ControlTree(cls._parse_hdc_node(source))

    @classmethod
    def parse_adb_xml(cls, source):
        # Parse an Android XML hierarchy into the unified tree model.
        return ControlTree(cls._parse_adb_node(ET.fromstring(source)))

    @classmethod
    def _parse_hdc_node(cls, source):
        # Convert one Harmony node and its descendants into Element objects.
        if "attributes" not in source:
            raise KeyError("expected key: attributes")

        extra = source["attributes"]
        x1, y1, x2, y2 = cls._parse_bounds(extra["bounds"])
        attributes = {
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
        }
        element = Element(attributes=attributes)
        for child in source.get("children", []):
            element.append(cls._parse_hdc_node(child))
        return element

    @classmethod
    def _parse_adb_node(cls, source):
        # Convert one Android XML node and its descendants into Element objects.
        if source.tag == "hierarchy":
            attributes = {
                "bundle": "",
                "page": "",
                "bounds": [[0, 0], [0, 0]],
                "center": [0, 0],
                "clickable": "",
                "longClickable": "",
                "selected": "",
                "checkable": "",
                "checked": "",
                "type": "",
                "id": "",
                "text": "",
                "enabled": "",
                "focused": "",
            }
        else:
            extra = source.attrib
            x1, y1, x2, y2 = cls._parse_bounds(extra.get("bounds", ""), allow_fallback=True)
            attributes = {
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
            }

        element = Element(attributes=attributes)
        for child in source:
            element.append(cls._parse_adb_node(child))
        return element

    @staticmethod
    def _parse_bounds(raw_bounds, allow_fallback=False):
        # Parse bounds text into coordinates, with an optional fallback for invalid values.
        match = re.match(r"\[(-?\d+),\s*(-?\d+)\]\[(-?\d+),\s*(-?\d+)\]", raw_bounds)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            if (x1, y1, x2, y2) == (2147483647, 2147483647, -2147483648, -2147483648):
                return 0, 0, 100, 100
            return x1, y1, x2, y2
        if allow_fallback:
            return 0, 0, 100, 100
        raise ValueError(f"invalid bounds: {raw_bounds}")
