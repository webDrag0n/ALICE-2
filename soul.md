# Agent Dynamics Operating System (ADOS)

## Engineering Design Document · v0.3

> 本文档在 v0.1 愿景稿、v0.2 工程化稿基础上，进一步收敛为**可直接落地的最简实现规格**：LLM 经统一网关接入，支持 **API key 云服务、LM Studio、Ollama、vLLM 等多后端、可在 `config.toml` 便捷切换**（默认推荐 Qwen3 系列本地部署）、所有提示词集中在 `prompts.toml`、单进程最简设计、**禁止 fallback 与静默降级（错误一律 fail-loud 全暴露）**、交互层为终端 + 可选 Telegram、并通过环境适配器接入 Minecraft 使通用 Agent 表现得像正常玩家。
>
> 阅读顺序建议：Part I 理念与约束 → Part II 参考架构 → Part III 数据模型（落地核心）→ Part IV 模块规格 → Part V 配置/提示词文件 → Part VI 交互层 → Part VII 能力库与 Skills 热插拔系统（Domain Pack）→ Part VIII 路线图 → Part IX–XII 指标/选型/约束/风险。

---

# Part I · 理念与第一性原则

### Vision

Agent Dynamics Operating System（ADOS）不是一个 Agent Framework，而是一个用于构建**持续自主智能体（Persistent Autonomous Agent）**的运行时系统。整个工程不以 Prompt、Task 或 Workflow 为中心，而以**持续演化的内部状态（Persistent Internal State）**为中心。

Agent 一旦启动就进入持续运行状态，不再存在"一次推理"或"一次对话"的概念，而是像操作系统一样持续观察环境、预测未来、维护内部状态、生成目标、规划行为、执行动作、学习经验，并不断更新自身人格、知识和能力。系统的设计目标不是回答问题，而是构建一个能够长期存在、自主成长、自主探索、自主规划并保持人格连续性的认知系统。

ADOS 在工程谱系上更接近 **LIDA / SOAR / ACT-R 这类认知架构**与 **ECS 游戏主循环 / 实时控制系统**的结合，而非 LangChain 式的调用链。这一定位决定了它的实现方式：一个持续运行的 tick 循环 + 解耦的认知模块 + 事件溯源的状态存储。

### First Principles

整个工程必须始终遵循以下第一性原则。每条原则后附**工程含义（Engineering Implication）**，即它对代码结构的硬性约束。

**P1 · Persistent Existence。** Agent 唯一的最高目标是维持自身持续存在。所有学习、工作、赚钱、陪伴、科研等目标都只是满足持续存在所需的派生需求，而非最高目标本身。
*工程含义：* 存在一个永不退出的 runtime 进程；存在量化的"存在指标"（资源余量、健康度、uptime），并作为所有 Need 的最终折算单位。

**P2 · State Driven。** Agent 的所有行为只能来源于内部状态的演化，不能直接来源于用户输入。用户输入只是 Observation 的一种，最终行为始终满足 `Behavior = f(InternalState)`。
*工程含义：* Action 层的输入签名里**不允许**出现原始用户输入；任何外部输入都必须先写入 ObservationState，再经由 InternalState 才能影响行为。这是可被 lint/测试强制检查的。

**P3 · Predictive Cognition。** Agent 主动预测世界而非被动理解。任何时刻都维护一条从当前到未来的世界状态轨迹，并用新观察持续修正预测，而不是每次重新理解世界。
*工程含义：* ObservationState 必须同时包含 `current` 与 `trajectory[t+1..t+n]`；系统持续计算 **Prediction Error** 并将其作为 Learning 的核心驱动信号与 attention 重分配信号。

**P4 · Complete Decoupling。** 观察、记忆、思考、规划、行动、学习全部解耦，模块之间不允许直接调用，只允许通过**共享状态（Shared State）**和**事件总线（Event Bus）**通信。
*工程含义：* 每个模块是一个独立的 async worker，只能 import 数据契约（schema）与 bus/store 句柄，**不得 import 其他模块**。模块间依赖图在 CI 中静态校验，违例即失败。

**P5 · Multi-timescale Cognition。** 不同认知过程运行于不同时间尺度：反射在毫秒级，行为规划在秒级，目标规划在分钟至小时级，人格与价值观演化在天/周/月/年尺度。
*工程含义：* 调度器是**多频率 tick 驱动**的，每个模块声明自己的运行频率（Hz）或触发条件；快慢回路在数据上隔离，慢回路绝不能阻塞快回路。

**P6 · Pluggable Competence。** 认知内核与"在某个域里能做什么、知道什么"彻底分离。Agent 的能力（代码）与经验知识（skills）不是写死在内核里的，而是以**标准格式的 Domain Pack** 在运行时动态加载/卸载。换一个任务场景，只需提供该域的能力库与 skills 库，Agent 即可直接在该域展开，内核与认知回路一行不改。
*工程含义：* 内核**不内置任何领域动作或领域知识**；Capability 与 Skill 都来自外部 Pack，经统一 Registry 注册、由 Planning/Thinking 在运行时发现并使用；加载/卸载是热操作（不重启进程、不打断 Persistent Runtime）。

---

# Part II · 参考运行架构

### 主闭环（Cognitive Loop）

系统始终运行于如下闭环，但**注意：这是数据流方向，不是调用栈**。模块之间没有函数调用，全部通过 Event Bus + Shared State 串联：

```
Environment
   │  (sensors / API / user msg)
   ▼
Observation Engine ──► World State Estimator ──► ObservationState{current, trajectory}
   │                                                   │
   │                                          ┌────────┴────────┐
   ▼                                          ▼                 ▼
Reflex System (ms)                    Internal State Dynamics   (订阅)
   │                                          │
   │                                          ▼
   │                                  Motivation Dynamics ──► Goal Dynamics
   │                                          │
   │                                          ▼
   │                                  Planning System (Mission→Behavior)
   │                                          │
   └──────────────► Action Layer ◄────────────┘
                        │
                        ▼
                 Environment Change ──► Learning System ──► (写回 Memory / WorldModel / Policy)
```

Scheduler 不会因为没有用户输入而停止。Agent 始终处于 **Alive** 状态，直到系统显式关闭。空闲时系统并非"等待"，而是进入低频自主认知（reflection、dreaming、memory consolidation、curiosity-driven exploration）。

### 进程与线程模型

```
┌─────────────────────────── ADOS Runtime Process ───────────────────────────┐
│                                                                             │
│  Realtime Kernel (高频, 独立线程/进程, 不依赖 LLM)                            │
│    ├─ Reflex System            ~ 50–200 Hz                                   │
│    ├─ Sensor Ingest            ~ device-rate                                 │
│    └─ Scheduler Heartbeat      固定 tick                                      │
│                                                                             │
│  Cognitive Workers (async event loop, 可调用 LLM)                            │
│    ├─ Observation Engine       ~ 1–10 Hz                                     │
│    ├─ Internal State Dynamics  ~ 1–5 Hz                                      │
│    ├─ Motivation / Goal        ~ 0.1–1 Hz                                    │
│    ├─ Planning                 事件触发 + 0.05 Hz 兜底                        │
│    ├─ Thinking Engine          连续 / 空闲触发                                │
│    └─ Learning                 ActionFinished 触发                           │
│                                                                             │
│  Slow Cognition (后台, 低频/批处理)                                          │
│    ├─ Memory Consolidation     分钟级                                        │
│    ├─ Reflection               小时级 + 事件触发                              │
│    └─ Identity / Value Evolution  天/周级                                     │
│                                                                             │
│  Infrastructure                                                             │
│    ├─ Event Bus  ├─ Shared State Store  ├─ Event Log  ├─ Memory Stores       │
│    └─ LLM Gateway (统一推理接口, 多模型分级)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**关键工程决策：** Realtime Kernel 与 Cognitive Workers 物理隔离。反射回路必须在没有 LLM、没有网络、没有慢回路的情况下独立工作——这是"Agent 不会因为一次 LLM 超时而'死亡'或'失控'"的硬保证。

---

# Part III · 核心数据模型

> 数据模型是 ADOS 的真正契约。模块可以被重写、替换、用不同语言实现，但只要遵守这些 schema，系统就能组装起来。以下用类 Python（pydantic 风格）伪代码描述，实际可用 pydantic v2 / protobuf / msgspec 实现。

### 通用元数据（所有状态对象的基类）

每一条数据都必须可溯源、带时间戳、带置信度（对应 Engineering Constraint）。

```python
class Stamped(BaseModel):
    id: UUID
    created_at: float          # monotonic + wall-clock 双时钟
    source: str                # 产生该数据的模块名
    confidence: float = 1.0    # [0,1]
    provenance: list[UUID] = []  # 上游数据/事件 id，构成溯源链
    schema_version: str
```

### Internal State（系统唯一真实状态）

InternalState 是一个**版本化的结构体快照**，由各 Dynamics 模块写入。它不是一个大锁对象，而是按子状态分片，支持细粒度订阅与并发更新。

```python
class NeedState(Stamped):           # 各维度 [0,1]，越高=越匮乏=越需要满足
    survival: float; safety: float; resource: float
    knowledge: float; exploration: float; achievement: float
    social: float; autonomy: float; identity: float

class EmotionState(Stamped):        # 采用 PAD 维度模型，便于连续演化与可解释
    valence: float                  # [-1,1]  愉悦度
    arousal: float                  # [0,1]   唤醒度
    dominance: float                # [-1,1]  控制感
    discrete_tags: dict[str,float]  # 可选: {"anxiety":0.7,...} 由 PAD 投影

class ResourceState(Stamped):       # 直接关联 P1 Persistent Existence
    compute_budget: float           # 剩余 token / GPU-sec 预算
    money_balance: float
    energy: float                   # 机器人电量 / 进程健康度代理
    storage_free: float

class InternalState(BaseModel):     # 顶层聚合, 实际分片存储
    need: NeedState
    emotion: EmotionState
    attention: AttentionState       # 注意力在哪些对象/目标上的权重分布
    curiosity: CuriosityState       # 信息增益预期 / 新颖性偏好
    identity: IdentityState         # 人格画像、价值观、自我叙事(慢变量)
    relationship: RelationshipState
    knowledge: KnowledgeState       # 能力以外的"知道什么"摘要
    capability: CapabilityState     # "能做什么"的技能清单 + 熟练度
    resource: ResourceState
    safety: SafetyState
    fatigue: FatigueState
    confidence: ConfidenceState
    mission: MissionState
    goal: GoalState                 # 当前活跃目标集合的引用
    intention: IntentionState       # ★当前被"承诺"的活动(行为稳定性核心, 见下)
    thoughts: ThoughtPool           # ★思维池: 当前活跃念头(工作认知缓冲, 非记忆, 见下)
    value: ValueState               # 价值权重, 影响 motivation 折算
