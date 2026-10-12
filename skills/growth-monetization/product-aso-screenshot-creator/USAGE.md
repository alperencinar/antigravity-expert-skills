# product-aso-screenshot-creator Usage Guide

This guide describes how to use the `product-aso-screenshot-creator` commands to generate App Store and Google Play screenshot assets.

---

## Commands Map

| Command | File | Purpose | Subcommands / Parameters |
| :--- | :--- | :--- | :--- |
| `/screenshot-spec` | [screenshot-spec.md](./commands/screenshot-spec.md) | Copywriting, localization, and story flow planning. | `tr`, `en` localizations, emotional hooks. |
| `/screenshot-generate` | [screenshot-generate.md](./commands/screenshot-generate.md) | Mockup scaling, layout rules, and generator prompts. | Aspect ratios (e.g. `3:4`), mockup sizes. |
| `/screenshot-process` | [screenshot-process.md](./commands/screenshot-process.md) | Automated resizing, JPEGs formatting, and file renaming. | `scripts/process_screenshots.sh` execution. |

---

## Typical Production Workflow

Follow these steps sequentially to generate a set of screenshots:

1.  **Draft the Copy Specs:**
    *   Open [screenshot-spec.md](./commands/screenshot-spec.md).
    *   Verify the emotional value and the list of headlines. Ensure no brand name is repeated.
2.  **Generate Banners:**
    *   Use the prompt template from [screenshot-generate.md](./commands/screenshot-generate.md).
    *   Embed raw screenshots as references.
    *   Ensure the device mockups are scaled to occupy **85% of the frame** and the top margins are close to the edge.
3.  **Process and Export:**
    *   Run the script as documented in [screenshot-process.md](./commands/screenshot-process.md):
        ```bash
        ./.agents/skills/product-aso-screenshot-creator/scripts/process_screenshots.sh <input_dir> <output_dir> 2064 2752 jpeg
        ```
    *   Confirm dimensions of the generated JPEGs in the output directory.
