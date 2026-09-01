"""
config/__init__.py

Parche de compatibilidad para Python 3.14+ con Django Template Context.
En Python 3.14+, copy(super()) en BaseContext.__copy__ produce AttributeError
porque el proxy super() no tiene __dict__.
"""
try:
    from django.template import context as _dt_context

    def _safe_base_context_copy(self):
        duplicate = object.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    def _safe_request_context_copy(self):
        duplicate = _safe_base_context_copy(self)
        duplicate.request = self.request
        return duplicate

    _dt_context.BaseContext.__copy__ = _safe_base_context_copy
    _dt_context.RequestContext.__copy__ = _safe_request_context_copy
except Exception:
    pass
