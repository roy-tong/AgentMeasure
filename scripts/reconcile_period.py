#!/usr/bin/env python3
"""Run an opt-in, period-scoped review in a private GitHub repository."""
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def validate_config(config, root, scheduled=False, today=None):
    vendor = config.get('vendor', '')
    period = config.get('billing_period', '')
    if not re.fullmatch(r'[a-z][a-z0-9_-]*', vendor):
        raise ValueError('vendor must be a registry id')
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
        raise ValueError('billing_period is required as YYYY-MM')
    if scheduled:
        today = today or datetime.date.today()
        expected = (today.replace(day=1) - datetime.timedelta(days=1)).strftime('%Y-%m')
        if period != expected:
            raise ValueError('Stale export configuration: scheduled run requires ' + expected)
    relative = config.get('export', '.verovo/recount-export.csv')
    if not isinstance(relative, str) or '\n' in relative or '\r' in relative:
        raise ValueError('export must be a repository-relative path')
    root = Path(root).resolve()
    export = (root / relative).resolve()
    if not export.is_relative_to(root) or not export.is_file():
        raise ValueError('export must exist inside this repository')
    if config.get('reviewed_export_sha256') != __import__('hashlib').sha256(export.read_bytes()).hexdigest():
        raise ValueError('Review the export for this period and set reviewed_export_sha256')
    if not isinstance(config.get('open_tracking_issue', False), bool):
        raise ValueError('open_tracking_issue must be true or false')
    return vendor, period, export


def needs_review(result):
    counts = result['counts']
    return any(counts.get(k, 0) > 0 for k in (
        'billed_but_not_billable', 'billable_but_not_billed', 'cannot_settle'))


def main():
    config_path = Path('.verovo/reconcile.json')
    if not config_path.is_file():
        raise ValueError('No config; follow RECONCILE.md before running')
    config = json.loads(config_path.read_text())
    vendor, period, export = validate_config(config, Path.cwd(), os.getenv('GITHUB_EVENT_NAME') == 'schedule')
    completed = subprocess.run(['verovo', 'recount', '--export', str(export),
                                '--vendor', vendor, '--json', 'recount-result.json'],
                               check=True, capture_output=True, text=True)
    report = 'Billing period: ' + period + '\n' + completed.stdout
    Path('recount-report.txt').write_text(report)
    result = json.loads(Path('recount-result.json').read_text())
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as stream:
            stream.write('## Period review\n\n```text\n' + report + '\n```\n')
    if not config.get('open_tracking_issue', False) or not needs_review(result):
        return
    title = 'Bill review: ' + vendor + ' ' + period
    # This is an evidence review, including offsetting differences and unknowns.
    # A zero net amount cannot suppress an unresolved task.
    body = ('Review this period: findings may offset or remain unknown. Published-price '
            'arithmetic is not a verified invoice or refund.\n\n```text\n' + report + '\n```\n')
    body_path = Path('recount-issue.md')
    body_path.write_text(body)
    listing = subprocess.run(['gh', 'issue', 'list', '--state', 'open', '--limit', '100',
                              '--search', title + ' in:title', '--json', 'number,title'],
                             check=True, capture_output=True, text=True)
    existing = next((x for x in json.loads(listing.stdout) if x['title'] == title), None)
    if existing:
        subprocess.run(['gh', 'issue', 'edit', str(existing['number']), '--body-file', str(body_path)], check=True)
    else:
        subprocess.run(['gh', 'issue', 'create', '--title', title, '--body-file', str(body_path)], check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('Period review stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
