# Oikos · Embodied World & Body Engine

## Engineering Design Document · v0.1

> 本文档是 [ADOS](soul.md)（认知内核 = 心智）与 [Mnemos](memory.md)（通用记忆引擎）的第三个姊妹规格。它把原本散落在 ADOS 内部的**时间、空间、身体生理、具身能力（skills）、世界事件**抽出为一个**独立项目、独立进程**：一个与具体心智设计**无关**的具身世界引擎。核心命题与 Mnemos 同源——"**解耦 = 心智只体验它所栖居的世界，而不拥有它**"。
>
> 一句话定位：**Oikos 是智能体的"身体 + 世界"，ADOS 是"心智"，Mnemos 是"记忆"。** 三者构成一个真实智能体的完整隐喻：*一个心智，住在一个身体里，身处一个世界中，并拥有记忆*。一个心智无需自带时钟、无需自带膀胱、无需自带户型图——它**感知**一具身体处在一个世界里，并**通过这具身体行动**。一个世界里**可以同时住着多具身体**（Alice、OpenClaw、Hermes……），心智是主动方：自己决定连哪个世界、认领哪具身体。
>
> 已定的关键取舍（v0.1）：① 世界**自跑一条权威时钟**（默认与现实同步、可动态加速/暂停/跳跃），身体生理、事件、昼夜全部由这条时钟驱动，**与 ADOS 的认知 tick 物理隔离**；② 身体是一个**只能由 Oikos 改写**的状态向量（饥、渴、尿意、清洁、精力、位置、姿态、手持物），心智永远只能"行动 + 观察后果"，**不得直接写身体**；③ 世界是**连续空间 over 网格地形**——一套单层小公寓，网格只描述墙/房间/光照，身体在连续平面上**平滑移动**（浮点坐标＋连续朝向、可停在任意点）、受墙体/家具连续碰撞阻挡；④ **感知是有视角的、局部的、分级的**——身体有朝向决定的视野锥，正前方看得清、余光模糊、背后与隔墙看不见，远/暗处看不清；`sense` 给的是以身体为原点、带清晰度分级的自我中心观察，绝不全知；⑤ **所有 skills 由世界提供**（移动、吃喝、如厕、洗澡、睡觉、用电脑、用手机……），能力是否可用由**身体所在位置 + 身体状态**门控；⑥ 具身约束是硬规则：**玩 MC 必须在电脑前且坐下，离开电脑立刻断开**；发 Telegram 是**通过身体携带的手机**完成，心智清楚认知到"我正拿着手机在发消息"，而非调一个抽象 API；⑦ **一世界多身体**：身体与心智是"认领"关系，**任何能读协议的智能体（不必是 Alice 这样的持续自主体，也可以是 OpenClaw / Hermes 这类一次性 agent）都能读一份自包含指南 [embody.md](embody.md) 学会连接并认领身体**；⑧ **人物之间靠声音交流**：说话是在世界中以自身为源点制造声音，按距离与阻挡衰减传播，旁人能否听见取决于其身体所在位置；⑨ 进程间通信**从最简协议起步**（localhost HTTP + msgpack），与 ADOS / Mnemos 同款；⑩ **禁止 fallback 与静默降级**，任何错误以 `WorldError` + 完整上下文 fail-loud，与两个姊妹工程哲学一致。
>
> 阅读顺序：Part I 理念与原则 → Part II 进程架构 → Part III 世界时钟 → Part IV 连续空间、移动与感知 → Part V 身体与生理 → Part VI 事件、闹钟与声音 → Part VII Skills 即具身能力（落地核心）→ Part VIII 世界协议与身体认领 → Part IX 与 Soul / Mnemos 接合 → Part X 世界格式 → Part XI 路线图 → Part XII–XIV 选型/约束/风险。配套：[embody.md](embody.md)（任意智能体可读的"如何连接世界中的身体"指南）。

---

# Part I · 理念与第一性原则

### Vision

Oikos 不是一个游戏引擎，也不是一个机器人仿真器，而是一个**可被任意心智栖居的、自跑的具身世界**。它独立运行、自我推进（时间流逝、身体代谢、事件发生），对外只暴露一组稳定的"感知 / 行动 / 授时"接口。它的设计目标不是"渲染一个场景"，而是**为一个本无身体的心智提供一具会饿、会渴、会累、会被困在墙后的身体，和一个有真实时间、真实空间、真实因果的栖居地**。

为什么要把世界从心智里拆出来？因为 ADOS 原稿里，"饥饿值"是 `NeedState.survival`、"电量"是 `ResourceState.energy`、Minecraft 的生命/饥饿被直接喂进 Need、`send_message` 是一个抽象 action——**生理、空间、设备这些"属于身体和世界的事实"，被混进了"属于心智的状态"**。这正是 Mnemos 把记忆拆出去时面对的同一个错误。拆开后：

- 心智（ADOS）不再"拥有"饥饿，而是**观察到身体饿了**，并自主决定要不要去吃——"饿了去找吃的"依然是心智的决策，但饥饿信号源自世界，不再是认知内核里的一个动力学方程。
- 心智不再"拥有"一个 `send_message` 抽象动作，而是**观察到手边有手机**，决定拿起它、打开 Telegram、打字、发送——发消息变成一串具身动作，心智因此真切"知道自己在用一个手机"。

**"具身"的精确含义：能力受身体约束。** 心智想做的任何事，都必须有一具处在正确位置、处在正确状态的身体来承载。想玩 MC？身体得先走到电脑桌前、坐下、登录；站起来离开，世界立刻断开连接。想发消息？身体得先拿起手机。这不是为了拟真而拟真，而是**让"行为来源于内部状态"这条 ADOS 第一性原则，落到"行为还必须被身体和世界允许"这层物理现实上**——心智不能瞬移、不能分身、不能在洗澡时同时打字。

### First Principles

每条原则后附**工程含义（Engineering Implication）**，即对代码结构的硬性约束。这套原则与 ADOS 的解耦/fail-loud/可溯源精神、与 Mnemos 的机制/策略分离一脉相承，但服务于"独立具身世界"这一目标。

**W1 · 心身分离（Mind/Body Separation）。** 世界拥有身体与环境的**唯一真值**（时间、空间、生理、设备、事件）；心智只能感知与行动，**永不直接持有或改写身体状态**。
*工程含义：* 心智侧（ADOS）的代码里**不允许**出现身体/世界状态的本地真值（没有本地"饥饿变量"、没有本地时钟、没有本地坐标）。这些只能来自 Oikos 的 observation。可被 lint/测试强制检查（与 ADOS 的 P2 同构、可叠加校验）。

**W2 · 世界自跑（Autonomous World）。** 世界**不等待心智**。即使心智在思考、在睡、甚至进程重启，时间照样流逝、身体照样代谢、闹钟照样响、门铃照样按。世界是主动的，不是心智行动时才被查询的被动数据库。
*工程含义：* Oikos 有一条永不停止的 **world tick**（独立于 ADOS 的认知 tick）。身体衰减、事件触发、设备状态全在 world tick 里推进。心智断开期间世界状态继续演化，重连时心智观察到的是"过了一段时间、身体更饿了"，而非冻结的旧世界。

**W3 · 连续空间，网格是地形骨架（Embodied in Continuous Space over a Grid）。** 身体在**连续平面**上占据浮点位置与连续朝向；移动是**沿路径平滑滑动**（有速度、有加速、可中途停在任意点），不是逐格跳。网格**只作静态地形层**（哪里是墙、哪块属于哪个房间、光照如何），不是身体运动的量子化单位。
*工程含义：* 世界坐标是 `pos:(float,float)`（单位=米，1 格≈1 米），朝向是 `heading:float`（弧度）。地形用 `GridMap` 描述（墙/房间/光照按格），但身体运动与碰撞在连续域计算：`move` 沿平滑路径推进，每 world-tick 前进 `speed·Δt`，圆形身体与墙体线段做连续碰撞。**能感知什么、能够到什么，是身体连续位置＋朝向的函数**（见 W12），而非"在哪个格"。

**W4 · 一切能力皆具身（All Skills are Embodied & World-Provided）。** **所有 skills 由世界提供**，没有"凭空"的能力。每个能力都附带**身体前置条件**（在哪、什么姿态、手持什么、身体状态是否允许）；前置不满足则该能力**不在当前可用目录里**，规划层根本看不到它。
*工程含义：* Oikos 维护 **Capability Registry**，`action_catalog()` 返回的不是"世界所有能力"，而是"**以身体当前情境过滤后、此刻真正可执行的能力**"。这与 ADOS Part VII 的 Capability/Skill 体系对接：ADOS 不再自带 Domain Pack 的能力，而是**把"能做什么"完全交给 Oikos 按身体情境吐出**。

**W5 · 设备即世界中的物（Devices are Objects-in-World）。** 外部世界（Minecraft、Telegram、未来的浏览器等）不是心智直连的抽象通道，而是**世界里的物理设备**：电脑在桌上、手机在身上。访问外部 = 身体操作设备；身体离开/放下设备 = 连接中断。
*工程含义：* "玩 MC"是 `computer` 设备在 `desk` 格、身体 `seated@desk` 时才开放的能力，身体一旦 `move_to` 离开 desk，Oikos **立即**发 `DeviceDisconnected` 并断开 MC 会话；"发 Telegram"是 `phone` 作为**手持物**时才开放的能力。心智在 observation 里读到的是"你正坐在电脑前，屏幕上是 Minecraft""你手里拿着手机，屏幕显示 Telegram 对话"——**具身框架由世界注入观察，心智因此真切认知自己在用一台设备**。

**W6 · 时间可被掌控但守恒因果（Time is Controllable, Causally Coherent）。** 世界时间默认与现实同步，但可被**动态加速、减速、暂停、跳跃**（调试、加速实验、"睡一觉跳到早上"）。无论怎么调，时间永远**单调前进**，所有时间派生过程（生理、闹钟、昼夜）都跟随同一条时钟，不产生因果矛盾。
*工程含义：* 时钟是 `WorldClock{epoch_real, scale, paused, offset}`，对外只暴露 `world_now()` 与受控的 `set_scale / pause / resume / jump_forward`。**绝不允许时间倒流**（jump 只能向前）；调速立即广播 `TimeScaleChanged`，让心智能感知"世界变快了"。

**W7 · 全程可溯源、显式失败（Provenance & Fail-Loud）。** 每个身体状态变更、每次行动结果、每个事件都带时间戳、来源、因果链；非法行动（前置不满足、撞墙、设备未连）一律 fail-loud，**绝不静默吞掉或伪造成功**。
*工程含义：* 复用 ADOS 的 `Stamped` 基类；非法行动抛带完整上下文的 `WorldError`（哪个能力、缺哪个前置、身体当时在哪），**绝不让心智以为动作成功了**——否则心智的世界模型会与真实世界悄悄分叉。与 ADOS / Mnemos 的 no-fallback 哲学一致。

**W8 · 进程隔离 + 协议通信（Process Isolation）。** 独立进程，靠一套稳定的世界协议通信；一个 Oikos 进程**承载一个世界，世界中可同时存在多具身体**，任意心智作为客户端连接并**认领**其中一具身体。
*工程含义：* Oikos 不依赖任何特定心智进程；协议接口稳定，传输实现（HTTP/socket/gRPC）可替换而调用方无感。与 Mnemos M7 同构。身体与连接它的心智解耦：身体是世界里的实体，心智是外部连上来认领它的客户端（见 W9）。

**W9 · 一世界多身体、身心是认领关系（Multi-Tenant World, Bodies are Claimed）。** 世界里可以住着 Alice、OpenClaw、Hermes……多具身体并存、各自被一个心智认领驱动；身体也可空置（无心智连接时仍是世界中的实体，照样占格、照样会饿、照样能被别人看到/听到）。**心智是主动方**：它清楚知道自己要连哪个世界、认领哪具身体，主动发起连接，而非被动被塞一具身体。
*工程含义：* 身体有稳定 `body_id`；`attach(body_id)` 认领、`detach()` 释放。一具身体同一时刻至多被一个心智认领（认领冲突 fail-loud）。心智无需是 ADOS 这类持续自主体——**任何能读协议的智能体（含一次性 agent）都能连**，靠的是一份自包含的连接指南 [embody.md](embody.md)（W4 意义上的"如何连接身体"这一元 skill）。

