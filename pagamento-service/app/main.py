import logging
import signal
import socket
import sys

from app.mensageria.consumidor import consumir
from app.registro_log import configurar_logs

logger = logging.getLogger(__name__)


def encerrar(sinal, quadro):
    logger.info("Encerrando Pagamento Service")
    sys.exit(0)


def main() -> None:
    configurar_logs()
    signal.signal(signal.SIGTERM, encerrar)
    logger.info("Pagamento Service iniciado na instância %s", socket.gethostname())
    consumir()


if __name__ == "__main__":
    main()
