from __future__ import annotations

import asyncio
import logging
import os
import typing
import uuid
from abc import ABC, abstractmethod

if typing.TYPE_CHECKING:
    from . import app

class SandboxInstance(ABC):
    """Abstract base class for a sandbox instance"""
    
    id: str
    
    def __init__(self, id: str):
        self.id = id

    @abstractmethod
    async def start(self):
        """Start the sandbox instance"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the sandbox instance"""
        pass

    @abstractmethod
    async def execute_command(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Execute a command in the sandbox
        
        Returns:
            tuple[int, str, str]: (exit_code, stdout, stderr)
        """
        pass

    @abstractmethod
    async def upload_file(self, src_path: str, dest_path: str):
        """Upload a file to the sandbox"""
        pass

    @abstractmethod
    async def download_file(self, src_path: str, dest_path: str):
        """Download a file from the sandbox"""
        pass


class FirecrackerSandbox(SandboxInstance):
    """Firecracker implementation of SandboxInstance"""
    
    # Note: This is a placeholder implementation. 
    # Real Firecracker integration requires interacting with the Firecracker API socket
    # and managing tap devices, which is complex and system-dependent.
    # For this MVP, we will simulate the interface or use a wrapper if available.
    # Since we are in a dev environment without actual Firecracker installed, 
    # we might need to mock this or use Docker as a fallback for "sandbox" behavior in dev.
    
    def __init__(self, id: str, config: dict):
        super().__init__(id)
        self.config = config
        self.process = None

    async def start(self):
        # In a real implementation, this would start the firecracker process
        pass

    async def stop(self):
        # Kill the firecracker process
        pass

    async def execute_command(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        # Send command to VM via API or SSH
        return 0, "simulated output", ""

    async def upload_file(self, src_path: str, dest_path: str):
        pass

    async def download_file(self, src_path: str, dest_path: str):
        pass


class DockerSandbox(SandboxInstance):
    """Docker implementation of SandboxInstance (easier for dev/testing)"""
    
    container_id: str | None = None
    
    def __init__(self, id: str, image: str = "alpine:latest"):
        super().__init__(id)
        self.image = image

    async def start(self):
        process = await asyncio.create_subprocess_exec(
            "docker", "run", "-d", "--rm", "-i", "--name", f"sandbox_{self.id}", self.image, "sh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to start docker sandbox: {stderr.decode()}")
        self.container_id = stdout.decode().strip()

    async def stop(self):
        if self.container_id:
            process = await asyncio.create_subprocess_exec(
                "docker", "stop", self.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            self.container_id = None

    async def execute_command(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        if not self.container_id:
            raise Exception("Sandbox not started")
            
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", self.container_id, "sh", "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            process.kill()
            return -1, "", "Command timed out"

    async def upload_file(self, src_path: str, dest_path: str):
        if not self.container_id:
            raise Exception("Sandbox not started")
        
        process = await asyncio.create_subprocess_exec(
            "docker", "cp", src_path, f"{self.container_id}:{dest_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

    async def download_file(self, src_path: str, dest_path: str):
        if not self.container_id:
            raise Exception("Sandbox not started")
            
        process = await asyncio.create_subprocess_exec(
            "docker", "cp", f"{self.container_id}:{src_path}", dest_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()


class SandboxManager:
    """Manager for sandbox instances"""
    
    ap: app.Application
    instances: dict[str, SandboxInstance]
    
    def __init__(self, ap: app.Application):
        self.ap = ap
        self.instances = {}

    async def create_sandbox(self, type: str = "docker", config: dict = None) -> SandboxInstance:
        sandbox_id = str(uuid.uuid4())
        
        if type == "firecracker":
            # For now, fallback to Docker or mock if Firecracker is not set up
            # sandbox = FirecrackerSandbox(sandbox_id, config or {})
            self.ap.logger.warning("Firecracker not fully implemented, falling back to Docker")
            sandbox = DockerSandbox(sandbox_id)
        elif type == "docker":
            sandbox = DockerSandbox(sandbox_id, config.get("image", "alpine:latest") if config else "alpine:latest")
        else:
            raise ValueError(f"Unknown sandbox type: {type}")
            
        await sandbox.start()
        self.instances[sandbox_id] = sandbox
        return sandbox

    async def get_sandbox(self, sandbox_id: str) -> SandboxInstance | None:
        return self.instances.get(sandbox_id)

    async def destroy_sandbox(self, sandbox_id: str):
        if sandbox_id in self.instances:
            sandbox = self.instances[sandbox_id]
            await sandbox.stop()
            del self.instances[sandbox_id]

    async def shutdown(self):
        for sandbox_id in list(self.instances.keys()):
            await self.destroy_sandbox(sandbox_id)
