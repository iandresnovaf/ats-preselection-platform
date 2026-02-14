"""Endpoint de métricas para Prometheus."""
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.metrics import get_prometheus_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Endpoint para métricas de Prometheus.
    
    Expone todas las métricas en formato Prometheus para scraping.
    """
    metrics_data = get_prometheus_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )
