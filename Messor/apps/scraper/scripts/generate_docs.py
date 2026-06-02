#!/usr/bin/env python3
"""
Documentation generation script for Messor codebase.

This script analyzes the codebase and generates comprehensive documentation
including API references, code coverage reports, and docstring validation.

Usage:
    python scripts/generate_docs.py [options]
    
Options:
    --format {html,markdown,json}  Output format (default: html)
    --output-dir DIR              Output directory (default: docs/generated)
    --include-private             Include private methods in documentation
    --validate-only               Only validate existing docstrings
    --coverage                    Generate documentation coverage report

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import argparse
import ast
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class DocstringAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing docstrings and function signatures."""
    
    def __init__(self):
        self.functions: List[Dict] = []
        self.classes: List[Dict] = []
        self.modules: List[Dict] = []
        self.missing_docstrings: List[str] = []
        self.current_class = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and extract documentation info."""
        docstring = ast.get_docstring(node)
        is_private = node.name.startswith('_')
        
        # Extract type hints from annotations
        args = []
        for arg in node.args.args:
            arg_info = {
                'name': arg.arg,
                'type': self._get_annotation_string(arg.annotation) if arg.annotation else None
            }
            args.append(arg_info)
        
        return_type = self._get_annotation_string(node.returns) if node.returns else None
        
        func_info = {
            'name': node.name,
            'docstring': docstring,
            'has_docstring': docstring is not None,
            'is_private': is_private,
            'line_number': node.lineno,
            'args': args,
            'return_type': return_type,
            'class': self.current_class
        }
        
        self.functions.append(func_info)
        
        # Track missing docstrings for public functions
        if not is_private and not docstring:
            location = f"{self.current_class}.{node.name}" if self.current_class else node.name
            self.missing_docstrings.append(location)
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and extract documentation info."""
        docstring = ast.get_docstring(node)
        is_private = node.name.startswith('_')
        
        prev_class = self.current_class
        self.current_class = node.name
        
        class_info = {
            'name': node.name,
            'docstring': docstring,
            'has_docstring': docstring is not None,
            'is_private': is_private,
            'line_number': node.lineno,
            'methods': []
        }
        
        self.classes.append(class_info)
        
        # Track missing docstrings for public classes
        if not is_private and not docstring:
            self.missing_docstrings.append(node.name)
        
        self.generic_visit(node)
        self.current_class = prev_class
    
    def _get_annotation_string(self, annotation) -> Optional[str]:
        """Convert AST annotation to string representation."""
        if annotation is None:
            return None
        
        try:
            if isinstance(annotation, ast.Name):
                return annotation.id
            elif isinstance(annotation, ast.Constant):
                return str(annotation.value)
            elif isinstance(annotation, ast.Attribute):
                return f"{self._get_annotation_string(annotation.value)}.{annotation.attr}"
            elif isinstance(annotation, ast.Subscript):
                value = self._get_annotation_string(annotation.value)
                slice_val = self._get_annotation_string(annotation.slice)
                return f"{value}[{slice_val}]"
            else:
                return ast.unparse(annotation)
        except Exception:
            return "Unknown"

