import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

DB_FILE = os.path.join(tempfile.gettempdir(), 'uptime-monitor-status-fallback.sqlite3')
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

os.environ['DATABASE_URL'] = f'sqlite:///{DB_FILE}'
os.environ['REDIS_SENTINEL_HOSTS'] = '10.255.255.1:26379'
os.environ['REDIS_MASTER_NAME'] = 'mymaster'

from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, SessionLocal, engine
from app.models import Check, Target


class StatusFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            target = Target(
                name='google',
                url='https://google.com/',
                interval_sec=30,
                timeout_ms=3000,
                enabled=True,
            )
            db.add(target)
            db.flush()
            db.add(Check(
                target_id=target.id,
                ts=datetime(2026, 5, 19, 11, 0, tzinfo=timezone.utc),
                ok=True,
                status_code=200,
                latency_ms=123,
                error=None,
            ))
            db.commit()
        finally:
            db.close()
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_status_one_falls_back_to_db_when_cache_errors(self):
        with patch('app.main.cache_get_last', side_effect=RuntimeError('redis down')):
            response = self.client.get('/status/1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['target_id'], 1)
        self.assertEqual(response.json()['status_code'], 200)
        self.assertTrue(response.json()['ok'])

    def test_status_list_falls_back_to_db_when_cache_errors(self):
        with patch('app.main.cache_get_last', side_effect=RuntimeError('redis down')):
            response = self.client.get('/status')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['target_id'], 1)
        self.assertEqual(response.json()[0]['status_code'], 200)


if __name__ == '__main__':
    unittest.main()
