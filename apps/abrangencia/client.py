"""Cliente HTTP da API Pedagógica para consulta de abrangência."""

from __future__ import annotations

import json
from typing import cast
from urllib.parse import quote

import httpx
from django.conf import settings
from pybreaker import CircuitBreakerError
from sme_sidecar_sdk.http import build_http_client

from apps.abrangencia.exceptions import (
    ServicoAbrangenciaIndisponivel,
)
from apps.abrangencia.models import Abrangencia, TipoAbrangencia


class AbrangenciaClient:
    """Consulta a abrangência vigente de um usuário no Pedagógico."""

    def obter_vigente(self, login: str, perfil: str) -> Abrangencia:
        """Obtém e normaliza a abrangência vigente.

        Args:
            login: Login autenticado presente no JWT.
            perfil: Identificador UUID do perfil presente no JWT.

        Returns:
            Abrangência normalizada do usuário.

        Raises:
            ServicoAbrangenciaIndisponivel: Se a integração estiver mal
                configurada, indisponível ou retornar um contrato inválido.
        """
        base_url = settings.PEDAGOGICO_API_URL
        api_key = settings.PEDAGOGICO_API_KEY
        if not base_url or not api_key:
            raise ServicoAbrangenciaIndisponivel()

        caminho = (
            "/api/abrangencia/compacta-vigente/"
            f"{quote(login, safe='')}/perfil/{quote(perfil, safe='')}"
        )
        try:
            with build_http_client(
                "sme-pedagogico-api",
                base_url=base_url,
            ) as cliente:
                resposta = cliente.get(
                    caminho,
                    headers={settings.PEDAGOGICO_API_KEY_HEADER: api_key},
                )
                dados = resposta.json()
        except (
            CircuitBreakerError,
            httpx.HTTPError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            raise ServicoAbrangenciaIndisponivel() from error

        try:
            return self._mapear(cast(dict[str, object], dados))
        except (KeyError, TypeError, ValueError) as error:
            raise ServicoAbrangenciaIndisponivel() from error

    @classmethod
    def _mapear(cls, dados: dict[str, object]) -> Abrangencia:
        """Converte o contrato JSON do Pedagógico para o tipo interno.

        Args:
            dados: Objeto retornado pelo endpoint de abrangência compacta.

        Returns:
            Abrangência com tipo e códigos institucionais normalizados.

        Raises:
            KeyError: Se uma propriedade obrigatória estiver ausente.
            TypeError: Se a estrutura de uma propriedade for inválida.
            ValueError: Se o tipo de abrangência não for reconhecido.
        """
        grupo = cls._obter(dados, "abrangencia", "Abrangencia")
        if not isinstance(grupo, dict):
            raise TypeError("Abrangência ausente.")
        tipo_bruto = cls._obter(grupo, "abrangencia", "Abrangencia")
        return Abrangencia(
            tipo=TipoAbrangencia(int(cast(int | str, tipo_bruto))),
            dres=cls._codigos(dados, "idDres", "IdDres"),
            ues=cls._codigos(dados, "idUes", "IdUes"),
            turmas=cls._codigos(dados, "idTurmas", "IdTurmas"),
        )

    @staticmethod
    def _obter(dados: dict[str, object], camel: str, pascal: str) -> object:
        """Obtém uma propriedade em camelCase ou PascalCase.

        Args:
            dados: Objeto JSON que contém a propriedade.
            camel: Nome esperado quando a serialização usa camelCase.
            pascal: Nome alternativo quando a serialização usa PascalCase.

        Returns:
            Valor associado ao primeiro nome encontrado.

        Raises:
            KeyError: Se nenhum dos nomes existir no objeto.
        """
        if camel in dados:
            return dados[camel]
        return dados[pascal]

    @classmethod
    def _codigos(
        cls, dados: dict[str, object], camel: str, pascal: str
    ) -> frozenset[str]:
        """Normaliza uma coleção opcional de códigos como texto.

        Args:
            dados: Objeto JSON que contém a coleção.
            camel: Nome esperado quando a serialização usa camelCase.
            pascal: Nome alternativo quando a serialização usa PascalCase.

        Returns:
            Conjunto imutável de códigos, vazio quando a coleção for nula.

        Raises:
            KeyError: Se a propriedade não existir no objeto.
            TypeError: Se o valor não for uma lista nem nulo.
        """
        valores = cls._obter(dados, camel, pascal)
        if valores is None:
            return frozenset()
        if not isinstance(valores, list):
            raise TypeError("Coleção de códigos inválida.")
        return frozenset(str(valor) for valor in valores)
