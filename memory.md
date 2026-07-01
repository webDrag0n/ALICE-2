# Mnemos · Universal Agent Memory Engine

## Engineering Design Document · v0.1

> 本文档是 [ADOS](idea.md) 的姊妹规格。它把 ADOS Part IV 中"Memory System"一节**抽出为一个独立项目、独立进程**：一个与具体智能体内部状态设计**无关**的通用记忆引擎。核心命题是"**通用 = 机制固定 + 策略可注册**"——内核只实现普适的存储/联想/遗忘/巩固机制，任何智能体的差异（有无情感、有无目标……）全部通过**首次连接时的注册 + LLM 驱动的适配**注入，落盘为与该智能体记忆库绑定的接口描述文件。
>
> 底层是一个**自研图搜索引擎驱动的"增强版双链笔记库"**：万物皆带类型的节点，联想即参数化的图扩散搜索。
>
> 已定的关键取舍（v0.1）：① 记忆系统**自跑 LLM** 做巩固/摘要/反思（结构性认知，非主体性认知）；② 注册维度采用**混合向量化**（语义主向量为骨干 + 维度按需选通道或字段）；③ 进程间通信**从最简协议起步**（localhost HTTP + msgpack）；④ 数据模型保留 `source_agent` 字段为将来的集体记忆**留口**，但 v0.1 **不实现**共享记忆（一智能体一库，物理隔离）。
>
> 阅读顺序：Part I 理念与原则 → Part II 进程架构 → Part III 统一图模型 → Part IV 三大基础接口 → Part V 注册与适配（落地核心）→ Part VI 记忆库格式 → Part VII 记忆协议 → Part VIII 与 ADOS 接合 → Part IX 路线图 → Part X–XII 选型/约束/风险。

---

# Part I · 理念与第一性原则

### Vision

Mnemos 不是一个向量数据库，也不是一个 RAG 库，而是一个**可被任意智能体注册、并据其内部状态自适应的通用联想记忆引擎**。它独立运行、自我维护（衰减、聚类、巩固、反思），对外只暴露一组稳定的"写入 / 整理 / 提取"接口。它的设计目标不是"存下来再搜出来"，而是**像一个会自我整理的认知笔记库**：记忆之间自动结网，调取时按当前状态发生有方向、有深度、可解释的联想。

"通用"的精确含义：**内核永远不内置任何领域概念**。它不知道什么是"情感""目标""社交关系"——这些只是某个智能体注册进来的"维度（dimension）"。同一个引擎，连上有情感的智能体就会按情感联想，连上没情感的就不会，靠的不是分支代码，而是注册数据。

### First Principles

每条原则后附**工程含义（Engineering Implication）**，即对代码结构的硬性约束。这套原则与 ADOS 的解耦/fail-loud/可溯源精神一致，但服务于"独立通用记忆"这一目标。

**M1 · 机制/策略分离（Mechanism vs Policy）。** 内核只实现通用机制：存、链、激活、衰减、巩固、检索。"哪些维度重要、阈值多少、权重几何"全部来自注册，是**数据不是代码**。
*工程含义：* 内核代码里**不允许**出现任何领域词（emotion/goal/...）的硬编码分支；所有维度通过 `dims` 字典与注册清单驱动。可被 lint/测试强制检查。

**M2 · 结构性认知，而非主体性认知（Structural, not Agentive Cognition）。** 记忆系统**可以**对自身内容做衰减、聚类、摘要、巩固、矛盾检测、反思（重组/抽象自己的记忆，且 v0.1 允许调 LLM 完成）；但**绝不**形成动机、目标或驱动外部行为的决策。
*工程含义：* 记忆系统的"反思"输出只能是**新的记忆节点/边**（写回自己的图），不能是"给智能体的指令"。它没有 Need/Goal/Action 概念。这是它与 ADOS 认知内核的清晰分界。

