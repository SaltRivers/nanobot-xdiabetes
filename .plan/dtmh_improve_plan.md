

A detailed **file-by-file modification plan** , focused on:

* **keeping** the good infrastructure,
* **removing** the demo-patient bias,
* **changing** the agent’s role to DTMH calling,
* **making** local HTTP DTMH the primary execution path.

to make the project focusing on working with DTMH.

---

## 1. Core entrypoint and runtime behavior

### `xdiabetes/cli/commands.py`

This is one of the highest-priority files.

#### Why modify it

It currently presents onboarding and runtime behavior as a profile that seeds a demo workspace and starts a consultation-style workflow. `xdiabetes_onboard()` still prints “Try the demo case” and explicitly frames the current system around a demo workflow .

#### Planned changes

* Rewrite onboarding messages so they no longer mention:

  * `demo_patient`
  * demo doctor report generation
  * mock-first demo validation
* Keep:

  * config creation
  * workspace creation
  * plugin onboarding
  * learning commands
* Update the “next steps” text so it points users toward:

  * configuring local DTMH HTTP endpoint
  * running `x-diabetes agent`
  * asking a patient/cohort inference query
* Keep `learning` subcommands unchanged unless wording needs cleanup.

#### Secondary changes

* Review `_prepare_runtime_workspace(...)` usage to ensure onboarding still creates useful directories without depending on demo case artifacts.
* Keep `_load_xdiabetes_runtime_config(...)` and runtime normalization logic, but align defaults with DTMH-first behavior.

---

## 2. Configuration defaults

### `xdiabetes/config/schema.py`

This is the main config-definition file and must be updated carefully.

#### Why modify it

It still encodes demo-era defaults:

* `default_patient_id = "demo_patient"`
* DTMH backend default = mock at the schema level
* the runtime is still framed partly around a consultation profile 

#### Planned changes

* Change DTMH defaults toward the new mainline path:

  * `backend = "http"`
  * `http_base_url = "http://localhost:8000"`
  * `http_endpoint = "/predict_csv"`
* Add or revise the `http_request_format` enum to support a more exact format for the new endpoint. Right now it supports `"xdiabetes"` and `"dtcan_predict"` .
  I would add something like:

  * `"dtcan_predict_csv"`
* Decide what to do with:

  * `checkpoint_path`
  * `config_path`
  * `output_format`

  These should remain in config because they are useful defaults for repeated calls.

#### What to preserve

* `memory`
* `rag`
* `learning`
* the rest of the config structure

#### What to revise

* `default_patient_id`

  Options:

  1. remove it entirely from the default flow, or
  2. keep it nullable / inert, but stop relying on it in prompts and onboarding.

---

### `xdiabetes/clinical/constants.py`

This file holds many user-facing defaults.

#### Why modify it

It still hardcodes demo-era assumptions:

* `DEFAULT_CASE_ID = "demo_patient"`
* `DEFAULT_DTMH_BACKEND = "mock"` 

#### Planned changes

* Change:

  * `DEFAULT_DTMH_BACKEND` from `"mock"` to `"http"`
* Remove or neutralize:

  * `DEFAULT_CASE_ID = "demo_patient"`
* Keep:

  * workspace path
  * learning directory
  * patient memory directory
* Review whether `DIRECTORY_TEMPLATES` should still include `cases/`

  * likely yes, if local case storage remains supported
  * but onboarding should stop forcing demo case content into it

---

## 3. HTTP DTMH integration

### `xdiabetes/clinical/adapters/http.py`

This is the most important implementation file for the new behavior.

#### Why modify it

It already supports HTTP DTMH integration and multiple request styles, but it is still centered on:

* native `DTMHRequest`
* a legacy `dtcan_predict` mode that converts `PatientCase` into a raw payload 

Your target case is different. It is not “load a local structured patient case and convert it.” It is:

* identify `cohort_dir`
* identify `patient_id`
* send those directly to `/predict_csv`
* include checkpoint/config/output options

The uploaded demo file confirms this exact usage style and target prompt .

#### Planned changes

