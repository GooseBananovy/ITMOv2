import unittest

from app.review import review_diff


class FakeClient:
    """Клиент, который запоминает вызов и не ходит в сеть."""

    def __init__(self, answer="замечаний нет"):
        self.answer = answer
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return self.answer


class ReviewDiffTest(unittest.TestCase):
    def test_returns_model_answer(self):
        client = FakeClient("нет проверки входа")
        result = review_diff("--- a\n+++ b\n+print(1)\n", client=client)
        self.assertEqual(result, {"status": "ok", "review": "нет проверки входа"})

    def test_sends_diff_to_model(self):
        client = FakeClient()
        review_diff("+print(1)", client=client)
        self.assertEqual(len(client.calls), 1)
        system, user = client.calls[0]
        self.assertIn("ревьюер", system)
        self.assertIn("+print(1)", user)


if __name__ == "__main__":
    unittest.main()
