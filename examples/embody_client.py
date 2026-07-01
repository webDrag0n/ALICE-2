#!/usr/bin/env python3
"""Oikos 参考客户端 —— "如何连接世界中的一具身体" 的可运行示范。

配套文档: ../embody.md (五步连接流程) / ../world.md Part VIII (协议)。

它把 embody.md 的流程落成真实代码: list_bodies -> attach -> 循环
(sense / list_skills / act) -> detach。只用 Python 标准库 (urllib),
任何能发 HTTP 的语言都能照着写。

两种运行方式:
    # 1) 连真实 Oikos 世界进程 (world.toml 里 server.port=7000)
    python embody_client.py --url http://localhost:7000 --body guest

    # 2) 无服务器, 用内置的离线桩 (FakeWorld) 跑通整条流程, 便于先理解
    python embody_client.py --demo

注意: 本文件是"心智侧"客户端。世界进程(Oikos daemon)本身见 world.md,
不在此实现 —— 这正是解耦: 连接方只需这几个调用, 不必懂世界内部。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request



# ───────────────────────── 协议客户端 ─────────────────────────
class OikosClient:
    """对 Oikos 世界协议的薄封装 (world.md Part VIII)。

    每个方法 = 一个协议操作。错误一律 fail-loud: 世界返回的错误会被原样
    抛成 WorldError, 绝不假装成功 —— 这样心智的世界模型不会与真实分叉。
    """

    def __init__(self, base_url: str, mind_id: str):
        self.base = base_url.rstrip("/")
        self.mind_id = mind_id
        self.body_id: str | None = None

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise WorldError(f"{method} {path} -> HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise WorldError(f"无法连到世界 {url}: {e.reason}") from e

    # -- 五步流程 --
    def list_bodies(self) -> list[dict]:
        return self._call("GET", "/list_bodies").get("bodies", [])

    def attach(self, body_id: str) -> dict:
        out = self._call("POST", "/attach",
                         {"mind_id": self.mind_id, "body_id": body_id})
        self.body_id = body_id
        return out.get("observation", {})

    def sense(self) -> dict:
        return self._call("GET", "/sense")

    def list_skills(self) -> list[str]:
        return self._call("GET", "/list_skills").get("skills", [])

    def act(self, skill: str, **args) -> dict:
        return self._call("POST", "/act", {"skill": skill, "args": args})

    def detach(self) -> None:
        self._call("POST", "/detach", {})
        self.body_id = None


class WorldError(RuntimeError):
    """世界显式失败 (world.md W7 no-fallback)。"""




# ───────────────── 离线桩: 一个最小 FakeWorld ─────────────────
# 它不是真正的 Oikos(没有时钟/生理/真实寻路), 只够把 embody.md 的
# 流程"演"出来, 让你在没有世界进程时也能理解客户端怎么用。
# 真实世界的规格见 world.md —— 那才是这个桩在模仿的对象。
class FakeWorld:
    """模拟 OikosClient 的同名方法, 用于 --demo。"""

    def __init__(self):
        # 极简户型: 几个房间由门相连(真实户型见 map.toml)
        self.bodies = {
            "alice": {"name": "Alice", "pos": [2.5, 2.5], "heading": 90,
                      "room": "bedroom", "claimed_by": "alice",
                      "posture": "standing", "held": []},
            "guest": {"name": "Hermes", "pos": [3.5, 6.5], "heading": 0,
                      "room": "living", "claimed_by": None,
                      "posture": "standing", "held": []},
        }
        self.me: str | None = None
        self.t = 0

    # -- 协议方法(签名与 OikosClient 对齐) --
    def list_bodies(self):
        return [{"body_id": bid, "display_name": b["name"],
                 "claimed_by": b["claimed_by"],
                 "status": f'在{b["room"]}, ' +
                           ("空置" if b["claimed_by"] is None else "已认领")}
                for bid, b in self.bodies.items()]

    def attach(self, body_id):
        if body_id not in self.bodies:
            raise WorldError(f"没有这具身体: {body_id}")
        if self.bodies[body_id]["claimed_by"] not in (None, "demo"):
            raise WorldError(f"身体 {body_id} 已被 "
                             f"{self.bodies[body_id]['claimed_by']} 认领")
        self.bodies[body_id]["claimed_by"] = "demo"
        self.me = body_id
        return self.sense()

    def detach(self):
        if self.me:
            self.bodies[self.me]["claimed_by"] = None
            self.me = None


    def sense(self):
        me = self.bodies[self.me]
        # 同室的其他身体 → seen(视觉); 同室说话 → heard(听觉)。简化: 同室=看得见/听得清。
        seen, heard = [], []
        for bid, b in self.bodies.items():
            if bid == self.me:
                continue
            if b["room"] == me["room"]:
                seen.append({"kind": "body", "ref": b["name"],
                             "bearing": "附近", "distance": 2.5,
                             "clarity": 0.9, "detail": f'{b["name"]}, {b["posture"]}'})
        room = me["room"]
        narration = (f'你在{room}，面朝 {me["heading"]}°，{me["posture"]}。'
                     + (f'附近有 {seen[0]["ref"]}。' if seen else '这里没别人。')
                     + f'肚子饿度约 {round(0.2 + self.t * 0.001, 2)}。')
        return {
            "world_time": {"clock": f"t+{self.t}s", "phase": "day"},
            "proprioception": {
                "posture": me["posture"], "heading_deg": me["heading"],
                "in_room": room, "held": me["held"], "reachable": [],
                "physiology": {"hunger": round(0.2 + self.t * 0.001, 2),
                               "thirst": 0.3, "bladder": 0.2, "fatigue": 0.15}},
            "here": {"room": room, "room_shape": "(demo 桩不建模形状)", "light": 0.8,
                     "exits": [{"to": "hall", "dir": "门口", "dist": 3.0}]},
            "seen": seen,
            "heard": heard,
            "held_detail": [],
            "available_skills": self.list_skills(),
            "narration": narration,
        }

    def list_skills(self):
        me = self.bodies[self.me]
        skills = ["move_to", "turn", "look_at", "speak", "scan"]
        if me["posture"] == "standing":
            skills += ["sit_down", "lie_down"]
        else:
            skills.append("stand_up")
        if "phone" in me["held"]:
            skills += ["open_app", "send_message"]
        else:
            skills.append("pick_up_phone")
        return skills

    def act(self, skill, **args):
        me = self.bodies[self.me]
        self.t += 5
        if skill == "move_to":
            target = args.get("target")
            # 桩: 接受房间名, 平滑"走"过去并切房间(真实世界是连续寻路, 这里简化)
            dest = {"kitchen": ([9.5, 6.5], "kitchen"), "living": ([3.5, 6.5], "living"),
                    "bedroom": ([2.5, 2.5], "bedroom")}.get(target)
            if dest:
                me["pos"], me["room"] = dest
                return {"ok": True, "outcome": {"now_at": me["pos"],
                                                "room": target, "distance_m": 4.5,
                                                "world_time_spent": "4s"}}
            raise WorldError(f"去不了 {target}: demo 桩只认 "
                             "living/kitchen/bedroom")
        if skill in ("turn", "look_at"):
            me["heading"] = args.get("heading", me["heading"])
            return {"ok": True, "outcome": {"heading": me["heading"], "note": "已转向"}}
        if skill == "speak":
            content = args.get("content", "")
            heard = [b["name"] for bid, b in self.bodies.items()
                     if bid != self.me and b["room"] == me["room"]]
            return {"ok": True, "outcome": {"said": content, "heard_by": heard}}
        if skill in ("sit_down", "lie_down"):
            me["posture"] = "seated" if skill == "sit_down" else "lying"
            return {"ok": True, "outcome": {"posture": me["posture"]}}
        if skill == "stand_up":
            me["posture"] = "standing"
            return {"ok": True, "outcome": {"posture": "standing"}}
        if skill == "pick_up_phone":
            me["held"].append("phone")
            return {"ok": True, "outcome": {"held": me["held"]}}
        if skill in ("scan", "open_app", "send_message"):
            return {"ok": True, "outcome": {"note": f"(demo) {skill} 完成"}}
        raise WorldError(f"此刻不能做 {skill} (不在可用目录里)")




# ───────────────────────── 场景演示 ─────────────────────────
def run_scenario(world) -> None:
    """走一遍 embody.md 的五步, 并演示"走到对方面前说句话"。

    `world` 可以是真实 OikosClient, 也可以是 FakeWorld —— 同一套调用,
    这正是文档想说的: 连接方代码与世界实现无关。
    """
    def show(title, obj):
        print(f"\n── {title} ──")
        print(json.dumps(obj, ensure_ascii=False, indent=2))

    # Step 1: 看世界里有哪些身体, 挑一具空置的
    bodies = world.list_bodies()
    show("Step 1 · list_bodies", bodies)
    free = [b for b in bodies if b["claimed_by"] in (None, "demo")]
    if not free:
        print("没有空置身体可认领, 退出。")
        return
    target_body = free[0]["body_id"]

    # Step 2: 主动认领 —— "我清楚知道我要进哪具身体"
    print(f"\n>>> 认领身体: {target_body}")
    obs = world.attach(target_body)
    show("Step 2 · attach 后的第一帧观察", obs)

    # Step 3 + 4: 循环 sense / 决策 / act
    plan = [
        ("move_to", {"target": "living"}),     # 走到客厅(对方在那)
        ("speak", {"content": "嗨 Hermes, 我刚到, 在忙吗?",
                   "loudness": "normal"}),
        ("scan", {}),                          # 环视一圈, 补全房间细节
    ]
    for skill, args in plan:
        skills = world.list_skills()
        if skill not in skills:
            print(f"\n[!] 此刻不能 {skill} (不在 {skills}); 跳过或先补前置")
            continue
        try:
            out = world.act(skill, **args)
            show(f"Step 4 · act({skill})", out)
        except WorldError as e:
            # fail-loud: 读懂错误 → 本该补前置 → 这里仅打印示范
            print(f"\n[WorldError] {e}\n  → 应对: 补上缺的前置后重试")
        time.sleep(0.2)

    show("再 sense 一次, 确认处境变化", world.sense())

    # Step 5: 离开前释放身体
    print("\n>>> detach: 释放身体, 它留在世界里变回空置")
    world.detach()


def main() -> int:
    ap = argparse.ArgumentParser(description="Oikos 参考客户端 (embody.md 流程)")
    ap.add_argument("--url", help="Oikos 世界进程地址, 如 http://localhost:7000")
    ap.add_argument("--mind", default="openclaw",
                    help="本心智的标识(用于认领归属/日志)")
    ap.add_argument("--body", help="要认领的 body_id (省略则自动挑空置的)")
    ap.add_argument("--demo", action="store_true",
                    help="无服务器, 用内置 FakeWorld 跑通流程")
    args = ap.parse_args()

    if args.demo:
        print("[demo] 用内置 FakeWorld (无真实世界进程)。真实规格见 world.md。")
        run_scenario(FakeWorld())
        return 0

    if not args.url:
        ap.error("需要 --url 指向 Oikos 世界进程, 或用 --demo 离线演示")
    client = OikosClient(args.url, args.mind)
    if args.body:                       # 指定身体时, 让场景直接用它
        client._forced = args.body      # noqa: 仅演示
    try:
        run_scenario(client)
    except WorldError as e:
        print(f"\n[致命] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




