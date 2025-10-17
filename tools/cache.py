"""
cache.py

A simple file-based cache with TTL, safe and small. Use this to cache Apify responses keyed by query.

Usage:
from tools.cache import FileCache
cache = FileCache('tools/cache_store.json', default_ttl=86400)
val = cache.get('marketing')
if val is None:
    val = expensive_request('marketing')
    cache.set('marketing', val)

"""
import json
import os
import time
from typing import Any, Optional


class FileCache:
    def __init__(self, path: str, default_ttl: int = 86400):
        self.path = path
        self.default_ttl = int(default_ttl)
        self._data = None
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self._data = {}
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def _save(self):
        tmp = self.path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        rec = self._data.get(key)
        if not rec:
            return None
        if 'expires_at' in rec and rec['expires_at'] and rec['expires_at'] < time.time():
            # expired
            try:
                del self._data[key]
            except KeyError:
                pass
            self._save()
            return None
        return rec.get('value')

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        rec = {
            'value': value,
            'expires_at': time.time() + int(ttl) if ttl > 0 else None,
            'created_at': time.time()
        }
        self._data[key] = rec
        self._save()

    def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()


# quick demo
if __name__ == '__main__':
    c = FileCache('tools/cache_store.json', default_ttl=60)
    print('set a')
    c.set('a', {'x': 1})
    print('get a', c.get('a'))
    time.sleep(2)
    print('get a', c.get('a'))
