"""
Prefix Trie Implementation for Fast Wildcard Key Matching (KEYS pattern*).
Jerry A. Nabasu (@JayNabasu)
"""

from typing import List, Dict

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_word = False
        self.key: str = ""

class PrefixTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, key: str):
        curr = self.root
        for char in key:
            if char not in curr.children:
                curr.children[char] = TrieNode()
            curr = curr.children[char]
        curr.is_end_of_word = True
        curr.key = key

    def delete(self, key: str) -> bool:
        def _delete(curr: TrieNode, key: str, depth: int) -> bool:
            if depth == len(key):
                if not curr.is_end_of_word:
                    return False
                curr.is_end_of_word = False
                return len(curr.children) == 0

            char = key[depth]
            if char not in curr.children:
                return False

            should_delete_child = _delete(curr.children[char], key, depth + 1)
            if should_delete_child:
                del curr.children[char]
                return len(curr.children) == 0 and not curr.is_end_of_word
            return False

        return _delete(self.root, key, 0)

    def find_by_prefix(self, prefix: str) -> List[str]:
        curr = self.root
        for char in prefix:
            if char not in curr.children:
                return []
            curr = curr.children[char]

        results = []
        self._collect_all(curr, results)
        return results

    def _collect_all(self, node: TrieNode, results: List[str]):
        if node.is_end_of_word:
            results.append(node.key)
        for char in sorted(node.children.keys()):
            self._collect_all(node.children[char], results)
