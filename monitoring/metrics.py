"""
FILE PURPOSE: FastAPI Prometheus Metrics Setup

This file configures HTTP metrics for the Production AI Platform API.

It uses prometheus-fastapi-instrumentator to:

1. Instrument FastAPI request handling.
2. Collect request metrics such as traffic, status codes, and latency.
3. Expose the collected metrics through a Prometheus-compatible endpoint.
4. Allow Prometheus to scrape the API for dashboards and alerts.

Application flow:

app/main.py
    -> setup_metrics(app)
    -> Instrument FastAPI
    -> Expose Prometheus metrics endpoint
    -> Prometheus scrapes metrics
    -> Grafana dashboards and alerting rules use the data

This module is imported by app/main.py during application initialization.
"""

# Import FastAPI for the application type annotation.
from fastapi import FastAPI

# Import the third-party helper that instruments FastAPI for Prometheus.
from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app: FastAPI) -> None:
    """
    Add Prometheus instrumentation to a FastAPI application.

    Args:
        app:
            The FastAPI application that should be monitored.

    Returns:
        None. The supplied FastAPI application is configured in place.

    Called by:
        app/main.py
    """

    # Create the Prometheus instrumentation manager.
    # This object controls metric collection and metric endpoint exposure.
    instrumentator = Instrumentator()

    # Attach instrumentation to the FastAPI application.
    # This allows the library to observe HTTP request and response activity.
    instrumentator.instrument(app)

    # Add the Prometheus metrics endpoint to the same FastAPI application.
    # Prometheus can scrape this endpoint to collect the generated metrics.
    instrumentator.expose(app)
