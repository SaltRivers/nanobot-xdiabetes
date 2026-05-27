## X-Diabetes Foundation Agent 工作范式精简报告

### 1. 总体定位：临床任务编排器

Foundation Agent 位于用户 query 与 DTMH 模型之间，承担三类核心职责：

1. **任务理解与分解**
   Agent 首先解析用户输入，将自然语言 query 转化为结构化临床任务。例如筛查、预测、疾病管理、治疗方案评估、患者分层等。

2. **工具选择与执行调度**
   Agent 根据任务需求调用不同工具，包括 Database RAG【暂时空置】、Search Engine【暂时空置】、Code Executor、Report Generation，以及最关键的 **Digital Twin Metabolic Human / DTMH endpoint**。其中：
	* Code Executor 用于执行代码，将数据转化称为需要的格式。
	* Report Generation 用于生成符合clinical style的输出response。
	* DTMH endpoint即为当前仓库中的DTMH HTTP inference

3. **结果整合与临床表达**
   Agent 接收 MHM 输出后，结合医学知识、指南、文献和上下文进行解释，最终生成临床可读的分析、报告或进一步任务指令。

因此，该 agent 的核心范式可以概括为：

> **Guideline-grounded planning → Tool-augmented execution → DTMH-driven computation → Evidence-aware interpretation → Reflective task refinement**

---

## 2. LLM Phase 1：任务规划与模型调用

在第一阶段，Foundation Agent 接收用户输入，包括 **Query** 和相关 **Data**。随后进入临床推理和工具编排流程。

### 2.1 Query Decomposition

随后，agent 对用户问题进行 **query decomposition**，将复杂临床请求拆解为若干（可以只有一个）临床医学格式的问题。

### 2.2 Guideline-Based Planning

针对2.1分解的临床医学格式的问题，Agent 首先基于临床指南和医学规范进行任务规划，而不是直接调用模型。“Guideline Based Planning”表示 agent 会模拟专家医生的工作流程，明确：

* 当前问题属于哪类糖尿病任务；
* 需要哪些患者信息；【允许agent输出，但是当前不使用这一步的结果，因为下游接口还没做好】
* 是否需要调用数据库、知识图谱或外部搜索；
* 是否需要进一步拆解为多个子任务；【当前默认不需要】
* 应该调用 DTMH 的哪个功能模块或输出头。【允许agent输出，但是当前不使用这一步的结果，因为下游接口还没做好】

这使得系统的推理过程更加符合临床诊疗逻辑，而不是单纯依赖黑箱模型预测。

### 2.3 Data Management

Agent 还负责组织输入数据，将用户提供的多模态临床信息整理为 DTMH 可接受的格式。图中对应 **Data Management**，其工作是：
编写python代码并允许，达到以下效果
* 检查输入数据是否完整；
* 标准化患者临床变量；
* 整理随访时间信息；
* 调用缺失数据补全模块；
* 准备 aligned patient profile 或 task-specific input。

这一步默认先不执行，因为下游接口没做好

### 2.4 Tool Calling

Phase 1 的工具列表包括【除了**Report Generation**和**DTMH**，其他都暂时置空】：

* **Database RAG**：检索内部数据库或临床知识库；
* **Search Engine**：补充外部医学文献或最新证据；
* **Code Executor**：执行统计分析、数据转换或辅助计算；
* **Report Generation**：生成结构化医学报告；
* **DTMH**：调用核心 MHM 模型进行患者表征、预测或干预建模。

其中，**MHM 是核心专业计算引擎**，而 Foundation Agent 是调度它的智能控制层。

---

## 4. LLM Phase 2：结果解释、反思与报告生成

当 MHM 返回结果后，Foundation Agent 进入第二阶段。

### 4.1 Result Analysis

Agent 首先分析 DTMH的results，包括：

* 预测分数；
* 风险等级；
* 轨迹预测结果；
* 药物类型或剂量建议；
* 统一患者表征；
* 输出头给出的任务特异结果。

这一步的目标是将模型输出转化为临床语义，而不是直接展示 raw logits 或 embedding。

### 4.2 Literature Retrieve

Agent 可进一步调用文献检索或知识库 RAG，对 MHM 结果进行证据增强。例如当模型预测某患者并发症风险升高时，agent 可以检索相关指南、药物证据或队列研究，为解释提供依据。

### 4.3 Report Generation

最终，Agent 生成面向临床用户的报告，包括：

* 任务结论；
* 关键依据；
* 风险解释；
* 个体化管理建议；
* 需要补充的数据；
* 后续随访或干预计划。

这一阶段使 X-Diabetes 不只是输出一个预测值，而是形成接近临床决策支持系统的完整交互闭环。

---

## 5. Reflective Loop：结果反思与子任务再分配

图中左侧还包含 **Reflect on Sub-Task Results** 和 **Sub-Task Assignment**，说明 Foundation Agent 支持循环式工作流。

如果 MHM 输出不充分、证据冲突、数据缺失或任务尚未完成，Agent 可以重新规划任务。

因此，它是一个 **iterative agent loop**，而不是一次性问答系统。
