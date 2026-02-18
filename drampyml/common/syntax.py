from sympy import Function

class Max(Function):
    @classmethod
    def eval(cls, a, b):
        if a.is_number and b.is_number:
            return max(a, b)

        return None