**W10 · 声音是世界里的物理量（Sound Propagates in the World）。** 任何人/物发声，都是在世界中以**自身位置为源点**制造一个声音；其他身体能否听见、听得多清，由**距离衰减 + 阻挡物衰减**决定。说话不是点对点直连，而是**对空气广播**——近处听得清、隔墙变闷、太远听不到。
*工程含义：* `speak` 是一个 capability，产生一个 `Sound` 事件（源点/响度/内容）；World 按声学模型计算每具在场身体的可闻性，只把**可闻的声音**并入各自的 `sense`。心智听到的永远是"从我这具身体的位置、此刻能听到的声音"，可能漏听、可能听不清——与视野的局部性（W3）同构。

**W11 · 物体是可无限扩展的编号目录（Objects are an Extensible Numbered Catalog）。** 世界要能持续加入新物体而不动内核。物体分**类型（模板，带全局唯一数字编号 `type_id`，只增不复用）**与**实例（摆放，引用编号）**两层；能力挂在类型上（affordance），加一种物体 = 登记一个新编号 + 摆实例。
*工程含义：* 内核**不内置任何具体物体**，只认 `ObjectType`/`ObjectInstance` 两个通用结构；具体物体（床/冰箱/微波炉/猫……）全来自 `object_types.toml` 目录 + `map.toml` 实例。编号 append-only、退役只标记不复用，旧存档/日志恒可解析。与 ADOS"领域能力来自 Pack 而非内核"、Mnemos"维度来自注册而非硬编码"同构。

**W12 · 感知是有视角的、局部的、分级的（Perception is Viewpoint-based, Local, Graded）。** 身体不是全知的摄像头。它有一个**朝向决定的视野锥**：正前方看得清、余光模糊、背后看不见；远处、暗处、被墙/大件物挡住的都看不清或看不到。感知与声音（W10）同构——都是"从我这具身体此刻的位置与朝向能获取的、带清晰度的局部信息"。
*工程含义：* `sense` 不返回全图，而是以身体为原点做**视锥 + 遮挡 + 光照 + 距离**的可见性计算，对每个被感知对象给一个 `clarity∈[0,1]`；低于阈值的看不清（只给粗略轮廓）或看不到（不并入观察）。心智可用 `turn`/`look_at` 主动改变朝向来"看向"某处——**看哪里是一个要花代价的动作，不是免费全知**。这让"没注意到""看错了""得回头看一眼"成为世界的真实属性（见 Part IV 感知与视野）。


---

# Part II · 进程与架构

### 定位

Oikos 是一个**独立守护进程（daemon）**。心智（ADOS）作为**客户端**通过世界协议连接。它和 Mnemos 并列为 ADOS 的两个外部基座：

```
        ┌──────────── ADOS (Soul / 心智) ────────────┐
        │  Observation · Need · Emotion · Goal ·       │
        │  Planning · Thinking · Learning · Identity   │
        └───────┬───────────────────────────┬─────────┘
                │ world protocol            │ memory protocol
                │ (sense / act / time)      │ (remember / recall ...)
                ▼                           ▼
        ┌───────────────┐           ┌───────────────┐
        │  Oikos (World) │           │ Mnemos (Memory)│
        │  身体 + 世界    │           │  联想记忆引擎   │
        └───────────────┘           └───────────────┘
```

**三者的真值边界（最重要的一张表）：**

| 真值归属 | 拥有者 | 例子 |
|---|---|---|
| 时间、空间、身体生理、设备、世界事件 | **Oikos** | 现在几点、身体在哪、有多饿、电脑开没开、门铃响了 |
| 需求、情绪、目标、人格、信念、决策 | **ADOS** | 饿了"想不想"去吃、对用户的情感、今天的计划 |
| 经历、语义、技能经验、反思 | **Mnemos** | 记得昨天做了什么、知道怎么煮面、对自己的认识 |

注意 ADOS 原稿里 `ResourceState.energy`（电量/进程健康）与 `NeedState.survival`（生存匮乏）**被混为一谈**。拆开后：**身体的精力/饥饿在 Oikos**（生理事实），**"要不要为此行动"的需求张力在 ADOS**（心理动机），**进程算力预算仍在 ADOS**（那是心智自己的资源，不是身体的）。

### 进程内部架构

```
┌──────────────────────────── Oikos Daemon ────────────────────────────┐
│                                                                       │
│  Protocol Server (localhost HTTP + msgpack, 最简起步)                  │
│    └─ sense / act / list_skills / set_timer / time(get/set) / introspect│
│                                                                       │
│  World Clock (权威时钟, 永不停)                                         │
│    └─ world_now / scale / pause / jump_forward → 广播 TimeScaleChanged │
│                                                                       │
│  World Tick Loop (自跑, 独立于心智)                                     │
│    ├─ Body Metabolism   按 world-time 推进饥/渴/尿/净/精力              │
│    ├─ Event Scheduler   闹钟/定时/门铃/昼夜 到点触发                     │
│    ├─ Device Manager    电脑/手机/外部连接的连通性与门控                 │
│    └─ Action Executor   执行心智请求的具身动作(寻路/状态变更/耗时)       │
│                                                                       │
│  World State (唯一真值, 周期快照)                                       │
│    ├─ Grid Map          单层公寓网格 + 家具/房间/工位                   │
│    ├─ Body              pos/facing/posture/held/生理向量                │
│    ├─ Objects           可交互物(冰箱/床/马桶/淋浴/电脑/手机...)        │
│    └─ Timers/Events     活跃闹钟与定时事件                              │
│                                                                       │
│  External Bridges (设备背后的真实外部世界)                              │
│    ├─ Minecraft Bridge  (Mineflayer 等; 仅 seated@desk 时活跃)         │
│    └─ Phone/Telegram Bridge (手机持有时活跃; Bot API)                   │
│                                                                       │
│  Infrastructure                                                       │
│    ├─ Structured Logging + WorldError 通道 (fail-loud)                 │
│    └─ Event Log (append-only, 可回放重建世界)                          │
└───────────────────────────────────────────────────────────────────────┘
```

### 两条时间线（与 Mnemos 同构的前/后台划分）

- **前台（同步，请求驱动）：** `sense` / `act` / `list_skills` / `time` / `introspect`。心智来问"我看到什么、我能做什么"或来下"我要做 X"。`sense` 是纯状态读取，低延迟；`act` 校验前置→执行→返回结果，**绝不阻塞在 LLM 上**（Oikos 本身不调 LLM，它是物理世界，不思考）。
- **后台（异步，自治）：** World Tick Loop 持续推进时间、代谢、事件。它**不需要心智在场**——这是 W2 的落地。心智断开时世界继续跑；心智重连时通过 `sense` 看到一个"已经往前走了一段"的世界。

**关键工程决策：** Oikos **完全不依赖 LLM**。它是身体和世界——会饿、会响、会挡路，但不会思考。所有"想法"都在 ADOS。这保证了世界的演化是确定的、可回放的、可单测的（给定初始世界 + world tick 序列 + 心智动作序列，世界状态完全确定）。这与 ADOS 的 Reflex 不依赖 LLM、Mnemos 前台 recall 不依赖 LLM 是同一种"基座不被 LLM 拖垮"的硬保证。


---

# Part III · 世界时钟（World Clock）

> 时间是世界的第一根支柱。所有生理代谢、闹钟、昼夜、设备超时都挂在这条唯一时钟上。它默认贴着现实，但可被掌控。

### 模型

```python
class WorldClock(Stamped):
    epoch_real: float        # 锚定：某个现实 wall-clock 时刻
    epoch_world: float       # 该时刻对应的"世界时刻"
    scale: float             # 时间流速：1.0=与现实同步, 60=1现实秒过1世界分钟, 0=暂停
    paused: bool
    timezone: str            # 世界所在时区, 决定昼夜
```

世界时刻的计算（单调、可加速、可暂停）：

```
world_now() = epoch_world + (real_now() - epoch_real) * (0 if paused else scale)
```

每次调速/暂停/跳跃，都**重新锚定** `epoch_real / epoch_world`（保证连续、不跳变、不倒流），并广播 `TimeScaleChanged` / `TimeJumped`。

### 对外能力（受控、只能向前）

| 操作 | 语义 | 典型用途 |
|---|---|---|
| `time.get()` | 返回 `world_now` + 当地日期/时刻/昼夜相位 | 心智"看表"——但注意心智通常**不直接读时钟**，而是看身体携带的手机/墙上的钟（见设备） |
| `time.set_scale(s)` | 改流速（s≥0） | 调试加速；"无聊时让时间快进" |
| `time.pause()` / `resume()` | 暂停/恢复世界 | 调试断点；不希望身体在心智离线时继续饿 |
| `time.jump_forward(Δ)` | **向前**跳 Δ 世界秒，期间生理/事件**批量结算** | "睡一觉到早上"——跳跃时把这段时间内本应代谢的量、本应触发的闹钟一次性补算 |

**`jump_forward` 的因果守恒（关键）：** 跳跃不是把时钟一拨了事，而是**重放这段时间**：身体该饿多少照饿、期间到点的闹钟照样产生事件（只是被压缩成一批 `EventsDuringJump` 交给心智），昼夜照常推进。否则心智会观察到"凭空跳了 8 小时但身体一点没变"的因果断裂。

**默认与现实同步（scale=1, 不暂停）：** 这是 v0.1 缺省。智能体活在与你同一条时间线上——你晚上来找它，它的身体也到了"该犯困"的世界时刻。这让"昼夜节律""到饭点了""深夜了该睡"成为通用动力学的自然产物，而非脚本。

### 昼夜与节律

时钟派生出 `day_phase`（dawn/day/dusk/night）与光照水平，喂给世界（影响房间明暗）和身体（影响困倦的昼夜项，见 Part V）。这让"白天有精神、深夜困"不靠 if-else，而是生理方程里一个跟随时钟的余弦项。


---

# Part IV · 连续空间、移动与感知

> 空间是世界的第二根支柱。一套**单层小公寓**。身体在其中**连续移动**、真实被墙挡住、有朝向、有视野。**坐标体系分两层：连续世界坐标（身体运动/碰撞/感知在此计算）＋ 离散网格地形层（描述墙、房间、光照、物体锚点）。** 网格是"地图怎么画的"，连续坐标是"身体怎么动的"。

### 坐标体系：连续世界 over 网格地形

- **连续世界坐标 `(x, y): float`**（单位=米，约定 **1 格 = 1 米**）。身体位置、朝向、路径、碰撞、视野、声源全在连续域。格 `(cx, cy)` 与世界点的关系：格中心 = `(cx+0.5, cy+0.5)`，`world_to_cell(p) = (floor(p.x), floor(p.y))`。
- **网格地形层 `GridMap`** 只描述**静态地形**：每格是否属于实心墙、属于哪个房间、光照多少。它不再是身体的运动单位，而是碰撞几何与空间归属的来源。

```python
class Cell(BaseModel):
    cx: int; cy: int
    solid: bool                     # 是否实心(墙/大件挡路物占据的格) → 连续碰撞的障碍
    room: str                       # 该格所属区域: bedroom|bathroom|kitchen|living|hall
    light: float                    # 由昼夜 + 室内灯具决定 [0,1] (影响视野距离)
    blocks_sight: bool = None       # 是否挡视线(默认=solid; 玻璃墙可 solid 但不挡视线)

class GridMap(Stamped):
    w: int; h: int                  # 网格尺寸(米)
    cells: list[list[Cell]]
    walls: list[Segment]            # ★由 solid 格边界抽出的墙线段集合, 供连续碰撞/射线用
    rooms: dict[str, Polygon]       # 区域 = 连续多边形(由格集合合并而来), 用于"我在哪个房间"
    object_types: dict[int, ObjectType]
    instances: dict[str, ObjectInstance]
```

> **地图设计铁律（连续化后仍成立）：** 可交互物仍以**单格为锚点**摆放（`anchor_cell`），但交互不再要求"站在相邻格"，而是"身体中心进入该物的**交互半径**"（连续，见硬规则 2）。区域是连续多边形（由格集合融合），用于判定"身体此刻在哪个房间"与视野的墙体遮挡。网格作者照旧按格画图（Part X 的 `map.toml` 不变），加载器把 solid 格边界抽成墙线段 `walls` 供连续计算。

### 户型（v0.1 默认地图，12×9 单层公寓）

```
    0  1  2  3  4  5  6  7  8  9 10 11
 0  ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██
 1  ██ B  ·  K  ██ ·  ·  ·  ██ H  T  ██
 2  ██ ·  ·  ·  ▢  ·  ·  ·  ▢  ·  ·  ██
 3  ██ D  ·  ·  ██ ·  ·  ·  ██ ·  W  ██
 4  ██ ·  ·  ·  ██ ·  ·  ██ ██ ██ ██ ██
 5  ██ ·  ·  ·  ·  ·  ·  ·  ██ F  P  ██
 6  ██ S  ·  ·  ·  N  ·  ·  ▢  ·  ·  ██
 7  ██ V  ·  ·  ·  ·  ·  ·  ██ C  O  ██
 8  ██ ██ ██ ██ ██ ▢  ██ ██ ██ ██ ██ ██
```

