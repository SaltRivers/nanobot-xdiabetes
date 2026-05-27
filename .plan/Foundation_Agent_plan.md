下面是**精简版仓库修改方案**，核心原则是把当前默认 workflow 改造成 Foundation Agent workflow。**

---

## 1. 总体改造目标

将当前仓库从：

```text
通用 AgentLoop + 若干 X-Diabetes tools + DTMH 调用
```

改为：

```text
X-Diabetes Foundation Agent
  = guideline-grounded clinical planner
  + data manager
  + DTMH orchestrator
  + evidence-aware interpreter
  + reflective report generator
```

也就是说，`AgentLoop` 只是 runtime，`xdiabetes_dtmh` 只是内部计算能力，真正的主流程应是：

```text
User Query
→ Query Decomposition
→ Guideline-Based Planning
→ Data Management
→ DTMH Orchestration
→ Result Interpretation
→ Evidence Retrieval
→ Reflection
→ Clinical Report
```

---

## 2. 新增核心模块

建议在 `xdiabetes/clinical/` 下新增：

```text
xdiabetes/clinical/foundation/
  __init__.py
  schemas.py
  workflow.py
  planner.py
  data_manager.py
  dtmh_orchestrator.py
  interpreter.py
  reflector.py
  trace.py
```

各模块职责：

```text
schemas.py
  定义 ClinicalTaskPlan、GuidelinePlan、DataPreparationResult、
  DTMHExecutionPlan、ClinicalInterpretation、ReflectionDecision、FoundationTrace

workflow.py
  Foundation Agent 主流程控制器

planner.py
  Query decomposition + guideline-based planning

data_manager.py
  患者数据检查、标准化、DTMH-ready payload 准备

dtmh_orchestrator.py
  根据 clinical task 选择 DTMH capability / output head / request format

interpreter.py
  将 raw DTMHResult 转成临床语义解释

reflector.py
  判断是否需要补数据、补证据、重跑 DTMH 或生成最终报告

trace.py
  保存完整 workflow trace，便于 debug、论文展示和审计
```

---

## 3. 修改默认运行路径

当前推荐命令：

```bash
x-diabetes agent -m "Check whether patient 4 in Dataset/private_fundus has diabetes"
```

内部应从现在的：

```text
AgentLoop → xdiabetes_dtmh → LLM response
```

改成：

```text
AgentLoop
→ FoundationWorkflow
   → planner
   → data_manager
   → dtmh_orchestrator
   → xdiabetes_dtmh / HTTPDTMHAdapter
   → interpreter
   → guideline/evidence retrieval
   → reflector
   → report_builder
→ final response
```

也就是说，`xdiabetes_dtmh` 继续存在，但变成 **FoundationWorkflow 内部调用的 DTMH execution backend**，而不是整个系统的默认逻辑核心。

---

## 4. 调整现有工具定位

### 保留但降级

```text
xdiabetes_dtmh
```

定位改为：

```text
低层 DTMH execution tool / backend adapter
```

不再是临床 workflow 的默认入口。

---

### 保留作为 demo shortcut

```text
xdiabetes_consultation
```

定位改为：

```text
legacy one-shot consultation / demo mode
```

短期可以保留，避免破坏现有可运行 demo；长期应由 `FoundationWorkflow` 替代。

---

### 强化已有能力

```text
xdiabetes_guideline_search
xdiabetes_report_generation
xdiabetes_safety_check
xdiabetes_patient_context
xdiabetes_patient_memory
```

这些不需要重写，但应被 `FoundationWorkflow` 编排，而不是让 LLM 自由选择调用顺序。

---

## 5. 新增关键 schema

最少需要新增 6 个结构化对象：

```text
ClinicalTaskPlan
  - original_query
  - task_type
  - audience
  - patient_reference
  - sub_tasks
  - required_data
  - required_dtmh_capability

GuidelinePlan
  - clinical_steps
  - guideline_basis
  - required_evidence
  - required_safety_checks
  - expected_dtmh_outputs

DataPreparationResult
  - patient_id
  - available_modalities
  - missing_fields
  - temporal_coverage
  - dtmh_ready
  - payload_preview

DTMHExecutionPlan
  - capability
  - output_heads
  - request_format
  - cohort_dir
  - patient_id
  - checkpoint_path
  - config_path

ClinicalInterpretation
  - main_conclusion
  - risk_level
  - model_outputs_used
  - uncertainty
  - data_limitations
  - recommended_next_actions

ReflectionDecision
  - is_complete
  - reason
  - failure_modes
  - next_action
```

