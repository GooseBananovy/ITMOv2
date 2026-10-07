import http.client
import socket
import unittest
import urllib.error

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


class TimeoutClient:
    """Клиент, имитирующий истечение ожидания ответа модели."""

    def complete(self, system, user):
        raise socket.timeout("timed out")


class UnavailableClient:
    """Клиент, имитирующий отсутствие соединения с моделью."""

    def complete(self, system, user):
        raise urllib.error.URLError("connection refused")


class HttpErrorClient:
    """Клиент, имитирующий HTTP-ошибку модели."""

    def complete(self, system, user):
        raise urllib.error.HTTPError(
            "http://localhost:11434/api/chat", 500, "Internal Server Error", None, None
        )


class BadResponseClient:
    """Клиент, имитирующий ответ без ожидаемых полей."""

    def complete(self, system, user):
        raise KeyError("message")


class IncompleteReadClient:
    """Клиент, имитирующий обрыв соединения посреди ответа.

    Сервер объявил Content-Length, но прислал меньше байт и закрыл
    соединение — urllib поднимает http.client.IncompleteRead.
    """

    def complete(self, system, user):
        raise http.client.IncompleteRead(b"partial")


class BadStatusLineClient:
    """Клиент, имитирующий нераспознаваемую стартовую строку HTTP-ответа."""

    def complete(self, system, user):
        raise http.client.BadStatusLine("garbage")


class RemoteDisconnectedClient:
    """Клиент, имитирующий разрыв соединения сервером без ответа.

    http.client.RemoteDisconnected наследуется и от HTTPException, и от
    ConnectionResetError (а значит, и от OSError) — неоднозначный случай,
    который проверяет выбор ветки в review_diff.
    """

    def complete(self, system, user):
        raise http.client.RemoteDisconnected(
            "Remote end closed connection without response"
        )


class TransportErrorClient:
    """Клиент, имитирующий транспортную ошибку ОС, не относящуюся к HTTP."""

    def complete(self, system, user):
        raise ConnectionRefusedError("connection refused by OS")


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

    def test_returns_model_timeout_when_wait_expires(self):
        result = review_diff("+print(1)", client=TimeoutClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_timeout")
        self.assertTrue(result["message"])

    def test_returns_model_unavailable_when_connection_fails(self):
        result = review_diff("+print(1)", client=UnavailableClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_unavailable")
        self.assertTrue(result["message"])

    def test_returns_model_http_error_when_model_responds_with_http_error(self):
        result = review_diff("+print(1)", client=HttpErrorClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_http_error")
        self.assertTrue(result["message"])

    def test_returns_model_bad_response_when_fields_are_missing(self):
        result = review_diff("+print(1)", client=BadResponseClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_bad_response")
        self.assertTrue(result["message"])

    def test_returns_model_bad_response_when_connection_breaks_mid_read(self):
        result = review_diff("+print(1)", client=IncompleteReadClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_bad_response")
        self.assertTrue(result["message"])

    def test_returns_model_bad_response_when_status_line_is_unparseable(self):
        result = review_diff("+print(1)", client=BadStatusLineClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_bad_response")
        self.assertTrue(result["message"])

    def test_returns_model_bad_response_when_remote_disconnects_without_response(self):
        # RemoteDisconnected — одновременно HTTPException и OSError;
        # правило классификации отдаёт приоритет протокольной ветке.
        result = review_diff("+print(1)", client=RemoteDisconnectedClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_bad_response")
        self.assertTrue(result["message"])

    def test_returns_model_unavailable_when_transport_error_occurs(self):
        result = review_diff("+print(1)", client=TransportErrorClient())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "model_unavailable")
        self.assertTrue(result["message"])


if __name__ == "__main__":
    unittest.main()
