from pathlib import Path


def test_readme_does_not_claim_certification():
    text = Path("README.md").read_text().lower()
    assert "not a certification badge" in text
    assert "owasp certified scqos" in text