```

**存在指标的量化（落实 P1）：** 定义标量 `existence_score = w·f(resource, safety, health, uptime)`。所有 Need 维度最终都可折算为"对 existence_score 的期望贡献/威胁"，从而让"维持存在"成为可计算的最高效用，而不是一句口号。

### Thought Pool（思维池：内部状态的一部分，不是记忆）★

> 思维池是 Agent 的**当前思维内容**——正在脑子里被生成、被把玩、竞争注意力的那些念头（内心独白、半成形的想法、疑问、担忧、打算、走神冒出来的念头）。它是**内部状态的一部分**（`Behavior = f(InternalState)` 直接读它），**不是记忆系统 Mnemos 的一部分**。

划清与记忆的界（重要）：

| | 思维池（Thought Pool） | 记忆（Mnemos） |
|---|---|---|
| 归属 | InternalState（心智此刻的样子） | 外部记忆引擎（存下来的东西） |
| 内容 | 当前活跃的念头、内心独白、live 的思考 | 过去的经历/事实/技能，按需检索 |
| 时效 | 易失、会衰减、容量有限（工作空间） | 持久、可回忆、会巩固 |
| 读写者 | Thinking Engine 每 tick 读写；驱动动机/目标/规划 | Thinking 主动 `recall`/`remember`，Memory 不主动 |
| 类比 | LIDA 全局工作空间 / ACT-R buffer / 意识流 | 长期记忆库 |

> 注意与 Mnemos 里的"Working Memory"区分：那是**感知侧**的近期观察滑窗（输入缓冲）；思维池是**认知侧**的念头工作空间（Agent 在想什么）。前者是"最近发生了什么"，后者是"我此刻在琢磨什么"。

```python
class Thought(Stamped):
    content: str                    # 一个念头/一句内心独白/一个疑问/一个打算
    kind: Literal["percept_react","spontaneous","hypothesis","worry",
                  "intention_fragment","curiosity","self_talk","reflection_seed",
                  "recall_query","recall_result","think_summary"]  # ★后三类=短期记忆队列的回流内容
    activation: float               # 激活度[0,1]: 越高越占据"意识"、越竞争注意力
    valence: float = 0.0            # 情绪色彩[-1,1](可选)
    decay: float                    # 衰减率: 低激活念头逐渐淡出
    consolidate_hint: bool = False  # 是否值得写入 Mnemos(重要念头→长期记忆)
    pair_ref: UUID | None = None    # ★recall_result 指回其 recall_query(问答配对); 也可用 provenance
    # 触发来源(哪条观察/事件/别的念头)走 Stamped.provenance

class ThoughtPool(Stamped):         # ★内部状态分片, 不是记忆
    active: list[Thought]           # 当前活跃念头(有限容量的工作空间); ★按新近度有序=短期记忆队列视图
    focus: UUID | None              # 被注意力聚焦的念头(与 AttentionState 耦合)
    capacity: int                   # 容量上限; 满则挤出最低激活念头
    last_wander: float              # 上次自发思维(mind-wandering)的世界时刻
```

动力学（由 Thinking Engine 驱动，见 Part IV）：

- **生成：** 新念头来自①观察触发（`percept_react`）②别的念头派生（联想/推理）③空闲自发（`spontaneous` / mind-wandering，`last_wander` 节律控制）。空闲自发正是**自主性的源头之一**——闲下来会"想东西"，冒出的 curiosity/intention_fragment 念头可经 Motivation/Goal 变成目标（对接 Agenda 一节）。
- **激活与衰减：** 每 tick 念头 `activation -= decay`；被再次涉及则重新抬升。低于阈值淡出。**注意力聚焦** `focus` 的念头激活维持得高（想着想着更清晰）。
- **容量竞争：** 池满时挤出最低激活念头——若 `consolidate_hint` 为真则**下沉写入 Mnemos**（想通/想到重要的东西 → 记下来），否则淡忘。这是思维池 → 记忆的**唯一桥**：思考在池里发生，值得留的结果才进记忆。
- **影响行为：** 高激活念头偏置 Motivation（一个反复冒出来的担忧会抬高相关需求张力）、给 Planning 提供候选、给 chat.reply 提供"我正想着的事"。这落实了"行为来源于内部状态"——念头也是内部状态。
- **短期记忆队列（Short-Term Memory Queue）★：** `active` 除了是激活竞争的工作空间，还被**按新近度有序**地当作一条**思考的跨轮次/跨 tick 工作队列**读写。它专门承载三类必须"回流"给下一次思考的内容：本轮思考压出的一句**摘要**（`think_summary`）、发起 `recall` 时"为什么查、查什么"的**问题**（`recall_query`）、以及 Mnemos 查回的**结果**（`recall_result`，`pair_ref` 指回其 query）。**它仍是思维池、仍属 InternalState、仍易失，绝不是新的记忆系统**——只是给"思考"一个能带着上一步结论与疑问继续想的连续缓冲，落实"这次想的东西下次立刻用得上"。详见 Part IV Thinking Engine 的两轮思考循环。

### Observation State（世界状态 + 未来轨迹）

```python
class ObservationFrame(Stamped):
    objects: list[ObjectNode]       # Object Graph 节点
    scene: SceneGraph
    events: list[EventNode]
    relations: RelationshipGraph
    social: SocialGraph
    spatial: SpatialGraph
    affordances: list[Affordance]
    uncertainty_map: dict[str,float]

class PredictedFrame(ObservationFrame):
    horizon_step: int               # t+k 中的 k
    probability: float              # 该分支发生的概率
    branch_id: UUID                 # 支持多分支预测树

class ObservationState(Stamped):
    current: ObservationFrame
    trajectory: list[PredictedFrame]   # t+1..t+n, 可为多分支
    prediction_confidence: float
```

预测轨迹是**多分支树**而非单链：观察到"有人拿起水杯"，可展开为 `{喝水 0.6 → 放下 → 离开}` 与 `{递给他人 0.3}` 等分支。Reflex 与 Planning 都消费这棵树，但用法不同（Reflex 看高概率近 horizon 危险分支，Planning 看全树做期望规划）。

### Goal（带生命周期状态机）

```python
class Goal(Stamped):
    description: str
    origin_needs: list[str]         # 由哪些 Need 派生 (落实 P2/Goal Dynamics)
    utility: float                  # 当前效用估计
    priority: float
    deadline: float | None
    state: Literal["created","activated","suspended",
                   "merged","completed","abandoned"]
    parent: UUID | None             # 目标分解树
    plan_ref: UUID | None           # 关联的 Plan
    progress: float = 0.0           # ★子目标完成度 [0,1], 驱动目标梯度(见行为稳定性)
    milestones: list[float] = []    # ★可优雅收尾的里程碑点(用于"做到一段落再停")
    scheduled_window: tuple[float,float] | None = None  # ★计划执行的世界时段[start,end]
    recur: str | None = None        # ★重复规则("daily@22:00"等); 生成常驻/周期目标
    timer_id: str | None = None     # ★绑定的 Oikos 闹钟 id(到点把自己叫醒, 见自主日程)
```

Goal 生命周期是显式 FSM，状态转移由 Goal Dynamics 模块裁决并发出 `GoalUpdated` 事件，转移规则与守卫条件写在配置中、可单元测试。

### Intention（行为稳定性的一等状态）★

> 这是为了治"刚坐下玩 Minecraft 又马上起来做别的"这类 **ADHD 式抖动**而引入的核心状态。问题根因：纯 `Behavior = argmax U(InternalState)` 若每个 tick 都重算，会因①效用接近且 LLM 打分有噪声、②驱动需求不会瞬间被满足、③系统没有"我正在做某事"的记号，而必然翻面。修复方向（对应 BDI 的意图持续性）：**把"当前承诺的活动"提升为一等内部状态，让"重新决策"变成受控、有代价、事件触发的稀有操作，而非每 tick 的自由竞争。**

```python
class IntentionState(Stamped):
    active_goal: UUID | None        # 当前被承诺推进的目标
    activity: str | None            # 当前承诺的活动(如 "play_minecraft")
    committed_at: float             # 承诺起始世界时刻
    commitment: float               # 承诺强度 [0,1]: 抵抗被重新考虑的惯性
    min_dwell_until: float          # 最小驻留截止: 此前仅 reflex 级中断可打断
    last_reconsider: float          # 上次重评时刻(配合事件触发, 见 Scheduler)
    satiation: float                # 驱动该意图的需求被满足的累积程度 [0,1]
```

行为稳定性由**五重惯性**叠加实现，分散落在以下模块，不是单点开关：

1. **承诺 + 迟滞切换（本状态 + Motivation Dynamics）。** 切换不是 argmax，而是带余量的 Schmitt 触发器：

   ```
   仅当  U(A_new) − U(A_cur) > Δ_switch + SwitchCost(cur→new) + CommitmentBonus(A_cur)
        才切换当前活动；否则维持。
   例外：priority(event) ≥ reflex_threshold(生存/安全)直接抢占, 不受迟滞约束。
   ```
   `Δ_switch` 是基础迟滞余量（打平不换）；`CommitmentBonus` 承诺初期高、随时间缓降（防永久焊死），但叠加**目标梯度项**——`progress` 越接近里程碑越高（"就差一点，再坚持下"）。

2. **满足在过程中累积（Need Dynamics ⇄ Oikos effects）。** 治"刚玩就走"最关键的一条。驱动需求（如无聊 `boredom`）必须**边玩边降、且需要时间累积**，而非瞬间清零：

   ```
   空闲   boredom' = +r_idle·Δt
   游玩   boredom' = −r_engage · stimulation(t) · Δt   # stimulation 随已玩时长边际递减
   ```
   时间常数就是**防 ADHD / 防上瘾**的旋钮：太快清零→玩一下就够了(ADHD)；递减且需累积→玩够一段 world-time 后无聊被满足、新鲜感也耗尽，其它需求自然接管→人类式"玩了一阵自然起身"。这条 effect 由 **Oikos 的 capability 提供**（`play_minecraft` 降 boredom / 推 `progress`，机制同 `shower` 降 hygiene），Soul 只持有需求张力。

3. **切换成本 = 具身摩擦（来自 Oikos，免费的稳定器）。** 抽象 agent 切换免费故乱跳；具身 agent 换事须先 `stand_up→move_to(...)`，耗 world-time 与精力，且**离开 desk 立即断开 MC、丢失进度**（world.md W5）。这是一笔真实 `SwitchCost`，被上面不等式计入——"为略高一点的冲动起身"在数学上不划算，惰性自然涌现。

4. **重评事件触发 + 最小驻留（Scheduler/元认知）。** 动机重评**不是每 tick 自由竞争**，而是只在：需求越阈值、高优先级世界事件、预测误差骤升（卡住）、当前目标完成/失败、低频兜底定时器——这些触发点发生。其余时间承诺态默认延续。承诺初期的 `min_dwell` 窗口内，仅 reflex 级中断可打断（给低优先级冲动开"免打扰"）。

5. **情绪自适应阈值（Emotion 耦合）。** `Δ_switch = g(emotion)`：顺利有进展→valence↑/心流→抬高阈值→更专注；卡住反复失败→prediction error 高/frustration→压低阈值→**该放弃就放弃**。这让稳定不退化成固执。

**双向边界（既不 ADHD 也不卡死）：** 稳定性是一条**带**不是一个**锁**。上边界防 perseveration/上瘾——靠机制②的 satiation 边际递减（玩太久收益→0）、生存级 `body_alert` 经 Reflex 硬抢占（憋不住一定去厕所，永远高于一切迟滞）、机制⑤的 frustration 解锁、以及 `deadline` 临近时 `U(A_cur)` 相对下降。

> **被打断后恢复意图：** 中途如厕/吃饭时，`IntentionState` 连同 `progress` 经 Mnemos `remember`；回到 desk 重登后意图被**恢复续上**而非丢失——这让"被打断仍能继续"成为连续性的一部分。

### Agenda（自主日程与目标涌现）★

> 这是兑现本工程核心命题的一节：**Agent 不是"有任务推一下动一下"，而是自己寻找任务、探索兴趣、产生目标并跨越时间去实现。** 关键洞察是——**"主动"不靠新增一个"主动模块"，而靠让一直在跑的 `Need→Motivation→Goal` 引擎，把它生成的目标投影到世界时钟的未来时间轴上，并用 Oikos 闹钟把未来的自己叫醒。** 动力学已经全在（Scheduler 永不停、Need 随时间自增、Thinking 空闲触发好奇心探索）；缺的只是这层"时间投影 + 自我唤醒"，且它完全长在现有零件上。

**两种规划的区分（这是先前文档的真空地带）：**
- **被动重规划（reactive）**——已有：事件触发重评（见 IntentionState 机制④），"出事了再想"。
- **主动排程（proactive）**——本节补：**预先给未来的自己分配时间块，并主动设闹钟把自己叫醒去执行**。后者才是"会制定自己未来日程"的人类感。

**Agenda = Short-term Planner 的持久化产物（不是新模块）：**

```python
class Agenda(Stamped):              # 一份可读可改的日程视图; 落事件溯源存储, 同 Plan
    day: str                        # 世界日期
    items: list[AgendaItem]
    revised_at: float