**M3 · 万物皆图中带类型的节点（Everything is a Typed Node）。** episode / semantic / procedural / entity / reflection，以及注册维度的落点，全部是同一张图里的节点或边。
*工程含义：* 不存在多个异构存储；只有一张 `nodes + links` 图。新记忆类型 = 新的 `NodeType` 枚举值，不需要新表。

**M4 · 联想即参数化图遍历（Association is Parametric Graph Traversal）。** 检索是"以种子节点为起点、沿带权类型边的扩散激活"，完全由一组多参数控制。"按某维度联想"不是特例代码，而是给该维度开一个相似通道或一条边类型——靠注册开启。
*工程含义：* 检索内核是一个**带类型导电率、束宽=fanout、深度=hops、按激活与重要性双阈值剪枝的优先队列扩散搜索**，对所有智能体是同一份实现。

**M5 · 适配是数据，不是代码（Adaptation is Data）。** 智能体专属调优全部落在可读、可编辑、可版本化的 manifest 文件里；LLM 在适配时只产出**配置与绑定**，不产出可执行代码。
*工程含义：* 高层接口必须能编译到内核已知的基础参数，且落在允许区间（越界即 clamp + `MemError`）。LLM 适配产物全程可审查、可回滚、可版本化。

**M6 · 全程可溯源、显式失败（Provenance & Fail-Loud）。** 每个节点/边带时间戳、置信度、来源；每次检索可解释（返回激活路径"为什么这些记忆浮现"）；检索/写入/巩固失败一律 fail-loud。
*工程含义：* 复用 ADOS 的 `Stamped` 基类；检索失败抛带完整上下文的 `MemError`，**绝不用空结果冒充"无记忆"**；与 ADOS 的 no-fallback 哲学一致。

**M7 · 进程隔离 + 协议通信（Process Isolation）。** 独立进程，靠一套稳定的记忆协议通信；一个引擎可服务多个智能体，每个智能体一个**物理隔离**的记忆库。
*工程含义：* 内核不依赖任何特定智能体进程；协议接口稳定，传输实现（HTTP/socket/gRPC）可替换而调用方无感。

---

# Part II · 进程与架构

### 定位

Mnemos 是一个**独立守护进程（daemon）**。智能体（如 ADOS）作为**客户端**通过记忆协议连接。一个 Mnemos 进程可同时挂载多个智能体的记忆库，但库与库之间物理隔离（不同目录、不同 SQLite、不同向量索引）。

```
┌──────────────────────────── Mnemos Daemon ────────────────────────────┐
│                                                                        │
│  Protocol Server (localhost HTTP + msgpack, 最简起步)                   │
│    └─ register / remember / recall / reinforce / forget / introspect   │
│                                                                        │
│  Per-Agent Memory Library (挂载多个, 物理隔离)                          │
│    ├─ library_<agent_a>/   ←─ 一智能体一库                              │
│    └─ library_<agent_b>/                                               │
│                                                                        │
│  Core Engines (对所有库共用同一份实现, 策略由各库 manifest 注入)         │
│    ├─ Graph Store           nodes + links (SQLite)                      │
│    ├─ Vector Index          语义主向量 + 注册维度通道 (本地向量检索)      │
│    ├─ Activation Engine     扩散激活检索 (自研图搜索)                     │
│    ├─ Consolidation Worker  衰减/聚类/摘要/反思 (低频, 自跑 LLM)          │
│    └─ Adaptation Engine     注册期 LLM 适配 + 在线参数微调               │
│                                                                        │
│  Infrastructure                                                        │
│    ├─ LLM Gateway (复用 ADOS 同款抽象: provider→model→role)             │
│    ├─ Embedding (锁定模型, 库级不可换)                                  │
│    └─ Structured Logging + MemError 通道 (fail-loud)                    │
└────────────────────────────────────────────────────────────────────────┘
```

### 两条时间线

