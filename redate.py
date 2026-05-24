"""
One-time script to rewrite all existing Add: commit dates
using the same map_commit_date() logic as committer.py.
Run once, then delete.
"""
import subprocess
from committer import map_commit_date

# Get all Add: commits: hash and author date
log = subprocess.run(
    ["git", "log", "--format=%H %aI %s", "--all"],
    capture_output=True, text=True, check=True,
).stdout.strip().splitlines()

mapping = {}  # hash → new ISO date
for line in log:
    parts = line.split(" ", 2)
    if len(parts) < 3:
        continue
    h, adate, subject = parts
    if not subject.startswith("Add:"):
        continue
    original_date = adate[:10]  # YYYY-MM-DD
    new_date = map_commit_date(original_date)
    if new_date != original_date:
        mapping[h] = new_date

if not mapping:
    print("Nothing to remap.")
    raise SystemExit

# Write mapping file for filter-branch to read
mapping_file = "/tmp/paper_redate.txt"
with open(mapping_file, "w") as f:
    for h, d in mapping.items():
        f.write(f"{h} {d}\n")

print(f"Remapping {len(mapping)} commits...")

env_filter = f"""
new_date=$(awk -v h="$GIT_COMMIT" '$1==h {{print $2}}' {mapping_file})
if [ -n "$new_date" ]; then
    # Preserve original time-of-day, just change the date
    orig_time=$(echo "$GIT_AUTHOR_DATE" | grep -oE 'T[0-9:]{{8}}' || echo "T12:00:00")
    export GIT_AUTHOR_DATE="${{new_date}}${{orig_time}}"
    export GIT_COMMITTER_DATE="${{new_date}}${{orig_time}}"
fi
"""

subprocess.run(
    ["git", "filter-branch", "-f", "--env-filter", env_filter, "HEAD"],
    check=True,
)

print("Done. Run: git push --force")
