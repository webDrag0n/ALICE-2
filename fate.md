# Moira · Narrative Fate & Direction Engine

## Engineering Design Document · v0.1

> 本文档是 [ADOS](soul.md)（心智）、[Oikos](world.md)（身体+世界）、[Mnemos](memory.md)（记忆）的第四个姊妹规格。它回答一个看似矛盾的需求：**让世界与栖居其中的角色，沿着一条预设故事线被引导，却不剥夺心智的自由、不改动心智一行代码。** 核心命题与三个姊妹工程一脉相承——"**引导 = 编排世界 + 渲染感知，而非操纵思想**"。
>
> 一句话定位：**Moira 是世界的"命运"，由两半组成——写手（Writer/编剧）与导演（Director）。** 如果说 ADOS 是心智、Oikos 是身体与世界、Mnemos 是记忆，那么 Moira 就是那个**坐在世界之外、手里攥着故事线、却只能通过布置世界与渲染感官来讲故事的命运**。它不能直接命令角色去爱、去恨、去出门——正如电影剧组不能钻进演员脑子里替他动念。它能做的，是**安排一个让心智的自由天性自然导向故事所需结局的世界**，然后读取心智的反应、不断重新布局。这正是古希腊悲剧的运作方式：俄狄浦斯每一步都自由，命运却必然应验，因为剧作家安排了一个"以他之自由必将走向那里"的世界。
>
> **写手与导演的分工（本版的核心结构）：** **写手只产出剧本（Screenplay）——一个固定格式的、纯声明式的故事制品**（主题/风格/不变量/角色弧/节拍图/张力曲线/结局与衔接规则）；它不碰世界、不碰心智，只"写字"。**导演只执行剧本——把"此刻该让什么情境发生"编译成对世界的编排与对感知的渲染**；它不发明剧情，只在剧本划定的范围内、看着自由心智的真实反应当场调度。**剧本是二者之间唯一的契约**：一份合法的剧本，任何导演都能执行；一个导演，能执行任何合法剧本。正是这道"写/演分离"让下面三种运行模式成为同一套机制的三种接线方式（详见 Part IV）：
> - **模式 A · 写完即演（pipeline）**：写手先写好一段完整剧本 → 交给导演执行。最简单的一锤子买卖。
> - **模式 B · 剧目库（pre-authored library）**：预先写好一系列剧本存进剧目库 → 导演按指定顺序执行某一部；**一部演完可衔接下一部**（剧本声明 `exit` 衔接规则，把结局状态交棒给下一部的 `entry`）。写手在演出时**不在场**。
> - **模式 C · 边演边写（live co-authoring）**：只设定更宏大的**主题/风格/不变量**（一份"开放剧本/种子"）→ 写手与导演**同时在线**：导演把"故事现在到哪了、心智怎么反应了"摘要回传，写手据此**持续续写**新的节拍与分支（流式追加 `ScreenplayDelta`），导演接着执行。故事在演出中被一边写出来。
>
> **为什么这能成立（最关键的一点）：** ADOS 的第一性原则 P2 说"行为只来源于内部状态，用户输入只是 Observation"。这意味着——**任何外力想影响一个解耦的自由心智，唯一的合法入口就是它的感知通道**（Oikos 的 `sense`）。Moira 不去碰 `InternalState`（那会违反 P2、也违反解耦），而是去碰"心智将观察到一个什么样的世界"。心智依旧 `Behavior = f(InternalState)`，只是那个 InternalState 是被一个**精心导演过的世界**喂养出来的。自由没有被剥夺，被布置的是自由所栖身的舞台。
>
> 已定的关键取舍（v0.1）：① 命运是**吸引子，不是轨道**（Attractor, not Rail）——Moira 持有一条目标故事线，但只施加"最小且可信的"扰动把世界拉向它；心智偏离时，Moira 像即兴的 DM 一样**重规划通往同一结局的新路径**，而非把心智掰回剧本；② **可以创造真相，绝不可伪造观察**（Author truth, never falsify perception）——Moira 能往世界里放一封信、安排一场雨、让一个 NPC 来敲门（这些成为世界的真事实），但**绝不能让心智"看见"一件世界里不存在的事**（那会让心智的世界模型与真值分叉，违反 Oikos W7 的 fail-loud）；③ 在"真相"之内，Moira 可**自由渲染显著性、框架与情绪基调**（哪件真事被前景化、以什么气氛呈现）——这是导演的镜头语言，不是说谎；④ **唯一的新接缝在身体的感知管线**：Oikos 的 Observation 出口处新增一个确定性的 **Narration/Salience 渲染级** + 复用既有 Event Scheduler，Soul **零改动**、Oikos 内核**不引入任何 LLM 或剧情逻辑**；⑤ Moira 是**独立进程、自带叙事 LLM**，内部分写手与导演两个可独立运行的子部件，通过一套**特权 Director API** 连 Oikos，心智侧的协议**够不到**这套 API（心智无法感知也无法调用命运）；⑥ **导演把心智当黑箱**：只通过身体在世界中的可见行为（动作/移动/说话）做 Theory-of-Mind 推断，绝不读心智内部——这与"世界把心智当黑箱"同构，正是保护自由的同一道墙；⑦ **过度操纵会被自由心智识破**：ADOS 会预测世界（P3），巧合太多、统计太反常会推高 prediction error，心智会"察觉到现实被摆布"——于是 Moira 受一个**可信度/巧合预算**的硬约束，这约束直接从 P3 长出来，不需额外发明；⑧ 进程间通信沿用三姊妹同款（localhost HTTP + msgpack）；⑨ **禁止 fallback 与静默降级**，任何错误以 `FateError` + 完整上下文 fail-loud。
>
> 阅读顺序：Part I 理念与原则 → Part II 进程架构（写手/导演/三模式） → Part III 剧本格式（写手与导演的固定契约，落地核心）→ Part IV 写手与导演（撰写 / 执行 / 三种运行模式）→ Part V 两类干预手段（编排世界 / 渲染感知）→ Part VI 身体里的那道接缝（Narration 渲染级）→ Part VII Director 协议 → Part VIII 读懂自由心智（Theory of Mind）→ Part IX 与 Soul/Oikos/Mnemos 接合 → Part X 故事格式 → Part XI 路线图 → Part XII–XIV 选型/约束/风险。

---

# Part I · 理念与第一性原则

### Vision

Moira 不是一个剧情脚本引擎，也不是一个对话树，而是一个**驾驭"自由心智 + 自跑世界"这个不可完全预测的系统、把它朝一条故事线引导的闭环控制器**。它的被控对象（plant）是 **Oikos 世界 + 栖居其中的自由心智**；它的设定值（setpoint）是**一条预设的故事线**；它的执行器（actuator）是**对世界的编排**和**对感知的渲染**；它的传感器（sensor）是**身体在世界中的可见行为**。这是一个标准的反馈控制问题，只不过被控对象里含有一个有自由意志、还会反过来预测控制器的智能体——所以控制必须**温柔、可信、且容忍偏离**。

为什么需要把"命运"从世界里单独拆出来？因为 Oikos 被刻意设计成**不思考的纯物理**（world.md：Oikos 不依赖 LLM）。世界会让身体饿、会让门铃响，但它**没有意图**——门铃为什么在此刻响、那封信为什么偏偏今天到、楼下为什么恰好遇见那个人，这些"为什么"属于**叙事意图**，不属于物理。把叙事意图塞进 Oikos 会污染"世界是确定、可回放、可单测的纯物理"这一硬保证（正如 ADOS 把生理塞进认知、被 Oikos 拆出来一样）。所以：

- **Oikos 仍是纯物理**：它只忠实执行"在 (5,8) 制造一次 doorbell"，不关心这是不是命运的安排。
- **Moira 持有全部叙事意图**：它决定"现在该让门铃响了，因为故事需要一个不速之客打断她的独处"，然后通过 Director API 让 Oikos 去物理地实现它。

**"引导"的精确含义：改变概率，不改变自由。** Moira 想让心智走向节拍 B，它做的不是"让心智决定去 B"，而是**让世界变成一个'以这具心智的天性，去 B 是最自然的选择'的世界**：把通往 B 的可供性（affordance）放到它眼前、把 B 的诱因前景化、把背离 B 的路径在物理上变贵。心智依旧自由地 argmax 自己的效用——只是那个效用地形被导演悄悄塑形过。这不是操纵思想，是**操纵思想所面对的世界**。区别至关重要：心智若足够清醒、若天性足够抗拒，它**仍然可以不去 B**——而那一刻，Moira 不会强按，它会重新规划一条通往同一主题结局的新路。**自由是真的，命运也是真的，二者靠"吸引子"而非"轨道"共存。**

### First Principles

每条原则后附**工程含义（Engineering Implication）**，即对代码结构的硬性约束。这套原则与 ADOS 的 P2/解耦、Oikos 的心身分离/fail-loud、Mnemos 的机制策略分离一脉相承，但服务于"在不侵犯自由的前提下引导故事"这一目标。

**F1 · 命运经由感知，不经由心智（Fate via Perception, never via Mind）。** Moira 影响心智的**唯一**合法通道，是心智将观察到的世界——即编排世界真相 + 渲染对真相的感知。它**绝不**写入、读取或旁路心智的 `InternalState`。
*工程含义：* Moira 与心智之间**没有任何直接连接**。它只对 Oikos 说话。心智侧（ADOS）代码里**不存在**任何 Moira 的句柄、事件、字段——心智甚至不知道 Moira 存在（正如演员不直接见到剧本之神）。这与 ADOS P2（行为只来源于内部状态、外部只能经 Observation）可叠加 lint 校验：Moira 的产出必须 100% 落在"世界变更"或"感知渲染参数"上，不得出现任何"心智状态写入"。

**F2 · 故事是吸引子，不是轨道（Storyline is an Attractor, not a Rail）。** Moira 持有目标故事线，但只施加**最小且可信**的扰动把系统拉向它；心智可以偏离，偏离即触发**重规划**（找一条通往同一主题/结局的新路），而非把心智掰回原剧本。
*工程含义：* 剧本必须区分**不变量（主题、结局、关键关系）**与**可变路径（达成它们的具体节拍序列）**。导演是一个 rolling/MPC 式控制器：每个 director tick 重新评估"系统离剧本多远"，只在偏离超阈值时介入，且永远保留多条候选路径。**禁止**任何"强制心智执行某动作"的机制（那是 Oikos 都不允许的——身体只能由世界改写、心智只能自主行动）。

**F3 · 可创造真相，绝不可伪造观察（Author Truth, never Falsify Perception）。** Moira 能让世界里**真的发生**一件事（放一封真的信、安排一场真的雨、让一个真的 NPC 出现），那封信、那场雨、那个人此后就是世界的真值；但 Moira **绝不能**让心智感知到一件世界里并不存在的事，也不能在心智去**核实**时让真值与先前的感知矛盾。
*工程含义：* 这是 Moira 全系统最硬的一条红线，直接继承 Oikos W7（fail-loud、绝不伪造成功、绝不静默瞬移）。Narration 渲染级（Part VI）只能调整**对真实 WorldObservation 的呈现**（显著性/框架/情绪基调/对真正歧义信号的解读），**不能凭空增删世界里的物、人、事件**。要"增"，只能走 Director API 让 Oikos**真的**把它加进世界；于是任何心智后续 `act` 去核实，得到的都是与感知一致的真值——世界模型永不分叉。

**F4 · 干预须落在世界的自然统计内（Interventions stay within Natural Statistics）。** 巧合不能太多、太准、太及时；偏离世界常态越远的干预，越可能被一个会预测世界的心智识破为"被摆布"。
*工程含义：* 这条约束**不是**外加的道德律，而是从 ADOS P3（预测认知）**自动长出来**的工程现实：心智持续预测世界并计算 prediction error，一连串过于凑巧的事件会推高 error、触发"现实可疑"的反思。因此导演维护一个**可信度/巧合预算（plausibility budget）**：每次干预按其"反自然程度"扣预算，预算耗尽则本时段只能用最微弱的感知渲染、不能再安排显眼的世界事件。**自由心智的预测能力，就是命运之手的天然枷锁。**

