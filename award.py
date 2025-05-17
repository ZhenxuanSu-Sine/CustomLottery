from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Callable
import operator

@dataclass
class Award:
    name: str
    award_type: str
    base_prob: float
    remaining: Optional[int] 
    operation: Optional[Dict[str, Any]] 
    current_prob: float = field(init=False)
    effect: Optional[Callable[[int], int]] = None
    def __post_init__(self):
        if self.base_prob < 0 or self.base_prob > 100:
            raise ValueError(f"Base probability must be between 0 and 100, got {self.base_prob}")

        self.current_prob = self.base_prob
        if self.operation:
            operation_map = {
                'add': operator.add,
                'sub': operator.sub,
                'mul': operator.mul,
                'div': operator.floordiv,
            }
            try:
                self.effect = lambda x: operation_map[self.operation['type']](x, self.operation['value'])
            except KeyError:
                raise ValueError(f"Unsupported operation type: {self.operation['type']}. Supported types are {list(operation_map.keys())}.")
        
    def to_json(self):
        d = asdict(self)
        return {k: v for k, v in d.items() if k in ['name', 'award_type', 'base_prob', 'remaining', 'operation'] and v is not None}

    def is_active(self):
        if self.base_prob == 0:
            return False
        return (self.award_type != '限量') or (self.remaining and self.remaining > 0)
