# Lastkajen inventory setup

This workflow only lists available Lastkajen data packages and file metadata. It does not download datasets, commit results, or publish to GitHub Pages.

1. Open Settings > Secrets and variables > Actions > New repository secret.
2. Add LASTKAJEN_USERNAME and LASTKAJEN_PASSWORD.
3. Open Actions > Inventory Lastkajen data packages > Run workflow.
4. Test first with package_limit 5, then 0 to inventory all available packages.
5. Download the lastkajen-inventory artifact from the run to inspect JSON.

The artifact can contain metadata from access-controlled catalogues. Since this repository is public, review access to GitHub Actions artifacts before downloading or sharing; for strict confidentiality, run this inventory in a private repository.

Reference: Trafikverket Lastkajen API guide v1.4 (2023-01-24), sections 2.1-2.3. Actual API compatibility must be confirmed by a live run.
