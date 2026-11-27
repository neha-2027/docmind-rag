import os
import sys
import tempfile
import types
import unittest
from unittest import mock

from app import create_app
from rag.chunker import chunk_text
from rag.llm import SYSTEM_PROMPT, ClaudeLLM, ExtractiveLLM, build_prompt
from rag.retriever import TfidfRetriever
from rag.service import NOT_FOUND, RagService
from rag.storage import LocalStorage, S3Storage, safe_name


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, question, hits):
        self.calls.append((question, hits))
        return "fake answer [1]"


class ChunkerTests(unittest.TestCase):
    def test_overlap_and_coverage(self):
        text = " ".join(f"w{i}" for i in range(50))
        chunks = chunk_text(text, "doc.txt", chunk_words=20, overlap=5)
        self.assertEqual(chunks[0].text.split()[-5:], chunks[1].text.split()[:5])
        self.assertIn("w49", chunks[-1].text)
        self.assertEqual([c.index for c in chunks], list(range(len(chunks))))

    def test_short_and_empty_text(self):
        self.assertEqual(len(chunk_text("just a few words", "d.txt")), 1)
        self.assertEqual(chunk_text("   ", "d.txt"), [])

    def test_bad_parameters(self):
        with self.assertRaises(ValueError):
            chunk_text("a b c", "d.txt", chunk_words=10, overlap=10)


class RetrieverTests(unittest.TestCase):
    def setUp(self):
        docs = {
            "sql.md": "A LEFT JOIN returns every row from the left table and matching rows from the right table.",
            "git.md": "A merge conflict happens when two branches change the same lines of a file.",
        }
        chunks = [c for n, t in docs.items() for c in chunk_text(t, n)]
        self.retriever = TfidfRetriever(chunks)

    def test_returns_most_relevant_first(self):
        hits = self.retriever.search("what does a left join return", top_k=2)
        self.assertEqual(hits[0][0].source, "sql.md")

    def test_irrelevant_question_returns_nothing(self):
        self.assertEqual(self.retriever.search("recipe for chocolate cake"), [])

    def test_empty_inputs(self):
        self.assertEqual(self.retriever.search("   "), [])
        self.assertEqual(TfidfRetriever([]).search("anything"), [])

    def test_documents_with_only_stop_words_do_not_crash(self):
        self.assertEqual(TfidfRetriever(chunk_text("the and of to", "x.txt")).search("the"), [])


class LlmTests(unittest.TestCase):
    def setUp(self):
        self.hits = [(chunk_text("Flask is a Python web framework. It has no database layer.", "flask.md")[0], 0.9)]

    def test_prompt_numbers_sources_and_includes_question(self):
        prompt = build_prompt("What is Flask?", self.hits)
        self.assertIn("[1] (source: flask.md)", prompt)
        self.assertIn("Question: What is Flask?", prompt)

    def test_extractive_prefers_relevant_sentence(self):
        answer = ExtractiveLLM().generate("Does Flask have a database layer?", self.hits)
        self.assertTrue(answer.startswith("It has no database layer."))

    def test_claude_llm_sends_grounding_system_prompt(self):
        captured = {}

        class FakeMessages:
            def create(self, **kwargs):
                captured.update(kwargs)
                block = types.SimpleNamespace(type="text", text="Flask is a framework [1]")
                return types.SimpleNamespace(content=[block])

        fake_module = types.SimpleNamespace(
            Anthropic=lambda api_key=None: types.SimpleNamespace(messages=FakeMessages())
        )
        with mock.patch.dict(sys.modules, {"anthropic": fake_module}):
            answer = ClaudeLLM(api_key="test-key", model="some-model").generate("What is Flask?", self.hits)
        self.assertEqual(answer, "Flask is a framework [1]")
        self.assertEqual(captured["system"], SYSTEM_PROMPT)
        self.assertEqual(captured["model"], "some-model")
        self.assertIn("What is Flask?", captured["messages"][0]["content"])