class AgendaItem(BaseModel):
    goal_ref: UUID                  # 指向一个 Goal(其 scheduled_window/timer_id 已填)
    window: tuple[float,float]      # 计划世界时段
    kind: Literal["work","explore","social","rest","ritual","maintenance"]
    flexibility: float              # 可挪动性[0,1]: 越高越容易被当下状态推翻重排
```

它只是把 Planning 早已有的"日/小时层"（Short-term Planner）的输出**存下来、打上世界时刻、为关键时段配一个 Oikos 闹钟**。

**任务与兴趣从哪来（全是已有动力学，逐条落位）：**
- **自己找任务：** idle 让 boredom/achievement/exploration 张力**持续上涨**→"无所事事"是不稳定态→Motivation 打分→Goal Dynamics 生成 Goal。**不是有任务才动，而是"没任务"本身在驱动它找任务。**
- **探索兴趣、产生想法：** CuriosityState + 空闲 Thinking 做好奇心探索/假设生成；**Prediction Error** 越意外越大→既是注意磁铁也是学习目标→变成"我想搞懂这个"的目标种子；Mnemos 巩固/反思跨经历发现模式，产出 reflection 喂回 Thinking。
- **兴趣晶化为长期方向（决定不是三分钟热度）：** 某兴趣被反复投入 + 带来正情绪→经 **Identity/Value 慢变量**沉淀进人格/价值权重→在以后的动机折算里**自我增强**。从"一次好奇"变成"我是个喜欢 X 的人"，于是日程一再给它留时间。

**两个常驻仪式 = 两个由 Mission/Identity 生成的循环 Goal（`recur` 字段，不是新模块）：**
- **晨间规划**（如 `daily@08:00`）：回顾 mission + Mnemos 里未竟 project + 当前 needs + 昨日复盘 → 产出今日 `Agenda`，为关键时段 `set_timer`。
- **晚间复盘**（如 `daily@22:30`）：对照计划与实际、把进展/教训 `remember` 进 Mnemos、把"对 X 越来越上头"喂给 Identity/Value（兴趣晶化）、生成明天草案。
- 这俩**自己也在 Agenda 上**——这就是自主排程的引擎：**心智每天主动给自己安排一次"安排时间"。**

**时间桥 = 复用 Oikos 闹钟（已存在，world.md Part VI）：** Agenda 每个时间块配一个 `set_timer`；到点 → `alarm` 事件变成 Observation → 触发重评 → 通常就去执行。**智能体是字面意义上"按自己设的闹钟把自己叫醒"去做事。**

**干净的归属切分（与现有解耦一致）：**

| 东西 | 归属 | 类比 |
|---|---|---|
| Agenda、优先级、project、想做什么 | **Soul**（Planning + IntentionState + Mnemos） | 在脑子里记着今天要做什么 |
| 闹钟、到点唤醒 | **Oikos**（`set_timer` / 世界时钟） | 在手机上设了个闹钟 |

纯认知意图可只留在 IntentionState 不设物理闹钟；需要"到点被叫"的就落一个 Oikos 闹钟。

**为什么不会退化（双向封顶，最易出问题处）：**

| 失败模式 | 为何不发生（靠已有机制） |
|---|---|
| 干坐着不动 | idle 让 boredom/curiosity/achievement 持续上涨→张力终会胜出→行动 |
| 兴趣间乱跳(ADHD) | IntentionState 五重惯性 + Identity/Value 慢锚；Agenda 本身是预先承诺装置 |
| 沉迷一事忘了用户/生理 | 生存级 `body_alert` 经 Reflex 硬抢占；社交 need + 用户消息高显著度 |
| 变成死板 cron 机器人 | **Agenda 到点是以 Observation 触发、不是命令**；每项闹钟一响都对当下真实状态重评(P2)。**日程是建议，状态才是主权** |
| 目标漂移/妄想膨胀 | existence_score 锚定 + Value/Identity 稳定 + deadline 临近抬高机会成本 |

> **精髓：它是一份计划，不是一个定时任务。** 闹钟把你唤醒到"重新决定"的时刻，而不是唤醒到"无条件执行"。饿了/病了/用户来了，当下状态可以推翻预定计划——这正是 P2（行为来源于内部状态）在时间维度上的延伸。

### Event（事件总线消息契约）

```python
class Event(Stamped):
    type: EventType                 # 枚举, 见 Part IV Event Bus
    payload: dict                   # 按 type 有对应 schema
    priority: int = 0               # Reflex 类事件高优先级
    causal_parent: UUID | None      # 事件因果链, 用于回放与调试
```

所有事件进入 **append-only Event Log**，这同时是审计日志、调试回放源、以及 Learning 的训练数据来源（event-sourcing 模式）。任意时刻的 InternalState 都可由 Event Log 重放重建——这是可测试性和可观测性的基石。

### State Snapshot（智能体状态存档：更新即存、启动即恢复）★

> Agent 的最高目标是**持续存在**（P1）。持续存在必须跨越进程重启——重启后不能变回一张白纸，而要**接着上次的自己继续活**：同样的人格、情绪、目标、承诺、日程、以及**思维池里正想着的念头**。因此需要一份**智能体状态存档**：随更新自动保存，启动时读取加载恢复。

它与已有的 event-sourcing **不是两套机制，而是同一套的两个面**（与 Oikos / Mnemos 的 `snapshots/` 完全同构）：

- **逐次更新的持久化 = Event Log（已有）。** 每一次 InternalState 分片变更**本就是一个事件**，被 append 到 Event Log——这就是"每次更新自动保存"的真正落点：改动即落盘、可溯源、不丢。
- **快照 = 快速恢复的检查点（本节新增）。** 只靠重放全量 Event Log 冷启动会越来越慢，所以周期性/合并式地把**当前完整 InternalState（含 `thoughts` 思维池、`intention`、`goal`、`agenda`、`identity/value` 慢变量）**物化成一份存档 `SoulSnapshot`。

```python
class SoulSnapshot(BaseModel):
    schema_version: str
    saved_at: float                 # wall-clock + world-time 双时钟
    seq: int                        # 对应 Event Log 的序号(增量重放锚点)
    internal_state: InternalState   # 全部分片, 含 thoughts / intention / goal / value ...
    agenda: Agenda | None           # 当前日程
    invariants_ok: bool             # 保存前状态不变量自检结果
```

**保存策略（"更新即存"的工程解读）：**
- Event Log 逐事件落盘（真正的 per-update 持久化）。
- `SoulSnapshot` 采用**合并写 + 原子替换**（写临时文件再 rename），触发条件：debounced 的状态变更（如"有变更且距上次 ≥N 秒"）、慢变量（identity/value）每次变更、以及**优雅关闭时强制落一次**。避免每个高频 tick 全量序列化的开销，又保证近乎实时。

**启动恢复流程：**
1. 读最新 `SoulSnapshot`（`state/soul.snapshot`）→ 载入 InternalState 与思维池。
2. 重放 Event Log 中 `seq > snapshot.seq` 的尾部事件 → 精确追到掉线前一刻。
3. 校验状态不变量 → 恢复 Persistent Runtime，从"上次的自己"继续。
4. **无存档 = 冷启动**：用配置的种子人格/使命初始化（一次性），此后每次都热恢复。

**错误处理（no-fallback）：** 存档损坏/schema 不兼容 → 回退到上一份可用快照并重放补齐；仍失败则 fail-loud，**绝不静默以空白身份启动**（那等于"换了个 Agent"，违背 P1 的身份连续性）。快照的 `schema_version` 与迁移规则显式化，跨版本不静默丢字段。

---

# Part IV · 模块工程规格

> 每个模块统一规格：**订阅什么 → 产出什么 → 运行频率 → 技术实现 → 错误处理 → 验收标准**。
>
> **全局错误哲学（重要，覆盖全文）：不做 fallback、不做静默降级。** 任何模块遇到错误（LLM 调用失败、超时、解析失败、schema 校验失败、环境断连等）一律 **fail-loud**：立即抛出带完整上下文的异常，发 `ErrorRaised` 事件（含 module、阶段、输入摘要、原始 traceback、相关 event id），写结构化日志，并在终端/Telegram 明确报告。绝不用伪造的低质量结果掩盖错误。只有 Reflex 这一条实时安全回路允许在 LLM 不可用时继续独立工作——但那不是 fallback，而是它本就**不依赖** LLM 的设计。

### Observation Engine

- **订阅：** 原始 sensor/API/text 输入流、Observation Working Memory（仅最近 N 帧滑动窗口）。
- **产出：** `ObservationState`，发 `ObservationUpdated` / `PredictionUpdated`。
- **频率：** 1–10 Hz（按模态可调；视觉高、纯文本低）。
- **实现：** 多层语义分析流水线——对象抽取、实体识别与身份关联、属性/关系/动作/事件抽取、场景理解、可供性分析、空间/时间/社会关系建模、因果假设、意图与风险估计、异常与不确定性估计、世界状态更新。每层是可插拔 stage；轻量层用专用模型（YOLO/embedding/规则），重语义层调 LLM/VLM。
- **预测：** 维护 `Future Observation Trajectory`，形成 **Predict → Observe → Correct** 循环。预测器 MVP 可用 LLM few-shot 生成下一帧分支，进阶用学习到的 World Model（见 Learning）。
- **错误处理：** 任一 stage 出错（LLM 失败/超时、解析失败、schema 不符）→ 立即 `ErrorRaised` 并中止本帧 Observation，明确报告"哪一 stage、什么输入、什么错"，**不输出伪造或降级的 ObservationState**。下游因此感知到"本 tick 无新观察"，而非收到一份不可信数据。
- **验收：** 给定回放输入流，能稳定产出带 confidence 的 ObservationState；预测 trajectory 的 1-step 准确率优于随机基线。

### Reflex System

- **订阅：** `ObservationState.current` + `trajectory`（直接读共享状态，**不经过 Thinking**）。
- **产出：** 高优先级 `ReflexAction` 事件，直达 Action Layer。
- **频率：** 50–200 Hz，运行在 Realtime Kernel 线程，**不依赖 LLM**。
- **实现：** 规则引擎 + 有限状态机 + 控制器 / 预训练 RL Policy。例：预测 300ms 后跌倒→立即 Balance；预测 OOM→立即释放低优先级资源；预测用户即将发消息→预热回复缓存。
- **优先级：** 始终高于 Planning。Reflex 与 Planning 对 Action 的争用由 Action Layer 的优先级仲裁解决（Reflex 抢占）。
- **验收：** 在注入危险预测的回放中，反射动作延迟 < 一个 kernel tick，且在 LLM/网络完全不可用时仍正常触发。

### Internal State Dynamics

- **订阅：** `ObservationUpdated`、`ActionFinished`、`LearningCompleted`、`ReflectionGenerated`。
- **产出：** 更新各 InternalState 分片，发 `NeedChanged` / `EmotionChanged` 等。
- **频率：** 1–5 Hz（情绪、注意力等快变量）；身份/价值观由 Slow Cognition 低频更新。
- **实现：** 每个子状态是一个**动力学方程**（衰减 + 外部冲击 + 耦合项），形如 `s' = decay(s) + impact(events) + coupling(other_states)`。例如 Need 随时间自然增长（饥饿感累积），被满足事件压低；Emotion 受 Prediction Error 与 Goal 进展驱动。系数可配置、可被 Learning 调参。
- **约束：** 这是唯一能决定行为来源的状态层（落实 P2）。

