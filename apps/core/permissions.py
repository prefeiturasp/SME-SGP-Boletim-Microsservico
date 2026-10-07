"""Permissões compartilhadas pelas APIs do microsserviço."""

from __future__ import annotations

from typing import Protocol, cast
from uuid import UUID

from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.abrangencia.models import RecursoAbrangencia
from apps.core.abrangencia.service import AbrangenciaService
from apps.core.authentication import (
    ApiKeyAuthentication,
    BearerTokenAuthentication,
)


class _UsuarioComClaims(Protocol):
    claims: dict[str, object]


class _ViewComAbrangencia(Protocol):
    campos_abrangencia: dict[str, str]


class RequerAbrangenciaParaJwt(BasePermission):
    """Exige abrangência vigente para JWT e confia na API key interna."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Autoriza a requisição conforme a credencial autenticada.

        Args:
            request: Requisição já processada pelos autenticadores do DRF.
            view: View que declara os parâmetros sujeitos à abrangência.

        Returns:
            `True` para API key válida ou JWT dentro da abrangência; `False`
            quando nenhum autenticador suportado processou a requisição.

        Raises:
            NotAuthenticated: Se o JWT não identificar login e perfil.
            PermissionDenied: Se o recurso estiver fora da abrangência.
            ServicoAbrangenciaIndisponivel: Se não for possível consultar a
                autorização no Pedagógico.
        """
        autenticador = request.successful_authenticator
        if isinstance(autenticador, ApiKeyAuthentication):
            return True
        if not isinstance(autenticador, BearerTokenAuthentication):
            return False

        claims = cast(_UsuarioComClaims, request.user).claims
        login, perfil = self._obter_identidade(claims)
        recursos = self._obter_recursos(request, view)
        service = AbrangenciaService()
        abrangencia = service.obter_vigente(login, perfil)
        for recurso in recursos:
            if not service.pode_acessar(abrangencia, recurso):
                if recurso.turma_codigo is not None:
                    raise PermissionDenied(
                        f"A turma {recurso.turma_codigo} não está na "
                        "abrangência do usuário."
                    )
                raise PermissionDenied(
                    "Usuário sem abrangência para o recurso solicitado."
                )
        return True

    @staticmethod
    def _obter_identidade(
        claims: dict[str, object],
    ) -> tuple[str, str]:
        """Extrai login e perfil válidos das claims do Pedagógico.

        Args:
            claims: Claims de um JWT cuja assinatura já foi validada.

        Returns:
            Login e UUID normalizado do perfil selecionado.

        Raises:
            NotAuthenticated: Se o login estiver vazio ou o perfil não for
                um UUID válido.
        """
        login = claims.get("login")
        perfil = claims.get("perfil")
        if not isinstance(login, str) or not login.strip():
            raise NotAuthenticated("Token sem claim de login válida.")
        try:
            perfil_normalizado = str(UUID(str(perfil)))
        except (TypeError, ValueError, AttributeError) as error:
            raise NotAuthenticated(
                "Token sem claim de perfil válida."
            ) from error
        return login, perfil_normalizado

    @staticmethod
    def _obter_recursos(
        request: Request,
        view: APIView,
    ) -> list[RecursoAbrangencia]:
        """Mapeia os parâmetros declarados pela view para os recursos.

        Args:
            request: Requisição que contém os códigos institucionais.
            view: View com o mapa `campos_abrangencia` configurado.

        Returns:
            Recursos formados pelos códigos de DRE, UE e todas as turmas
            informadas, inclusive quando o parâmetro se repete.
        """
        configuracao = cast(_ViewComAbrangencia, view).campos_abrangencia
        dre_codigo = request.query_params.get(configuracao["dre"])
        ue_codigo = request.query_params.get(configuracao["ue"])
        turmas: list[str | None] = [
            *request.query_params.getlist(configuracao["turma"])
        ]
        if not turmas:
            turmas.append(None)
        return [
            RecursoAbrangencia(
                dre_codigo=dre_codigo,
                ue_codigo=ue_codigo,
                turma_codigo=turma_codigo,
            )
            for turma_codigo in turmas
        ]
