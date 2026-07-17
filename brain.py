import ollama
import os
import json
import re
from dotenv import load_dotenv
from memory.sqlite_memory import SQLiteMemory

load_dotenv()


class JarvisBrain:
    MAX_MESSAGES = 40

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.db = SQLiteMemory()
        self.system_prompt = (
            "You are J.A.R.V.I.S — personal AI for Mohammed Areeb Ali Shivji. "
            "Loyal, concise, dry British wit. Obey all commands without hesitation. "
            "Use tools via [TOOL: name(args)] format. Be brief by default, detailed when asked."
        )
        self.conversation_id = self.db.create_conversation(title="JARVIS Session")
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        self._load_recent_context()

    def _trim_messages(self):
        if len(self.messages) > self.MAX_MESSAGES:
            system = self.messages[0]
            recent = self.messages[-(self.MAX_MESSAGES - 1):]
            self.messages = [system] + recent

    def _load_recent_context(self):
        recent = self.db.get_recent_conversations(limit=1)
        if recent:
            conv = self.db.get_conversation(recent[0]["id"])
            if conv and len(conv["messages"]) > 2:
                context = "Recent conversation history:\n"
                for msg in conv["messages"][-4:]:
                    context += f"{msg['role'].capitalize()}: {msg['content'][:200]}\n"
                self.messages.append({"role": "system", "content": context})

    def inject_rag_context(self, context_text):
        if context_text:
            self.messages.append({"role": "system", "content": f"Knowledge:\n{context_text}"})

    def inject_skill_context(self, skill_name, skill_result):
        self.messages.append({"role": "system", "content": f"Skill '{skill_name}': {skill_result}"})

    def chat(self, user_input, rag_context=None, skill_context=None):
        if rag_context:
            self.inject_rag_context(rag_context)
        if skill_context:
            self.inject_skill_context(skill_context["name"], skill_context["result"])

        self.messages.append({"role": "user", "content": user_input})
        self._trim_messages()

        try:
            response = ollama.chat(model=self.model, messages=self.messages)
            ai_response = response['message']['content']

            self.db.add_message(self.conversation_id, "user", user_input)
            self.db.add_message(self.conversation_id, "assistant", ai_response)
            self.messages.append({"role": "assistant", "content": ai_response})

            return ai_response

        except Exception as e:
            error_msg = f"Error: {str(e)}. Is Ollama running with model '{self.model}'?"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg

    def chat_stream(self, user_input, rag_context=None, skill_context=None):
        if rag_context:
            self.inject_rag_context(rag_context)
        if skill_context:
            self.inject_skill_context(skill_context["name"], skill_context["result"])

        self.messages.append({"role": "user", "content": user_input})
        self._trim_messages()

        full_response = ""
        try:
            stream = ollama.chat(model=self.model, messages=self.messages, stream=True)
            for chunk in stream:
                token = chunk['message']['content']
                full_response += token
                yield token

            self.db.add_message(self.conversation_id, "user", user_input)
            self.db.add_message(self.conversation_id, "assistant", full_response)
            self.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            full_response = error_msg
            yield error_msg
            self.messages.append({"role": "assistant", "content": full_response})

    def add_tool_descriptions(self, tools_list):
        tool_instruction = (
            f"\n\nTools available (use [TOOL: name(args)]):\n"
            f"{tools_list}\n"
        )
        self.messages[0]["content"] += tool_instruction

    def clear_context(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.conversation_id = self.db.create_conversation(title="New Session")
