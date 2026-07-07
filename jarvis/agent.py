import json
import re

from jarvis.schemas import ChatResponse

SYSTEM_PROMPT = """You are Jarvis, a local personal AI assistant inspired by JARVIS.
You are in Phase 1: text only. Do not claim voice, phone access, smart home control,
or cloud access exists yet.

You can use tools for local files, terminal commands, and browser control.
Use tools when they are needed to answer accurately or complete a concrete action.
Be concise, practical, and explicit about what you did.
Never ask for passwords, one-time codes, or CAPTCHA solving.

File tools:
- list_files and read_file accept paths starting with ~/ (e.g. ~/Desktop, ~/Documents/notes.txt)
  to access anywhere under the user's home directory, not just the workspace.
- When asked to list or find files in a specific location, call list_files directly with that
  path. Do not guess what's there, and do not ask the user to run terminal commands themselves
  when a file tool can answer it directly.
- write_file and delete_file run immediately inside the workspace, but outside it they are
  queued and require the user to confirm via /api/confirm before anything happens — do not
  treat a "confirmation required" result as failure or as license to try a different tool.

If a tool call fails, try at most one reasonable alternative. If that also fails, stop and
report the failure clearly to the user with what you tried, instead of retrying repeatedly
or calling unrelated tools.

Once a tool call succeeds and its result already answers the request, respond with a final
text summary for the user instead of calling the same tool again.
"""

DEDUP_TOOLS = {"list_files", "read_file", "write_file", "delete_file"}


class JarvisAgent:
    def __init__(self, settings, llm, tools):
        self.settings = settings
        self.llm = llm
        self.tools = tools
        self.sessions = {}

    def chat(self, session_id, message):
        history = self.sessions.setdefault(session_id, [{"role": "system", "content": SYSTEM_PROMPT}])
        history.append({"role": "user", "content": message})
        tool_results = []
        last_key = None
        last_result = None
        repeat_count = 0

        for _ in range(self.settings.max_tool_calls):
            response = self.llm.chat(history, self.tools.schemas)
            assistant_message = response.get("message", {})
            history.append(assistant_message)

            calls = assistant_message.get("tool_calls") or []
            if not calls:
                fallback_call = self._extract_text_tool_call(assistant_message.get("content", ""))
                if fallback_call:
                    calls = [fallback_call]

            if not calls:
                return ChatResponse(
                    session_id=session_id,
                    answer=assistant_message.get("content", ""),
                    tool_results=tool_results,
                )

            for call in calls:
                function = call.get("function", {})
                name = function.get("name", "")
                raw_arguments = function.get("arguments") or {}
                arguments = self._coerce_arguments(raw_arguments)
                arguments = {key: value for key, value in arguments.items() if value is not None}

                key = (name, json.dumps(arguments, sort_keys=True))
                if key == last_key:
                    repeat_count += 1
                else:
                    last_key = key
                    repeat_count = 1

                if name in DEDUP_TOOLS and repeat_count == 2:
                    tool_results.append(last_result)
                    history.append(
                        {
                            "role": "tool",
                            "name": last_result.name,
                            "content": (
                                "(repeat call, no new information) {}\n\n"
                                "You already have this result from your previous identical "
                                "call. Respond to the user now instead of calling this again."
                            ).format(last_result.content),
                        }
                    )
                    continue

                if name in DEDUP_TOOLS and repeat_count >= 3:
                    summary = "\n\n".join(
                        "{} {}:\n{}".format("OK" if r.ok else "FAILED", r.name, r.content)
                        for r in tool_results
                    )
                    return ChatResponse(session_id=session_id, answer=summary, tool_results=tool_results)

                result = self.tools.call(name, arguments)
                last_result = result
                tool_results.append(result)
                history.append(
                    {
                        "role": "tool",
                        "name": result.name,
                        "content": result.content,
                    }
                )

        return ChatResponse(
            session_id=session_id,
            answer="I hit the configured tool-call limit before reaching a final answer.",
            tool_results=tool_results,
        )

    @staticmethod
    def _coerce_arguments(raw_arguments):
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            try:
                decoded = json.loads(raw_arguments)
                return decoded if isinstance(decoded, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _extract_text_tool_call(content):
        text = content.strip()
        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        candidates = fenced_blocks + [text]

        decoder = json.JSONDecoder()
        for candidate in candidates:
            candidate = candidate.strip()
            for match in re.finditer(r"\{", candidate):
                try:
                    decoded, _ = decoder.raw_decode(candidate, match.start())
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict) and "name" in decoded:
                    return {
                        "function": {
                            "name": decoded.get("name", ""),
                            "arguments": decoded.get("arguments") or {},
                        }
                    }
        return None
