# TaskNotes/Tasks/Task

* [Retire cross-wing mutex + revisit hook strategy when MemPalace #976 merges](Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges.md) - Watch MemPalace #976 (HNSW thread-safety). When merged, retire palace-global mutex and revisit dropping our custom Stop-hook in favor of the plugin's native auto-ingest.
* [Relocate Check 14a/14b/14c/14d/16b bash blocks to references/ (shrink-to-core follow-up)](Arkskill-011-relocate-check-14-and-16b-bash-to-references.md) - v1.21.0 Shrink-to-Core moved heavy bash to references/. v1.21.1/2 added new checks inline. Relocate them to honor the original direction once they've stabilized.
