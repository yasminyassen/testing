import ast
import json
# pip install radon
from radon.complexity import cc_visit

class ASTCouplingAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.hardcoded_instantiations = 0
        # أمثلة على مكتبات خارجية أو I/O لا يجب استدعاؤها داخل جسم الدالة مباشرة
        self.io_libraries = ['sqlite3', 'smtplib', 'requests', 'pymongo', 'boto3']

    def visit_Call(self, node):
        # البحث عن استدعاءات مثل sqlite3.connect() أو smtplib.SMTP()
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id in self.io_libraries:
                self.hardcoded_instantiations += 1
        self.generic_visit(node)

class ArchitectureEvaluator:
    def __init__(self, code_snippet: str):
        self.code = code_snippet

    def _call_llm(self, metric: str, prompt: str) -> int:
        """
        هنا يتم استدعاء الـ LLM (Gemini, Claude, OpenAI).
        يجب أن يعود الـ LLM برقم فقط من 0 إلى 100.
        """
        system_prompt = f"""
        You are an expert Software Architect. Evaluate the provided Python code strictly for the metric: '{metric}'.
        {prompt}
        Output ONLY an integer between 0 and 100 representing the score. No explanations.
        """
        # محاكاة لرد الـ LLM (في التطبيق الحقيقي استبدل هذا باستدعاء الـ API)
        # return int(api_response.text.strip())
        pass 

    def evaluate_srp_llm(self) -> int:
        prompt = "Does the code follow the Single Responsibility Principle? Penalize functions or classes that mix database, network, and business logic."
        return self._call_llm("SRP / Layer Count", prompt)

    def evaluate_cohesion_llm(self) -> int:
        prompt = "Evaluate semantic cohesion. Do not be fooled by coincidental cohesion (e.g., sharing a global DB variable). Do the functions and variables logically belong to the same specific domain?"
        return self._call_llm("Cohesion", prompt)

    def evaluate_god_class_hybrid(self) -> int:
        # 1. Static Analysis (Cyclomatic Complexity via Radon)
        try:
            blocks = cc_visit(self.code)
            max_complexity = max([block.complexity for block in blocks]) if blocks else 0
        except:
            max_complexity = 0
        
        # تحويل التعقيد لسكور (كل ما زاد التعقيد، قل السكور)
        static_score = max(0, 100 - (max_complexity * 5))

        # 2. LLM Analysis
        prompt = "Does this code act as a 'God Class' or 'God Function' controlling too many entities? Ignore line count, focus on centralization of control."
        llm_score = self._call_llm("God Class", prompt)

        # دمج النتيجتين (نعطي وزن أكبر للـ LLM)
        return int((static_score * 0.4) + (llm_score * 0.6))

    def evaluate_coupling_hybrid(self) -> int:
        # 1. Static Analysis (AST detection of hardcoded IO)
        tree = ast.parse(self.code)
        visitor = ASTCouplingAnalyzer()
        visitor.visit(tree)
        
        # خصم 20 نقطة على كل استدعاء مباشر (Hardcoded instantiation)
        static_score = max(0, 100 - (visitor.hardcoded_instantiations * 20))

        # 2. LLM Analysis
        prompt = "Evaluate efferent coupling. Is the business logic tightly coupled to concrete implementations (like specific payment or email services) instead of interfaces?"
        llm_score = self._call_llm("Coupling", prompt)

        return int((static_score * 0.5) + (llm_score * 0.5))

    # بقية الـ Metrics يتم تقييمها بنفس نمط הـ SRP
    def evaluate_di_llm(self) -> int:
        prompt = "Is Dependency Injection used? Are resources like DB connections or external services passed as arguments/interfaces rather than instantiated globally or inside functions?"
        return self._call_llm("Dependency Injection", prompt)

    def get_full_report(self):
        # محاكاة لجمع كل النتائج
        print("Running Architecture Pipeline...")
        # سيقوم الكود باستدعاء الدوال وإرجاع JSON بالنتيجة النهائية