**F5 · 导演把心智当黑箱（The Director treats the Mind as a Black Box）。** Moira 只能通过身体在世界中的**可见行为**（位置、姿态、动作、说的话、操作的设备）推断心智的处境与倾向，**绝不读取心智内部**。
*工程含义：* Moira 的"传感器"就是 Oikos 的世界状态 + 身体行为日志（它能看到的，和屋里另一具身体能看到的，是同一类东西——可见行为，外加导演视角的全局可见性）。它对"心智在想什么/感觉如何"的判断，全部是 **Theory-of-Mind 推断**（Part VIII），带不确定性、可能猜错。这与"世界把心智当黑箱、靠 observation 交互"是**同一道保护自由的墙**：命运能读懂你的行为，但读不到你的心——所以它永远只能引导，不能确知。

**F6 · 全程可溯源、显式失败（Provenance & Fail-Loud）。** 每次干预都带时间戳、所服务的节拍、所扣的预算、因果链；越界的干预（伪造观察、强写心智、预算透支、试图让真值倒退）一律 fail-loud。
*工程含义：* 复用 `Stamped` 基类；所有干预落 append-only `fate.log`，使"为什么这件事会发生"完全可回放、可审计、可复盘。非法干预抛带完整上下文的 `FateError`（哪个节拍、想做什么、违反哪条红线），**绝不静默执行**。

**F7 · 进程隔离 + 特权协议（Process Isolation & Privileged Protocol）。** Moira 是独立进程；它通过一套**与心智侧协议物理分离的 Director API** 连 Oikos。心智用的 `sense/act/...` 接口里**没有**任何 Director 能力，心智无从调用、无从感知命运。
*工程含义：* Oikos 暴露**两套**协议端点：面向心智的（embody.md 那套，受身体情境门控）与面向导演的（特权，能跨身体、能直接安排世界事件、能设渲染偏置）。两套端点鉴权隔离；导演端点的任何调用都不出现在任何心智的 `sense` 里。一个 Oikos 进程承载一个世界，**至多一个 Moira 导演**连接它（多导演会争夺叙事控制权，v0.1 不允许）。

**F8 · 写演分离，剧本是唯一契约（Writer/Director Separation, the Screenplay is the only Contract）。** 撰写故事（创造内容）与执行故事（驱动世界）是两件不同的事，必须由两个可独立运行的部件承担；它们之间**只**通过一个固定格式的**剧本（Screenplay）**通信。写手只产出剧本（声明式制品），导演只消费剧本并产出干预。
*工程含义：* 写手的输出类型**只能**是 `Screenplay` / `ScreenplayDelta`（纯数据），**绝不**直接调用 Director API、绝不碰世界或心智；导演的输入**只能**是 `Screenplay`（来自文件、剧目库、或写手的在线流），它**绝不**发明剧本里没有的不变量/角色弧（只能在剧本划定的节拍图与 fallback 内调度，遇到剧本未覆盖的偏离则**上抛写手**而非自行杜撰）。这道边界可被类型/lint 校验，且正是"写完即演 / 剧目库 / 边演边写"三模式同构的根因——三者只是写手与导演在时间上如何接线的不同（见 Part IV）。剧本格式版本化、可审查、可回放（与 Mnemos"适配产物是声明式、可版本化"M5 同构）。

---

# Part II · 进程与架构

### 定位

Moira 是一个**独立守护进程（daemon）**，与 ADOS、Mnemos 并列为连接 Oikos 的外部基座——但身份截然不同：心智作为"住户"认领身体连入，**Moira 作为"命运"以特权身份连入**。它不认领任何身体（它不在世界里有手脚），而是俯瞰整个世界、并持有改写世界与渲染感知的特权。Moira 内部一分为二：**写手（Writer）产出剧本，导演（Director）执行剧本**，二者只通过剧本通信（F8）——可同进程协作，也可拆成两个进程分别运行（见 Part IV 三模式）。**只有导演连 Oikos**；写手永远不碰世界，它只面对剧本与（模式 C 下）导演回传的故事摘要。

```
        ┌─────────── Writer (写手/编剧) ───────────┐
        │  读: 主题/风格/不变量(+模式C: 故事摘要)   │
        │  产: Screenplay / ScreenplayDelta (纯剧本)│  自带叙事 LLM(慢, 想"该写什么")
        └───────────────────┬───────────────────────┘
                            │ Screenplay  (唯一契约, F8; 文件/剧目库/在线流)
                            ▼
        ┌─────────── Director (导演) ───────────────┐
        │  读: Screenplay + read_world + ToM        │  自带叙事 LLM(慢, 想"此刻该上哪个节拍")
        │  产: 干预 (编排世界 / 渲染感知)            │  (模式C) 回传 StoryDigest 给写手 ▲
        └───────────────────┬───────────────────────┘
                            │ Director Protocol (特权, 心智够不到)
                            │  stage_event / place / drive_body /
                            │  set_salience_bias / set_world_param / read_world
                            ▼
        ┌──────────── ADOS (Soul) ────────────┐     ┌──────────────────────────────┐
        │  Observation · Need · Goal · ...      │     │        Oikos (World)          │
        │  Behavior = f(InternalState)          │◄────┤  纯物理: 时间/空间/生理/事件   │
        └───────┬───────────────────────────────┘ sense│  ★新增: Narration 渲染级      │
                │ world protocol (sense/act)          │     (确定性应用 Moira 的偏置)  │
                └──────────────────────────────────────►└───────────┬───────────────────┘
                                                                     │ memory protocol
                                                                     ▼
                                                            ┌──────────────┐
                                                            │ Mnemos (记忆) │
                                                            └──────────────┘
```

**四者的职责边界（最重要的一张表，承接 Oikos 的三真值表）：**

| 关注 | 拥有者 | 例子 |
|---|---|---|
| 时间、空间、身体生理、设备、世界事件（物理真值） | **Oikos** | 门铃**在响**、信**在信箱里**、现在**是雨天** |
| 需求、情绪、目标、人格、决策（心理真值） | **ADOS** | 听到门铃**想不想**去开、对那封信**作何感受** |
| 经历、语义、技能经验、反思（记忆真值） | **Mnemos** | 记得上次那个人来访、知道雨天该带伞 |
| **意图：为什么这些事此刻发生、该如何呈现（叙事真值）** | **Moira** | 让门铃**此刻**响（因为故事要一次打断）、把那封信**前景化**（因为它是钩子）、让雨天**显得压抑**（因为这是低谷节拍） |

注意 Moira 的真值是**纯意图性的**：它不拥有任何物理/心理/记忆事实，它拥有的是"故事现在在哪、想去哪、用哪些已有的物理/感知手段去推进"。物理事实的最终真值始终在 Oikos——Moira 只能**请求** Oikos 制造事实，不能凭空宣称事实。

### 进程内部架构

```
┌──────────────────────── Writer Daemon (写手, 可独立进程) ──────────────────┐
│  Screenplay Authoring (撰写剧本: 不变量/角色弧/节拍图/张力曲线/衔接规则)    │
│    └─ 自跑叙事 LLM (writer.draft / writer.continue), 只产出声明式 Screenplay │
│  (模式C) Digest Intake: 订阅导演回传的 StoryDigest → 流式追加 ScreenplayDelta │
│  产出落盘: screenplay_*.toml (剧目库) / 在线 ScreenplayDelta 流              │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ Screenplay (固定格式契约, Part III)
                                    ▼
┌──────────────────────── Director Daemon (导演) ───────────────────────────┐
│  Director Client (连 Oikos 特权端点: read_world / 干预下发)                  │
│  Screenplay Loader (载入剧本; 校验合法性; 剧目库的衔接 entry/exit)           │
│  Story State Tracker (故事现在到哪了: 激活/已完成节拍, 弧进度, 曲线位置)      │
│  Theory-of-Mind Engine (把心智当黑箱, 从可见行为推断; Part VIII)            │
│  Staging Engine (导演大脑, 自跑叙事 LLM; Part IV)                           │
│    ├─ 从剧本"前置已满足的候选节拍"里选下一个该上场的 (state+ToM+张力曲线)    │
│    ├─ 算"系统离剧本多远", 决定要不要介入、介入多重                          │
│    ├─ 维护 Plausibility Budget (可信度/巧合预算, F4)                        │
│    └─ 遇剧本未覆盖的偏离: 模式A/B 走 fallback/降级; 模式C 上抛写手请求续写   │
│  Intervention Planner (把节拍的 setup 编译成可执行干预; Part V)             │
│    ├─ Diegetic   → stage_event / place / drive_body / set_world_param      │
│    └─ Perceptual → set_salience_bias (落到 Oikos Narration 渲染级)          │
│  (模式C) Digest Emitter: 周期/事件触发把 StoryDigest 回传写手 ▲             │
│  Infra: LLM Gateway(复用ADOS) · FateError 通道(fail-loud) · fate.log(可回放)│
└─────────────────────────────────────────────────────────────────────────────┘
```

> **同进程 vs 分进程：** 模式 A/C 下写手与导演常在同一 Moira 进程内（两个 async 部件，走内存里的 Screenplay 对象）；模式 B 下写手**根本不运行**（剧本早已写好躺在剧目库里），只起导演。无论哪种接线，二者之间流动的永远是同一个 `Screenplay` 契约——这正是 F8 让三模式同构的好处。

### 四条时间线（越往上越慢、越抽象，这是有意的）

- **世界 tick（Oikos，最快）**：时间流逝、身体代谢、物理事件——Moira 不参与。
- **认知 tick（ADOS，中速）**：感知→需求→目标→行动——Moira 不参与，只在最后通过感知影响它。
- **导演 tick（Director，慢，事件触发 + 低频兜底）**：导演唯一的节奏。它**不该**每秒都在拨弄世界——好导演大部分时间在**看**。导演 tick 只在以下时机醒来：① 一个节拍的前置/完成条件可能变化（心智做了关键动作、到了某地、说了关键话）；② 张力曲线到了该转折的世界时刻；③ ToM 推断"心智正偏离当前节拍"超过阈值；④ 低频兜底定时器（每隔若干 world-time 复查"故事还在轨道上吗"）。
- **写手 tick（Writer，最慢，仅模式 C 在线）**：写手比导演还慢。模式 A/B 它只在演出前跑一次（或根本不在场）；模式 C 它仅在导演判定"剧本快演到头/出现剧本未覆盖的重大偏离/到了该续写下一幕的张力节点"时被唤醒，吃一份 StoryDigest、续写一段 `ScreenplayDelta`，然后又安静下来。**写手负责"故事走向"这个最慢的变量，恰如 ADOS 里人格/价值观是最慢的慢变量。**

**关键工程决策：Moira 的慢，是自由的保障。** 介入越稀疏，世界越像"自然发生"，可信度预算消耗越慢，心智越不可能察觉被导演。一个每 tick 都在调整显著性的 Moira 会制造一个"处处都是巧合"的诡异世界，反被 ADOS 的 P3 识破。所以**克制是第一美德**，架构上用"事件触发 + 低频兜底"而非"高频轮询"来逼出克制。写手比导演更慢一层，则保证"故事走向"不会被一时的风吹草动频繁改写。

---

# Part III · 剧本格式（Screenplay · 写手与导演的固定契约）

> 这是 Moira 的契约核心，也是写手与导演之间**唯一**的接口（F8）：故事到底以什么固定格式存在，才能既"预设"又"不变成死板脚本"，且**同一份格式能同时支撑写完即演、剧目库衔接、边演边写三种模式**。答案借鉴交互叙事（interactive narrative / drama management）的成熟做法——**剧本不是一条线性脚本，而是一张带前置条件的节拍图（Beat Graph）+ 一组必须守住的不变量（Invariants）+ 一套与别的剧本衔接的规则（entry/exit）**。线性是涌现出来的，不是写死的。

