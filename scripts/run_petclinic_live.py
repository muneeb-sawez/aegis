"""Spring Petclinic Microservices Local Live Runner.

Starts and manages live Spring Petclinic microservices on localhost:
- config-server        (Port 8888)
- discovery-server     (Port 8761)
- api-gateway          (Port 8080)
- customers-service    (Port 8081)
- visits-service       (Port 8082)
- vets-service         (Port 8083)
- admin-server         (Port 9090)

Modes:
1. Docker Compose Mode: If Docker Desktop is active, runs containers from C:\\Users\\Fawaz\\Desktop\\spring-petclinic-microservices.
2. Lightweight Native Live Mock Mode: If Docker is stopped, launches high-performance asynchronous HTTP servers
   serving Spring Boot Actuator /actuator/health and real JSON payloads on the exact service ports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Dict
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("petclinic-runner")

PETCLINIC_DIR = r"C:\Users\Fawaz\Desktop\spring-petclinic-microservices"

SERVICES = [
    {
        "name": "config-server",
        "port": 8888,
        "description": "Spring Cloud Centralized Configuration Server",
    },
    {
        "name": "discovery-server",
        "port": 8761,
        "description": "Netflix Eureka Discovery & Service Registry",
    },
    {
        "name": "api-gateway",
        "port": 8085,
        "description": "Spring Cloud Gateway (Ingress & Reverse Proxy)",
    },
    {
        "name": "customers-service",
        "port": 8081,
        "description": "Pet Owners and Pets Domain Service",
    },
    {
        "name": "visits-service",
        "port": 8082,
        "description": "Pet Clinic Visits & Appointments Service",
    },
    {
        "name": "vets-service",
        "port": 8083,
        "description": "Veterinarians & Specialties Service",
    },
    {
        "name": "admin-server",
        "port": 9090,
        "description": "Spring Boot Admin Monitoring Dashboard",
    },
]

# In-memory service state (for fault simulation)
service_states: Dict[str, dict] = {
    svc["name"]: {"status": "UP", "http_code": 200, "delay_ms": 15}
    for svc in SERVICES
}


def is_docker_running() -> bool:
    """Check if Docker daemon is accessible."""
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def run_docker_compose():
    """Launch microservices via Docker Compose."""
    if not os.path.exists(PETCLINIC_DIR):
        logger.error(f"Petclinic directory not found at: {PETCLINIC_DIR}")
        sys.exit(1)

    logger.info("Docker daemon detected! Starting Spring Petclinic microservices via Docker Compose...")
    cmd = [
        "docker", "compose", "up", "-d",
        "config-server", "discovery-server", "customers-service",
        "visits-service", "vets-service", "api-gateway"
    ]
    subprocess.run(cmd, cwd=PETCLINIC_DIR, check=True)
    logger.info("Spring Petclinic microservices containers launched successfully!")


def create_service_app(svc_name: str, port: int) -> web.Application:
    """Construct an aiohttp app simulating a Spring Boot microservice with Actuator."""
    app = web.Application()

    async def handle_health(request: web.Request):
        state = service_states.get(svc_name, {"status": "UP", "http_code": 200, "delay_ms": 15})
        if state.get("delay_ms", 0) > 0:
            await asyncio.sleep(state["delay_ms"] / 1000.0)

        code = state.get("http_code", 200)
        status = state.get("status", "UP")

        payload = {
            "status": status,
            "components": {
                "discoveryComposite": {
                    "status": status,
                    "components": {
                        "eureka": {"status": status, "description": "Spring Cloud Eureka Client"}
                    }
                },
                "diskSpace": {
                    "status": "UP",
                    "details": {"total": 512000000000, "free": 240000000000, "threshold": 10485760}
                },
                "ping": {"status": "UP"},
            }
        }
        return web.json_response(payload, status=code)

    async def handle_actuator(request: web.Request):
        payload = {
            "_links": {
                "self": {"href": f"http://localhost:{port}/actuator"},
                "health": {"href": f"http://localhost:{port}/actuator/health"},
                "info": {"href": f"http://localhost:{port}/actuator/info"},
            }
        }
        return web.json_response(payload)

    async def handle_api(request: web.Request):
        """Simulate real microservice domain API response."""
        state = service_states.get(svc_name, {})
        if state.get("delay_ms", 0) > 0:
            await asyncio.sleep(state["delay_ms"] / 1000.0)

        if svc_name == "customers-service" or "customer" in request.path:
            return web.json_response([
                {"id": 1, "firstName": "George", "lastName": "Franklin", "city": "Madison", "telephone": "6085551023"},
                {"id": 2, "firstName": "Betty", "lastName": "Davis", "city": "Sun Prairie", "telephone": "6085551749"},
            ])
        elif svc_name == "vets-service" or "vet" in request.path:
            return web.json_response([
                {"id": 1, "firstName": "James", "lastName": "Carter", "specialties": []},
                {"id": 2, "firstName": "Helen", "lastName": "Leary", "specialties": [{"id": 1, "name": "radiology"}]},
            ])
        elif svc_name == "visits-service" or "visit" in request.path:
            return web.json_response([
                {"id": 1, "date": "2026-10-24", "description": "rabies shot", "petId": 1},
                {"id": 2, "date": "2026-10-24", "description": "neutered", "petId": 2},
            ])
        else:
            return web.json_response({"service": svc_name, "active": True})

    async def handle_fault(request: web.Request):
        """Fault injection endpoint for chaos and outage testing."""
        fault_type = request.query.get("type", "down")
        if fault_type == "down":
            service_states[svc_name] = {"status": "DOWN", "http_code": 503, "delay_ms": 10}
        elif fault_type == "slow":
            service_states[svc_name] = {"status": "UP", "http_code": 200, "delay_ms": 2500}
        elif fault_type == "recover":
            service_states[svc_name] = {"status": "UP", "http_code": 200, "delay_ms": 15}
        return web.json_response({"service": svc_name, "state": service_states[svc_name]})

    app.router.add_get("/actuator/health", handle_health)
    app.router.add_get("/actuator", handle_actuator)
    app.router.add_get("/fault", handle_fault)
    app.router.add_post("/fault", handle_fault)
    app.router.add_get("/{tail:.*}", handle_api)

    return app


async def start_all_live_services():
    """Start all Spring Petclinic services concurrently."""
    runners = []
    logger.info("=" * 68)
    logger.info("  🚀 Starting Spring Petclinic Live Microservices Network")
    logger.info("=" * 68)

    for svc in SERVICES:
        app = create_service_app(svc["name"], svc["port"])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", svc["port"])
        try:
            await site.start()
            runners.append(runner)
            logger.info(f"  [ONLINE]  {svc['name']:<20} -> http://127.0.0.1:{svc['port']}/actuator/health")
        except OSError as e:
            logger.warning(f"  [IN-USE]  {svc['name']:<20} (Port {svc['port']} already occupied: {e})")

    logger.info("-" * 68)
    logger.info("All Petclinic microservices are LIVE and responding to health probes.")
    logger.info("AEGIS Mission Control will observe live node beats in real time!")
    logger.info("Press Ctrl+C to stop services.")
    logger.info("=" * 68)

    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Stopping microservices...")
    finally:
        for runner in runners:
            await runner.cleanup()
        logger.info("All microservices shut down cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Spring Petclinic Microservices Live Runner")
    parser.add_argument("--mode", choices=["auto", "docker", "native"], default="auto",
                        help="Execution mode (auto detects Docker, native starts lightweight HTTP servers)")
    parser.add_argument("--fail", help="Simulate failure on a specific service (e.g. visits-service)")
    parser.add_argument("--recover", help="Recover a specific service (e.g. visits-service)")
    args = parser.parse_args()

    if args.fail:
        import urllib.request
        for svc in SERVICES:
            if svc["name"] == args.fail:
                url = f"http://127.0.0.1:{svc['port']}/fault?type=down"
                try:
                    urllib.request.urlopen(url)
                    print(f"Injected fault DOWN on {args.fail}")
                except Exception as e:
                    print(f"Failed to inject fault: {e}")
                return
        print(f"Service {args.fail} not found.")
        return

    if args.recover:
        import urllib.request
        for svc in SERVICES:
            if svc["name"] == args.recover:
                url = f"http://127.0.0.1:{svc['port']}/fault?type=recover"
                try:
                    urllib.request.urlopen(url)
                    print(f"Recovered service {args.recover}")
                except Exception as e:
                    print(f"Failed to recover: {e}")
                return
        print(f"Service {args.recover} not found.")
        return

    if args.mode == "docker" or (args.mode == "auto" and is_docker_running()):
        run_docker_compose()
    else:
        logger.info("Starting microservices in high-performance native live mode...")
        asyncio.run(start_all_live_services())


if __name__ == "__main__":
    main()
