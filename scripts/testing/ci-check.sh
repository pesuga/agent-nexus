#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python3"
SMOKE_SCRIPT="${ROOT_DIR}/scripts/maintenance/smoke-auth.sh"
LIFECYCLE_SCRIPT="${ROOT_DIR}/scripts/testing/integration-lifecycle.py"
CLI_CONTEXT_SCRIPT="${ROOT_DIR}/scripts/testing/integration-cli-context.py"
CLI_CONTEXT_INVALID_SCRIPT="${ROOT_DIR}/scripts/testing/integration-cli-context-invalid.py"
AGENT_LOCK_SCRIPT="${ROOT_DIR}/scripts/testing/integration-agent-lock.py"
CLI_PARITY_SCRIPT="${ROOT_DIR}/scripts/testing/integration-cli-parity.py"
CLI_PERMISSIONS_SCRIPT="${ROOT_DIR}/scripts/testing/integration-cli-permissions.py"
STAGE_WORKLOOP_SCRIPT="${ROOT_DIR}/scripts/testing/integration-stage-workloop.py"
STAGE_SUBMIT_NEGATIVE_SCRIPT="${ROOT_DIR}/scripts/testing/integration-stage-submit-negative.py"
STAGE_CHECK_SCRIPT="${ROOT_DIR}/scripts/testing/integration-stage-check.py"
FULL_STAGE_FLOW_SCRIPT="${ROOT_DIR}/scripts/testing/integration-full-stage-flow.py"
DOC_PARITY_SCRIPT="${ROOT_DIR}/scripts/testing/check-cli-docs.py"

BASE_URL="${1:-}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "[FAIL] Missing virtualenv python: ${VENV_PYTHON}"
  echo "Create it with: python3 -m venv .venv && source .venv/bin/activate"
  exit 1
fi

echo "[1/12] Auth smoke check"
"${SMOKE_SCRIPT}"
echo "[PASS] Auth smoke check"
echo

echo "[2/12] CLI docs parity check"
"${VENV_PYTHON}" "${DOC_PARITY_SCRIPT}"
echo "[PASS] CLI docs parity check"
echo

echo "[3/12] CLI invalid context-file check"
"${VENV_PYTHON}" "${CLI_CONTEXT_INVALID_SCRIPT}"
echo "[PASS] CLI invalid context-file check"
echo

echo "[4/12] agent-cli lock stress check"
"${VENV_PYTHON}" "${AGENT_LOCK_SCRIPT}"
echo "[PASS] agent-cli lock stress check"
echo

echo "[5/12] Lifecycle integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${LIFECYCLE_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${LIFECYCLE_SCRIPT}"
fi
echo "[PASS] Lifecycle integration check"
echo

echo "[6/12] CLI context integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${CLI_CONTEXT_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${CLI_CONTEXT_SCRIPT}"
fi
echo "[PASS] CLI context integration check"
echo

echo "[7/12] CLI parity integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${CLI_PARITY_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${CLI_PARITY_SCRIPT}"
fi
echo "[PASS] CLI parity integration check"
echo

echo "[8/12] CLI permissions integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${CLI_PERMISSIONS_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${CLI_PERMISSIONS_SCRIPT}"
fi
echo "[PASS] CLI permissions integration check"
echo

echo "[9/12] Stage submit negative integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${STAGE_SUBMIT_NEGATIVE_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${STAGE_SUBMIT_NEGATIVE_SCRIPT}"
fi
echo "[PASS] Stage submit negative integration check"
echo

echo "[10/12] Stage workloop integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${STAGE_WORKLOOP_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${STAGE_WORKLOOP_SCRIPT}"
fi
echo "[PASS] Stage workloop integration check"
echo

echo "[11/12] Stage-check integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${STAGE_CHECK_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${STAGE_CHECK_SCRIPT}"
fi
echo "[PASS] Stage-check integration check"
echo

echo "[12/12] Full stage-flow integration check"
if [[ -n "${BASE_URL}" ]]; then
  "${VENV_PYTHON}" "${FULL_STAGE_FLOW_SCRIPT}" --base-url "${BASE_URL}"
else
  "${VENV_PYTHON}" "${FULL_STAGE_FLOW_SCRIPT}"
fi
echo "[PASS] Full stage-flow integration check"
echo

echo "[PASS] CI checks completed successfully."
