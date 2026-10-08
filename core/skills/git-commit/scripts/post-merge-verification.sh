#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: post-merge-verification.sh --repo DIR --fork SHA \
  --baseline-before SHA --baseline-after SHA \
  --fork-source persisted --integration-mode managed-no-ff [--manual-resolution]
EOF
}

repo=
fork=
baseline_before=
baseline_after=
integration_mode=
fork_source=missing
manual_resolution=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) [[ $# -ge 2 ]] || { usage; exit 2; }; repo=$2; shift 2 ;;
    --fork) [[ $# -ge 2 ]] || { usage; exit 2; }; fork=$2; shift 2 ;;
    --baseline-before) [[ $# -ge 2 ]] || { usage; exit 2; }; baseline_before=$2; shift 2 ;;
    --baseline-after) [[ $# -ge 2 ]] || { usage; exit 2; }; baseline_after=$2; shift 2 ;;
    --fork-source) [[ $# -ge 2 ]] || { usage; exit 2; }; fork_source=$2; shift 2 ;;
    --integration-mode) [[ $# -ge 2 ]] || { usage; exit 2; }; integration_mode=$2; shift 2 ;;
    --manual-resolution) manual_resolution=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$repo" || -z "$fork" || -z "$baseline_before" || -z "$baseline_after" || -z "$integration_mode" ]]; then
  printf 'RUN_TARGETED\nreason=required merge verification metadata is missing\n'
  exit 0
fi

is_commit() {
  git -C "$repo" cat-file -e "$1^{commit}" 2>/dev/null
}

reason=
if [[ ! -d "$repo/.git" && ! -f "$repo/.git" ]]; then
  reason='repository is unavailable'
elif [[ "$fork_source" != 'persisted' ]]; then
  reason="task fork provenance is not persisted: $fork_source"
elif ! is_commit "$fork"; then
  reason='task fork SHA is missing or invalid'
elif ! is_commit "$baseline_before"; then
  reason='pre-merge baseline SHA is missing or invalid'
elif ! is_commit "$baseline_after"; then
  reason='post-merge baseline SHA is missing or invalid'
elif ! git -C "$repo" merge-base --is-ancestor "$fork" "$baseline_before"; then
  reason='task fork is not an ancestor of the pre-merge baseline'
elif ! git -C "$repo" merge-base --is-ancestor "$baseline_before" "$baseline_after"; then
  reason='pre-merge baseline is not an ancestor of the post-merge baseline'
elif [[ "$manual_resolution" == true ]]; then
  reason='merge required manual conflict resolution'
elif [[ "$integration_mode" != 'managed-no-ff' ]]; then
  reason="integration mode is not managed-no-ff: $integration_mode"
fi

if [[ -n "$reason" ]]; then
  printf 'RUN_TARGETED\nreason=%s\n' "$reason"
  exit 0
fi

merges=$(git -C "$repo" rev-list --first-parent --merges "$fork..$baseline_before")
if [[ -n "$merges" ]]; then
  printf 'RUN_TARGETED\nreason=other first-parent merge(s) existed before this task merge\nmerges=%s\nchanged_files=%s\n' \
    "$(printf '%s' "$merges" | tr '\n' ' ')" \
    "$(git -C "$repo" diff --name-only "$baseline_before" "$baseline_after" | tr '\n' ' ')"
else
  printf 'SKIP_DUPLICATE\nreason=no first-parent merge existed between task fork and pre-merge baseline\nfork=%s\nbaseline_before=%s\nbaseline_after=%s\nchanged_files=%s\n' \
    "$fork" "$baseline_before" "$baseline_after" \
    "$(git -C "$repo" diff --name-only "$baseline_before" "$baseline_after" | tr '\n' ' ')"
fi
