import ast
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ComplexityAnalyzer(ast.NodeVisitor):
    """
    AST 复杂度分析器
    通过遍历抽象语法树，识别循环嵌套深度，估算时间复杂度
    """
    
    def __init__(self):
        self.max_loop_depth = 0
        self.current_loop_depth = 0
        self.loop_count = 0
        self.function_count = 0
        self.recursive_functions = []
        self.has_recursion = False
        self.total_lines = 0
        self.comment_lines = 0
        self.details = []
    
    def analyze(self, code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "error": f"语法错误: {str(e)}",
                "complexity": "UNKNOWN",
                "details": []
            }
        
        lines = code.split("\n")
        self.total_lines = len(lines)
        self.comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        
        self.visit(tree)
        
        complexity = self._estimate_complexity()
        
        return {
            "complexity": complexity,
            "max_loop_depth": self.max_loop_depth,
            "loop_count": self.loop_count,
            "function_count": self.function_count,
            "has_recursion": self.has_recursion,
            "recursive_functions": self.recursive_functions,
            "total_lines": self.total_lines,
            "comment_lines": self.comment_lines,
            "comment_ratio": round(self.comment_lines / max(self.total_lines, 1) * 100, 1),
            "details": self.details
        }
    
    def visit_For(self, node):
        self._enter_loop(node, "for")
        self.generic_visit(node)
        self._exit_loop()
    
    def visit_While(self, node):
        self._enter_loop(node, "while")
        self.generic_visit(node)
        self._exit_loop()
    
    def visit_FunctionDef(self, node):
        self.function_count += 1
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == node.name:
                    self.has_recursion = True
                    self.recursive_functions.append(node.name)
                    self.details.append({
                        "type": "recursion",
                        "name": node.name,
                        "line": node.lineno,
                        "message": f"检测到递归函数: {node.name}"
                    })
                    break
        
        self.generic_visit(node)
    
    def _enter_loop(self, node, loop_type: str):
        self.current_loop_depth += 1
        self.loop_count += 1
        
        if self.current_loop_depth > self.max_loop_depth:
            self.max_loop_depth = self.current_loop_depth
        
        self.details.append({
            "type": "loop",
            "loop_type": loop_type,
            "depth": self.current_loop_depth,
            "line": node.lineno,
            "message": f"第 {node.lineno} 行: {loop_type} 循环（嵌套深度 {self.current_loop_depth}）"
        })
    
    def _exit_loop(self):
        self.current_loop_depth -= 1
    
    def _estimate_complexity(self) -> str:
        if self.has_recursion:
            if self.max_loop_depth >= 2:
                return "O(n²) 或更高（含递归+嵌套循环）"
            elif self.max_loop_depth == 1:
                return "O(n log n) 或 O(n²)（含递归）"
            else:
                return "O(n) 或 O(log n)（递归）"
        
        depth = self.max_loop_depth
        if depth == 0:
            return "O(1)"
        elif depth == 1:
            return "O(n)"
        elif depth == 2:
            return "O(n²)"
        elif depth == 3:
            return "O(n³)"
        else:
            return f"O(n^{depth})"