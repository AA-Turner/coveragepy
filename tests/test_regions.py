# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""Tests for coverage/regions.py."""

from __future__ import annotations

import collections
import textwrap
from pathlib import Path

import pytest

import coverage
from coverage import env
from coverage.plugin import CodeRegion
from coverage.regions import code_regions


skip_pypy38 = pytest.mark.skipif(
    env.PYPY and env.PYVERSION < (3, 9),
    reason="PyPy 3.8 somehow gets different results from ast?",
    # But PyPy 3.8 is almost out of support so meh.
)

@skip_pypy38
def test_code_regions() -> None:
    regions = code_regions(textwrap.dedent("""\
        # Numbers in this code are the line number.
        '''Module docstring'''

        CONST = 4
        class MyClass:
            class_attr = 6

            def __init__(self):
                self.x = 9

            def method_a(self):
                self.x = 12
                def inmethod():
                    self.x = 14
                    class DeepInside:
                        def method_b():
                            self.x = 17
                        class Deeper:
                            def bb():
                                self.x = 20
                self.y = 21

            class InnerClass:
                constant = 24
                def method_c(self):
                    self.x = 26

        def func():
            x = 29
            y = 30
            def inner():
                z = 32
                def inner_inner():
                    w = 34

            class InsideFunc:
                def method_d(self):
                    self.x = 38

            return 40

        async def afunc():
            x = 43
    """))

    assert regions == {
        "function": [
            CodeRegion("MyClass.__init__", start=8, lines={9}),
            CodeRegion("MyClass.method_a", start=11, lines={12, 13, 21}),
            CodeRegion("MyClass.method_a.inmethod", start=13, lines={14, 15, 16, 18, 19}),
            CodeRegion("MyClass.method_a.inmethod.DeepInside.method_b", start=16, lines={17}),
            CodeRegion("MyClass.method_a.inmethod.DeepInside.Deeper.bb", start=19, lines={20}),
            CodeRegion("MyClass.InnerClass.method_c", start=25, lines={26}),
            CodeRegion("func", start=28, lines={29, 30, 31, 35, 36, 37, 39, 40}),
            CodeRegion("func.inner", start=31, lines={32, 33}),
            CodeRegion("func.inner.inner_inner", start=33, lines={34}),
            CodeRegion("func.InsideFunc.method_d", start=37, lines={38}),
            CodeRegion("afunc", start=42, lines={43}),
        ],
        "class": [
            CodeRegion("MyClass", start=5, lines={9, 12, 13, 14, 15, 16, 18, 19, 21}),
            CodeRegion("MyClass.method_a.inmethod.DeepInside", start=15, lines={17}),
            CodeRegion("MyClass.method_a.inmethod.DeepInside.Deeper", start=18, lines={20}),
            CodeRegion("MyClass.InnerClass", start=23, lines={26}),
            CodeRegion("func.InsideFunc", start=36, lines={38}),
        ],
    }


@skip_pypy38
def test_real_code_regions() -> None:
    # Run code_regions on most of the coverage source code, checking that it
    # succeeds and there are no overlaps.

    cov_dir = Path(coverage.__file__).parent.parent
    any_fails = False
    # To run against all the files in the tox venvs:
    #   for source_file in cov_dir.rglob("*.py"):
    for sub in [".", "ci", "coverage", "lab", "tests"]:
        for source_file in (cov_dir / sub).glob("*.py"):
            regions = code_regions(source_file.read_text(encoding="utf-8"))
            for kind, regs in regions.items():
                line_counts = collections.Counter(lno for reg in regs for lno in reg.lines)
                overlaps = [line for line, count in line_counts.items() if count > 1]
                if overlaps:    # pragma: only failure
                    print(
                        f"{kind.title()} overlaps in {source_file.relative_to(Path.cwd())}: "
                        + f"{overlaps}"
                    )
                    any_fails = True
    if any_fails:
        pytest.fail("Overlaps were found")  # pragma: only failure
