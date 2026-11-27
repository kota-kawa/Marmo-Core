"""Terminal tables must shorten and align by display width, not by character count (#87)."""

from __future__ import annotations

import re
import unicodedata
import unittest

from marmo_core import ResourceDefinition
from marmo_core.formatting import render_resource_table


def _width(text: str) -> int:
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _description_cell(table: str) -> str:
    """The last column of the last row; columns are separated by two or more spaces."""

    return re.split(r"\s{2,}", table.splitlines()[-1].strip())[-1]


def _definition(resource_id: str, description: str, *, tags: tuple[str, ...] = ("test",)) -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": "memory",
            "name": resource_id,
            "version": "1.0.0",
            "description": description,
            "capabilities": ["x"],
            "input_summary": "x",
            "output_summary": "x",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"memory://test/{resource_id}",
            "tags": list(tags),
        }
    )


class DisplayWidthTests(unittest.TestCase):
    def test_a_long_japanese_description_keeps_its_opening(self) -> None:
        description = "ファイルを読み込んで内容をそのまま返すツールです。" * 6

        table = render_resource_table([_definition("memory.test.a", description)])

        cell = _description_cell(table)
        self.assertTrue(cell.startswith("ファイルを読み込んで"), cell)
        self.assertTrue(cell.endswith("..."))
        self.assertLessEqual(_width(cell), 58)
        self.assertGreater(_width(cell), 50)

    def test_a_long_ascii_description_still_breaks_on_a_word(self) -> None:
        description = "Read a UTF-8 file from a confined local workspace and return its contents as text " * 2

        table = render_resource_table([_definition("memory.test.a", description)])

        cell = _description_cell(table)
        self.assertEqual(cell, "Read a UTF-8 file from a confined local workspace and...")

    def test_short_text_is_untouched(self) -> None:
        table = render_resource_table([_definition("memory.test.a", "短い説明")])

        self.assertIn("短い説明", table)
        self.assertNotIn("...", table)

    def test_mixed_text_cuts_inside_the_japanese_run(self) -> None:
        description = "Read ファイルを読み込んで内容をそのまま返すツールです。とても長い説明が続きます" * 2

        cell = _description_cell(render_resource_table([_definition("memory.test.a", description)]))

        self.assertTrue(cell.startswith("Read ファイル"), cell)
        self.assertLessEqual(_width(cell), 58)

    def test_columns_line_up_by_display_width(self) -> None:
        resources = [
            _definition("memory.test.ascii", "plain ascii description"),
            _definition("memory.test.jp", "日本語だけの説明です" * 8, tags=("日本語", "検索")),
            _definition("memory.test.mixed", "Mixed 日本語 text", tags=("タグ",)),
        ]

        lines = render_resource_table(resources).splitlines()

        self.assertEqual(len({_width(line) for line in lines}), 1, lines)
        # The version column starts at the same display offset in the header and every row.
        starts = {_width(line[: line.index(marker)]) for line, marker in zip((lines[0], *lines[2:]), ("version", "1.0.0", "1.0.0", "1.0.0"))}
        self.assertEqual(len(starts), 1, starts)

    def test_wide_tags_are_aligned_with_the_header(self) -> None:
        resource = _definition("memory.test.a", "x", tags=("日本語のタグ",))

        lines = render_resource_table([resource]).splitlines()

        self.assertEqual(_width(lines[0]), _width(lines[1]))
        self.assertEqual(_width(lines[2]), _width(lines[1]))


if __name__ == "__main__":
    unittest.main()
