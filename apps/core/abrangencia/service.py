"""Regras compartilhadas de autorização por abrangência."""

from apps.core.abrangencia.cache_repository import (
    AbrangenciaCacheRepository,
)
from apps.core.abrangencia.client import AbrangenciaClient
from apps.core.abrangencia.models import (
    Abrangencia,
    RecursoAbrangencia,
    TipoAbrangencia,
)


class AbrangenciaService:
    """Verifica se um recurso pertence à abrangência informada."""

    def __init__(
        self,
        client: AbrangenciaClient | None = None,
        cache_repository: AbrangenciaCacheRepository | None = None,
    ) -> None:
        """Inicializa o serviço com a integração e o cache compartilhado.

        Args:
            client: Cliente opcional da API Pedagógica para testes.
            cache_repository: Cache opcional de abrangências para testes.
        """
        self._client = client or AbrangenciaClient()
        self._cache_repository = (
            cache_repository or AbrangenciaCacheRepository()
        )

    def obter_vigente(self, login: str, perfil: str) -> Abrangencia:
        """Obtém a abrangência vigente com cache por usuário e perfil.

        Apenas respostas válidas da API Pedagógica são armazenadas. Erros da
        integração continuam sendo propagados e nunca entram no cache.

        Args:
            login: Login autenticado presente no JWT.
            perfil: UUID normalizado do perfil selecionado.

        Returns:
            Abrangência vigente obtida do cache ou da API Pedagógica.

        Raises:
            ServicoAbrangenciaIndisponivel: Se a API Pedagógica falhar e não
                houver uma resposta válida armazenada.
        """
        chave = self._cache_repository.gerar_chave(login, perfil)
        abrangencia = self._cache_repository.obter(chave)
        if abrangencia is not None:
            return abrangencia

        with self._cache_repository.bloquear(chave) as adquirido:
            if adquirido:
                abrangencia = self._cache_repository.obter(chave)
                if abrangencia is not None:
                    return abrangencia
                abrangencia = self._client.obter_vigente(login, perfil)
                self._cache_repository.armazenar(chave, abrangencia)
                return abrangencia

        abrangencia = self._cache_repository.obter(chave)
        if abrangencia is not None:
            return abrangencia
        return self._client.obter_vigente(login, perfil)

    def pode_acessar(
        self,
        abrangencia: Abrangencia,
        recurso: RecursoAbrangencia,
    ) -> bool:
        """Valida o recurso conforme a granularidade do perfil.

        Args:
            abrangencia: Códigos e tipo de abrangência do usuário.
            recurso: Códigos institucionais do recurso solicitado.

        Returns:
            `True` quando o recurso pertence à abrangência; caso contrário,
            `False`.
        """
        if abrangencia.tipo == TipoAbrangencia.SME:
            return True
        if abrangencia.tipo in {
            TipoAbrangencia.PROFESSOR,
            TipoAbrangencia.UE_TURMAS_DISCIPLINAS,
        }:
            return (
                recurso.turma_codigo is not None
                and recurso.turma_codigo in abrangencia.turmas
            )
        if abrangencia.tipo == TipoAbrangencia.UE:
            return (
                recurso.ue_codigo is not None
                and recurso.ue_codigo in abrangencia.ues
            )
        if abrangencia.tipo == TipoAbrangencia.DRE:
            return (
                recurso.dre_codigo is not None
                and recurso.dre_codigo in abrangencia.dres
            )
        return False
