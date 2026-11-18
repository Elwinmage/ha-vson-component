#!/bin/bash
# Print the line coverage written by the pytest hook to reports/coverage.xml
# and fail unless it reaches 100 %.
report="reports/coverage.xml"
if [ ! -f "${report}" ]; then
    echo "${report} not found: run the pytest hook first" >&2
    exit 1
fi
val=$(head -n 2 "${report}" | grep -Eo 'line-rate="[0-9.]+"' | head -n 1 | cut -d '"' -f 2)
percent=$(awk -v v="${val}" 'BEGIN { printf "%.2f", v * 100 }')
echo "${percent}%"
awk -v v="${val}" 'BEGIN { exit !(v >= 1) }'