- **前台（同步，请求驱动）：** `remember` / `recall` / `reinforce` / `introspect`。低延迟，不调或只调轻量模型（embedding）。`recall` 是纯图计算 + 向量检索，**不阻塞在 LLM 上**。
- **后台（异步，自治低频）：** Consolidation Worker 周期性跑衰减、聚类、LLM 摘要、反思、边维护。它**自跑 LLM**（M2），但严格只产出"写回自己图"的节点/边，且全程 append-only 落 `consolidate.log` 可回放。

**关键工程决策：** 前台检索绝不依赖后台 LLM。即使 LLM Gateway 完全不可用，`recall` 仍能基于已有图结构与向量正常返回——这是"记忆调取不会因为一次 LLM 超时而瘫痪"的硬保证（与 ADOS Reflex 不依赖 LLM 同源思想）。后台巩固在 LLM 不可用时 fail-loud 并暂停，不伪造摘要。

---

# Part III · 统一图模型

> 这是 Mnemos 的真正契约。复用 ADOS 的 `Stamped` 基类（id / 双时钟 created_at / source / confidence / provenance / schema_version），确保每条数据可溯源。

### 节点与边

```python
class MemoryNode(Stamped):
    type: NodeType                  # episode|semantic|procedural|entity|reflection|...
    content: str                    # 原文 / 摘要文本
    structured: dict | None         # 可选结构化字段
    embedding: Vector               # 语义主向量(锁定的 embedding 模型产出)
    importance: float               # 初始重要性, 可被使用频率/图中心度修正
    base_level: float               # ACT-R 式基础激活, 随访问衰减/强化
    last_access: float
    access_count: int
    dims: dict[str, Vector | float | str]  # ← 注册维度落点(混合: 通道向量 或 标量/类别字段)
    source_agent: str               # ← 为集体记忆留口; v0.1 永远=本库 agent_id

class MemoryLink(Stamped):
    src: UUID
    dst: UUID
    type: LinkType                  # temporal|causal|semantic|cooccur|elaborates|contradicts|<custom>
    weight: float                   # Hebbian 强化 / 不用则衰减
    directed: bool
```

### 与普通双链笔记（Obsidian/Roam）的区别

1. **边有类型有权重**：不是无差别的 `[[wikilink]]`，而是 `causal/temporal/semantic/...` 各有不同"导电率"。
2. **边自动生长**：由 embedding 相似度、时间共现窗口、LLM 推断的因果/语义关系自动建边，不依赖人手连。
3. **节点有激活动力学**：`base_level` 随近因/频率以对数律衰减，被访问即强化——这是遗忘曲线与"越想越清晰"的物理基础。
4. **维度混合落点（本文档关键取舍）：** 注册维度既可作为**独立 embedding 通道**（如情感 PAD 投影成向量，参与相似度联想），也可作为**结构化字段**（如类别标签，检索时过滤/加权）。具体每个维度落哪种，由适配引擎在注册时决定（见 Part V），混合共存于 `dims`。

### 节点类型语义

| NodeType | 含义 | 主要产生者 |
|---|---|---|
| `episode` | 一段经历/事件原文 | 智能体 `remember` 写入 |
| `semantic` | 摘要后的事实/概念 | Consolidation 聚类 episode 抽象 |
| `procedural` | 技能/做法/启发式 | 智能体写入 或 巩固固化 |
| `entity` | 人/物/地点等实体 | 抽取自 episode, 跨记忆复用 |
| `reflection` | 对自身记忆的再认识 | Consolidation 反思产出(M2) |

---

# Part IV · 三大基础多参数接口

> 内核固定提供三个底座接口，覆盖最基础功能（遗忘曲线、多维动态联想的相关度与深度等）。高层接口都编译到这三者上（Part V）。

### 1) 写入 `remember(payload, params) -> node_id`

