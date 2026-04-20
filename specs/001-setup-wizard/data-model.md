# Data Model: Setup Wizard & Data Connectors

## Entities

### DataSourceConnection
Representa una conexión a una fuente de datos provista por el usuario. Puede ser una base de datos SQL o un archivo JSON estático. Esta información se almacena en la base de datos secundaria (SQLite) de estado de la aplicación.

- **id**: UUID (Primary Key)
- **user_session_id**: String (Identificador de la sesión del usuario para Multitenancy)
- **type**: Enum (`POSTGRESQL`, `MYSQL`, `SQLITE`, `JSON`)
- **name**: String (Nombre amigable asignado por el usuario, ej. "Ventas Q1")
- **connection_string**: String (URL de conexión, encriptado o seguro. Nulo si es JSON)
- **file_path**: String (Ruta local en el servidor donde se guardó el archivo JSON. Nulo si es SQL)
- **status**: Enum (`ACTIVE`, `ERROR`, `PENDING`)
- **created_at**: Timestamp
- **updated_at**: Timestamp
