"""Tests for BuildGraph DAG orchestration.

Tests:
- DAG validation (no cycles)
- Cycle detection and prevention
- Correct topological ordering
- Component dependency tracking
"""

import pytest
from scripts.intelligence.build import BuildGraph


class TestBuildGraphDAGValidation:
    """Test DAG validation and cycle detection."""

    def test_empty_graph(self):
        """Test empty graph is valid DAG."""
        graph = BuildGraph()
        assert graph.validate_dag() is True

    def test_single_component(self):
        """Test single component with no dependencies."""
        graph = BuildGraph()
        graph.add_component("classifier")
        assert graph.validate_dag() is True

    def test_linear_dependency_chain(self):
        """Test valid linear chain: A <- B <- C."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])
        graph.add_component("symbol_index", ["dependency_graph"])
        assert graph.validate_dag() is True

    def test_multiple_components_no_deps(self):
        """Test multiple independent components."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("test_mapper")
        graph.add_component("metrics")
        assert graph.validate_dag() is True

    def test_diamond_dependency(self):
        """Test valid diamond: C <- A, B; C <- D."""
        graph = BuildGraph()
        graph.add_component("base")
        graph.add_component("middle1", ["base"])
        graph.add_component("middle2", ["base"])
        graph.add_component("top", ["middle1", "middle2"])
        assert graph.validate_dag() is True

    def test_self_dependency_rejected(self):
        """Test that self-dependencies are rejected."""
        graph = BuildGraph()
        with pytest.raises(ValueError, match="cannot depend on itself"):
            graph.add_component("classifier", ["classifier"])

    def test_simple_cycle_rejected(self):
        """Test that simple cycles are rejected."""
        graph = BuildGraph()
        graph.add_component("A")
        graph.add_component("B", ["A"])
        with pytest.raises(ValueError, match="would create a cycle"):
            graph.add_component("A", ["B"])

    def test_indirect_cycle_rejected(self):
        """Test that indirect cycles are rejected."""
        graph = BuildGraph()
        graph.add_component("A")
        graph.add_component("B", ["A"])
        graph.add_component("C", ["B"])
        with pytest.raises(ValueError, match="would create a cycle"):
            graph.add_component("A", ["C"])


class TestBuildGraphBuildOrder:
    """Test topological sort and build ordering."""

    def test_single_component_order(self):
        """Test order for single component."""
        graph = BuildGraph()
        graph.add_component("classifier")
        order = graph.build_order()
        assert order == ["classifier"]

    def test_linear_chain_order(self):
        """Test order for linear chain."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])
        graph.add_component("symbol_index", ["dependency_graph"])

        order = graph.build_order()
        # Dependencies must come before dependents
        assert order.index("classifier") < order.index("dependency_graph")
        assert order.index("dependency_graph") < order.index("symbol_index")

    def test_diamond_order(self):
        """Test order for diamond dependency."""
        graph = BuildGraph()
        graph.add_component("base")
        graph.add_component("middle1", ["base"])
        graph.add_component("middle2", ["base"])
        graph.add_component("top", ["middle1", "middle2"])

        order = graph.build_order()
        assert order.index("base") < order.index("middle1")
        assert order.index("base") < order.index("middle2")
        assert order.index("middle1") < order.index("top")
        assert order.index("middle2") < order.index("top")

    def test_multiple_independent_order(self):
        """Test order for multiple independent components."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("test_mapper")
        graph.add_component("metrics")

        order = graph.build_order()
        assert len(order) == 3
        assert set(order) == {"classifier", "test_mapper", "metrics"}

    def test_complex_dag_order(self):
        """Test complex DAG with multiple levels."""
        graph = BuildGraph()
        # Level 0
        graph.add_component("classifier")
        graph.add_component("test_mapper")

        # Level 1 depends on Level 0
        graph.add_component("dependency_graph", ["classifier"])
        graph.add_component("metrics", ["test_mapper"])

        # Level 2 depends on Level 1
        graph.add_component("symbol_index", ["dependency_graph"])
        graph.add_component("importance", ["metrics"])

        # Level 3 depends on Level 2
        graph.add_component("docstring_parser", ["symbol_index"])

        order = graph.build_order()

        # Verify ordering constraints
        assert order.index("classifier") < order.index("dependency_graph")
        assert order.index("dependency_graph") < order.index("symbol_index")
        assert order.index("symbol_index") < order.index("docstring_parser")

        assert order.index("test_mapper") < order.index("metrics")
        assert order.index("metrics") < order.index("importance")


class TestBuildGraphDependencyTracking:
    """Test dependency tracking and relationships."""

    def test_get_dependencies(self):
        """Test getting component dependencies."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])

        deps = graph.get_dependencies("dependency_graph")
        assert deps == {"classifier"}

    def test_get_no_dependencies(self):
        """Test component with no dependencies."""
        graph = BuildGraph()
        graph.add_component("classifier")

        deps = graph.get_dependencies("classifier")
        assert deps == set()

    def test_get_multiple_dependencies(self):
        """Test component with multiple dependencies."""
        graph = BuildGraph()
        graph.add_component("base1")
        graph.add_component("base2")
        graph.add_component("top", ["base1", "base2"])

        deps = graph.get_dependencies("top")
        assert deps == {"base1", "base2"}

    def test_get_dependents(self):
        """Test getting components that depend on a component."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])
        graph.add_component("symbol_index", ["classifier"])

        dependents = graph.get_dependents("classifier")
        assert dependents == {"dependency_graph", "symbol_index"}

    def test_get_no_dependents(self):
        """Test component with no dependents."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])

        dependents = graph.get_dependents("dependency_graph")
        assert dependents == set()

    def test_partial_dependencies(self):
        """Test partial dependencies in complex graph."""
        graph = BuildGraph()
        graph.add_component("A")
        graph.add_component("B", ["A"])
        graph.add_component("C", ["A"])
        graph.add_component("D", ["B", "C"])

        # B depends on A, not on C
        b_deps = graph.get_dependencies("B")
        assert b_deps == {"A"}

        # A has two dependents
        a_dependents = graph.get_dependents("A")
        assert a_dependents == {"B", "C"}


class TestBuildGraphEdgeCases:
    """Test edge cases and error conditions."""

    def test_build_order_with_no_components(self):
        """Test build order for empty graph."""
        graph = BuildGraph()
        order = graph.build_order()
        assert order == []

    def test_missing_dependency_allowed(self):
        """Test that referencing non-existent dependency is allowed."""
        graph = BuildGraph()
        # In a real system, this might be caught elsewhere
        # For now, we allow forward references
        graph.add_component("a", ["nonexistent"])
        # Should not raise during add

    def test_add_component_twice(self):
        """Test adding same component twice overwrites."""
        graph = BuildGraph()
        graph.add_component("classifier")
        graph.add_component("classifier", ["test"])

        deps = graph.get_dependencies("classifier")
        assert deps == {"test"}

    def test_remove_dependency(self):
        """Test removing a dependency by re-adding with fewer deps."""
        graph = BuildGraph()
        graph.add_component("A")
        graph.add_component("B", ["A"])
        graph.add_component("B", [])  # Remove dependency on A

        deps = graph.get_dependencies("B")
        assert deps == set()