Add a new request path such as:

* `dtcan_predict_csv`

This mode should:

* build payloads like:

  * `cohort_dir`
  * `patient_id`
  * `checkpoint_path`
  * `config_path`
  * `output_format`
* POST to `/predict_csv`
* normalize the response into the internal `DTMHResult` shape

#### Concrete internal work

Add methods such as:

* `_build_dtcan_predict_csv_payload(...)`
* possibly `_normalize_predict_csv_response(...)`

#### What to preserve

* the existing response normalization structure
* HTTP error handling
* the overall adapter abstraction

#### What to stop prioritizing

* the assumption that every call begins from a local `PatientCase` object

---

### `xdiabetes/clinical/adapters/__init__.py`

#### Why modify it

This is where backend selection happens.

#### Planned changes

* Keep the adapter factory structure.
* Update comments and expectations so HTTP is treated as the main intended path, not mock.
* Ensure the new request format is documented in code comments if you add a new format option.

---

## 4. Tool routing and agent tool design

### `xdiabetes/clinical/registry.py`

This is where the diabetes toolchain is assembled.

#### Why modify it

Right now it registers a consultation-heavy stack:

* patient context
* patient memory
* guideline search
* dtmh
* safety check
* report generation
* consultation 

That registry is fine structurally, but the **priority** is wrong for the new role.

#### Planned changes

* Keep the registry pattern.
* Reorder the conceptual priority toward:

  1. DTMH inference
  2. patient context / patient memory as optional support
  3. safety / retrieval / report as optional post-processing
* Consider adding a new dedicated tool:

  * `xdiabetes_dtmh_predict_csv`
  * or revising the existing `xdiabetes_dtmh` tool to accept `cohort_dir`-based input

#### Preserve

* PatientMemoryStore / Builder wiring
* KnowledgeRouter wiring
* Learning compatibility

#### Possibly demote

* `XDiabetesConsultationTool` as the “primary” first tool

---

### `xdiabetes/agent/tools/diabetes/dtmh_adapter.py`

This is the current DTMH tool.

#### Why modify it

Right now it still expects:

* `patient_id` or `case_file`
* `clinical_question`
* `task`
* `audience`
* and it loads a `PatientCase` from `PatientStore` before calling DTMH 

That is too tied to the old local-case workflow.

#### Planned changes

Revise this tool so it can support the new primary case:

* `cohort_dir`
* `patient_id`
* optional `checkpoint_path`
* optional `config_path`
* optional `output_format`

It can still support legacy case-based usage, but the mainline behavior should be direct DTMH inference over the HTTP service.

#### Best implementation option

Either:

1. expand `xdiabetes_dtmh`, or
2. create a second DTMH tool dedicated to `predict_csv`

I would lean toward **adding an explicit tool** for clarity, then possibly letting `xdiabetes_dtmh` become the generic wrapper.

---

### `xdiabetes/agent/tools/diabetes/consultation.py`

This is the current end-to-end primary workflow tool.

#### Why modify it

Its description explicitly says:

> “Primary X-Diabetes entrypoint” and “loads the patient case, merges longitudinal memory, runs DTMH, retrieves evidence, applies safety checks, and writes a report” 

That is exactly the role you want to de-emphasize.

#### Planned changes

Do **not necessarily delete** this tool. Instead:

* stop making it the default first action
* demote it to an optional higher-level orchestration tool
* revise its description so the LLM no longer prefers it for every diabetes request

#### Optional internal changes

* Allow it to call the new DTMH-first path internally when appropriate
* Make report generation optional and not the central point of the repo’s identity

---

### `xdiabetes/agent/tools/diabetes/__init__.py`

#### Why modify it

This export file controls the visible diabetes tool surface .

#### Planned changes

* Export any new DTMH CSV prediction tool if added
* Keep existing exports where still useful
* Make sure the final tool list reflects DTMH-first positioning

---

## 5. Prompt and skill layer

### `xdiabetes/templates/workspace_seed/AGENTS.md`

This is one of the most important prompt files.

#### Why modify it

