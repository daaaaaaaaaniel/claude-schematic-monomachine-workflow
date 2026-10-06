#!/usr/bin/env python3
"""Lock (or unlock) the parts of one approved block on the live board, through KiCad's API, then save.

    python3 pcb/tools/lock_block.py <group> [--unlock]       # group from pcb/design/groups.py, e.g. seed3, power
    python3 pcb/tools/lock_block.py --refs A1,C6 [--unlock]

Only for blocks d has approved; commit right after, so git history records each approval. Only the parts already
on the board are locked (a group's untraced minor parts that are still parked stay free). check_locks.py then
rejects any later candidate that moves them. To revise an approved block, unlock just that block.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import groups as G  # noqa: E402
from kipy import KiCad  # noqa: E402

SOCK = "ipc:///tmp/kicad/api.sock"


def refs_for(name):
    for table in (G.MAIN, G.CONTROL):
        if name in table:
            primary, rest = table[name]
            return [primary] + list(rest)
    raise SystemExit(f"unknown group {name!r}; groups: {', '.join(list(G.MAIN) + list(G.CONTROL))}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    unlock = "--unlock" in sys.argv
    refs = args[0].split(",") if "--refs" in sys.argv else refs_for(args[0])
    traced = set()
    try:
        import drc_summary as D
        traced = D.traced_parts()
    except Exception:
        pass
    b = KiCad(socket_path=SOCK).get_board()
    sec = {r for v in G.SECONDARY.values() for r in v}
    changed = []
    for f in b.get_footprints():
        r = f.reference_field.text.value
        if r not in refs:
            continue
        minor = r[0] in "RC" and r not in sec and r not in traced
        if minor and not unlock:
            continue                                   # parked minor part: not part of the approval
        if f.locked != (not unlock):
            f.locked = not unlock
            changed.append(f)
    if changed:
        cm = b.begin_commit()
        b.update_items(changed)
        b.push_commit(cm, f"{'Unlock' if unlock else 'Lock'} block {args[0]}")
        b.save()
    print(f"{'unlocked' if unlock else 'locked'}: {', '.join(sorted(f.reference_field.text.value for f in changed)) or 'nothing new'}")


if __name__ == "__main__":
    main()
