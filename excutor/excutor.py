# modified code from https://github.com/microsoft/autogen/blob/main/autogen/coding/docker_commandline_code_executor.py

import docker
from docker.errors import ImageNotFound,NotFound
import logging
import uuid
from hashlib import md5
import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
import re,os
from .utils import CommandLineCodeResult 

TIMEOUT_MSG = "Timeout"

def _wait_for_ready(container: Any, timeout: int = 60, stop_time: float = 0.1) -> None:
    elapsed_time = 0.0
    while container.status != "running" and elapsed_time < timeout:
        time.sleep(stop_time)
        elapsed_time += stop_time
        container.reload()
        continue
    if container.status != "running":
        raise ValueError("Container failed to start")

def _cmd(lang: str) -> str:
    if lang in ["py","python"]:
        return "python"
    if lang.startswith("python") or lang in ["bash", "sh"]:
        return lang
    if lang in ["shell"]:
        return "sh"
    if lang == "javascript":
        return "node"

    raise NotImplementedError(f"{lang} not recognized in code execution")
    
def silence_pip(code: str, lang: str) -> str:
    """Apply -qqq flag to pip install commands."""
    if lang == "python":
        regex = r"^! ?pip install"
    elif lang in ["bash", "shell", "sh", "pwsh", "powershell", "ps1"]:
        regex = r"^pip install"
    else:
        return code

    # Find lines that start with pip install and make sure "-qqq" flag is added.
    lines = code.split("\n")
    for i, line in enumerate(lines):
        # use regex to find lines that start with pip install.
        match = re.search(regex, line)
        if match is not None:
            if "-qqq" not in line:
                lines[i] = line.replace(match.group(0), match.group(0) + " -qqq")
    return "\n".join(lines)
    
class CodeExecutor: 
    DEFAULT_EXECUTION_POLICY: ClassVar[Dict[str, bool]] = {
        "bash": True,
        "shell": True,
        "sh": True,
        "pwsh": False,
        "powershell": False,
        "ps1": False,
        "python": True,
        "javascript": False,
        "html": False,
        "css": False,
    }
    LANGUAGE_ALIASES: ClassVar[Dict[str, str]] = {"py": "python", "js": "javascript"}

    def __init__(self, 
                image: str = "python:3-slim", 
                container_name = None,
                timeout: int = 60,
                auto_remove: bool = True,
                work_dir = "./code",
                bind_dir = None,
                stop_container: bool = True,
                ):
        self._client = docker.from_env()
        self._image = image
        if container_name is None:
            container_name = f"code-exec-{uuid.uuid4()}"
        self._container_name = container_name
        self._timeout = timeout
        self._auto_remove = auto_remove
        self._bind_dir = bind_dir
        self._work_dir = work_dir  
        self._stop_container = stop_container  
        
        # Check if the image exists
        try:
            self._client.images.get(image)
        except ImageNotFound:
            logging.info(f"Pulling image {image}...")
            # Let the docker exception escape if this fails.
            self._client.images.pull(image)
        # Start a container from the image, read to exec commands later
        try:
            self._container = self._client.containers.get(container_name)
        except NotFound:
            self._container = self._client.containers.create(
                image,
                name=container_name,
                entrypoint="/bin/sh",
                tty=True,
                auto_remove=auto_remove,
                volumes={bind_dir: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace"
            )
        # Start the container if it is not running
        if self._container.status != "running":
            self._container.start()
            _wait_for_ready(self._container)
        
    def execute_code_blocks(self, code_blocks: List[str]) -> List[str]:
        outputs = []
        files = []
        last_exit_code = 0
        for code_block in code_blocks:
            lang = self.LANGUAGE_ALIASES.get(code_block.language.lower(), code_block.language.lower())
            if lang not in self.DEFAULT_EXECUTION_POLICY:
                outputs.append(f"Unsupported language {lang}\n")
                last_exit_code = 1
                break
            code = silence_pip(code_block.code, lang)

            filename = f"tmp_code_{md5(code.encode()).hexdigest()}.{lang}"

            code_path = os.path.join(self._work_dir, filename)
            with open(code_path, "w") as fout:
                fout.write(code)
            files.append(code_path)

            command = ["timeout", str(self._timeout), _cmd(lang), filename]
            result = self._container.exec_run(command)
            exit_code = result.exit_code
            output = result.output.decode("utf-8")
            if exit_code == 124:
                output += "\n" + TIMEOUT_MSG
            outputs.append(output)

            last_exit_code = exit_code
            if exit_code != 0:
                break

        code_file = str(files[0]) if files else None
        return CommandLineCodeResult(exit_code=last_exit_code, output="".join(outputs), code_file=code_file)
    
    def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        self._container.restart()
        if self._container.status != "running":
            raise ValueError(f"Failed to restart container. Logs: {self._container.logs()}")

    def stop(self) -> None:
        """(Experimental) Stop the code executor."""
        try:
            self._container.stop()
        except docker.errors.NotFound:
            pass