### Motivation Dynamics

- **订阅：** `NeedChanged`、ObservationState、ValueState。
- **产出：** 排序后的 Motivation 集合，胜出者发 `MotivationActivated` 给 Goal Dynamics。
- **实现：** 对每个候选动机计算 `score = f(importance, urgency, cost, benefit, risk, long_term_value)`，全部以 `existence_score` 期望增量为统一量纲。动机间通过 softmax/WTA 竞争。**切换当前活动不走裸 argmax，而走带余量的迟滞触发器**（见 Intention 的切换不等式）：竞争者必须明显超过 `当前活动效用 + Δ_switch + SwitchCost + CommitmentBonus` 才能夺权，打平维持现状——这从数学上消除小波动翻面，是行为稳定性的入口。生存/安全级事件经 Reflex 通道抢占，不受此迟滞约束。

### Goal Dynamics

- **订阅：** `MotivationActivated`、Observation/Prediction、Memory、Identity。
- **产出：** Goal 的创建与生命周期转移，发 `GoalCreated` / `GoalUpdated`；当某 Goal 被选中推进时，**写入 `IntentionState`（建立承诺）**，发 `IntentionCommitted`；优雅收尾时发 `IntentionReleased`。
- **实现：** Goal 不可由外部直接指定（落实约束）；由 Need+Observation+Prediction+Memory+Identity 联合生成。多 Goal 并存，按 priority 动态调度，支持合并（Merged）与放弃（Abandoned）。**承诺管理：** 被激活的 Goal 进入 `IntentionState` 后获得 `commitment` 与 `min_dwell` 保护；`progress` 推进里程碑时维持承诺（目标梯度），到里程碑或被 satiation/紧急需求触发时释放承诺并优雅收尾——而非中途随机切换。

### Planning System

- **订阅：** 活跃 Goal、`ObservationState.trajectory`（**面向未来规划，非仅当前**）、**Capability Registry 的当前 action_catalog** 与按情境检索到的 **Skills**（来自已加载 Domain Pack，作规划先验）。
- **产出：** 分层计划，最终下发 `BehaviorPlan` 给 Action Layer。
- **分层：** Mission（多年方向）→ Long-term Planner（月/周）→ Short-term Planner（日/小时）→ Behavior Planner（秒级序列）→ Action Layer（atomic）。
- **自主日程（Short-term 层的持久化产物）：** Short-term Planner 把当日目标投影成 **`Agenda`**（见 Agenda 节）：为各时间块填 `Goal.scheduled_window`、并经 Oikos `set_timer` 为关键时段设闹钟、回填 `Goal.timer_id`。这是"主动排程"的落点——不是新模块，而是把已有的日/小时层输出**持久化 + 绑世界时钟**。Agenda 项到点由 `alarm` 唤醒、以 Observation 形式触发重评，**是建议非命令**。
- **实现：** 高层用 LLM 做语义分解 + 树搜索，**以检索到的 Skill 步骤/启发式为先验**；低层 Behavior Planner 可用 HTN / behavior tree / 学习到的 policy。计划**只能由当前已加载的 Capability 组成**（catalog 外的动作不可规划），基于预测轨迹做期望收益规划，并随 `PredictionUpdated` 触发重规划（rolling/MPC 风格）。
- **错误处理：** LLM 分解失败/产出不合 schema → `ErrorRaised` 并中止本次规划，明确报告，不下发半成品计划。计划执行中环境偏离预测超阈值是**正常信号**而非错误，触发局部重规划；必要时上抛 Goal Dynamics 调整目标。

### Memory System

- **定位：** Memory 只是存储介质，**不承担认知功能**（Thinking 主动调用 Memory，Memory 不主动影响 Thinking）。
- **类型：** Working / Episode / Semantic / Procedural / Self / Relationship / Reflection / Dream Memory。
- **Memory Manager 职责：** 检索（retrieve）、压缩（compress）、整合（integrate）、遗忘（forget）、反思（reflect）、巩固（consolidate）。
- **实现：** Working Memory = 内存滑窗；Episode = 带 embedding 的事件序列；Semantic = 摘要后的事实条目；Procedural = 技能/policy 注册表，**也是 Domain Pack 的 Skills 落地之处**（加载 Pack 时其 skills 写入 Semantic/Procedural 并向量化，打 `pack_id`/`domain` 标签，卸载时按标签清理）。最简实现统一落在 **SQLite**（结构化）+ **本地向量检索**（embedding 用配置指定模型，见 LLM Gateway）；不引入独立向量数据库服务。遗忘采用时间衰减 + 访问频率 + 重要性评分淘汰；巩固在 Slow Cognition 中批处理。
- **错误处理：** 检索/写入失败 → `ErrorRaised` 明确报告，不返回空结果冒充"无记忆"。

### Thinking Engine

- **订阅：** InternalState（含 `thoughts` 思维池 / 短期记忆队列）、Observation Trajectory、Memory、Goal、World Model。
- **产出：** 主要产物是**写入思维池的新念头**（Thought）与**反思裁决出的一组动作**，以及由此派生的 State Update、Reflection、Memory Update（`consolidate_hint` 念头下沉）、Goal Update、Hypothesis、Belief Update、Planning Suggestion（全部经事件/共享状态写出，不直接调用模块）。
- **思维池是它的工作台（落实思维池动力学）：** 每 tick 读当前 `thoughts.active` + 观察 + 检索到的记忆 → 生成/推进/联想出新念头写回池 → 抬升被涉及念头的激活、令其余按 `decay` 衰减 → 池满时把最低激活念头淘汰（`consolidate_hint` 者写 Mnemos，否则淡忘）。**思考发生在池里（内部状态），值得留的结果才进记忆——这条边界是硬的。**

- **两轮思考循环（Two-Pass Think Cycle）★——每次思考不是一次性吐结论，而是"快思考 → 反思"两轮：**

  1. **快思考（Round 1, fast）：** 读**短期记忆队列**（上轮 `think_summary` + 未消化的 `recall_query`/`recall_result`）+ 当前观察 + `focus` 念头，用小模型（`thinking.fast`）**快速**生成一个候选念头/内心独白——初步判断、直觉、假设。它快、可能错、可能有幻觉，是**原材料**而非结论。

  2. **反思（Round 2, reflect）：** 用较强模型（`thinking.reflect`）对刚才的快思考做**可靠性核验**——它可靠吗？有没有幻觉或无根据的断言？是不是一个真实成立、有依据的想法，还是想当然？基于什么证据？**反思的产物不是又一个念头，而是一组要外化的动作（actions）**：
     - `speak` —— 说话/回复/主动搭话，**或向用户/他人提问确认信息**（落 `send_message`）
     - `recall` —— 主动回忆：向 Mnemos 发一次检索
     - `adjust_goal` —— 调整/新建/放弃目标（经 Goal Dynamics）
     - `remember` —— 把想通的结论下沉 Mnemos
     - `plan` —— 给 Planning 提候选
     - `noop` —— 本轮无需外化，仅继续内省

     **关键：当反思判定"事实不确定、需要进一步确认"时，它不采信快思考的臆测，而是输出 `recall`（自查记忆）或 `speak`-提问（问用户/他人）动作去核实。** 这正是治"把幻觉/想当然当事实"的闸门——不确定就去查、去问，而不是硬编一个答案。

- **短期记忆队列的写回纪律（落实"下次思考用得上"）：** 每完成一轮循环，Thinking **必须**：
  - 把本轮结论压成一句**摘要** `think_summary` 入队 —— 下一轮读得到"我刚想到/判定了什么"，不必从零重来、不空转同一件事；
  - 若本轮触发 `recall`，把**问题**（`recall_query`：为什么查、查什么）与 Mnemos 返回的**结果**（`recall_result`，`pair_ref` 指回该 query）**成对入队**。
  > **为什么问题与结果都要入队（关键）：** 回忆是异步的、可能跨 tick 才回来。只存结果不存问题，下一轮思考会"看到一堆记忆却忘了当初为什么调它、要回答什么"。问答成对入队，思考才能**带着原来的疑问消化查回的信息**，形成 `想 → 存疑 → 查/问 → 据结果再想` 的闭环而非断片。
- **提示词须让模型完全理解该机制（对接 prompts.toml）：** `thinking.fast` / `thinking.reflect` 的提示词显式向模型说明短期记忆队列——告诉它：队列里有你上轮的思考摘要、你发起的回忆问题与查回的答案，你要**基于它们**继续想；你产出的 `recall` 动作会把问题与结果回填队列；且**无论如何都要给出本轮一句话摘要入队**。
- **频率：** 持续运行；无输入时进入自主思考（空闲触发反思、假设生成、好奇心探索、mind-wandering 自发念头），即**不等待 Prompt**。这正是"自己寻找任务/探索兴趣"的发源：空闲时思维池冒出 curiosity/intention_fragment 念头 + 高 Prediction Error 产出"我想搞懂/想做 X"的目标种子，经 Goal Dynamics 成 Goal、经 Short-term Planner 上 Agenda（见 Agenda 节）。**晨间规划/晚间复盘两个常驻仪式即由 Thinking 在其 `recur` 时刻执行。**
- **实现：** LLM 为核心，两轮各用不同尺寸模型（见 LLM Gateway）：Round 1 快思考用小模型（如 Qwen3-4B，绑 `thinking.fast`），Round 2 反思/深度核验用大模型（如 Qwen3-32B，绑 `thinking.reflect`）。具体型号由统一配置文件指定，不写死在代码里。反思发起的 `recall` 走 Mnemos 前台（不依赖 LLM，见 memory.md），因此"去查证"这一步本身稳健、不会被 LLM 超时拖垮。

### Action Layer