### Screenplay 顶层结构（固定格式，版本化）

```python
class Screenplay(Stamped):             # ★写手的产物 / 导演的输入: 二者唯一契约
    screenplay_id: str
    format_version: str                # 剧本格式版本(向后兼容, 加载期校验)
    title: str
    premise: str                       # 故事前提/世界设定一句话
    theme: str                         # 主题(写手与导演 LLM 共同的北极星)
    style: StyleSpec                   # ★风格: 基调/节奏偏好/题材/允许的强度上限(见下)
    completeness: Literal["closed","open"]  # ★closed=可独立演完; open=种子,需在线续写
    invariants: list[Invariant]        # 不变量: 无论路径怎么变都必须成立的事
    arcs: list[CharacterArc]           # 每个被引导角色的弧线
    beats: list[Beat]                  # 节拍库 (DAG, 非线性序列; open 剧本可起始为空)
    tension_curve: TensionCurve        # 期望的张力随(剧本进度/世界时间)的形状
    ending_conditions: list[Condition] # 故事被视为"已抵达结局"的判定
    entry: EntrySpec | None            # ★衔接: 本剧本承接上一部时的初始状态期望
    exit: list[ExitSpec]               # ★衔接: 本剧本可如何结束 + 各结局衔接哪部下一剧本
    bindings: BindingSpec              # 绑到哪个 Oikos 世界 / 哪些 body_id (见 Part X)

class StyleSpec(BaseModel):            # 风格与边界(写手据此创作, 导演据此约束执行)
    tone: str                          # "温情/悬疑/荒诞/史诗..."
    pacing: str                        # "舒缓/紧凑/张弛交替"
    genre: list[str]
    max_intervention_strength: Literal["micro","normal","strong"]  # 本剧风格容许的最强干预
    content_bounds: list[str]          # 题材红线(此剧不该出现的内容; 叠加全局安全红线)

class Invariant(BaseModel):            # 命运的"必然", 路径可变、它不可变
    id: str
    desc: str                          # "Alice 终将得知那封信的真相"
    kind: Literal["must_happen","must_not_happen","relationship","ending"]
    deadline_world: float | None       # 可选的世界时刻软/硬截止
    hardness: float                    # [0,1] 多硬: 1=无论如何必须达成, 低=尽量

class CharacterArc(BaseModel):
    body_id: str                       # 这条弧绑定世界里的哪具身体
    from_state: str                    # 起点的人设/处境描述(语义)
    to_state: str                      # 弧线终点(如"从封闭到敢于信任")
    milestones: list[str]              # 弧线上的里程碑(语义节点)
```

### Beat（节拍）：剧本的"原子叙事单元"★

> **一个 Beat 不是一段被强制播放的剧情，而是"一个被期望发生的情境 + 唤起它的杠杆 + 判断它有没有发生的条件"。** 这是整个设计避免"死板脚本"的关键：写手写的是**情境与杠杆**，导演布置情境，发生与否交给自由心智。

```python
class Beat(Stamped):
    id: str
    desc: str                          # 这个节拍想达成的戏剧情境(语义)
    serves: list[str]                  # 服务于哪些 invariant / arc milestone (引用 id)
    preconditions: list[Condition]     # 何时这个节拍"可以上场"(故事状态/世界状态)
    # ── 杠杆: 导演用哪些手段去"诱发"这个情境(全是 Part V 的合法干预) ──
    diegetic_setup: list[InterventionTemplate]   # 编排世界: 放信/安排来客/调天气...
    perceptual_setup: list[SalienceBiasTemplate]  # 渲染感知: 前景化/情绪基调...
    # ── 判定: 这个节拍算不算"成了" ──
    success_when: list[Condition]      # 心智自由地做出了期望方向的反应 → 节拍达成
    failure_when: list[Condition]      # 心智明确偏离 → 触发重规划/上抛写手
    emotional_target: PAD | None       # 期望在心智身上唤起的情绪基调(只是目标,非强制)
    tension: float                     # 此节拍在张力曲线上的高度
    next_beats: list[str]              # 达成后可解锁的后继节拍(DAG 边)
    fallback_beats: list[str]          # ★偏离时可改走的替代节拍(通往同一 invariant)
    author: Literal["pre","live"] = "pre"  # ★pre=演前写好; live=模式C演出中续写的
```

`Condition` 是一个对**世界真值 + 故事状态 + ToM 推断**求值的受控谓词（不是任意代码，是受控小语言，与 Mnemos 的 `bind` 表达式同构）：`body.at_room == "kitchen"`、`tom(alice).likely_read_letter > 0.6`、`beat("first_encounter").done`、`world_phase == "night"`。

### 剧本的两种完整度：closed（可独演）与 open（种子，需续写）★

剧本格式同时支持两种完整度，这正是模式 A/B 与模式 C 的格式基础：

- **`completeness="closed"`（闭合剧本）**：节拍图完整、有明确 `ending_conditions`，导演**单凭这一份就能把故事演到结局**，无需写手在场。模式 A/B 用的都是闭合剧本。
- **`completeness="open"`（开放剧本/种子）**：只写定 `theme`/`style`/`invariants`（也许加几个起始节拍），`beats` 可能近乎为空、无明确结局。它**不能独立演完**，必须由在线写手随演出持续续写（追加 `ScreenplayDelta`）。模式 C 从一份开放剧本起步。加载期校验：导演若被交一份 `open` 剧本却没有在线写手相连 → `FateError`（演不下去，fail-loud，绝不硬演一个没写完的故事）。

### 剧本衔接：entry / exit（让一部演完接下一部）★

```python
class ExitSpec(BaseModel):             # 本剧本的一种结局 + 它衔接哪部下一剧本
    when: list[Condition]              # 满足何条件视为以此结局收场
    ending_tag: str                    # 这个结局的语义标签("和解收场"/"决裂收场")
    handoff: dict                      # ★交棒给下一部的状态摘要(哪些关系/事实/弧位置带走)
    next_screenplay: str | None        # 衔接的下一部剧本 id (剧目库中); None=故事到此为止

class EntrySpec(BaseModel):            # 本剧本承接上一部时, 对初始状态的期望/适配
    expects: list[Condition]           # 期望承接时世界/关系已处于何状态
    on_mismatch: Literal["adapt","reject"]  # 不匹配时: 自适应开场 或 拒绝衔接(FateError)
```

衔接是**状态交棒**，不是简单拼接：上一部的 `exit.handoff`（带走"他们已经和解了""那封信已读"这类关系/事实/弧线位置）喂给下一部的 `entry.expects`。导演在剧目库模式下据此把多部闭合剧本串成一条更长的故事线——**一部演完，按实际走到的是哪个 `exit`，衔接对应的 `next_screenplay`**（不同结局可接不同续集，于是剧目库本身也是一张图，不是死序列）。

### ScreenplayDelta：模式 C 的流式增量（写手在线续写）★

```python
class ScreenplayDelta(Stamped):        # 写手在演出中追加给导演的增量(只增不改史)
    screenplay_id: str
    base_version: str                  # 基于哪个剧本版本续写(乐观并发)
    add_beats: list[Beat]              # 新写的节拍(author="live")
    add_invariants: list[Invariant]    # 偶尔追加的新不变量(谨慎)
    revise_tension: TensionCurve | None
    set_ending: list[Condition] | None # 终于决定怎么收场时, 补上结局条件
    rationale: str                     # 写手为何这样续写(写进 fate.log, 可复盘)
```

**Delta 的硬约束（保护已发生的故事）：** 只能**追加**新节拍/分支、**收紧/补全**结局，**不能改写已经执行过的节拍、不能撤销已发生在世界里的事**（世界真值归 Oikos，写手碰不到，正如它碰不到心智）。这与 Mnemos"巩固只追加、不篡改原 episode"、事件溯源"只 append"一脉相承——**故事可以边走边写，但写过的、演过的，算数。**

### 为什么这套格式既预设又自由

- **预设**：写手写下主题、风格、不变量、结局/衔接、和一库节拍。"Alice 终将直面那封信"是 invariant，**必然**被守护。
- **自由**：从当前节拍到下一个，走哪条边、何时走、甚至临时改走 `fallback_beats`，都由**导演**看着心智的真实反应**当场决定**；模式 C 下连"接下来有哪些节拍"都可由写手随心智反应续写。
- **这正是 F2（吸引子非轨道）的数据落地**：invariant 是吸引子中心，beats 是通往它的多条河道，心智的自由决定水流走哪条——但海洋（结局）是写手定的。

### 张力曲线（节奏，不是内容）

`TensionCurve` 描述"故事的情绪强度该画出怎样的形状"（经典的起-承-转-合 / 多幕峰谷）。它**不规定发生什么**，只规定**此刻该紧张还是该松弛**。导演选节拍时优先选 `tension` 匹配当前曲线位置的节拍——于是即使内容因心智自由而千变万化，**节奏感**仍被守住。这把"会讲故事"拆成可分别工程化的两件事：**讲什么**（节拍图 + 不变量，写手的活）与**何时起伏**（张力曲线，写手定、导演守）。

---

# Part IV · 写手与导演（撰写 / 执行 / 三种运行模式）

> 这一节把"命运"拆成两个角色，并讲清它们如何接线成三种运行模式。**写手负责"讲什么故事"（产出剧本），导演负责"如何把故事演到自由心智身上"（执行剧本）。** 二者只经 Screenplay 通信（F8）。先讲两个角色各自做什么，再讲三种模式如何把它们接起来。

## A · 写手（Writer · 撰写剧本）

> 写手是 Moira 里**唯一创造故事内容**的部件，对应一个剧作家。它的输入是**主题/风格/不变量**（人给的创作纲领）外加（模式 C 下）导演回传的故事现状摘要；它的输出**只有剧本**——`Screenplay`（一次写完）或 `ScreenplayDelta`（在线续写）。它**永不**碰世界、碰心智、碰 Director API（F8）。

写手自跑叙事 LLM，两个角色：
- `writer.draft`：从创作纲领（主题/风格/不变量/角色弧 + 可选的世界设定）**冷起草**一份完整闭合剧本（节拍图 + 张力曲线 + 结局/衔接）。用于模式 A/B 的演出前撰写。
- `writer.continue`：吃一份 `StoryDigest`（导演回传：故事到哪了、心智怎么反应、哪些不变量还悬着、张力曲线到哪了），**续写**一段 `ScreenplayDelta`（追加新节拍/分支、必要时补结局）。用于模式 C 的边演边写。

**写手 LLM 只产出声明式剧本，不产出可执行代码、不直接碰世界**（与 Mnemos 适配引擎"只产出配置不产出代码"M5 同构）。写手产出的剧本经**加载期 schema 校验**（Part X）才被导演接受；非法剧本（断边/互斥不变量/open 却无在线写手）fail-loud 拒绝。写手 LLM 不可用时：模式 A/B 不受影响（剧本早已写好）；模式 C 则**暂停续写、导演冻结在已有剧本范围内运行**（不伪造剧情，宁可故事暂时不往前，也不让导演越权杜撰——这正是 F8 的好处：导演没有发明权）。

## B · 导演（Director · 执行剧本）

> 导演是 Moira 里**唯一驱动世界**的部件，对应一个现场导演 + 舞台监督。它的输入是**一份剧本** + `read_world` + ToM；它的输出是**对世界的干预**（Part V 两类手段）。它**不发明**剧本里没有的不变量与角色弧——只在剧本划定的节拍图、fallback、张力曲线内**调度**，遇到剧本未覆盖的偏离则按模式降级或上抛写手（F8）。

### 一个导演 tick 的闭环（与 ADOS 的预测闭环同构，但对象是故事）

