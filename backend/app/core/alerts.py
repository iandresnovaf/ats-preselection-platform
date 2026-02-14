"""Sistema de alertas para monitoreo de producción."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Callable, Any
from collections import deque
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Niveles de severidad de alertas."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(Enum):
    """Estados de una alerta."""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Representa una alerta."""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    value: float
    threshold: float
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "labels": self.labels or {}
        }


@dataclass
class AlertRule:
    """Regla para generar alertas."""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[], bool]
    get_value: Callable[[], float]
    threshold: float
    duration: timedelta  # Tiempo que debe cumplirse la condición
    cooldown: timedelta  # Tiempo entre alertas repetidas
    labels: Dict[str, str] = None


class AlertManager:
    """Gestor de alertas."""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.notifiers: List[Callable[[Alert], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Trackers para condiciones
        self._condition_start: Dict[str, datetime] = {}
        self._last_alert: Dict[str, datetime] = {}
    
    def add_rule(self, rule: AlertRule):
        """Agrega una regla de alerta."""
        self.rules.append(rule)
        logger.info(f"Alert rule added: {rule.name}")
    
    def add_notifier(self, notifier: Callable[[Alert], None]):
        """Agrega un notificador de alertas."""
        self.notifiers.append(notifier)
    
    async def start(self):
        """Inicia el monitoreo de alertas."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Alert manager started")
    
    async def stop(self):
        """Detiene el monitoreo de alertas."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert manager stopped")
    
    async def _monitor_loop(self):
        """Loop principal de monitoreo."""
        while self._running:
            try:
                await self._check_rules()
                await asyncio.sleep(10)  # Chequear cada 10 segundos
            except Exception as e:
                logger.error(f"Error in alert monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_rules(self):
        """Verifica todas las reglas de alerta."""
        now = datetime.now()
        
        for rule in self.rules:
            try:
                # Verificar cooldown
                last_alert = self._last_alert.get(rule.name)
                if last_alert and (now - last_alert) < rule.cooldown:
                    continue
                
                # Verificar condición
                condition_met = rule.condition()
                
                if condition_met:
                    # Verificar si es la primera vez o si ya pasó el duration
                    if rule.name not in self._condition_start:
                        self._condition_start[rule.name] = now
                    
                    elapsed = now - self._condition_start[rule.name]
                    
                    if elapsed >= rule.duration:
                        # Generar alerta
                        value = rule.get_value()
                        await self._fire_alert(rule, value, now)
                        self._last_alert[rule.name] = now
                        del self._condition_start[rule.name]
                else:
                    # Condición no se cumple, limpiar tracker
                    if rule.name in self._condition_start:
                        del self._condition_start[rule.name]
                    
                    # Verificar si hay alerta activa para resolver
                    await self._resolve_if_needed(rule, now)
                    
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
    
    async def _fire_alert(self, rule: AlertRule, value: float, timestamp: datetime):
        """Dispara una alerta."""
        alert_id = f"{rule.name}_{timestamp.timestamp()}"
        
        alert = Alert(
            id=alert_id,
            name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=rule.description,
            value=value,
            threshold=rule.threshold,
            timestamp=timestamp,
            labels=rule.labels
        )
        
        self.alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"ALERT FIRING: {rule.name} - {rule.description} "
                      f"(value: {value}, threshold: {rule.threshold})")
        
        # Notificar
        for notifier in self.notifiers:
            try:
                notifier(alert)
            except Exception as e:
                logger.error(f"Notifier failed: {e}")
    
    async def _resolve_if_needed(self, rule: AlertRule, timestamp: datetime):
        """Resuelve alertas si la condición ya no se cumple."""
        # Buscar alertas activas de esta regla
        for alert_id, alert in list(self.alerts.items()):
            if alert.name == rule.name and alert.status == AlertStatus.FIRING:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = timestamp
                logger.info(f"ALERT RESOLVED: {rule.name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Obtiene alertas activas."""
        return [a for a in self.alerts.values() if a.status == AlertStatus.FIRING]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Obtiene historial de alertas."""
        return list(self.alert_history)[-limit:]
    
    def acknowledge_alert(self, alert_id: str):
        """Marca una alerta como reconocida."""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            logger.info(f"Alert acknowledged: {alert_id}")


# ============================================
# Notificadores
# ============================================

def console_notifier(alert: Alert):
    """Notificador simple que escribe en consola."""
    emoji = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.WARNING else "🔵"
    print(f"{emoji} [{alert.severity.value.upper()}] {alert.name}: {alert.message}")


def webhook_notifier(webhook_url: str):
    """Crea un notificador que envía a un webhook."""
    import aiohttp
    
    async def _send(alert: Alert):
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(
                    webhook_url,
                    json=alert.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
    
    def notifier(alert: Alert):
        asyncio.create_task(_send(alert))
    
    return notifier


def slack_notifier(webhook_url: str):
    """Crea un notificador para Slack."""
    import aiohttp
    
    async def _send(alert: Alert):
        color = "danger" if alert.severity == AlertSeverity.CRITICAL else "warning" if alert.severity == AlertSeverity.WARNING else "good"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"{alert.name}",
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Status", "value": alert.status.value, "short": True},
                    {"title": "Value", "value": str(alert.value), "short": True},
                    {"title": "Threshold", "value": str(alert.threshold), "short": True},
                ],
                "footer": "ATS Platform Alerts",
                "ts": alert.timestamp.timestamp()
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
    
    def notifier(alert: Alert):
        asyncio.create_task(_send(alert))
    
    return notifier


# ============================================
# Reglas predefinidas
# ============================================

def create_error_rate_rule(error_rate_fn: Callable[[], float]) -> AlertRule:
    """Crea regla para error rate > 5% en 5 minutos."""
    return AlertRule(
        name="high_error_rate",
        description="Error rate excede 5% en los últimos 5 minutos",
        severity=AlertSeverity.CRITICAL,
        condition=lambda: error_rate_fn() > 0.05,
        get_value=error_rate_fn,
        threshold=0.05,
        duration=timedelta(minutes=5),
        cooldown=timedelta(minutes=15),
        labels={"category": "reliability"}
    )


def create_latency_rule(latency_fn: Callable[[], float]) -> AlertRule:
    """Crea regla para latencia p95 > 2 segundos."""
    return AlertRule(
        name="high_latency_p95",
        description="Latencia p95 excede 2 segundos",
        severity=AlertSeverity.WARNING,
        condition=lambda: latency_fn() > 2000,
        get_value=latency_fn,
        threshold=2000,
        duration=timedelta(minutes=2),
        cooldown=timedelta(minutes=10),
        labels={"category": "performance"}
    )


def create_db_connections_rule(connections_fn: Callable[[], float], max_connections: int) -> AlertRule:
    """Crea regla para conexiones a BD > 80% del pool."""
    threshold = max_connections * 0.8
    return AlertRule(
        name="high_db_connections",
        description=f"Conexiones a BD exceden 80% del pool ({threshold:.0f})",
        severity=AlertSeverity.WARNING,
        condition=lambda: connections_fn() > threshold,
        get_value=connections_fn,
        threshold=threshold,
        duration=timedelta(minutes=1),
        cooldown=timedelta(minutes=10),
        labels={"category": "database"}
    )


def create_llm_error_rate_rule(error_rate_fn: Callable[[], float]) -> AlertRule:
    """Crea regla para LLM API errors > 10%."""
    return AlertRule(
        name="high_llm_error_rate",
        description="Error rate de LLM API excede 10%",
        severity=AlertSeverity.WARNING,
        condition=lambda: error_rate_fn() > 0.10,
        get_value=error_rate_fn,
        threshold=0.10,
        duration=timedelta(minutes=3),
        cooldown=timedelta(minutes=15),
        labels={"category": "external_api"}
    )


def create_disk_space_rule(disk_usage_fn: Callable[[], float]) -> AlertRule:
    """Crea regla para disk space > 85%."""
    return AlertRule(
        name="high_disk_usage",
        description="Uso de disco excede 85%",
        severity=AlertSeverity.CRITICAL,
        condition=lambda: disk_usage_fn() > 85,
        get_value=disk_usage_fn,
        threshold=85,
        duration=timedelta(minutes=1),
        cooldown=timedelta(minutes=30),
        labels={"category": "system"}
    )


def create_memory_usage_rule(memory_usage_fn: Callable[[], float]) -> AlertRule:
    """Crea regla para memory usage > 90%."""
    return AlertRule(
        name="high_memory_usage",
        description="Uso de memoria excede 90%",
        severity=AlertSeverity.CRITICAL,
        condition=lambda: memory_usage_fn() > 90,
        get_value=memory_usage_fn,
        threshold=90,
        duration=timedelta(minutes=2),
        cooldown=timedelta(minutes=15),
        labels={"category": "system"}
    )


# Instancia global del alert manager
alert_manager = AlertManager()
