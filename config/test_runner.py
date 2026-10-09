"""Test runner para criação temporária de tabelas não gerenciadas."""

from typing import Any

from django.apps import apps
from django.db import connections
from django.test.runner import DiscoverRunner


class BoletimTestRunner(DiscoverRunner):
    """Cria tabelas de models externos somente durante os testes."""

    def setup_databases(self, **kwargs: Any) -> Any:
        """Prepara o banco de teste e cria models com `managed=False`."""
        result = super().setup_databases(**kwargs)
        with connections["default"].schema_editor() as editor:
            created_tables: set[str] = set()
            for model in apps.get_models():
                if not model._meta.managed:
                    table_name = model._meta.db_table
                    if table_name not in created_tables:
                        editor.create_model(model)
                        created_tables.add(table_name)
        return result
