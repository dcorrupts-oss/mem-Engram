import re
import logging
from typing import List

logger = logging.getLogger("mem-Engram.recall_trigger")

RECALL_TRIGGER_PATTERNS = [
    r"你还记得",
    r"之前.*说过",
    r"上次.*提到",
    r"帮我回忆",
    r"回忆一下",
    r"之前.*讲",
    r"刚才.*说",
    r"do you remember",
    r"remember.*when",
    r"之前.*聊",
    r"之前.*提",
    r"还记得.*吗",
    r"之前.*那个",
]


class RecallTriggerDetector:
    def __init__(self, patterns: List[str] = None):
        self.patterns = patterns or RECALL_TRIGGER_PATTERNS

    def detect(self, query: str) -> bool:
        for pattern in self.patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
