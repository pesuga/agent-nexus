#!/usr/bin/env python3
"""
Integration test for full gated stage flow:

backlog -> todo -> planning -(submit)-> hitl_review -(approve)-> working
working -(submit)-> ready_to_implement -> approval -(approve)-> completed

Validates:
- planning/working artifacts are created and exist on disk
- artifact content quality gates pass via stage/check
- comments and context are updated
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import requests


def load_cli_config() -> Dict[str, Any]:
    cfg_path = Path.home() / ".agent_task_manager.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def request(method: str, base_url: str, path: str, headers: Dict[str, str], **kwargs):
    url = f"{base_url}{path}"
    resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed ({resp.status_code}): {resp.text}")
    if resp.text:
        return resp.json()
    return None


def assert_status(task: Dict[str, Any], expected: str):
    got = task.get("status")
    if got != expected:
        raise AssertionError(f"Expected status '{expected}', got '{got}'")


def latest_stage_artifact(base_url: str, headers: Dict[str, str], task_id: str, stage: str) -> Dict[str, Any]:
    artifacts = request("GET", base_url, f"/api/tasks/{task_id}/artifacts?limit=100", headers)
    for item in artifacts:
        if str(item.get("stage", "")).lower() == stage:
            return item
    raise AssertionError(f"No artifact found for stage '{stage}' task={task_id}")


def append_substantive_update(path: Path, title: str, bullets: List[str]):
    update = (
        f"\n## Update ({title})\n"
        + "".join(f"- {line}\n" for line in bullets)
        + "\n"
    )
    path.write_text(path.read_text(encoding="utf-8") + update, encoding="utf-8")


def main():
    cfg = load_cli_config()
    parser = argparse.ArgumentParser(description="Full stage-flow integration test")
    parser.add_argument("--base-url", default=cfg.get("api_base_url", "http://localhost:8000"))
    parser.add_argument("--actor-role", default=cfg.get("actor_role", "human_admin"))
    parser.add_argument("--actor-id", default=cfg.get("actor_id", "integration-full-stage-flow"))
    parser.add_argument("--api-token", default=cfg.get("api_token", ""))
    args = parser.parse_args()

    headers = {
        "X-Actor-Role": args.actor_role,
        "X-Actor-Id": args.actor_id,
        "X-API-Token": args.api_token,
    }

    health = request("GET", args.base_url, "/health", headers)
    if health.get("status") != "healthy":
        raise AssertionError(f"Unhealthy API: {health}")

    project = request(
        "POST",
        args.base_url,
        "/api/projects",
        headers,
        json={
            "name": f"it-full-flow-{uuid.uuid4().hex[:8]}",
            "description": "Full gated stage flow integration project",
        },
    )
    project_id = project["id"]

    task = request(
        "POST",
        args.base_url,
        "/api/tasks",
        headers,
        json={
            "title": f"full stage flow {uuid.uuid4().hex[:6]}",
            "description": "Validate gated planning/working submissions to completion",
            "project_id": project_id,
            "priority": 2,
        },
    )
    task_id = task["id"]

    task = request("PUT", args.base_url, f"/api/tasks/{task_id}", headers, json={"status": "todo"})
    assert_status(task, "todo")
    task = request("PUT", args.base_url, f"/api/tasks/{task_id}", headers, json={"status": "planning"})
    assert_status(task, "planning")

    planning_artifact = latest_stage_artifact(args.base_url, headers, task_id, "planning")
    planning_path = Path(planning_artifact["path"])
    if not planning_path.exists():
        raise AssertionError(f"Planning artifact missing on disk: {planning_path}")

    append_substantive_update(
        planning_path,
        "Planning package",
        [
            "Defined scope, milestones, and acceptance criteria.",
            "Mapped dependencies and execution order.",
            "Added review checklist and rollback considerations.",
            "Captured assumptions and open questions for HITL.",
        ],
    )

    readiness = request(
        "GET",
        args.base_url,
        f"/api/tasks/{task_id}/stage/check?stage=planning&to_status=hitl_review",
        headers,
    )
    if not readiness.get("ready"):
        raise AssertionError(f"Planning readiness should be ready: {readiness}")

    task = request(
        "POST",
        args.base_url,
        f"/api/tasks/{task_id}/stage/submit",
        headers,
        json={"stage": "planning", "to_status": "hitl_review", "note": "Planning ready for review"},
    )
    assert_status(task, "hitl_review")

    task = request(
        "POST",
        args.base_url,
        f"/api/tasks/{task_id}/hitl/approve",
        headers,
        json={"comment": "HITL approved planning package"},
    )
    assert_status(task, "working")

    working_artifact = latest_stage_artifact(args.base_url, headers, task_id, "working")
    working_path = Path(working_artifact["path"])
    if not working_path.exists():
        raise AssertionError(f"Working artifact missing on disk: {working_path}")

    append_substantive_update(
        working_path,
        "Implementation package",
        [
            "Implemented workflow handlers and validated transitions.",
            "Added artifact references and reviewer-facing notes.",
            "Verified API responses and task state consistency.",
            "Prepared deployment/readiness checklist for handoff.",
        ],
    )

    readiness = request(
        "GET",
        args.base_url,
        f"/api/tasks/{task_id}/stage/check?stage=working&to_status=ready_to_implement",
        headers,
    )
    if not readiness.get("ready"):
        raise AssertionError(f"Working readiness should be ready: {readiness}")

    task = request(
        "POST",
        args.base_url,
        f"/api/tasks/{task_id}/stage/submit",
        headers,
        json={"stage": "working", "to_status": "ready_to_implement", "note": "Implementation package complete"},
    )
    assert_status(task, "ready_to_implement")

    task = request("PUT", args.base_url, f"/api/tasks/{task_id}", headers, json={"status": "approval"})
    assert_status(task, "approval")
    task = request(
        "POST",
        args.base_url,
        f"/api/tasks/{task_id}/hitl/approve",
        headers,
        json={"comment": "Final approval granted"},
    )
    assert_status(task, "completed")

    request(
        "POST",
        args.base_url,
        f"/api/tasks/{task_id}/comments",
        headers,
        json={"comment": "Integration full-flow final reviewer note"},
    )

    comments = request("GET", args.base_url, f"/api/tasks/{task_id}/comments?limit=100", headers)
    context = request("GET", args.base_url, f"/api/tasks/{task_id}/context", headers)

    if not any("final reviewer note" in str(c.get("comment", "")).lower() for c in comments):
        raise AssertionError("Missing expected reviewer note comment")
    if context.get("task", {}).get("status") != "completed":
        raise AssertionError(f"Context task status mismatch: {context.get('task')}")
    if not any(str(a.get("stage", "")).lower() == "planning" for a in context.get("artifacts", [])):
        raise AssertionError("Context missing planning artifact")
    if not any(str(a.get("stage", "")).lower() == "working" for a in context.get("artifacts", [])):
        raise AssertionError("Context missing working artifact")

    print("Full stage-flow integration test passed.")
    print(f"Project: {project_id}")
    print(f"Task: {task_id}")
    print(f"Planning artifact: {planning_path}")
    print(f"Working artifact: {working_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Full stage-flow integration test failed: {exc}", file=sys.stderr)
        sys.exit(1)
