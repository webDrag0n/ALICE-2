# Agent Dynamics Operating System (ADOS)

## Engineering Design Document · v0.3

> 本文档在 v0.1 愿景稿、v0.2 工程化稿基础上，进一步收敛为**可直接落地的最简实现规格**：LLM 经统一网关接入，支持 **API key 云服务、LM Studio、Ollama、vLLM 等多后端、可在 `config.toml` 便捷切换**（默认推荐 Qwen3 系列本地部署）、所有提示词集中在 `prompts.toml`、单进程最简设计、**禁止 fallback 与静默降级（错误一律 fail-loud 全暴露）**、交互层为终端 + 可选 Telegram、并通过环境适配器接入 Minecraft 使通用 Agent 表现得像正常玩家。
>
> 阅读顺序建议：Part I 理念与约束 → Part II 参考架构 → Part III 数据模型（落地核心）→ Part IV 模块规格 → Part V 配置/提示词文件 → Part VI 交互层 → Part VII 环境适配器与 Minecraft → Part VIII 路线图 → Part IX–XII 指标/选型/约束/风险。

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
    value: ValueState               # 价值权重, 影响 motivation 折算
```

**存在指标的量化（落实 P1）：** 定义标量 `existence_score = w·f(resource, safety, health, uptime)`。所有 Need 维度最终都可折算为"对 existence_score 的期望贡献/威胁"，从而让"维持存在"成为可计算的最高效用，而不是一句口号。

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
```

Goal 生命周期是显式 FSM，状态转移由 Goal Dynamics 模块裁决并发出 `GoalUpdated` 事件，转移规则与守卫条件写在配置中、可单元测试。

### Event（事件总线消息契约）

```python
class Event(Stamped):
    type: EventType                 # 枚举, 见 Part IV Event Bus
    payload: dict                   # 按 type 有对应 schema
    priority: int = 0               # Reflex 类事件高优先级
    causal_parent: UUID | None      # 事件因果链, 用于回放与调试
```

所有事件进入 **append-only Event Log**，这同时是审计日志、调试回放源、以及 Learning 的训练数据来源（event-sourcing 模式）。任意时刻的 InternalState 都可由 Event Log 重放重建——这是可测试性和可观测性的基石。

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
- **实现：** 对每个候选动机计算 `score = f(importance, urgency, cost, benefit, risk, long_term_value)`，全部以 `existence_score` 期望增量为统一量纲。动机间通过 softmax/WTA 竞争，支持滞后（hysteresis）避免目标抖动。

### Goal Dynamics

- **订阅：** `MotivationActivated`、Observation/Prediction、Memory、Identity。
- **产出：** Goal 的创建与生命周期转移，发 `GoalCreated` / `GoalUpdated`。
- **实现：** Goal 不可由外部直接指定（落实约束）；由 Need+Observation+Prediction+Memory+Identity 联合生成。多 Goal 并存，按 priority 动态调度，支持合并（Merged）与放弃（Abandoned）。

### Planning System

- **订阅：** 活跃 Goal、`ObservationState.trajectory`（**面向未来规划，非仅当前**）。
- **产出：** 分层计划，最终下发 `BehaviorPlan` 给 Action Layer。
- **分层：** Mission（多年方向）→ Long-term Planner（月/周）→ Short-term Planner（日/小时）→ Behavior Planner（秒级序列）→ Action Layer（atomic）。
- **实现：** 高层用 LLM 做语义分解 + 树搜索；低层 Behavior Planner 可用 HTN / behavior tree / 学习到的 policy。计划基于预测轨迹做期望收益规划，并随 `PredictionUpdated` 触发重规划（rolling/MPC 风格）。
- **错误处理：** LLM 分解失败/产出不合 schema → `ErrorRaised` 并中止本次规划，明确报告，不下发半成品计划。计划执行中环境偏离预测超阈值是**正常信号**而非错误，触发局部重规划；必要时上抛 Goal Dynamics 调整目标。

### Memory System

