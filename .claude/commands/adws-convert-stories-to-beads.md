# /adws-convert-stories-to-beads

Convert BMAD stories to Beads issues with bidirectional tracking.

## Usage

Invoke this command to convert all stories in a BMAD epics markdown file into Beads issues. Each issue gets a workflow tag embedded, and the beads_id is written back to the source file.

## What it does

1. Parses the BMAD epics markdown file to extract epics and stories (FR24)
2. For each story, checks if it already has a beads_id (idempotent skip)
3. Creates a Beads issue via `bd create` with the story content and embedded workflow tag (FR25, FR26)
4. Writes the beads_id back into the source BMAD file's YAML front matter (FR27)
5. Reports progress: created, skipped, and failed counts per story
6. Continues processing remaining stories even if one fails (error isolation)

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch convert_stories_to_beads`

The dispatch routes to `run_convert_stories_command` in
`adws.adw_modules.commands.convert_stories`, which loads and
executes the `convert_stories_to_beads` workflow via `io_ops`.

All testable logic lives in `adws/adw_modules/commands/convert_stories.py` --
the .md file is the natural language entry point only (FR23).
