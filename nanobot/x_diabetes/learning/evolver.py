"""Instinct-to-draft-skill evolution for X-Diabetes learning."""

from __future__ import annotations

import hashlib
import re

from nanobot.x_diabetes.learning.schemas import LearningInstinct, LearningSkillDraft


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "workflow"


def _build_description(instinct: LearningInstinct) -> str:
    base = f"Learned X-Diabetes {instinct.mode} workflow for {instinct.domain}"
    if instinct.task != "general":
        base += f" during {instinct.task} requests"
    return base[:120]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _build_markdown(skill_name: str, instinct: LearningInstinct) -> str:
    workflow_steps = [
        "Start from the observed workflow trigger and choose the matching X-Diabetes tools.",
        instinct.action,
        "Keep the response aligned with the current doctor/patient mode.",
        "Do not copy patient-specific content into reusable instructions.",
    ]
    if instinct.safety_tool_used:
        workflow_steps.insert(2, "Run a safety review before finalizing high-impact recommendations.")
    if instinct.report_requested:
        workflow_steps.append("Generate a structured Markdown report only after the safety and consultation steps succeed.")
    workflow_steps = _dedupe_preserve_order(workflow_steps)

    step_lines = "\n".join(f"{index}. {step}" for index, step in enumerate(workflow_steps, start=1))
    return "\n".join(
        [
            "---",
            f"name: {skill_name}",
            f'description: "{_build_description(instinct)}"',
            'metadata: {"nanobot":{"xDiabetesLearned":true}}',
            "---",
            "",
            f"# {instinct.title}",
            "",
            "## Overview",
            (
                f"This learned skill captures a repeated {instinct.mode}-mode workflow observed in the "
                "X-Diabetes workspace while preserving privacy and avoiding patient-specific content."
            ),
            "",
            "## When to use",
            f"- {instinct.trigger}",
            f"- Confidence: {instinct.confidence:.0%} based on {instinct.evidence_count} sanitized observations.",
            "",
            "## Learned workflow",
            step_lines,
            "",
            "## Safety boundaries",
            "- Never include patient-specific identifiers, reports, or case content in reusable instructions.",
            "- Protect privacy by storing only workflow guidance instead of patient-specific details.",
            "- These workflow hints do not replace clinician judgment and are not medical advice.",
            "- When in doubt, prefer the built-in xdiabetes_consultation tool and clinician-reviewed safety checks.",
        ]
    )


def evolve_instincts_to_drafts(
    instincts: list[LearningInstinct],
    existing_drafts: list[LearningSkillDraft],
) -> list[LearningSkillDraft]:
    """Create draft skills for strong instincts that do not already have drafts."""

    existing_by_source = {
        source_instinct_id
        for draft in existing_drafts
        for source_instinct_id in draft.source_instinct_ids
    }
    drafts: list[LearningSkillDraft] = []

    for instinct in instincts:
        if instinct.status != "strong" or instinct.instinct_id in existing_by_source:
            continue
        stem = _slugify(f"xdiabetes-learned-{instinct.mode}-{instinct.domain}-{instinct.task}")
        suffix = hashlib.sha1(instinct.instinct_id.encode("utf-8")).hexdigest()[:6]
        skill_name = f"{stem}-{suffix}"
        draft_id = skill_name
        drafts.append(
            LearningSkillDraft(
                draft_id=draft_id,
                skill_name=skill_name,
                title=instinct.title,
                description=_build_description(instinct),
                domain=instinct.domain,
                mode=instinct.mode,
                task=instinct.task,
                trigger_summary=instinct.trigger,
                workflow_summary=instinct.action,
                source_instinct_ids=[instinct.instinct_id],
                source_observation_ids=list(instinct.evidence_observation_ids),
                confidence=instinct.confidence,
                skill_markdown=_build_markdown(skill_name, instinct),
                activation_notes=[
                    "Requires evaluation before activation.",
                    "Designed to capture workflow behavior only; patient data must remain out of the skill.",
                ],
            )
        )

    return drafts