这些 schema 是让 Foundation Agent “像医学系统一样工作”的关键，而不是只靠 prompt 约束。

---

## 6. DTMH 接口扩展方向

当前 DTMH 主要返回 diabetes probability。短期不需要立刻实现所有输出头，但接口层应先预留：

```text
diabetes_screening
subtype_classification
complication_prediction
trajectory_prediction
treatment_response
medication_next_time
medication_type
medication_dose
unified_representation
```

建议把当前 `task` 参数升级为：

```text
clinical_task
dtmh_capability
output_heads
time_horizon
intervention_context
return_latents
return_uncertainty
```

这样未来 DTMH 模型扩展时，Foundation Agent 不需要再重构。

---

## 7. 文档与配置同步

需要同步修改：

```text
CLAUDE.md
docs/XDIABETES_QUICKSTART.md
docs/XDIABETES_ARCHITECTURE.md
docs/XDIABETES_DTMH_ADAPTER.md
xdiabetes/skills/x-diabetes/SKILL.md
xdiabetes/templates/workspace_seed/
```

重点统一一句话：

```text
X-Diabetes is a Foundation Agent system for precision diabetology.
DTMH is its core computational engine, not the whole agent.
AgentLoop is the runtime, not the clinical reasoning architecture.
```

并明确两种运行模式：

```text
mock mode
  用于本地 demo / 测试

http DTMH mode
  用于真实 DTMH /predict_csv 或未来多输出头 inference
```

---

## 8. 最小 MVP 实施顺序

### Step 1：新增 foundation 目录和 schema

先实现结构，不改太多现有逻辑。

```text
xdiabetes/clinical/foundation/schemas.py
```

---

### Step 2：实现 `FoundationWorkflow`

先支持最核心场景：

```text
Check whether patient 4 in Dataset/private_fundus has diabetes
```

流程固定为：

```text
screening task
→ prepare cohort_dir + patient_id
→ call current xdiabetes_dtmh
→ interpret diabetes_probability
→ generate doctor-facing report
```

---

### Step 3：把默认 agent prompt / skill 改成优先走 FoundationWorkflow

不要让 LLM 首选 `xdiabetes_dtmh`，而是要求：

```text
For X-Diabetes clinical queries, follow FoundationWorkflow.
Use DTMH only through the workflow unless debugging.
```

---

### Step 4：保留旧工具，避免破坏 demo

`xdiabetes_consultation` 和 `xdiabetes_dtmh` 暂时不删除，只重新定位。

---

### Step 5：保存 trace

每次运行保存：

```text
workspace/runs/<timestamp>_<patient_id>_foundation_trace.json
workspace/reports/<timestamp>_<patient_id>.md
```

---

## 9. 最终目标结构

改造后仓库应表达为：

```text
xdiabetes/
  agent/
    loop.py
    context.py
    tools/
      diabetes/
        dtmh_adapter.py          # DTMH execution backend
        consultation.py          # legacy shortcut

  clinical/
    foundation/
      workflow.py                # main Foundation Agent workflow
      schemas.py
      planner.py
      data_manager.py
      dtmh_orchestrator.py
      interpreter.py
      reflector.py
      trace.py

    adapters/
      http.py                    # remote DTMH service adapter

    services/
      report_builder.py
      safety_engine.py
      knowledge_router.py
      patient_store.py
```

---

## 一句话总结

**不要把 Foundation Agent 做成一个新工具；要把整个仓库的默认临床工作流重构为 Foundation Agent。**

最重要的修改是新增 `xdiabetes/clinical/foundation/`，把当前分散的 DTMH、RAG、safety、memory、report 能力组织成一个显式的、可追踪的医学工作流：

```text
Clinical planning → Data preparation → DTMH orchestration → Interpretation → Reflection → Report
```
