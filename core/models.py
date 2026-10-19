import uuid
from django.db import models

class BaseModel(models.Model):
    """
    Abstract base model providing audit timestamps, active status,
    UUID identifier, and soft-deletion flags for all domain models.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    is_active = models.BooleanField(default=True, help_text="Designates whether this record is active.")
    is_deleted = models.BooleanField(default=False, help_text="Designates whether this record is soft-deleted.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at', '-id']

    @property
    def uuid_str(self):
        return str(self.uuid)

