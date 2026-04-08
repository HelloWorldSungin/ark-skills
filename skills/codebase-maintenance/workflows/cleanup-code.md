<workflow name="cleanup-code">
<title>Code and Script Cleanup</title>
<description>Find and clean up dead code, stale scripts, and unused source code.</description>

<steps>
<step_1>
<title>Enter Planning Mode</title>
<action>Activate planning mode. No deletions until user approves.</action>
</step_1>

<step_2>
<title>Scan Scripts</title>
<actions>
<action>Glob `scripts/**/*.py` and `scripts/**/*.sh` — list all scripts</action>
<action>Check git status for untracked scripts</action>
</actions>
</step_2>

<step_3>
<title>Dead Code Detection — Scripts</title>
<actions>
<action>For each script, grep codebase for imports or references to it</action>
<action>Identify scripts that reference removed modules or deprecated features</action>
<action>Flag scripts whose imports would fail (reference deleted modules)</action>
</actions>
</step_3>

<step_4>
<title>Dead Code Detection — Source</title>
<actions>
<action>Grep for functions/classes in the project's source directories (discovered from CLAUDE.md or project structure) that have zero callers outside their own file</action>
<action>Check for imports that reference removed modules</action>
<action>Flag unused utility functions</action>
</actions>
</step_4>

<step_5>
<title>Git Untracked Audit</title>
<actions>
<action>Run git status to list all untracked files</action>
<action>Categorize each as: commit, .gitignore, or delete</action>
</actions>
</step_5>

<step_6>
<title>Generate Cleanup Plan</title>
<action>Produce the cleanup plan in the standard DELETE/UPDATE/KEEP format from SKILL.md</action>
</step_6>

<step_7>
<title>Present Plan and Exit Planning Mode</title>
<action>Use ExitPlanMode to present the plan for user approval</action>
</step_7>

<step_8>
<title>Execute Cleanup</title>
<action>After approval, delete/archive flagged files, commit changes</action>
</step_8>

<step_9>
<title>Post-Cleanup</title>
<actions>
<action>Document changes in commit message</action>
<action>Run tests if available to verify nothing broke</action>
</actions>
</step_9>
</steps>
</workflow>