- `importance`：显式重要性，或交由系统用轻量估计器打分
- `node_type`：可显式指定，或让系统从内容推断
- `dims_snapshot`：**写入时刻**的注册状态值（如当前情感、当前目标、注意焦点）→ 落 `node.dims`。既是元数据，也是额外相似通道与造边依据
- `auto_link`：`{ sim_threshold, cooccur_window, infer_causal: bool }` — 自动建边策略
- `dedup_merge`：遇到高相似既有节点时，合并强化 还是 新建

写入是同步、低延迟操作：只算 embedding + 入库 + 建即时边；重的聚类/摘要留给后台。

### 2) 整理 `consolidate(params)`（后台自治，低频）

这是记忆系统的"新陈代谢"，自跑 LLM（M2）。可调参数：

- **遗忘曲线**：`retention = f(Δt, access_count, importance, reinforcement)`，幂律/指数衰减。低于阈值的节点**分层降级**而非物理删除：
  - `active → archived`（移出热索引，仍可深检索）→ `compressed`（并入所属 semantic 摘要，原文可丢）→ 仅在 `consolidate.log` 留痕。
- **聚类抽象**：相似 episode 簇 → LLM 摘要成 `semantic` 父节点，原 episode 连 `elaborates` 边。
- **边维护**：常被一起激活的边 **Hebbian 强化**；长期不激活的边衰减；周期性 LLM 推断新的因果/语义边。
- **矛盾检测**：发现 `contradicts` 关系 → 建边并标记，供智能体后续反思（记忆系统只标记，不裁决真伪）。
- 控制项：`batch_size`、`frequency`、`llm_budget`（token 预算上限）。

### 3) 提取 `recall(query, params) -> ranked[Node] + activation_paths`

**多维动态联想的核心。** 你点名的参数全部落位：

| 参数 | 含义 |
|---|---|
| `seed_k` | 第一次联想搜索多少个相似种子节点 |
| `hops` | 联想多少跳 |
| `fanout` | 每个节点每跳向外联想多少个 |
| `importance_threshold` | 重要性低于此值不纳入 |
| `activation_threshold` | 激活低于此值停止继续扩散（剪枝） |
| `edge_type_weights` | 各类型边的"导电率"（语义/因果/情感各占多少） |
| `dim_weights` | 各维度在相关度里的权重（语义 vs 情感 vs 时间…） |
| `hop_decay` | 每跳激活衰减系数 |
| `recency_boost` / `frequency_boost` | 近因/高频加成 |
| `diversity` | MMR 去冗余强度（聚焦 ↔ 发散） |
| `budget` | 最多返回节点数 / token 预算 |
| `seed_dims` | 以哪些维度值作种子匹配（如"当前情感"） |

**检索内核 = ACT-R 激活方程的图扩展版（自研图搜索引擎的算法心脏）：**

```
A(i) = base_level(i)                              # 随近因/频率, 对数衰减
     + Σ_j  A(j) · hop_decay · Σ_t  w_t · S_t(j→i)  # 沿类型 t 的边加权扩散
     + noise
保留:  A(i) ≥ activation_threshold  且  importance(i) ≥ importance_threshold
扩散:  优先队列, 束宽 = fanout, 深度 ≤ hops, 种子 = seed_k 个相似/维度匹配节点
```

它天然**可解释**（返回每个结果的激活路径：从哪个种子、经哪些边、如何衰减到达）、**可调**（全是显式参数）、**可单测**（给定图与参数，结果确定）。

**"动态"在哪里：** `dim_weights` / `edge_type_weights` 不是常量，而是**当前注册状态的函数**。例如智能体 `arousal` 高 → 情感维权重自动抬升 → 自然涌现"情绪一致性回忆"。这层"状态→参数"的绑定由适配层生成（Part V）。

### 反馈 `reinforce(recall_id, useful: bool, notes?)`

提取结果被智能体使用后回传是否有用 → 在线微调多参数 + 强化被证明有用的激活路径上的边（又一条 Hebbian）。这让"用着用着越来越懂这个智能体"成为机制而非口号。

---

# Part V · 注册与适配（落地核心）

