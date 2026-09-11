from django.db import models
from core.models import BaseModel

class PortalSetting(BaseModel):
    institution_legal_name = models.CharField(
        max_length=255,
        default="Avemaria Career Guidance Center Ltd."
    )
    admissions_email = models.EmailField(
        default="admissions@avemariacareer.co.uk"
    )
    direct_telephone = models.CharField(
        max_length=50,
        default="+44 20 3960 4120"
    )
    whatsapp_desk = models.CharField(
        max_length=50,
        default="442039604120"
    )
    working_hours = models.CharField(
        max_length=100,
        default="Mon - Sat  09:00 - 18:00 (GMT)"
    )
    campus_address = models.TextField(
        default="71-75 Shelton Street, Covent Garden, London, WC2H 9JQ, United Kingdom"
    )

    class Meta:
        verbose_name = 'Portal & Brand Setting'
        verbose_name_plural = 'Portal & Brand Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.institution_legal_name