- **定位：** Memory 只是存储介质，**不承担认知功能**（Thinking 主动调用 Memory，Memory 不主动影响 Thinking）。
- **类型：** Working / Episode / Semantic / Procedural / Self / Relationship / Reflection / Dream Memory。
- **Memory Manager 职责：** 检索（retrieve）、压缩（compress）、整合（integrate）、遗忘（forget）、反思（reflect）、巩固（consolidate）。
- **实现：** Working Memory = 内存滑窗；Episode = 带 embedding 的事件序列；Semantic = 摘要后的事实条目；Procedural = 技能/policy 注册表。最简实现统一落在 **SQLite**（结构化）+ **本地向量检索**（embedding 用 Qwen3-Embedding，见 LLM Gateway）；不引入独立向量数据库服务。遗忘采用时间衰减 + 访问频率 + 重要性评分淘汰；巩固在 Slow Cognition 中批处理。
- **错误处理：** 检索/写入失败 → `ErrorRaised` 明确报告，不返回空结果冒充"无记忆"。

### Thinking Engine

- **订阅：** InternalState、Observation Trajectory、Memory、Goal、World Model。
- **产出：** State Update、Reflection、Memory Update、Goal Update、Hypothesis、Belief Update、Planning Suggestion（全部经事件/共享状态写出，不直接调用模块）。
- **频率：** 持续运行；无输入时进入自主思考（空闲触发反思、假设生成、好奇心探索），即**不等待 Prompt**。
- **实现：** LLM 为核心，按任务选用不同大小的 Qwen3 模型（见 LLM Gateway）：高频快思考用小模型（如 Qwen3-4B），深度反思/长程规划建议用大模型（如 Qwen3-32B）。具体型号由统一配置文件指定，不写死在代码里。

### Action Layer

- **定位：** 只执行 Atomic Action，不思考、不规划、不记忆；**保持无状态**以确保可替换、可测试、可复用。
- **订阅：** `BehaviorPlan`、`ReflexAction`（高优先级抢占）。
- **产出：** Environment Change，发 `ActionFinished`（含 outcome、实际/预测对比）。
- **实现：** 每个 action 是一个纯函数式 effect（tool call / API / 电机指令），带超时、重试、幂等键。**输入签名中禁止出现原始用户输入**（可被 lint 检查，落实 P2）。

### Learning System

- **触发：** 每次 `ActionFinished` 立即进入；另有批量离线学习在 Slow Cognition。
- **产出：** Memory Update、Policy Update、World Model Update、Capability Update，发 `LearningCompleted`。
- **核心信号：** Prediction Error。误差越大，学习强度越高，使 Agent 逐步提升预测与决策能力（落实 P3）。
- **实现：** MVP 用 in-context / 经验回放 + 反思总结写回 Memory；进阶用监督微调 World Model、RL 更新 Behavior Policy、技能蒸馏更新 Capability。

### Runtime Scheduler

- **定位：** 驱动整个系统持续运行的心跳。生命周期中**不存在 Conversation Loop，只有 Persistent Runtime**。
- **实现：** 多频率 tick 调度。维护一张 `{module: (frequency_hz | trigger_condition, last_run, budget)}` 表，每个 tick 检查应运行的模块并投递执行。慢模块在独立 worker pool 异步执行，绝不阻塞 tick。
- **背压与预算：** 当 `ResourceState.compute_budget` 紧张时，调度器自动降频认知回路（先砍慢思考、保留反射与生存相关回路），实现资源自适应——这本身就是 P1 的体现。
- **验收：** 在无任何外部输入下连续运行 ≥ 24h 不崩溃、不无限增长内存、不进入忙等死循环。

### Event Bus

