import tempfile
from app.database import DatabaseManager
from app.learning.concept_selector import ConceptSelector


def test_concept_selection_and_rotation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db = DatabaseManager(db_path=f"{tmp_dir}/test.db")
        selector = ConceptSelector(db=db, avoid_recent_days=30)

        headline_text = "US Treasury yields rise as bond prices fall"
        c1 = selector.select_concept(headline_text)
        assert "concept" in c1
        assert "numerical_example" in c1

        # Second run: c1 should be avoided and recorded in SQLite
        recent = db.get_recent_used_concepts(days=30)
        assert c1["concept"] in recent

        headline_text_2 = "TCS quarterly earnings margin expands"
        c2 = selector.select_concept(headline_text_2)
        assert c2["concept"] != c1["concept"]