class DocumentationGenerator:
    """Main documentation generator class."""
    
    def __init__(self, output_dir: str = "docs/generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_file(self, file_path: Path) -> DocstringAnalyzer:
        """Analyze a Python file for documentation completeness."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = DocstringAnalyzer()
            analyzer.visit(tree)
            
            return analyzer
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
            return DocstringAnalyzer()
    
    def scan_codebase(self, include_private: bool = False) -> Dict:
        """Scan the entire codebase for documentation analysis."""
        results = {
            'files_analyzed': 0,
            'total_functions': 0,
            'documented_functions': 0,
            'total_classes': 0,
            'documented_classes': 0,
            'missing_docstrings': [],
            'files': {}
        }
        
        # Define directories to scan
        scan_dirs = ['core', 'services', 'api']
        
        for scan_dir in scan_dirs:
            dir_path = Path(scan_dir)
            if not dir_path.exists():
                continue
                
            for py_file in dir_path.rglob('*.py'):
                if py_file.name == '__init__.py':
                    continue
                
                self.logger.info(f"Analyzing {py_file}")
                analyzer = self.analyze_file(py_file)
                
                # Filter private items if requested
                functions = analyzer.functions
                classes = analyzer.classes
                
                if not include_private:
                    functions = [f for f in functions if not f['is_private']]
                    classes = [c for c in classes if not c['is_private']]
                
                results['files'][str(py_file)] = {
                    'functions': functions,
                    'classes': classes,
                    'missing_docstrings': analyzer.missing_docstrings
                }
                
                results['files_analyzed'] += 1
                results['total_functions'] += len(functions)
                results['documented_functions'] += sum(1 for f in functions if f['has_docstring'])
                results['total_classes'] += len(classes)
                results['documented_classes'] += sum(1 for c in classes if c['has_docstring'])
                results['missing_docstrings'].extend(analyzer.missing_docstrings)
        
        return results
    
    def generate_coverage_report(self, results: Dict) -> str:
        """Generate documentation coverage report."""
        total_functions = results['total_functions']
        documented_functions = results['documented_functions']
        total_classes = results['total_classes']
        documented_classes = results['documented_classes']
        
        func_coverage = (documented_functions / total_functions * 100) if total_functions > 0 else 100
        class_coverage = (documented_classes / total_classes * 100) if total_classes > 0 else 100
        overall_coverage = ((documented_functions + documented_classes) / 
                          (total_functions + total_classes) * 100) if (total_functions + total_classes) > 0 else 100
        
        report = f"""# Documentation Coverage Report

## Summary
- **Files Analyzed**: {results['files_analyzed']}
- **Overall Coverage**: {overall_coverage:.1f}%

## Functions
- **Total Functions**: {total_functions}
- **Documented Functions**: {documented_functions}
- **Function Coverage**: {func_coverage:.1f}%

## Classes
- **Total Classes**: {total_classes}
- **Documented Classes**: {documented_classes}
- **Class Coverage**: {class_coverage:.1f}%

## Missing Docstrings
"""
        
        if results['missing_docstrings']:
            report += "\nThe following items are missing docstrings:\n\n"
            for item in sorted(set(results['missing_docstrings'])):
                report += f"- `{item}`\n"
        else:
            report += "\n✅ All public functions and classes have docstrings!\n"
        
        return report
    
    def generate_api_reference(self, results: Dict) -> str:
        """Generate API reference documentation."""
        api_doc = "# API Reference\n\n"
        
        for file_path, file_data in results['files'].items():
            api_doc += f"## {file_path}\n\n"
            
            # Document classes
            for class_info in file_data['classes']:
                api_doc += f"### class {class_info['name']}\n\n"
                if class_info['docstring']:
                    api_doc += f"{class_info['docstring']}\n\n"
                else:
                    api_doc += "*No documentation available*\n\n"
                
                # Document class methods
                class_methods = [f for f in file_data['functions'] if f['class'] == class_info['name']]
                for method in class_methods:
                    api_doc += f"#### {method['name']}({', '.join(arg['name'] for arg in method['args'])})\n\n"
                    if method['docstring']:
                        api_doc += f"{method['docstring']}\n\n"
                    else:
                        api_doc += "*No documentation available*\n\n"
            
            # Document standalone functions
            standalone_functions = [f for f in file_data['functions'] if f['class'] is None]
            if standalone_functions:
                api_doc += "### Functions\n\n"
                for func in standalone_functions:
                    args_str = ', '.join(f"{arg['name']}: {arg['type'] or 'Any'}" for arg in func['args'])
                    return_str = f" -> {func['return_type']}" if func['return_type'] else ""
                    api_doc += f"#### {func['name']}({args_str}){return_str}\n\n"
                    if func['docstring']:
                        api_doc += f"{func['docstring']}\n\n"
                    else:
                        api_doc += "*No documentation available*\n\n"
        
        return api_doc
    
    def run(self, 
            format_type: str = 'html',
            include_private: bool = False,
            validate_only: bool = False,
            generate_coverage: bool = True) -> None:
        """Run the documentation generation process."""
        
        self.logger.info("Starting documentation analysis...")
        results = self.scan_codebase(include_private=include_private)
        
        if validate_only:
            # Just validate and report
            coverage_report = self.generate_coverage_report(results)
            print(coverage_report)
            return
        
        # Generate coverage report
        if generate_coverage:
            coverage_report = self.generate_coverage_report(results)
            coverage_path = self.output_dir / "coverage.md"
            with open(coverage_path, 'w') as f:
                f.write(coverage_report)
            self.logger.info(f"Coverage report written to {coverage_path}")
        
        # Generate API reference
        api_reference = self.generate_api_reference(results)
        api_path = self.output_dir / "api-reference-generated.md"
        with open(api_path, 'w') as f:
            f.write(api_reference)
        self.logger.info(f"API reference written to {api_path}")
        
        # Print summary
        total_items = results['total_functions'] + results['total_classes']
        documented_items = results['documented_functions'] + results['documented_classes'] 
        coverage_pct = (documented_items / total_items * 100) if total_items > 0 else 100
        
        print(f"\n✅ Documentation generation complete!")
        print(f"📊 Overall coverage: {coverage_pct:.1f}%")
        print(f"📁 Output directory: {self.output_dir}")
        
        if results['missing_docstrings']:
            print(f"⚠️  {len(results['missing_docstrings'])} items missing docstrings")

def main():
    """Main entry point for the documentation generator."""
    parser = argparse.ArgumentParser(description="Generate documentation for Messor codebase")
    parser.add_argument('--format', choices=['html', 'markdown', 'json'], 
                       default='markdown', help='Output format')
    parser.add_argument('--output-dir', default='docs/generated', 
                       help='Output directory')
    parser.add_argument('--include-private', action='store_true',
                       help='Include private methods in documentation')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate existing docstrings')
    parser.add_argument('--coverage', action='store_true', default=True,
                       help='Generate documentation coverage report')
    
    args = parser.parse_args()
    
    generator = DocumentationGenerator(args.output_dir)
    generator.run(
        format_type=args.format,
        include_private=args.include_private,
        validate_only=args.validate_only,
        generate_coverage=args.coverage
    )

if __name__ == '__main__':
    main()