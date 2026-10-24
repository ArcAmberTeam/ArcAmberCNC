"""Interactive test-only G0/G1 playback. Never imports LinuxCNC or opens a socket.

This is not an RS274 interpreter, motion planner or cutting simulation. Reject
unsupported syntax rather than displaying plausible but incorrect geometry.
"""
import math
import re
from pathlib import Path

INITIAL = [0.0, 0.0, 5.0]
WORD = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
SETUP = {17, 21, 40, 49, 54, 80, 90, 94}


def read_linear_program(path):
    """Read explicit metric/absolute, XY-plane G0/G1 programs, max 128 KiB."""
    path = Path(path).resolve(strict=True)
    if path.stat().st_size > 128 * 1024:
        raise ValueError("模拟文件不能超过 128 KiB")
    source = path.read_text(encoding="utf-8-sig")
    position, feed, spindle = INITIAL[:], 0.0, 0.0
    spindle_on, motion, ended = False, None, False
    setup, blocks, segments = set(), [], []
    for number, original in enumerate(source.splitlines(), 1):
        line = re.sub(r"\([^()]*\)", "", original.split(";", 1)[0]).upper()
        line = re.sub(r"\s+", "", line)
        if not line:
            continue
        def fail(reason):
            raise ValueError(f"第 {number} 行：{reason}")
        if ended:
            fail("M2 后仍有指令")
        words = WORD.findall(line)
        if "".join(letter + value for letter, value in words) != line:
            fail("只支持数字 G0/G1 演示程序，不支持表达式、子程序或宏")
        axes, gwords, mwords, seen = {}, [], [], set()
        for letter, raw in words:
            value = float(raw)
            if not math.isfinite(value) or abs(value) > 1e6:
                fail("数值超出测试回放范围")
            if letter not in "GM" and letter in seen:
                fail(f"重复的 {letter} 字")
            seen.add(letter)
            if letter == "G":
                if value not in SETUP | {0, 1}:
                    fail(f"回放器不支持 G{raw}")
                gwords.append(int(value))
            elif letter == "M":
                if value not in {2, 3, 5, 9}:
                    fail(f"回放器不支持 M{raw}")
                mwords.append(int(value))
            elif letter in "XYZ":
                axes["XYZ".index(letter)] = value
            elif letter == "F":
                if value <= 0:
                    fail("进给必须大于 0")
                feed = value
            elif letter == "S":
                if value < 0:
                    fail("主轴转速不能为负")
                spindle = value
            else:
                fail(f"回放器不支持 {letter} 字")
        if len([g for g in gwords if g in {0, 1, 80}]) > 1 or len(mwords) != len(set(mwords)) or (3 in mwords and 5 in mwords):
            fail("冲突或重复的模态指令")
        setup.update(gwords)
        for g in gwords:
            if g in {0, 1, 80}:
                motion = None if g == 80 else g
        if 3 in mwords:
            spindle_on = True
        if 5 in mwords or 2 in mwords:
            spindle_on = False
        start = position[:]
        segment, duration, velocity = None, 0.15, 0.0
        if axes:
            if not SETUP.issubset(setup) or motion is None:
                fail("移动前需完整的 G21/G17/G90/G94/G40/G49/G54/G80 初始化及 G0/G1")
            if 2 in mwords:
                fail("演示程序要求 M2 单独结束")
            if motion == 1 and feed <= 0:
                fail("G1 前需指定 F")
            for axis, value in axes.items():
                position[axis] = value
            velocity = (1200.0 if motion == 0 else feed) / 60
            length = math.dist(start, position)
            duration = max(0.15, length / velocity)
            if length:
                segment = {"type": "rapid" if motion == 0 else "feed", "start": start,
                           "end": position[:], "line": number}
                segments.append(segment)
        blocks.append({"line": number, "start": start, "end": position[:],
                       "duration": duration, "velocity": velocity, "motion": bool(axes), "axes": axes,
                       "rapid": motion == 0, "spindle": spindle if spindle_on else 0})
        ended = 2 in mwords
    if not ended or not segments:
        raise ValueError("演示程序需包含移动并以 M2 结束")
    points = [INITIAL] + [s["end"] for s in segments]
    return {"path": str(path), "text": source, "lines": source.splitlines(), "blocks": blocks,
            "segments": segments, "bounds": {key: [fn(p[i] for p in points) for i in range(3)]
                                              for key, fn in (("min", min), ("max", max))}}