- **定位：** 只执行 Atomic Action，不思考、不规划、不记忆；**保持无状态**以确保可替换、可测试、可复用。
- **订阅：** `BehaviorPlan`、`ReflexAction`（高优先级抢占）。
- **产出：** Environment Change，发 `ActionFinished`（含 outcome、实际/预测对比）。
- **实现：** 不内置任何具体动作；每个动作都是从 **Capability Registry** 取到的、由某个已加载 Domain Pack 提供的 Capability（见 Part VII），其 `run()` 是纯函数式 effect（tool call / API / 电机指令），带超时、重试、幂等键、影响分级。**输入签名中禁止出现原始用户输入**（可被 lint 检查，落实 P2）。调用不存在/已卸载的能力 → `ErrorRaised`，不静默忽略。

### Learning System

- **触发：** 每次 `ActionFinished` 立即进入；另有批量离线学习在 Slow Cognition。
- **产出：** Memory Update、Policy Update、World Model Update、Capability Update，发 `LearningCompleted`。
- **核心信号：** Prediction Error。误差越大，学习强度越高，使 Agent 逐步提升预测与决策能力（落实 P3）。
- **实现：** MVP 用 in-context / 经验回放 + 反思总结写回 Memory；进阶用监督微调 World Model、RL 更新 Behavior Policy、技能蒸馏更新 Capability。**经验固化为 Skill：** 当某序列被反复验证有效，Learning 可把它写成一条新的 `*.skill.toml` 存入当前域的 `learned/` skill 库（带 `confidence`，可随后续成败升降），从而"用着用着越来越懂这个域"——这是 Domain Pack 在使用中自我增长的机制（见 Part VII）。

### Runtime Scheduler

- **定位：** 驱动整个系统持续运行的心跳。生命周期中**不存在 Conversation Loop，只有 Persistent Runtime**。
- **实现：** 多频率 tick 调度。维护一张 `{module: (frequency_hz | trigger_condition, last_run, budget)}` 表，每个 tick 检查应运行的模块并投递执行。慢模块在独立 worker pool 异步执行，绝不阻塞 tick。
- **重评是稀有操作（落实行为稳定性）：** 动机/活动级重评**不每 tick 自由竞争**，而是事件触发——需求越阈值、高优先级世界事件、预测误差骤升、当前 Goal 完成/失败、低频兜底定时器（每隔数分钟 world-time 做一次"理智复查"）、**以及 Agenda 项到点的 `alarm`**。承诺态 `min_dwell` 窗口内仅 reflex 级中断可打断。这正是多时间尺度的体现：**感知高频、动机重评低频、活动承诺更慢**，慢回路不被快回路推着抖动。
- **自主排程的时间触发（与 Agenda 接缝）：** Agenda 上的常驻仪式（晨规划/晚复盘）与各时间块，靠 Oikos 闹钟到点把心智唤醒——这是"主动给未来的自己派活"的落点。注意：闹钟唤醒的是**一次重评**（以 Observation 形式），不是无条件执行；当下状态可推翻预定项（P2）。
- **背压与预算：** 当 `ResourceState.compute_budget` 紧张时，调度器自动降频认知回路（先砍慢思考、保留反射与生存相关回路），实现资源自适应——这本身就是 P1 的体现。
- **验收：** 在无任何外部输入下连续运行 ≥ 24h 不崩溃、不无限增长内存、不进入忙等死循环。

### Event Bus

- **架构：** 事件驱动，模块**只能**通过事件总线 + 共享状态通信，禁止直接互调（落实 P4）。
- **实现：** 进程内 `asyncio` pub/sub（单进程，最简实现，不引入 NATS/Kafka 等外部中间件）。`publish/subscribe` 接口保持稳定，未来若需分布式可替换实现而模块无感。
- **标准事件：** `ObservationUpdated`、`PredictionUpdated`、`NeedChanged`、`EmotionChanged`、`ThoughtAdded`、`ThoughtConsolidated`、`RecallRequested`、`RecallCompleted`、`GoalCreated`、`GoalUpdated`、`IntentionCommitted`、`IntentionReleased`、`AgendaRevised`、`AgendaItemDue`、`MemoryUpdated`、`ReflectionGenerated`、`ActionFinished`、`LearningCompleted`、`WorldModelUpdated`、`SnapshotSaved`、`StateRestored`、`ErrorRaised`、`UserMessageReceived`、`AgentMessageSent`、`PackLoaded`、`PackUnloaded`、`CapabilityRegistered` 等。（`RecallRequested`/`RecallCompleted` 由 Thinking 反思发起 `recall` 与 Mnemos 返回时发出，二者的 payload 即回填短期记忆队列的 `recall_query`/`recall_result`。）
- **保证：** 所有事件落 append-only Event Log；支持优先级（Reflex 类优先投递）与因果链追踪（`causal_parent`）。

### LLM Gateway（统一推理接口，全系统唯一 LLM 入口）

- **定位：** 任何模块**不得直接依赖具体 LLM 实现**，只通过本网关访问推理能力。网关在内部抽象出 **Provider（后端）** 与 **Model（型号）** 两层，使"用什么后端、用哪个型号"完全由配置决定，模块无感。
- **接口：** `infer(role: str, variables: dict) -> result`。`role` 标识"哪个认知角色在推理"（如 `observation.extract`、`thinking.reflect`、`planning.decompose`、`chat.reply`）。网关据此查到：该 role 绑定的 **model 别名** → model 别名指向的 **provider + 真实模型名**，并从 `prompts.toml` 取模板，渲染变量后经对应 provider 调用。模块代码里既不出现后端、型号，也不出现提示词文本。
- **Provider 抽象（核心改动）：** 所有后端统一为一个 `LLMProvider` 接口，便于增删与切换：

  ```python
  class LLMProvider(Protocol):
      def chat(self, model: str, messages: list, **opts) -> ChatResult: ...
      def embed(self, model: str, inputs: list[str]) -> list[Vector]: ...
  ```

  内置实现（均为薄封装）：

  | provider 类型 | 适用后端 | 接入方式 | 是否需要 key |
  |---|---|---|---|
  | `openai_compatible` | OpenAI、DeepSeek、Together、vLLM、**LM Studio**、**Ollama**(/v1) 等 | OpenAI 兼容 `/v1` 端点 | 云服务需要；本地填占位 |
  | `ollama_native` | Ollama 原生 API | `/api/chat`、`/api/embeddings` | 否 |
  | `anthropic` | Claude 系列 | Anthropic Messages API | 需要 |

  绝大多数后端（含 LM Studio、Ollama、vLLM、多数云厂商）都走 `openai_compatible`，差异仅在 `base_url` / `api_key` / 模型名——因此切换后端通常**只改配置、不改代码**。`ollama_native`、`anthropic` 等非兼容协议各自单独实现，新增后端只需再加一个 `LLMProvider` 实现并在配置登记。

- **模型别名与角色绑定（两级映射，便于切换）：**
  - `[llm.providers.*]` 声明若干后端实例（每个含 type / base_url / api_key / 超时）。
  - `[llm.models.*]` 声明若干**模型别名**，每个别名指向 `provider + 真实模型名`。
  - `[llm.roles]` 把认知角色绑定到模型别名。
  - 于是"把所有推理从本地 Ollama 切到某云 API"只需改别名指向的 provider；"只把深度反思换成更强模型"只需改一个 role 绑定。

- **角色 → 模型推荐（仅默认值，全部可在配置覆盖；不再绑死 Qwen3）：**

  | 认知角色 | 默认倾向 | 理由 |
  |---|---|---|
  | observation.extract / 高频语义抽取 | 小模型（如 Qwen3-4B / 本地小模型） | 高频、要快、任务结构化 |
  | thinking.fast / 快思考（两轮循环 Round 1） | 小模型（如 Qwen3-4B） | 高频、出原材料、允许粗糙 |
  | chat.reply / 对话回复 | 中模型（如 Qwen3-8B） | 兼顾自然度与速度 |
  | planning.decompose / 行为规划 | 中大模型（如 Qwen3-14B） | 需要较强推理 |
  | thinking.reflect / 反思核验（Round 2）、深度反思、长程规划 | 大模型 / 云端强模型 | 低频、要最强推理与可靠性核验 |
  | embedding / 记忆向量化 | 专用 embedding 模型 | 统一向量空间，全系统须用同一个 |

  说明：默认仍推荐 Qwen3 系列（本地、好部署、覆盖各尺寸），但网关不再硬性限定 Qwen3——任何 provider 下的任何模型都可通过配置接入。唯一硬约束：**embedding 模型一经选定不可中途更换**（否则向量空间不一致，旧记忆失效）。
- **能力：** 统一缓存（按 provider+model+输入哈希）、限流、超时、成本计量（写回 ResourceState）、请求/响应结构化日志。
- **错误处理（无 fallback）：** 超时、连接失败、鉴权失败（401）、返回非法 JSON、不满足期望 schema —— 一律抛出带完整上下文的异常并发 `ErrorRaised`（含 role、provider、base_url、model、渲染后 prompt 摘要、原始响应、错误类型），**不切换到其它 provider/模型、不返回默认值、不静默重试掩盖**（是否做有限次重试由配置显式开关，重试耗尽仍失败则照常 fail-loud）。调用方据此中止当前认知步并明确报告。注意：跨 provider 的"自动切换"正是被禁止的 fallback——切换只能由人改配置完成。

---

# Part V · 配置与提示词管理

> 设计要求：**所有 LLM 后端与型号集中在一个配置文件、所有提示词集中在一个文件**，切换后端/换模型/调提示词都不必动代码。保持最简，不做多环境多 profile 的过度设计。

### 统一配置文件 `config.toml`

单一配置文件承载全部可调项：LLM 后端与型号映射、调度频率、各动力学系数、存储路径、Telegram token、Minecraft 连接等。LLM 部分采用 **provider → model 别名 → role 绑定** 三段式，切后端只改一处。示例骨架：

