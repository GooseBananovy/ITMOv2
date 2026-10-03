import unittest

from app.review import MAX_DIFF_BYTES, review_diff


class FakeClient:
    """Клиент, который запоминает вызов и не ходит в сеть."""

    def __init__(self, answer="замечаний нет"):
        self.answer = answer
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return self.answer


class ExplodingClient:
    """Клиент, который падает при вызове — для проверки отказов."""

    def complete(self, system, user):
        raise AssertionError("модель не должна вызываться при отказе")


class ReviewDiffTest(unittest.TestCase):
    def test_rejects_empty_diff_without_calling_model(self):
        result = review_diff("", client=ExplodingClient())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "empty_diff")
        self.assertTrue(result["message"])

    def test_rejects_whitespace_only_diff_without_calling_model(self):
        result = review_diff("   \n\t  ", client=ExplodingClient())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "empty_diff")
        self.assertTrue(result["message"])

    def test_rejects_oversized_diff_without_calling_model(self):
        oversized = "a" * (MAX_DIFF_BYTES + 1)
        result = review_diff(oversized, client=ExplodingClient())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "diff_too_large")
        self.assertTrue(result["message"])

    def test_rejects_oversized_diff_counted_in_bytes_not_characters(self):
        # "ы" занимает 2 байта в UTF-8: символов меньше MAX_DIFF_BYTES,
        # а байт — больше, отказ должен считаться по байтам.
        oversized = "ы" * (MAX_DIFF_BYTES // 2 + 1)
        result = review_diff(oversized, client=ExplodingClient())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "diff_too_large")

    def test_accepts_diff_exactly_at_max_diff_bytes(self):
        exact = "a" * MAX_DIFF_BYTES
        client = FakeClient("ок")
        result = review_diff(exact, client=client)
        self.assertEqual(result["status"], "ok")

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