> 这是"通用"真正兑现的地方。智能体首次连接时注册，Mnemos 用 LLM 把通用机制**投影**成适配该智能体的形态。适配分**静态（注册期一次）**与**动态（在线持续）**两段，两段都要。

### 注册清单（智能体首连发来 `register`）

```toml
agent_id = "ados-1"
embedding_model = "qwen3-embedding:0.6b"   # 锁定, 终身不可换(否则向量空间失效, 旧记忆失效)

[[state_vars]]                 # 每个会影响记忆的状态变量
name = "emotion"
type = "vector"
dims = ["valence", "arousal", "dominance"]
influences = ["write", "retrieve"]    # 影响写入打标 + 提取联想
cadence = "fast"
desc = "PAD 情感模型。希望相似情感的记忆更易被联想到（情绪一致性回忆）。"

[[state_vars]]
name = "current_goal"
type = "categorical"
influences = ["retrieve"]
cadence = "medium"
desc = "当前活跃目标。希望优先回忆与当前目标相关的经历与教训。"

[[wanted_interfaces]]          # 期望的高层接口(自然语言描述)
desc = "给我当前心情一致的回忆"
[[wanted_interfaces]]
desc = "根据当前目标提醒我相关的过往教训"
```

### 适配引擎（注册期 LLM 分析，只产出配置不产出代码）

LLM 读注册清单，做三件事：

**① 维度落点决策（混合向量化）。** 对每个 `state_var` 判定它落 `dims` 的哪种形态：
- `type=vector` 且 `influences` 含 `retrieve` → 多半建**独立 embedding 通道**（参与相似度联想，联想更强、成本更高）。
- `type=categorical/scalar` → 多半作**结构化字段**（检索时过滤/加权，更省）。
- 二者混合共存，决策与理由写入 `adaptation.md`（可审阅、可改）。

**② 基础接口默认参数预设。** 例如把 `emotion` 绑到 `recall.dim_weights.emotion`，并设为随 `arousal` 动态。

**③ 把每个 `wanted_interface` 编译成"基础接口 + 参数预设 + 状态绑定"的声明式定义：**

```toml
[interfaces.recall_mood_congruent]
base   = "recall"
preset = { seed_k = 12, hops = 2, dim_weights = { semantic = 0.5, emotion = 0.5 } }
bind   = { "dim_weights.emotion" = "f(arousal)", "seed_dims.emotion" = "$state.emotion" }
desc   = "情绪一致性回忆"

[interfaces.recall_goal_lessons]
base   = "recall"
preset = { seed_k = 8, hops = 3, edge_type_weights = { causal = 0.6, semantic = 0.4 } }
bind   = { "seed_dims.current_goal" = "$state.current_goal" }
filter = { node_type = ["episode", "reflection"], importance_min = 0.5 }
desc   = "按当前目标提醒相关教训"
```

**关键安全约束（M5 落实）：**
- 高层接口必须能**编译到内核已知的基础参数**；任何参数越界 → **clamp + 记 `MemError` 警告**，绝不静默执行未知行为。
- LLM 只设计"绑定与预设"，**不写可执行代码**——杜绝注入与不可审查逻辑。
- 重新注册 = 重新适配，结果**版本化**写入新版 `interfaces.toml`，绝不静默改变已有接口行为。冲突（如改了已锁定的 embedding 模型）→ fail-loud 拒绝。

### 动态适配（在线持续，让"适配"不止于注册时）

冷启动时，注册期适配只能给**先验默认**；真正的"懂这个智能体"靠运行中持续校准：

- 智能体对 `recall` 结果回传 `reinforce(useful?)`。
- Mnemos 据此微调那组多参数（哪类边更该导电、阈值高低、各维权重），并强化被证明有用的边。
- 这与 ADOS 里 Skill 自增长同构：**用着用着越来越懂**。微调有界（参数始终落在允许区间），且变更落 `consolidate.log` 可审计、可回滚。

---

