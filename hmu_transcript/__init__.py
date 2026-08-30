"""海南医科大学成绩单 → 留学常用分制参考转换。"""

from .pipeline import convert_pdf

__version__ = "0.2.0"
__all__ = ["convert_pdf", "__version__"]
