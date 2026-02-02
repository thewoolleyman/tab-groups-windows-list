"""Shared test fixtures for ADWS test suite.

Scaffold story (1.1) - infrastructure only. Fixtures will be added in Story 1.2
when the types they depend on are implemented:

- mock_io_ops: Mocked io_ops module (common mock patterns
  for file ops, subprocess, SDK calls)
- sample_workflow_context: Sample WorkflowContext instances
  (with/without issue IDs, feedback)
- sample_result_message: Sample ResultMessage objects (realistic SDK responses)
- sample_beads_issue: Sample Beads issue data (for bridge step tests)
- sample_bmad_story: Sample BMAD story markdown (for parse step tests)

See: architecture.md § conftest.py Shared Fixtures (porting requirement)
"""