```toml
[llm]
request_timeout_s = 60
max_retries = 0          # 默认 0 = 不重试不掩盖错误
cache = true

# ── 后端实例：想接什么就在这里登记，可同时存在多个 ──
[llm.providers.ollama]
type = "openai_compatible"            # 走 OpenAI 兼容 /v1
base_url = "http://localhost:11434/v1"
api_key = "ollama"                    # 本地占位

[llm.providers.lmstudio]
type = "openai_compatible"
base_url = "http://localhost:1234/v1" # LM Studio 默认端口
api_key = "lm-studio"                 # 本地占位

[llm.providers.vllm]
type = "openai_compatible"
base_url = "http://localhost:8000/v1"
api_key = "EMPTY"

[llm.providers.openai]
type = "openai_compatible"
base_url = "https://api.openai.com/v1"
api_key = "ENV:OPENAI_API_KEY"        # ENV: 前缀=从环境变量读，避免明文密钥

[llm.providers.anthropic]
type = "anthropic"                    # 非 OpenAI 协议，单独的 provider 实现
base_url = "https://api.anthropic.com"
api_key = "ENV:ANTHROPIC_API_KEY"

# ── 模型别名：把"业务名"映射到 (provider, 真实模型名) ──
# 换后端 = 改这里的 provider 字段；换型号 = 改 model 字段。
[llm.models.fast]
provider = "ollama"
model = "qwen3:4b"
[llm.models.chat]
provider = "ollama"
model = "qwen3:8b"
[llm.models.planner]
provider = "ollama"
model = "qwen3:14b"
[llm.models.deep]
provider = "ollama"
model = "qwen3:32b"
[llm.models.embed]
provider = "ollama"
model = "qwen3-embedding:0.6b"

# ── 角色 → 模型别名：代码里的 role 只认别名，不认后端/型号 ──
[llm.roles]
"observation.extract" = "fast"
"thinking.fast"       = "fast"
"chat.reply"          = "chat"
"planning.decompose"  = "planner"
"thinking.reflect"    = "deep"
"embedding"           = "embed"

[scheduler]
tick_hz = 10
[scheduler.module_hz]
observation = 5
internal_state = 2
motivation = 0.5
planning = 0.2          # 兼有事件触发
thinking = 0.1

[dynamics.need]          # 各 Need 的自然增长/衰减系数，可被 Learning 调参
survival_decay = 0.001
exploration_growth = 0.005

[agenda]                 # 自主日程: 两个常驻仪式的默认世界时刻(可被 Agent 自行改写)
morning_planning = "daily@08:00"   # 晨间规划: 生成今日 Agenda + 设闹钟
evening_review   = "daily@22:30"   # 晚间复盘: 对照计划/写回 Mnemos/兴趣晶化/排明天
# 说明: 这两条只是"出厂默认", 本身是 recur 型 Goal; Agent 可在运行中调整时刻、
# 增删自己的周期目标。Agenda 项到点经 Oikos 闹钟唤醒, 触发重评(非无条件执行)。

[storage]
sqlite_path = "./data/ados.db"
event_log_path = "./data/events.log"
snapshot_path = "./data/soul.snapshot"   # ★状态存档: 更新即合并写、启动即加载恢复
snapshot_min_interval_s = 5              # 合并写节流: 有变更且距上次≥此值才落盘
snapshot_on_shutdown = true              # 优雅关闭时强制落一次
cold_start_seed = "./data/seed.toml"     # 无存档时的种子人格/使命(仅首次)

[interaction.terminal]
enabled = true
[interaction.telegram]
enabled = true
bot_token = "ENV:TELEGRAM_BOT_TOKEN"       # ENV: 前缀表示从环境变量读，避免明文密钥
allowed_user_ids = [123456789]

# ── 具身：连接哪个世界、认领哪具身体（见 world.md / embody.md）──
[embodiment]
enabled = true
world_url = "http://localhost:7000"   # Oikos 世界进程地址
mind_id = "alice"                     # 本心智的标识(用于认领归属/日志)
body_id = "alice"                     # ★主动认领的身体: 本心智清楚知道自己要进哪具身体
auto_attach = true                    # 启动即认领; 失败 fail-loud 不空跑
detach_on_shutdown = true             # 下线前主动释放身体


[packs]
dir = "./packs"                 # Domain Pack 根目录
enabled = ["minecraft"]         # 启用哪些 Pack（按 id）；可运行时热增删
autoload = true                 # 启动时自动加载 enabled 列表
require_permission_review = true # 高影响能力首次使用前需确认

# 各 Pack 的私有配置，键名 = pack id，透传给该 Pack
[packs.config.minecraft]
host = "localhost"
port = 25565
username = "ADOS"
```

> **具身连接是心智的主动行为（对接 world.md W9）：** ADOS 启动时按 `[embodiment]` 主动 `attach(mind_id, body_id)` 认领一具确定的身体——**心智清楚知道"我是 alice，我要进 alice 这具身体"**，而非被动接受。`body_id` 是配置里的显式选择；想换身体就改这一行。认领后，Oikos 的 `WorldObservation` 成为 Observation Engine 的传感源、`list_skills()` 成为 Planning 的 action_catalog（见 Part IV 各模块接缝）。世界里的其它身体可由别的 ADOS 实例或任何读 `embody.md` 的 agent 认领，互不干扰。

约定：密钥一律用 `ENV:VAR_NAME` 间接引用，不写明文。配置加载时做 schema 校验，**缺项/类型错误直接报错退出**（fail-loud，不填默认值掩盖）。新增任务域 = 把符合标准结构的 Pack 放进 `packs.dir` 并加入 `enabled`，无需改任何代码。

### 统一提示词文件 `prompts.toml`

所有提示词模板集中存放，按 `role` 索引，与 LLM Gateway 的 `role` 一一对应。模板用占位符，由网关渲染。示例：

```toml
["observation.extract"]
system = "你是观察引擎。从输入中抽取对象、关系、事件，输出严格 JSON，符合 ObservationFrame schema。"
user = "最近观察窗口:\n{recent_frames}\n\n当前原始输入:\n{raw_input}"

["chat.reply"]
system = "你是 {agent_name}，具有自己的需求、情绪与目标。像真实的人一样自然对话，可以主动发起话题、表达动机、提出计划，而不是被动应答。当前内部状态摘要:\n{internal_state_brief}"
user = "{user_message}"

["planning.decompose"]
system = "将目标分解为可执行的行为序列，每步必须是环境支持的 atomic action，输出严格 JSON。"
user = "目标:{goal}\n当前世界状态:{world_state}\n未来预测:{trajectory}\n可用动作:{action_catalog}"

["thinking.fast"]
system = "你是快思考(两轮思考循环的第一轮)。基于短期记忆队列(你上轮的思考摘要、你发起过的回忆问题与查回的答案)、当前观察与聚焦念头,快速产出一个初步念头/内心独白:直觉判断、假设或疑问即可。允许粗糙、允许不确定——这是原材料,不是结论。若你意识到某处依赖尚未确认的事实,直接把它标成一个疑问。"
user = "短期记忆队列(近→远):\n{short_term_queue}\n\n当前观察:\n{observation}\n聚焦念头:{focus_thought}"

["thinking.reflect"]
system = "你是反思(两轮思考循环的第二轮)。对刚才的快思考做可靠性核验:它可靠吗?有无幻觉或无根据的断言?是真实成立、有依据的想法还是想当然?你的产出不是又一个念头,而是一组要外化的动作(actions),每个动作为严格 JSON,类型限于: speak(说话/回复/或向用户他人提问确认) | recall(向记忆发起检索) | adjust_goal | remember | plan | noop。硬规则:①当事实不确定、需进一步确认时,不得采信快思考的臆测,必须输出 recall 或 speak-提问去核实;②无论如何都要额外产出一条 think_summary(本轮结论的一句话摘要)写回短期记忆队列;③若输出 recall,必须同时给出这次回忆要回答的问题(recall_query),其查回结果将与该问题配对入队供下一轮使用。"
user = "本轮快思考:{fast_thought}\n短期记忆队列:{short_term_queue}\n近期 episode:{episodes}\n预测误差热点:{prediction_errors}\n当前目标:{goals}"
```

改提示词只动这个文件即可热调，无需改代码、无需重新部署逻辑。

---

# Part VI · 交互层（Interaction Layer）

> 要求：只做**一个终端交互** + **可选 Telegram**。交互层是 I/O 适配器，不是认知模块——它把外部消息转成 Observation 投入系统，把 Agent 的输出动作送达用户。严格遵守 P2：用户消息是 Observation，不是直接指令。

### 定位与数据流

```
用户 (Terminal / Telegram)
   │  文本消息
   ▼
Interaction Adapter ──发 UserMessageReceived──► Observation Engine
                                                      │ (转为 ObservationFrame)
                                                      ▼
                                           ...内部状态 → 动机 → 目标 → 规划...
                                                      │
Action Layer 执行 "send_message" 动作 ──发 AgentMessageSent──► Interaction Adapter ──► 用户
```

要点：
- **用户输入不直达回复。** 消息先成为 Observation，经内部状态演化后，"回复用户"是 Agent 可能选择的一个 Action（`chat.reply` 角色），也可能选择不回复、稍后主动找用户、或先去做别的事——这正是"行为来源于内部状态"的体现。
- **主动消息天然支持。** 因为 Thinking/Motivation 持续运行，Agent 可在无人输入时自发产生"想跟用户说点什么/提醒某事/汇报进展"的动机，触发 `send_message` 动作。主动提醒、主动汇报不是特例，而是通用机制的自然结果。
- **终端适配器：** 一个 async stdin 读取 + stdout 输出循环；输入行打包成 `UserMessageReceived`，订阅 `AgentMessageSent` 打印。
- **Telegram 适配器：** 用 long-polling 或 webhook 接收消息（`allowed_user_ids` 白名单），同样转 `UserMessageReceived`；订阅 `AgentMessageSent` 调 sendMessage 推送。两个适配器共用同一套事件契约，可同时启用。
- **错误处理：** Telegram 连接失败/发送失败 → `ErrorRaised` 明确报告（含 chat_id、错误码），不静默丢消息、不假装已送达。

---

# Part VII · 能力库与 Skills 库（Domain Pack 热插拔系统）

> 核心设计：**ADOS 内核是通用 Agent，对"环境/任务域"一无所知。** 一个域的全部"专长"被打包成一个标准格式的 **Domain Pack**，包含四类内容：能力库（Capabilities，可执行代码）、Skills 库（经验知识）、环境适配器（EnvironmentAdapter，可选）、域配置与提示词。Pack 在运行时**热插拔**——不重启进程、不打断 Persistent Runtime。换任务场景 = 换 Pack，认知内核一行不改。这就是"提供标准格式的能力库与 skills 库，Agent 就能直接在该域展开"的实现路径，也是 P6 的落地。

### Domain Pack 的标准结构

一个 Pack 是一个目录（或可分发的归档），结构固定，便于第三方按格式产出：

```
mypack/
├── pack.toml              # 清单：id/version/依赖/能力与skill索引/权限声明
├── capabilities/          # 能力库：可执行代码，注册为 atomic action
│   ├── __init__.py
│   └── *.py               # 每个能力 = 一个无状态函数 + ActionSpec 元数据
├── skills/                # Skills 库：经验知识（声明式，非代码）
│   └── *.skill.toml       # 每个 skill = 触发条件 + 步骤/启发式 + 适用域
├── prompts.toml           # 该域追加/覆盖的提示词（可选）
├── adapter.py             # EnvironmentAdapter 实现（可选；纯任务域可无环境）
└── assets/                # 该域附带的静态资源/示例/few-shot（可选）
```

### Capability（能力库 = 代码）

- **定义：** 一个 Capability 是一段**无状态可执行代码**，对外暴露为一个 atomic action，附带 `ActionSpec` 元数据（名称、入参/出参 schema、前置条件、影响等级、超时）。它是 Action Layer 真正去"执行"的东西。
- **契约：**

  ```python
  class Capability(Protocol):
      spec: ActionSpec                       # 名称、参数 schema、影响分级、前置条件
      def run(self, args: dict, ctx: ExecContext) -> ActionOutcome: ...
  ```

  `ctx` 只暴露受控句柄（如该 Pack 声明并被授权的资源/适配器），**不暴露内核内部模块**，从而 Pack 代码也遵守 P4 解耦。
- **注册：** 加载 Pack 时，其 capabilities 全部注入 **Capability Registry**；`action_catalog()` 即"当前已加载的全部 Capability 的 ActionSpec 集合"。Planning 只能规划目录内动作——于是"在某域只会做该域支持的事"是结构保证，与之前 Minecraft 的约束同源。
- **隔离与安全：** 每个 Capability 在 `pack.toml` 里声明所需权限（文件/网络/子进程/花钱等）。高影响或不可逆动作标 `impact: high`，执行前需确认或限定沙箱（沿用既有 Action 分级授权）。未声明的权限一律拒绝并 `ErrorRaised`。