# Part VI · 记忆库的格式与结构

> 一个智能体一个库，目录即库，便于隔离、迁移、快照。选型刻意与 ADOS Part X 对齐，使其既能独立存在，又能被 ADOS 无缝当作外部服务接入。

```
library_<agent_id>/
├── manifest.toml      # 库元数据: id / 创建时间 / embedding 模型(锁定) / 内核版本 / schema 版本
├── profile.toml       # 注册清单(state_vars + 描述) —— 适配的【输入】
├── interfaces.toml    # LLM 综合出的高层接口定义(声明式) —— 适配的【产物】
├── adaptation.md      # LLM 适配的分析与理由(人读, 审计/回滚用)
├── graph.db           # SQLite: nodes / links 两表(结构化主存)
├── vectors/           # 本地向量索引(语义主向量 + 各注册维度通道)
├── consolidate.log    # append-only 整理/微调操作日志(可溯源、可回放)
└── snapshots/         # 周期快照, 配合日志可重建
```

- **"接口描述文件"三件套** = `profile.toml`（是什么）+ `interfaces.toml`（怎么调）+ `adaptation.md`（为什么）。三者分离，便于人工审阅与回滚。
- **与 ADOS 对齐的硬约定：** SQLite + 本地向量检索、TOML 配置、append-only 日志、schema 校验缺项即 fail-loud、**embedding 模型创建即锁定终身不可换**。
- **可重建性：** `consolidate.log` + `snapshots/` 使任意时刻库状态可重放重建（event-sourcing 式），是可测试性与可观测性的基石。

---

# Part VII · 记忆协议（Memory Protocol）

> 智能体与 Mnemos 进程之间的契约。**从最简起步：localhost HTTP + msgpack**。接口语义稳定，传输实现（socket/gRPC）将来可替换而调用方无感（M7）。

| 操作 | 方向 | 说明 |
|---|---|---|
| `register(manifest)` | agent → mnemos | 首连注册/重注册；触发适配；返回库句柄与生成的接口清单 |
| `remember(payload, params)` | agent → mnemos | 写入一条记忆，返回 node_id |
| `recall(query, params \| interface_name)` | agent → mnemos | 联想检索；可直接调基础 `recall` 或具名高层接口；返回结果 + 激活路径 |
| `reinforce(recall_id, useful, notes?)` | agent → mnemos | 反馈，驱动在线微调与 Hebbian 强化 |
| `forget(selector, params)` | agent → mnemos | 显式遗忘/降级（受 M2 分层降级语义约束） |
| `annotate(node_id, link)` | agent → mnemos | 显式加边/标注 |
| `introspect(query)` | agent → mnemos | 调试/可观测：返回激活路径、当前参数、库统计 |

- **状态同步：** 智能体在调 `recall` 时随请求带上当前注册状态值（`$state.*`），供 `bind` 表达式求值。这是"动态联想"的输入。
- **错误处理（no-fallback）：** 任一操作失败（向量索引损坏、schema 不符、LLM 巩固失败、库锁冲突）→ 抛带完整上下文的 `MemError` 并结构化记日志，**绝不用空结果或伪造摘要掩盖**。

---

# Part VIII · 与 ADOS 接合

接入后，ADOS [Part IV 的 "Memory System" 模块](idea.md) **退化成一个薄客户端**：把 `InternalState` 的相关分片（need / emotion / attention / identity / goal …）按 Part V 的清单注册进来，ADOS 认知内核**一行不改**——完全符合其 P4(解耦) / P6(可插拔)。

**一个已拍板的设计边界（原 ADOS 文档说"Memory 不思考"，本设计让记忆自跑巩固/反思）：**

采用 **M2 的划界**——记忆系统做**结构性认知**，ADOS 做**主体性认知**：

