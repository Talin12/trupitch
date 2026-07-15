# The 3-stage evaluation pipeline, one module per stage:
#   stage1_heuristics.py - does the repo exist? (cheap gate)
#   stage2_structure.py  - languages + dependency manifests
#   stage3_scoring.py    - LLM qualitative scoring against the rubric
# Run in order by apps/worker/tasks.py's evaluate_submission task.
