# -*- coding: utf-8 -*-
import unittest
import logging
import gpsoauth
import json
import six

if six.PY2:
    import mock
else:
    from unittest import mock

from gkeepapi import Keep, node

logging.getLogger(node.__name__).addHandler(logging.NullHandler())

def resp(name):
    with open('test/data/%s' % name, 'r') as fh:
        return json.load(fh)

def mock_keep(keep):
    k_api = mock.MagicMock()
    r_api = mock.MagicMock()
    m_api = mock.MagicMock()
    keep._keep_api._session = k_api
    keep._reminders_api._session = r_api
    keep._media_api._session = m_api

    return k_api, r_api, m_api

class KeepTests(unittest.TestCase):
    @mock.patch('gpsoauth.perform_oauth')
    @mock.patch('gpsoauth.perform_master_login')
    def test_sync(self, perform_master_login, perform_oauth):
        keep = Keep()
        k_api, r_api, m_api = mock_keep(keep)

        perform_master_login.return_value = {
            'Token': 'FAKETOKEN',
        }
        perform_oauth.return_value = {
            'Auth': 'FAKEAUTH',
        }
        k_api.request().json.side_effect = [
            resp('keep-00'),
        ]
        r_api.request().json.side_effect = [
            resp('reminder-00'),
            resp('reminder-01'),
        ]
        keep.login('user', 'pass')

        self.assertEqual(39, len(keep.all()))