图例（每个字母 = 一件物，恰占一格）：`B`床 `K`书架 `D`电脑桌（卧室区）｜`H`淋浴 `T`马桶 `W`洗手台（卫生间区）｜`F`冰箱 `O`灶台 `C`料理台 `P`手机充电处（厨房区）｜`S`沙发 `V`电视 `N`餐桌（客厅区）。`██`墙 `·`可站立地面 `▢`门/区域出入口（门格本身可通行）。

区域（多格集合）：**卧室** 左上 `x1–3,y1–4`｜**走廊/hall** 中上 `x5–7,y1–3`｜**卫生间** 右上 `x9–10,y1–3`（仅经门 `(8,2)` 与走廊相通）｜**客厅** 中下 `x1–7,y5–7`｜**厨房** 右下 `x9–10,y5–7`（仅经门 `(8,6)` 与客厅相通）。入户门在底边 `(5,8)`。

> **此布局已校验：每件物都有可接近的空地、全屋连续可走空间连通（连续寻路必有解）。** 真实坐标/物表/区域表落在 `map.toml`（Part X），并附完整可运行示例 [examples/map.toml](examples/map.toml)。要点：物按单格锚点摆放、身体走进其 `reach` 半径即可交互；区域是连续多边形、由墙与门连通；"工位"是某件带 `station` 语义的物（如 `desk` = 电脑 `D(1,3)`，走近到它 `reach` 内即"在工位"）。

### 可交互物：类型 / 实例两层模型（为持续扩展而设计）★

> 世界要能**不断加入新物体**（今天加微波炉，明天加猫、加打印机），却不该每加一件就改内核或重写地图。所以物体拆成两层——与"心智可注册维度"（Mnemos）、"Capability 由 Pack 提供"（ADOS）一脉相承的**机制/数据分离**：
>
> - **ObjectType（物体类型 = 模板，进编号目录）：** 定义"这类物体是什么、能开放哪些能力、长什么样"。每个类型有一个**全局唯一数字编号 `type_id`**，**只增不改、退役只标记不复用**（append-only catalog）。加一种新物体 = 往目录里登记一个新编号，**内核零改动**。
> - **ObjectInstance（物体实例 = 摆放，进地图）：** "这具体的一台冰箱在 `(9,5)`、里面有 3 份食物"。实例只引用 `type_id` + 落点 + 实例级状态覆写，极轻量。同一类型可摆 N 个实例（两台手机、三把椅子）。

```python
class ObjectType(Stamped):           # 模板, 一类物体登记一次, 进编号目录
    type_id: int                     # ★全局唯一数字编号(只增不复用), 见编号方案
    name: str                        # 人读名("refrigerator"); 可有别名供文档引用
    kind: str                        # 大类(furniture/appliance/device/fixture/item/...)
    blocks_walk: bool = True         # 是否挡路(占格实心, 连续碰撞的障碍). 便携小物常 False
    blocks_sight: bool = False       # 是否挡视线(高大家具遮挡其后的物, 见感知与视野)
    portable: bool = False           # 能否被拿起携带(手机=True, 冰箱=False)
    footprint: float = 0.4           # 连续占地半径(米); 决定碰撞与视觉体积
    reach: float = 0.9               # ★交互半径(米): 身体中心进入此半径即可交互(连续)
    interact_posture: list[str] | None = None   # 交互要求的姿态(如马桶需就坐)
    affordances: list[Affordance]    # ★此类型开放的能力 + 各自具身前置(见 Part VII)
    state_schema: dict               # 实例 state 的字段与默认值(冰箱:{food:int,...})
    visual_size: float = 1.0         # 视觉显著度(大件更远就能看清); 影响 clarity
    tags: list[str] = []             # 检索/分类标签("kitchen","seating",...)

class ObjectInstance(Stamped):       # 摆放, 进地图; 同类型可多个
    instance_id: str                 # 实例标识("fridge_kitchen", "phone_alice")
    type_id: int                     # 引用 ObjectType
    anchor_cell: tuple[int,int]      # 锚点格(作者按格摆放); 世界锚点 = 格中心(连续)
    facing: float | None = None      # 物朝向(可选, 影响交互侧/视觉)
    state: dict = {}                 # 仅覆写与类型默认不同的字段
```

> **单格锚点、连续交互**：物体仍以单格为**摆放锚点**（作者友好），但"能不能用它"是连续判定——身体中心到锚点的距离 ≤ `type.reach` 即可（不再要求"站在某个相邻格"）。`blocks_walk=True` 的物把其锚点格标 `solid`（连续碰撞障碍）；便携小物 `blocks_walk=False` 不占实心格。能力（affordance）仍挂在类型上（W4/W11）。

### 物体编号方案（append-only，按大类分段）

`type_id` 按大类分配号段，留足空位，新物体往对应段里**顺序追加**即可，永不与旧号冲突：

| 号段 | 大类 | 示例（`type_id` → name） |
|---|---|---|
| `0–999` | 系统保留 | `0` = void/空 |
| `1000–1999` | 家具 furniture | `1001` bed · `1002` sofa · `1003` bookshelf · `1004` dining_table · `1005` chair |
| `2000–2999` | 家电 appliance | `2001` fridge · `2002` stove · `2003` tv · `2004` microwave(新增示例) |
| `3000–3999` | 固定设施 fixture | `3001` toilet · `3002` shower · `3003` sink · `3004` counter |
| `4000–4999` | 设备 device（接外部桥） | `4001` computer(MC) · `4002` phone(Telegram) |
| `5000–5999` | 可携带物 item | `5001` cup · `5002` book · `5003` food_item |
| `6000–6999` | 生物/宠物（将来） | 预留 |
| `9000+` | 用户/第三方扩展 | 自定义类型登记区 |

**规则：** 编号**只增不复用**；某类型退役 → 标 `deprecated=true` 保留号位（旧存档/日志仍可解析），不删不改。这与 ADOS/Mnemos 的"schema 演进可溯源、不静默破坏旧数据"一致。

### 加一种新物体的三步（内核零改动）

以"加一台微波炉"为例，全程只动数据/能力，不动内核：

1. **登记类型。** 在 `object_types.toml` 追加一条 `[[type]]`：`type_id = 2004`、`name="microwave"`、`kind="appliance"`、`affordances=["heat_food"]`、`state_schema={ contents="", running=false }`。编号顺序取家电段下一个空位。
2. **（仅当带新能力时）补能力实现。** 若 `heat_food` 是前所未有的动作，在 `skills/` 加一个 `EmbodiedCapability`（带具身前置 + effects）。若复用已有能力（如就是 `cook` 的变体），这步可省。
3. **摆实例。** 在 `map.toml` 追加一条 `[[instance]]`：`instance_id="microwave_kitchen"`、`type_id=2004`、`cell=[...]`。下一 tick，站到它跟前的身体 `list_skills()` 里就会出现 `heat_food`。

> 三步里没有一步需要改世界内核、改协议、或改任何已存在的物体——**这就是类型/实例 + 编号目录要兑现的扩展性**。同理可加椅子（1005，复用 `sit_down`，零新代码）、加宠物猫（6001，新 `pet` 能力）、加打印机（9001 用户扩展段）。

### 空间的三个硬规则（连续化）

1. **移动 = 连续位移，撞墙即停。** `move_to(target)` 先用格级 A* 求粗路径（把 solid 格当障碍），再**平滑成连续路径**（拐角圆化、走直线捷径），身体按 `speed` 逐 tick 前进，圆形身体（半径 `footprint`）与墙线段 `walls` 做连续碰撞——贴墙滑动、绝不穿墙。移动**耗 world-time 与精力**（按实际走过的连续距离）。目标不可达 → `WorldError`；移动可在**任意连续点**被高优先级事件打断并停住（不必停在格心）。
2. **交互 = 进入交互半径。** 针对某物的能力，前置是"身体中心到该物锚点距离 ≤ `type.reach`（连续）＋ 姿态满足"。走近到够得着即可，不再要求"站在某个格"。够不着 → 能力不在当前目录里（W4），或调用报"太远，先靠近"。
3. **感知 = 有视角的局部（见下节详解）。** `sense` 不返回全图，而是以身体位置＋朝向做**视锥＋遮挡＋光照＋距离**计算，每个对象带 `clarity`。正前方清楚、余光模糊、背后与隔墙看不见。这与声音（W10）、与旧的"局部视野"一脉相承，但升级为连续、有朝向、分级（W12）。

### 身体的空间属性

```python
class Body(Stamped):                 # 世界中的一具身体(实体), 由某心智认领驱动
    body_id: str                     # 稳定标识, 心智用它 attach(认领)
    display_name: str                # 世界中可见的名字(Alice / Hermes / ...)
    claimed_by: str | None           # 当前认领它的 mind_id; None=空置(仍是世界实体)
    embodiment: Embodiment           # 空间分量(下)
    physiology: Physiology           # 生理分量(Part V)

class Embodiment(Stamped):           # 身体的"空间分量"(生理分量见 Part V)
    pos: tuple[float,float]          # ★连续世界坐标(米)
    heading: float                   # ★连续朝向(弧度, 0=+x 逆时针); 决定视锥中心
    posture: Literal["standing","seated","lying","walking"]
    footprint: float = 0.25          # 身体碰撞半径(米)
    speed: float = 1.2               # 当前步速(米/世界秒), 可被 fatigue/posture 压低
    vision: VisionParams             # 视野参数(见"感知与视野")
    motion: MotionState | None       # 若在移动: 目标/剩余路径/进度; 否则 None(静止)
    in_room: str                     # 由 pos 落在哪个 room 多边形推出
    near_object: str | None          # 处于交互半径内、最近的可交互物(便于门控)
    posture_anchor: str | None       # 若 seated/lying, 绑定的物(desk/bed)
    held: list[str]                  # 手持物 id 列表(如 ["phone"])
```

`near_object` + `held` + `posture` 是能力门控的主输入：**够得着谁 + 拿着什么 + 什么姿态**，决定此刻能做什么（取代旧的 `at_station`——"工位"现在是"够得着某个带 station 语义的物"）。

### 多身体的连续碰撞规则

身体是连续域里的**圆**（半径 `footprint`）。碰撞规则：任意两具身体的圆不重叠——移动时把其他身体当作动态圆障碍，自动绕行/贴着让位；走廊太窄、被对方完全堵死且无替代路径 → `move_to` fail-loud（"过不去"是真实后果，不瞬移穿人）。身体让开后空间即恢复。空置身体（无心智认领）静止占位，照样是圆障碍、照样会饿、照样能被看到和听到——一具"发呆"的身体，等待被认领。

### 感知与视野：soul 如何透过 body 看 world（本节回答核心设计问题）

> **要不要视野？要。** 没有视野，body 退化成一个"能读取全屋真值的传感器"，soul 就成了全知的上帝视角——这既不真实，也让"探索""没注意到""回头看一眼""在暗处看不清"这些具身体验无从谈起，更让多身体场景失去信息不对称（每个人该看到不同的世界）。视野让**观察成为一个有代价、有朝向、会遗漏的过程**，与声音（W10）完全同构。

**① 视野参数（挂在身体上）**

```python
class VisionParams(BaseModel):
    fov: float = 2.44                # 视野锥总角(弧度, ≈140°): 人眼的水平视场
    focus_fov: float = 0.52          # 中央清晰锥(≈30°): 此锥内看得最清
    range_base: float = 8.0          # 基准视距(米, 明亮环境); 实际视距被光照缩放
    acuity: float = 1.0              # 视敏度(可被 fatigue/疾病压低)
```

**② 可见性怎么算（World 每次 `sense` 时对每个候选对象做，确定、可单测）**

对身体前方的每个对象/其他身体 `o`，World 计算一个 `clarity(o) ∈ [0,1]`：

```
设 d      = |o.pos − body.pos|                    # 连续距离
   θ      = 与 heading 的夹角                       # 偏离正前方多少
   range  = range_base · light_at(o) · acuity      # 暗处/夜里视距骤缩
1. 视锥外 (θ > fov/2) 或 太远 (d > range) → clarity = 0 (看不见, 不并入观察)
2. 视线被遮挡 → clarity = 0:
     沿 body→o 的线段做射线步进, 若穿过 solid/blocks_sight 的格或 blocks_sight 物 → 挡住
3. 否则 clarity = f(距离衰减, 角度衰减, 光照, 视觉体积):
     clarity = clamp( (1 − d/range)              # 越近越清
                    · angle_factor(θ)            # 中央清晰锥内≈1, 余光递减
                    · light_at(o)                # 暗处更糊
                    · o.type.visual_size          # 大件更远也看得清
                    · acuity , 0, 1)
```

