import time
import re
import warnings
import threading
warnings.filterwarnings("ignore", category=UserWarning, module="jieba")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from brain import JarvisBrain
from ears import JarvisEars
from voice import JarvisVoice
from automation import JarvisHands
from skill_engine import SkillEngine
from memory.sqlite_memory import SQLiteMemory
from memory.rag_engine import RAGEngine


class Jarvis:
    def __init__(self):
        print("Initializing JARVIS...")
        self.brain = JarvisBrain()
        self.ears = JarvisEars()
        self.voice = JarvisVoice()
        self.hands = JarvisHands()
        self.db = SQLiteMemory()
        self.memory = RAGEngine()
        self.skill_engine = SkillEngine()
        self._speaking = False

        tools_desc = self.hands.get_tool_descriptions()
        self.brain.add_tool_descriptions(tools_desc)

        print("--- JARVIS IS ONLINE ---")

    def _speak_async(self, text):
        if self._speaking:
            return
        self._speaking = True
        def _do():
            try:
                self.voice.speak(text)
            finally:
                self._speaking = False
        threading.Thread(target=_do, daemon=True).start()

    def _inject_relevant_memories(self, user_text):
        memories = self.memory.search_conversations(user_text, n_results=3)
        if memories:
            context = "\n".join([m["text"][:150] for m in memories])
            self.brain.inject_rag_context(context)

    def _store_memory(self, user_text, response):
        self.memory.store_conversation(user_text, response)

    def _execute_tool(self, tool_call_str):
        tool_pattern = r"(\w+)\((.*?)\)"
        match = re.match(tool_pattern, tool_call_str.strip())
        if not match:
            return None, "Invalid tool call format"

        tool_name = match.group(1)
        args_str = match.group(2).strip()

        kwargs = {}
        if args_str:
            arg_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
            for am in re.finditer(arg_pattern, args_str):
                key = am.group(1)
                value = am.group(2) or am.group(3) or am.group(4)
                kwargs[key] = value

        if not kwargs and args_str:
            clean = args_str.strip().strip('"').strip("'")
            skill = self.skill_engine.classify(tool_name)
            if skill and skill.parameters:
                kwargs[skill.parameters[0]] = clean

        result = self.hands.execute(tool_name, **kwargs)
        return tool_name, result

    def _handle_tools(self, response_text):
        tool_pattern = r"\[TOOL:\s*(.*?)\]"
        matches = re.findall(tool_pattern, response_text)
        results = []
        for match in matches:
            tool_name, result = self._execute_tool(match)
            if result:
                results.append(f"Result of {tool_name}: {result}")
        return "\n".join(results) if results else None

    def run(self):
        print("\nJARVIS is ready. Speak or type your message.")
        print("Type 'exit' or 'quit' to shut down.\n")

        while True:
            try:
                print("[Listening...]")
                user_text = self.ears.listen()

                if not user_text:
                    continue

                print(f"\nMr. Mohammed: {user_text}")

                if user_text.lower() in ["exit", "quit", "terminate", "shutdown"]:
                    self._speak_async("Shutting down. Goodbye, sir.")
                    time.sleep(1)
                    break

                self._inject_relevant_memories(user_text)

                skill = self.skill_engine.classify(user_text)
                if skill:
                    print(f"  [Auto-skill: {skill.name}]")
                    params = self.skill_engine.extract_params(skill, user_text)
                    result = self.hands.execute(skill.action, **params)
                    self.brain.inject_skill_context(skill.name, result)

                current_input = user_text
                final_response = ""
                for _ in range(3):
                    response = self.brain.chat(current_input)
                    final_response = response

                    tool_results = self._handle_tools(response)

                    clean_response = re.sub(r"\[TOOL:.*?\]", "", response).strip()
                    if clean_response:
                        print(f"\nJARVIS: {clean_response}")
                        self._speak_async(clean_response)

                    if tool_results:
                        current_input = (
                            f"TOOL_RESULTS: {tool_results}\n"
                            "Continue if not complete, otherwise acknowledge."
                        )
                    else:
                        break

                self._store_memory(user_text, final_response)

            except KeyboardInterrupt:
                print("\n\n[Manual Interrupt]")
                user_text = input("Type your message: ").strip()
                if user_text:
                    response = self.brain.chat(user_text)
                    print(f"JARVIS: {response}")
                continue
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.5)


if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.run()
