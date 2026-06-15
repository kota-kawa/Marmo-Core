#!/usr/bin/env python3
"""
Step Functions Visualizer
Visualizes AWS Step Functions state machine definitions in Mermaid, HTML, and text tree formats.

Author: BanquetKuma
"""

import json
import sys
import os
from typing import Dict, List, Tuple, Set
from pathlib import Path


class StepFunctionsVisualizer:
    """Parse and visualize AWS Step Functions definitions"""

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.definition = None
        self.states = {}
        self.start_at = None
        self.nodes = []
        self.edges = []
        self.stats = {
            'total_states': 0,
            'by_type': {},
            'has_error_handling': 0,
            'terminal_states': 0
        }

    def load_definition(self) -> bool:
        """Load Step Functions JSON definition"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.definition = json.load(f)
            self.states = self.definition.get('States', {})
            self.start_at = self.definition.get('StartAt')
            return True
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return False

    def analyze_states(self):
        """Analyze states and build statistics"""
        self.stats['total_states'] = len(self.states)

        for state_name, state_def in self.states.items():
            state_type = state_def.get('Type', 'Unknown')
            self.stats['by_type'][state_type] = self.stats['by_type'].get(state_type, 0) + 1

            if state_def.get('Catch'):
                self.stats['has_error_handling'] += 1

            if state_def.get('End', False):
                self.stats['terminal_states'] += 1

    def build_graph(self):
        """Build graph structure for visualization"""
        visited = set()

        def add_node(name: str, state_def: Dict):
            state_type = state_def.get('Type', 'Unknown')
            is_terminal = state_def.get('End', False)

            self.nodes.append({
                'id': name,
                'label': name,
                'type': state_type,
                'terminal': is_terminal
            })

        def add_edge(from_state: str, to_state: str, label: str = '', edge_type: str = 'normal'):
            self.edges.append({
                'from': from_state,
                'to': to_state,
                'label': label,
                'type': edge_type
            })

        def process_state(name: str):
            # 訪問済みチェックを最初に実行して無限再帰を防止
            if name in visited:
                return

            if name not in self.states:
                return

            # 即座に訪問済みとしてマーク
            visited.add(name)

            state_def = self.states[name]
            add_node(name, state_def)

            state_type = state_def.get('Type')

            # Handle Next transition
            if 'Next' in state_def:
                next_state = state_def['Next']
                add_edge(name, next_state)
                process_state(next_state)

            # Handle Choice state
            if state_type == 'Choice':
                choices = state_def.get('Choices', [])
                for i, choice in enumerate(choices):
                    next_state = choice.get('Next')
                    if next_state:
                        # Create simplified label from choice condition
                        label = self._create_choice_label(choice, i)
                        add_edge(name, next_state, label, 'choice')
                        process_state(next_state)

                # Handle Default
                if 'Default' in state_def:
                    default_state = state_def['Default']
                    add_edge(name, default_state, 'Default', 'default')
                    process_state(default_state)

            # Handle Catch (error handling)
            if 'Catch' in state_def:
                for catch in state_def['Catch']:
                    next_state = catch.get('Next')
                    if next_state:
                        error_equals = ', '.join(catch.get('ErrorEquals', []))
                        label = f"Catch: {error_equals}"
                        add_edge(name, next_state, label, 'catch')
                        process_state(next_state)

        # Start from StartAt state
        if self.start_at:
            process_state(self.start_at)

    def _create_choice_label(self, choice: Dict, index: int) -> str:
        """Create a simplified label for Choice conditions"""
        # Try to extract a meaningful condition
        if 'Variable' in choice:
            var = choice['Variable'].split('.')[-1]  # Get last part of JSONPath

            if 'BooleanEquals' in choice:
                return f"{var}={choice['BooleanEquals']}"
            elif 'StringEquals' in choice:
                return f"{var}='{choice['StringEquals']}'"
            elif 'NumericEquals' in choice:
                return f"{var}=={choice['NumericEquals']}"
            elif 'IsPresent' in choice:
                return f"{var} exists" if choice['IsPresent'] else f"{var} not exists"
            else:
                return f"Condition {index + 1}"

        return f"Choice {index + 1}"

    def generate_mermaid(self) -> str:
        """Generate Mermaid flowchart wrapped in Markdown code block"""
        lines = ["# Step Functions Flow Diagram", "", "```mermaid", "graph TD"]

        # Add nodes
        for node in self.nodes:
            node_id = self._sanitize_id(node['id'])
            label = node['label']
            node_type = node['type']

            # Choose shape based on type
            if node_type == 'Choice':
                lines.append(f"    {node_id}{{{label}}}")
            elif node['terminal']:
                lines.append(f"    {node_id}(({label}))")
            else:
                lines.append(f"    {node_id}[{label}]")

        # Add edges
        for edge in self.edges:
            from_id = self._sanitize_id(edge['from'])
            to_id = self._sanitize_id(edge['to'])
            label = edge['label']
            edge_type = edge['type']

            if edge_type == 'catch':
                lines.append(f"    {from_id} -.->|{label}| {to_id}")
            elif label:
                lines.append(f"    {from_id} -->|{label}| {to_id}")
            else:
                lines.append(f"    {from_id} --> {to_id}")

        lines.append("```")

        # Add statistics section
        lines.extend(["", "## Statistics", ""])
        lines.append(f"- **Total States**: {self.stats['total_states']}")
        lines.append(f"- **Terminal States**: {self.stats['terminal_states']}")
        lines.append(f"- **States with Error Handling**: {self.stats['has_error_handling']}")
        lines.append("")
        lines.append("### States by Type")
        lines.append("")
        for state_type, count in sorted(self.stats['by_type'].items()):
            lines.append(f"- **{state_type}**: {count}")

        return '\n'.join(lines)

    def generate_html(self, template_path: str = None) -> str:
        """Generate HTML with vis.js visualization"""
        if template_path is None:
            template_path = Path(__file__).parent / 'templates' / 'template.html'

        # Read template
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception:
            # Fallback to embedded template
            template = self._get_embedded_template()

        # Prepare nodes data
        nodes_data = []
        for node in self.nodes:
            color = self._get_node_color(node['type'])
            shape = 'diamond' if node['type'] == 'Choice' else 'ellipse' if node['terminal'] else 'box'

            nodes_data.append({
                'id': node['id'],
                'label': node['label'],
                'color': color,
                'shape': shape
            })

        # Prepare edges data
        edges_data = []
        for edge in self.edges:
            dashes = edge['type'] == 'catch'
            color = '#ff0000' if edge['type'] == 'catch' else '#2B7CE9'

            edges_data.append({
                'from': edge['from'],
                'to': edge['to'],
                'label': edge['label'],
                'dashes': dashes,
                'color': color
            })

        # Replace placeholders
        html = template.replace('{{NODES_DATA}}', json.dumps(nodes_data, indent=2))
        html = html.replace('{{EDGES_DATA}}', json.dumps(edges_data, indent=2))
        html = html.replace('{{TITLE}}', f"Step Functions: {Path(self.json_path).stem}")

        return html

    def generate_text_tree(self) -> str:
        """Generate text tree representation"""
        lines = ["Step Functions Flow Visualization", "=" * 50, ""]
        lines.append(f"StartAt: {self.start_at}\n")

        visited = set()

        def print_state(name: str, indent: int = 0, prefix: str = ""):
            if name in visited:
                lines.append(f"{' ' * indent}{prefix}{name} (already shown)")
                return

            visited.add(name)

            if name not in self.states:
                lines.append(f"{' ' * indent}{prefix}{name} (not found)")
                return

            state_def = self.states[name]
            state_type = state_def.get('Type', 'Unknown')

            lines.append(f"{' ' * indent}{prefix}{name} ({state_type})")

            # Handle Next
            if 'Next' in state_def:
                print_state(state_def['Next'], indent + 2, "└─> ")

            # Handle Choice
            if state_type == 'Choice':
                choices = state_def.get('Choices', [])
                for i, choice in enumerate(choices):
                    label = self._create_choice_label(choice, i)
                    next_state = choice.get('Next')
                    if next_state:
                        print_state(next_state, indent + 2, f"├─[{label}]─> ")

                if 'Default' in state_def:
                    print_state(state_def['Default'], indent + 2, "└─[Default]─> ")

            # Handle Catch
            if 'Catch' in state_def:
                for catch in state_def['Catch']:
                    error_equals = ', '.join(catch.get('ErrorEquals', []))
                    next_state = catch.get('Next')
                    if next_state:
                        print_state(next_state, indent + 2, f"├─[Catch: {error_equals}]─> ")

        if self.start_at:
            print_state(self.start_at)

        # Add statistics
        lines.append("\n" + "=" * 50)
        lines.append("Statistics:")
        lines.append(f"  Total States: {self.stats['total_states']}")
        lines.append(f"  Terminal States: {self.stats['terminal_states']}")
        lines.append(f"  States with Error Handling: {self.stats['has_error_handling']}")
        lines.append("\n  States by Type:")
        for state_type, count in sorted(self.stats['by_type'].items()):
            lines.append(f"    {state_type}: {count}")

        return '\n'.join(lines)

    def _sanitize_id(self, name: str) -> str:
        """Sanitize state name for Mermaid"""
        return name.replace(' ', '_').replace('-', '_')

    def _get_node_color(self, state_type: str) -> str:
        """Get color for node based on state type"""
        colors = {
            'Task': '#2B7CE9',
            'Choice': '#FFA500',
            'Pass': '#00FF00',
            'Wait': '#FF8C00',
            'Fail': '#FF0000',
            'Succeed': '#00FF00',
            'Parallel': '#9370DB',
            'Map': '#4682B4'
        }
        return colors.get(state_type, '#97C2FC')

    def _get_embedded_template(self) -> str:
        """Embedded HTML template as fallback"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>{{TITLE}}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        #mynetwork { width: 100%; height: 800px; border: 1px solid #ddd; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>{{TITLE}}</h1>
    <div id="mynetwork"></div>
    <script>
        var nodes = new vis.DataSet({{NODES_DATA}});
        var edges = new vis.DataSet({{EDGES_DATA}});
        var container = document.getElementById('mynetwork');
        var data = { nodes: nodes, edges: edges };
        var options = {
            layout: {
                hierarchical: {
                    direction: 'UD',
                    sortMethod: 'directed',
                    levelSeparation: 150,
                    nodeSpacing: 200
                }
            },
            physics: false,
            edges: {
                arrows: 'to',
                smooth: { type: 'cubicBezier' }
            },
            nodes: {
                font: { size: 14 }
            }
        };
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>'''


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualizer.py <stepfunctions.json> [output_format]")
        print("  output_format: mermaid, html, text, all (default: all)")
        sys.exit(1)

    json_path = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'all'

    visualizer = StepFunctionsVisualizer(json_path)

    if not visualizer.load_definition():
        sys.exit(1)

    visualizer.analyze_states()
    visualizer.build_graph()

    base_name = Path(json_path).stem

    # プロジェクトルートディレクトリを検出（.claude/skills が存在する親ディレクトリ）
    current_path = Path(json_path).absolute()
    project_root = None

    # 現在のパスから上位ディレクトリを探索
    for parent in current_path.parents:
        if (parent / '.claude').exists() or (parent / '.git').exists():
            project_root = parent
            break

    # プロジェクトルートが見つからない場合は入力ファイルの親ディレクトリを使用
    if project_root is None:
        project_root = Path(json_path).parent

    # imagesディレクトリを作成（存在しない場合）
    output_dir = project_root / 'images'
    output_dir.mkdir(exist_ok=True)

    if output_format in ['mermaid', 'all']:
        mermaid_output = visualizer.generate_mermaid()
        mermaid_path = output_dir / f"{base_name}.md"
        with open(mermaid_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_output)
        print(f"Mermaid diagram saved to: {mermaid_path}")

    if output_format in ['html', 'all']:
        html_output = visualizer.generate_html()
        html_path = output_dir / f"{base_name}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"HTML visualization saved to: {html_path}")

    if output_format in ['text', 'all']:
        text_output = visualizer.generate_text_tree()
        text_path = output_dir / f"{base_name}-tree.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_output)
        print(f"Text tree saved to: {text_path}")
        print("\n" + text_output)


if __name__ == '__main__':
    main()
