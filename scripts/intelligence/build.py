"""Build orchestrator with DAG (Directed Acyclic Graph) orchestration.

Manages component build order using topological sort and cycle detection.
Components are executed in dependency order to ensure data availability.
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque


class BuildGraph:
    """DAG-based build orchestrator for component ordering.

    Components declare dependencies, BuildGraph determines build order
    using topological sorting and validates for cycles.
    """

    def __init__(self):
        """Initialize empty build graph."""
        self.components: Dict[str, Set[str]] = {}
        self.all_deps: Dict[str, Set[str]] = defaultdict(set)

    def add_component(self, name: str, dependencies: Optional[List[str]] = None):
        """Add component to build graph with its dependencies.

        Args:
            name: Component name (e.g., "classifier", "dependency_graph").
            dependencies: List of component names this depends on.

        Raises:
            ValueError: If adding would create a cycle.
        """
        # Initialize or clear dependencies
        if name not in self.components:
            self.components[name] = set()
        else:
            # Clear old dependencies for update
            self.components[name].clear()
            self.all_deps[name].clear()

        # Add new dependencies
        if dependencies:
            for dep in dependencies:
                if dep == name:
                    raise ValueError(f"Component {name} cannot depend on itself")
                self.components[name].add(dep)
                self.all_deps[name].add(dep)

        # Validate DAG after adding
        if self._would_create_cycle(name):
            # Rollback
            self.components[name].clear()
            self.all_deps[name].clear()
            raise ValueError(f"Adding {name} with deps {dependencies} would create a cycle")

    def build_order(self) -> List[str]:
        """Compute build order using topological sort.

        Returns:
            List of component names in build order (dependencies first).

        Raises:
            ValueError: If graph contains a cycle.
        """
        if self._has_cycle():
            raise ValueError("Build graph contains a cycle")

        # Kahn's algorithm for topological sort
        in_degree = defaultdict(int)
        graph = defaultdict(list)

        # Build adjacency list and in-degrees
        for node in self.components:
            if node not in in_degree:
                in_degree[node] = 0

        for node, deps in self.components.items():
            for dep in deps:
                graph[dep].append(node)
                in_degree[node] += 1

        # Queue of nodes with no dependencies
        queue = deque([node for node in self.components if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for dependent in graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.components):
            raise ValueError("Build graph contains a cycle")

        return result

    def validate_dag(self) -> bool:
        """Validate that graph is a valid DAG.

        Returns:
            True if valid DAG, False if contains cycle.
        """
        return not self._has_cycle()

    def _has_cycle(self) -> bool:
        """Detect cycle using DFS.

        Returns:
            True if graph contains a cycle.
        """
        visited = set()
        rec_stack = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in self.components.get(node, set()):
                if dep not in visited:
                    if _dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.components:
            if node not in visited:
                if _dfs(node):
                    return True

        return False

    def _would_create_cycle(self, node: str) -> bool:
        """Check if adding node's current dependencies would create a cycle.

        Args:
            node: Node to check.

        Returns:
            True if would create cycle.
        """
        # Check if any dependency already depends on this node
        for dep in self.components.get(node, set()):
            if self._has_path(dep, node):
                return True
        return False

    def _has_path(self, start: str, end: str) -> bool:
        """Check if there's a path from start to end node.

        Args:
            start: Starting node.
            end: Ending node.

        Returns:
            True if path exists.
        """
        visited = set()
        queue = deque([start])

        while queue:
            node = queue.popleft()
            if node == end:
                return True

            if node in visited:
                continue
            visited.add(node)

            for dep in self.components.get(node, set()):
                if dep not in visited:
                    queue.append(dep)

        return False

    def get_dependencies(self, component: str) -> Set[str]:
        """Get direct dependencies of a component.

        Args:
            component: Component name.

        Returns:
            Set of component names this depends on.
        """
        return self.components.get(component, set()).copy()

    def get_dependents(self, component: str) -> Set[str]:
        """Get components that depend on this component.

        Args:
            component: Component name.

        Returns:
            Set of component names that depend on this.
        """
        dependents = set()
        for node, deps in self.components.items():
            if component in deps:
                dependents.add(node)
        return dependents
