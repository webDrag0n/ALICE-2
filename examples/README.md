# Oikos 示例 · 一套可运行的世界三件套 + 连接客户端

这些文件把 [world.md](../world.md) 和 [embody.md](../embody.md) 的规格落成**可读、可运行、已校验**的具体例子。它们是说明性参考实现的素材，不是完整的 Oikos 守护进程（世界进程本身的规格见 world.md）。

## 文件清单

| 文件 | 是什么 | 对应文档 |
|---|---|---|
| [object_types.toml](object_types.toml) | **物体类型目录（编号模板）**：16 个带 `type_id` 的类型（家具/家电/固定设施/设备/可携带物），加新物体只往这里追加 | world.md Part IV / VII / W11 |
| [map.toml](map.toml) | 12×9 公寓地图：layout 字符画（地形+挡路物）+ legend（字母→type_id）+ 实例表（覆写/便携物）+ 5 区域 + 4 门 + 声学参数 | world.md Part IV / X |
| [world.toml](world.toml) | 世界配置：时钟、生理代谢系数、行为稳定性钩子、设备（电脑/MC、手机/Telegram）、协议服务、存储 | world.md Part III / V / VII / X |
| [bodies.toml](bodies.toml) | 世界里住着哪些身体（Alice、客人 Hermes），与"谁来认领"解耦 | world.md Part IV / VIII |
| [embody_client.py](embody_client.py) | 心智侧参考客户端：把 embody.md 的五步流程落成代码，含离线 `--demo` | embody.md / world.md Part VIII |
| [connect.sh](connect.sh) | 纯 curl 走一遍同样的五步流程 | embody.md |

## 加一种新物体（内核零改动）

以微波炉为例（`object_types.toml` 里已是 `2004`）：

1. **登记类型** → 在 `object_types.toml` 追加一段 `[[type]]`，编号取对应号段下一空位，声明它的 `affordances`（带来的能力）。
2. **（仅当带新能力时）补能力** → 在 `skills/` 加一个 `EmbodiedCapability`；复用已有能力则跳过。
3. **摆实例** → 在 `map.toml` 追加 `[[instance]]`（或在 layout legend 里给个字母）。

号段：`1000`家具 `2000`家电 `3000`固定设施 `4000`设备 `5000`可携带物 `6000`生物 `9000+`扩展。编号 append-only、退役只标记不复用。

## 快速开始

不需要世界进程，先离线看懂客户端流程：

```bash
python3 examples/embody_client.py --demo
```

它会打印 `list_bodies → attach → sense → list_skills → act → detach` 的每一步，并演示"走到客厅、对屋里的人说一句话"。

连真实 Oikos 世界进程（按 world.toml 在 7000 端口起好后）：

```bash
python3 examples/embody_client.py --url http://localhost:7000 --mind hermes --body guest
# 或用纯 curl:
bash examples/connect.sh guest
```

## 地图已校验

`map.toml` 的**网格地形层**满足 world.md 的硬约束，可用下面这段自检（已通过：12 件挡路物锚点旁都有可走空地、48 个可走格连续连通、layout 字母都映射到目录里存在的 `type_id`）。注：网格仍是地形层，身体在其上**连续移动**；这里用格级邻接近似检查"锚点 `reach` 半径内有空地"与"全屋连通"。

```bash
python3 - <<'PY'
layout=["############","#B.K#...#HT#","#...+...+..#","#D..#...#.W#",
        "#...#..#####","#.......#F.#","#S...N..+..#","#V......#CO#","#####+######"]
H,W=len(layout),len(layout[0]); walk=lambda x,y:0<=x<W and 0<=y<H and layout[y][x] in ".+"
objs=[(x,y) for y in range(H) for x in range(W) if layout[y][x] not in "#.+"]
bad=[(x,y) for x,y in objs if not any(walk(x+dx,y+dy) for dx,dy in[(1,0),(-1,0),(0,1),(0,-1)])]
s=next((x,y) for y in range(H) for x in range(W) if walk(x,y)); seen={s}; st=[s]
while st:
    x,y=st.pop()
    for dx,dy in[(1,0),(-1,0),(0,1),(0,-1)]:
        n=(x+dx,y+dy)
        if walk(*n) and n not in seen: seen.add(n); st.append(n)
tot=sum(walk(x,y) for y in range(H) for x in range(W))
print("挡路物锚点旁无空地:", bad or "无", "| 可走格连通:", len(seen)==tot)
PY
```

（便携物如手机不进 layout，落在地面格、不挡路，所以这里不计入挡路物。）

## 注意

- 这些是**心智侧 / 配置侧**素材。真正的世界进程（时钟推进、生理代谢、连续移动/碰撞、视锥感知、声学传播、设备桥）按 world.md 实现，不在此目录。
- `embody_client.py` 的 `FakeWorld` 是个**极简桩**，只为把连接流程演出来，不模拟时间/生理/连续移动/视锥/编号目录。别拿它当世界规格——那是 world.md 的事。
- 密钥（Telegram token 等）一律用 `ENV:VAR_NAME` 间接引用，示例里不写明文。
