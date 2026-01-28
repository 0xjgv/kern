[x] Identify opportunities to simplify the codebase with 7 proposals
    Research: 10 simplification opportunities found in kern.sh (~21% reduction):

  1. [ ] Use show_result() consistently (4 inline jq calls)
  2. [ ] Extract execute_stage() wrapper (~40 lines saved)
  3. [ ] Consolidate stage validation with get_stage_result()
  4. [ ] Generic has_task_status() checker
  5. [ ] Stage file path helper stage_file()
  6. [ ] Result pattern checker check_stage_result()
  7. [ ] Invert resume logic with should_run_stage()
  Files: kern.sh, prompts/*.md
