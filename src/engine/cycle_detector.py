"""
Tarjan's Strongly Connected Components (SCC) and Cycle Washing Detection Engine.
Identifies circular transaction routing (A -> B -> C -> A) used to disguise fund origins.
"""

from __future__ import annotations
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from src.models.transaction import BankTransaction, ActivityType


class CycleDetector:
    """
    Detects laundering cycles in multi-account transaction networks.
    Utilizes Tarjan's SCC algorithm to locate closed directed loops.
    """

    def __init__(self, target_account: str):
        self.target_account = target_account

    def detect_cycles(self, transactions: List[BankTransaction]) -> List[List[str]]:
        """
        Builds a directed adjacency list from transactions and returns
        all strongly connected components with length >= 2 (cycles).
        """
        adj: Dict[str, Set[str]] = defaultdict(set)

        for tx in transactions:
            if tx.activity == ActivityType.OUTFLOW and tx.counterparty_account:
                adj[tx.account_no].add(tx.counterparty_account)
            elif tx.activity == ActivityType.INFLOW and tx.counterparty_account:
                adj[tx.counterparty_account].add(tx.account_no)

        # Iterative Tarjan's algorithm (Stack-safe for deep graph chains)
        index = 0
        stack: List[str] = []
        on_stack: Set[str] = set()
        indices: Dict[str, int] = {}
        lowlinks: Dict[str, int] = {}
        sccs: List[List[str]] = []

        all_nodes = set(adj.keys())
        for neighbors in adj.values():
            all_nodes.update(neighbors)

        for root in all_nodes:
            if root in indices:
                continue

            call_stack = [(root, iter(adj.get(root, [])))]
            indices[root] = index
            lowlinks[root] = index
            index += 1
            stack.append(root)
            on_stack.add(root)

            while call_stack:
                node, it = call_stack[-1]
                try:
                    neighbor = next(it)
                    if neighbor not in indices:
                        indices[neighbor] = index
                        lowlinks[neighbor] = index
                        index += 1
                        stack.append(neighbor)
                        on_stack.add(neighbor)
                        call_stack.append((neighbor, iter(adj.get(neighbor, []))))
                    elif neighbor in on_stack:
                        lowlinks[node] = min(lowlinks[node], indices[neighbor])
                except StopIteration:
                    call_stack.pop()
                    if call_stack:
                        parent, _ = call_stack[-1]
                        lowlinks[parent] = min(lowlinks[parent], lowlinks[node])

                    if lowlinks[node] == indices[node]:
                        scc: List[str] = []
                        while True:
                            w = stack.pop()
                            on_stack.remove(w)
                            scc.append(w)
                            if w == node:
                                break
                        # Only keep components with >= 2 nodes or self-loops
                        if len(scc) > 1 or (len(scc) == 1 and node in adj.get(node, [])):
                            sccs.append(scc)

        return sccs