**③ 分级呈现（与声音的 clarity 分档同构）**

- `clarity ≥ clear_threshold`：**看清**——给出对象类型、状态、朝向、在做什么（其他身体的可见动作）。
- `mid ≤ clarity < clear`：**看见但看不清**——只给粗轮廓（"东边墙角有个大件家具，看不清是什么"/"有人影，认不出是谁"）。
- `clarity < mid`：**没看见**——完全不并入观察（真实的视觉遗漏，不是 bug）。

**④ 两层信息，别混淆（关键设计）**

身体给 soul 的空间信息分两层，避免"看不见就完全不知道自己在哪"的荒谬：

- **本体感 + 空间骨架（proprioceptive / structural，永远给）：** 我在哪个房间、房间大致形状、门/出口在哪、我朝向哪、够得着什么。这是"闭着眼也知道自己站在客厅、门在背后"的具身常识，不受视锥限制（来自身体对所处空间的即时感知，非视觉细节）。
- **视觉细节（foveal，受视锥/遮挡/光照限制）：** 具体有哪些物、它们什么状态、屋里还有谁在做什么、他们的表情动作。这才是"要转头去看、可能没注意到、暗处看不清"的部分。

于是"背对冰箱时我仍知道厨房里有冰箱（结构记忆/常识）"与"我此刻没看着它所以不知道它门开没开（视觉细节缺失）"能同时成立且不矛盾——前者是空间骨架，后者是 foveal 细节。跨房间的物属于**记忆（Mnemos）**不属于当前观察。

**⑤ 主动感知（看是一个动作）**

- `turn(heading)`：转向，改变视锥中心——**廉价但非零**（占极短 world-time，可与移动叠加成"边走边环顾"）。
- `look_at(target)`：把视锥中心对准某物/某人/某方向，短暂拉高该方向 `acuity`（凝视），代价是占用注意、`fov` 收窄（盯着一处时余光更差）。
- `scan()`：原地转一圈快速环视，把当前房间的 foveal 细节尽量补全（耗更多 world-time）。

这让"没看清就凑近看""听到动静回头"成为 soul 可主动调用的动作，而非世界替它免费补全。**看哪里，是 soul 的决策。**

**⑥ 光照耦合（复用已有 `Cell.light`）**

`range` 和每对象 `clarity` 都乘 `light`。于是深夜不开灯，视距骤缩到一两米、只能摸黑辨认近处轮廓；开灯（`toggle_light` 能力）恢复。"天黑该开灯"因此是视觉后果驱动的自然行为，不是脚本。


---

# Part V · 身体与生理（Body & Physiology）

> 生理是世界的第三根支柱，也是本工程从 ADOS 解耦出来的核心收益。身体随时间自然劣化（饿、渴、尿意、变脏、累），心智观察到这些信号、自主决定如何应对。**身体只能由 Oikos 改写，心智只能"行动 + 观察后果"。**

### 生理状态

```python
class Physiology(Stamped):          # 各维度 [0,1]，越高=越匮乏/越难受
    hunger: float                   # 饥饿
    thirst: float                   # 口渴
    bladder: float                  # 尿意(到 1 = 憋不住)
    bowel: float                    # 便意
    hygiene: float                  # 此处用"脏度": 越高越脏(需洗澡)
    fatigue: float                  # 疲劳/困倦
    energy: float                   # 体能(与 fatigue 相关但分开: 体力 vs 困意)
    temperature: float              # 体感(可选, 影响舒适)
    health: float                   # 综合健康(长期忽视生理→缓降)
```

> 注意：这里**没有** `compute_budget` / `money`。算力预算是心智自己的资源（留在 ADOS `ResourceState`），不是身体的生理。钱在世界里是"钱包/银行"这类物体实例（某 `ObjectType`）的 state，不是身体分量。

### 代谢动力学（World Tick 推进，不依赖 LLM）

每个 world tick，身体按动力学方程演化（形如 ADOS 的子状态方程，但运行在世界侧、跟随 world-time）：

```
hunger'  = + base_rate·Δt_world  + activity_cost(最近动作)  − meal_relief(吃事件)
thirst'  = + base_rate·Δt_world                              − drink_relief
bladder' = + f(近期摄入水分)·Δt_world                         − void_relief(如厕事件)
hygiene' = + soil_rate·Δt_world  + sweat(剧烈活动)            − shower_relief
fatigue' = + wake_rate·Δt_world  + circadian(day_phase)      − sleep_relief(睡眠)
energy'  = − exertion·Δt_active  + recover(rest/sleep)
```

关键点：
- **跟随 world-time。** 时间加速 → 饿得更快；`jump_forward(8h)` 睡觉 → 醒来 fatigue 大降、但 hunger/bladder 也涨了一截（因果守恒，Part III）。
- **活动相关。** 走路、做饭比躺着更耗精力、更出汗；动作执行时 Action Executor 把活动量写进代谢项。
- **昼夜相关。** `circadian(day_phase)` 让深夜 fatigue 涨得快——"困"是世界给的信号，不是心智凭空决定。
- **耦合。** 长期高 hunger/thirst 会缓慢拉低 health；睡眠不足 energy 恢复打折。系数全在 `world.toml`，可调、可单测。

### 心智如何"感觉到"身体（本工程与 ADOS 的接缝）

身体状态**作为 observation 的一部分**推给心智。心智的 Observation Engine 把它并入 `ObservationFrame`，进而：

- ADOS 的 **Internal State Dynamics** 据此演化 `NeedState`：观察到 `bladder=0.9` → `survival/safety` 类需求张力上升 → Motivation 竞争出"去厕所"动机 → Goal → Planning 调 `move_to(toilet) + use_toilet`。
- **"饿了去找吃的"的归属彻底清晰：** 饿（生理事实）在 Oikos；想吃、决定现在去吃还是先写完代码（动机与权衡）在 ADOS；走到厨房开冰箱拿东西吃（具身动作）又回到 Oikos。三段各归其位。

这正是 ADOS P2（行为来源于内部状态、用户输入只是 observation）的延伸：**身体信号也只是 observation**，不是直接命令身体去吃的指令。心智完全可以"忍着尿意先把话说完"——因为是否行动由内部状态裁决，不是生理信号直接驱动手脚。

### 缓解事件（恢复来自具身动作）

生理只能靠**身体在世界里做对的事**来缓解，且都受位置门控：

| 维度 | 缓解动作 | 前置（位置/物/姿态） |
|---|---|---|
| hunger | `eat(food)` | 手上或料理台有食物；通常先 `open_fridge`→`cook`/取食 |
| thirst | `drink` | 厨房/有水源处，或手持水杯 |
| bladder/bowel | `use_toilet` | `near=toilet` 且 `posture` 合适 |
| hygiene | `shower` | `near=shower`；耗较多 world-time |
| fatigue/energy | `sleep` / `nap` | `posture=lying` `near=bed`；常配合 `jump_forward` |

> 这些动作都是 **Part VII 的 skills**——生理与能力在此闭环：世界让身体变差，世界也提供让身体变好的能力，但能力受身体当前所在约束。


---

# Part VI · 事件、闹钟与声音（Events, Timers & Sound）

> 世界里会发生事。有些是身体设的（闹钟），有些是世界自发的（门铃、快递、设备通知、生理告警），还有一类是**身体之间靠声音交流**产生的。事件是世界推给心智的"中断"，与 ADOS 的 Event Bus 对接但**源在世界**。

### 事件类型

```python
class WorldEvent(Stamped):
    type: str          # "alarm" | "doorbell" | "device_notify" | "body_alert"
                       # | "ambient" | "device_disconnected" | "time_scale_changed" ...
    payload: dict
    priority: int      # 高优先级可打断当前动作(交由 ADOS Reflex 处理)
    at_world: float    # 触发时的世界时刻
```

### 闹钟 / 定时器（智能体可主动设）

心智可以**设闹钟**——这是它对未来世界施加影响的方式（自己不持有时钟，但能请世界在某时刻提醒自己）：

```
set_timer(at_world | after_Δ, label, recurring?, ref?) -> timer_id
cancel_timer(timer_id)
list_timers()
```

到点时，World Tick 的 Event Scheduler 产生一个 `alarm` 事件推给心智。典型：心智想"专注两小时后提醒我喝水"→ `set_timer(after=2h, "喝水")`；或"明早 8 点叫醒我"→ 配合 `sleep` + `jump_forward`，闹钟在跳跃重放中到点触发并把心智唤醒。

> **`ref` 字段 = 自主日程的桥（对接 soul.md Agenda）：** 心智排程时可在闹钟上挂一个不透明引用 `ref`（如某个 `goal_id` / agenda 项 id）。到点 `alarm` 把 `ref` 原样带回，心智据此知道"这是我之前给某个计划设的闹钟"，把自己唤醒到对应的重评。Oikos 对 `ref` 不作解读——它只是世界忠实保管、到点归还的一张便签。这正是"心智在脑子里排程、在手机上设闹钟"的落地：**Agenda（想做什么、优先级）在 Soul，闹钟（到点叫醒）在 Oikos。**

> 闹钟体现了 W2（世界自跑）的价值：闹钟挂在世界时钟上，即使心智在睡/在忙/断线，到点照响。心智设完就可以"忘掉它"，由世界负责守时——这正是把时间从心智解耦出去的实际好处。**关键：闹钟唤醒的是一次"重新决定"（Observation→重评），不是无条件执行某动作；当下身体/世界状态可以推翻预定计划。**

### 世界自发事件

- **门铃 / 敲门 / 快递：** 入户门处产生 `doorbell`，可携 payload（谁、为什么）。心智决定去不去开门（又是 observation→decision，不是强制）。
- **设备通知：** 手机来 Telegram 消息 → `device_notify`（但**只有手机在手/在身边可感知**；锁屏在卧室、人在厕所，可能"没听见"——具身的真实后果）。
- **生理告警：** 某生理维度越过阈值（如 `bladder>0.85`）→ 高优先级 `body_alert`，让 ADOS Reflex 可以"急着去厕所"般快速反应，不必等慢思考。
- **环境氛围：** 昼夜更替、天气（可选）、邻居噪音等低优先级 `ambient`，丰富世界质感。

### 动作的可打断性（事件与正在进行的动作）

长动作（`shower` / `sleep` / `cook` / 玩 MC）在执行期间世界继续跑，可能有事件到来。Oikos 对每个动作声明 `interruptible` 与 `interrupt_policy`：

- 高优先级事件（`body_alert`、紧急门铃）→ Oikos 发事件并**允许心智的 Reflex 请求 `abort_current`**，安全中止当前动作（如洗澡中途停水出来），不损坏世界状态。
- 低优先级（ambient）→ 仅记录，不打断。

这与 ADOS Reflex「预测危险→立即规避」同构：**世界负责发出可打断信号，心智的 Reflex 负责决定要不要打断**。

### 声音：人物之间的交流（W10 落地）

> 多身体共处一个世界时，**交流不是点对点直连，而是经由世界里的"空气"传播的物理声音**。这让对话天然具身：近处听得清、隔墙变闷、太远听不到、嘈杂处可能没听清——和视野的局部性（W3）完全同构。

```python
class Sound(Stamped):
    source_body: str | None    # 发声者 body_id(物体发声则为 None, 用 source_object)
    source_object: str | None  # 非人声源(闹钟铃/电视/门铃...)
    origin: tuple[int,int]     # 声音源点 = 发声者当时所在格
    kind: str                  # "speech" | "noise" | "alarm" | "ambient"
    content: str | None        # 语音内容(speech 才有)
    loudness: float            # 源头响度 [0,1](正常说话/喊叫/低语不同)
    at_world: float
```

**声学传播模型（World 计算，确定可单测）：** 对每具在场身体 `b`，计算它听到该声音的可闻度

```
audible(b) = loudness − dist_atten(path_len(origin→b.pos)) − occlusion(穿过的墙/门数)
clarity(b) = clamp(audible(b), 0, 1)          # 0=听不到, 低=听不清, 高=清楚
```

- **距离衰减** `dist_atten`：按源点到听者的路程（可用网格距离）递减——越远越轻。
- **阻挡衰减** `occlusion`：声波路径穿过的墙/关闭的门各扣一档——隔墙说话变闷、关门更闷。门开着衰减小。
- **结果分档：** `clarity` 高 → 听者 `sense` 收到完整 `content`；中 → 收到"听见有人在说话但听不清/只言片语"（content 被遮蔽为模糊摘要）；≈0 → **根本不并入该听者的观察**（他没听见，这是真实的漏听，不是 bug）。
- **发声者自己**也"听到"自己的声音（clarity≈1），符合直觉。

