"""
title: n8n Workflow Trigger
author: HomeAI
description: Triggers n8n workflows from Open WebUI. Use when asked to run automations,
             send digests, trigger workflows, or execute any n8n-based task.
version: 1.0.0
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        n8n_webhook_url: str = Field(
            default="http://localhost:5678/webhook/openwebui",
            description="Base webhook URL for your n8n instance",
        )
        auth_token: Optional[str] = Field(
            default=None,
            description="Optional Bearer token if your n8n webhook requires authentication",
        )
        timeout_seconds: int = Field(
            default=30,
            description="How long to wait for n8n to respond before timing out",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def trigger_workflow(
        self,
        workflow: str,
        message: str,
        data: Optional[dict] = None,
        __event_emitter__=None,
    ) -> str:
        """
        Trigger an n8n workflow via webhook. Use this when the user asks to run
        an automation, send a digest, execute a workflow, or trigger any n8n task.

        :param workflow: Name of the workflow to trigger (e.g. "morning_digest", "seo_report", "send_email")
        :param message: The main instruction or content to pass to the workflow
        :param data: Optional extra key/value pairs to include in the payload
        :return: Response from n8n confirming the workflow ran
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": f"Triggering n8n workflow: {workflow}...", "done": False},
            })

        payload = json.dumps({
            "workflow": workflow,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if self.valves.auth_token:
            headers["Authorization"] = f"Bearer {self.valves.auth_token}"

        try:
            req = urllib.request.Request(
                self.valves.n8n_webhook_url,
                data=payload,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.valves.timeout_seconds) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"n8n responded: {status}", "done": True},
                })

            try:
                result = json.loads(body)
                return f"Workflow `{workflow}` completed.\n\n```json\n{json.dumps(result, indent=2)}\n```"
            except Exception:
                return f"Workflow `{workflow}` completed.\n\n{body}"

        except urllib.error.URLError as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Could not reach n8n: {e.reason}", "done": True},
                })
            return (
                f"Could not connect to n8n at `{self.valves.n8n_webhook_url}`. "
                f"Make sure n8n is running on your Mac. Error: {e.reason}"
            )

        except TimeoutError:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "n8n timed out", "done": True},
                })
            return (
                f"n8n did not respond within {self.valves.timeout_seconds} seconds. "
                f"The workflow may still be running — check n8n directly."
            )

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Error: {e}", "done": True},
                })
            return f"Unexpected error triggering workflow: {e}"