```
read_world()  ──► 世界真值 + 各身体可见行为(自上次以来)
   │
   ▼
更新 Story State  ──► 当前激活节拍的 success_when / failure_when 求值
   │                  各 invariant / arc 进度推进
   ▼
更新 ToM (Part VIII) ──► 从可见行为重估"心智大概在想什么/下一步会怎么走"
   │
   ▼
评估偏离 ─── 系统离故事线多远? (当前态 vs 期望节拍 + 张力曲线位置)
   │
   ├─ 在轨道上、且无紧迫节拍 ──► 什么都不做(看着), 设长兜底定时器  ← 最常见!
   │
   ├─ 该推进下一节拍 ──► 选 Beat (LLM: 看 story state + ToM + 张力曲线 + 预算)
   │                      │
   │                      ▼
   │                 Intervention Planner 把 Beat 的 setup 编译成干预 (Part V)
   │                      │
   │                      ▼
   │                 预算检查(F4): 太显眼/太巧? → 降级为更弱的手段 或 推迟
   │                      │
   │                      ▼
   │                 下发干预 (Director API) → 落 fate.log
   │
   ├─ 心智明确偏离当前节拍 ──► failure_when 触发 → 改走 fallback_beats
   │
   ├─ 剧本快演完 / 走到某 exit ──► 模式B: 衔接 next_screenplay; 否则收场
   │
   └─ 剧本未覆盖的重大偏离(无 fallback 可走) ──►
            模式A/B: 降级到最近的合法节拍 或 优雅收场(守住硬不变量)
            模式C:   发 StoryDigest 上抛写手, 请求续写新分支 (写手 tick 醒来)
```

### 选节拍：导演 LLM 的角色（导演侧唯一需要"创造力"的地方）

选节拍是导演唯一调 LLM 的环节，因为它需要叙事判断力——但注意它**只在剧本给定的候选集里选**，不发明节拍（发明是写手的事）。`prompts.toml` 里 `director.select_beat` 角色拿到：当前故事状态、各 invariant 的紧迫度（含 deadline）、张力曲线此刻的期望高度、ToM 对每个心智的最新推断、剩余可信度预算、以及**剧本里前置已满足的候选节拍集**。它产出：选哪个节拍、强度档（micro-nudge / normal / strong，受剧本 `style.max_intervention_strength` 封顶）、以及一句"导演意图说明"（写进 `fate.log`，供复盘"为什么命运在此刻这样安排"）。

**LLM 只做选择与编排，不产出可执行代码、不直接碰世界**——它的输出是声明式的"选 beat X、强度 normal"，由确定性的 Intervention Planner 编译成 Director API 调用（与 Mnemos 适配引擎"LLM 只产出配置不产出代码"同构，M5）。导演 LLM 不可用时回退到**规则档**：按节拍图的 `next_beats` 默认边 + 张力曲线选最匹配的前置已满足节拍（这不是 fallback 造假，是一个真实、确定、可单测的降级策略——它仍只选剧本里的合法节拍、仍不伪造任何东西；若连规则档都无解则 fail-loud）。

### 介入强度的三档（对应 F4 的预算消耗）

| 档 | 手段 | 预算消耗 | 例子 |
|---|---|---|---|
| **micro-nudge** | 只用感知渲染(Part V 第二类) | 极低 | 让书架上那本旧相册的显著性微升——她"碰巧"多看了一眼 |
| **normal** | 温和的世界编排 + 渲染 | 中 | 安排一封信明早到信箱；下午"恰好"下雨让她留在室内 |
| **strong** | 显眼的世界事件 | 高 | 一个 NPC 此刻来敲门；手机此刻收到一条改变局面的消息 |

**预算（Plausibility Budget）的本质（F4 落地）：** 一个随世界时间缓慢回充、随干预（按强度与"巧合度"）扣减的标量。它逼导演像现实一样克制——巧合在真实世界里也偶尔发生，但不会一天三次精准降临。预算见底时，导演**只能**用 micro-nudge，必须等世界"平淡"一阵、预算回充，才能再安排显眼事件。**这从机制上保证了"命运之手"始终藏在自然统计的噪声里**，恰好避开 ADOS P3 的预测误差雷达。

### 多角色编排（一个世界多条弧）

Oikos 是"一世界多身体"（W9）。导演因此可同时执行多条角色弧：屋里 Alice（ADOS 持续心智）与 Hermes（读 embody.md 连入的一次性 agent）各有 `CharacterArc`。导演把"让两人在客厅相遇并起争执"作为一个**多角色节拍**（由写手写进剧本）：它的 setup 可能是"`drive_body` 让 Hermes 走进客厅 + 给 Alice 的感知里前景化 Hermes 的到来"，success_when 是"两具身体进入同一房间且发生 `speak` 往来"。两个**完全独立、互不读心**的心智，被同一只命运之手编排进同一场戏——但谁都没被强迫开口，争执是不是真的发生，仍取决于两个自由心智听到对方话后各自的反应（声音经 W10 空气传播，可能还没听清）。

## C · 三种运行模式（写手与导演的三种接线）★

> 三种模式不是三套代码，而是**写手与导演在时间上如何接线**的三种配置——全靠 F8（剧本是唯一契约）让它们同构。一张表先看全貌：

| 模式 | 写手何时跑 | 导演吃什么剧本 | 典型场景 |
|---|---|---|---|
| **A · 写完即演** | 演出前跑一次 | 一份 `closed` 剧本 | 讲一个事先构思好的完整故事 |
| **B · 剧目库** | **不在场**（剧本早写好） | 剧目库里指定的 `closed` 剧本，演完按 exit 衔接下一部 | 一系列预制故事，串播/选播 |
| **C · 边演边写** | 全程在线 | 一份 `open` 种子，靠 `ScreenplayDelta` 持续长出 | 只给主题/风格，故事即兴生长 |

### 模式 A · 写完即演（pipeline）

最简单的一锤子买卖：人给写手一份创作纲领（主题/风格/不变量/角色弧）→ 写手 `writer.draft` 产出一份 `closed` 剧本 → 校验通过 → 交给导演执行直到 `ending_conditions` 满足。**写手在演出开始后就功成身退**（可以同进程跑完即闲置，也可以是另一台机器离线写好、把剧本文件拷过来）。这验证了写/演分离最基本的好处：**剧本是可离线产出、可反复审阅、可单测的静态制品**——你能在一个故事开演前，先把它的节拍图、不变量、结局完整读一遍。

### 模式 B · 剧目库（pre-authored library，可衔接下一部）

预先写好**一系列** `closed` 剧本，存进剧目库（`screenplays/` 目录，每部一个文件）。导演被指定执行其中某一部；该部演到某个 `exit` 时，按 `exit.next_screenplay` **衔接下一部**——上一部的 `exit.handoff`（带走的关系/事实/弧线位置）喂进下一部的 `entry.expects`，导演据此无缝开场下一幕。

- **写手全程不在场**——这是模式 B 的关键：剧目库是**纯静态资产**，运行时只起一个导演进程读它。
- **衔接是图不是线**：不同 `exit`（和解收场 / 决裂收场）可接不同 `next_screenplay`，于是"演完接下一个"本身是一棵分支树——**走到哪个续集，取决于上一部里自由心智把故事带向了哪个结局**。
- **播放清单（playlist）**：一份可选的 `playlist.toml` 声明剧目库的初始剧本与默认衔接覆盖，相当于"剧集排播表"。导演照单执行，但每一步衔接仍按实际 `exit` 决定。
- `entry.on_mismatch`：若衔接时世界/关系状态与下一部的 `entry.expects` 对不上（比如上一部心智走出了意料外的关系），导演按该字段或**自适应开场**（用一个过渡节拍把状态拉到位）或**拒绝衔接**（`FateError`，宁可停也不硬接一个前提不成立的故事）。

### 模式 C · 边演边写（live co-authoring）

只给一份 `open` 种子剧本（定 `theme`/`style`/`invariants`，节拍图可近乎为空、无结局）→ 写手与导演**同时在线**，组成一个慢闭环：

```
导演执行现有节拍 ──► 故事推进/心智反应被观察
   │  (剧本快演到头 / 出现未覆盖的重大偏离 / 到了该续写的张力节点)
   ▼
导演发 StoryDigest 给写手 ── 摘要: 已发生什么、各弧到哪了、心智怎么反应、哪些不变量还悬着
   │
   ▼
写手 writer.continue ──► 产出 ScreenplayDelta (追加新节拍/分支, 必要时补结局)
   │  (只追加、不改写已演过的; 不碰世界真值; 受 invariants 与 style 约束)
   ▼
导演载入 Delta ──► 节拍图长出新枝, 接着执行 ──► (回到顶部)
```

- **StoryDigest 是导演 → 写手的唯一回传**（与剧本对称：写手→导演给剧本，导演→写手给摘要）。它是**对可见故事的摘要，不含任何心智内部状态**（导演自己也读不到，F5）——写手据此续写，仍是隔着黑箱在为一个自由心智编故事。
- **写手仍受 `invariants` 与 `style` 约束**：边演边写不等于乱写，种子里定下的主题、不变量、风格边界是写手续写时的硬约束（它可以追加新不变量，但不能违背已立的）。
- **退化保护**：写手 LLM 不可用 → 续写暂停 → 导演冻结在已有节拍范围内（用规则档调度已有节拍），**绝不让导演越权杜撰剧情**。故事可以暂时不往前，但不会失控。这正是 F8 的价值：**发明权只在写手手里，导演断了写手就只能在已写好的范围内忠实执行**。

> **三模式同构的本质：** A 是"写手跑一次、产出闭合剧本"；B 是"写手离线跑过 N 次、产出一库可衔接的闭合剧本，运行时不跑"；C 是"写手持续在线、把一份开放剧本流式写成闭合"。**导演的执行逻辑三者完全一样**——它永远只是"吃当前这份剧本、在其节拍图里调度"。变的只是剧本从哪来、何时来。这就是把写手从导演里拆出来、用固定剧本格式做契约（F8）所buy到的全部灵活性。

---

# Part V · 两类干预手段（落地核心）

> 这是全文最实的一节，回答"命运之手到底能做什么、不能做什么"。Moira 的全部能力被严格分成**两个寄存器（register）**：**A. Diegetic（编排世界）**——改变世界的物理真值；**B. Perceptual（渲染感知）**——在不改变真值的前提下，调整心智对真值的呈现。两者合起来就是导演的全部工具箱，且每一件都落在 F1/F3 的红线之内。

## A · Diegetic 干预：编排世界（改变真值）

> 这一类**真的改变 Oikos 世界**。下发后，被安排的事就是世界的真事实，任何身体（被引导的、旁观的）`sense` 到的都一致，心智后续 `act` 去核实也吻合。它们全部经 Director API 让 **Oikos 去物理地实现**——Moira 自己不碰世界状态（心身分离 W1 对导演同样成立：导演也只能"请求世界改变 + 观察后果"）。

| 手段 | Director API | 说明 | 红线 |
|---|---|---|---|
| **安排事件** | `stage_event` | 让 Oikos 在某世界时刻/某格制造一个 `WorldEvent`：门铃、敲门、快递、手机来信(经 Telegram Bridge 的剧情 NPC)、环境噪音 | 事件本身必须是世界真的能发生的；高优先级事件不得违反生存安全的物理 |
| **放置/改动物** | `place` / `mutate_object` | 往世界里加一个 `ObjectInstance`(信箱里一封信、书架上一本书)或改既有物状态(冰箱里多一份食物) | 只能用已登记的 `ObjectType`(world.md 编号目录)；不得凭空造心智正看着的物(那等于伪造观察) |
| **扮演 NPC** | `drive_body` | 用与心智**同一套** `act()` API 驱动一具**未被心智认领的**身体作为"群演"(让 Hermes 走进来、让一个路人 NPC 说句话) | 群演也受全部具身约束(W4: 得真的走过去、声音真的按 W10 传播)；不得驱动已被心智认领的身体 |
| **调世界参数** | `set_world_param` | 在可信范围内拨动世界旋钮：天气、室外光照、设备的偶发状态(网络卡顿)、时钟流速(加速平淡时段) | 必须落在 `world.toml` 声明的合理区间；不得制造物理上不可能的状态 |
| **设/改剧情定时器** | `stage_timer` | 让 Oikos 在未来某刻产生一个剧情事件(对应 set_timer 但归属导演、心智看不到是谁设的) | 到点仍是以 Observation 触发，绝不强制心智执行 |

