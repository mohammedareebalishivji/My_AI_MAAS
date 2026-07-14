import re
from typing import Optional


class Skill:
    def __init__(self, name, description, keywords, parameters=None, action=None):
        self.name = name
        self.description = description
        self.keywords = [kw.lower() for kw in keywords]
        self.parameters = parameters or []
        self.action = action


class SkillEngine:
    def __init__(self):
        self.skills = []
        self._register_defaults()

    def _register_defaults(self):
        self.register(Skill(
            name="web_search",
            description="Search the web for information",
            keywords=["search", "google", "look up", "find online", "web search",
                       "what is", "who is", "how to", "where is", "when was"],
            parameters=["query"],
            action="search_web"
        ))
        self.register(Skill(
            name="open_website",
            description="Open a website in the browser",
            keywords=["open", "go to", "navigate to", "visit", "launch site"],
            parameters=["url"],
            action="open_website"
        ))
        self.register(Skill(
            name="launch_app",
            description="Launch a macOS application",
            keywords=["open app", "launch app", "launch", "start app", "run app",
                       "open application", "start application", "start"],
            parameters=["app_name"],
            action="launch_app"
        ))
        self.register(Skill(
            name="system_health",
            description="Check CPU, RAM, battery status",
            keywords=["system health", "cpu", "ram", "memory", "battery", "performance",
                       "how is my mac", "system status"],
            parameters=[],
            action="get_system_health"
        ))
        self.register(Skill(
            name="weather",
            description="Get current weather for a city",
            keywords=["weather", "temperature", "forecast", "rain", "sunny",
                       "climate", "how hot", "how cold"],
            parameters=["city"],
            action="get_weather"
        ))
        self.register(Skill(
            name="reminder_add",
            description="Add a reminder or todo",
            keywords=["remind me", "add reminder", "set reminder", "todo", "to-do",
                       "remember to", "don't forget"],
            parameters=["task"],
            action="add_reminder"
        ))
        self.register(Skill(
            name="reminder_list",
            description="List all current reminders",
            keywords=["show reminders", "list reminders", "my reminders", "what reminders",
                       "any reminders", "remind me of"],
            parameters=[],
            action="get_reminders"
        ))
        self.register(Skill(
            name="file_read",
            description="Read the contents of a file",
            keywords=["read file", "open file", "show file", "file contents", "cat file"],
            parameters=["filepath"],
            action="read_file"
        ))
        self.register(Skill(
            name="file_write",
            description="Write content to a file",
            keywords=["write to file", "save to file", "create file", "write file"],
            parameters=["filepath", "content"],
            action="write_file"
        ))
        self.register(Skill(
            name="directory_list",
            description="List files in a directory",
            keywords=["list files", "ls", "directory", "folder contents", "what's in"],
            parameters=["path"],
            action="list_directory"
        ))
        self.register(Skill(
            name="shell_command",
            description="Run a terminal/shell command",
            keywords=["run command", "terminal", "shell", "execute", "terminal command"],
            parameters=["command"],
            action="run_shell_command"
        ))
        self.register(Skill(
            name="media_control",
            description="Control media playback (play/pause/next)",
            keywords=["play", "pause", "next song", "previous", "skip track",
                       "music", "spotify", "media"],
            parameters=["action"],
            action="control_media"
        ))
        self.register(Skill(
            name="volume",
            description="Set system volume",
            keywords=["volume", "mute", "unmute", "louder", "quieter", "sound"],
            parameters=["level"],
            action="set_volume"
        ))
        self.register(Skill(
            name="screenshot",
            description="Take a screenshot of the screen",
            keywords=["screenshot", "capture screen", "screen capture", "take screenshot"],
            parameters=[],
            action="take_screenshot"
        ))
        self.register(Skill(
            name="clipboard",
            description="Copy or paste text from/to clipboard",
            keywords=["copy", "paste", "clipboard"],
            parameters=["action", "text"],
            action="clipboard"
        ))
        self.register(Skill(
            name="file_search",
            description="Search for files on the system",
            keywords=["find file", "locate file", "locate", "search for file",
                       "where is file", "find document"],
            parameters=["name"],
            action="find_file_advanced"
        ))
        self.register(Skill(
            name="brightness",
            description="Adjust screen brightness",
            keywords=["brightness", "dim screen", "brighten screen", "screen brightness"],
            parameters=["level"],
            action="set_brightness"
        ))

    def register(self, skill):
        self.skills.append(skill)

    def _kw_match(self, keyword, text_lower):
        if len(keyword) <= 2:
            return re.search(r'(?:^|\s)' + re.escape(keyword) + r'(?:\s|$)', text_lower) is not None
        return keyword in text_lower

    def classify(self, user_text):
        user_lower = user_text.lower().strip()

        # Pre-check: URL pattern -> open_website
        if re.search(r'\b(?:open|go to|visit|navigate to)\s+https?://', user_lower):
            for s in self.skills:
                if s.name == "open_website":
                    return s

        # Pre-check: "open X app" pattern -> launch_app
        if re.search(r'\bopen\b.*\bapp\b', user_lower):
            for s in self.skills:
                if s.name == "launch_app":
                    return s

        # Pre-check: action verb + app name -> launch_app
        action_verbs = ["launch", "start", "run"]
        for verb in action_verbs:
            if user_lower.startswith(verb) or f" {verb} " in user_lower:
                remaining = user_lower.replace(verb, "", 1).strip()
                if remaining and not any(
                    kw in remaining for kw in
                    ["search", "google", "web", "file", "command", "shell",
                     "terminal", "reminder", "music", "volume", "brightness",
                     "screenshot", "clipboard", "browser", "website"]
                ):
                    for s in self.skills:
                        if s.name == "launch_app":
                            return s

        scores = []

        for skill in self.skills:
            score = 0
            matched_any = False
            for kw in skill.keywords:
                if self._kw_match(kw, user_lower):
                    score += len(kw) * 2
                    matched_any = True
            if matched_any:
                scores.append((score, skill))

        scores.sort(key=lambda x: x[0], reverse=True)
        if scores and scores[0][0] > 2:
            top = scores[0][1]
            if len(scores) > 1:
                second = scores[1][1]
                if top.name == "web_search" and second.name in (
                    "open_website", "launch_app", "media_control",
                    "reminder_add", "file_read", "directory_list", "file_search"
                ):
                    return second
                if top.name == "web_search" and second.name == "weather":
                    if re.search(r'\bweather\b.*\bin\b', user_lower):
                        return second
                if top.name == "media_control" and second.name == "launch_app":
                    action_words = ["launch", "open", "start", "run"]
                    if any(w in user_lower for w in action_words):
                        return second
                if top.name == "shell_command" and second.name == "launch_app":
                    if re.search(r'\bopen\b.*\bapp\b', user_lower):
                        return second
            return top
        return None

    def extract_params(self, skill, user_text):
        params = {}
        user_lower = user_text.lower()
        if not skill.parameters:
            return params

        if skill.name == "weather":
            city_match = re.search(
                r"(?:weather|temperature|forecast)\s+(?:in|for|at)\s+(.+?)(?:\?|$)",
                user_text, re.IGNORECASE
            )
            if city_match:
                params["city"] = city_match.group(1).strip()

        elif skill.name == "web_search":
            for prefix in ["search for ", "google ", "look up ", "search ", "find online "]:
                if prefix in user_text.lower():
                    query = user_text.lower().split(prefix, 1)[-1].strip()
                    if query:
                        params["query"] = query
                        break
            if "query" not in params:
                params["query"] = user_text

        elif skill.name == "open_website":
            url_match = re.search(
                r"(?:open|go to|visit|navigate to)\s+(https?://\S+|[\w.-]+\.\w{2,})",
                user_text, re.IGNORECASE
            )
            if url_match:
                params["url"] = url_match.group(1)

        elif skill.name == "launch_app":
            app_match = re.search(
                r"(?:open|launch|start|run)\s+(?:app\s+)?(.+?)(?:\s+app)?$",
                user_text, re.IGNORECASE
            )
            if app_match:
                params["app_name"] = app_match.group(1).strip()

        elif skill.name == "reminder_add":
            task_match = re.search(
                r"(?:remind me to?|add reminder|set reminder|todo|remember to)\s+(.+?)(?:\s+(?:at|on|by)\s+.+)?$",
                user_text, re.IGNORECASE
            )
            if task_match:
                params["task"] = task_match.group(1).strip()

        elif skill.name == "file_read":
            path_match = re.search(
                r"(?:read|open|show|cat)\s+(?:file\s+)?(.+?)(?:\s|$)",
                user_text, re.IGNORECASE
            )
            if path_match:
                params["filepath"] = path_match.group(1).strip()

        elif skill.name == "file_write":
            params["filepath"] = ""
            params["content"] = user_text

        elif skill.name == "directory_list":
            path_match = re.search(
                r"(?:list|ls)\s+(?:files in\s+|directory\s+)?(.+?)(?:\s|$)",
                user_text, re.IGNORECASE
            )
            params["path"] = path_match.group(1).strip() if path_match else "."

        elif skill.name == "shell_command":
            cmd_match = re.search(
                r"(?:run|execute|terminal|shell)\s+(?:command\s+)?(.+?)$",
                user_text, re.IGNORECASE
            )
            if cmd_match:
                params["command"] = cmd_match.group(1).strip()

        elif skill.name == "media_control":
            if any(w in user_lower for w in ["play", "resume"]):
                params["action"] = "play"
            elif "pause" in user_lower or "stop" in user_lower:
                params["action"] = "pause"
            elif "next" in user_lower or "skip" in user_lower:
                params["action"] = "next"
            elif "previous" in user_lower or "back" in user_lower:
                params["action"] = "previous"

        elif skill.name == "volume":
            level_match = re.search(r"(\d+)", user_text)
            if level_match:
                params["level"] = level_match.group(1)
            elif any(w in user_lower for w in ["louder", "max", "full", "up"]):
                params["level"] = "100"
            elif any(w in user_lower for w in ["mute", "silent"]):
                params["level"] = "0"
            elif any(w in user_lower for w in ["quieter", "lower", "down"]):
                params["level"] = "30"

        elif skill.name == "brightness":
            level_match = re.search(r"(\d+)", user_text)
            params["level"] = level_match.group(1) if level_match else "50"

        elif skill.name == "clipboard":
            if "copy" in user_lower:
                params["action"] = "copy"
                text_match = re.search(r"copy\s+(.+)", user_text, re.IGNORECASE)
                params["text"] = text_match.group(1).strip() if text_match else ""
            else:
                params["action"] = "paste"

        elif skill.name == "file_search":
            name_match = re.search(
                r"(?:find|locate|search for)\s+(?:file\s+)?(.+?)(?:\s|$)",
                user_text, re.IGNORECASE
            )
            if name_match:
                params["name"] = name_match.group(1).strip()

        return params