class StorageTests(unittest.TestCase):
    def test_safe_name_blocks_path_tricks(self):
        for bad in ("../secret.txt", "a/b.md", "..\\x.md", "notes.exe", "", None, ".hidden.md"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                safe_name(bad)
        self.assertEqual(safe_name("notes-1.md"), "notes-1.md")

    def test_local_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            storage = LocalStorage(root)
            storage.write("a.md", "hello")
            self.assertEqual(storage.list_names(), ["a.md"])
            self.assertEqual(storage.read("a.md"), "hello")

    def test_s3_storage_uses_prefix_and_filters_keys(self):
        calls = {}

        class FakeBody:
            def read(self):
                return b"s3 text"

        class FakePaginator:
            def paginate(self, **kwargs):
                calls["paginate"] = kwargs
                return [{"Contents": [{"Key": "docs/a.md"}, {"Key": "docs/img.png"}, {"Key": "docs/sub/b.md"}]}]

        class FakeS3:
            def get_paginator(self, _name):
                return FakePaginator()

            def get_object(self, **kwargs):
                calls["get"] = kwargs
                return {"Body": FakeBody()}

            def put_object(self, **kwargs):
                calls["put"] = kwargs

        fake_boto3 = types.SimpleNamespace(client=lambda _service: FakeS3())
        with mock.patch.dict(sys.modules, {"boto3": fake_boto3}):
            storage = S3Storage("my-bucket", "docs/")
            self.assertEqual(storage.list_names(), ["a.md"])
            self.assertEqual(storage.read("a.md"), "s3 text")
            storage.write("c.md", "x")
        self.assertEqual(calls["paginate"], {"Bucket": "my-bucket", "Prefix": "docs/"})
        self.assertEqual(calls["get"], {"Bucket": "my-bucket", "Key": "docs/a.md"})
        self.assertEqual(calls["put"]["Key"], "docs/c.md")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        storage = LocalStorage(self.tmp.name)
        storage.write("sql.md", "A LEFT JOIN returns every row from the left table and matching rows from the right table.")
        self.llm = FakeLLM()
        self.service = RagService(storage, self.llm)

    def tearDown(self):
        self.tmp.cleanup()

    def test_answer_includes_sources(self):
        result = self.service.ask("What does a LEFT JOIN return?")
        self.assertTrue(result["used_llm"])
        self.assertEqual(result["sources"][0]["source"], "sql.md")

    def test_no_relevant_passage_skips_llm(self):
        result = self.service.ask("What is the capital of France?")
        self.assertEqual(result["answer"], NOT_FOUND)
        self.assertFalse(result["used_llm"])
        self.assertEqual(self.llm.calls, [])

    def test_new_document_becomes_searchable(self):
        self.service.add_document("git.md", "A merge conflict happens when two branches change the same lines.")
        result = self.service.ask("What causes a merge conflict?")
        self.assertEqual(result["sources"][0]["source"], "git.md")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        storage = LocalStorage(self.tmp.name)
        storage.write("sql.md", "A LEFT JOIN returns every row from the left table and matching rows from the right table.")
        self.llm = FakeLLM()
        self.client = create_app(RagService(storage, self.llm)).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ask(self):
        res = self.client.post("/ask", json={"question": "What does a LEFT JOIN return?"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["answer"], "fake answer [1]")
        self.assertEqual(body["sources"][0]["ref"], 1)

    def test_ask_validation(self):
        for payload in ({}, {"question": ""}, {"question": "x" * 501}, {"question": "ok", "top_k": 0},
                        {"question": "ok", "top_k": True}, {"question": 5}):
            self.assertEqual(self.client.post("/ask", json=payload).status_code, 400, payload)
        self.assertEqual(self.client.post("/ask", data="no", content_type="text/plain").status_code, 400)

    def test_llm_failure_returns_502_without_details(self):
        def boom(question, hits):
            raise RuntimeError("secret internal detail")

        self.llm.generate = boom
        res = self.client.post("/ask", json={"question": "What does a LEFT JOIN return?"})
        self.assertEqual(res.status_code, 502)
        self.assertNotIn("secret", res.get_data(as_text=True))

    def test_upload_and_list_documents(self):
        res = self.client.post("/documents", json={"name": "notes.md", "text": "Docker packages apps into containers."})
        self.assertEqual(res.status_code, 201)
        names = [d["name"] for d in self.client.get("/documents").get_json()["documents"]]
        self.assertEqual(names, ["notes.md", "sql.md"])

    def test_upload_rejects_bad_input(self):
        bad = [
            {"name": "../evil.md", "text": "x"},
            {"name": "a.exe", "text": "x"},
            {"name": "ok.md", "text": ""},
            {"name": "ok.md", "text": "x" * 200_001},
        ]
        for payload in bad:
            self.assertEqual(self.client.post("/documents", json=payload).status_code, 400, payload["name"])

    def test_health_home_404(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/missing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