It currently tells the agent:

* “Prefer `xdiabetes_consultation` as the first tool”
* default demo patient id is `demo_patient` 

That directly conflicts with the new role.

#### Planned changes

Rewrite the mission and working rules so they say:

* The primary role is to interpret diabetes-analysis requests and invoke DTMH.
* Prefer the DTMH tool first for:

  * diabetes prediction
  * patient/cohort analysis
  * probability requests
* Use patient memory only as supporting context.
* Use consultation/report tools only if the user explicitly wants a broader workflow artifact.

#### Remove

* `demo_patient` as a workspace default
* “Prefer consultation first”

#### Keep

* safety framing
* storage-path notes for memory and learning
* clear caveats around model output

---

### `xdiabetes/templates/workspace_seed/TOOLS.md`

#### Why modify it

It currently says:

* `xdiabetes_consultation` is the preferred first tool 

#### Planned changes

Change the tool note hierarchy to something like:

* `xdiabetes_dtmh` or new DTMH CSV tool is the preferred first tool for structured diabetes inference
* `xdiabetes_patient_memory` is optional context
* `xdiabetes_guideline_search` and `xdiabetes_safety_check` are secondary tools
* `xdiabetes_generate_report` is optional, not the default workflow destination

---

### `xdiabetes/templates/workspace_seed/USER.md`

#### Why modify it

This file currently frames the runtime around doctor/patient modes and still mentions a placeholder mock backend .

#### Planned changes

Keep the mode concept if you still want it, but revise the content to reflect:

* DTMH-first execution
* local HTTP model invocation
* structured inference support

Remove emphasis on the placeholder mock backend from the default prompt template unless mock remains an explicit fallback mode.

---

### `xdiabetes/skills/x-diabetes/SKILL.md`

This is the main reusable skill file and needs direct revision.

#### Why modify it

It currently instructs:

1. Start with `xdiabetes_consultation`
2. Then use lower-level tools
   and it explicitly says the default runnable workflow uses a placeholder mock adapter .

#### Planned changes

Rewrite the default workflow section to something closer to:

1. For diabetes-analysis requests, first extract:

   * `cohort_dir`
   * `patient_id`
   * and any explicit model/config overrides
2. Use the DTMH HTTP tool first
3. Use patient memory only if prior results or persistent context are helpful
4. Use report generation only when the user requests saved artifacts
5. Do not rely on demo cases

#### Add examples

Include the exact target pattern from your requirement, based on the uploaded demo script prompt .

---

## 6. Demo-case removal and local case storage cleanup

### `xdiabetes/templates/workspace_seed/cases/demo_patient.json`

#### Why modify it

This is the strongest single demo artifact in the repo. It is explicitly marked:

* `patient_id: "demo_patient"`
* “Demo case for the X-Diabetes MVP” 

#### Planned changes

Delete this file from the seeded workspace content.

If you still want to keep an example artifact for developers, move it:

* out of the default bootstrap path,
* into docs/examples,
* and do not let prompts refer to it.

---

### `xdiabetes/clinical/services/patient_store.py`

#### Why modify it

It currently assumes:

* local JSON case storage
* default fallback to the demo case if no patient is supplied 

#### Planned changes

Keep `PatientStore`, because local case storage is still useful.

But revise:

* `load_case(...)` should no longer implicitly fall back to `demo_patient`
* `_resolve_case_path(...)` should not rely on a demo default
* error messages should reflect real usage instead of “default demo case”

#### Preserve

* case listing
* normalized context building
* local structured patient support as an optional capability

---

## 7. Onboarding seed content and workspace layout

### `xdiabetes/clinical/workspace.py`

#### Why modify it

This file copies the packaged workspace seed into the user workspace and currently installs:

* root prompt files
* `cases/`
* `knowledge/`
* `playbooks/`
* `rules/`
* `reports/`
* learning dirs
* patient memory dirs 

#### Planned changes

Keep the bootstrap mechanism.

Change only what is copied by default:

