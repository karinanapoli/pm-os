"""Minimal MCP stdio client for local capability discovery."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from typing import Any

from pm_os.web.mcp_client import PROTOCOL_VERSION, MCPDiscovery, MCPError


class MCPStdioClient:
    def __init__(self, timeout: float = 10):
        self.timeout = timeout
        self._request_id = 0

    def discover(self, connection: dict[str, Any]) -> MCPDiscovery:
        command = str(connection.get("command") or "").strip()
        if not command:
            raise MCPError("Informe o comando do servidor stdio.")
        args = [str(item) for item in (connection.get("args") or [])]
        custom_env = connection.get("env") or {}
        if not isinstance(custom_env, dict):
            raise MCPError("As variáveis de ambiente do servidor stdio são inválidas.")
        process_env = {
            **os.environ,
            **{str(key): str(value) for key, value in custom_env.items()},
        }
        try:
            process = subprocess.Popen(
                [command, *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=process_env,
                shell=False,
                bufsize=1,
            )
        except (FileNotFoundError, PermissionError, OSError) as exc:
            raise MCPError(f"Não foi possível iniciar o comando stdio: {exc}") from exc

        try:
            initialized = self._call(process, "initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "PM Studio", "version": "0.1.0"},
            })
            self._send(process, {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })
            capabilities = initialized.get("capabilities") or {}
            tools = []
            if "tools" in capabilities:
                tools = (self._call(process, "tools/list", {}).get("tools") or [])
            server_info = initialized.get("serverInfo") or {}
            return MCPDiscovery(
                protocol_version=str(initialized.get("protocolVersion") or PROTOCOL_VERSION),
                server_name=str(server_info.get("name") or connection.get("name") or "MCP"),
                server_version=str(server_info.get("version") or ""),
                tools=[
                    {
                        "name": str(tool.get("name") or ""),
                        "description": str(tool.get("description") or "")[:300],
                    }
                    for tool in tools
                    if isinstance(tool, dict) and tool.get("name")
                ],
                resources_supported="resources" in capabilities,
                prompts_supported="prompts" in capabilities,
            )
        finally:
            self._stop(process)

    def _call(
        self,
        process: subprocess.Popen,
        method: str,
        params: dict,
    ) -> dict:
        self._request_id += 1
        request_id = self._request_id
        self._send(process, {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        })
        deadline = time.monotonic() + self.timeout
        selector = selectors.DefaultSelector()
        if process.stdout is None:
            raise MCPError("O processo stdio não abriu a saída padrão.")
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    detail = self._stderr(process)
                    raise MCPError(
                        "O servidor stdio encerrou antes de responder."
                        + (f" {detail}" if detail else "")
                    )
                events = selector.select(max(0, deadline - time.monotonic()))
                if not events:
                    continue
                line = process.stdout.readline()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != request_id:
                    continue
                if message.get("error"):
                    error = message["error"]
                    raise MCPError(str(error.get("message") or "O servidor stdio retornou um erro.")[:300])
                if isinstance(message.get("result"), dict):
                    return message["result"]
                raise MCPError("Resposta stdio inválida: campo result ausente.")
        finally:
            selector.close()
        raise MCPError("O servidor stdio não respondeu dentro do limite de tempo.")

    @staticmethod
    def _send(process: subprocess.Popen, payload: dict) -> None:
        if process.stdin is None:
            raise MCPError("O processo stdio não abriu a entrada padrão.")
        try:
            process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError("Não foi possível enviar dados ao servidor stdio.") from exc

    @staticmethod
    def _stderr(process: subprocess.Popen) -> str:
        if process.stderr is None:
            return ""
        try:
            return process.stderr.read(500).strip()
        except OSError:
            return ""

    @staticmethod
    def _stop(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