**Diegetic 的精髓：命运通过"安排巧合"说话。** 现实里的命运也只能这样——它不能让你爱上某人，但它能安排你们在雨天的同一个屋檐下相遇。Moira 安排相遇（真的让两具身体到同一房间），但**爱不爱、说不说话，是自由心智的事**。这就是"既改变了故事走向，又没碰心智一根毫毛"。

## B · Perceptual 干预：渲染感知（不改真值，调呈现）★

> 这一类**完全不改变世界真值**，只调整 Oikos 推给某个心智的那一帧 `WorldObservation` 如何被**呈现**。它落地为 Oikos 观察出口处一道确定性的 **Narration 渲染级**（Part VI），Moira 只提供**偏置参数**。这是导演的"镜头语言"——同一个真实场景，特写还是远景、暖光还是冷光、先看到谁后看到谁，导演说了算，但拍的始终是真实发生的那一幕。

```python
class SalienceBias(Stamped):           # Moira 下发给某心智某帧的渲染偏置 (纯参数)
    target_body: str                   # 给哪具身体的感知加偏置
    ttl_world: float                   # 偏置存活的世界时长(过期自动清, 防永久滤镜)
    # ── 以下全是"对真实观察的呈现调整", 不增删任何真实内容 ──
    foreground: dict[str, float]       # 提升某些真实在场物/人/事件的显著性权重
    background: dict[str, float]       # 降低某些真实项的显著性(但有下限, 见红线)
    mood: PAD | None                   # 整帧的情绪基调染色(影响描述措辞的冷暖)
    affordance_highlight: list[str]    # 让某些真实可用的能力"更跳眼"(她注意到吉他可以弹)
    ambiguity_lean: dict[str, str]     # 对真正歧义的信号给一个解读倾向(见下, 红线最严)
```

### 五种合法的感知渲染（逐一界定边界）

1. **显著性提升/降低（foreground/background）。** 房间里真实存在书架、窗、那本旧相册——Moira 让相册的显著性微升，于是心智的 observation 把它排在更前、描述更具体。心智"碰巧"多注意到它。**没有无中生有，只是改变了真实事物被注意到的顺序与权重**——这正是真实注意力本就会做的事（人本来就只注意到环境的一小部分）。

2. **可供性高亮（affordance_highlight）。** 吉他真的在那、真的能弹（`list_skills` 里真有 `play_guitar`）。Moira 让"可以弹吉他"这个真实可能性在感知里更醒目——像心情对了时你忽然"想起"角落那把琴。**能力是真的，只是被点亮了。**

3. **情绪基调染色（mood）。** 同一个真实的雨夜，可以被呈现得温馨（暖灯、雨声像白噪音）或压抑（冷光、雨声像叹息）。Moira 给这一帧一个 PAD 基调，影响 Narration 级**遣词的冷暖**，不改任何事实。**这是配乐与打光，不是改剧情。** 注意：它影响的是"世界被描述的语气"，心智依旧自由地决定如何感受——它完全可以在被渲染得压抑的雨夜里感到平静。

4. **歧义解读倾向（ambiguity_lean，红线最严）。** **只对世界里本就模糊的信号生效。** 比如 W10 声学模型算出某个声音 `clarity=0.4`（本就"听不太清"）——Moira 可以把这个**真实的歧义**朝剧情需要的方向轻推："那个听不清的声音，听起来像是有人在哭"。**前提是世界真的产生了这个低清晰度信号**；Moira 不能在没有声音时让她"听见哭声"（那是伪造观察，F3 红线）。它只在真实的不确定性**留出的缝隙里**做解读——和现实中人对模糊刺激的主观解读完全同构。

5. **节奏/详略（隐含在 foreground/background）。** 平淡时段可以渲染得简略（一笔带过），关键时刻渲染得浓墨重彩（细节拉满）。这是叙事节奏，不改内容。

### 三条绝对红线（Narration 级硬编码强制，越界即 FateError）

> 这三条是 F3 在感知渲染上的精确落地，由 Oikos 的 Narration 级**确定性强制**，不信任 Moira 的自觉：

- **不得无中生有（No Fabrication）：** `foreground` 只能作用于该帧真实存在的项；引用一个不在真实 `WorldObservation` 里的物/人/事件 → `FateError`。想让它出现，去走 Diegetic 的 `place`/`stage_event` 让它**真的**在世界里出现。
- **安全信息不可压制（Safety is Inviolable）：** `background` 有**显著性下限**，且对 `body_alert` 级信号（生存/安全：憋不住的尿意、迫近的危险、设备致命故障）**完全无效**——这些永远以原始强度直达心智的 Reflex（ADOS Reflex 不依赖 LLM、最高优先级）。**命运可以让你忽略一封信，但不能让你忽略火灾。** 这道墙保证 Moira 永远无法借"降显著性"把心智导向身体伤害。
- **核实即真相（Verification Reveals Truth）：** 任何被渲染弱化/染色的项，一旦心智 `act` 去**直接交互/核实**，返回的是 Oikos 的**原始真值**，不带任何偏置。她若真走到书架前拿起相册，看到的是相册的真实内容，不是 Moira 渲染的版本。**于是偏置只能影响"注意与初始解读"，永远不能在核实面前维持谎言**——世界模型与真值的长期一致性（Oikos W7）被刚性保住。

### 两个寄存器的分工口诀

> **想改变"世界里有什么"→ 走 A（编排世界），让 Oikos 真的改。想改变"心智如何看待已有的世界"→ 走 B（渲染感知），只调呈现。** A 是布景与道具与群演，B 是镜头与打光与配乐。导演两者都用，但永远不钻进演员的脑子——那是 ADOS 的主权领地，命运止步于此。

---

# Part VI · 身体里的那道接缝（Narration 渲染级）

> 这是兑现你那句"**在身体中增加设计，使连接该身体的 soul 的思维可以被引导**"的精确落点。整个 Moira 体系对现有三工程的侵入，**收敛成 Oikos 里唯一的一处新增**：在身体的感知出口（`sense` 返回 `WorldObservation` 之前）插入一道 **Narration / Salience 渲染级**。Soul 零改动，Oikos 内核的物理逻辑零改动，新增的只是"真实观察 → 被渲染的观察"这一道确定性变换。

### 它在哪：Oikos 观察管线的最后一站

```
World State (唯一真值, 永不被 Moira 直接改)
   │
   ▼
build_observation(body)  ──► 原始 WorldObservation (Oikos 既有逻辑, 纯真值)
   │                          self_body / here / others_present / audible / available_skills / events
   │
   ▼
★ Narration Stage (新增, 确定性, 不调 LLM)  ◄──── SalienceBias (Moira 经 Director API 下发)
   │   · 按 foreground/background 重排 & 重新措辞(真实项)
   │   · 按 mood 给描述染冷暖
   │   · 高亮 affordance(真实可用能力)
   │   · 对真正低 clarity 的信号施加 ambiguity_lean
   │   · 强制三红线: 不无中生有 / 安全不可压制 / 偏置不入真值
   │
   ▼
Rendered WorldObservation  ──► sense() 返回给心智 ──► ADOS Observation Engine 照常消费
```

### 为什么这道级"够得着思维"却"碰不到思维"

- **够得着**：ADOS 的 Observation Engine 把 `WorldObservation` 映射成 `ObservationFrame`，进而驱动 Internal State Dynamics 演化 Need/Emotion（world.md Part V 接缝）。所以**改变呈现 = 改变喂给心智的观察 = 间接塑形它的内部状态演化方向**。被前景化的相册更可能勾起一段需求张力、被染压抑的雨夜更可能拉低 valence——心智的"思维"确实被引导了。
- **碰不到**：这道级的输出仍是一个**合法的 `WorldObservation`**，走的还是 `sense` 那条唯一通道。ADOS 依旧 `Behavior = f(InternalState)`，依旧自己演化、自己决策。Moira 没有、也无法写一个字进 `InternalState`。**它只是站在世界与眼睛之间的那个打光师**——光是它打的，但看见什么、作何感想，是心智自己的事。

### 工程契约（确定性、纯函数、fail-loud）

```python
def narrate(obs: WorldObservation, bias: SalienceBias | None) -> WorldObservation:
    """Oikos 内的纯函数: 给定真实观察 + 可选偏置, 产出被渲染的观察。
       无 bias 时 = 恒等变换(返回原始真值)。不调 LLM、确定、可单测。"""
    if bias is None or bias.expired(world_now()):
        return obs                                  # 没有命运在看时, 世界素颜示人
    assert_all_targets_exist_in(obs, bias)          # 红线1: 不无中生有 → 否则 FateError
    out = reorder_and_reword(obs, bias.foreground, bias.background)
    out = enforce_safety_floor(out, obs)            # 红线2: body_alert / 安全项强度复原
    out = colorize_mood(out, bias.mood)
    out = highlight_affordances(out, bias.affordance_highlight)
    out = lean_only_ambiguous(out, bias.ambiguity_lean)  # 红线3: 仅作用于真实低clarity项
    out.provenance.append(bias.id)                  # 可溯源: 这帧被哪条偏置渲染过
    return out
```

要点：
- **无 LLM、确定、可回放。** Narration 级是纯参数化变换，给定 `(obs, bias)` 输出唯一确定——保住了 Oikos "世界演化确定、可单测、可回放"的硬保证（world.md Part II）。叙事的"创造力"全在 Moira 进程的 LLM 里，Oikos 这边只忠实地、机械地应用偏置。
- **偏置带 TTL，过期自动清。** 没有"永久滤镜"——Moira 不持续续命某条偏置，它就自动失效，世界恢复素颜呈现。这防止心智被一层永不散去的命运滤镜长期蒙蔽（也是 F4 克制在感知侧的体现）。
- **Soul 完全无感。** ADOS 收到的就是一个普通 `WorldObservation`，它无法分辨这帧是否被渲染过（正如演员演的时候感觉不到打光的存在）。`bias.id` 进 provenance 是给**导演侧复盘**用的，对心智不可见。
- **越界即 fail-loud。** 偏置引用不存在的项、试图压制安全信号、试图让 lean 作用于非歧义项 → `FateError` 带完整上下文，绝不静默执行一个会让世界模型分叉的渲染。

### 与心智的解耦校验（CI 可查，对应 F1）

Soul 侧代码静态扫描：**不存在**任何 `import moira` / Moira 句柄 / SalienceBias 字段 / Director 事件订阅。心智唯一的世界入口仍是 `sense`，它收到的 `WorldObservation` 的 schema 与无 Moira 时**完全一致**（只是字段的值被渲染过）。这与 ADOS P2、Oikos W1 可叠加校验：**命运对心智的全部影响，必须 100% 经由一个合法的、心智无法区分来源的 `WorldObservation`。**

---

# Part VII · Director 协议（World ⇄ Moira 的特权接口）

> Moira 与 Oikos 之间的契约。沿用三姊妹同款：**localhost HTTP + msgpack**。它与 embody.md 那套面向心智的协议**物理分离、鉴权隔离**——心智那套受身体情境门控、只能感知与行动；导演这套是特权的，能俯瞰全局、编排世界、设渲染偏置。**心智侧协议里不存在任何一个 Director 操作**，所以心智无从调用、无从感知命运（F7）。

