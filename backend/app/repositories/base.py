from abc import ABC, abstractmethod

from app.models.connection import DataSourceConnection


class DataSourceRepository(ABC):
    """Protocolo abstracto para la persistencia de conexiones a fuentes de datos.

    Define el contrato que cualquier implementación concreta debe cumplir,
    permitiendo intercambiar el motor de persistencia sin alterar las capas superiores (DIP).
    """

    @abstractmethod
    async def save(self, connection: DataSourceConnection) -> DataSourceConnection:
        """Persiste una nueva conexión y retorna la entidad con su ID asignado."""

    @abstractmethod
    async def find_by_id(self, connection_id: str) -> DataSourceConnection | None:
        """Retorna una conexión por su ID, o None si no existe."""

    @abstractmethod
    async def find_by_session(self, session_id: str) -> list[DataSourceConnection]:
        """Retorna todas las conexiones activas para una sesión de usuario dada."""