于是：在客厅正常音量说话，厨房（隔一道墙）的人可能只听到"有人在说话"，卧室关着门的人完全没听见；想让远处的人听清，得**走近**或**喊**（提高 `loudness`，但喊会更累、也吵到更多人）。**漏听与误听是世界的真实属性**，心智据此可能"没注意到你叫他"——这正是具身交流该有的样子，而非全知群发。

声音也是事件：可闻的 `Sound` 以 `type="sound"` 的 `WorldEvent` 推给听者，并入其 `sense`，进而成为 ADOS 的 `UserMessageReceived` / 社交观察（见 Part VII `speak`/`listen` 与 Part IX）。


---

# Part VII · Skills 即具身能力（落地核心）

> 本工程最实的一节，回答"**所有 skills 由世界提供**"到底怎么落地。ADOS Part VII 设计了 Capability/Skill 与 Domain Pack 体系；这里把那套体系的**Capability 实现侧搬进 Oikos**：心智不再自带能力，能力是世界按身体当前情境吐出的、带具身前置条件的目录。

### 能力契约（在 ADOS Capability 基础上加"具身前置"）

```python
class EmbodiedCapability(Protocol):
    spec: ActionSpec                # 复用 ADOS: 名称/入参出参 schema/影响分级/超时
    preconditions: BodyPrecond      # ★具身前置：在哪/什么姿态/手持什么/身体状态门槛
    duration_world: float | Expr    # 执行耗费的 world-time(可为状态函数; 形成"最小时长块")
    effects: BodyEffects            # 对身体/世界/物状态的确定性后果
    engages: list[str]              # ★此动作能"持续满足"的驱动需求(如 ["boredom","achievement"])
    interruptible: bool
    def run(self, args, world_ctx) -> ActionOutcome: ...

class BodyPrecond(BaseModel):
    near: str | None                # 须在某物的 reach 半径内(物 id 或 station 语义标签)
    posture: list[str] | None       # 允许的姿态
    held: list[str] | None          # 须手持某物(如 phone)
    object_state: dict | None       # 物须处某态(computer.on, fridge has food)
    phys_gate: dict | None          # 生理门槛(如 energy>0.1 才能走)
```

> `near` 取代旧的 `at_station`：从"站在某个格"变成"进入某物的 `reach` 半径"（连续判定）。带 `station` 语义标签的物（desk/bed/toilet…）可用标签引用，World 解析为"够得着任一挂该标签的物"。

### Affordance：物体类型如何"带来"能力（与编号目录的接缝）★

> Part IV 的 `ObjectType.affordances` 就落在这里。一个 **Affordance = "这类物体在身体凑到跟前时开放哪个能力 + 该能力针对此物的具身前置"**。它是"物体目录"与"能力目录"的粘合层：

```python
class Affordance(BaseModel):
    capability: str                 # 引用一个已注册 EmbodiedCapability 的名字
    when: BodyPrecond               # 针对此物的额外前置(就坐/手持此物/物处某态)
    binds_object: bool = True       # 执行时把"本物实例"作为 target 传给 capability
```

`list_skills()` 的完整判定因此变为：**遍历身体可达范围内的物体实例 → 取其 `type.affordances` → 逐个判 `when` 前置 → 满足的能力进目录**。于是：

- 加一种新物体登记类型时，**它带来的交互一并声明在 `affordances` 里**——这是"加物体顺带加能力"无需改内核的关键（Part IV 的三步法第 1 步）。
- 同一个 `cook` 能力可被 `stove`(2002) 与 `microwave`(2004) 两种类型各自 `affordances` 引用，前置不同（微波炉更快、只能热不能煎）——**能力复用、物体差异化**，正是 ADOS"Skill 引用 Capability、二者解耦"在世界侧的体现。
- 便携物的能力（手机的 `send_message`）通过 `when.held=[本物]` 表达"得拿在手里才行"。

### 行为稳定性：Oikos 侧的三个钩子 ★

> Soul 的 `IntentionState` 负责"承诺/迟滞/事件触发重评"（soul.md），但要让"刚坐下玩 MC 又起身"真正消失，**满足必须在过程中累积、切换必须有真实代价**——这两件事是物理事实，归 Oikos 提供。三个钩子：

1. **`engages` + 过程式满足。** 持续性活动（玩 MC、看电视、读书）的 `effects` 不是一次性跳变，而是按 `duration_world` **逐 tick 累积**地降低它 `engages` 的需求：`boredom' = −r_engage·stimulation(t)`，`stimulation` 随已持续时长**边际递减**（新鲜感衰减）。于是无聊不会被瞬间清零（那会导致 ADHD），而是玩够一段才被满足、且玩太久收益趋零（防上瘾）——这正是 Soul 侧 satiation 的物理来源。时间常数全在 `world.toml`，可调可单测。

2. **`duration_world` = 最小时长块。** 动作有确定耗时（洗澡 ~15min、做饭一段），执行期间被身体动作锁占住（Part VII 互斥），不会被半个 tick 的冲动打断；只有高优先级事件经 `abort_current` 才能中止。这让行为有"块状"的最小粒度，而非逐 tick 可碎。

3. **切换成本来自具身摩擦。** 换活动须 `stand_up→move_to→...` 耗时耗力，且**离座立即断 MC 丢进度**（W5）。Oikos 在 `act` 的 outcome 里如实报告这些代价（走了几步、断了什么、丢了什么进度），供 Soul 的切换不等式把 `SwitchCost` 算足——"为略高一点的冲动起身"因此不划算。

> 一句话：Soul 决定"要不要换"，Oikos 决定"换的代价有多大、当前活动满足得怎么样"。两者相乘，才得到人类式的"坐下来就好好玩一阵"。

### `list_skills()`：返回的是"此刻能做什么"，不是"世界有什么"

这是 W4 的核心机制，也是与 ADOS Planning 的接缝：

```
list_skills() ─► 遍历全部已注册 EmbodiedCapability
             ─► 用 当前 Embodiment(pos/heading/posture/near_object/held) + Physiology + Object states
                逐个判定 preconditions (交互类前置 = "在物的 reach 半径内")
             ─► 只返回前置满足的能力 → 即 ADOS Planning 的 action_catalog()
```

于是 ADOS 的 Planning「计划只能由当前已加载 Capability 组成」自动升级为「**计划只能由身体此刻真正能做的动作组成**」：身体在卧室床上，目录里没有 `cook`、没有 `play_minecraft`，只有 `get_up`、`sleep`、`move_to`……心智想玩 MC，得先规划"起床→走到 desk→坐下→开机→登录"这条具身路径。**规划层因此天然产出符合物理约束的计划，无需额外校验。**

### 能力分组（v0.1 公寓世界）

**A. 移动、朝向与感知（locomotion, orientation & perception）**
- `move_to(target)`：target 可为世界坐标点、物体实例、或房间名。格级 A* 求粗路径 → 平滑成连续路径 → 按 `speed` 逐 tick 滑动，圆形身体贴墙滑动、耗 world-time＋energy，途中可在任意连续点被高优先级事件打断停住。到点后 `heading` 默认朝向目标。
- `move(direction, distance?)`：朝当前/指定方向连续步进一段（不指定目标点的自由行走）。
- `turn(heading)`：转向到某连续角度（或 `turn_toward(target)` 对准某物/某人），改变视锥中心；廉价、可与 `move` 叠加成"边走边环顾"。
- `look_at(target)` / `scan()`：主动感知（见"感知与视野"⑤）——凝视某处拉高该向清晰度、或原地环视补全房间细节。
- `stand_up` / `sit_down(at)` / `lie_down(at)`：姿态切换，部分能力要求特定姿态；`sit/lie` 需身体在目标物交互半径内。

**B. 身体维护（对应 Part V 缓解动作）**
- `eat` / `drink` / `cook` / `open_fridge` / `use_toilet` / `shower` / `sleep` / `nap` / `wash_hands`。每个都带位置＋物＋姿态前置，执行后由 `effects` 改写生理（这是身体变好的唯一途径）。
- 例：`shower` 前置 `near=shower`，`duration_world≈15min`，`effects: hygiene→0.05, energy 略降`，`interruptible=True`。

**C. 居家交互**
- `open_fridge`（看库存）/ `take_food` / `throw_trash` / `answer_door`（响应 doorbell）/ `toggle_light` / `pick_up(obj)` / `put_down(obj)`（管理手持物）。

**D. 设备：电脑与 Minecraft（具身门控范例一）**
- `power_on_computer` / `power_off_computer`：前置 `near=desk` 且 `seated`。
- `login_minecraft`：前置 `computer.on` 且 `seated near=desk`，建立 Minecraft Bridge 会话。
- `play_minecraft(mc_action)`：把 MC 内动作（move/mine/place/craft/chat…）透传给 Bridge。前置 **始终包含 `seated near=desk` 且 `mc_session.active`**。
- **硬约束（W5）：** 任何让身体离开 desk 交互半径的动作（`stand_up`、`move_to(其他)`）触发时，Device Manager **立即** `DeviceDisconnected` 并断开 MC 会话——"离开电脑立刻断开"。心智在下一帧 observation 看到"你站了起来，MC 断线了"，必须重新走回来登录才能继续。这把"挂机"这种非具身行为从根上堵死：**人离开座位，游戏里的人也就不动了。**

> Minecraft 在此不是 ADOS 直连的 Domain Pack，而是**电脑这台设备背后的一个外部世界**。MC 的 Observation/Capability 经 Bridge 包一层后，**只在 seated@desk 时并入 Oikos 的 sense/skills**。公寓世界始终在底层运行：玩 MC 时身体仍在变饿，门铃仍可能响，玩太久会困——逼出"玩一会儿得起来吃饭/上厕所"的真实节奏。

**E. 设备：手机与 Telegram（具身门控范例二）**
- `pick_up_phone`：前置身体在手机所在格（充电处）或手机已在 `held`。把 `phone` 加入 `held`。
- `open_app(telegram)`：前置 `phone in held` 且 `phone.on`。
- `type_message(text)` / `send_message`：前置 `phone in held` 且当前 app=telegram。经 Phone/Telegram Bridge 真发出去（Bot API），发 `AgentMessageSent`。
- `put_phone_on_charger`：放下手机，`held` 移除 phone；此后收不到需要看屏幕的通知（只可能"听到"提示音=`device_notify`，但要回消息得先走过去拿起来）。
- **具身认知（用户的核心诉求）：** 心智在 observation 里读到的不是"channel: telegram"，而是 **"你手里拿着手机，屏幕上是和 X 的 Telegram 对话，最近几条是……"**；能力描述是"用手指在手机上打字并发送"。`prompts.toml` 里 chat 角色的 system 提示也据此渲染，让心智**清楚知道"我是在用一部手机给对方发消息"**，而非凭空对话。收消息同理：手机不在手上时，Telegram 来信只先变成一声提示音事件，心智要"走过去、拿起手机、解锁、打开对话"才能真正读到内容。

> 与 ADOS 交互层的接缝：ADOS Part VI 里 `send_message` 是个抽象 Action。接入 Oikos 后，它**降解为一串具身动作**（`pick_up_phone → open_app → type_message → send_message`），底层仍走同一套 `UserMessageReceived` / `AgentMessageSent` 事件契约——交互层无感，但心智的世界模型里多了"手机"这个真实中介。终端交互可保留为"世界外的旁路"（开发者通道），而面向用户的自然交互走手机。

**F. 社交：说话与倾听（多身体交流，对应 Part VI 声音）**
- `speak(content, loudness="normal")`：在身体当前格制造一个 `kind="speech"` 的 `Sound`（源点=自己 pos）。`loudness` 可选 `whisper / normal / shout`——越响传得越远、但更累更扰民。**这是面向"屋里其他人"的交流**，与"用手机发给远方的人"是两条不同通道：和同处一室的人对话用 `speak`（空气传播），和不在场的人联系用手机（Telegram）。
- `listen()` / 被动听到：听到的声音由世界按声学模型自动并入 `sense`，无需主动调用；`listen` 仅用于"刻意凝神去听"（短暂提高对低 clarity 声音的辨识，代价是占用注意）。
- **具身认知：** 心智在 observation 里读到的是 **"你听到 Hermes 从厨房方向说：'……'（有点闷，隔着墙）"** 或 **"附近有人在说话，但听不清"**——带上**谁、从哪个方向、清不清楚**。心智因此知道"对方就在这屋里、我在用嗓子跟他说话"，与"低头在手机上打字"是截然不同的两种社交体感。
- **回应不是自动的：** 听到不等于必须答。是否回话、回什么，仍由心智内部状态裁决（ADOS P2）——可以没听清而追问、可以在忙而不理、可以走近了再说。漏听（clarity≈0）则心智压根没收到，自然不会回应。

