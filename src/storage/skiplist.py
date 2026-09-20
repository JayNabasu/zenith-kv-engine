"""
Probabilistic SkipList Implementation for O(log n) Sorted Sets.
Jerry A. Nabasu (@JayNabasu)
"""

import random
from typing import List, Optional, Tuple, Any

class SkipNode:
    def __init__(self, score: float, member: str, level: int):
        self.score = score
        self.member = member
        self.forward: List[Optional['SkipNode']] = [None] * (level + 1)

class SkipList:
    def __init__(self, max_level: int = 16, p: float = 0.5):
        self.max_level = max_level
        self.p = p
        self.level = 0
        self.header = SkipNode(float('-inf'), "", self.max_level)
        self.size = 0

    def _random_level(self) -> int:
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, score: float, member: str) -> bool:
        """Inserts or updates a member with the given score."""
        update = [None] * (self.max_level + 1)
        current = self.header

        for i in range(self.level, -1, -1):
            while current.forward[i] and (
                current.forward[i].score < score or 
                (current.forward[i].score == score and current.forward[i].member < member)
            ):
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]
        if current and current.score == score and current.member == member:
            return False # Member already exists with exact score

        # If member exists with different score, remove it first
        self.delete(member)

        # Recalculate insertion point after deletion
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] and (
                current.forward[i].score < score or 
                (current.forward[i].score == score and current.forward[i].member < member)
            ):
                current = current.forward[i]
            update[i] = current

        rlevel = self._random_level()
        if rlevel > self.level:
            for i in range(self.level + 1, rlevel + 1):
                update[i] = self.header
            self.level = rlevel

        new_node = SkipNode(score, member, rlevel)
        for i in range(rlevel + 1):
            new_node.forward[i] = update[i].forward[i]
            update[i].forward[i] = new_node

        self.size += 1
        return True

    def delete(self, member: str) -> bool:
        """Removes a member from the skip list."""
        update = [None] * (self.max_level + 1)
        current = self.header

        found_node = None
        for i in range(self.level, -1, -1):
            while current.forward[i]:
                if current.forward[i].member == member:
                    found_node = current.forward[i]
                    break
                current = current.forward[i]
            update[i] = current

        if not found_node:
            # Full linear search if member not directly matched
            curr = self.header.forward[0]
            while curr:
                if curr.member == member:
                    found_node = curr
                    break
                curr = curr.forward[0]

        if not found_node:
            return False

        # Find update pointers for found_node
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] and (
                current.forward[i].score < found_node.score or 
                (current.forward[i].score == found_node.score and current.forward[i].member < found_node.member)
            ):
                current = current.forward[i]
            update[i] = current

        for i in range(self.level + 1):
            if update[i] and update[i].forward[i] == found_node:
                update[i].forward[i] = found_node.forward[i]

        while self.level > 0 and self.header.forward[self.level] is None:
            self.level -= 1

        self.size -= 1
        return True

    def range_all(self, start: int = 0, stop: int = -1) -> List[Tuple[str, float]]:
        """Returns ordered list of (member, score) elements."""
        result = []
        curr = self.header.forward[0]
        while curr:
            result.append((curr.member, curr.score))
            curr = curr.forward[0]

        if stop == -1:
            stop = len(result)
        else:
            stop = stop + 1
        return result[start:stop]

    def range_by_score(self, min_score: float, max_score: float) -> List[Tuple[str, float]]:
        """Returns members with scores in [min_score, max_score]."""
        result = []
        curr = self.header.forward[0]
        while curr and curr.score < min_score:
            curr = curr.forward[0]

        while curr and curr.score <= max_score:
            result.append((curr.member, curr.score))
            curr = curr.forward[0]

        return result