- **架构：** 事件驱动，模块**只能**通过事件总线 + 共享状态通信，禁止直接互调（落实 P4）。
- **实现：** 进程内 `asyncio` pub/sub（单进程，最简实现，不引入 NATS/Kafka 等外部中间件）。`publish/subscribe` 接口保持稳定，未来若需分布式可替换实现而模块无感。
- **标准事件：** `ObservationUpdated`、`PredictionUpdated`、`NeedChanged`、`EmotionChanged`、`GoalCreated`、`GoalUpdated`、`MemoryUpdated`、`ReflectionGenerated`、`ActionFinished`、`LearningCompleted`、`WorldModelUpdated`、`ErrorRaised`、`UserMessageReceived`、`AgentMessageSent` 等。
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
  | chat.reply / 对话回复 | 中模型（如 Qwen3-8B） | 兼顾自然度与速度 |
  | planning.decompose / 行为规划 | 中大模型（如 Qwen3-14B） | 需要较强推理 |
  | thinking.reflect / 深度反思、长程规划 | 大模型 / 云端强模型 | 低频、要最强推理 |
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

[storage]
sqlite_path = "./data/ados.db"
event_log_path = "./data/events.log"

[interaction.terminal]
enabled = true
[interaction.telegram]
enabled = true
bot_token = "ENV:TELEGRAM_BOT_TOKEN"       # ENV: 前缀表示从环境变量读，避免明文密钥
allowed_user_ids = [123456789]


[environment.minecraft]
enabled = false
host = "localhost"
port = 25565
username = "ADOS"
```

约定：密钥一律用 `ENV:VAR_NAME` 间接引用，不写明文。配置加载时做 schema 校验，**缺项/类型错误直接报错退出**（fail-loud，不填默认值掩盖）。

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

["thinking.reflect"]
system = "基于近期经历与预测误差进行反思，更新信念、提出假设、生成可能的新动机。"
user = "近期 episode:{episodes}\n预测误差热点:{prediction_errors}\n当前目标:{goals}"
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

# Part VII · 环境适配器与 Minecraft 接入

> 核心设计：**ADOS 内核是通用 Agent，对"环境"一无所知。** 每个环境（终端世界、Minecraft、未来的机器人/网页）实现同一个 `EnvironmentAdapter` 接口，把环境状态翻译成 Observation、把 Agent 的 atomic action 翻译成环境指令。换环境只换适配器，内核不变——这就是"通用 agent + 接入 Minecraft 后表现得像玩家"的实现路径。

### EnvironmentAdapter 接口

```python
class EnvironmentAdapter(Protocol):
    def observe(self) -> RawObservation: ...        # 拉取环境原始状态
    def action_catalog(self) -> list[ActionSpec]: ...  # 本环境支持的 atomic action
    def execute(self, action: AtomicAction) -> ActionOutcome: ...  # 执行并返回结果