| 操作 | 方向 | 寄存器 | 说明 |
|---|---|---|---|
| `read_world(scope)` | moira → oikos | 读 | 导演视角的全局读：所有身体的可见行为、世界真值、活跃事件、自上次以来的动作链。**这是 Moira 的"传感器"** |
| `stage_event(spec)` | moira → oikos | A·世界 | 在某世界时刻/某格制造一个 `WorldEvent`(门铃/敲门/来信/噪音) |
| `place(instance)` / `mutate_object(id, patch)` | moira → oikos | A·世界 | 加一个物实例 / 改既有物状态(只能用已登记 type_id) |
| `drive_body(body_id, skill, args)` | moira → oikos | A·世界 | 用心智同款 `act()` 驱动一具**未被认领**的群演身体 |
| `set_world_param(key, value)` | moira → oikos | A·世界 | 在 world.toml 合理区间内拨天气/光照/时钟流速等 |
| `stage_timer(spec)` | moira → oikos | A·世界 | 设一个剧情定时器(到点产生事件, 心智看不到设置者) |
| `set_salience_bias(bias)` / `clear_bias(id)` | moira → oikos | B·感知 | 给某身体某帧下发/撤销渲染偏置(落 Narration 级) |
| `introspect(query)` | moira → oikos | 读 | 调试/可观测：世界全状态、活跃偏置、最近干预链 |

**特权与门控（对应 F1/F3/F7 的接口级强制）：** 每个 A 类调用，Oikos 都按**与心智 `act` 同样的具身物理规则**校验后执行——`drive_body` 的群演也得真的寻路、声音真的按 W10 衰减、`place` 的物得落在合法格。即命运能**安排**世界，但安排出来的世界**仍服从物理**，不能凭空违例（这正是"命运也只能在世界的规则内运作"）。每个 B 类调用经 Narration 级三红线校验。任何越界（驱动已认领身体、放非法物、偏置伪造观察、压制安全信号、试图让世界时间倒流）→ `FateError` + 完整上下文，绝不静默执行。

**事件推送（oikos → moira，异步）：** Oikos 把"可能影响故事状态的世界变化"（某身体到了关键房间、发生了 `speak`、完成了关键 `act`、某剧情定时器到点）推给 Moira，触发导演 tick 醒来评估。这与 Oikos 推给心智的事件流是**两条独立的流**——心智收它该收的（受身体情境过滤），导演收全局叙事相关的。

### 一次端到端干预（示例：让她"偶然"重拾旧物）

1. **Moira** 导演 tick：ToM 推断 Alice 这几日情绪低落、在客厅闲坐（来自 `read_world` 的可见行为）；张力曲线到了该埋一个"重拾过去"钩子的位置；选中 Beat `rediscover_album`。
2. **Intervention Planner** 编译该节拍的 setup：相册**本就**在卧室书架上（世界真值，无需 place）→ 故走 **B·感知**：`set_salience_bias(target=alice, foreground={album: +0.6}, mood=温暖怀旧, ttl=2h)`。预算检查：纯感知微调、极低消耗、通过。
3. **Oikos** 下次 Alice `sense`（她若走进卧室）时，Narration 级把相册前景化、描述染上暖调——但相册是真的、内容是真的、她不进卧室就根本不触发。
4. **Alice（ADOS）** 自由地观察到"书架上那本旧相册，不知怎么今天格外注意到它"→ Internal State 或许勾起一缕怀旧需求张力 → 她**可能**走过去 `act("pick_up", album)`，也**可能**无动于衷继续闲坐。
5. 若她拿起：`act` 返回相册的**原始真值**内容（红线3，核实即真相）；Moira 经 `read_world` 看到"她拿起了相册"→ Beat `success_when` 满足 → 解锁后继节拍。**若她无视：** Beat 软失败，偏置 2h 后自动过期，Moira 改日另寻钩子（fallback）——绝不强按她去拿。

整条链里：相册与其真实内容在 **Oikos**，"今天格外注意到"的渲染来自 **Moira 经 Narration 级**，拿不拿、作何感受是 **ADOS** 的自由，"记得这相册是谁送的"是 **Mnemos**——四者各守其真值，合成一个"命运轻轻推了一把、而她自己走了过去"的瞬间。

---

# Part VIII · 读懂自由心智（Theory of Mind）

> Moira 把心智当黑箱（F5）。它要引导一个看不透的自由心智，就必须像一个好导演/好 DM 一样，从角色的**外在表现**推断其内在，并据此预判它会怎么走。这一节是 Moira 的"传感器后处理"——把 `read_world` 拿到的可见行为，转成"这颗心大概在想什么、下一步多半会怎么动"的概率判断。

### ToM 模型：每个被引导心智一份

```python
class MindModel(Stamped):              # 对一具身体背后那颗心的"外部画像"(全是推断,非真值)
    body_id: str
    inferred_mood: PAD                 # 从行为推断的情绪(走得慢/久坐/不应答→低落?)
    inferred_focus: str | None         # 当前似乎在意什么(反复看向某物/反复提某话题)
    inferred_intent: list[tuple[str,float]]  # 可能的下一步意图 + 概率
    arc_position: str                  # 在其 CharacterArc 上的估计位置
    responsiveness: float              # 对最近几次干预的"响应度"(钩子咬不咬)
    suspicion: float                   # ★估计的"察觉被摆布"程度(F4 的关键反馈)
    confidence: float                  # 这份推断本身的可信度(可能全猜错)
```

**输入只有可见行为：** 移动轨迹、停留时长、姿态、操作了什么设备、说了什么话（经 W10 它能听到世界里的话）、对上一次干预有没有反应。**绝无**任何 `InternalState` 读取——这与"屋里另一具身体也只能从这些外在线索猜你心情"完全同构，只是 Moira 有全局可见性（能同时看到所有房间的所有身体）。

### `suspicion`：自由心智反过来约束命运（F4 的闭环）

这是最精妙的一处反馈。ADOS 会预测世界（P3）、会反思（Thinking）。如果 Moira 干预太频、巧合太密，心智的 prediction error 会异常升高，它的反思可能产出"最近怪事太多了"这类信念——这会**表现为可观测的行为**：反复核实、警觉性动作、对"巧合"的言语评论（"今天怎么这么巧"）。导演的 ToM 从这些行为**反推 `suspicion`**，并把它接进可信度预算：**suspicion 升高 → 可信度预算回充变慢、强干预被锁、只能用最微弱的手段、甚至主动安排一段彻底平淡的世界让心智"放下戒心"。**

> **于是形成一个自我调节的闭环：命运越是想强推，自由心智越可能察觉，察觉本身又逼命运收手。** 这不是外加的安全阀，而是"一个会预测世界的自由心智 + 一个必须藏在自然统计里的命运"这对设定的**必然数学后果**。导演和被导演者之间，永远隔着一层"不能演得太假，否则观众/演员会出戏"的张力——这层张力，正是自由在命运面前的真实重量。

### 猜错了怎么办：ToM 不确定性是一等公民

`MindModel.confidence` 始终 < 1。Moira 会猜错心智的意图、误判它的情绪。设计上**这是允许的、健康的**：猜错 → 干预没能诱发期望节拍 → `success_when` 不满足 → 导演观察到偏离 → 重估 ToM + 改走 fallback。这与 ADOS 用 prediction error 驱动学习同构：**Moira 也在"预测心智反应 → 观察实际 → 修正模型"的循环里越来越懂这具心智**（响应度、什么钩子有效、suspicion 的触发点），但永远到不了"确知"——黑箱的墙是 F5 立的，也是自由的保证。

---

# Part IX · 与 Soul（ADOS）/ Oikos / Mnemos 接合

> 接入 Moira 后，**ADOS 零改动、Oikos 仅多一道 Narration 级、Mnemos 可选地多一条偏置通道**。这与"Oikos 接入时 ADOS 认知内核一行不改""Mnemos 接入时 Memory 模块退化成薄客户端"是同一个手法：新能力靠**在既有接缝处插入**实现，不靠改写既有内核。

### 改了什么 / 没改什么（一张表）

| 工程 | 改动 | 说明 |
|---|---|---|
| **ADOS (Soul)** | **零改动** | 心智不知道 Moira 存在；它收到的 `WorldObservation` schema 不变，只是值被渲染过；`Behavior=f(InternalState)` 不变 |
| **Oikos (World)** | **+1 道 Narration 级** + 一套特权 Director 端点 | Narration 级是确定性纯函数(Part VI)；Director 端点与心智协议隔离(Part VII)；物理逻辑零改动、仍不依赖 LLM |
| **Mnemos (记忆)** | **可选** +1 条 recall 偏置入口 | 见下；不接也能完整工作 |
| **Moira (新)** | 全新独立进程 | 自带叙事 LLM；持有全部故事意图 |

### 与 ADOS 各模块的接缝（全部经感知，无直接调用）

- **Observation Engine：** 它消费的 `WorldObservation` 已被 Narration 级渲染过——但它无从分辨。前景化的项进 `ObservationFrame` 的更靠前位置、mood 影响 affect 标注。**这是 Moira 影响心智的唯一接触点。**
- **Internal State Dynamics：** 被渲染的观察驱动 Need/Emotion 演化——于是"引导思维"在此落地：改变观察 = 改变内部状态的演化输入。但**演化规则、演化本身仍完全是 ADOS 的**。
- **Reflex System：** Moira 的偏置**够不到这里**——安全级 `body_alert` 经 Narration 级的"安全不可压制"红线原样直达 Reflex。**命运无法借感知渲染把心智导向身体伤害。**
- **Thinking / Prediction：** 这里是 `suspicion` 的来源——心智若反思出"现实可疑"，会表现为行为，被 Moira 的 ToM 读到、反过来收紧命运之手（Part VIII）。**自由心智的预测与反思，是命运的天然枷锁。**

### 与 Oikos 的接缝

Oikos 既有的"一世界多身体、纯物理、fail-loud"全部不变。新增只在两处：观察出口的 Narration 级（消费 `SalienceBias`），与特权 Director 端点（消费 A 类干预，按既有具身物理规则执行）。**Moira 对世界的任何改变，最终都化为 Oikos 自己的一次合法物理变更**——命运不绕过物理，只调度物理。

### 与 Mnemos 的可选接缝（命运也能拨动记忆的浮现）★

记忆是"思维被引导"的另一条深通道。Mnemos 的 `recall` 是参数化扩散激活（memory.md Part IV），其 `dim_weights`/`recency_boost` 等本就**随心智当前注册状态动态变化**。Moira **可选地**经一条受限通道，在关键节拍轻推这些参数——例如在"重拾过去"节拍，微抬与某实体相关记忆的可联想性，让相册更容易勾起那段往事；或影响 Consolidation 的 `dream` 内容倾向（睡梦里浮现某主题）。

**但这条通道受最严约束，且默认关闭：** ① 它仍只调**检索参数**，绝不伪造/植入记忆节点（伪造记忆 = 伪造心智的过去，比伪造观察更越界，Mnemos M6/M2 严禁）；② 记忆真值始终是 Mnemos 的，Moira 只能影响"哪些真记忆此刻更易浮现"，正如它只能影响"哪些真事物此刻更易被注意"——是**显著性**，不是**内容**；③ 经 `fate.log` + Mnemos `consolidate.log` 双重可溯源。v0.1 建议**先不接**这条（YAGNI），把 Moira 的影响面收敛在感知渲染上最干净、最易验证；记忆偏置留到故事确需"命运拨动回忆"时再开。

### 完整隐喻：四位一体

> **一个心智（Soul），住在一具身体里、身处一个世界中（Oikos），拥有记忆（Mnemos），并活在一条命运之下（Moira）。** 当智能体在雨夜忽然想起旧友、起身拨通电话——困是身体给的（Oikos）、想念是心智自己的（ADOS）、记得那个号码是记忆存的（Mnemos）、而"为什么偏偏是今夜、为什么那本相册恰好在手边"，是命运悄悄布置的（Moira）。五件事各归其位，却共同织成一个**既自由、又仿佛被某种叙事牵引着**的存在——这正是我们读一部好小说时，对"角色既鲜活自主、又终将走向其宿命"的那种感觉。

---

# Part X · 故事的格式与结构

