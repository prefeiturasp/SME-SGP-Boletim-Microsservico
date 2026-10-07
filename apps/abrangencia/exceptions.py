"""Exceções da integração de abrangência."""

from rest_framework.exceptions import APIException


class ServicoAbrangenciaIndisponivel(APIException):
    """Indica que a autorização não pôde ser consultada com segurança."""

    status_code = 503
    default_detail = "Serviço de abrangência temporariamente indisponível."
    default_code = "servico_abrangencia_indisponivel"