* stop seeding demo patient content
* keep empty or minimal `cases/` if local case storage remains supported
* keep:

  * patient memory
  * learning
  * reports
  * rules
  * workspace prompt files

#### Result

The workspace stays useful and structured, but no longer installs a fake patient workflow.

---

## 8. Documentation and README cleanup

### `README.md`

#### Why modify it

The README still says onboarding bootstraps:

* demo case `demo_patient`
* doctor-facing consultation workflow
* patient-facing explanation workflow
* consultation/report emphasis 

#### Planned changes

Rewrite the README to present the repo as:

* a DTMH-calling diabetes-analysis agent
* using a local HTTP service
* preserving memory, learning, and storage infrastructure

#### Specific README edits

* Remove “demo case `demo_patient`”
* Replace current quick-start query examples with the new target use case
* Add the `/predict_csv` HTTP contract
* Explain that patient memory and continuous learning remain available but are not the primary execution engine

---

## 9. Optional but likely useful schema/model updates

### `xdiabetes/clinical/schemas.py`

I have not opened this file here, but it is very likely relevant.

#### Why likely modify it

If the current `DTMHRequest` assumes a `PatientCase`-centric structure, then supporting the new direct `cohort_dir + patient_id` path cleanly may require:

* new request model fields, or
* a separate request model for DTMH HTTP CSV prediction

#### Planned changes

Review and likely add one of:

* `cohort_dir`
* `checkpoint_path`
* `config_path`
* `output_format`

Or create a separate schema specifically for the direct HTTP prediction mode.

---

## 10. Recommended modification order

Here is the order I would use in practice:

### Phase 1: Change the control plane

Modify:

* `xdiabetes/config/schema.py`
* `xdiabetes/clinical/constants.py`
* `xdiabetes/cli/commands.py`

This sets the new defaults and onboarding behavior.

### Phase 2: Change the execution path

Modify:

* `xdiabetes/clinical/adapters/http.py`
* `xdiabetes/agent/tools/diabetes/dtmh_adapter.py`
* `xdiabetes/clinical/registry.py`
* possibly `xdiabetes/clinical/schemas.py`

This gives the repo a real DTMH-first tool path.

### Phase 3: Change the LLM’s behavior

Modify:

* `xdiabetes/templates/workspace_seed/AGENTS.md`
* `xdiabetes/templates/workspace_seed/TOOLS.md`
* `xdiabetes/templates/workspace_seed/USER.md`
* `xdiabetes/skills/x-diabetes/SKILL.md`

This makes the agent choose the right tool first.

### Phase 4: Remove the demo bias

Modify/remove:

* `xdiabetes/templates/workspace_seed/cases/demo_patient.json`
* `xdiabetes/clinical/services/patient_store.py`
* `xdiabetes/clinical/workspace.py`
* `README.md`

This cleans the repo without deleting good infrastructure.

---

## 11. High-priority file list

If you want the shortest “must-touch” set, it is this:

1. `xdiabetes/clinical/adapters/http.py`
2. `xdiabetes/agent/tools/diabetes/dtmh_adapter.py`
3. `xdiabetes/clinical/registry.py`
4. `xdiabetes/templates/workspace_seed/AGENTS.md`
5. `xdiabetes/templates/workspace_seed/TOOLS.md`
6. `xdiabetes/skills/x-diabetes/SKILL.md`
7. `xdiabetes/config/schema.py`
8. `xdiabetes/clinical/constants.py`
9. `xdiabetes/cli/commands.py`
10. `xdiabetes/templates/workspace_seed/cases/demo_patient.json`
11. `xdiabetes/clinical/services/patient_store.py`
12. `README.md`

## 12. Files to keep largely intact

These are useful and should likely stay with only minor wording changes, if any:

* `xdiabetes/clinical/services/patient_memory_store.py` — keep as persistent patient memory 
* Continuous learning code and directories — keep
* general `AgentLoop` structure — keep, because it already registers clinical tools cleanly 
* workspace bootstrap mechanism — keep, but change seed contents
* storage/report infrastructure — keep if you still want saved DTMH analysis artifacts
