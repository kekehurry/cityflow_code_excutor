# modified code from https://github.com/microsoft/autogen/blob/main/autogen/coding

from pydantic import BaseModel, Field
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

class CodeBlock(BaseModel):
    """(Experimental) A class that represents a code block."""

    code: str = Field(description="The code to execute.")

    language: str = Field(description="The language of the code.")

class CodeResult(BaseModel):
    """(Experimental) A class that represents the result of a code execution."""
    exit_code: int = Field(description="The exit code of the code execution.")
    output: str = Field(description="The output of the code execution.")


class CommandLineCodeResult(CodeResult):
    """(Experimental) A code result class for command line code executor."""
    code_file: Optional[str] = Field(
        default=None,
        description="The file that the executed code block was saved to.",
    )