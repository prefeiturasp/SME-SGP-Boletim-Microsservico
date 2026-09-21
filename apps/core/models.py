"""Abstrações de models compartilhadas pelo microsserviço."""

from django.db import models


class ModeloBase(models.Model):
    """Base abstrata para tabelas externas não gerenciadas pelo Django."""

    class Meta:
        abstract = True
        managed = False