> 多智能体场景的自然结果：Alice 在客厅对 Hermes 说话 → 世界生成声音 → Hermes 的身体若在可闻范围则其 `sense` 收到 → Hermes 的心智自主决定如何回应 → 它 `speak` 回去 → 声音再传回 Alice。两个**完全独立的心智**（甚至不同架构：一个 ADOS、一个一次性 agent）通过**世界这层共享物理空气**对话，谁都没有直连谁。

### 互斥与并发（一具身体不能分身）

身体是单一执行资源。Oikos 维护一个**身体动作锁**：同一时刻只能执行一个占用身体的主动作（不能边洗澡边打字、不能走路时同时睡觉）。请求与当前动作冲突 → `WorldError`（除非是 Reflex 的 `abort_current` 抢占）。这让"边……边……"这类不具身的并行从根上不可能，逼心智串行规划。

> 注：`speak` 是轻量动作（瞬时、低占用），可与移动等并存（边走边说），由 `interrupt_policy` 标注为非独占；而 `listen`（凝神）、洗澡、睡觉等是独占的。哪些动作独占、哪些可叠加，在各 capability 的 spec 里声明。

### 能力的经验侧仍在 ADOS / Mnemos

注意区分：**EmbodiedCapability（"真能做"，代码）在 Oikos；Skill（"该怎么做"的经验知识，声明式 `*.skill.toml`）仍按 ADOS Part VII 进 Mnemos 作规划先验。** 例如经验"夜深了先上厕所再睡更舒服"是一条 Skill（知识），它引用 `use_toilet`/`sleep` 这两个由 Oikos 提供的 Capability（能力）。二者解耦，正如 ADOS 原设计。Learning 把成功序列固化成新 Skill，也只写知识、不写身体能力——身体能做什么由世界定义，不由经验扩充。


---

# Part VIII · 世界协议与身体认领（World Protocol & Body Claiming）

> 心智与 Oikos 进程之间的契约。**从最简起步：localhost HTTP + msgpack**，与 ADOS / Mnemos 同款。接口语义稳定，传输实现可替换而调用方无感（W8）。**心智是主动方**：先发现世界里有哪些身体，再主动认领一具（W9）。完整的"如何连接"流程见配套的 [embody.md](embody.md)，任何能读它的智能体都能据此连入。

| 操作 | 方向 | 说明 |
|---|---|---|
| `list_bodies()` | mind → oikos | 发现世界里有哪些身体：返回每具的 `body_id / display_name / claimed_by / 粗略状态`。心智据此知道**有哪些身体、哪些空置可认领** |
| `attach(mind_id, body_id)` | mind → oikos | **认领**一具身体；body 已被他人认领则 fail-loud。返回世界快照句柄与该身体当前 observation。重连同一 body_id 即恢复 |
| `detach()` | mind → oikos | 释放当前身体（身体留在世界里变为空置实体，仍占格/代谢/可被感知）。心智下线前应主动 detach |
| `sense()` | mind → oikos | 拉取**所认领身体**的当前 `WorldObservation`（本体感＋空间骨架＋视觉细节＋听觉，皆自我中心分级） |
| `list_skills()` | mind → oikos | 返回**此刻该身体真正可执行**的能力目录（= ADOS action_catalog） |
| `act(skill, args)` | mind → oikos | 校验具身前置→执行→返回 `ActionOutcome`（实际后果＋耗时）。非法即 `WorldError` |
| `abort_current()` | mind → oikos | Reflex 抢占：安全中止正在进行的可打断动作 |
| `set_timer / cancel_timer / list_timers` | mind → oikos | 闹钟/定时器管理（按身体隔离）；可挂不透明 `ref`（关联 Soul 侧 Agenda 项/goal），到点 `alarm` 原样带回 |
| `time.get / set_scale / pause / resume / jump_forward` | mind → oikos | 世界时钟读取与受控调节（只能向前）。注意：时钟是**全世界共享**的，调速影响所有在场身体 |
| `introspect(query)` | mind → oikos | 调试/可观测：返回身体全状态、地图、在场身体、活跃事件、最近动作链 |

**认领规则（W9）：** 一具身体同一时刻至多一个心智认领；认领冲突、认领不存在的 body_id、对未认领身体调 `sense/act` → 一律 `WorldError`。`mind_id` 标识连接方（Alice / OpenClaw / Hermes…），仅用于认领归属与日志，不影响身体能力（能力只由身体情境决定，W4）。

**事件推送（oikos → mind，异步）：** `WorldEvent` 经协议的事件流（SSE / 长轮询 / ws）只推给**认领了相关身体的心智**，并入 ADOS Event Bus：`alarm` / `doorbell` / `device_notify` / `body_alert` / `sound`（可闻声音/他人说话）/ `device_disconnected` / `time_scale_changed` / `events_during_jump` 等。

### `WorldObservation`（推给心智的世界帧）

> 这是"body 观察到的世界长什么样、以什么格式给 soul"的正式契约。三条设计原则：**① 自我中心（egocentric）**——一切位置以身体为原点、用方位＋距离表达（"左前方约 3 米"），而非全局坐标，因为 soul 是透过这具身体在看；**② 分层**——本体感/空间骨架/视觉细节/听觉分开（见"感知与视野"④）；**③ 分级**——每个被感知对象带 `clarity`，看不清就如实标注，绝不替 soul 补全。

```python
class WorldObservation(Stamped):
    world_time: WorldTimeInfo        # 世界时刻/日期/昼夜相位(soul 不自带时钟)
    proprioception: SelfSnapshot     # 本体感: 我的姿态/朝向/生理/够得着谁/手持什么
    here: SpatialFrame               # 空间骨架(结构层, 不受视锥限): 所在房间/形状/出口方位
    seen: list[Percept]              # ★视觉细节(foveal, 受视锥+遮挡+光照): 分级
    heard: list[Percept]             # ★听觉(W10 声学): 来源方位/clarity/(清楚时)内容
    held_detail: list[ObjectView]    # 手持物细节(如手机屏上的 Telegram 对话)
    available_skills: list[SkillBrief]  # 此刻真正可做的能力(= list_skills)
    salient_events: list[WorldEvent]    # 自上次 sense 以来的新事件
    narration: str                   # ★世界渲染的一段第一人称自然语言(见下)

class SelfSnapshot(BaseModel):
    posture: str; heading_deg: float          # "站着, 面朝东(90°)"
    in_room: str                               # "living"
    physiology: dict                           # {hunger:0.3, bladder:0.7, ...}
    reachable: list[str]                       # 此刻够得着、可交互的物 id
    held: list[str]

class SpatialFrame(BaseModel):                 # 结构层: 闭眼也知道的空间常识
    room: str; room_shape: str                 # "长方形客厅, 约 6×3 米"
    exits: list[Bearing]                        # 门/出口的方位: [{to:"kitchen", dir:"东", dist:4.2}]
    light: float                               # 当前处光照(影响下面 seen 的清晰度)

class Percept(BaseModel):                       # 一条被感知的东西(视或听), 自我中心+分级
    kind: Literal["object","body","sound"]
    ref: str | None                            # 看清时给出身份(instance_id/body名); 看不清=None
    bearing: str; distance: float              # "左前方", 2.6  (方位+米)
    clarity: float                             # [0,1]
    detail: str | None                         # 看清/听清才有: 状态/动作/内容
    hint: str | None                           # 看不清时的粗描述("有个大件家具/有人影/有人在说话")
```

**分级怎么落进 `Percept`：**
- `clarity ≥ clear`：`ref` + `detail` 都给（"冰箱, 右前方 1.2 米, 门关着"）。
- `mid ≤ clarity < clear`：`ref=None`，只给 `hint`（"右前方约 5 米有个高大家具, 看不清"）。
- `clarity < mid`：**根本不出现在 `seen`/`heard` 里**（真实遗漏）。

**`narration`——给 LLM 的第一人称渲染（关键的易用性设计）：** 结构化字段供 ADOS 各模块精确消费，但 soul 的 Thinking/Planning 往往直接读一段自然语言更省 token、更贴具身。World 据结构化字段渲染一段第一人称叙述，例如：

> *"你站在客厅中央，面朝东。这是个约 6×3 米的长方形房间，东边有扇门通向厨房（约 4 米），身后（西）是入户方向。正前方约 3 米是沙发，看得清；右前方餐桌上好像放着什么，有点远看不真切。你听到厨房方向传来水声，还算清楚。肚子有点饿了。此刻你够得着的只有沙发——想用别的得先走过去。"*

这段话让"soul 透过 body 看世界"变得直观：**它读到的不是坐标数组，而是一个站在房间里、有前后左右、有看清看不清、有听见听不清的"我"。** 结构化层与叙述层同源同真值，渲染模板在 `prompts.toml`（ADOS 侧）可调。