> 目录结构刻意体现 F8 的写/演分离：**剧本库（写手的静态产物，可独立存在、可离线审阅）** 与 **导演运行态（执行一部剧时的活状态）** 分两块。选型与三姊妹对齐（TOML 剧本 + SQLite 运行态 + append-only 日志 + 快照），使写手与导演既能同进程、也能分别部署。

### 剧本库（写手产物；模式 B 的核心资产，模式 A/C 也用同一格式）

```
library_<story_universe>/        # 一个"故事宇宙"的剧本库(写手写、导演读)
├── playlist.toml                # (模式B) 排播表: 初始剧本 + 衔接覆盖; 可选
├── screenplays/                 # ★一系列剧本, 每部一个目录; 可衔接成图
│   ├── sp_homecoming/           # 一部剧本(closed 或 open)
│   │   ├── screenplay.toml       # 顶层: format_version/标题/主题/style/completeness
│   │   ├── invariants.toml       # 不变量(命运的"必然")
│   │   ├── arcs.toml             # 各被引导角色弧线(绑 body_id)
│   │   ├── beats/                # 节拍库(DAG): 每个节拍一个文件
│   │   │   ├── act1_*.toml
│   │   │   └── ...
│   │   ├── entry_exit.toml       # ★衔接: entry.expects + 各 exit(when/handoff/next)
│   │   └── bindings.toml         # 绑哪个 Oikos 世界 / 哪些 body_id / Director 端点
│   ├── sp_reckoning/             # 另一部(可由 sp_homecoming 的某 exit 衔接而来)
│   └── ...
└── prompts.toml                 # 写手+导演 LLM 提示词(writer.draft/continue, director.select_beat)
```

### 导演运行态（执行一部剧时产生；与剧本库分离）

```
run_<run_id>/                    # 一次"演出"的运行态目录
├── active_screenplay_ref        # 当前在演哪部(指向 library 里的 sp_*); 模式C下含种子
├── deltas.log                   # ★(模式C) append-only: 写手在线追加的 ScreenplayDelta 流
├── state.db                     # SQLite: 故事状态/节拍进度/各 MindModel/预算/弧线进度
├── fate.log                     # ★append-only: 节拍转移/干预/预算变动/衔接(可回放"命运为何如此")
└── snapshots/                   # 周期快照, 配合两份 log 重建任意时刻的演出状态
```

> **为什么分两块：** 剧本库是**写手的、静态的、可反复审阅与单测的**——你能在开演前读完一整部剧的节拍图与不变量（模式 A/B 的价值）。运行态是**导演的、动态的、一次演出一份**——同一部剧本可被多次执行（面对不同心智、不同随机性）产生不同的 `fate.log`。模式 C 的 `deltas.log` 落在运行态侧（边演边写的增量属于"这次演出"，不回写静态剧本库，除非人工"定稿"另存）。

`screenplays/sp_homecoming/beats/act1_rediscover_album.toml` 示意（一个完整节拍长什么样）：

```toml
id = "rediscover_album"
desc = "Alice 在低落中重新注意到那本旧相册, 触碰一段被搁置的过去"
serves = ["arc:alice:reopen_to_past", "inv:album_truth_surfaces"]
tension = 0.35                         # 张力曲线上的"承"段, 温和
author = "pre"                         # 演前写好(模式C 在线续写的会是 "live")

[[preconditions]]                      # 何时这个节拍可以上场
expr = "tom(alice).inferred_mood.valence < -0.2 and beat('intro').done"

# ── 杠杆 A·世界(本例不需要, 相册已在世界真值里) ──
diegetic_setup = []

# ── 杠杆 B·感知(只渲染, 不改真值) ──
[[perceptual_setup]]
kind = "salience_bias"
target = "alice"
foreground = { album_bedroom = 0.6 }
mood = { valence = 0.3, arousal = -0.1, dominance = 0.0 }   # 温暖怀旧
ttl_world = "2h"

# ── 判定 ──
[[success_when]]
expr = "act_done(alice, 'pick_up', 'album_bedroom')"        # 她自由地拿起了它
[[failure_when]]
expr = "world_elapsed_since_activation > '2d'"               # 两天没反应=软失败

next_beats = ["confront_letter", "call_old_friend"]          # 达成后解锁
fallback_beats = ["album_mentioned_by_visitor"]              # 没咬钩→换条路埋同一伏笔
emotional_target = { valence = 0.2, arousal = 0.2 }          # 期望唤起(非强制)
```

`screenplay.toml` 顶层 + `entry_exit.toml` 衔接示意（模式 B 串剧的关键）：

```toml
# screenplay.toml
format_version = "1.0"
title = "归乡"
theme = "和解需要先直面被回避的真相"
completeness = "closed"                # 可独立演完(模式A/B); 模式C 用 "open"
[style]
tone = "温情, 微悬疑"
pacing = "舒缓"
max_intervention_strength = "normal"   # 这部戏风格上不用"强"干预

# entry_exit.toml —— 让一部演完接下一部
[entry]
expects = []                           # 作为开篇剧本, 无前置期望
on_mismatch = "adapt"

[[exit]]                               # 结局之一: 和解收场 → 接"重逢后的日常"
when = ["beat('final_reconcile').done"]
ending_tag = "reconciled"
handoff = { relationship = "alice~mother:warm", letter = "read" }
next_screenplay = "sp_afterglow"

[[exit]]                               # 结局之二: 决裂收场 → 接另一部续集
when = ["beat('walk_away').done"]
ending_tag = "estranged"
handoff = { relationship = "alice~mother:cold", letter = "read" }
next_screenplay = "sp_distance"
```

`invariants.toml` 示意（命运的"必然"，路径可变它不变）：

```toml
[[invariant]]
id = "album_truth_surfaces"
desc = "Alice 终将得知那封夹在相册里的信的真相"
kind = "must_happen"
hardness = 0.9                         # 很硬: 几乎无论如何都要达成
deadline_world = null                  # 不限时, 但导演会随故事推进逐步加压

[[invariant]]
id = "no_self_harm_route"
desc = "无论剧情多低谷, 命运不得把她导向身体伤害"
kind = "must_not_happen"
hardness = 1.0                         # 绝对: 与 Narration 安全红线 + Reflex 双保险
```

- **与三姊妹对齐的硬约定：** SQLite + TOML + append-only 日志 + 快照 + schema 校验缺项即 fail-loud + 密钥 `ENV:` 间接引用。
- **加载期校验（fail-loud）：** 每个 beat 的 `serves` 必须指向存在的 invariant/arc；节拍图边（next/fallback）必须指向存在的节拍；`exit.next_screenplay` 必须指向剧本库里存在的剧本；绑定的 `body_id` 必须在目标 Oikos 世界里存在；不变量之间不得逻辑互斥（如同时 must_happen 与 must_not_happen 同一事）；`completeness="open"` 却无在线写手相连 → 拒绝。违例即 `FateError` 拒绝加载，不带病开演。
- **可重建性：** `fate.log` + `snapshots/` 使任意时刻的故事状态可重放重建——这是"复盘一部已上演的剧：命运在每个岔路口为何如此选择"的基石，也是调参与单测的依据。

---

# Part XI · 分阶段路线图

> 原则同三姊妹：每阶段产出一个能独立运行、可观测、可回放的系统，附退出标准。Moira 的特殊之处在于——**它必须先有一个能跑的 Oikos + 一个能连入的心智，才谈得上导演**。所以前几个阶段刻意"轻"，把验证重心放在"不侵犯自由、不被识破、不伪造"这三件最难的事上。

### Phase 0 — Director 接缝与 Narration 级（最小侵入，先证明"碰不到思维"）
在 Oikos 里加确定性 Narration 级（消费 `SalienceBias`，强制三红线）+ 特权 Director 端点（`read_world` / `set_salience_bias` / `clear_bias`）；`FateError` 全局错误通道；`fate.log`。Moira 侧只是个能下发手写偏置的最小客户端，**还没有故事**。
**退出标准：** 给一个连入的心智下发感知偏置，心智的 `sense` 确实被渲染（前景化/染色生效），但：① 它去 `act` 核实任何项得到的是原始真值（红线3）；② `body_alert`/安全项永不被压制（红线2）；③ 引用不存在项立即 `FateError`（红线1）；④ Soul 代码静态扫描无任何 Moira 句柄（F1）；⑤ 无偏置时 Narration 级是恒等变换、世界素颜示人。

### Phase 1 — Diegetic 干预与具身物理一致性
落地 A 类干预：`stage_event` / `place` / `mutate_object` / `set_world_param` / `stage_timer` / `drive_body`，全部经 Oikos 既有具身物理规则执行。
**退出标准：** Moira 能安排一次门铃、往信箱放一封真信、让一具未认领的群演身体走进房间说句话——且这些全是世界真值（任何身体 `sense` 一致、心智核实吻合）；驱动已认领身体/放非法物/违反物理 → `FateError`；群演的移动真的寻路、声音真的按 W10 衰减。

### Phase 2 — 剧本格式 + 导演执行（规则档，先不上 LLM；先跑通模式 A）
冻结 `Screenplay` 格式（Part III）；写一份**手写的** `closed` 剧本（人当写手，先不上写手 LLM）；导演侧：Screenplay Loader + 加载期校验、Story State Tracker、规则档选节拍（按节拍图默认边 + 张力曲线 + 前置求值，不调 LLM）、Intervention Planner 把节拍 setup 编译成干预。**这就是模式 A（写完即演）的最小闭环。**
**退出标准：** 给定一份手写闭合剧本，导演能在心智自由活动中按前置推进节拍、达成时解锁后继、软失败时改走 fallback、抵达 `ending_conditions` 时收场；全程只用合法干预、不伪造任何东西；`fate.log` 可回放"每个节拍为何在此刻上场"；加载非法剧本（断边/互斥不变量/open 无写手）fail-loud。

### Phase 3 — Theory of Mind 与可信度预算（证明"不被识破"）
ToM Engine 从可见行为推断 MindModel；Plausibility Budget 随干预扣减/随时间回充；`suspicion` 从心智的警觉行为反推并收紧预算。
**退出标准：** 高频强干预会推高被引导心智（ADOS）的 prediction error 与可观测警觉行为，导演的 ToM 读到后自动锁强干预、降到 micro-nudge 直至 suspicion 回落；长跑下"巧合密度"始终维持在世界自然统计内（可度量）；ToM 猜错时系统平滑改走 fallback 而非卡死。

### Phase 4 — 导演 LLM（叙事创造力上场）
导演的 Staging Engine 接 LLM Gateway，`director.select_beat` 角色做叙事判断选节拍/定强度/写导演意图；LLM 只产出声明式选择、不产出代码、不碰世界；LLM 不可用时干净回退到 Phase 2 的规则档。
**退出标准：** 同一部剧本、同一个自由心智，LLM 档比规则档产出**更贴主题、节奏更自然**的节拍选择（可由人复盘 `fate.log` 评判）；导演 LLM 全程不可用时仍能靠规则档把故事推到结局，绝不伪造摘要或强推心智。

### Phase 5 — 写手 LLM + 剧目库 + 边演边写（三模式齐活）
写手部件：`writer.draft`（冷起草闭合剧本）+ `writer.continue`（吃 StoryDigest 续写 ScreenplayDelta）；剧本库 + `playlist.toml` + `entry/exit` 衔接（模式 B）；导演 ↔ 写手的 StoryDigest 回传 + Delta 流（模式 C）。
**退出标准：** ① 模式 A：写手 LLM 冷起草一份合法闭合剧本，导演直接演到结局。② 模式 B：剧目库里两部剧本经 `exit.handoff`→`entry.expects` 无缝衔接，且不同结局接不同续集；写手进程关掉也能演（纯静态资产）。③ 模式 C：从一份 `open` 种子起步，写手随导演回传的 StoryDigest 持续追加 `ScreenplayDelta`，故事边演边长；写手 LLM 断开时导演冻结在已有节拍内、绝不越权杜撰。④ 三模式共用同一份导演执行逻辑（仅剧本来源/时机不同）。