| 操作 | 归属 |
|---|---|
| 衰减、聚类、把 episode 摘要成 semantic、强化/衰减边、矛盾检测、记忆内反思 | **Mnemos**（自跑 LLM，但只重组自己的图） |
| 产生动机/目标、决定行为、形成驱动智能体的新信念 | **ADOS Thinking**（结论作为新记忆 `remember` 写回） |

这样两边都自洽：Mnemos 是"会自我整理的笔记库 + 图搜索引擎"，不是"会自己拿主意的第二个大脑"。ADOS 原文"Thinking 调用 Memory、Memory 不主动影响 Thinking"依然成立——Mnemos 的自治巩固只改自己的内容，从不主动给 ADOS 推送指令。

**集体记忆留口（不实现）：** `MemoryNode.source_agent` 字段已就位；将来多智能体共享记忆可在协议层加"跨库检索"而不动图模型。v0.1 该字段恒等于本库 `agent_id`，一智能体一库物理隔离。

---

# Part IX · 分阶段路线图

> 原则同 ADOS：每阶段产出一个能独立运行、可观测、可回放的系统，附退出标准。

### Phase 0 — 图底座与协议骨架
SQLite `nodes/links` 图、本地向量索引、localhost HTTP + msgpack 协议、`MemError` 全局错误通道、结构化日志。实现 `remember` / 朴素 `recall`（仅向量 top-k，无扩散）。
**退出标准：** 能写入、能按相似度检索、能回放重建库；故意触发 schema/索引错误时 fail-loud 带完整上下文。

### Phase 1 — 扩散激活检索引擎
落地 ACT-R 式图扩散搜索：`seed_k / hops / fanout / 双阈值 / edge_type_weights / hop_decay`，返回激活路径。
**退出标准：** 给定图与参数，检索结果确定且可解释；多跳联想能召回纯向量检索召回不到的相关记忆。

### Phase 2 — 注册与静态适配
`register` 接口、注册清单解析、LLM 适配引擎产出 `interfaces.toml` + `adaptation.md`，维度混合落点（通道 vs 字段），具名高层接口可调用。
**退出标准：** 同一引擎连"有情感"与"无情感"两个 mock 智能体，前者按情感联想、后者不，**全靠注册数据驱动、内核零分支**。

### Phase 3 — 自治巩固（自跑 LLM）
Consolidation Worker：遗忘曲线分层降级、相似 episode 聚类摘要成 semantic、Hebbian 边强化/衰减、矛盾检测。接 LLM Gateway。
**退出标准：** 长跑后 episode 被合理摘要、低价值记忆分层降级、热记忆边增强；LLM 不可用时巩固 fail-loud 暂停而前台 `recall` 不受影响。

### Phase 4 — 动态适配与反馈闭环
`reinforce` 接口、在线参数微调、有用路径 Hebbian 强化、变更落 `consolidate.log`。
**退出标准：** 注入"某类边长期有用/无用"的反馈后，可观测到对应参数有界、平滑地朝预期方向漂移，检索质量随之提升。

### Phase 5 — 接入 ADOS
ADOS Memory 模块替换为 Mnemos 薄客户端，注册 InternalState 维度，验证 Part VIII 的认知边界。
**退出标准：** ADOS 认知内核零改动接入；记忆调取/写回正常；记忆自治巩固不越界产生指令。

> **范围说明：** 集体记忆/跨库共享、分布式部署暂不实现（YAGNI），但 `source_agent` 字段与协议接口已为其留口。

---

# Part X · 技术选型（单进程最简实现）

