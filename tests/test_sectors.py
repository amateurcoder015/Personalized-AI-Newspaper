from app.database.models import Story
from app.processing.sector_classifier import SectorClassifier


def test_sector_classification_banking():
    story = Story(
        headline="SBI and HDFC Bank Announce Deposit Interest Rate Revisions",
        summary="Commercial banks adjusted interest rates following RBI liquidity guidelines."
    )
    sector = SectorClassifier.classify_story(story)
    assert sector == "Banking & Financial Services"


def test_sector_classification_it():
    story = Story(
        headline="TCS Signs $500M Cloud Software Deal with European Client",
        summary="IT services major TCS expands enterprise cloud software delivery."
    )
    sector = SectorClassifier.classify_story(story)
    assert sector == "Information Technology"


def test_sector_classification_auto():
    story = Story(
        headline="Tata Motors Electric Vehicle Sales Rise 35% Year-on-Year",
        summary="EV battery adoption and new car models boost auto sales."
    )
    sector = SectorClassifier.classify_story(story)
    assert sector == "Automobiles"