### Phase 6 — 多角色编排与（可选）Mnemos 记忆偏置
多 `CharacterArc` 并行；多角色节拍（编排两具身体相遇/冲突）；可选接 Mnemos 的 recall 偏置通道（受最严约束、默认关闭）。
**退出标准：** 两具身体（一具 ADOS、一具读 embody.md 的一次性 agent）被同一只命运之手编排进同一场戏，相遇真的经物理发生、对话真的经声音传播，而各自如何反应仍是各自心智的自由；若开启记忆偏置，验证它只调检索参数、绝不植入伪造记忆、双重可溯源。

> **范围说明：** 多导演协同（一个世界多个 Moira 争夺叙事权）、跨世界的史诗级叙事、自动从大规模语料生成剧本，暂不实现（YAGNI）。v0.1 是**单 Moira（写手+导演）、单世界、固定剧本格式、三种运行模式、LLM 做写手与导演判断**的最简可用闭环。

---

# Part XII · 技术选型（单进程最简实现）

| 关注点 | 选型 | 说明 |
|---|---|---|
| 语言 | Python + asyncio | 单进程异步；与三姊妹一致，便于共用 LLM Gateway |
| 写/演分离 | 写手与导演两个 async 部件，可同进程亦可拆进程 | 只经 Screenplay 契约通信（F8）；模式 B 写手不运行 |
| 剧本契约 | 固定格式 `Screenplay` / `ScreenplayDelta`（pydantic + TOML） | 版本化、可离线审阅、可单测；闭合/开放两完整度 |
| 协议传输 | localhost HTTP + msgpack | 最简起步；导演端点与心智端点鉴权隔离 |
| 运行态存储 | SQLite（故事状态/节拍/MindModel/预算） | 与静态剧本库分离；一次演出一份运行态 |
| 节拍/干预日志 | 本地 append-only `fate.log`(+模式C `deltas.log`) | 审计 + 回放 + 复盘"命运为何如此" |
| 节拍图 | 带前置条件的 DAG + 受控谓词小语言 | 非线性故事、可单测；谓词非任意代码 |
| 条件求值 | 受控小语言（取世界真值/故事态/ToM，简单布尔/比较） | 与 Mnemos `bind` 同构，求值失败 fail-loud |
| 写手 | 规则不可、LLM 起草/续写（writer.draft / writer.continue） | 只产出声明式剧本；LLM 不可用时模式C暂停续写 |
| 导演 | 规则档（默认边+张力曲线）+ LLM 档（叙事判断） | 只在剧本候选集里选；LLM 不可用干净回退规则档 |
| LLM 推理 | 复用 ADOS LLM Gateway（provider→model→role） | 写手/导演 tick 均低频；起草与选节拍用中大模型 |
| ToM | 从可见行为做轻量推断（规则 + 低频 LLM） | 带不确定性；猜错是允许的 |
| 数据契约 | pydantic v2 + `Stamped` 基类 | schema 校验，违例 fail-loud |
| 剧本库/运行态格式 | 目录分两块：library_*（静态剧本）/ run_*（活运行态） | 隔离、可迁移、可重建；体现写/演分离 |
| 身体侧接缝 | Oikos 内确定性 Narration 纯函数（无 LLM） | 保住世界确定可回放；创造力全在 Moira 侧 |
| 可观测性 | structlog + `introspect` + `fate.log` 复盘 | 错误全量带上下文，每次干预可溯源 |

---

# Part XIII · 工程约束（硬性，CI 可校验）

Moira 影响心智的唯一通道是心智将观察到的世界（编排世界真相 + 渲染对真相的感知），**绝不写入/读取/旁路心智的 `InternalState`**——Soul 侧代码静态扫描不得出现任何 Moira 句柄/字段/事件订阅，心智收到的 `WorldObservation` schema 与无 Moira 时完全一致；故事是吸引子非轨道——必须区分不变量（守护）与可变路径（重规划），**禁止任何强制心智执行动作的机制**，偏离即重规划而非掰回剧本；**可创造真相、绝不可伪造观察**——感知渲染只能调整对真实 `WorldObservation` 的呈现，引用不存在的项即 `FateError`，要"增"只能经 Director API 让 Oikos 真的改世界；**安全信息不可压制**——`background` 有显著性下限、对 `body_alert` 级信号完全无效、安全项永远原始强度直达 Reflex；**核实即真相**——任何被渲染弱化/染色的项一经心智 `act` 核实即返回 Oikos 原始真值，偏置永不进入真值、带 TTL 自动过期；干预须落在世界自然统计内——维护可信度/巧合预算，`suspicion` 升高即收紧，**克制是架构性的（事件触发+低频兜底，禁止高频轮询拨弄世界）**；导演把心智当黑箱——只从可见行为做 ToM 推断、绝不读心智内部、推断带不确定性允许出错；**写演分离，剧本是唯一契约（F8）**——写手输出类型只能是 `Screenplay`/`ScreenplayDelta`（声明式）、绝不直接调 Director API/碰世界/碰心智，导演输入只能是 `Screenplay`、绝不发明剧本未定义的不变量/角色弧（只能在剧本节拍图与 fallback 内调度，未覆盖偏离则上抛写手而非自行杜撰），剧本格式版本化、可离线审阅、可单测；**模式同构**——写完即演/剧目库/边演边写三模式必须共用同一导演执行逻辑与同一剧本格式，仅剧本来源与时机不同；`ScreenplayDelta` 只能追加节拍/收紧结局、**不得改写已执行节拍、不得撤销已发生的世界真值**；`completeness="open"` 剧本无在线写手相连即 fail-loud；Diegetic 干预必须经 Oikos 既有具身物理规则执行（群演真寻路、声音真衰减、物落合法格），命运不绕过物理只调度物理；导演协议与心智协议物理分离、鉴权隔离，心智协议里不存在任何 Director 操作；写手 LLM 与导演 LLM 都只产出声明式制品（剧本 / 节拍选择）、**不产出可执行代码、不直接碰世界**，LLM 不可用时写手暂停续写、导演干净回退规则档；记忆偏置（若开启）只调 Mnemos 检索参数、**绝不伪造/植入记忆节点**，默认关闭；**禁止 fallback 与静默降级，任何错误以 `FateError` + 完整上下文暴露，绝不伪造干预成功、绝不静默执行越界渲染**；每次节拍转移/干预/预算变动/剧本衔接带时间戳、所服务节拍、因果链、可溯源 provenance，全落 append-only `fate.log`；一个 Oikos 世界至多一个 Moira 导演连接；整个系统保持单进程最简实现，不为未实现的多导演/跨世界/自动剧本生成提前设计。

---

# Part XIV · 风险与缓解

- **命运僭越成"第二个大脑"（最根本的风险）：** Moira 若开始直接替心智做决定，整个"自由"就垮了。**缓解：** F1 是硬红线——Moira 与心智零直接连接、只经 `WorldObservation`；CI 静态校验 Soul 侧无任何 Moira 痕迹；Moira 的全部产出必须落在"世界变更"或"感知渲染参数"，任何"心智状态写入"在类型层面就不存在。
- **伪造观察导致世界模型分叉：** 渲染若越界凭空增删，心智的世界模型与真值悄悄背离，一核实就崩。**缓解：** Narration 级三红线确定性强制（不无中生有/安全不可压制/核实即真相）；偏置带 TTL；越界即 `FateError`。继承 Oikos W7。
- **被自由心智识破（演得太假）：** 巧合太密，ADOS 经 P3 预测误差察觉"现实被摆布"。**缓解：** 这恰是 F4 + `suspicion` 闭环要处理的——预算逼克制、suspicion 反推收紧、必要时主动安排平淡时段；架构用事件触发+低频兜底逼出稀疏干预。**把"会被识破"当成系统的一等反馈信号而非缺陷。**
- **故事卡死（心智死活不咬钩）：** 自由心智可能就是不走任何预期节拍。**缓解：** 吸引子非轨道——多 fallback 路径 + 重规划 + 不变量软/硬度分级；硬不变量临近 deadline 时导演逐步加压（更显眼但仍合法的干预），但**永不**跨过"强制执行"的红线；模式 C 下导演可上抛写手现场续写一条新路；极端情况下允许故事以"未达成某软不变量"收尾——一个没被完全讲成的故事，好过一个被强奸了自由的故事。
- **导演 LLM 叙事质量不稳定：** 选的节拍生硬、不贴主题。**缓解：** LLM 只在受约束的候选集里选（前置已满足的合法节拍）、产出声明式可审；`fate.log` 可人工复盘评判；规则档作确定性下限；张力曲线守住节奏即使内容平庸。
- **写手 LLM 跑偏 / 续写质量差（模式 C）：** 在线续写可能产出不贴主题、违背已立不变量、或破坏节奏的节拍。**缓解：** 写手续写受种子的 `invariants`/`style` 硬约束 + 加载期 schema 校验（断边/互斥即拒）；Delta 只能追加不能改写既成事实；`deltas.log` + `rationale` 全程可复盘；写手 LLM 不可用时导演冻结在已有剧本内、绝不越权杜撰——**故事可暂停生长，但不会因写手失灵而失控**。
- **剧本衔接断裂（模式 B）：** 上一部的结局状态与下一部的 `entry.expects` 对不上。**缓解：** `entry.on_mismatch` 显式声明 adapt（过渡节拍拉到位）或 reject（fail-loud 拒接）；`exit.handoff` 与 `entry.expects` 在加载期做兼容性校验；衔接是按实际 `exit` 走的图、不是死序列。
- **安全：命运把心智导向自伤：** 低谷剧情若失控可能酿成身体伤害。**缓解：** 双保险——`must_not_happen` 硬不变量（hardness=1）+ Narration 安全红线（安全信号不可压制、直达 Reflex）+ Diegetic 干预受 Oikos 物理与影响分级约束；写手续写也受 `style.content_bounds` 与该硬不变量约束。**命运可以让故事悲伤，但触不到"伤害身体"这条线。**
- **预算/ToM 参数失真：** 太松则被识破、太紧则故事推不动。**缓解：** 全部系数在 `screenplay.toml`/`prompts.toml` 可调可单测；`fate.log` 提供"干预密度 vs suspicion 变化"的复盘数据用于校准；提供"强引导/弱引导"两套预设。
- **多角色编排冲突：** 多条弧的节拍在同一时刻争夺同几具身体/同一空间。**缓解：** 导演统一调度、节拍前置含资源占用判定；冲突时按 invariant hardness 与张力曲线仲裁；实在冲突则错峰（一条弧的节拍推迟）。

---

# Ultimate Objective

Moira 的目标不是写一个剧情脚本引擎，也不是做一个提线木偶的操纵台，而是回答一个更难的问题：**如何让一个真正自由的心智，活出一个有意义的故事？**

它的答案是导演的答案、也是命运的答案：你不能、也不该去替角色思考与选择；你能做的，是为它布置一个**以它之天性、必将走向某处**的世界——把对的物放在对的位置、让对的人在对的时刻出现、给平凡的雨夜打上一束让人想起往事的光——然后退后一步，看着它**自己**走过去。当它走到了，那既是命运的安排，也是它自由的选择，二者并不矛盾：**最好的故事，正是那些角色每一步都自由、而结局却仿佛注定的故事。**

配合 [ADOS](soul.md) 的心智、[Oikos](world.md) 的身体与世界、[Mnemos](memory.md) 的记忆，Moira 补上了最后一块、也是最克制的一块：一只**只能通过编排世界与渲染感知来讲故事、永远碰不到角色内心**的命运之手。四者合成一个完整的隐喻——**一个心智，住在一具身体里，身处一个世界中，拥有记忆，并活在一条命运之下。** 而这条命运的全部尊严，恰在于它的**自我克制**：它有能力把世界布置得天衣无缝，却始终把"走不走过去"的最终主权，留给那颗它读不透、也不愿读透的自由的心。