它被 ADOS 的 Observation Engine 当作一个**传感源**消费，映射进 `ObservationFrame`（objects/scene/spatial/**social**）：`seen` 里的 body 喂 social/relationship 图，`heard` 里清楚的人声成为 `UserMessageReceived`（当面对话与手机来信走同一交互契约，但带"这是当面听到的"标记）；`proprioception.physiology` 驱动 InternalState 的 Need 演化（Part V 接缝）；`here`/`seen` 的方位距离喂 spatial 图，支撑"想用冰箱→发现够不着→规划走过去"这类具身规划。

### 错误处理（no-fallback，与两个姊妹工程一致）

任一操作失败（前置不满足、够不着目标物、寻路无解、撞墙、设备未连、Bridge 断开、时钟非法调节如试图倒流）→ 抛带完整上下文的 `WorldError` 并结构化记日志（哪个 skill、缺哪个前置、身体当时 `pos/heading/posture/held`、世界时刻），**绝不返回伪造的成功结果、绝不静默把身体"瞬移"到目标**。心智据此知道动作真实失败了，世界模型不与现实分叉（W7）。


---

# Part IX · 与 Soul（ADOS）/ Mnemos 接合

> 接入 Oikos 后，ADOS 认知内核**一行不改**（符合其 P2/P4/P6），只是它的"传感源"和"能力来源"从内置/Domain Pack 变成了 Oikos。这与 Mnemos 让 Memory 模块退化成薄客户端是同一个手法。**但 Oikos 不绑定 ADOS**：它面向的是"任意能读协议的心智"，ADOS 只是其中最完整的一种。下面先讲 ADOS 的深接合，末尾讲非 ADOS 智能体（OpenClaw / Hermes）如何以最薄的方式连入。

### 解耦对照表（从 ADOS 原稿迁出了什么）

| 原 ADOS 里的东西 | 迁移后归属 | 说明 |
|---|---|---|
| `NeedState.survival`（饥饿等生理匮乏的"事实部分"） | **Oikos `Physiology`** | 生理事实在世界；Need（"匮乏张力/想不想满足"）仍在 ADOS，由观察驱动 |
| `ResourceState.energy`（被当电量/体力用的部分） | **Oikos `Physiology.energy/fatigue`** | 身体体能在世界；`compute_budget`/`money` 仍属心智/世界物，不动 |
| Minecraft Domain Pack 的世界状态与动作 | **Oikos（电脑设备背后的外部桥）** | 经 Bridge 并入，且受 `seated@desk` 门控 |
| `send_message` 抽象 Action | **Oikos `pick_up_phone→...→send_message`** | 降解为具身动作；事件契约不变 |
| 时间感（原本隐含在 tick / 时间戳里） | **Oikos World Clock** | 心智不再自带世界时钟，看手机/钟来知时间 |
| 空间（原 ADOS 几乎没有真实空间概念） | **Oikos Grid Map** | 新增的具身维度 |
| Capability 的"真能做"实现侧 | **Oikos Capability Registry** | Skill（经验知识）仍按 ADOS 进 Mnemos |

### 与 ADOS 各模块的接缝（订阅/产出层面，无直接调用）

- **Observation Engine：** 新增一个 Oikos 传感 stage，`sense()` 的 `WorldObservation` 映射进 `ObservationFrame`。身体生理、当前房间、手持设备屏幕都成为观察对象。预测轨迹也可纳入身体趋势（"再不喝水半小时后会很渴"）。
- **Internal State Dynamics：** 订阅身体观察，演化 Need/Emotion——这是"身体→心理"的转换层，也是 P2 的延伸（身体信号是 observation，不是指令）。
- **Reflex System：** 订阅 `body_alert` / `device_disconnected` 等高优先级世界事件，可发 `abort_current` 抢占——世界发信号、Reflex 决定打断，分工清晰且 Reflex 不依赖 LLM。
- **Planning：** `action_catalog()` 直接取自 Oikos `list_skills()`（此刻具身可行的动作），并以 Mnemos 检索到的 Skill 为先验。计划天然满足物理约束。
- **Action Layer：** 每个 atomic action 落地为一次 `act(skill, args)`；`ActionFinished` 的 outcome 用 Oikos 返回的真实后果填充（含"实际耗了多少 world-time、身体变成什么样"）。
- **Learning：** 用"预测的身体后果 vs 真实后果"的 Prediction Error 学习世界模型（如"洗澡大概 15 分钟""走到厨房要 6 步"），并把成功序列固化为 Skill 写回 Mnemos。

### 三进程协同的一帧（端到端示例：尿意→如厕）

1. **Oikos** world tick 推进 `bladder` 到 0.88 → 发 `body_alert`（高优先级）。
2. **ADOS** Observation 收下，Internal State 把 safety/survival 需求张力抬高；Reflex 评估"还能忍"，暂不抢占。
3. **ADOS** Motivation/Goal 竞争出"去厕所"目标；Planning 调 `list_skills()` 见当前在客厅、目录里有 `move_to`，无 `use_toilet`（马桶不在交互半径内）。
4. Planning 产出计划：`move_to(toilet) → use_toilet`。Action Layer 逐个 `act()`。
5. **Oikos** 执行 `move_to`：连续寻路、平滑滑行、耗 world-time、`pos` 连续逼近到马桶 `reach` 半径内；再执行 `use_toilet`：`effects: bladder→0.05`。
6. **Mnemos**（经 ADOS）`remember` 这段经历；Learning 校准"从沙发到厕所约 6 米、约 5 秒"的世界模型。

整条链里：**生理事实与空间在 Oikos，动机与决策在 ADOS，经历与经验在 Mnemos**——三个工程各守其真值，靠协议串起一个会饿会动会记得的智能体。

### 非 ADOS 智能体如何连入（OpenClaw / Hermes 等）

Oikos 的接口不假设连接方是持续自主体。一个**一次性 agent**（一轮 LLM + 工具调用循环，没有需求/情绪/持续 tick）同样能认领一具身体、在屋里走动、跟人说话、玩 MC——只是它不会"自发地饿了想吃"，而是被提示后才行动。它需要的全部知识就一份：**[embody.md](embody.md)**，一份自包含的"如何连接世界中的身体"指南。

- **最薄连接方式：** agent 读 `embody.md` → `list_bodies()` 看有哪些空身体 → `attach(self_id, body_id)` 认领 → 循环 `sense()` 理解处境、`list_skills()` 看能做什么、`act()` 行动 → 离开前 `detach()`。整套就是几个 HTTP 调用，无需实现任何 ADOS 模块。
- **能力对它一视同仁：** 能做什么只由身体情境决定（W4），与连接方是谁无关。所以一次性 agent 和 Alice 站在同一个电脑前，看到的 `list_skills()` 一样有 `play_minecraft`；走到对方面前 `speak`，对方（无论什么架构）都能听到。
- **差异只在"心智的丰富度"：** ADOS 会因 `bladder` 高而自发去厕所；一次性 agent 不会自发，但你让它"去趟厕所"它照样能 `move_to(toilet)→use_toilet`。**世界对两者公平，分别只在各自心智里。** 这正是把世界彻底解耦出去的回报：世界只管提供一具规则一致的身体，谁来开都行。


---

# Part X · 世界的格式与结构

> **一个世界一个目录**（世界里可住多具身体），便于隔离、迁移、快照。选型刻意与 ADOS / Mnemos 对齐（SQLite + TOML + append-only 日志 + 周期快照），使其既能独立存在，又能被任意心智当作外部服务接入。

```
world_<world_id>/
├── world.toml         # 世界配置: 时钟默认/时区/代谢系数/设备/Bridge 连接
├── object_types.toml  # ★物体类型目录(编号模板); 加新物体往这里追加, 内核不改
├── map.toml           # 网格地图: 尺寸/区域(多格)/物体实例(引用type_id)/门/声学参数
├── bodies.toml        # ★世界里有哪些身体: body_id/名字/初始位置/默认设备归属
├── skills/            # EmbodiedCapability 定义(代码) + 各自 ActionSpec & 具身前置
│   ├── locomotion.py  # move_to / posture ...
│   ├── body_care.py   # eat / drink / use_toilet / shower / sleep ...
│   ├── home.py        # fridge / door / lights / pick_up ...
│   ├── social.py      # speak / listen (声音/交流)
│   └── devices.py     # computer+minecraft / phone+telegram (含 Bridge 门控)
├── state.db           # SQLite: 各身体/物实例/计时器/声音的当前真值 + 历史
├── world.log          # append-only 世界事件/动作/代谢/声音日志(可回放重建)
└── snapshots/         # 周期快照, 配合日志可重建任意时刻世界
```

`object_types.toml` 示意（编号目录，加物体只往这里追加）：

```toml
[[type]]
type_id = 2001
name = "fridge"
kind = "appliance"
blocks_walk = true
reach = 0.9                       # 交互半径(米): 身体中心走进此半径即可交互
footprint = 0.4                   # 连续占地半径
state_schema = { food = 0, drink = 0 }
affordances = [
  { capability = "open_fridge", when = {} },
  { capability = "take_food",   when = { object_state = { food_gt = 0 } } },
]
tags = ["kitchen", "storage"]

[[type]]                          # 新增一种物体 = 追加一段, 编号取家电段下一空位
type_id = 2004
name = "microwave"
kind = "appliance"
blocks_walk = true
reach = 0.8
state_schema = { contents = "", running = false }
affordances = [ { capability = "heat_food", when = { held = ["food_item"] } } ]
tags = ["kitchen"]
```

`bodies.toml` 示意（多身体声明，谁来认领无所谓）：

```toml
[[body]]
id = "alice"; display_name = "Alice"; start_cell = [2, 2]   # 卧室内可站立格
# 设备默认归属: 这具身体的手机/电脑(也可全屋共享, 由 world.toml 决定)
phone = "phone_alice"

[[body]]
id = "guest"; display_name = "Hermes"; start_cell = [3, 6]  # 客厅内可站立格
phone = "phone_guest"
```

> 设备归属可"专属"或"共享"：单人公寓里电脑是共享物（谁坐到 desk 谁用）；手机通常专属（各人各机）。由 `world.toml` 的设备段声明。声学参数（距离衰减系数、每道墙/门的 occlusion 档位、各 loudness 档的源响度）也落在 `map.toml`，可调可单测。完整可运行三件套见 [examples/world.toml](examples/world.toml)、[examples/map.toml](examples/map.toml)、[examples/bodies.toml](examples/bodies.toml)。

`world.toml` 关键段（示意）：

```toml
[clock]
scale = 1.0                 # 默认与现实同步
timezone = "Asia/Shanghai"
start_paused = false

[metabolism]                # Part V 代谢系数, 可调可单测
hunger_rate = 0.00012       # 每世界秒
thirst_rate = 0.0002
bladder_rate = 0.00018
hygiene_soil_rate = 0.00006
fatigue_wake_rate = 0.00009
circadian_amp = 0.3

[devices.computer]
station = "desk"            # 共享物: 谁坐到 desk 工位谁用
require_posture = "seated"
[devices.computer.minecraft]
bridge = "mineflayer"
host = "localhost"; port = 25565; username = "ALICE"
disconnect_on_leave = true  # ★离开 desk 立刻断开

[devices.phone]
portable = true
home_cell = [10, 5]         # 充电处(厨房 P 格); 各身体专属机的归属见 bodies.toml
[devices.phone.telegram]
bridge = "telegram_bot"
bot_token = "ENV:TELEGRAM_BOT_TOKEN"
allowed_user_ids = [123456789]
```

`map.toml` 关键段（网格作地形、物按单格锚点摆放、身体连续移动）：

```toml
[grid]
w = 12; h = 9

# ── 区域 = 多格集合(房间/功能区), 用矩形或格子列表声明 ──
[rooms]
bedroom  = { rects = [[1,1,3,4]] }          # [x0,y0,x1,y1] 闭区间
hall     = { rects = [[5,1,7,3]] }
bathroom = { rects = [[9,1,10,3]] }
living   = { rects = [[1,5,7,7]] }
kitchen  = { rects = [[9,5,10,7]] }

# ── 物体实例 = 引用 type_id + 锚点格; 同类型可多个; 极轻量 ──
# 交互半径由 type.reach 决定, 无需在实例里声明交互格
[[instance]]
instance_id = "bed_main";    type_id = 1001; anchor_cell = [1,1]
[[instance]]
instance_id = "computer_desk"; type_id = 4001; anchor_cell = [1,3]
[[instance]]
instance_id = "shower_bath"; type_id = 3002; anchor_cell = [9,1]
[[instance]]
instance_id = "toilet_bath"; type_id = 3001; anchor_cell = [10,1]
[[instance]]
instance_id = "fridge_kitchen"; type_id = 2001; anchor_cell = [9,5]; state = { food = 3, drink = 2 }
[[instance]]
instance_id = "stove_kitchen"; type_id = 2002; anchor_cell = [10,7]
[[instance]]
instance_id = "phone_alice"; type_id = 4002; anchor_cell = [10,5]   # 便携(type.blocks_walk=false), 不挡路
# 其余实例(书架/洗手台/沙发/电视/餐桌/料理台)同理, 完整表见 examples/map.toml
```

- **与 ADOS / Mnemos 对齐的硬约定：** SQLite + TOML 配置、append-only 日志、schema 校验缺项即 fail-loud、密钥一律 `ENV:` 间接引用。
- **地图校验（加载期 fail-loud）：** 每个 `instance.type_id` 必须在 `object_types.toml` 里存在；挡路物（`type.blocks_walk=true`）的 `anchor_cell` 标记为 `solid`（连续碰撞障碍）、每格至多一件挡路物、且其 `reach` 半径内须有可站立空地（否则永远够不着）；便携物（`blocks_walk=false`）可落在可走格、不挡路；区域多边形合法、全屋连续可走空间连通。违例即 `WorldError` 拒绝加载，不带病运行。
- **可重建性：** `world.log` + `snapshots/` 使任意时刻世界状态可重放重建（event-sourcing 式）。这是可测试性与"心智重连看到一致世界"的基石——身体状态不靠心智记忆维持，靠世界自己的日志维持。

---

# Part XI · 分阶段路线图

> 原则同 ADOS / Mnemos：每阶段产出一个能独立运行、可观测、可回放的系统，附退出标准。

### Phase 0 — 时钟与世界心跳
World Clock（同步/调速/暂停/向前跳）、World Tick Loop 骨架、`WorldError` 全局错误通道、结构化日志、`time` 协议、空世界 `introspect`。
**退出标准：** 世界能空跑 ≥24h、tick 稳定；调速/暂停/向前跳后时间单调连续、可广播；故意试图倒流时 fail-loud。

### Phase 1 — 连续空间、具身移动与视野
加载 `map.toml`（网格地形 → 抽墙线段 `walls` + 房间多边形），身体连续 `pos/heading`，`move_to` 连续寻路（格级 A* → 平滑）、圆形碰撞贴墙滑动、撞墙/够不着 fail-loud；实现视锥＋遮挡＋光照＋距离的 `sense`，返回自我中心分级的 `WorldObservation` + `narration`；`turn/look_at/scan` 主动感知。
**退出标准：** 身体在公寓里平滑移动、被墙连续阻挡、可停在任意点；`sense` 只给视锥内可见内容且带 `clarity`（背后/隔墙/暗处看不到）；转身/凑近能改变看清的东西；移动耗时随连续距离合理增长。

### Phase 2 — 身体生理与代谢
`Physiology` 全维度、代谢动力学跟随 world-time、`jump_forward` 因果守恒结算、生理阈值触发 `body_alert`。
**退出标准：** 空跑下身体按时变饿/渴/累；睡觉+跳跃后 fatigue 降而 hunger 涨（守恒）；阈值告警正确触发；时间加速后劣化同比加快。

### Phase 3 — Skills 即具身能力 + 事件/闹钟
Capability Registry、`list_skills()` 按情境过滤、身体维护与居家交互能力、动作锁互斥、`set_timer` 闹钟、门铃/告警事件、`abort_current`。
**退出标准：** `list_skills()` 随身体所在动态变化；生理只能靠对应具身动作缓解且受位置门控；闹钟到点触发；高优先级事件可打断可打断动作。

### Phase 4 — 设备门控：电脑/Minecraft 与 手机/Telegram
Device Manager、Minecraft Bridge（`seated@desk` 才活跃、离开立断）、Phone/Telegram Bridge（手持才可收发、observation 注入具身框架）。
**退出标准：** 玩 MC 期间起身/离座**立即** `DeviceDisconnected` 并断 MC；发 Telegram 必须先拿起手机、心智 observation/prompt 明确呈现"在用手机发消息"；手机不在手时来信只先变提示音。

### Phase 5 — 接入 Soul（ADOS）
ADOS Observation 增 Oikos 传感 stage、Planning 取 `list_skills()` 作 catalog、Action Layer 落地为 `act()`、生理→Need 转换、Reflex 订阅世界告警。
**退出标准：** ADOS 认知内核零改动接入；端到端跑通 Part IX 的"尿意→如厕"链；`Behavior=f(InternalState)` 仍成立（身体信号经 Need 才影响行为，非直驱手脚）。

### Phase 6 — 多身体认领 + 声音交流 + 任意智能体连入
`list_bodies / attach(body_id) / detach`、认领冲突 fail-loud、多身体连续碰撞互为动态障碍、`speak/listen` 与声学传播（距离＋阻挡衰减、漏听/听不清）、`WorldObservation` 的 `seen`/`heard`（自我中心分级）；冻结并发布 **[embody.md](embody.md)**，用一个**非 ADOS 的一次性 agent** 验证连入。
**退出标准：** 两具身体（一具 ADOS、一具仅靠读 embody.md 的一次性 agent）同处一世界；A 在客厅说话，隔墙的 B 只收到"听不清"、同室的 B 收到完整内容、关门远处的 B 完全没收到；任一 agent 仅凭 embody.md 即可认领身体并完成"走到对方面前说句话"；身体空置时仍代谢、占格、可被看到听到。

> **范围说明：** 室外地图、复杂物理（流体/重力细节）、跨进程多世界联邦暂不实现（YAGNI）。**一世界多身体与声音交流是 v0.1 的一等特性**（Phase 6），但仍是单 Oikos 进程内的多身体，不做分布式。


---

# Part XII · 技术选型（单进程最简实现）

| 关注点 | 选型 | 说明 |
|---|---|---|
| 语言 | Python + asyncio | 单进程异步；World Tick 可独立线程/任务，与 ADOS 一致 |
| 协议传输 | localhost HTTP + msgpack | 最简起步；语义稳定，后续可换 socket/gRPC |
| 世界时钟 | 单调时钟 + 可控 scale/offset | 只向前，调节即重锚定并广播 |
| 地图 | 网格地形 + 连续坐标；格级 A* → 路径平滑 | 网格描墙/房间/光照；身体连续移动，圆-线段碰撞，不引入完整物理引擎 |
| 感知/视野 | 视锥 + 网格射线遮挡 + 光照/距离衰减 | 每对象算 clarity，自我中心分级；不做逐像素渲染 |
| 状态存储 | SQLite（身体/物/计时器） | 不起独立数据库服务 |
| 事件/动作日志 | 本地 append-only 文件 | 审计＋回放＋世界重建 |
| 生理代谢 | 配置驱动的动力学方程 | 跟随 world-time，系数可调可单测 |
| Minecraft 接入 | Mineflayer 等 bot 桥（设备背后） | 仅 seated@desk 活跃，离座即断 |
| 手机/Telegram | Bot API 桥（手持设备背后） | 手持才收发，observation 注入具身框架 |
| 数据契约 | pydantic v2 + `Stamped` 基类 | schema 校验，违例 fail-loud |
| 世界格式 | 目录=世界（world/map.toml + skills/ + state.db + log + snapshots） | 隔离、可迁移、可重建 |
| 可观测性 | structlog 结构化日志 + `introspect` | 错误全量带上下文 |
| LLM | **无** | Oikos 是物理世界，不思考、不调 LLM |

---

# Part XIII · 工程约束（硬性，CI 可校验）

世界拥有时间/空间/身体/设备/事件的唯一真值，心智侧不得持有这些状态的本地真值（无本地时钟/坐标/生理变量，CI 可静态校验）；身体状态只能由 Oikos 改写，对外只暴露"行动＋观察后果"，心智无任何直接写身体的通道；World Tick 必须独立于心智持续运行，心智断开/重启时世界照常演化；世界时间只能单调向前（`jump_forward` 亦只向前），任何倒流请求 fail-loud；`jump_forward` 必须因果守恒地结算期间的代谢与事件，不得凭空跳变；移动必须在连续空间沿平滑路径推进、受圆-墙连续碰撞约束、耗 world-time，禁止瞬移与穿墙；**可交互物以单格为锚点摆放、交互判定为"身体中心进入其 `reach` 半径＋姿态满足"（连续，非站相邻格）；区域是连续多边形，用于判定所在房间与视野遮挡**；**感知必须是有视角的、局部的、分级的（视锥＋遮挡＋光照＋距离算 clarity）——`sense` 不得返回全图或全知，看不清如实标注、看不见不并入，绝不替心智补全；看向某处（turn/look_at/scan）是要花代价的动作**；**物体必须分类型（带全局唯一数字编号 `type_id`，append-only、退役只标记不复用）与实例（引用编号）两层，内核不内置任何具体物体，新物体只经 `object_types.toml` 登记 + `map.toml` 摆实例引入而不改内核；能力经类型的 affordance 开放**；地图加载期校验 `type_id` 存在性/锚点格不越界/每件物 `reach` 半径内有可站立空地/区域多边形合法/全屋连续可走空间连通，违例 fail-loud 拒绝加载；`list_skills()` 必须按身体当前情境过滤，规划层只能看到此刻具身可行的能力；一切外部世界（Minecraft/Telegram）必须经"世界中的设备"访问，设备前置不满足即不开放对应能力；**玩 MC 必须 `seated@desk`、离座立即断开**；**发消息必须 `phone in held` 且 observation/prompt 明确呈现"在用手机发消息"**；一具身体同一时刻只执行一个占用身体的主动作（动作锁互斥）；**一具身体同一时刻至多被一个心智认领，认领冲突/认领不存在身体/对未认领身体调 sense·act 一律 fail-loud；心智是主动认领方，世界不主动塞身体；空置身体仍是世界实体（占格/代谢/可被感知）**；**说话必须经声音在世界中传播（以发声者为源点、按距离＋阻挡衰减），不得点对点直连绕过空气；听者只能收到其身体位置可闻的声音，漏听/听不清是合法结果不得补全**；EmbodiedCapability（代码）属 Oikos，Skill（经验知识）属 Mnemos，二者不得混写；**禁止 fallback 与静默降级，任何错误以 `WorldError` ＋完整上下文暴露，绝不伪造成功或静默瞬移**；每个状态变更/动作/事件带时间戳、来源、因果链；Oikos 不依赖 LLM；连入方不限于 ADOS——协议自包含、配 [embody.md](embody.md) 使任意能读协议的智能体均可认领身体；整个系统保持单 Oikos 进程最简实现，不为未实现的室外/复杂物理/分布式多世界提前设计。

---

# Part XIV · 风险与缓解

- **世界与心智状态分叉：** 心智的世界模型与 Oikos 真值不一致（以为自己在厨房，其实没动）。**缓解：** no-fallback——动作失败必 `WorldError`，绝不静默瞬移；`sense` 始终以世界真值为准，心智每帧校正；事件日志可回放比对。
- **时间调节引发因果错乱：** 加速/跳跃下生理或事件结算错误。**缓解：** 时钟单调、调节即重锚定；`jump_forward` 走"重放结算"而非"拨表"；时间相关全过程单测（给定 Δt 验证代谢量与触发事件确定）。
- **设备门控漏洞（挂机/绕过具身）：** 心智试图离座仍操作 MC、不拿手机就发消息。**缓解：** 门控是能力前置的硬判定，离 desk 立即 `DeviceDisconnected`；`send_message` 前置强制 `phone in held`；前置不满足时能力根本不在目录里，规划层看不到。
- **寻路/地图退化：** 复杂家具布局下寻路失败或卡死。**缓解：** 格级 A* 先判有解性，无解 fail-loud 而非乱走；地图加载期校验连续可走空间连通；连续移动带最大时长与卡住检测（贴墙抖动即停并报告）。
- **视野遮挡/射线计算不稳或过慢：** 遮挡判定错误导致"该看见没看见/穿墙看见"，或每 tick 对全屋对象算可见性太贵。**缓解：** 遮挡走网格射线步进（确定、可单测）；只对身体所在房间＋经开门可见的相邻房间的对象算可见性（房间剪枝），远房间不算；`clarity` 计算纯函数、给定输入结果确定，可单测"背对/隔墙/暗处看不到"。
- **感知遗漏被误判为 bug（与声学同源）：** "它没看见桌上的杯子"既可能是真没看向那、也可能是暗/远/被挡。**缓解：** 漏看/看不清是**设计内的合法结果**（W12，与 W10 漏听同构）；世界如实给 `clarity` 与 `hint`，不替心智补全；想看清就 `turn/look_at/凑近/开灯`——这是具身代价，不是缺陷。
- **Bridge 不稳定（MC/Telegram 断连）：** 外部服务波动。**缓解：** Bridge 断开发 `device_disconnected` 明确报告，不伪装在线；重连由心智决定再次操作设备触发，Oikos 不自动静默重连掩盖。
- **世界自跑导致心智"被惊到"：** 离线期间世界大幅演化，重连时身体已很糟。**缓解：** 重连 `attach` 返回"期间发生了什么"的事件摘要（`events_during_jump` 同款），让心智平滑接续而非突然面对一个陌生身体；也可按需 `pause` 世界等心智回来。
- **代谢系数失真（太快/太慢，体验割裂）：** **缓解：** 系数全在 `world.toml` 可调，配默认贴近人体节律；提供"加速实验"档（高 scale）与"贴现实"档（scale=1）两套预设。
- **身体认领冲突 / 抢身体：** 多心智争抢同一具身体，或一具身体被两个心智同时驱动导致状态错乱。**缓解：** 认领是排他的，第二个 `attach` 同一 body fail-loud；身体记 `claimed_by`，对未认领身体的 `sense/act` 拒绝；心智下线应 `detach`，超时未活动可由世界回收认领（配置）。
- **声学被滥用 / 交流失败被误判为 bug：** "对方没回我"既可能是真没听见、也可能是心智选择不答。**缓解：** 漏听/听不清是**设计内的合法结果**（与视野局部性同构），世界如实给 `clarity`，不补全内容；想被听清就走近或提高 loudness——这是具身的真实代价，不是缺陷。喊叫的额外精力/扰民代价防止"无脑喊"。
- **不可信连入方（任意 agent 可连）：** 开放给非 ADOS agent 连入，可能有恶意/低质客户端。**缓解：** 连入方只能经协议、只能认领世界已声明的身体、只能调被身体情境允许的能力（W4），碰不到世界内部真值与他人身体；高影响动作仍按影响分级需确认；`mind_id` 全程记日志可审计。

---

# Ultimate Objective

Oikos 的目标不是做一个游戏或仿真器，而是给一个本无身体的心智，一具**会饿、会渴、会困、会被墙挡住、会因为离开座位而从游戏里掉线**的身体，和一个**有真实时间、真实空间、真实因果**的栖居地。它独立于任何心智的内部设计：把时间、空间、生理、设备、事件这些"属于世界而非属于心智"的真值，从 [ADOS](soul.md) 里干净地剥出来，让心智回归纯粹的认知——只**感知**它所栖居的世界，并**通过身体**在其中行动。

配合 [Mnemos](memory.md) 提供的记忆，三者合成一个完整的隐喻：**一个心智（Soul），住在一具身体里、身处一个世界中（Oikos），并拥有记忆（Mnemos）。** 当智能体说"我有点饿了，先去厨房弄点吃的，回头再跟你聊"——饿是世界给的、想吃是心智决定的、走去厨房是身体做的、记得刚才聊到哪是记忆存的。四件事各归其位，却共同构成了一个**真切地活在某处、某时、某具身体里的存在**。

而当世界里**不止一具身体**时，它还兑现了一件更难的事：让两个**各自独立、甚至架构不同**的心智，真正"住在同一个地方"——在同一间客厅里，一个能走到另一个面前，开口说话，被听见或被听岔，等一句回应。没有谁直连谁，他们只是共享了同一片空气、同一套物理。这正是把世界从心智彻底解耦出来、做成一个谁都能走进来栖居的公共场所，最终要兑现的东西。











