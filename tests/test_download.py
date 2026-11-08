import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fnm.engine import Conflict
from fnm.updater import fetch


@unittest.skipUnless(os.name == 'nt', 'Windows certificate-store transport')
class DownloadTests(unittest.TestCase):
    def test_windows_transport_keeps_tls_verification_and_bounds(self):
        with patch('fnm.updater.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=b'body', stderr=b'')) as call:
            self.assertEqual(fetch('https://api.github.com/example'), b'body')
            command = call.call_args.args[0]
            self.assertIn('--max-filesize', command)
            self.assertIn('--proto-redir', command)
            self.assertNotIn('-k', command)
            self.assertNotIn('--insecure', command)

    def test_failed_tls_download_is_not_retried_insecurely(self):
        with patch('fnm.updater.subprocess.run', return_value=SimpleNamespace(returncode=60, stdout=b'', stderr=b'certificate error')) as call:
            with self.assertRaisesRegex(Conflict, 'certificate error'):
                fetch('https://api.github.com/example')
            self.assertEqual(call.call_count, 1)

    def test_oversized_response_is_refused(self):
        with patch('fnm.updater.LIMIT', 5), patch('fnm.updater.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=b'123456', stderr=b'')):
            with self.assertRaisesRegex(Conflict, 'limit'):
                fetch('https://api.github.com/example')
