from app.services.documents import split_chunks
from app.core.security import hash_password, verify_password

def test_password_hashing():
    value = hash_password("correct horse battery staple")
    assert value != "correct horse battery staple"
    assert verify_password("correct horse battery staple", value)
    assert not verify_password("wrong password", value)

def test_chunking_overlaps_and_covers_text():
    chunks = split_chunks("A" * 1700 + "\n" + "B" * 600, size=800, overlap=100)
    assert len(chunks) >= 3
    assert all(chunks)
    assert any("B" in chunk for chunk in chunks)