```

内核不内置任何环境动作；可做什么由 `action_catalog()` 在运行时声明，Planning 只能规划目录内的动作。这天然保证"在 Minecraft 里只会做 Minecraft 能做的事"。

### Minecraft 适配器

- **接入方式：** 通过 Mineflayer（Node 侧 bot）或等价的 Python bot 库连接服务器，本适配器把 bot 的世界状态/事件桥接给 ADOS（可用本地 socket/HTTP 在 Python 内核与 bot 进程间通信）。
- **observe → Observation：** 把玩家视野、附近实体、库存、生命/饥饿值、时间天气、聊天消息等映射为 ObservationFrame 的 objects/scene/events/social 图。生命/饥饿/危险生物等直接喂给 InternalState 的 survival/safety 维度——于是"饿了去找吃的、有苦力怕逼近会紧张/躲避"成为通用动力学的自然产物，而非脚本。
- **action_catalog：** move/jump/look、mine_block、place_block、craft、attack、use_item、equip、drop、chat 等 atomic action。
- **聊天即对话：** Minecraft 内的玩家聊天经适配器变成 `UserMessageReceived`（与 Telegram/终端同一通道），`chat` 动作即 `send_message` 的环境实现。于是 Agent 在游戏内能聊天、应答、也能主动搭话。
- **像正常玩家一样的行为从何而来：**
  - *主动动机/探索：* Curiosity/exploration Need 持续增长 → 无人指挥时自发去探索、挖矿、盖房子。
  - *制定计划：* Goal "造一个庇护所" 经 Planning 分解为"收集木头→做工作台→做工具→挖石头→搭建"的行为序列，基于对夜晚（怪物）来临的预测安排优先级。
  - *分配任务/协作：* 多人/多 agent 场景下，可把子目标通过 chat 表达为对他人的请求（仍是一个 `send_message` 动作）。
  - *主动提醒：* 预测到"天要黑了/血量低/背包满了" → Reflex 或快思考触发提醒消息。
- **Reflex 在 Minecraft：** 预测到将受到致命伤害/掉入岩浆/夜晚怪物逼近 → 反射层立即触发规避（逃跑、吃食物、放方块挡路），不等慢思考。
- **错误处理：** bot 断连、指令执行失败 → `ErrorRaised` 明确报告（含动作、bot 状态），不伪装成功。

---

# Part VIII · 分阶段实现路线图

> 原则：**每个阶段都产出一个能持续运行、可观测、可回放的系统**，而不是先攒齐所有模块再点火。先打通"持续存在 + 闭环"，再逐步加深认知。每阶段给出**退出标准（Exit Criteria）**。

### Phase 0 — Skeleton / Heartbeat（骨架与心跳）
搭基础设施：Event Bus（进程内 asyncio）、Shared State Store、Event Log、Scheduler、LLM Gateway（Qwen3 + 统一 `config.toml`/`prompts.toml`）、`ErrorRaised` 全局错误通道、结构化日志、**终端交互适配器**。实现一个"只会 tick + 记录存在指标 + 把任何错误清晰报告到终端"的最小 Agent。
**退出标准：** 空载持续运行 ≥ 24h，tick 稳定，Event Log 可回放重建 InternalState；故意触发 LLM/配置错误时能 fail-loud 并打出完整上下文；终端能收发消息。

### Phase 1 — Minimal Closed Loop（最小认知闭环 + 对话）
打通 `Observation(文本) → InternalState(Need+Emotion) → Motivation → Goal → Planning → Action → Learning`。用户终端消息作为 Observation 进入；`send_message` 作为一个 Action。Memory 只上 Working + Episode（SQLite + Qwen3-Embedding）；Learning 只做"反思写回记忆"。
**退出标准：** Agent 能在无人输入时自发产生并推进目标，也能自然对话与主动发起消息；每个动作可从 Event Log 追到驱动它的 InternalState（`Behavior=f(InternalState)`）。

### Phase 2 — Predictive Cognition（预测认知）
为 Observation 加 Future Trajectory（Qwen3 few-shot 预测），Learning 引入 Prediction Error 驱动，初版 World Model 上线，形成 Predict→Observe→Correct 闭环。
**退出标准：** 预测 1-step 准确率随运行时间提升并稳定优于基线；高 Prediction Error 能正确提升对应区域的学习强度与注意力权重。

### Phase 3 — Telegram + Multi-timescale & Reflex（远程交互与反射）
接入 **Telegram 适配器**；分离 Realtime Kernel，落地 Reflex System 与多频率调度。
**退出标准：** 终端与 Telegram 可同时收发并共用同一事件通道；注入危险预测时反射延迟 < 1 tick，且 LLM 全程不可用时 Agent 仍存活并维持反射回路。

### Phase 4 — Minecraft Embodiment（Minecraft 接入，像玩家一样）
实现 `EnvironmentAdapter` 接口与 **Minecraft 适配器**：世界状态映射为 Observation、生命/饥饿映射到 survival/safety Need、atomic action 目录、游戏内聊天接入统一对话通道。
**退出标准：** 在 Minecraft 中，Agent 无人指挥时自发探索/采集/建造，能根据昼夜预测安排优先级，能在游戏内聊天与主动提醒，危险临近时反射规避——整体表现像一个正常玩家。

### Phase 5 — Deep Memory & Identity Evolution（深层记忆与人格演化）
补全 Semantic / Procedural / Self / Relationship / Reflection / Dream Memory 与巩固/遗忘；上线 Slow Cognition 的 Identity / Value 演化。
**退出标准：** 长期运行（周级）后，可观测到人格画像与价值权重的连续、可解释演化，且保持身份连续性（无突变/人格崩塌）。

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
- **Error Transparency：** 错误是否都以 `ErrorRaised` + 完整上下文暴露，无静默吞错（按注入故障的捕获率衡量）。
- **Cost Efficiency：** 每 tick / 每决策的 token 与算力成本，各 Qwen3 型号的调用占比与缓存命中率。

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
| Minecraft | Mineflayer/等价 bot 桥接 | 经 EnvironmentAdapter 接入 |
| 可观测性 | structlog 结构化日志 | 错误全量带上下文 |

---

# Part XI · 工程约束（硬性，CI 可校验）

任何行为必须来源于 InternalState；任何规划必须基于未来 Observation 轨迹而非仅当前状态；Observation 必须持续预测未来并维护世界状态；所有模块必须完全解耦（依赖图 CI 校验）；Scheduler 必须持续运行；Memory 仅负责存储；Thinking 负责主动认知；Action 保持无状态且禁止直接接收原始用户输入；Reflex 始终具最高实时优先级；任何模块不得直接依赖具体 LLM 实现或具体后端，只能经 LLM Gateway，后端（API key 云服务 / LM Studio / Ollama / vLLM 等）与型号一律由配置注入；**所有 LLM 后端与型号集中在 `config.toml`、所有提示词集中在 `prompts.toml`，代码中不得出现硬编码后端、型号或提示词文本**；**禁止 fallback 与静默降级（含跨 provider 自动切换），任何错误必须以 `ErrorRaised` + 完整上下文暴露**；所有数据必须带时间戳、置信度、可溯源 provenance；整个系统保持单进程最简实现，不为未实现的分布式/多 Agent 提前设计；整个系统始终围绕持续内部状态动力学运行，而非围绕一次 Prompt 或一次 Task。

---

# Part XII · 风险与缓解

- **算力/成本：** 持续运行的 Qwen3 调用是主要成本。**缓解：** 按角色选最小够用型号（高频用 4B/8B，大模型仅低频反思）、按 role+输入哈希缓存、空闲时调度降频。注意：降频是"少想"，不是"用更差的结果冒充"——不违反 no-fallback。
- **认知失控 / 无限自我强化：** 自主目标可能漂移或自我放大。**缓解：** Value/Identity 作为慢变量提供稳定锚；Goal 抖动滞后；kill-switch + 终端/Telegram 可观测可干预。
- **状态损坏：** 长期运行下状态累积漂移或损坏。**缓解：** event-sourcing 可重放重建 + 周期快照 + 状态不变量断言（违反即 fail-loud）。
- **自主行动安全：** Agent 自主执行外部动作（发消息、Minecraft 破坏方块、潜在花钱）风险不一。**缓解：** Action 目录按影响分级，高影响/不可逆动作需显式确认或限定沙箱；默认选择非破坏性动作。
- **慢回路阻塞快回路：** **缓解：** Reflex 运行在独立线程、不依赖 LLM；慢模块异步执行并带超时，超时即 `ErrorRaised` 而非静默挂起。
- **错误被掩盖（本设计刻意规避）：** no-fallback 的代价是错误会更"吵"。**缓解：** 这是有意为之——宁可吵闹地暴露，也不安静地积累隐患；用结构化日志 + 错误分类让"吵"是可读的。

---

# Ultimate Objective

ADOS 最终目标不是实现一个聊天机器人，也不是实现一个 Workflow Agent，而是实现一种新的 Agent 运行范式：一个具有持续内部动力学、持续世界预测、自主目标形成、自主长期规划、自主学习、自主人格演化以及持续存在能力的认知操作系统。Agent 不是一系列 Prompt 组成的流水线，而是一个持续运行、持续预测、持续学习、持续成长的动力系统，其行为始终来源于内部状态的连续演化，而不是外部输入本身。

本 v0.3 文档的作用，是把这一愿景拆解为**可被一个小团队按 Phase 0→5 逐步构建、每步都有退出标准与评估指标、且核心契约（数据模型 + 事件 + 调度 + 配置/提示词文件 + 适配器接口）已明确**的系统。落地基调是**单进程、最简、LLM 多后端可切换（默认 Qwen3 本地）、no-fallback、错误全暴露**。下一步建议从 Phase 0 的 Skeleton（含终端交互与 fail-loud 错误通道）开始。





