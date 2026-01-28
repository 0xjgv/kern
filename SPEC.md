[x] Identify opportunities to simplify the codebase with 7 proposals
    Research: 10 simplification opportunities found in kern.sh (~21% reduction):

  1. [x] Use show_result() consistently
     Consolidated last inline jq call in build_prompt() at line 181.
  2. [x] Extract execute_stage() wrapper (~40 lines saved)
     Added execute_stage(num, label, name, prev_num, exit_on_fail) wrapper at line 274.
     Refactored 4 stage calls to use the wrapper. Net reduction: 28 lines.
  3. [ ] Consolidate stage validation with get_stage_result()
  4. [ ] Generic has_task_status() checker
  5. [x] Stage file path helper stage_file()
     Added single-line helper `stage_file() { echo "$OUTPUT_DIR/stage${1}.json"; }` at line 118.
     Replaced 5 occurrences in execute_stage(), detect_resume_stage(), and main loop.
  6. [x] Result pattern checker check_stage_result()
     Added `check_stage_result()` at line 119. Combines validation + extraction.
     Replaced stage_complete() calls in detect_resume_stage() and Stage 1 validation.
     Removed unused stage_complete() function (~5 lines saved).
  7. [ ] Invert resume logic with should_run_stage()
  Files: kern.sh, prompts/*.md
