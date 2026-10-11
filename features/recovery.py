"""Bounded procedural lessons, never target algorithm evidence or executable repairs."""
import json
from learning.core import save

LESSONS = {
    'locator': 'When a visible locator fails, inspect the current dialog and use one unambiguous observed role, label or row. A row label may include its trailing colon.',
    'readback': 'If numeric readback rejects a setting, inspect the observed domain and current value before a corrected action. Never assume the requested value was applied.',
    'specification': 'Return the exact requested request string. parameter must be exactly one controls label, not instructions. Cite actual observations; retain unresolved facts rather than inventing them.'
}

def category(error):
    message = str(error)
    if message.startswith('Ambiguous or missing visible control:'): return 'locator'
    if message.startswith('Requested value rejected:'): return 'readback'
    return None

class Memory:
    def __init__(self, path): self.path = path
    def load(self):
        if not self.path.exists(): return {}
        if self.path.stat().st_size > 8000: raise ValueError('Recovery memory size limit')
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('schema') != 1: raise ValueError('Recovery memory schema')
        rows = data.get('lessons', {})
        if not isinstance(rows, dict) or not set(rows) <= set(LESSONS): raise ValueError('Unknown recovery lesson')
        for row in rows.values():
            if set(row) != {'failures', 'successful_recoveries'} or any(type(v) is not int or not 0 <= v <= 1000000 for v in row.values()):
                raise ValueError('Invalid recovery counts')
        return rows
    def record(self, kind, recovered=False):
        if kind not in LESSONS: raise ValueError('Unknown recovery category')
        rows = self.load(); row = rows.setdefault(kind, {'failures': 0, 'successful_recoveries': 0})
        row['successful_recoveries' if recovered else 'failures'] += 1
        save(self.path, {'schema': 1, 'scope': 'procedural strategy, not target behavior evidence', 'lessons': rows})
    def guidance(self):
        rows = self.load()
        return {kind: {'strategy': LESSONS[kind], **row} for kind, row in rows.items()}

def validated_decision(invoke, validate, memory, notify=lambda **data: None, attempts=2):
    """One correction at most; invoke enforces the shared deadline/tool budgets."""
    failures = []; previous = None
    for index in range(attempts):
        value = invoke(index, previous)
        try:
            validate(value)
        except ValueError as error:
            previous = {'error': str(error)[:1000], 'previous_specification': value}
            failures.append({'attempt': index + 1, 'error': previous['error']})
            memory.record('specification')
            notify(activity='Specification validation failed; bounded correction pending')
            if index + 1 == attempts: raise
        else:
            if failures: memory.record('specification', recovered=True)
            return value, failures