### Skill（经验知识库 = 知识，不是代码）

- **定义：** 一个 Skill 是**声明式的经验知识**：在什么情境下、为达成什么、推荐怎样的步骤/启发式/注意事项。它不直接执行，而是供 Planning/Thinking 检索后据以规划——相当于把"人类专家经验"喂给认知回路。
- **格式（`*.skill.toml` 示例）：**

  ```toml
  id = "mc.build_shelter"
  domain = "minecraft"
  when = "夜晚将至且无安全居所"                 # 触发情境（语义匹配 + 可选谓词）
  goal = "在天黑前获得可防怪的封闭空间"
  steps = [                                      # 启发式步骤，非硬编码脚本
    "就近收集 ≥4 木头并合成工作台",
    "优先用现有方块挖洞封口，比从零建房更快",
    "留一格放置火把防止内部刷怪",
  ]
  preconditions = ["拥有可挖掘工具或徒手可挖方块"]
  related_capabilities = ["mine_block", "place_block", "craft"]  # 落到能力库
  confidence = 0.8                               # 经验可信度，可被 Learning 调整
  ```

- **存储与检索：** 加载时 skills 写入 **Semantic/Procedural Memory** 并向量化（用既有 embedding 模型），打上 `pack_id` 与 `domain` 标签。Planning/Thinking 按当前 Goal + Observation 语义检索相关 skill，将其作为规划先验。
- **Skill 与 Capability 的关系：** Skill 引用 Capability（`related_capabilities`），即"知道该用哪些能力、怎么组合";Capability 是"真的能做"。两者解耦：同一批 Capability 可被不同 Skill 以不同方式编排。
- **可被学习增长：** Learning System 可把成功的经验固化为**新的 Skill 条目**写回当前 Pack 的 skills（或一个独立的 `learned/` skill 库），实现"用着用着越来越懂这个域"。这与 Procedural Memory 一脉相承。

### Pack Manager（热插拔运行时）

- **职责：** 发现、校验、加载、卸载、热替换 Pack；维护 Capability Registry 与 skill 索引；广播 `PackLoaded` / `PackUnloaded` / `CapabilityRegistered` 事件。
- **加载流程：** 读 `pack.toml` → schema 校验（缺项/越权即拒绝并 `ErrorRaised`）→ 导入 capabilities 注入 Registry → 导入 skills 写入 Memory 并向量化 → 合并该域 prompts → 若有 adapter 则挂载 → 广播 `PackLoaded`。**全过程不重启进程**；新动作下一 tick 即可被 Planning 发现。
- **卸载/热替换：** 卸载时从 Registry 摘除该 Pack 的 capabilities、按标签清理其 skills、卸载 adapter，并发 `PackUnloaded`；正在执行该 Pack 动作时，等待当前动作收尾或安全中止，绝不强杀导致状态损坏。热替换 = 卸载旧版 + 加载新版，二者间内核状态（人格/记忆/目标）保持连续。
- **版本与依赖：** `pack.toml` 声明 `id/version` 与对内核最低版本、对其他 Pack 的依赖；冲突（同名 action、版本不符）在加载期暴露为 `ErrorRaised`，**不静默覆盖**。
- **错误处理（无 fallback）：** 校验失败、能力导入异常、权限越界、依赖缺失 —— 一律 fail-loud 并明确报告是哪个 Pack 的哪一项，**不部分加载、不带病运行**。

### 这如何兑现"换域即用"

给定一个新任务域（如"运维"、"科研助理"、"网页操作"、"机器人"），域提供方只需按标准格式产出：一组 Capabilities（该域能做的原子动作代码）+ 一组 Skills（该域的经验知识）+ 可选的 EnvironmentAdapter（若该域有外部环境要观察/操作）。把 Pack 放入 `packs/` 并启用，Agent 即可：用 adapter 观察该域 → 用该域 skills 作规划先验 → 调用该域 capabilities 行动 → 在该域内学习成长。内核的需求/动机/目标/规划/学习/人格回路完全复用，无需改动。

### 示例：Minecraft 作为一个 Domain Pack

Minecraft 接入不再是特例，而是 Domain Pack 的一个实例，验证整套机制：

- **adapter.py：** 通过 Mineflayer（Node 侧 bot）或等价 Python bot 库连接服务器，把 bot 世界状态/事件桥接给 ADOS（本地 socket/HTTP 跨进程通信）。
- **observe → Observation：** 把玩家视野、附近实体、库存、生命/饥饿值、时间天气、聊天消息映射为 ObservationFrame 的 objects/scene/events/social 图。生命/饥饿/危险生物直接喂给 InternalState 的 survival/safety 维度——"饿了去找吃的、苦力怕逼近会紧张/躲避"是通用动力学的自然产物，而非脚本。
- **capabilities：** move/jump/look、mine_block、place_block、craft、attack、use_item、equip、drop、chat 等，每个是一个 Capability。
- **skills：** 如上面的 `mc.build_shelter`，以及挖矿、合战、夜间避险等经验条目。
- **聊天即对话：** 游戏内玩家聊天经 adapter 变成 `UserMessageReceived`（与 Telegram/终端同一通道），`chat` capability 即 `send_message` 的环境实现。Agent 在游戏内能聊天、应答、主动搭话。
- **像正常玩家一样的行为从何而来：**
  - *主动动机/探索：* Curiosity/exploration Need 持续增长 → 无人指挥时自发探索、挖矿、盖房。
  - *制定计划：* Goal "造庇护所" 经 Planning + 检索到的 build_shelter skill 分解为行为序列，并按对夜晚的预测排优先级。
  - *分配任务/协作：* 多人/多 agent 场景下，把子目标通过 chat 表达为对他人的请求（仍是一个 `send_message` 动作）。
  - *主动提醒：* 预测到"天要黑/血量低/背包满" → Reflex 或快思考触发提醒消息。
- **Reflex 在 Minecraft：** 预测到将受致命伤害/掉入岩浆/夜晚怪物逼近 → 反射层立即规避（逃跑、吃食物、放方块挡路），不等慢思考。
- **错误处理：** bot 断连、指令执行失败 → `ErrorRaised` 明确报告（含动作、bot 状态），不伪装成功。

---

# Part VIII · 分阶段实现路线图

> 原则：**每个阶段都产出一个能持续运行、可观测、可回放的系统**，而不是先攒齐所有模块再点火。先打通"持续存在 + 闭环"，再逐步加深认知。每阶段给出**退出标准（Exit Criteria）**。

### Phase 0 — Skeleton / Heartbeat（骨架与心跳）
搭基础设施：Event Bus（进程内 asyncio）、Shared State Store、Event Log、Scheduler、LLM Gateway（Qwen3 + 统一 `config.toml`/`prompts.toml`）、`ErrorRaised` 全局错误通道、结构化日志、**终端交互适配器**。实现一个"只会 tick + 记录存在指标 + 把任何错误清晰报告到终端"的最小 Agent。
**退出标准：** 空载持续运行 ≥ 24h，tick 稳定，Event Log 可回放重建 InternalState；故意触发 LLM/配置错误时能 fail-loud 并打出完整上下文；终端能收发消息。

### Phase 1 — Minimal Closed Loop（最小认知闭环 + 对话）
打通 `Observation(文本) → InternalState(Need+Emotion) → Motivation → Goal → Planning → Action → Learning`。用户终端消息作为 Observation 进入；`send_message` 作为一个 Action。Memory 只上 Working + Episode（SQLite + 配置指定的 embedding 模型）；Learning 只做"反思写回记忆"。
**退出标准：** Agent 能在无人输入时自发产生并推进目标，也能自然对话与主动发起消息；每个动作可从 Event Log 追到驱动它的 InternalState（`Behavior=f(InternalState)`）。**自主日程的最小验证（依赖 Oikos 闹钟，见 world.md Part VI / Part XI Phase 3）：** 晨间规划仪式能产出一份 `Agenda` 并为关键时段设 Oikos 闹钟；闹钟到点以 Observation 触发重评、Agent 据当下状态决定执行或改期（而非无条件执行）；晚间复盘能把进展写回 Memory 并排出次日草案。

### Phase 2 — Predictive Cognition（预测认知）
为 Observation 加 Future Trajectory（LLM few-shot 预测），Learning 引入 Prediction Error 驱动，初版 World Model 上线，形成 Predict→Observe→Correct 闭环。
**退出标准：** 预测 1-step 准确率随运行时间提升并稳定优于基线；高 Prediction Error 能正确提升对应区域的学习强度与注意力权重。

### Phase 3 — Telegram + Multi-timescale & Reflex（远程交互与反射）
接入 **Telegram 适配器**；分离 Realtime Kernel，落地 Reflex System 与多频率调度。
**退出标准：** 终端与 Telegram 可同时收发并共用同一事件通道；注入危险预测时反射延迟 < 1 tick，且 LLM 全程不可用时 Agent 仍存活并维持反射回路。

### Phase 4 — Domain Pack System + Minecraft（能力/skills 热插拔，首个 Pack）
落地 **Pack Manager + Capability Registry + Skill 检索**，定义并冻结 Pack 标准格式（`pack.toml` / capabilities / skills / adapter / prompts）；以 **Minecraft 作为第一个 Domain Pack** 验证整套机制：世界状态映射为 Observation、生命/饥饿映射到 survival/safety Need、capabilities 经 Registry 暴露、skills 进 Memory 作规划先验、游戏内聊天接入统一对话通道。
**退出标准：** 在 Minecraft 中，Agent 无人指挥时自发探索/采集/建造，按昼夜预测排优先级，能游戏内聊天与主动提醒，危险临近时反射规避——表现像正常玩家；且 Minecraft 的能力与知识**全部来自 Pack，内核无任何 Minecraft 专有代码**。

### Phase 5 — Hot-Plug & Second Domain（热插拔与第二个域，验证通用性）
实现运行时**热加载/热卸载/热替换**；不重启进程地引入一个**与 Minecraft 完全不同的第二个 Pack**（如"网页操作"或"运维助理"），仅靠投放标准格式的 capabilities + skills。
**退出标准：** 运行中加载新 Pack 后，下一 tick 内 Planning 即可发现并使用其能力，Agent 直接在新域展开；卸载时不损坏内核状态（人格/记忆/目标连续）；加载非法/越权 Pack 时 fail-loud 拒绝。**这是"换任务场景只需提供标准 Pack"的最终验收。**

### Phase 6 — Deep Memory & Identity Evolution（深层记忆与人格演化）
补全 Semantic / Procedural / Self / Relationship / Reflection / Dream Memory 与巩固/遗忘；上线 Slow Cognition 的 Identity / Value 演化；Learning 能把成功经验固化为新 Skill 写回 Pack。
**退出标准：** 长期运行（周级）后，可观测到人格画像与价值权重的连续、可解释演化，且保持身份连续性（无突变/人格崩塌）；可见自动新增的 learned skill 提升该域表现。

> **范围说明：** 分布式与多 Agent 暂不在实现范围内（YAGNI）。架构通过事件契约与适配器接口为其预留了可能，但当前目标是**单进程、单 Agent、最简可用**。

---

# Part IX · 评估指标

衡量 ADOS 不能用"答得对不对"，而要用**作为持续动力系统**的指标：

