from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine


class ConnectionTesterService:
    """
    Servicio de dominio (SRP) responsable de verificar la conectividad
    a una base de datos externa usando SQLAlchemy.
    """

    async def test_connection(self, connection_string: str) -> tuple[bool, str | None]:
        """
        Intenta establecer una conexión y devolverla inmediatamente.
        
        Args:
            connection_string: URI de conexión estilo SQLAlchemy.
            
        Returns:
            Una tupla (is_valid, error_message).
        """
        try:
            # Creamos un motor temporal
            engine = create_async_engine(connection_string, echo=False)
        except ArgumentError as e:
            return False, f"Invalid URL: {str(e)}"
        except Exception as e:
            return False, f"Could not parse URL: {str(e)}"

        try:
            # Intentamos abrir una conexión real
            async with engine.connect() as conn:
                pass  # Si pasamos esto, la DB conectó y autenticó correctamente
            
            return True, None
        except SQLAlchemyError as e:
            return False, str(e)
        finally:
            # Siempre desechamos el motor para no dejar recursos colgados
            await engine.dispose()
