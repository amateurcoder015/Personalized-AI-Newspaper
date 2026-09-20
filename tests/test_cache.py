import tempfile
from app.database import DatabaseManager
from app.llm.cache import LLMCache


def test_llm_cache_put_and_get():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db = DatabaseManager(db_path=f"{tmp_dir}/test.db")
        cache = LLMCache(db=db, enabled=True)

        prompt = "Summarize RBI monetary policy announcement"
        model = "gpt-3.5-turbo"
        response = "RBI kept the repo rate unchanged at 6.5%."

        # Cache Miss initially
        cached_val = cache.get(prompt, model)
        assert cached_val is None

        # Put in cache
        cache.put(prompt, model, response)

        # Cache Hit now
        cached_val = cache.get(prompt, model)
        assert cached_val == response
        assert cache.cache_hits == 1