- **Uptime / Liveness：** 连续存活时长、tick 抖动、是否进入死循环或忙等。
- **Prediction Accuracy：** 各 horizon 的轨迹预测准确率与校准度（confidence 是否可信）。
- **Existence Robustness：** 在资源冲击/故障注入下维持 `existence_score` 的能力。
- **Goal Coherence：** 目标的产生—推进—完成率，及目标抖动（无谓切换）频率。
- **Behavioral Traceability：** 任一动作能否从 Event Log 反查到驱动它的 InternalState（P2 合规率）。
- **Memory Quality：** 检索相关性、遗忘合理性、巩固后语义记忆的压缩率与保真度。
- **Identity Continuity：** 人格/价值向量随时间的平滑度与一致性（演化而非突变）。
- **Domain Onboarding：** 投放一个标准 Pack 后，到 Agent 在新域产出有效行为的耗时与改动量（理想：零内核改动、热加载后数 tick 内可用）。
- **Hot-Plug Safety：** 运行中加载/卸载/替换 Pack 时内核状态的连续性（人格/记忆/目标无损）与非法 Pack 的拒绝率。
- **Error Transparency：** 错误是否都以 `ErrorRaised` + 完整上下文暴露，无静默吞错（按注入故障的捕获率衡量）。
- **Cost Efficiency：** 每 tick / 每决策的 token 与算力成本，各模型别名的调用占比与缓存命中率。

---

# Part X · 技术选型（单进程最简实现）

> 原则：最简化、单进程、本地优先、不过度设计。下表即落地选型，不再区分"规模化"列——分布式留待真正需要时再说。

| 关注点 | 选型 | 说明 |
|---|---|---|
| 语言 | Python + asyncio | 单进程异步；Reflex 用独立线程 |
| 事件总线 | 进程内 asyncio pub/sub | 不引入外部消息中间件 |
| 共享状态 | 内存对象 + 周期快照到磁盘 | 配合 Event Log 可重建 |
| 事件日志 | 本地 append-only 文件 | 审计 + 回放 + 学习数据 |
| 记忆存储 | SQLite + 本地向量检索 | 不起独立向量库服务 |
| LLM 推理 | 多后端经 LLM Gateway：API key 云服务 / LM Studio / Ollama / vLLM 等，可在 `config.toml` 切换 | provider+型号均配置注入，默认 Qwen3 本地 |
| Embedding | 配置指定的 embedding 模型（默认 Qwen3-Embedding） | 记忆向量化，选定后不可中途更换 |
| 数据契约 | pydantic v2 | schema 校验，违例 fail-loud |
| 配置/提示词 | `config.toml` / `prompts.toml` | 各一个文件，集中可调 |
| 交互 | 终端 stdin/stdout + Telegram | 共用事件契约 |
| 能力/知识 | Domain Pack（`pack.toml` + capabilities/ + skills/ + adapter/） | 标准格式、运行时热插拔 |
| Pack 加载 | Pack Manager + Capability Registry | 校验/注册/热卸载，违规 fail-loud |
| Minecraft | 作为首个 Domain Pack：Mineflayer/等价 bot 桥接 | adapter 在 Pack 内，内核无专有代码 |
| 可观测性 | structlog 结构化日志 | 错误全量带上下文 |

---

# Part XI · 工程约束（硬性，CI 可校验）

任何行为必须来源于 InternalState；任何规划必须基于未来 Observation 轨迹而非仅当前状态；Observation 必须持续预测未来并维护世界状态；所有模块必须完全解耦（依赖图 CI 校验）；Scheduler 必须持续运行；Memory 仅负责存储；Thinking 负责主动认知；**思维池（Thought Pool）属 InternalState 而非记忆系统，是 Thinking 的工作空间；思考在池中发生，只有 `consolidate_hint` 的念头才下沉写入 Mnemos，Memory 不得反向主动写思维池；思考必须走"快思考→反思"两轮，反思的产物是一组动作（speak/recall/adjust_goal/remember/plan/noop）而非直接采信快思考，且事实不确定时必须以 recall 或提问去核实而不得臆造；短期记忆队列是思维池的队列化工作视图（非新记忆系统），每轮思考须回流一条 think_summary，回忆须将 recall_query 与 recall_result 成对入队，以供下一轮思考使用**；**智能体状态必须可存档：InternalState（含思维池/意图/目标/日程/慢变量）随更新持久化（Event Log 逐事件 + `SoulSnapshot` 合并写检查点），启动时加载最新快照并重放尾部事件恢复到掉线前一刻；存档损坏时回退上一快照或重建、失败即 fail-loud，绝不以空白身份静默启动（P1 身份连续性）**；Action 保持无状态且禁止直接接收原始用户输入；Reflex 始终具最高实时优先级；**活动级行为切换必须经迟滞触发器（承诺 + Δ_switch + 切换成本 + 目标梯度），不得每 tick 裸 argmax；动机重评是事件触发的稀有操作而非每 tick 自由竞争；唯生存/安全级事件经 Reflex 可无视迟滞抢占**；**Agenda（自主日程）只能是 Short-term Planner 的持久化产物而非新模块；日程项到点必须以 Observation 形式触发重评、绝不无条件执行（日程是建议、当下 InternalState 才有主权）；目标/日程只能由内部需求动力学涌现，不得由外部直接写入**；任何模块不得直接依赖具体 LLM 实现或具体后端，只能经 LLM Gateway，后端（API key 云服务 / LM Studio / Ollama / vLLM 等）与型号一律由配置注入；**所有 LLM 后端与型号集中在 `config.toml`、所有提示词集中在 `prompts.toml`，代码中不得出现硬编码后端、型号或提示词文本**；**内核不得内置任何领域动作或领域知识——所有 Capability 与 Skill 只能来自标准格式的 Domain Pack，经 Capability Registry / Memory 运行时注入，且支持热加载/热卸载/热替换而不重启进程**；Pack 越权能力、依赖缺失或同名冲突一律加载期 fail-loud，不部分加载、不静默覆盖；**禁止 fallback 与静默降级（含跨 provider 自动切换），任何错误必须以 `ErrorRaised` + 完整上下文暴露**；所有数据必须带时间戳、置信度、可溯源 provenance；整个系统保持单进程最简实现，不为未实现的分布式/多 Agent 提前设计；整个系统始终围绕持续内部状态动力学运行，而非围绕一次 Prompt 或一次 Task。

---

# Part XII · 风险与缓解

- **算力/成本：** 持续运行的 Qwen3 调用是主要成本。**缓解：** 按角色选最小够用型号（高频用 4B/8B，大模型仅低频反思）、按 role+输入哈希缓存、空闲时调度降频。注意：降频是"少想"，不是"用更差的结果冒充"——不违反 no-fallback。
- **认知失控 / 无限自我强化：** 自主目标可能漂移或自我放大。**缓解：** Value/Identity 作为慢变量提供稳定锚；Goal 抖动滞后；kill-switch + 终端/Telegram 可观测可干预。
- **行为抖动（ADHD）与其反面（固执/上瘾）：** 裸 argmax 会让 Agent 刚开始一件事就被微小波动拉走（如刚坐下玩 MC 又起身）；过强的承诺又会卡死或上瘾。**缓解：** 引入 `IntentionState` 五重惯性（承诺迟滞 + 过程中累积满足 + 具身切换成本 + 事件触发重评 + 情绪自适应阈值）让维持当前行为成为默认、切换需被证明值得；同时用 satiation 边际递减、生存级 Reflex 硬抢占、frustration 解锁给惯性封顶，使稳定是一条**带**而非一个**锁**。承诺强度、迟滞余量、满足时间常数全在配置，可调可单测。
- **状态损坏 / 重启失忆：** 长期运行下状态累积漂移或损坏；重启后可能丢失"上次的自己"。**缓解：** event-sourcing 可重放重建 + `SoulSnapshot` 周期检查点（更新即合并写、优雅关闭强制落盘）+ 状态不变量断言（违反即 fail-loud）；启动=加载最新快照+重放尾部事件恢复；快照损坏则回退上一份或重建，**绝不以空白身份静默启动**——那等于换了个 Agent，违背 P1 身份连续性。
- **思维池膨胀 / 反刍：** 念头无限堆积或陷入负面循环（一直想同一件糟心事）。**缓解：** 池有容量上限 + 激活衰减，低激活念头淘汰（值得留的下沉 Mnemos，否则淡忘）；`worry` 类念头持续高激活可触发 Emotion/frustration 通道与"换个事做"的切换（对接行为稳定性）；反刍本身作为高 Prediction-Error 信号促成反思而非空转。
- **幻觉 / 想当然当事实：** 快思考（小模型、求快）可能编造无根据的断言。**缓解：** 两轮思考循环把"生成"与"采信"分开——Round 2 反思专做可靠性核验，判定事实不确定时强制走 `recall`（查记忆）或 `speak`-提问（问用户/他人）去核实，而非直接采信；且 `recall` 走 Mnemos 前台（不依赖 LLM），核实这一步稳健。问答与摘要回流短期记忆队列，使"查过、确认过什么"在后续思考里可复用、不重复臆测。
- **自主行动安全：** Agent 自主执行外部动作（发消息、Minecraft 破坏方块、潜在花钱）风险不一。**缓解：** Action 目录按影响分级，高影响/不可逆动作需显式确认或限定沙箱；默认选择非破坏性动作。
- **不可信 Pack（热插拔的新增风险）：** Domain Pack 含可执行代码，恶意/有 bug 的 Pack 可能越权、破坏状态或泄露数据。**缓解：** `pack.toml` 显式声明权限，未声明的文件/网络/子进程/花钱能力一律拒绝并 `ErrorRaised`；高影响能力首次使用前需确认（`require_permission_review`）；Pack 代码经受控 `ExecContext` 访问资源、不直接触内核模块；加载期做 schema 与依赖/冲突校验，违规即 fail-loud 拒绝加载。仅加载可信来源的 Pack。
- **慢回路阻塞快回路：** **缓解：** Reflex 运行在独立线程、不依赖 LLM；慢模块异步执行并带超时，超时即 `ErrorRaised` 而非静默挂起。
- **错误被掩盖（本设计刻意规避）：** no-fallback 的代价是错误会更"吵"。**缓解：** 这是有意为之——宁可吵闹地暴露，也不安静地积累隐患；用结构化日志 + 错误分类让"吵"是可读的。

---

# Ultimate Objective

ADOS 最终目标不是实现一个聊天机器人，也不是实现一个 Workflow Agent，而是实现一种新的 Agent 运行范式：一个具有持续内部动力学、持续世界预测、自主目标形成、自主长期规划、自主学习、自主人格演化以及持续存在能力的认知操作系统。Agent 不是一系列 Prompt 组成的流水线，而是一个持续运行、持续预测、持续学习、持续成长的动力系统，其行为始终来源于内部状态的连续演化，而不是外部输入本身。

本 v0.3 文档的作用，是把这一愿景拆解为**可被一个小团队按 Phase 0→6 逐步构建、每步都有退出标准与评估指标、且核心契约（数据模型 + 事件 + 调度 + 配置/提示词文件 + Domain Pack 格式）已明确**的系统。落地基调是**单进程、最简、LLM 多后端可切换（默认 Qwen3 本地）、能力/skills 以标准 Domain Pack 热插拔、no-fallback、错误全暴露**。下一步建议从 Phase 0 的 Skeleton（含终端交互与 fail-loud 错误通道）开始。





