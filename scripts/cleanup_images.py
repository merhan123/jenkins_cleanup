"""Preview and remove explicitly labelled, unused dangling Docker images."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, timeout=60).strip()


def candidates(label, hours, now=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+=[A-Za-z0-9_.-]+', label):
        raise ValueError('Label must be an explicit key=value using letters, numbers, dots, underscores or hyphens')
    if not 24 <= hours <= 87600:
        raise ValueError('Minimum age must be between 24 and 87600 hours')
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=hours)
    ids = docker('image', 'ls', '--quiet', '--no-trunc', '--filter', 'dangling=true', '--filter', 'label='+label).split()
    container_ids = docker('container', 'ls', '--all', '--quiet', '--no-trunc').split()
    used = set()
    for cid in container_ids:
        used.add(json.loads(docker('container', 'inspect', cid))[0]['Image'])
    key, value = label.split('=', 1)
    result = []
    for image_id in sorted(set(ids)):
        item = json.loads(docker('image', 'inspect', image_id))[0]
        created = datetime.fromisoformat(item['Created'].replace('Z', '+00:00'))
        tags = item.get('RepoTags') or []
        labels = (item.get('Config') or {}).get('Labels') or {}
        if item['Id'] in used or tags or labels.get(key) != value or created >= cutoff:
            continue
        result.append({'id': item['Id'], 'created': item['Created'], 'size_bytes': item['Size']})
    return result


def apply(plan, label, hours, report):
    # Re-query before every removal; never expand the reviewed candidate set.
    results = []
    try:
        for item in plan['images']:
            image_id = item['id']
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
                raise ValueError('Invalid image ID in plan')
            eligible = {x['id'] for x in candidates(label, hours)}
            if image_id not in eligible:
                results.append({'id': image_id, 'status': 'skipped: no longer eligible'})
                continue
            try:
                output = docker('image', 'rm', '--no-prune', image_id)
                results.append({'id': image_id, 'status': 'removed', 'output': output})
            except subprocess.SubprocessError:
                results.append({'id': image_id, 'status': 'failed'})
                raise
    finally:
        report.write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'apply'])
    parser.add_argument('--label', required=True)
    parser.add_argument('--hours', type=int, required=True)
    parser.add_argument('--plan', default='cleanup-plan.json')
    args = parser.parse_args()
    daemon = docker('info', '--format', '{{.ID}}')
    if not daemon:
        raise ValueError('Docker daemon identity is unavailable')
    path = Path(args.plan)
    if args.mode == 'plan':
        plan = {'daemon': daemon, 'label': args.label, 'hours': args.hours,
                'images': candidates(args.label, args.hours)}
        path.write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(plan, indent=2))
        print(f"Selected {len(plan['images'])} images; sizes are not a reclaimed-space estimate.")
    else:
        plan = json.loads(path.read_text(encoding='utf-8'))
        if (plan['daemon'], plan['label'], plan['hours']) != (daemon, args.label, args.hours):
            raise ValueError('Daemon or retention settings differ from the reviewed plan')
        apply(plan, args.label, args.hours, Path('cleanup-results.json'))


if __name__ == '__main__':
    main()
