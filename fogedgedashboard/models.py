from django.db import models

class SecurityAlert(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    
    # Store the raw sensor telemetry
    rf_signal = models.FloatField()
    acoustic_freq = models.FloatField()
    seismic_vib = models.FloatField()
    object_mass = models.FloatField()

    def __str__(self):
        return f"{self.timestamp} - {self.alert_type}"
    
class EdgeMetric(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dropped_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Heartbeat: {self.dropped_count} dropped alerts at {self.timestamp}"