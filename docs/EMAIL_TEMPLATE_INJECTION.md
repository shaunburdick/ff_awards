# Email Template Injection Feature

## Overview
The email HTML output now supports optional metadata injection via HTML comment markers. This allows GitHub Actions (or other automation) to add runtime information without affecting local CLI usage.

## How It Works

### 1. Default Behavior (CLI Usage)
When you run the tool locally:
```bash
uv run ff-tracker --env --format email > report.html
```

The HTML contains invisible markers:
```html
<div class="footer">
    Game data: 180 individual results processed<br>
    <!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END --><strong>Fantasy Football Challenge Tracker</strong><br>
    <a href="https://github.com/shaunburdick/ff_awards">View on GitHub 🔗</a>
</div>
```

**Rendered output:**
- Game data: 180 individual results processed
- **Fantasy Football Challenge Tracker**
- View on GitHub 🔗

The HTML comments are invisible when viewed in a browser or email client.

### 2. GitHub Actions Enhancement
The workflow automatically injects metadata:

```yaml
- name: Prepare email content
  run: |
    GENERATED_TIME=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    EXECUTION_TIME="${{ steps.generate-report.outputs.execution_time }}"
    RUN_ID="${{ github.run_id }}"
    REPO="${{ github.repository }}"

    METADATA_HTML="Generated: ${GENERATED_TIME} (took ${EXECUTION_TIME}s)<br>"
    METADATA_HTML+="<a href=\"https://github.com/${REPO}/actions/runs/${RUN_ID}\">Download Full Report Artifacts 📦</a><br>"

    sed -i "s|<!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END -->|<!-- GENERATED_METADATA_START -->${METADATA_HTML}<!-- GENERATED_METADATA_END -->|g" ./reports/standings.html
```

**Rendered output (emails only):**
- Game data: 180 individual results processed
- Generated: 2024-10-25 10:00:00 UTC (took 5s)
- Download Full Report Artifacts 📦
- **Fantasy Football Challenge Tracker**
- View on GitHub 🔗

## Benefits

1. **Transparency**: Email recipients can see when the report was generated
2. **Performance Tracking**: Execution time helps identify performance issues
3. **Easy Access**: Direct link to download all report formats (TSV, JSON, Markdown)
4. **No Impact on CLI**: Local usage remains unchanged
5. **Extensible**: Easy to add more metadata in the future

## Adding Custom Metadata

You can inject any HTML between the markers:

```bash
# Example: Add custom message
CUSTOM_HTML="<strong>Special Note:</strong> Playoff brackets updated!<br>"
sed -i "s|<!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END -->|<!-- GENERATED_METADATA_START -->${CUSTOM_HTML}<!-- GENERATED_METADATA_END -->|g" report.html
```

## Technical Details

- **Markers**: `<!-- GENERATED_METADATA_START -->` and `<!-- GENERATED_METADATA_END -->`
- **Location**: Email footer, always present (even with empty challenges)
- **Format**: Any valid HTML can be injected
- **Preservation**: Markers remain after injection for debugging
- **Visibility**: HTML comments are invisible in rendered output
