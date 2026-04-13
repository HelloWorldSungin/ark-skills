"""Verify that /ark-workflow's Step 6.5 frontmatter template still contains the required fields."""
import subprocess
from pathlib import Path

CHECK = Path(__file__).parent / "check_contract_extension.py"


def test_passes_on_current_repo():
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", "skills/ark-workflow/SKILL.md"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"


def test_fails_when_field_missing(tmp_path):
    # Write a SKILL.md without the four fields
    f = tmp_path / "SKILL.md"
    f.write_text("---\n---\n\n### Step 6.5: Activate Continuity\nSome body without the fields.\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "missing" in r.stderr.lower()


def test_fails_when_no_step_65_section(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("---\n---\n\n### Step 7: Hand Off\nNo step 6.5 section.\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "6.5" in r.stderr or "Activate Continuity" in r.stderr.lower() or "continuity" in r.stderr.lower()


def test_fields_must_be_in_step_65_section_not_elsewhere(tmp_path):
    """Deferred finding: plan-as-written would pass if fields appear anywhere in the file.
    This test verifies the check is scoped to the Step 6.5 section body."""
    f = tmp_path / "SKILL.md"
    # Fields are mentioned in prose outside Step 6.5 — should still fail because
    # they're not in the actual Step 6.5 section.
    f.write_text(
        "---\nname: foo\n---\n\n"
        "# Skill\n\n"
        "This skill uses chain_id, task_text, task_summary, task_normalized, and task_hash as frontmatter.\n\n"
        "### Step 6.5: Activate Continuity\n"
        "This section does not actually contain the fields in a template.\n\n"
        "### Step 7: Hand Off\n"
    )
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "missing" in r.stderr.lower()


def test_fails_when_bash_helper_snippet_missing(tmp_path):
    """Deferred finding: the bash snippet that invokes warmup-helpers.py must be present
    in Step 6.5 — otherwise /ark-workflow won't actually compute the fields."""
    f = tmp_path / "SKILL.md"
    # Has all five field names in Step 6.5 frontmatter but no warmup-helpers.py invocation.
    f.write_text(
        "---\nname: foo\n---\n\n"
        "### Step 6.5: Activate Continuity\n"
        "Frontmatter template:\n"
        "  ---\n"
        "  chain_id: {CHAIN_ID}\n"
        "  task_text: |\n"
        "    verbatim\n"
        "  task_summary: {TASK_SUMMARY}\n"
        "  task_normalized: {TASK_NORMALIZED}\n"
        "  task_hash: {TASK_HASH}\n"
        "  ---\n\n"
        "### Step 7: Hand Off\n"
    )
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "warmup-helpers" in r.stderr.lower() or "bash" in r.stderr.lower()