| 关注点 | 选型 | 说明 |
|---|---|---|
| 语言 | Python + asyncio | 单进程异步；与 ADOS 一致便于共用 LLM Gateway |
| 协议传输 | localhost HTTP + msgpack | 最简起步；语义稳定，后续可换 socket/gRPC |
| 图存储 | SQLite（nodes / links 两表） | 不起独立图数据库 |
| 向量检索 | 本地向量索引（语义主向量 + 维度通道） | 不起独立向量库服务 |
| 检索引擎 | 自研 ACT-R 式扩散激活 | 带类型导电率、束宽/深度/双阈值剪枝 |
| LLM 推理 | 复用 ADOS LLM Gateway（provider→model→role） | 巩固/摘要/适配用，配置注入 |
| Embedding | 库级锁定模型（默认 Qwen3-Embedding） | 创建即锁定，终身不可换 |
| 数据契约 | pydantic v2 + `Stamped` 基类 | schema 校验，违例 fail-loud |
| 库格式 | 目录 = 库（manifest/profile/interfaces/graph.db/vectors/log/snapshots） | 隔离、可迁移、可重建 |
| 适配产物 | `interfaces.toml` + `adaptation.md`（声明式） | 可审查、可版本化、可回滚 |
| 可观测性 | structlog 结构化日志 + `introspect` | 错误全量带上下文，检索可解释 |

---

# Part XI · 工程约束（硬性，CI 可校验）

内核不得内置任何领域概念（情感/目标等只能来自注册，无领域硬编码分支）；所有智能体差异只能经注册清单 + 适配产物注入，适配产物只能是配置/绑定而非可执行代码，且必须编译到内核已知基础参数、越界即 clamp+告警；记忆系统只做结构性认知（衰减/聚类/摘要/反思/建边），其一切输出只能是写回自身图的节点/边，**绝不产出动机/目标/行为指令**；前台 `recall` 不得阻塞或依赖后台 LLM；embedding 模型库级锁定，创建后不可更换；每个节点/边必须带时间戳、置信度、可溯源 provenance；每次 `recall` 必须可返回激活路径（可解释）；**禁止 fallback 与静默降级，任何错误以 `MemError` + 完整上下文暴露，绝不用空结果/伪造摘要掩盖**；一智能体一库物理隔离，`source_agent` 为集体记忆留口但 v0.1 恒等于本库 agent_id；整个系统保持单进程最简实现，不为未实现的分布式/集体记忆提前设计。

---

# Part XII · 风险与缓解

- **适配质量不稳定（LLM 生成的接口/绑定不合理）：** **缓解：** 适配产物声明式、落 `adaptation.md` 可人工审阅与改写；参数恒被 clamp 在安全区间；动态反馈持续校准先验偏差。
- **图爆炸 / 检索变慢：** 长跑下节点边无限增长。**缓解：** 遗忘曲线分层降级 + 边衰减控制活跃子图规模；扩散搜索靠双阈值与 fanout/hops 剪枝，复杂度受控；热索引只含 active 节点。
- **巩固漂移 / 记忆损坏：** 自跑 LLM 摘要可能引入错误或语义漂移。**缓解：** 摘要保留对原 episode 的 `elaborates` 边与 provenance（可回溯原文）；`consolidate.log` + 快照可重放重建；摘要失败 fail-loud 不静默写入。
- **embedding 模型误换：** 一旦更换向量空间不一致、旧记忆失效。**缓解：** 库级锁定，`register` 时校验，冲突即 fail-loud 拒绝。
- **状态绑定求值出错（`$state.*` / `f(arousal)`）：** **缓解：** 绑定表达式限定为受控小语言（取值/简单函数），非任意代码；求值失败 fail-loud 而非取默认值掩盖。
- **前台被后台拖慢：** **缓解：** 巩固在独立 worker 低频异步执行并带 LLM 预算上限；`recall` 走纯图+向量路径，物理上不经过巩固 LLM。

---

# Ultimate Objective

Mnemos 的目标不是做一个更好的向量库，而是提供一种**通用的、可被任意智能体注册并自适应的联想记忆基座**：机制普适、策略可注册、联想可解释、自我会整理。它独立于任何智能体的内部状态设计，却能借一次注册 + 持续反馈，长成最贴合该智能体的记忆系统。对 [ADOS](idea.md) 而言，它兑现了"Memory 只是存储介质、认知留在智能体"的承诺，同时把"存储介质"做成一个会自我新陈代谢的活体笔记库。
