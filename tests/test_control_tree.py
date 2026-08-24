import json

import pytest

from omni_driver.errors import HierarchyError
from omni_driver.model import ControlTree, ControlTreeParser


ANDROID_XML = """<hierarchy>
  <node package="com.example" bounds="[0,0][100,200]" clickable="true"
        long-clickable="false" selected="false" checkable="false" checked="false"
        class="android.widget.Button" resource-id="com.example:id/ok" text="OK"
        enabled="true" focused="false" />
</hierarchy>"""

HARMONY_JSON = {
    "attributes": {
        "bundleName": "com.example.harmony",
        "pagePath": "pages/Main",
        "bounds": "[0,0][100,200]",
        "clickable": True,
        "longClickable": False,
        "selected": False,
        "checkable": False,
        "checked": False,
        "type": "Button",
        "id": "ok",
        "text": "OK",
        "enabled": True,
        "focused": False,
    },
    "children": [],
}


def test_android_and_harmony_boolean_attributes_are_normalized():
    android = ControlTreeParser.parse_adb_xml(ANDROID_XML)
    harmony = ControlTreeParser.parse_hdc_json(HARMONY_JSON)

    assert android(text="OK")[0].attribute["clickable"] is True
    assert harmony(text="OK")[0].attribute["clickable"] is True
    assert android(clickable=True)[0].attribute["text"] == "OK"
    assert harmony(clickable="true")[0].attribute["text"] == "OK"


def test_control_tree_dump_and_load_round_trip(tmp_path):
    tree = ControlTreeParser.parse_adb_xml(ANDROID_XML)
    output = tmp_path / "tree.json"

    ControlTreeParser.dump(tree, output)
    loaded = ControlTreeParser.load(output)

    assert loaded.to_dict() == tree.to_dict()
    assert json.loads(str(loaded)) == tree.to_dict()


def test_empty_control_tree_can_round_trip(tmp_path):
    output = tmp_path / "empty.json"
    ControlTreeParser.dump(ControlTree(), output)

    assert ControlTreeParser.load(output).count() == 0


def test_invalid_hierarchy_has_stable_error():
    with pytest.raises(HierarchyError, match="invalid Android hierarchy XML"):
        ControlTreeParser.parse_adb_xml("<hierarchy>")

    with pytest.raises(HierarchyError, match="missing attributes"):
        ControlTreeParser.parse_hdc_json({"children": []})
