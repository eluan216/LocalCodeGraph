# Competition integration status

This folder is documentation, not a valid submission archive.

The competition provides get_code_neighbors, search_similar_code and get_code_subgraph. Reimplementing them locally does not replace their registered harness implementations. The standalone toolkit can support offline experiments; competition skills/scripts must execute through the permitted sandbox facilities.

Before producing agent.yaml:
1. Obtain the exact official HARNESS_README.md, sample config and wheel versions.
2. Inspect actual graph and embedding schemas.
3. Build prompts and skills against registered tool names and response formats.
4. Validate includes, model selection, archive paths and script execution with the official compiler.
5. Run smoke tasks, patch controls and a full offline evaluation.

The [main competition](https://www.kaggle.com/competitions/gemma-4-developer-agent) and [paper track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper) have different deliverables. A toolkit is a potential paper-track resource; it is not by itself a scored patch-producing agent. No Kaggle entry or submission has been made by this project.
