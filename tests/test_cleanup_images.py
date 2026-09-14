from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).resolve().parents[1]/'scripts/cleanup_images.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)
IMAGE = 'sha256:'+'a'*64


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.item = {'Id': IMAGE, 'Created': '2020-01-01T00:00:00Z', 'Size': 12,
                     'RepoTags': [], 'Config': {'Labels': {'cleanup.enabled': 'true'}}}
        self.containers = []

    def fake(self, *args):
        if args[:2] == ('image', 'ls'): return IMAGE
        if args[:2] == ('container', 'ls'): return ' '.join(self.containers)
        if args[:2] == ('container', 'inspect'): return json.dumps([{'Image': IMAGE}])
        if args[:2] == ('image', 'inspect'): return json.dumps([self.item])
        raise AssertionError(args)

    def select(self):
        with patch.object(cleanup, 'docker', side_effect=self.fake):
            return cleanup.candidates('cleanup.enabled=true', 168, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_old_labelled_dangling_image_selected(self):
        self.assertEqual(self.select()[0]['id'], IMAGE)

    def test_tagged_image_retained(self):
        self.item['RepoTags'] = ['app:latest']
        self.assertEqual(self.select(), [])

    def test_stopped_container_image_retained(self):
        self.containers = ['stopped-container']
        self.assertEqual(self.select(), [])

    def test_young_image_retained(self):
        self.item['Created'] = '2025-12-31T00:00:00Z'
        self.assertEqual(self.select(), [])

    def test_unlabelled_image_retained(self):
        self.item['Config']['Labels'] = {}
        self.assertEqual(self.select(), [])

    def test_invalid_policy_fails_before_docker(self):
        with patch.object(cleanup, 'docker') as command:
            for label, hours in [('anything', 168), ('x=y', 0), ('x=y;rm', 168)]:
                with self.assertRaises(ValueError): cleanup.candidates(label, hours)
            command.assert_not_called()

    def test_apply_rechecks_and_skips_changed_image(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cleanup, 'candidates', return_value=[]), patch.object(cleanup, 'docker') as command:
            report = Path(folder)/'result.json'
            cleanup.apply({'images': [{'id': IMAGE}]}, 'cleanup.enabled=true', 168, report)
            command.assert_not_called()
            self.assertIn('skipped', json.loads(report.read_text())[0]['status'])

    def test_apply_uses_exact_id_without_force(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cleanup, 'candidates', return_value=[{'id': IMAGE}]), patch.object(cleanup, 'docker', return_value='deleted') as command:
            cleanup.apply({'images': [{'id': IMAGE}]}, 'cleanup.enabled=true', 168, Path(folder)/'result.json')
            command.assert_called_once_with('image', 'rm', '--no-prune', IMAGE)

    def test_failure_is_recorded_and_propagated(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cleanup, 'candidates', return_value=[{'id': IMAGE}]), patch.object(cleanup, 'docker', side_effect=subprocess.CalledProcessError(1, 'docker')):
            report = Path(folder)/'result.json'
            with self.assertRaises(subprocess.CalledProcessError):
                cleanup.apply({'images': [{'id': IMAGE}]}, 'cleanup.enabled=true', 168, report)
            self.assertEqual(json.loads(report.read_text())[0]['status'], 'failed')


if __name__ == '__main__': unittest.main()
