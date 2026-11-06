import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "sip_chatbot_web", Path(__file__).with_name("sip-chatbot-web.py")
)
web = importlib.util.module_from_spec(spec)
with patch("shutil.which", return_value="copilot"):
    spec.loader.exec_module(web)


class RunCopilotTests(unittest.TestCase):
    def test_prompt_is_sent_only_through_stdin(self):
        prompt = 'Instructions\nClient description:\nErrore "consegna" & stampa\nTickets:\n{"results":[]}'
        with patch.object(web, "COPILOT", "copilot.CMD"), patch.object(
            web.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, '{"results":[]}', ""),
        ) as run:
            self.assertEqual(web.run_copilot(prompt), '{"results":[]}')
        run.assert_called_once_with(
            ["copilot.CMD", "--silent"], input=prompt, capture_output=True,
            text=True, encoding="utf-8", timeout=web.LLM_TIMEOUT,
        )

    def test_multiline_unicode_prompt_survives_pipe(self):
        prompt = 'Instructions\nClient description:\nPerché "errore" & stampa %PATH%?\nTickets:\n' + "x" * 20000
        real_run = subprocess.run

        def echo_stdin(cmd, **kwargs):
            return real_run(
                [sys.executable, "-c",
                 "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
                **kwargs,
            )

        with patch.object(web.subprocess, "run", side_effect=echo_stdin):
            self.assertEqual(web.run_copilot(prompt), prompt)

    def test_nonzero_exit_reports_stderr(self):
        with patch.object(web.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 1, "", "authentication failed"
        )):
            with self.assertRaisesRegex(RuntimeError, "authentication failed"):
                web.run_copilot("prompt")

    def test_empty_reply_is_rejected(self):
        with patch.object(web.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, " \n", ""
        )):
            with self.assertRaisesRegex(RuntimeError, "empty reply"):
                web.run_copilot("prompt")

    def test_timeout_propagates(self):
        with patch.object(web.subprocess, "run", side_effect=subprocess.TimeoutExpired(
            "copilot", web.LLM_TIMEOUT
        )):
            with self.assertRaises(subprocess.TimeoutExpired):
                web.run_copilot("prompt")


if __name__ == "__main__":
    unittest.main()
